"""Mount point and device models for container configuration."""

from dataclasses import dataclass
from typing import Optional
import os
import re


@dataclass
class MountPoint:
    """Mapping between host directories and container paths.

    Attributes:
        id: Mount point identifier (mp0, mp1, etc.)
        host_path: Absolute path on Proxmox host
        container_path: Absolute path in container
        read_only: Read-only mount (default: False)
        size: Size limit (e.g., "10G")
        backup: Include in backups (default: True)
    """

    id: str
    host_path: str
    container_path: str
    read_only: bool = False
    size: Optional[str] = None
    backup: bool = True

    def __post_init__(self):
        """Validate mount point configuration after initialization."""
        self.validate()

    def validate(self):
        """Validate mount point configuration.

        Raises:
            ValueError: If any validation rule is violated
        """
        # Validate mount ID
        if not self._is_valid_mount_id(self.id):
            raise ValueError(f"Invalid mount point ID: {self.id}. Must be mp0-mp255")

        # Validate paths are absolute
        if not os.path.isabs(self.host_path):
            raise ValueError(f"Host path must be absolute: {self.host_path}")

        if not os.path.isabs(self.container_path):
            raise ValueError(f"Container path must be absolute: {self.container_path}")

        # Validate container path doesn't conflict with system paths
        system_paths = ["/", "/bin", "/boot", "/dev", "/etc", "/lib", "/lib64",
                        "/proc", "/root", "/sbin", "/sys", "/usr", "/var"]
        if self.container_path in system_paths:
            raise ValueError(f"Container path conflicts with system path: {self.container_path}")

        # Validate size format if provided
        if self.size and not self._is_valid_size(self.size):
            raise ValueError(f"Invalid size format: {self.size}. Use format like '10G' or '100M'")

    def _is_valid_mount_id(self, mount_id: str) -> bool:
        """Check if mount ID is valid.

        Args:
            mount_id: Mount point ID to validate

        Returns:
            True if valid, False otherwise
        """
        if not mount_id.startswith("mp"):
            return False

        try:
            num = int(mount_id[2:])
            return 0 <= num <= 255
        except (ValueError, IndexError):
            return False

    def _is_valid_size(self, size: str) -> bool:
        """Check if size format is valid.

        Args:
            size: Size string to validate (e.g., "10G", "100M")

        Returns:
            True if valid, False otherwise
        """
        pattern = r'^\d+[KMGT]?$'
        return bool(re.match(pattern, size.upper()))

    def to_api_format(self) -> str:
        """Convert mount point to Proxmox API format.

        Returns:
            API formatted string for mount point
        """
        # Basic format: host_path,mp=container_path
        config = f"{self.host_path},mp={self.container_path}"

        # Add optional parameters
        if self.read_only:
            config += ",ro=1"

        if self.size:
            config += f",size={self.size}"

        if not self.backup:
            config += ",backup=0"

        return config

    @classmethod
    def from_api_format(cls, mount_id: str, config: str) -> 'MountPoint':
        """Create MountPoint from Proxmox API format.

        Args:
            mount_id: Mount point ID (e.g., "mp0")
            config: API config string

        Returns:
            MountPoint instance
        """
        # Parse format like: /host/path,mp=/container/path,ro=1,size=10G
        parts = config.split(',')
        host_path = parts[0] if parts else ""
        container_path = ""
        read_only = False
        size = None
        backup = True

        for part in parts[1:]:
            if '=' in part:
                key, value = part.split('=', 1)
                if key == 'mp':
                    container_path = value
                elif key == 'ro':
                    read_only = value == '1'
                elif key == 'size':
                    size = value
                elif key == 'backup':
                    backup = value != '0'

        return cls(
            id=mount_id,
            host_path=host_path,
            container_path=container_path,
            read_only=read_only,
            size=size,
            backup=backup
        )

    def to_dict(self) -> dict:
        """Convert mount point to dictionary representation.

        Returns:
            Dictionary representation
        """
        return {
            'id': self.id,
            'host_path': self.host_path,
            'container_path': self.container_path,
            'read_only': self.read_only,
            'size': self.size,
            'backup': self.backup
        }


