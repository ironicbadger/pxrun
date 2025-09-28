"""Provisioning configuration models for post-creation setup."""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class ProvisioningScript:
    """Individual provisioning command or script.

    Attributes:
        name: Script identifier
        interpreter: Script interpreter (bash, sh, python)
        content: Script content
        run_as: User to run as (default: root)
        working_dir: Working directory
        environment: Environment variables
        timeout: Timeout in seconds (default: 300)
        continue_on_error: Continue if script fails
    """

    name: str
    content: str
    interpreter: str = "bash"
    run_as: str = "root"
    working_dir: str = "/root"
    environment: Dict[str, str] = field(default_factory=dict)
    timeout: int = 300
    continue_on_error: bool = False

    def __post_init__(self):
        """Validate script configuration after initialization."""
        self.validate()

    def validate(self):
        """Validate provisioning script configuration.

        Raises:
            ValueError: If any validation rule is violated
        """
        # Validate required fields
        if not self.name:
            raise ValueError("Script name is required")

        if not self.content:
            raise ValueError("Script content is required")

        # Validate interpreter
        valid_interpreters = ["bash", "sh", "python", "python3", "perl", "ruby"]
        if self.interpreter not in valid_interpreters:
            raise ValueError(f"Invalid interpreter: {self.interpreter}. Must be one of {valid_interpreters}")

        # Validate timeout
        if self.timeout <= 0:
            raise ValueError(f"Timeout must be positive: {self.timeout}")

        if self.timeout > 3600:
            raise ValueError(f"Timeout too large (max 3600 seconds): {self.timeout}")

        # Validate working directory
        if not self.working_dir.startswith("/"):
            raise ValueError(f"Working directory must be absolute path: {self.working_dir}")

    def get_command(self) -> str:
        """Get the full command to execute the script.

        Returns:
            Command string to execute
        """
        # Build the command based on interpreter
        if self.interpreter in ["bash", "sh"]:
            # Use heredoc for shell scripts
            return f"{self.interpreter} -c '{self.content}'"
        elif self.interpreter.startswith("python"):
            # Use -c for Python scripts
            return f"{self.interpreter} -c '{self.content}'"
        else:
            # For other interpreters, write to temp file first
            return f"echo '{self.content}' | {self.interpreter}"

    def get_ssh_command(self) -> str:
        """Get SSH command to execute the script remotely.

        Returns:
            SSH command string
        """
        cmd = self.get_command()

        # Add user prefix if not root
        if self.run_as != "root":
            cmd = f"su - {self.run_as} -c '{cmd}'"

        # Add working directory
        if self.working_dir and self.working_dir != "/root":
            cmd = f"cd {self.working_dir} && {cmd}"

        # Add environment variables
        if self.environment:
            env_vars = " ".join(f"{k}={v}" for k, v in self.environment.items())
            cmd = f"{env_vars} {cmd}"

        return cmd

    def to_dict(self) -> dict:
        """Convert script to dictionary representation.

        Returns:
            Dictionary representation
        """
        return {
            'name': self.name,
            'interpreter': self.interpreter,
            'content': self.content,
            'run_as': self.run_as,
            'working_dir': self.working_dir,
            'environment': self.environment,
            'timeout': self.timeout,
            'continue_on_error': self.continue_on_error
        }


