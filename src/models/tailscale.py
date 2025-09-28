"""Tailscale VPN configuration model."""

from dataclasses import dataclass, field
from typing import List, Optional
import re


@dataclass
class TailscaleConfig:
    """Tailscale VPN configuration.

    Attributes:
        auth_key: Authentication key (encrypted)
        hostname: Tailscale hostname (optional)
        ephemeral: Whether the node should be ephemeral (removed on disconnect)
        accept_routes: Accept advertised routes
        advertise_routes: Routes to advertise
        shields_up: Block incoming connections
    """

    auth_key: str
    hostname: Optional[str] = None
    ephemeral: bool = False  # Default to persistent for containers
    accept_routes: bool = False
    advertise_routes: List[str] = field(default_factory=list)
    shields_up: bool = False

    def __post_init__(self):
        """Validate Tailscale configuration after initialization."""
        self.validate()

    def validate(self):
        """Validate Tailscale configuration.

        Raises:
            ValueError: If any validation rule is violated
        """
        # Validate auth key is provided
        if not self.auth_key:
            raise ValueError("Tailscale auth key is required")

        # Validate auth key format (basic check)
        if not self._is_valid_auth_key(self.auth_key):
            raise ValueError("Invalid Tailscale auth key format")

        # Validate hostname if provided
        if self.hostname and not self._is_valid_hostname(self.hostname):
            raise ValueError(f"Invalid Tailscale hostname: {self.hostname}")

        # Validate advertised routes
        for route in self.advertise_routes:
            if not self._is_valid_cidr(route):
                raise ValueError(f"Invalid CIDR notation for route: {route}")

    def _is_valid_auth_key(self, key: str) -> bool:
        """Check if auth key appears valid.

        Args:
            key: Authentication key to validate

        Returns:
            True if appears valid, False otherwise
        """
        # Basic validation - should be non-empty and start with expected prefix
        # Real Tailscale keys start with "tskey-"
        # Also accept environment variable references like ${TAILSCALE_AUTH_KEY}
        if key.startswith("${") and key.endswith("}"):
            return True
        if key.startswith("tskey-"):
            # Check basic format: tskey-[hex chars]-[hex chars]
            parts = key.split("-")
            if len(parts) >= 3:
                return True
        return False

    def _is_valid_hostname(self, hostname: str) -> bool:
        """Check if hostname is valid for Tailscale.

        Args:
            hostname: Hostname to validate

        Returns:
            True if valid, False otherwise
        """
        # Tailscale hostnames: alphanumeric and dash, max 63 chars
        if len(hostname) > 63:
            return False
        pattern = r'^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$'
        return bool(re.match(pattern, hostname.lower()))

    def _is_valid_cidr(self, cidr: str) -> bool:
        """Check if route is in valid CIDR notation.

        Args:
            cidr: IP address range in CIDR format

        Returns:
            True if valid CIDR, False otherwise
        """
        try:
            parts = cidr.split('/')
            if len(parts) != 2:
                return False

            # Check IP part
            ip_parts = parts[0].split('.')
            if len(ip_parts) != 4:
                return False
            for octet in ip_parts:
                num = int(octet)
                if not (0 <= num <= 255):
                    return False

            # Check mask part
            mask = int(parts[1])
            if not (0 <= mask <= 32):
                return False

            return True
        except (ValueError, AttributeError):
            return False

    def get_install_script(self) -> str:
        """Generate Tailscale installation script.

        Returns:
            Bash script for installing and configuring Tailscale
        """
        script_lines = [
            "#!/bin/bash",
            "set -e",
            "",
            "echo 'Installing Tailscale...'",
            "",
            "# Add Tailscale repository",
            "curl -fsSL https://pkgs.tailscale.com/stable/debian/bookworm.noarmor.gpg | tee /usr/share/keyrings/tailscale-archive-keyring.gpg >/dev/null",
            "curl -fsSL https://pkgs.tailscale.com/stable/debian/bookworm.tailscale-keyring.list | tee /etc/apt/sources.list.d/tailscale.list",
            "",
            "# Install Tailscale",
            "apt-get update",
            "apt-get install -y tailscale",
            "",
            "# Start Tailscale daemon",
            "systemctl enable tailscaled",
            "systemctl start tailscaled",
            "",
            "# Configure and authenticate",
            "echo 'Configuring Tailscale...'",
        ]

        # Build up command
        up_cmd = "tailscale up --authkey=$TAILSCALE_AUTH_KEY"

        if self.hostname:
            up_cmd += f" --hostname={self.hostname}"

        if self.accept_routes:
            up_cmd += " --accept-routes"

        if self.advertise_routes:
            routes = ",".join(self.advertise_routes)
            up_cmd += f" --advertise-routes={routes}"

        if self.shields_up:
            up_cmd += " --shields-up"

        # Handle auth key (could be env var reference)
        if self.auth_key.startswith("${") and self.auth_key.endswith("}"):
            # It's an environment variable reference
            env_var = self.auth_key[2:-1]
            script_lines.append(f"TAILSCALE_AUTH_KEY=\"${env_var}\"")
        else:
            # Direct key (should be encrypted/secure in real usage)
            script_lines.append(f"TAILSCALE_AUTH_KEY=\"{self.auth_key}\"")

        script_lines.append(up_cmd)
        script_lines.append("")
        script_lines.append("echo 'Tailscale installation complete'")
        script_lines.append("tailscale status")

        return "\n".join(script_lines)

    def get_up_command(self, auth_key: Optional[str] = None) -> str:
        """Get tailscale up command with all parameters.

        Args:
            auth_key: Override auth key (for security)

        Returns:
            Complete tailscale up command
        """
        key = auth_key or self.auth_key
        cmd_parts = ["tailscale", "up", f"--authkey={key}"]

        if self.hostname:
            cmd_parts.append(f"--hostname={self.hostname}")

        if self.accept_routes:
            cmd_parts.append("--accept-routes")

        if self.advertise_routes:
            routes = ",".join(self.advertise_routes)
            cmd_parts.append(f"--advertise-routes={routes}")

        if self.shields_up:
            cmd_parts.append("--shields-up")

        return " ".join(cmd_parts)

    @classmethod
    def from_yaml(cls, data: dict) -> 'TailscaleConfig':
        """Create TailscaleConfig from YAML data.

        Args:
            data: YAML tailscale section

        Returns:
            TailscaleConfig instance
        """
        # If just 'true' or has 'provision: true', enable with auto-generated key
        if data is True or (isinstance(data, dict) and data.get('provision') is True):
            # Use placeholder that will trigger auto-generation
            auth_key = data.get('auth_key', '${TAILSCALE_AUTH_KEY}') if isinstance(data, dict) else '${TAILSCALE_AUTH_KEY}'
        else:
            # Standard parsing
            auth_key = data.get('auth_key', '${TAILSCALE_AUTH_KEY}')
        
        return cls(
            auth_key=auth_key,
            hostname=data.get('hostname') if isinstance(data, dict) else None,
            ephemeral=data.get('ephemeral', False) if isinstance(data, dict) else False,  # Default to persistent
            accept_routes=data.get('accept_routes', False) if isinstance(data, dict) else False,
            advertise_routes=data.get('advertise_routes', []) if isinstance(data, dict) else [],
            shields_up=data.get('shields_up', False) if isinstance(data, dict) else False
        )

    def to_dict(self) -> dict:
        """Convert config to dictionary representation.

        Returns:
            Dictionary representation (auth key masked)
        """
        # Mask auth key for security
        masked_key = self.auth_key
        if self.auth_key and not self.auth_key.startswith("${"):
            # Mask the actual key but keep format visible
            if self.auth_key.startswith("tskey-"):
                parts = self.auth_key.split("-")
                if len(parts) >= 3:
                    masked_key = f"{parts[0]}-{'*' * 8}-{'*' * 8}"
            else:
                masked_key = "***masked***"

        return {
            'auth_key': masked_key,
            'hostname': self.hostname,
            'ephemeral': self.ephemeral,
            'accept_routes': self.accept_routes,
            'advertise_routes': self.advertise_routes,
            'shields_up': self.shields_up
        }