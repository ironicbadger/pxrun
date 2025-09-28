"""SSH provisioner for container post-creation setup."""

import logging
import os
import time
from typing import Optional, List, Tuple, Any
from dataclasses import dataclass

import paramiko
from paramiko import SSHClient, AutoAddPolicy
from paramiko.ssh_exception import SSHException, AuthenticationException

from src.models.provisioning import ProvisioningConfig, ProvisioningScript
from src.models.tailscale import TailscaleConfig
from src.models.user import UserConfig

logger = logging.getLogger(__name__)


@dataclass
class SSHConfig:
    """SSH connection configuration."""

    host: str
    port: int = 22
    username: str = "root"
    password: Optional[str] = None
    key_filename: Optional[str] = None
    timeout: int = 30
    retry_attempts: int = 10
    retry_delay: int = 3


class SSHProvisioner:
    """Service for provisioning containers via SSH."""

    def __init__(self, ssh_config: SSHConfig, container_name: Optional[str] = None):
        """Initialize SSH provisioner.

        Args:
            ssh_config: SSH connection configuration
            container_name: Optional container name for context
        """
        self.config = ssh_config
        self._client: Optional[SSHClient] = None
        self.container_name = container_name

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()

    def connect(self, wait_for_ssh: bool = True) -> bool:
        """Connect to container via SSH.

        Args:
            wait_for_ssh: Wait for SSH service to be available

        Returns:
            True if connected successfully
        """
        if wait_for_ssh:
            if not self._wait_for_ssh():
                return False

        try:
            self._client = SSHClient()
            self._client.set_missing_host_key_policy(AutoAddPolicy())

            connect_kwargs = {
                'hostname': self.config.host,
                'port': self.config.port,
                'username': self.config.username,
                'timeout': self.config.timeout
            }

            if self.config.password:
                connect_kwargs['password'] = self.config.password
            elif self.config.key_filename:
                connect_kwargs['key_filename'] = self.config.key_filename
            else:
                # Try to use system SSH keys
                connect_kwargs['look_for_keys'] = True

            self._client.connect(**connect_kwargs)
            logger.info(f"Connected to {self.config.host}:{self.config.port}")
            return True

        except AuthenticationException:
            logger.error("Authentication failed")
            return False
        except SSHException as e:
            logger.error(f"SSH connection failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False

    def disconnect(self):
        """Disconnect SSH client."""
        if self._client:
            try:
                self._client.close()
                logger.info("SSH connection closed")
            except:
                pass
            self._client = None

    def _wait_for_ssh(self) -> bool:
        """Wait for SSH service to become available.

        Returns:
            True if SSH is available, False if timeout
        """
        logger.info(f"Waiting for SSH on {self.config.host}:{self.config.port}...")

        for attempt in range(self.config.retry_attempts):
            try:
                test_client = SSHClient()
                test_client.set_missing_host_key_policy(AutoAddPolicy())

                test_client.connect(
                    hostname=self.config.host,
                    port=self.config.port,
                    username=self.config.username,
                    password=self.config.password,
                    key_filename=self.config.key_filename,
                    timeout=5,
                    look_for_keys=not (self.config.password or self.config.key_filename)
                )
                test_client.close()
                logger.info("SSH service is available")
                return True

            except Exception as e:
                if attempt < self.config.retry_attempts - 1:
                    logger.debug(f"SSH not ready (attempt {attempt + 1}/{self.config.retry_attempts}): {e}")
                    time.sleep(self.config.retry_delay)
                else:
                    logger.error(f"SSH service not available after {self.config.retry_attempts} attempts")
                    return False

        return False

    def execute_command(self, command: str, timeout: int = 300) -> Tuple[int, str, str]:
        """Execute a command via SSH.

        Args:
            command: Command to execute
            timeout: Command timeout in seconds

        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        if not self._client:
            raise RuntimeError("Not connected to SSH")

        try:
            stdin, stdout, stderr = self._client.exec_command(
                command,
                timeout=timeout
            )

            # Wait for command to complete
            exit_code = stdout.channel.recv_exit_status()

            # Read output
            stdout_data = stdout.read().decode('utf-8')
            stderr_data = stderr.read().decode('utf-8')

            return exit_code, stdout_data, stderr_data

        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return 1, "", str(e)

    def execute_script(self, script: ProvisioningScript) -> bool:
        """Execute a provisioning script.

        Args:
            script: ProvisioningScript to execute

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Executing script: {script.name}")

        # Get the SSH command
        command = script.get_ssh_command()

        # Execute with specified timeout
        exit_code, stdout, stderr = self.execute_command(
            command,
            timeout=script.timeout
        )

        if exit_code == 0:
            logger.info(f"Script {script.name} completed successfully")
            if stdout:
                logger.debug(f"Output: {stdout}")
            return True
        else:
            logger.error(f"Script {script.name} failed with exit code {exit_code}")
            if stderr:
                logger.error(f"Error: {stderr}")
            if stdout:
                logger.debug(f"Output: {stdout}")

            # Check if we should continue on error
            return script.continue_on_error

    def provision(self, config: ProvisioningConfig) -> bool:
        """Run complete provisioning based on config.

        Args:
            config: ProvisioningConfig with all provisioning steps

        Returns:
            True if all provisioning succeeded
        """
        if not self._client:
            if not self.connect():
                logger.error("Failed to connect for provisioning")
                return False

        success = True

        # Always detect OS type and configure locales for Debian/Ubuntu
        os_type = self._detect_os_type()
        
        # Configure locales first (for Debian/Ubuntu systems) - always do this
        if os_type in ['debian', 'ubuntu']:
            logger.info("Configuring locales...")
            self._setup_locales()

        # If no other provisioning is configured, we're done
        if not config.has_provisioning():
            logger.info("No additional provisioning configured")
            return True

        # Update package lists first
        logger.info("Updating package lists...")
        exit_code, _, _ = self.execute_command("apt update", timeout=60)
        if exit_code != 0:
            logger.warning("Failed to update package lists")

        # Install packages
        if config.packages:
            logger.info(f"Installing packages: {', '.join(config.packages)}")
            cmd = config.get_install_packages_command()
            if cmd:
                exit_code, stdout, stderr = self.execute_command(cmd, timeout=300)
                if exit_code != 0:
                    logger.error(f"Package installation failed: {stderr}")
                    success = False

        # Install Docker if requested
        if config.docker:
            logger.info("Installing Docker...")
            docker_script = ProvisioningScript(
                name="docker-install",
                content=config.get_docker_install_script(),
                interpreter="bash",
                timeout=600
            )
            if not self.execute_script(docker_script):
                logger.error("Docker installation failed")
                success = False

        # Configure Tailscale if requested
        if config.tailscale:
            logger.info("Installing and configuring Tailscale...")
            if not self.setup_tailscale(config.tailscale):
                logger.error("Tailscale setup failed")
                success = False

        # Add SSH keys
        if config.ssh_keys:
            logger.info("Adding SSH keys...")
            if not self.add_ssh_keys(config.ssh_keys):
                logger.error("Failed to add SSH keys")
                success = False

        # Create users
        if config.users:
            for user_config in config.users:
                logger.info(f"Creating user: {user_config.username}")
                if not self.create_user(user_config):
                    logger.error(f"Failed to create user: {user_config.username}")
                    success = False

        # Execute custom scripts
        for script in config.scripts:
            if not self.execute_script(script):
                logger.error(f"Script {script.name} failed")
                if not script.continue_on_error:
                    success = False
                    break

        return success

    def setup_tailscale(self, tailscale: TailscaleConfig) -> bool:
        """Install and configure Tailscale.

        Args:
            tailscale: TailscaleConfig with settings

        Returns:
            True if successful
        """
        # Try to get or generate an auth key if needed
        from src.services.tailscale import TailscaleProvisioningService
        
        # Always try to use a fresh auth key if we have API credentials
        try:
            provisioning_service = TailscaleProvisioningService()
            container_name = getattr(self, 'container_name', None) or tailscale.hostname
            
            # Try to generate a fresh key (will use API if available), respecting ephemeral setting
            auth_key = provisioning_service.get_or_generate_auth_key(container_name, ephemeral=tailscale.ephemeral)
            
            # Create a modified config with the fresh key
            tailscale = TailscaleConfig(
                auth_key=auth_key,
                hostname=tailscale.hostname,
                ephemeral=tailscale.ephemeral,
                accept_routes=tailscale.accept_routes,
                advertise_routes=tailscale.advertise_routes,
                shields_up=tailscale.shields_up
            )
            logger.info("Using fresh auth key for Tailscale setup")
        except Exception as e:
            # Fall back to original config if generation fails
            logger.warning(f"Could not get/generate auth key, using original config: {e}")
            # The original config might have ${TAILSCALE_AUTH_KEY} which will be resolved in the script
        
        # Create installation script
        install_script = ProvisioningScript(
            name="tailscale-setup",
            content=tailscale.get_install_script(),
            interpreter="bash",
            timeout=600
        )

        return self.execute_script(install_script)

    def create_user(self, user: UserConfig) -> bool:
        """Create a user account.

        Args:
            user: UserConfig with user settings

        Returns:
            True if successful
        """
        # Create user setup script
        setup_script = ProvisioningScript(
            name=f"create-user-{user.username}",
            content=user.get_setup_script(),
            interpreter="bash",
            timeout=60
        )

        return self.execute_script(setup_script)

    def add_ssh_keys(self, keys: List[str], username: str = "root") -> bool:
        """Add SSH public keys for a user.

        Args:
            keys: List of SSH public keys
            username: Target user (default: root)

        Returns:
            True if successful
        """
        if username == "root":
            ssh_dir = "/root/.ssh"
        else:
            ssh_dir = f"/home/{username}/.ssh"

        commands = [
            f"mkdir -p {ssh_dir}",
            f"touch {ssh_dir}/authorized_keys",
            f"chmod 700 {ssh_dir}",
            f"chmod 600 {ssh_dir}/authorized_keys"
        ]

        # Add each key
        for key in keys:
            # Escape single quotes in the key
            escaped_key = key.replace("'", "'\"'\"'")
            commands.append(f"echo '{escaped_key}' >> {ssh_dir}/authorized_keys")

        # Set ownership
        if username != "root":
            commands.append(f"chown -R {username}:{username} {ssh_dir}")

        # Execute all commands
        full_command = " && ".join(commands)
        exit_code, _, stderr = self.execute_command(full_command)

        if exit_code != 0:
            logger.error(f"Failed to add SSH keys: {stderr}")
            return False

        logger.info(f"Added {len(keys)} SSH key(s) for {username}")
        return True

    def upload_file(self, local_path: str, remote_path: str) -> bool:
        """Upload a file to the container.

        Args:
            local_path: Local file path
            remote_path: Remote file path

        Returns:
            True if successful
        """
        if not self._client:
            raise RuntimeError("Not connected to SSH")

        try:
            sftp = self._client.open_sftp()
            sftp.put(local_path, remote_path)
            sftp.close()
            logger.info(f"Uploaded {local_path} to {remote_path}")
            return True
        except Exception as e:
            logger.error(f"File upload failed: {e}")
            return False

    def download_file(self, remote_path: str, local_path: str) -> bool:
        """Download a file from the container.

        Args:
            remote_path: Remote file path
            local_path: Local file path

        Returns:
            True if successful
        """
        if not self._client:
            raise RuntimeError("Not connected to SSH")

        try:
            sftp = self._client.open_sftp()
            sftp.get(remote_path, local_path)
            sftp.close()
            logger.info(f"Downloaded {remote_path} to {local_path}")
            return True
        except Exception as e:
            logger.error(f"File download failed: {e}")
            return False

    def _detect_os_type(self) -> str:
        """Detect the operating system type of the container.

        Returns:
            OS type string: 'debian', 'ubuntu', 'alpine', 'centos', 'rocky', or 'unknown'
        """
        # Try to read /etc/os-release (works for most modern Linux distros)
        exit_code, stdout, _ = self.execute_command("cat /etc/os-release 2>/dev/null")
        
        if exit_code == 0 and stdout:
            stdout_lower = stdout.lower()
            if 'debian' in stdout_lower:
                return 'debian'
            elif 'ubuntu' in stdout_lower:
                return 'ubuntu'
            elif 'alpine' in stdout_lower:
                return 'alpine'
            elif 'centos' in stdout_lower:
                return 'centos'
            elif 'rocky' in stdout_lower:
                return 'rocky'
            elif 'rhel' in stdout_lower or 'red hat' in stdout_lower:
                return 'rhel'
        
        # Fallback: check for package manager
        exit_code, _, _ = self.execute_command("which apt 2>/dev/null")
        if exit_code == 0:
            return 'debian'  # Could be Debian or Ubuntu
        
        exit_code, _, _ = self.execute_command("which apk 2>/dev/null")
        if exit_code == 0:
            return 'alpine'
        
        exit_code, _, _ = self.execute_command("which yum 2>/dev/null")
        if exit_code == 0:
            return 'centos'  # Could be CentOS, RHEL, Rocky
        
        return 'unknown'

    def _setup_locales(self) -> bool:
        """Configure locales for Debian/Ubuntu systems to prevent SSH locale warnings.

        Returns:
            True if successful, False otherwise
        """
        logger.info("Setting up locales for en_US.UTF-8...")
        
        # Commands to set up locales on Debian/Ubuntu
        locale_commands = [
            # Install locales package if not present
            "apt update && apt install -y locales 2>/dev/null || true",
            
            # Generate en_US.UTF-8 locale
            "locale-gen en_US.UTF-8",
            
            # Update locale settings
            "update-locale LANG=en_US.UTF-8",
            
            # Also set LC_ALL to avoid any remaining warnings
            "update-locale LC_ALL=en_US.UTF-8",
            
            # Make the changes effective for current session
            "export LANG=en_US.UTF-8",
            "export LC_ALL=en_US.UTF-8"
        ]
        
        # Execute locale setup commands
        for cmd in locale_commands:
            exit_code, stdout, stderr = self.execute_command(cmd, timeout=60)
            if exit_code != 0 and "locale-gen" in cmd:
                # locale-gen might fail if locales are already configured
                logger.warning(f"Locale command had non-zero exit: {cmd}")
                # Continue anyway as this might not be critical
        
        # Verify locale is set correctly
        exit_code, stdout, _ = self.execute_command("locale")
        if exit_code == 0:
            if "en_US.UTF-8" in stdout:
                logger.info("Locales configured successfully")
                return True
            else:
                logger.warning("Locales may not be fully configured")
        
        return True  # Don't fail provisioning if locale setup has issues