@dataclass
class ProvisioningConfig:
    """Post-creation setup configuration.

    Attributes:
        scripts: Scripts to execute
        packages: System packages to install
        docker: Install Docker (default: False)
        tailscale: Tailscale setup configuration
        ssh_keys: SSH public keys to add
        users: Additional users to create
    """

    scripts: List[ProvisioningScript] = field(default_factory=list)
    packages: List[str] = field(default_factory=list)
    docker: bool = False
    tailscale: Optional[Any] = None  # TailscaleConfig
    ssh_keys: List[str] = field(default_factory=list)
    users: List[Any] = field(default_factory=list)  # List[UserConfig]

    def __post_init__(self):
        """Validate provisioning configuration after initialization."""
        self.validate()

    def validate(self):
        """Validate provisioning configuration.

        Raises:
            ValueError: If any validation rule is violated
        """
        # Validate SSH keys format
        for key in self.ssh_keys:
            if not self._is_valid_ssh_key(key):
                raise ValueError(f"Invalid SSH key format: {key[:50]}...")

        # Validate package names
        for package in self.packages:
            if not self._is_valid_package_name(package):
                raise ValueError(f"Invalid package name: {package}")

    def _is_valid_ssh_key(self, key: str) -> bool:
        """Check if SSH key is in valid format.

        Args:
            key: SSH public key string

        Returns:
            True if valid SSH key, False otherwise
        """
        # Basic validation - should start with ssh type
        valid_prefixes = ["ssh-rsa", "ssh-dss", "ssh-ed25519", "ecdsa-sha2-nistp"]
        return any(key.strip().startswith(prefix) for prefix in valid_prefixes)

    def _is_valid_package_name(self, package: str) -> bool:
        """Check if package name is valid.

        Args:
            package: Package name to validate

        Returns:
            True if valid package name, False otherwise
        """
        # Basic validation - alphanumeric, dash, underscore, plus, dot
        import re
        pattern = r'^[a-zA-Z0-9\-_+.]+$'
        return bool(re.match(pattern, package))

    def get_setup_script(self) -> str:
        """Generate a complete setup script for all provisioning.

        Returns:
            Bash script content for all provisioning steps
        """
        script_lines = ["#!/bin/bash", "set -e", ""]

        # Update package lists
        script_lines.append("echo 'Updating package lists...'")
        script_lines.append("apt-get update")
        script_lines.append("")

        # Install packages
        if self.packages:
            script_lines.append("echo 'Installing packages...'")
            packages_str = " ".join(self.packages)
            script_lines.append(f"DEBIAN_FRONTEND=noninteractive apt-get install -y {packages_str}")
            script_lines.append("")

        # Install Docker if requested
        if self.docker:
            script_lines.append("echo 'Installing Docker...'")
            script_lines.extend([
                "curl -fsSL https://get.docker.com | sh",
                "systemctl enable docker",
                "systemctl start docker",
                ""
            ])

        # Add SSH keys
        if self.ssh_keys:
            script_lines.append("echo 'Adding SSH keys...'")
            script_lines.append("mkdir -p /root/.ssh")
            script_lines.append("chmod 700 /root/.ssh")
            for key in self.ssh_keys:
                script_lines.append(f"echo '{key}' >> /root/.ssh/authorized_keys")
            script_lines.append("chmod 600 /root/.ssh/authorized_keys")
            script_lines.append("")

        return "\n".join(script_lines)

    def get_install_packages_command(self) -> Optional[str]:
        """Get command to install all packages.

        Returns:
            Command string or None if no packages
        """
        if not self.packages:
            return None

        packages_str = " ".join(self.packages)
        return f"DEBIAN_FRONTEND=noninteractive apt-get update && apt-get install -y {packages_str}"

    def get_docker_install_script(self) -> str:
        """Get Docker installation script.

        Returns:
            Script content for Docker installation
        """
        return """#!/bin/bash
set -e

# Install Docker using official script
curl -fsSL https://get.docker.com | sh

# Enable and start Docker
systemctl enable docker
systemctl start docker

# Add default user to docker group if exists
if id -u 1000 >/dev/null 2>&1; then
    usermod -aG docker $(id -un 1000)
fi

echo "Docker installation complete"
"""

    def has_provisioning(self) -> bool:
        """Check if any provisioning is configured.

        Returns:
            True if provisioning is needed, False otherwise
        """
        return bool(
            self.scripts or
            self.packages or
            self.docker or
            self.tailscale or
            self.ssh_keys or
            self.users
        )

    @classmethod
    def from_yaml(cls, data: dict) -> 'ProvisioningConfig':
        """Create ProvisioningConfig from YAML data.

        Args:
            data: YAML provisioning section

        Returns:
            ProvisioningConfig instance
        """
        config = cls()

        # Parse packages
        config.packages = data.get('packages', [])

        # Parse docker flag
        config.docker = data.get('docker', False)

        # Parse SSH keys
        config.ssh_keys = data.get('ssh_keys', [])

        # Parse scripts
        scripts_data = data.get('scripts', [])
        for script_data in scripts_data:
            if isinstance(script_data, dict):
                script = ProvisioningScript(
                    name=script_data.get('name', 'unnamed'),
                    content=script_data.get('content', ''),
                    interpreter=script_data.get('interpreter', 'bash'),
                    run_as=script_data.get('run_as', 'root'),
                    working_dir=script_data.get('working_dir', '/root'),
                    environment=script_data.get('environment', {}),
                    timeout=script_data.get('timeout', 300),
                    continue_on_error=script_data.get('continue_on_error', False)
                )
                config.scripts.append(script)

        return config

    def to_dict(self) -> dict:
        """Convert provisioning config to dictionary representation.

        Returns:
            Dictionary representation
        """
        return {
            'scripts': [s.to_dict() for s in self.scripts],
            'packages': self.packages,
            'docker': self.docker,
            'ssh_keys': self.ssh_keys,
            'has_provisioning': self.has_provisioning()
        }