@dataclass
class Device:
    """Hardware device passthrough configuration.

    Attributes:
        path: Device path (e.g., "/dev/dri/renderD128")
        major: Device major number
        minor: Device minor number
        mode: Access mode (rw, r, w)
        uid: User ID in container (default: 0)
        gid: Group ID in container (default: 0)
    """

    path: str
    major: Optional[int] = None
    minor: Optional[int] = None
    mode: str = "rw"
    uid: int = 0
    gid: int = 0

    def __post_init__(self):
        """Validate device configuration after initialization."""
        self.validate()
        # Try to get major/minor if not provided
        if self.path and (self.major is None or self.minor is None):
            self._get_device_numbers()

    def validate(self):
        """Validate device configuration.

        Raises:
            ValueError: If any validation rule is violated
        """
        # Validate device path
        if not self.path:
            raise ValueError("Device path is required")

        if not self.path.startswith("/dev/"):
            raise ValueError(f"Device path must start with /dev/: {self.path}")

        # Validate mode
        valid_modes = ["rw", "r", "w", "rwm"]
        if self.mode not in valid_modes:
            raise ValueError(f"Invalid device mode: {self.mode}. Must be one of {valid_modes}")

        # Validate UID/GID
        if self.uid < 0:
            raise ValueError(f"UID cannot be negative: {self.uid}")

        if self.gid < 0:
            raise ValueError(f"GID cannot be negative: {self.gid}")

        # Validate major/minor if provided
        if self.major is not None and self.major < 0:
            raise ValueError(f"Major number cannot be negative: {self.major}")

        if self.minor is not None and self.minor < 0:
            raise ValueError(f"Minor number cannot be negative: {self.minor}")

    def _get_device_numbers(self):
        """Try to get device major/minor numbers from system.

        This would typically use os.stat() but we'll leave it as
        optional since we may not have access to the actual device.
        """
        # In a real implementation, this would do:
        # try:
        #     stat = os.stat(self.path)
        #     self.major = os.major(stat.st_rdev)
        #     self.minor = os.minor(stat.st_rdev)
        # except OSError:
        #     pass
        pass

    def to_lxc_config(self) -> dict:
        """Convert device to LXC configuration format.

        Returns:
            Dictionary of LXC config entries
        """
        config = {}

        # Basic device allow rule
        if self.major is not None and self.minor is not None:
            # Format: lxc.cgroup2.devices.allow = c major:minor mode
            device_type = "c"  # character device (most common)
            allow_rule = f"{device_type} {self.major}:{self.minor} {self.mode}"
            config['lxc.cgroup2.devices.allow'] = allow_rule

        # Mount the device into container
        config[f'lxc.mount.entry'] = f"{self.path} {self.path[1:]} none bind,create=file 0 0"

        # Set ownership if not root
        if self.uid != 0 or self.gid != 0:
            config[f'lxc.hook.autodev'] = f"/bin/chown {self.uid}:{self.gid} {self.path}"

        return config

    def requires_privileged(self) -> bool:
        """Check if device requires privileged container.

        Returns:
            True if privileged container is required
        """
        # GPU devices typically require privileged
        gpu_devices = ["/dev/dri", "/dev/nvidia", "/dev/vga"]
        return any(self.path.startswith(dev) for dev in gpu_devices)

    @classmethod
    def from_lxc_config(cls, path: str, config: dict) -> 'Device':
        """Create Device from LXC configuration.

        Args:
            path: Device path
            config: LXC configuration dictionary

        Returns:
            Device instance
        """
        # Parse device allow rule if present
        major = None
        minor = None
        mode = "rw"

        allow_rule = config.get('lxc.cgroup2.devices.allow', '')
        if allow_rule:
            # Parse format: c major:minor mode
            parts = allow_rule.split()
            if len(parts) >= 2 and ':' in parts[1]:
                maj_min = parts[1].split(':')
                try:
                    major = int(maj_min[0])
                    minor = int(maj_min[1])
                except ValueError:
                    pass
                if len(parts) >= 3:
                    mode = parts[2]

        return cls(
            path=path,
            major=major,
            minor=minor,
            mode=mode
        )

    def to_dict(self) -> dict:
        """Convert device to dictionary representation.

        Returns:
            Dictionary representation
        """
        return {
            'path': self.path,
            'major': self.major,
            'minor': self.minor,
            'mode': self.mode,
            'uid': self.uid,
            'gid': self.gid,
            'requires_privileged': self.requires_privileged()
        }