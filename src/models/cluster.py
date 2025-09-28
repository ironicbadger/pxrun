"""Cluster node model for Proxmox servers."""

from dataclasses import dataclass, field
from typing import List, Optional, Any


@dataclass
class ClusterNode:
    """Individual Proxmox server in the cluster.

    Attributes:
        name: Node identifier
        status: Node status (online/offline)
        cpu_total: Total CPU cores
        cpu_used: Used CPU percentage (0-100)
        memory_total: Total memory in bytes
        memory_used: Used memory in bytes
        storage_pools: Available storage pools
        networks: Available network bridges
        version: Proxmox VE version
    """

    name: str
    status: str = "online"
    cpu_total: int = 0
    cpu_used: float = 0.0
    memory_total: int = 0
    memory_used: int = 0
    storage_pools: List[Any] = field(default_factory=list)  # List[StoragePool]
    networks: List[str] = field(default_factory=list)
    version: str = ""

    def __post_init__(self):
        """Validate node configuration after initialization."""
        self.validate()

    def validate(self):
        """Validate node configuration.

        Raises:
            ValueError: If any validation rule is violated
        """
        # Validate node name is not empty
        if not self.name:
            raise ValueError("Node name cannot be empty")

        # Validate status
        if self.status not in ["online", "offline", "unknown"]:
            raise ValueError(f"Invalid node status: {self.status}")

        # Validate CPU usage percentage
        if not (0 <= self.cpu_used <= 100):
            raise ValueError(f"CPU usage must be between 0 and 100, got {self.cpu_used}")

        # Validate memory values
        if self.memory_used > self.memory_total:
            raise ValueError(f"Used memory ({self.memory_used}) cannot exceed total memory ({self.memory_total})")

        # Validate CPU total
        if self.cpu_total < 0:
            raise ValueError(f"CPU total cannot be negative: {self.cpu_total}")

    @property
    def is_online(self) -> bool:
        """Check if node is online.

        Returns:
            True if node is online, False otherwise
        """
        return self.status == "online"

    @property
    def memory_free(self) -> int:
        """Calculate free memory in bytes.

        Returns:
            Free memory in bytes
        """
        return max(0, self.memory_total - self.memory_used)

    @property
    def memory_usage_percent(self) -> float:
        """Calculate memory usage percentage.

        Returns:
            Memory usage as percentage (0-100)
        """
        if self.memory_total == 0:
            return 0.0
        return min(100.0, (self.memory_used / self.memory_total) * 100)

    @property
    def cpu_free_percent(self) -> float:
        """Calculate free CPU percentage.

        Returns:
            Free CPU as percentage (0-100)
        """
        return max(0.0, 100.0 - self.cpu_used)

    def has_storage_pool(self, pool_name: str) -> bool:
        """Check if node has a specific storage pool.

        Args:
            pool_name: Name of the storage pool to check

        Returns:
            True if node has the storage pool, False otherwise
        """
        for pool in self.storage_pools:
            if hasattr(pool, 'name') and pool.name == pool_name:
                return True
        return False

    def has_network_bridge(self, bridge_name: str) -> bool:
        """Check if node has a specific network bridge.

        Args:
            bridge_name: Name of the network bridge to check

        Returns:
            True if node has the bridge, False otherwise
        """
        return bridge_name in self.networks

    def can_allocate(self, cores: int, memory_mb: int) -> bool:
        """Check if node can allocate specified resources.

        Args:
            cores: Number of CPU cores required
            memory_mb: Memory required in MB

        Returns:
            True if resources are available, False otherwise
        """
        if not self.is_online:
            return False

        # Check CPU availability (assuming we can use up to 80% of total)
        max_cpu_usage = 80.0
        available_cores = self.cpu_total * (max_cpu_usage - self.cpu_used) / 100
        if available_cores < cores:
            return False

        # Check memory availability
        memory_bytes = memory_mb * 1024 * 1024
        if self.memory_free < memory_bytes:
            return False

        return True

    @classmethod
    def from_api_response(cls, data: dict) -> 'ClusterNode':
        """Create ClusterNode instance from Proxmox API response.

        Args:
            data: API response data

        Returns:
            ClusterNode instance
        """
        # Calculate CPU usage from uptime data
        cpu_used = 0.0
        if 'cpu' in data:
            # CPU is given as a fraction (0-1) in API
            cpu_used = data['cpu'] * 100
        elif 'loadavg' in data and isinstance(data['loadavg'], list) and len(data['loadavg']) > 0:
            # Use load average as approximation if available
            load_avg = float(data['loadavg'][0])
            max_threads = data.get('maxcpu', 1)
            cpu_used = min(100.0, (load_avg / max_threads) * 100)

        return cls(
            name=data.get('node', ''),
            status=data.get('status', 'unknown'),
            cpu_total=data.get('maxcpu', 0),
            cpu_used=cpu_used,
            memory_total=data.get('maxmem', 0),
            memory_used=data.get('mem', 0),
            networks=[],  # Will be populated from separate API call
            version=data.get('version', ''),
            storage_pools=[]  # Will be populated from separate API call
        )

    def to_dict(self) -> dict:
        """Convert node to dictionary representation.

        Returns:
            Dictionary representation of the node
        """
        return {
            'name': self.name,
            'status': self.status,
            'cpu_total': self.cpu_total,
            'cpu_used': self.cpu_used,
            'cpu_free_percent': self.cpu_free_percent,
            'memory_total': self.memory_total,
            'memory_used': self.memory_used,
            'memory_free': self.memory_free,
            'memory_usage_percent': self.memory_usage_percent,
            'networks': self.networks,
            'version': self.version,
            'is_online': self.is_online
        }