"""Proxmox client wrapper - adapter for services.proxmox."""

from src.services.proxmox import ProxmoxService


class ProxmoxClient:
    """Proxmox client wrapper for test compatibility."""

    def __init__(self, auth=None):
        """Initialize client with authentication.

        Args:
            auth: ProxmoxAuth instance or config dict
        """
        from src.proxmox.auth import ProxmoxAuth

        if isinstance(auth, dict):
            auth = ProxmoxAuth(auth)

        self.service = ProxmoxService(auth)

    def list_nodes(self):
        """List cluster nodes."""
        return self.service.list_nodes()

    def create_lxc(self, node, vmid, config):
        """Create LXC container."""
        from src.models.container import Container

        container = Container(
            vmid=vmid,
            hostname=config.get('hostname', f'ct{vmid}'),
            template=config.get('ostemplate', 'local:vztmpl/debian-13'),
            node=node,
            cores=config.get('cores', 2),
            memory=config.get('memory', 1024),
            storage=config.get('rootfs_size', 10),
            storage_pool=config.get('storage', 'local-lvm')
        )

        return self.service.create_container(container)

    def destroy_lxc(self, node, vmid):
        """Destroy LXC container."""
        return self.service.destroy_container(node, vmid)

    def list_containers(self):
        """List all containers."""
        return self.service.list_containers()

    def get_storage_pools(self, node=None):
        """Get storage pools."""
        return self.service.get_storage_pools(node)

    def get_templates(self):
        """Get available templates."""
        return self.service.get_templates()