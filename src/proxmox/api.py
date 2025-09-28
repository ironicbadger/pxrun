"""Proxmox API wrapper - adapter for services.proxmox."""

from src.services.proxmox import ProxmoxService as _ProxmoxService

# Alias for compatibility with tests
ProxmoxAPI = _ProxmoxService