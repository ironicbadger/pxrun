"""Credentials manager for environment variables and .env files."""

import os
import logging
from typing import Dict, Optional, List, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class CredentialsManager:
    """Service for managing credentials from environment and .env files."""

    def __init__(self, env_file: Optional[str] = None):
        """Initialize credentials manager.

        Args:
            env_file: Path to .env file (optional)
        """
        self.env_file = env_file or '.env'
        self.loaded = False

    def load_env_file(self, env_file: Optional[str] = None) -> Dict[str, str]:
        """Load environment variables from .env file.

        Args:
            env_file: Path to .env file (uses default if not provided)

        Returns:
            Dictionary of loaded environment variables
        """
        env_file = env_file or self.env_file
        env_vars = {}

        if not Path(env_file).exists():
            logger.debug(f"Environment file {env_file} not found")
            return env_vars

        try:
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if line and not line.startswith('#'):
                        if '=' in line:
                            key, value = line.split('=', 1)
                            # Remove quotes if present
                            value = value.strip().strip('"').strip("'")
                            key = key.strip()
                            env_vars[key] = value
                            # Set in environment if not already set
                            if key not in os.environ:
                                os.environ[key] = value

            logger.info(f"Loaded {len(env_vars)} environment variables from {env_file}")
            self.loaded = True

        except Exception as e:
            logger.error(f"Failed to load environment file: {e}")

        return env_vars

    def get_credential(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a credential value from environment.

        Args:
            key: Environment variable name
            default: Default value if not found

        Returns:
            Credential value or default
        """
        # Load .env file if not already loaded
        if not self.loaded and Path(self.env_file).exists():
            self.load_env_file()

        return os.environ.get(key, default)

    def set_credential(self, key: str, value: str):
        """Set a credential in the environment.

        Args:
            key: Environment variable name
            value: Value to set
        """
        os.environ[key] = value
        logger.debug(f"Set environment variable: {key}")

    def validate_credentials(self, required_keys: List[str]) -> Tuple[bool, List[str]]:
        """Validate that required credentials are present.

        Args:
            required_keys: List of required environment variable names

        Returns:
            Tuple of (all_present, missing_keys)
        """
        # Load .env file if not already loaded
        if not self.loaded and Path(self.env_file).exists():
            self.load_env_file()

        missing = []
        for key in required_keys:
            if not os.environ.get(key):
                missing.append(key)

        return len(missing) == 0, missing

    def get_proxmox_credentials(self) -> Dict[str, str]:
        """Get Proxmox connection credentials.

        Returns:
            Dictionary with Proxmox credentials
        """
        # Load .env file if not already loaded
        if not self.loaded and Path(self.env_file).exists():
            self.load_env_file()

        return {
            'host': self.get_credential('PROXMOX_HOST', 'https://localhost:8006'),
            'token_id': self.get_credential('PROXMOX_TOKEN_ID', ''),
            'token_secret': self.get_credential('PROXMOX_TOKEN_SECRET', ''),
            'user': self.get_credential('PROXMOX_USER', ''),
            'password': self.get_credential('PROXMOX_PASSWORD', ''),
            'verify_ssl': self.get_credential('PROXMOX_VERIFY_SSL', 'false').lower() == 'true'
        }

    def get_ssh_credentials(self) -> Dict[str, str]:
        """Get SSH credentials for provisioning.

        Returns:
            Dictionary with SSH credentials
        """
        # Load .env file if not already loaded
        if not self.loaded and Path(self.env_file).exists():
            self.load_env_file()

        return {
            'user': self.get_credential('SSH_USER', 'root'),
            'key_path': self.get_credential('SSH_KEY_PATH', '~/.ssh/id_rsa'),
            'timeout': int(self.get_credential('SSH_TIMEOUT', '30'))
        }

    def get_container_defaults(self) -> Dict[str, any]:
        """Get default container settings.

        Returns:
            Dictionary with default container settings
        """
        # Load .env file if not already loaded
        if not self.loaded and Path(self.env_file).exists():
            self.load_env_file()

        return {
            'cores': int(self.get_credential('DEFAULT_CORES', '2')),
            'memory': int(self.get_credential('DEFAULT_MEMORY', '1024')),
            'storage': int(self.get_credential('DEFAULT_STORAGE', '10')),
            'bridge': self.get_credential('DEFAULT_BRIDGE', 'vmbr0'),
            'storage_pool': self.get_credential('DEFAULT_STORAGE_POOL', 'local-lvm')
        }

    def mask_sensitive_value(self, value: str, show_chars: int = 4) -> str:
        """Mask a sensitive value for display.

        Args:
            value: Value to mask
            show_chars: Number of characters to show at start

        Returns:
            Masked value
        """
        if not value:
            return ""

        if len(value) <= show_chars:
            return "*" * len(value)

        return value[:show_chars] + "*" * (len(value) - show_chars)