"""Custom exceptions for pxrun."""


class PxrunException(Exception):
    """Base exception for pxrun."""
    pass


class TailscaleConfigError(PxrunException):
    """Raised when Tailscale configuration is invalid or missing."""
    pass


class TailscaleInstallationError(PxrunException):
    """Raised when Tailscale installation fails."""
    pass


class TailscaleAuthenticationError(PxrunException):
    """Raised when Tailscale authentication fails."""
    pass


class SSHConnectionError(PxrunException):
    """Raised when SSH connection fails."""
    pass


class UnsupportedSystemError(PxrunException):
    """Raised when system is not supported."""
    pass


class InvalidAuthKeyError(PxrunException):
    """Raised when Tailscale auth key format is invalid."""
    pass