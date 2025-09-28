"""Proxmox API service wrapper."""

import os
import warnings
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import logging

# Suppress SSL warnings if not verifying
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from proxmoxer import ProxmoxAPI as ProxmoxClient
from proxmoxer import AuthenticationError

from src.models.container import Container
from src.models.cluster import ClusterNode
from src.models.template import Template
from src.models.storage import StoragePool

logger = logging.getLogger(__name__)


@dataclass
class ProxmoxAuth:
    """Proxmox authentication configuration."""

    host: str
    token_id: str
    token_secret: str
    verify_ssl: bool = True

    @classmethod
    def from_env(cls) -> 'ProxmoxAuth':
        """Create auth config from environment variables.

        Returns:
            ProxmoxAuth instance

        Raises:
            ValueError: If required environment variables are missing
        """
        # Load .env file if exists
        from src.services.credentials import CredentialsManager
        creds = CredentialsManager()
        creds.load_env_file()

        host = os.environ.get('PROXMOX_HOST')
        token_id = os.environ.get('PROXMOX_TOKEN_ID')
        token_secret = os.environ.get('PROXMOX_TOKEN_SECRET')

        if not all([host, token_id, token_secret]):
            missing = []
            if not host:
                missing.append('PROXMOX_HOST')
            if not token_id:
                missing.append('PROXMOX_TOKEN_ID')
            if not token_secret:
                missing.append('PROXMOX_TOKEN_SECRET')
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

        # Clean up host URL - remove https:// prefix if present
        if host.startswith('https://'):
            host = host[8:]
        elif host.startswith('http://'):
            host = host[7:]

        verify_ssl = os.environ.get('PROXMOX_VERIFY_SSL', 'false').lower() == 'true'

        return cls(
            host=host,
            token_id=token_id,
            token_secret=token_secret,
            verify_ssl=verify_ssl
        )


