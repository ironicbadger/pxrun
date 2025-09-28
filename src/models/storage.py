"""Storage pool model for Proxmox storage locations."""

from dataclasses import dataclass, field
from typing import List


@dataclass
class StoragePool:
    """Named storage location on cluster nodes.

    Attributes:
        name: Pool identifier
        type: Storage type (lvm, zfs, directory, etc.)
        total: Total space in bytes
        used: Used space in bytes
        available: Available space in bytes
        content_types: Supported content (rootdir, images, vztmpl)
        nodes: Nodes with this pool
    """

    name: str
    type: str = "directory"
    total: int = 0
    used: int = 0
    available: int = 0
    content_types: List[str] = field(default_factory=list)
    nodes: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate storage pool configuration after initialization."""
        self.validate()

    def validate(self):
        """Validate storage pool configuration.

        Raises:
            ValueError: If any validation rule is violated
        """
        # Validate pool name
        if not self.name:
            raise ValueError("Storage pool name is required")

        # Validate storage type
        valid_types = [
            "dir", "directory", "lvm", "lvmthin", "zfs", "zfspool",
            "nfs", "cifs", "glusterfs", "iscsi", "iscsidirect",
            "rbd", "cephfs"
        ]
        if self.type and self.type not in valid_types:
            raise ValueError(f"Invalid storage type: {self.type}")

        # Validate space values
        if self.total < 0:
            raise ValueError(f"Total space cannot be negative: {self.total}")

        if self.used < 0:
            raise ValueError(f"Used space cannot be negative: {self.used}")

        if self.available < 0:
            raise ValueError(f"Available space cannot be negative: {self.available}")

        # Validate space consistency
        if self.used > self.total:
            raise ValueError(f"Used space ({self.used}) cannot exceed total space ({self.total})")

    @property
    def usage_percent(self) -> float:
        """Calculate storage usage percentage.

        Returns:
            Usage as percentage (0-100)
        """
        if self.total == 0:
            return 0.0
        return min(100.0, (self.used / self.total) * 100)

    @property
    def free_percent(self) -> float:
        """Calculate free storage percentage.

        Returns:
            Free space as percentage (0-100)
        """
        return max(0.0, 100.0 - self.usage_percent)

    @property
    def total_gb(self) -> float:
        """Get total space in GB.

        Returns:
            Total space in gigabytes
        """
        return self.total / (1024 ** 3)

    @property
    def used_gb(self) -> float:
        """Get used space in GB.

        Returns:
            Used space in gigabytes
        """
        return self.used / (1024 ** 3)

    @property
    def available_gb(self) -> float:
        """Get available space in GB.

        Returns:
            Available space in gigabytes
        """
        return self.available / (1024 ** 3)

    def supports_containers(self) -> bool:
        """Check if pool supports container root filesystems.

        Returns:
            True if pool supports containers, False otherwise
        """
        return "rootdir" in self.content_types

    def supports_templates(self) -> bool:
        """Check if pool supports templates.

        Returns:
            True if pool supports templates, False otherwise
        """
        return "vztmpl" in self.content_types

    def supports_images(self) -> bool:
        """Check if pool supports disk images.

        Returns:
            True if pool supports images, False otherwise
        """
        return "images" in self.content_types

    def is_available_on_node(self, node_name: str) -> bool:
        """Check if pool is available on specific node.

        Args:
            node_name: Name of the node to check

        Returns:
            True if pool is available on node, False otherwise
        """
        return node_name in self.nodes

    def can_allocate(self, size_gb: int) -> bool:
        """Check if pool can allocate specified size.

        Args:
            size_gb: Required size in GB

        Returns:
            True if space is available, False otherwise
        """
        required_bytes = size_gb * (1024 ** 3)
        # Add 10% buffer for filesystem overhead
        required_with_buffer = required_bytes * 1.1
        return self.available >= required_with_buffer

    def is_thin_provisioned(self) -> bool:
        """Check if storage uses thin provisioning.

        Returns:
            True if thin provisioned, False otherwise
        """
        return self.type in ["lvmthin", "zfs", "zfspool", "cephfs", "rbd"]

    def is_shared(self) -> bool:
        """Check if storage is shared across cluster.

        Returns:
            True if shared storage, False otherwise
        """
        return self.type in ["nfs", "cifs", "glusterfs", "cephfs", "rbd", "iscsi", "iscsidirect"]

    def is_local(self) -> bool:
        """Check if storage is local to node.

        Returns:
            True if local storage, False otherwise
        """
        return self.type in ["dir", "directory", "lvm", "lvmthin", "zfs", "zfspool"]

    @classmethod
    def from_api_response(cls, data: dict) -> 'StoragePool':
        """Create StoragePool instance from Proxmox API response.

        Args:
            data: API response data

        Returns:
            StoragePool instance
        """
        # Parse content types
        content = data.get('content', '')
        content_types = content.split(',') if content else []

        # Parse nodes
        nodes_str = data.get('nodes', '')
        nodes = nodes_str.split(',') if nodes_str else []

        return cls(
            name=data.get('storage', ''),
            type=data.get('type', 'directory'),
            total=data.get('total', 0),
            used=data.get('used', 0),
            available=data.get('avail', 0),
            content_types=content_types,
            nodes=nodes if nodes else []  # Empty list means all nodes
        )

    def to_dict(self) -> dict:
        """Convert storage pool to dictionary representation.

        Returns:
            Dictionary representation of the storage pool
        """
        return {
            'name': self.name,
            'type': self.type,
            'total': self.total,
            'total_gb': self.total_gb,
            'used': self.used,
            'used_gb': self.used_gb,
            'available': self.available,
            'available_gb': self.available_gb,
            'usage_percent': self.usage_percent,
            'free_percent': self.free_percent,
            'content_types': self.content_types,
            'nodes': self.nodes,
            'supports_containers': self.supports_containers(),
            'supports_templates': self.supports_templates(),
            'supports_images': self.supports_images(),
            'is_thin_provisioned': self.is_thin_provisioned(),
            'is_shared': self.is_shared(),
            'is_local': self.is_local()
        }