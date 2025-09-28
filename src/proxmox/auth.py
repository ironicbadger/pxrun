"""Proxmox authentication wrapper - adapter for services.proxmox."""

from src.services.proxmox import ProxmoxAuth as _ProxmoxAuth


class ProxmoxAuth(_ProxmoxAuth):
    """Proxmox authentication wrapper for test compatibility."""

    def __init__(self, config=None):
        """Initialize auth from config dict or env.

        Args:
            config: Optional config dict with host, token_name, token_value
        """
        if config:
            # Convert test format to our format
            host = config.get('host', 'localhost')
            port = config.get('port', 8006)
            if port != 8006:
                host = f"{host}:{port}"

            token_id = config.get('user', 'root@pam')
            if config.get('token_name'):
                token_id = f"{token_id}!{config['token_name']}"

            super().__init__(
                host=host,
                token_id=token_id,
                token_secret=config.get('token_value', ''),
                verify_ssl=config.get('verify_ssl', False)
            )
        else:
            # Use environment variables
            super().__init__.from_env()

    def authenticate(self):
        """Test authentication with the server.

        Returns:
            True if authentication succeeds
        """
        from src.services.proxmox import ProxmoxService

        try:
            service = ProxmoxService(self)
            result = service.test_connection()
            self._authenticated = result
            return result
        except Exception:
            self._authenticated = False
            return False

    def is_authenticated(self):
        """Check if authentication has been verified.

        Returns:
            True if authenticated successfully
        """
        return getattr(self, '_authenticated', False)