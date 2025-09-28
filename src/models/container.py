"""Container model with validation for LXC containers."""

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
import re


@dataclass
class Container:
    """Represents all settings needed to create an LXC container.

    Attributes:
        vmid: Unique container identifier (100-999999999)
        hostname: Container hostname (alphanumeric + dash, max 63 chars)
        template: Template identifier (e.g., "local:vztmpl/debian-13-standard_13.0-1_amd64.tar.zst")
        node: Target Proxmox node name
        cores: Number of CPU cores (1-128, default: 2)
        memory: Memory in MB (16-524288, default: 1024)
        storage: Root disk size in GB (1-8192, default: 10)
        storage_pool: Storage pool name (e.g., "local-lvm")
        network_bridge: Network bridge (default: "vmbr0")
        network_ip: Static IP in CIDR notation or "dhcp"
        network_gateway: Gateway IP address
        start_on_boot: Auto-start container (default: False)
        unprivileged: Run as unprivileged container (default: True)
        features: Container features (nesting, keyctl, etc.)
        mount_points: Host directory mappings
        devices: Hardware device passthrough
        provisioning: Post-creation setup
    """

    vmid: int
    hostname: str
    template: str
    node: str
    cores: int = 2
    memory: int = 1024
    storage: int = 10
    storage_pool: str = "local-lvm"
    network_bridge: str = "vmbr0"
    network_ip: Optional[str] = None
    network_gateway: Optional[str] = None
    start_on_boot: bool = False
    unprivileged: bool = True
    features: Dict[str, bool] = field(default_factory=dict)
    mount_points: List[Any] = field(default_factory=list)  # List[MountPoint]
    devices: List[Any] = field(default_factory=list)  # List[Device]
    provisioning: Optional[Any] = None  # ProvisioningConfig

    def __post_init__(self):
        """Validate container configuration after initialization."""
        self.validate()

    def validate(self):
        """Validate all container settings.

        Raises:
            ValueError: If any validation rule is violated
        """
        # Validate VMID range
        if not (100 <= self.vmid <= 999999999):
            raise ValueError(f"VMID must be between 100 and 999999999, got {self.vmid}")

        # Validate hostname
        if not self._is_valid_hostname(self.hostname):
            raise ValueError(f"Invalid hostname: {self.hostname}")

        # Validate cores
        if not (1 <= self.cores <= 128):
            raise ValueError(f"Cores must be between 1 and 128, got {self.cores}")

        # Validate memory
        if not (16 <= self.memory <= 524288):
            raise ValueError(f"Memory must be between 16 and 524288 MB, got {self.memory}")

        # Validate storage
        if not (1 <= self.storage <= 8192):
            raise ValueError(f"Storage must be between 1 and 8192 GB, got {self.storage}")

        # Validate network IP if provided
        if self.network_ip and self.network_ip != "dhcp":
            if not self._is_valid_cidr(self.network_ip):
                raise ValueError(f"Invalid network IP CIDR: {self.network_ip}")

        # Validate gateway if provided
        if self.network_gateway:
            if not self._is_valid_ip(self.network_gateway):
                raise ValueError(f"Invalid gateway IP: {self.network_gateway}")

    def _is_valid_hostname(self, hostname: str) -> bool:
        """Check if hostname is valid DNS name.

        Args:
            hostname: The hostname to validate

        Returns:
            True if hostname is valid, False otherwise
        """
        if len(hostname) > 63:
            return False
        # Hostname pattern: alphanumeric and dash, must start/end with alphanumeric
        pattern = r'^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$'
        return bool(re.match(pattern, hostname.lower()))

    def _is_valid_cidr(self, cidr: str) -> bool:
        """Check if IP is in valid CIDR notation.

        Args:
            cidr: IP address in CIDR format (e.g., "192.168.1.100/24")

        Returns:
            True if valid CIDR, False otherwise
        """
        try:
            parts = cidr.split('/')
            if len(parts) != 2:
                return False
            ip_part = parts[0]
            mask_part = int(parts[1])
            if not (0 <= mask_part <= 32):
                return False
            return self._is_valid_ip(ip_part)
        except (ValueError, AttributeError):
            return False

    def _is_valid_ip(self, ip: str) -> bool:
        """Check if IP address is valid IPv4.

        Args:
            ip: IP address to validate

        Returns:
            True if valid IPv4, False otherwise
        """
        try:
            octets = ip.split('.')
            if len(octets) != 4:
                return False
            for octet in octets:
                num = int(octet)
                if not (0 <= num <= 255):
                    return False
            return True
        except (ValueError, AttributeError):
            return False

    def to_api_params(self) -> Dict[str, Any]:
        """Convert container configuration to Proxmox API parameters.

        Returns:
            Dictionary of parameters for Proxmox API
        """
        params = {
            'vmid': self.vmid,
            'hostname': self.hostname,
            'ostemplate': self.template,
            'cores': self.cores,
            'memory': self.memory,
            'rootfs': f"{self.storage_pool}:{self.storage}",
            'start': int(self.start_on_boot),
            'unprivileged': int(self.unprivileged),
        }

        # Add network configuration
        if self.network_ip:
            if self.network_ip == "dhcp":
                params['net0'] = f"bridge={self.network_bridge},name=eth0,ip=dhcp"
            else:
                net_config = f"bridge={self.network_bridge},name=eth0,ip={self.network_ip}"
                if self.network_gateway:
                    net_config += f",gw={self.network_gateway}"
                params['net0'] = net_config
        else:
            params['net0'] = f"bridge={self.network_bridge},name=eth0"

        # Add features if specified
        if self.features:
            feature_list = []
            for feature, enabled in self.features.items():
                feature_list.append(f"{feature}={int(enabled)}")
            if feature_list:
                params['features'] = ','.join(feature_list)

        return params

    @classmethod
    def from_api_response(cls, data: Dict[str, Any], node: str, vmid: int = None) -> 'Container':
        """Create Container instance from Proxmox API response.

        Args:
            data: API response data
            node: Node name where container resides
            vmid: Container ID (if not in data)

        Returns:
            Container instance
        """
        # Get VMID from data or parameter
        container_vmid = data.get('vmid', vmid)
        if not container_vmid:
            raise ValueError("VMID not provided")

        # Parse rootfs to get storage info
        rootfs = data.get('rootfs', 'local-lvm:10')
        storage_parts = rootfs.split(':')
        storage_pool = storage_parts[0] if storage_parts else 'local-lvm'
        storage_size = int(storage_parts[1]) if len(storage_parts) > 1 and storage_parts[1].isdigit() else 10

        # Parse network configuration
        net0 = data.get('net0', '')
        network_bridge = 'vmbr0'
        network_ip = None
        network_gateway = None

        if net0:
            # Parse network string like "bridge=vmbr0,name=eth0,ip=192.168.1.100/24,gw=192.168.1.1"
            for part in net0.split(','):
                if '=' in part:
                    key, value = part.split('=', 1)
                    if key == 'bridge':
                        network_bridge = value
                    elif key == 'ip':
                        network_ip = value
                    elif key == 'gw':
                        network_gateway = value

        # Parse features
        features = {}
        features_str = data.get('features', '')
        if features_str:
            for feature in features_str.split(','):
                if '=' in feature:
                    key, value = feature.split('=', 1)
                    features[key] = value == '1'

        return cls(
            vmid=container_vmid,
            hostname=data.get('hostname', f"ct{container_vmid}"),
            template=data.get('ostemplate', ''),
            node=node,
            cores=data.get('cores', 2),
            memory=data.get('memory', 1024),
            storage=storage_size,
            storage_pool=storage_pool,
            network_bridge=network_bridge,
            network_ip=network_ip,
            network_gateway=network_gateway,
            start_on_boot=bool(data.get('onboot', 0)),
            unprivileged=bool(data.get('unprivileged', 1)),
            features=features
        )