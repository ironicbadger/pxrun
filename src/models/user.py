"""User configuration model for additional user accounts."""

from dataclasses import dataclass, field
from typing import List, Optional
import re


@dataclass
class UserConfig:
    """Additional user account configuration.

    Attributes:
        username: Linux username
        uid: User ID (optional)
        gid: Group ID (optional)
        groups: Additional groups
        shell: Login shell (default: /bin/bash)
        home: Home directory
        ssh_keys: SSH public keys
    """

    username: str
    uid: Optional[int] = None
    gid: Optional[int] = None
    groups: List[str] = field(default_factory=list)
    shell: str = "/bin/bash"
    home: Optional[str] = None
    ssh_keys: List[str] = field(default_factory=list)
    password: Optional[str] = None  # Should be hashed

    def __post_init__(self):
        """Set defaults and validate after initialization."""
        # Set default home directory if not provided
        if not self.home:
            self.home = f"/home/{self.username}"
        self.validate()

    def validate(self):
        """Validate user configuration.

        Raises:
            ValueError: If any validation rule is violated
        """
        # Validate username
        if not self._is_valid_username(self.username):
            raise ValueError(f"Invalid Linux username: {self.username}")

        # Validate UID if provided
        if self.uid is not None:
            if not (1000 <= self.uid <= 65535):
                raise ValueError(f"UID should be between 1000 and 65535: {self.uid}")

        # Validate GID if provided
        if self.gid is not None:
            if not (1000 <= self.gid <= 65535):
                raise ValueError(f"GID should be between 1000 and 65535: {self.gid}")

        # Validate shell
        valid_shells = [
            "/bin/bash", "/bin/sh", "/bin/zsh", "/bin/fish",
            "/usr/bin/bash", "/usr/bin/sh", "/usr/bin/zsh", "/usr/bin/fish",
            "/bin/false", "/usr/sbin/nologin"
        ]
        if self.shell not in valid_shells:
            raise ValueError(f"Invalid shell: {self.shell}")

        # Validate home directory
        if not self.home.startswith("/"):
            raise ValueError(f"Home directory must be absolute path: {self.home}")

        # Validate groups
        for group in self.groups:
            if not self._is_valid_group_name(group):
                raise ValueError(f"Invalid group name: {group}")

        # Validate SSH keys
        for key in self.ssh_keys:
            if not self._is_valid_ssh_key(key):
                raise ValueError(f"Invalid SSH key format: {key[:50]}...")

    def _is_valid_username(self, username: str) -> bool:
        """Check if username is valid Linux username.

        Args:
            username: Username to validate

        Returns:
            True if valid, False otherwise
        """
        # Linux username rules:
        # - Start with lowercase letter
        # - Contain lowercase letters, digits, dash, underscore
        # - Max 32 characters
        if len(username) > 32:
            return False
        pattern = r'^[a-z][a-z0-9_-]*$'
        return bool(re.match(pattern, username))

    def _is_valid_group_name(self, group: str) -> bool:
        """Check if group name is valid.

        Args:
            group: Group name to validate

        Returns:
            True if valid, False otherwise
        """
        # Similar rules to username
        if len(group) > 32:
            return False
        pattern = r'^[a-z][a-z0-9_-]*$'
        return bool(re.match(pattern, group))

    def _is_valid_ssh_key(self, key: str) -> bool:
        """Check if SSH key is in valid format.

        Args:
            key: SSH public key string

        Returns:
            True if valid SSH key, False otherwise
        """
        valid_prefixes = ["ssh-rsa", "ssh-dss", "ssh-ed25519", "ecdsa-sha2-nistp"]
        return any(key.strip().startswith(prefix) for prefix in valid_prefixes)

    def get_useradd_command(self) -> str:
        """Generate useradd command to create the user.

        Returns:
            Complete useradd command
        """
        cmd_parts = ["useradd"]

        # Add UID if specified
        if self.uid is not None:
            cmd_parts.extend(["-u", str(self.uid)])

        # Add GID if specified
        if self.gid is not None:
            cmd_parts.extend(["-g", str(self.gid)])

        # Add groups
        if self.groups:
            groups_str = ",".join(self.groups)
            cmd_parts.extend(["-G", groups_str])

        # Add shell
        cmd_parts.extend(["-s", self.shell])

        # Add home directory
        cmd_parts.extend(["-m", "-d", self.home])

        # Add username
        cmd_parts.append(self.username)

        return " ".join(cmd_parts)

    def get_setup_script(self) -> str:
        """Generate complete setup script for user creation.

        Returns:
            Bash script for creating and configuring user
        """
        script_lines = [
            "#!/bin/bash",
            "set -e",
            "",
            f"echo 'Creating user {self.username}...'",
            ""
        ]

        # Check if user already exists
        script_lines.append(f"if id {self.username} &>/dev/null; then")
        script_lines.append(f"    echo 'User {self.username} already exists'")
        script_lines.append("else")

        # Create user
        script_lines.append(f"    {self.get_useradd_command()}")

        # Set password if provided (should be hashed)
        if self.password:
            script_lines.append(f"    echo '{self.username}:{self.password}' | chpasswd")

        script_lines.append("fi")
        script_lines.append("")

        # Ensure groups exist and add user to them
        if self.groups:
            script_lines.append("# Ensure groups exist")
            for group in self.groups:
                script_lines.append(f"getent group {group} || groupadd {group}")
                script_lines.append(f"usermod -a -G {group} {self.username}")
            script_lines.append("")

        # Setup SSH keys if provided
        if self.ssh_keys:
            script_lines.append("# Setup SSH keys")
            script_lines.append(f"mkdir -p {self.home}/.ssh")
            script_lines.append(f"touch {self.home}/.ssh/authorized_keys")

            for key in self.ssh_keys:
                script_lines.append(f"echo '{key}' >> {self.home}/.ssh/authorized_keys")

            script_lines.append(f"chmod 700 {self.home}/.ssh")
            script_lines.append(f"chmod 600 {self.home}/.ssh/authorized_keys")
            script_lines.append(f"chown -R {self.username}:{self.username} {self.home}/.ssh")
            script_lines.append("")

        # Create basic shell configuration
        script_lines.append("# Create basic shell configuration")
        if self.shell.endswith("bash"):
            script_lines.append(f"touch {self.home}/.bashrc")
            script_lines.append(f"touch {self.home}/.profile")
        elif self.shell.endswith("zsh"):
            script_lines.append(f"touch {self.home}/.zshrc")

        script_lines.append(f"chown -R {self.username}:{self.username} {self.home}")
        script_lines.append("")
        script_lines.append(f"echo 'User {self.username} setup complete'")

        return "\n".join(script_lines)

    def get_sudo_config(self, no_password: bool = False) -> str:
        """Generate sudoers configuration for the user.

        Args:
            no_password: Allow sudo without password

        Returns:
            Sudoers configuration line
        """
        if no_password:
            return f"{self.username} ALL=(ALL) NOPASSWD:ALL"
        else:
            return f"{self.username} ALL=(ALL) ALL"

    @classmethod
    def from_yaml(cls, data: dict) -> 'UserConfig':
        """Create UserConfig from YAML data.

        Args:
            data: YAML user configuration

        Returns:
            UserConfig instance
        """
        return cls(
            username=data.get('username', ''),
            uid=data.get('uid'),
            gid=data.get('gid'),
            groups=data.get('groups', []),
            shell=data.get('shell', '/bin/bash'),
            home=data.get('home'),
            ssh_keys=data.get('ssh_keys', []),
            password=data.get('password')
        )

    def to_dict(self) -> dict:
        """Convert user config to dictionary representation.

        Returns:
            Dictionary representation (password masked)
        """
        return {
            'username': self.username,
            'uid': self.uid,
            'gid': self.gid,
            'groups': self.groups,
            'shell': self.shell,
            'home': self.home,
            'ssh_keys_count': len(self.ssh_keys),
            'has_password': bool(self.password)
        }