class ProxmoxService:
    """Service wrapper for Proxmox API operations."""

    def __init__(self, auth: Optional[ProxmoxAuth] = None):
        """Initialize Proxmox service.

        Args:
            auth: Authentication configuration (uses env vars if not provided)
        """
        self.auth = auth or ProxmoxAuth.from_env()
        self._client = None

    @property
    def client(self) -> ProxmoxClient:
        """Get or create Proxmox API client.

        Returns:
            Proxmox API client instance
        """
        if self._client is None:
            # Parse token_id to get user and token name
            if '!' in self.auth.token_id:
                user, token_name = self.auth.token_id.split('!', 1)
            else:
                user = self.auth.token_id
                token_name = ''

            # Proxmoxer expects these separately
            self._client = ProxmoxClient(
                self.auth.host,
                user=user,
                token_name=token_name,
                token_value=self.auth.token_secret,
                verify_ssl=self.auth.verify_ssl,
                port=443 if ':' not in self.auth.host else None  # Use 443 for HTTPS by default
            )
        return self._client

    def test_connection(self) -> bool:
        """Test connection to Proxmox API.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Try to get version info
            version = self.client.version.get()
            logger.info(f"Connected to Proxmox VE {version.get('version', 'unknown')}")
            return True
        except AuthenticationError:
            logger.error("Authentication failed - check credentials")
            return False
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False

    # Node operations

    def list_nodes(self) -> List[ClusterNode]:
        """List all nodes in the cluster.

        Returns:
            List of ClusterNode objects
        """
        nodes = []
        for node_data in self.client.nodes.get():
            node = ClusterNode.from_api_response(node_data)

            # Get network bridges for this node
            try:
                network_data = self.client.nodes(node.name).network.get()
                bridges = [net['iface'] for net in network_data
                          if net.get('type') == 'bridge']
                node.networks = bridges
            except:
                pass

            # Get storage pools for this node
            try:
                storage_data = self.client.nodes(node.name).storage.get()
                for storage in storage_data:
                    pool = StoragePool.from_api_response(storage)
                    node.storage_pools.append(pool)
            except:
                pass

            nodes.append(node)

        return nodes

    def get_node(self, node_name: str) -> Optional[ClusterNode]:
        """Get specific node by name.

        Args:
            node_name: Name of the node

        Returns:
            ClusterNode object or None if not found
        """
        nodes = self.list_nodes()
        for node in nodes:
            if node.name == node_name:
                return node
        return None

    # Container operations

    def create_container(self, container: Container) -> str:
        """Create a new LXC container.

        Args:
            container: Container configuration

        Returns:
            Task ID for the creation operation

        Raises:
            ValueError: If validation fails
            RuntimeError: If API call fails
        """
        # Validate container configuration
        container.validate()

        # Get node
        node = self.client.nodes(container.node)

        # Convert to API parameters
        params = container.to_api_params()

        # Create container
        try:
            result = node.lxc.create(**params)
            task_id = result
            logger.info(f"Container creation started: VMID={container.vmid}, Task={task_id}")
            return task_id
        except Exception as e:
            logger.error(f"Failed to create container: {e}")
            raise RuntimeError(f"Container creation failed: {e}")

    def destroy_container(self, node_name: str, vmid: int, purge: bool = True) -> str:
        """Destroy an LXC container.

        Args:
            node_name: Node where container resides
            vmid: Container ID
            purge: Also remove from backup storage

        Returns:
            Task ID for the destruction operation
        """
        node = self.client.nodes(node_name)

        try:
            # Stop container first if running
            try:
                status = node.lxc(vmid).status.current.get()
                if status['status'] == 'running':
                    node.lxc(vmid).status.stop.post()
            except:
                pass  # Container might already be stopped

            # Delete container
            result = node.lxc(vmid).delete(purge=1 if purge else 0)
            task_id = result
            logger.info(f"Container destruction started: VMID={vmid}, Task={task_id}")
            return task_id
        except Exception as e:
            logger.error(f"Failed to destroy container: {e}")
            raise RuntimeError(f"Container destruction failed: {e}")

    def list_containers(self, node_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all LXC containers.

        Args:
            node_name: Optional node name to filter by

        Returns:
            List of container information dictionaries
        """
        containers = []

        if node_name:
            nodes = [node_name]
        else:
            # Get all nodes
            nodes = [n['node'] for n in self.client.nodes.get()]

        for node in nodes:
            try:
                node_containers = self.client.nodes(node).lxc.get()
                for ct in node_containers:
                    ct['node'] = node
                    containers.append(ct)
            except Exception as e:
                logger.warning(f"Failed to get containers from node {node}: {e}")

        return containers

    def get_container(self, node_name: str, vmid: int) -> Optional[Container]:
        """Get specific container by VMID.

        Args:
            node_name: Node where container resides
            vmid: Container ID

        Returns:
            Container object or None if not found
        """
        try:
            config = self.client.nodes(node_name).lxc(vmid).config.get()
            return Container.from_api_response(config, node_name)
        except Exception as e:
            logger.error(f"Failed to get container {vmid}: {e}")
            return None

    def start_container(self, node_name: str, vmid: int) -> str:
        """Start a container.

        Args:
            node_name: Node where container resides
            vmid: Container ID

        Returns:
            Task ID for the operation
        """
        try:
            result = self.client.nodes(node_name).lxc(vmid).status.start.post()
            return result
        except Exception as e:
            logger.error(f"Failed to start container {vmid}: {e}")
            raise RuntimeError(f"Container start failed: {e}")

    def stop_container(self, node_name: str, vmid: int) -> str:
        """Stop a container.

        Args:
            node_name: Node where container resides
            vmid: Container ID

        Returns:
            Task ID for the operation
        """
        try:
            result = self.client.nodes(node_name).lxc(vmid).status.stop.post()
            return result
        except Exception as e:
            logger.error(f"Failed to stop container {vmid}: {e}")
            raise RuntimeError(f"Container stop failed: {e}")

    # Storage operations

    def get_storage_pools(self, node_name: Optional[str] = None) -> List[StoragePool]:
        """Get available storage pools.

        Args:
            node_name: Optional node name to filter by

        Returns:
            List of StoragePool objects
        """
        pools = []

        if node_name:
            nodes = [node_name]
        else:
            nodes = [n['node'] for n in self.client.nodes.get()]

        for node in nodes:
            try:
                storage_data = self.client.nodes(node).storage.get()
                for storage in storage_data:
                    pool = StoragePool.from_api_response(storage)
                    if node not in pool.nodes:
                        pool.nodes.append(node)
                    pools.append(pool)
            except Exception as e:
                logger.warning(f"Failed to get storage from node {node}: {e}")

        return pools

    # Template operations

    def get_templates(self, node_name: Optional[str] = None,
                     storage_name: Optional[str] = None) -> List[Template]:
        """Get available container templates.

        Args:
            node_name: Optional node name to filter by
            storage_name: Optional storage name to filter by

        Returns:
            List of Template objects
        """
        templates = []

        if node_name:
            nodes = [node_name]
        else:
            nodes = [n['node'] for n in self.client.nodes.get()]

        for node in nodes:
            # Get storage pools that support templates
            storage_pools = self.get_storage_pools(node)

            for pool in storage_pools:
                if not pool.supports_templates():
                    continue

                if storage_name and pool.name != storage_name:
                    continue

                try:
                    # Get contents of this storage
                    contents = self.client.nodes(node).storage(pool.name).content.get()

                    for item in contents:
                        if item.get('content') == 'vztmpl':
                            template = Template.from_api_response(item, pool.name)
                            if node not in template.available_on_nodes:
                                template.available_on_nodes.append(node)
                            templates.append(template)

                except Exception as e:
                    logger.warning(f"Failed to get templates from {pool.name} on {node}: {e}")

        return templates

    # Task operations

    def wait_for_task(self, node_name: str, task_id: str,
                     timeout: int = 60) -> Tuple[bool, str]:
        """Wait for a task to complete.

        Args:
            node_name: Node where task is running
            task_id: Task ID to wait for
            timeout: Maximum seconds to wait

        Returns:
            Tuple of (success, status_message)
        """
        import time

        node = self.client.nodes(node_name)
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                status = node.tasks(task_id).status.get()

                if status['status'] == 'stopped':
                    if status.get('exitstatus') == 'OK':
                        return True, "Task completed successfully"
                    else:
                        return False, f"Task failed: {status.get('exitstatus', 'Unknown error')}"

                time.sleep(1)

            except Exception as e:
                logger.error(f"Error checking task status: {e}")
                return False, str(e)

        return False, f"Task timeout after {timeout} seconds"

    def get_next_vmid(self) -> int:
        """Get the next available VMID.

        Returns:
            Next available VMID
        """
        try:
            result = self.client.cluster.nextid.get()
            return int(result)
        except Exception as e:
            logger.warning(f"Failed to get next VMID: {e}")
            # Fallback: find highest VMID and add 1
            containers = self.list_containers()
            if containers:
                max_vmid = max(ct['vmid'] for ct in containers)
                return max_vmid + 1
            return 100  # Start from 100 if no containers


# Alias for backwards compatibility
ProxmoxAPI = ProxmoxService