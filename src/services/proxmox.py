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
            return Container.from_api_response(config, node_name, vmid=vmid)
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
        pools_dict = {}  # Use dict to deduplicate by storage name

        if node_name:
            nodes = [node_name]
        else:
            nodes = [n['node'] for n in self.client.nodes.get()]

        for node in nodes:
            try:
                storage_data = self.client.nodes(node).storage.get()
                for storage in storage_data:
                    pool = StoragePool.from_api_response(storage)
                    pool_name = pool.name

                    if pool_name in pools_dict:
                        # Pool already exists, just add this node to available nodes
                        if node not in pools_dict[pool_name].nodes:
                            pools_dict[pool_name].nodes.append(node)
                    else:
                        # New pool
                        pool.nodes = [node]
                        pools_dict[pool_name] = pool
            except Exception as e:
                logger.warning(f"Failed to get storage from node {node}: {e}")

        return list(pools_dict.values())

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
        templates_dict = {}  # Use dict to deduplicate by template name

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
                            template_key = f"{pool.name}:{template.name}"

                            if template_key in templates_dict:
                                # Template already exists, just add this node to available_on_nodes
                                if node not in templates_dict[template_key].available_on_nodes:
                                    templates_dict[template_key].available_on_nodes.append(node)
                            else:
                                # New template
                                template.available_on_nodes = [node]
                                templates_dict[template_key] = template

                except Exception as e:
                    logger.warning(f"Failed to get templates from {pool.name} on {node}: {e}")

        return list(templates_dict.values())

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

    def get_next_vmid(self, min_vmid: int = 100) -> int:
        """Get the next available VMID.

        Args:
            min_vmid: Minimum VMID to start from (default: 100)

        Returns:
            Next available VMID
        """
        try:
            result = self.client.cluster.nextid.get()
            vmid = int(result)
            # Ensure we don't go below the minimum
            return max(vmid, min_vmid)
        except Exception as e:
            logger.warning(f"Failed to get next VMID: {e}")
            # Fallback: find highest VMID and add 1
            containers = self.list_containers()
            if containers:
                max_vmid = max(ct['vmid'] for ct in containers)
                return max(max_vmid + 1, min_vmid)
            return min_vmid  # Start from min_vmid if no containers

    def exec_container_command(self, node_name: str, vmid: int, command: str) -> Tuple[bool, str]:
        """Execute a command in a container via pct exec on Proxmox host.

        Args:
            node_name: Node where container resides
            vmid: Container ID
            command: Command to execute

        Returns:
            Tuple of (success, output)
        """
        import paramiko
        import os

        # Suppress paramiko logging for cleaner output
        paramiko_logger = logging.getLogger('paramiko')
        original_level = paramiko_logger.level
        paramiko_logger.setLevel(logging.WARNING)

        try:
            # SSH to the specific Proxmox node (not the API endpoint)
            # The node_name is the actual server we want to connect to via Tailscale SSH
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # Try to connect with SSH key from environment
            ssh_key_path = os.environ.get('SSH_KEY_PATH', '~/.ssh/id_rsa')
            ssh_key_path = os.path.expanduser(ssh_key_path)

            ssh.connect(
                hostname=node_name,  # Use the actual node name (e.g., "c137")
                username='root',
                key_filename=ssh_key_path if os.path.exists(ssh_key_path) else None,
                timeout=30
            )

            # Execute pct exec command
            pct_command = f"pct exec {vmid} -- {command}"
            logger.debug(f"Executing on {node_name}: {pct_command}")

            stdin, stdout, stderr = ssh.exec_command(pct_command)
            exit_code = stdout.channel.recv_exit_status()

            output = stdout.read().decode('utf-8')
            error = stderr.read().decode('utf-8')

            ssh.close()

            if exit_code == 0:
                return True, output
            else:
                logger.error(f"Command failed with exit code {exit_code}: {error}")
                return False, error

        except Exception as e:
            logger.error(f"Failed to execute command in container {vmid}: {e}")
            return False, str(e)
        finally:
            # Restore original paramiko log level
            paramiko_logger.setLevel(original_level)

    def provision_container_via_exec(self, node_name: str, vmid: int, provisioning_config) -> bool:
        """Provision container using pct exec commands.

        Args:
            node_name: Node where container resides
            vmid: Container ID
            provisioning_config: ProvisioningConfig object

        Returns:
            True if provisioning succeeded, False otherwise
        """
        try:
            # Skip SSH key installation - Tailscale SSH handles authentication

            # Update package lists
            logger.info("Updating package lists...")
            success, output = self.exec_container_command(node_name, vmid, "apt-get update")
            if not success:
                logger.warning(f"Failed to update package lists: {output}")

            # Install packages
            if provisioning_config.packages:
                packages_str = " ".join(provisioning_config.packages)
                logger.info(f"Installing packages: {packages_str}")
                success, output = self.exec_container_command(
                    node_name, vmid,
                    f"bash -c 'DEBIAN_FRONTEND=noninteractive apt-get install -y {packages_str}'"
                )
                if not success:
                    logger.error(f"Failed to install packages: {output}")
                    return False
                logger.info("Packages installed successfully")

            # Install Docker if requested
            if provisioning_config.docker:
                logger.info("Installing Docker...")
                commands = [
                    ("Install prerequisites", "bash -c 'DEBIAN_FRONTEND=noninteractive apt-get install -y ca-certificates curl'"),
                    ("Create keyrings directory", "install -m 0755 -d /etc/apt/keyrings"),
                    ("Download Docker GPG key", "curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc"),
                    ("Set GPG key permissions", "chmod a+r /etc/apt/keyrings/docker.asc"),
                    ("Add Docker repository", "bash -c '. /etc/os-release && echo \"deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian $VERSION_CODENAME stable\" | tee /etc/apt/sources.list.d/docker.list > /dev/null'"),
                    ("Update package lists", "apt-get update"),
                    ("Install Docker", "bash -c 'DEBIAN_FRONTEND=noninteractive apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin'")
                ]
                for description, cmd in commands:
                    success, output = self.exec_container_command(node_name, vmid, cmd)
                    if not success:
                        logger.error(f"Failed to {description.lower()}: {output}")
                        return False
                logger.info("Docker installed successfully")

            # Install Tailscale if configured
            if provisioning_config.tailscale and provisioning_config.tailscale.auth_key:
                logger.info("Installing Tailscale...")

                # Resolve environment variable if needed
                auth_key = provisioning_config.tailscale.auth_key
                if auth_key.startswith("${") and auth_key.endswith("}"):
                    env_var = auth_key[2:-1]
                    auth_key = os.environ.get(env_var, "")
                    if not auth_key:
                        logger.error(f"Environment variable {env_var} not found")
                        return False

                commands = [
                    ("Install Tailscale", "curl -fsSL https://tailscale.com/install.sh | sh"),
                    ("Connect to Tailscale", f"tailscale up --authkey={auth_key}")
                ]
                for description, cmd in commands:
                    success, output = self.exec_container_command(node_name, vmid, cmd)
                    if not success:
                        logger.error(f"Failed to {description.lower()}: {output}")
                        return False
                logger.info("Tailscale configured successfully")

            return True

        except Exception as e:
            logger.error(f"Provisioning failed: {e}")
            return False

    def configure_lxc_for_tailscale(self, node_name: str, vmid: int) -> bool:
        """Configure LXC container for Tailscale by adding TUN device mapping.

        Args:
            node_name: Node where container resides
            vmid: Container ID

        Returns:
            True if configuration succeeded, False otherwise
        """
        import paramiko
        import os

        # Suppress paramiko logging for cleaner output
        paramiko_logger = logging.getLogger('paramiko')
        original_level = paramiko_logger.level
        paramiko_logger.setLevel(logging.WARNING)

        try:
            logger.info("Configuring LXC for Tailscale...")

            # SSH to the Proxmox node
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            ssh_key_path = os.environ.get('SSH_KEY_PATH', '~/.ssh/id_rsa')
            ssh_key_path = os.path.expanduser(ssh_key_path)

            ssh.connect(
                hostname=node_name,
                username='root',
                key_filename=ssh_key_path if os.path.exists(ssh_key_path) else None,
                timeout=30
            )

            # Check if TUN device mapping already exists
            check_cmd = f"grep -q 'dev/net/tun' /etc/pve/lxc/{vmid}.conf"
            stdin, stdout, stderr = ssh.exec_command(check_cmd)
            exit_code = stdout.channel.recv_exit_status()

            if exit_code == 0:
                logger.debug("TUN device mapping already exists")
                ssh.close()
                return True

            # Add TUN device mapping to LXC config
            logger.debug("Adding TUN device mapping to LXC config")
            config_lines = [
                "# Allow TUN device for Tailscale",
                "lxc.cgroup2.devices.allow: c 10:200 rwm",
                "lxc.mount.entry: /dev/net/tun dev/net/tun none bind,create=file"
            ]

            for line in config_lines:
                add_cmd = f"echo '{line}' >> /etc/pve/lxc/{vmid}.conf"
                stdin, stdout, stderr = ssh.exec_command(add_cmd)
                exit_code = stdout.channel.recv_exit_status()
                if exit_code != 0:
                    error = stderr.read().decode('utf-8')
                    logger.error(f"Failed to add config line: {error}")
                    ssh.close()
                    return False

            ssh.close()
            logger.info("LXC configured for Tailscale")
            return True

        except Exception as e:
            logger.error(f"Failed to configure LXC for Tailscale: {e}")
            return False
        finally:
            paramiko_logger.setLevel(original_level)


# Alias for backwards compatibility
ProxmoxAPI = ProxmoxService