"""Proxmox API service wrapper."""

import os
import sys
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
from src.utils import output

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
        self._tailscale_info = None  # Store Tailscale info after provisioning

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
            ValueError: If validation fails or VMID already exists
            RuntimeError: If API call fails
        """
        # Validate container configuration
        container.validate()

        # Check if VMID already exists
        existing = None
        try:
            existing = self.get_container_info(container.node, container.vmid)
        except Exception as e:
            # If we can't check, continue (unless it's a ValueError we're raising)
            if isinstance(e, ValueError):
                raise
            pass
        
        if existing:
            logger.error(f"Container with VMID {container.vmid} already exists on node {container.node}")
            raise ValueError(f"Container with VMID {container.vmid} already exists. Please use a different VMID or remove the existing container.")

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
            error_msg = str(e)
            logger.error(f"Failed to create container: {error_msg}")
            
            # Provide more specific error messages for common failures
            if "500 Internal Server Error" in error_msg:
                # Check for common causes of 500 errors
                if "already exists" in error_msg.lower() or "duplicate" in error_msg.lower():
                    raise ValueError(f"Container with VMID {container.vmid} already exists. Please use a different VMID.")
                elif "storage" in error_msg.lower():
                    raise RuntimeError(f"Storage pool error: {error_msg}. Please check that storage pool '{container.storage_pool}' exists and has sufficient space.")
                elif "template" in error_msg.lower():
                    raise RuntimeError(f"Template error: {error_msg}. Please check that template '{container.template}' exists and is accessible.")
                else:
                    raise RuntimeError(f"Container creation failed with server error. This often means the VMID {container.vmid} is already in use, the storage pool is full, or there's a template issue. Original error: {error_msg}")
            elif "401" in error_msg or "permission" in error_msg.lower():
                raise RuntimeError(f"Permission denied. Please check your API token has the required privileges for creating containers.")
            elif "404" in error_msg:
                raise RuntimeError(f"Resource not found. Please check that node '{container.node}' exists and is accessible.")
            elif "timeout" in error_msg.lower():
                raise RuntimeError(f"Operation timed out. The Proxmox server may be overloaded or the container creation is taking longer than expected.")
            else:
                raise RuntimeError(f"Container creation failed: {error_msg}")

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

    def get_container_info(self, node_name: str, vmid: int) -> Optional[Dict[str, Any]]:
        """Get container runtime information including network details.

        Args:
            node_name: Node where container resides
            vmid: Container ID

        Returns:
            Container runtime info dict or None if not found
        """
        try:
            # Get container status which includes network information
            status = self.client.nodes(node_name).lxc(vmid).status.current.get()
            return status
        except Exception as e:
            # Don't log 500 errors right after container creation - these are expected
            if "500" not in str(e):
                logger.error(f"Failed to get container info for {vmid}: {e}")
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

    def exec_container_command_streaming(self, node_name: str, vmid: int, command: str, stage_name: str = "", verbose: bool = None, add_line_func=None) -> Tuple[bool, str]:
        """Execute a command in a container with real-time output streaming.

        Args:
            node_name: Node where container resides
            vmid: Container ID
            command: Command to execute
            stage_name: Optional stage name for prefixed output
            verbose: Whether to show verbose output (defaults to PXRUN_VERBOSE env var)
            add_line_func: Optional function to call with each output line

        Returns:
            Tuple of (success, full_output)
        """
        import paramiko
        import os
        import sys
        import select

        # Check verbosity setting
        if verbose is None:
            verbose = os.environ.get('PXRUN_VERBOSE', '1').lower() in ('1', 'true', 'yes')

        # Suppress paramiko logging for cleaner output
        paramiko_logger = logging.getLogger('paramiko')
        original_level = paramiko_logger.level
        paramiko_logger.setLevel(logging.WARNING)

        output_lines = []

        try:
            # SSH to the specific Proxmox node
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

            # Execute pct exec command
            pct_command = f"pct exec {vmid} -- {command}"

            # Create channel for streaming
            channel = ssh.get_transport().open_session()
            channel.exec_command(pct_command)

            # Stream output in real-time
            while True:
                # Check if channel is ready for reading
                ready, _, _ = select.select([channel], [], [], 0.1)

                if ready:
                    # Read available data
                    if channel.recv_ready():
                        chunk = channel.recv(1024).decode('utf-8', errors='replace')
                        if chunk:
                            # Print each line with proper indentation (if verbose)
                            for line in chunk.splitlines():
                                if line.strip():
                                    if add_line_func:
                                        add_line_func(line)
                                    output_lines.append(line)
                            # Handle partial lines
                            if not chunk.endswith('\n') and verbose:
                                sys.stdout.flush()

                    if channel.recv_stderr_ready():
                        chunk = channel.recv_stderr(1024).decode('utf-8', errors='replace')
                        if chunk:
                            for line in chunk.splitlines():
                                if line.strip():
                                    if add_line_func:
                                        add_line_func(line)
                                    output_lines.append(line)

                # Check if command finished
                if channel.exit_status_ready():
                    break

            # Get final exit status
            exit_code = channel.recv_exit_status()
            full_output = '\n'.join(output_lines)

            ssh.close()

            return exit_code == 0, full_output

        except Exception as e:
            logger.error(f"Failed to execute streaming command: {e}")
            return False, str(e)
        finally:
            paramiko_logger.setLevel(original_level)


    def get_stored_tailscale_info(self) -> Optional[Dict[str, str]]:
        """Get stored Tailscale info from last provisioning.
        
        Returns:
            Dict with 'fqdn' and 'ip' keys, or None if not available
        """
        return self._tailscale_info
    
    def get_tailscale_info(self, node_name: str, vmid: int) -> Optional[Dict[str, str]]:
        """Get Tailscale connection info from a container.
        
        Args:
            node_name: Node where container resides
            vmid: Container ID
            
        Returns:
            Dict with 'fqdn' and 'ip' keys, or None if not available
        """
        try:
            # Get Tailscale status
            success, output = self.exec_container_command(
                node_name, vmid,
                "tailscale status --json"
            )
            
            if success and output:
                import json
                status = json.loads(output)
                
                # Get the self node info
                self_node = status.get('Self', {})
                tailnet_name = status.get('MagicDNSSuffix', '')
                hostname = self_node.get('HostName', '')
                
                # Build FQDN
                fqdn = f"{hostname}.{tailnet_name}" if hostname and tailnet_name else None
                
                # Get Tailscale IP
                tailscale_ips = self_node.get('TailscaleIPs', [])
                tailscale_ip = tailscale_ips[0] if tailscale_ips else None
                
                if fqdn and tailscale_ip:
                    return {
                        'fqdn': fqdn,
                        'ip': tailscale_ip,
                        'hostname': hostname
                    }
        except Exception as e:
            logger.debug(f"Could not get Tailscale info: {e}")
        
        return None
    
    def provision_container_via_exec(self, node_name: str, vmid: int, provisioning_config, verbose: bool = None) -> bool:
        """Provision container using pct exec commands with stage-based output.

        Args:
            node_name: Node where container resides
            vmid: Container ID
            provisioning_config: ProvisioningConfig object
            verbose: Whether to show verbose output (defaults to PXRUN_VERBOSE env var)

        Returns:
            True if provisioning succeeded, False otherwise
        """
        try:
            # Check verbosity setting
            if verbose is None:
                verbose = os.environ.get('PXRUN_VERBOSE', '1').lower() in ('1', 'true', 'yes')

            # Configure locales first to prevent SSH warnings (for Debian/Ubuntu containers)
            # Don't use spinner here as it conflicts with Live displays used later
            # Install locales package first
            success, cmd_output = self.exec_container_command_streaming(
                node_name, vmid,
                "bash -c 'export DEBIAN_FRONTEND=noninteractive && apt update -qq && apt install -y locales'",
                verbose=False
            )
            
            if success:
                # Now properly configure locales - use dpkg-reconfigure which is the proper Debian way
                locale_setup_cmds = [
                    # First, ensure the locale is available in locale.gen
                    "sed -i 's/^# *en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen",
                    # Generate the locale
                    "locale-gen",
                    # Set it as the default using update-locale (the proper Debian tool)
                    "update-locale LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8"
                ]
                
                for cmd in locale_setup_cmds:
                    success, cmd_output = self.exec_container_command_streaming(
                        node_name, vmid,
                        cmd,
                        verbose=False
                    )
                    if not success and verbose:
                        logger.debug(f"Warning: locale command '{cmd}' had issues")

            # Skip SSH key installation - Tailscale SSH handles authentication
            
            # Track step progress
            current_step = 0
            total_steps = 1  # package update
            if provisioning_config.packages:
                total_steps += 1
            if provisioning_config.docker:
                total_steps += 1
            if provisioning_config.tailscale:
                total_steps += 1
            if provisioning_config.scripts:
                total_steps += len(provisioning_config.scripts)

            # Update package lists
            current_step += 1
            with output.live_output("Updating package lists") as add_line:
                success, cmd_output = self.exec_container_command_streaming(
                    node_name, vmid, "apt update", 
                    verbose=verbose, add_line_func=add_line  # Always stream to display
                )
                if not success:
                    output.error(f"Failed to update package lists: {cmd_output}")
                    return False
            output.success(f"[{current_step}/{total_steps}] Package lists updated")

            # Install packages
            if provisioning_config.packages:
                current_step += 1
                packages_str = " ".join(provisioning_config.packages)
                with output.live_output(f"Installing packages: {packages_str}") as add_line:
                    success, cmd_output = self.exec_container_command_streaming(
                        node_name, vmid,
                        f"bash -c 'DEBIAN_FRONTEND=noninteractive apt install -y {packages_str}'",
                        verbose=verbose, add_line_func=add_line  # Always stream to display
                    )
                    if not success:
                        output.error(f"Failed to install packages: {cmd_output}")
                        return False
                output.success(f"[{current_step}/{total_steps}] Packages installed")

            # Install Docker if requested
            if provisioning_config.docker:
                current_step += 1
                with output.live_output("Installing Docker") as add_line:
                    commands = [
                        ("Install prerequisites", "bash -c 'DEBIAN_FRONTEND=noninteractive apt install -y ca-certificates curl'"),
                        ("Create keyrings directory", "install -m 0755 -d /etc/apt/keyrings"),
                        ("Download Docker GPG key", "curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc"),
                        ("Set GPG key permissions", "chmod a+r /etc/apt/keyrings/docker.asc"),
                        ("Add Docker repository", "bash -c '. /etc/os-release && echo \"deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian $VERSION_CODENAME stable\" | tee /etc/apt/sources.list.d/docker.list > /dev/null'"),
                        ("Update package lists", "apt update"),
                        ("Install Docker", "bash -c 'DEBIAN_FRONTEND=noninteractive apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin'")
                    ]
                    for description, cmd in commands:
                        add_line(f"• {description}...")  # Always show progress
                        success, cmd_output = self.exec_container_command_streaming(
                            node_name, vmid, cmd, 
                            verbose=verbose, add_line_func=add_line  # Always stream to display
                        )
                        if not success:
                            output.error(f"Docker installation failed during {description.lower()}: {cmd_output}")
                            return False
                output.success(f"[{current_step}/{total_steps}] Docker installed")

            # Install Tailscale if configured
            if provisioning_config.tailscale:
                current_step += 1
                with output.live_output("Installing Tailscale") as add_line:
                    # Try to get or generate an auth key
                    from src.services.tailscale import TailscaleProvisioningService
                    
                    try:
                        provisioning_service = TailscaleProvisioningService()
                        # Try to get container hostname for the key description
                        container_name = provisioning_config.tailscale.hostname or f"container-{vmid}"
                        
                        # Always try to generate a fresh key if API is available, respecting ephemeral setting
                        ephemeral = provisioning_config.tailscale.ephemeral
                        auth_key = provisioning_service.get_or_generate_auth_key(container_name, ephemeral=ephemeral)
                        
                        if not auth_key:
                            output.error("Could not obtain Tailscale auth key")
                            return False
                            
                    except Exception as e:
                        # Fall back to resolving from environment if present
                        auth_key = provisioning_config.tailscale.auth_key
                        if auth_key.startswith("${") and auth_key.endswith("}"):
                            env_var = auth_key[2:-1]
                            auth_key = os.environ.get(env_var, "")
                        
                        if not auth_key:
                            output.error(f"Failed to get auth key: {e}")
                            return False
                        
                        # Log that we're using fallback
                        add_line("• Using fallback auth key from config/env")

                    # Use the official installation script but with better error handling
                    commands = [
                        ("Download Tailscale installer", "curl -fsSL https://tailscale.com/install.sh -o /tmp/tailscale-install.sh"),
                        ("Make installer executable", "chmod +x /tmp/tailscale-install.sh"),
                        ("Install Tailscale", "/tmp/tailscale-install.sh"),
                        ("Start Tailscale daemon", "systemctl enable --now tailscaled"),
                        ("Wait for daemon", "sleep 2"),
                        #todo why is accept-risk needed here?
                        ("Connect to Tailscale", f"tailscale up --authkey={auth_key} --ssh --accept-risk=lose-ssh")
                    ]
                    for description, cmd in commands:
                        add_line(f"• {description}...")  # Always show progress
                        success, cmd_output = self.exec_container_command_streaming(
                            node_name, vmid, cmd, 
                            verbose=verbose, add_line_func=add_line  # Always stream to display
                        )
                        if not success:
                            output.error(f"Tailscale installation failed during {description.lower()}: {cmd_output}")
                            return False
                
                # Capture Tailscale connection info
                tailscale_info = self.get_tailscale_info(node_name, vmid)
                if tailscale_info:
                    # Store the info for later use
                    self._tailscale_info = tailscale_info
                    output.success(f"[{current_step}/{total_steps}] Tailscale connected: {tailscale_info.get('fqdn', 'unknown')}")
                else:
                    output.success(f"[{current_step}/{total_steps}] Tailscale installed and connected")

            # Run custom scripts if provided
            if provisioning_config.scripts:
                for script in provisioning_config.scripts:
                    current_step += 1
                    with output.live_output(f"Running script: {script.name}") as add_line:
                        # Write script to temporary file
                        script_path = f"/tmp/pxrun_script_{script.name}.sh"
                        script_content = f"#!/bin/{script.interpreter}\n{script.content}"

                        add_line(f"• Writing script to {script_path}...")  # Always show progress
                        success, cmd_output = self.exec_container_command_streaming(
                            node_name, vmid,
                            f"cat > {script_path} << 'EOF'\n{script_content}\nEOF",
                            verbose=False
                        )
                        if not success:
                            output.error(f"Failed to write script: {cmd_output}")
                            if not script.continue_on_error:
                                return False
                            continue

                        add_line(f"• Making script executable...")  # Always show progress
                        success, cmd_output = self.exec_container_command_streaming(
                            node_name, vmid, f"chmod +x {script_path}",
                            verbose=False
                        )
                        if not success:
                            output.error(f"Failed to make script executable: {cmd_output}")
                            if not script.continue_on_error:
                                return False
                            continue

                        add_line(f"• Executing script...")  # Always show progress
                        # Change to working directory and execute
                        exec_cmd = f"cd {script.working_dir} && {script_path}"
                        if script.environment:
                            env_vars = " ".join([f"{k}={v}" for k, v in script.environment.items()])
                            exec_cmd = f"env {env_vars} {exec_cmd}"

                        success, cmd_output = self.exec_container_command_streaming(
                            node_name, vmid, exec_cmd,
                            verbose=verbose, add_line_func=add_line  # Always stream to display
                        )
                        if not success:
                            output.error(f"Script execution failed: {cmd_output}")
                            if not script.continue_on_error:
                                return False
                        else:
                            output.success(f"[{current_step}/{total_steps}] Script {script.name} completed")

                        # Clean up script file
                        self.exec_container_command_streaming(node_name, vmid, f"rm -f {script_path}")

            return True

        except Exception as e:
            output.error(f"Provisioning failed: {e}")
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