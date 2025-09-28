"""Template model for pre-built OS images."""

from dataclasses import dataclass, field
from typing import List, Optional
import re


@dataclass
class Template:
    """Pre-built OS images available on Proxmox nodes.

    Attributes:
        storage: Storage location (e.g., "local")
        format: Template format (e.g., "vztmpl")
        name: Template filename
        size: Size in bytes
        os_type: OS type (debian, ubuntu, alpine, etc.)
        os_version: OS version string
        architecture: Architecture (amd64, arm64)
        available_on_nodes: Nodes with this template
    """

    storage: str
    format: str
    name: str
    size: int = 0
    os_type: str = ""
    os_version: str = ""
    architecture: str = "amd64"
    available_on_nodes: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Parse template name and validate after initialization."""
        if self.name and not self.os_type:
            self._parse_template_name()
        self.validate()

    def _parse_template_name(self):
        """Parse OS type, version, and architecture from template name.

        Examples:
            debian-13-standard_13.0-1_amd64.tar.zst -> debian, 13, amd64
            ubuntu-22.04-standard_22.04-1_amd64.tar.zst -> ubuntu, 22.04, amd64
            alpine-3.18-standard_3.18.0-1_amd64.tar.gz -> alpine, 3.18, amd64
        """
        # Common pattern: os-version-standard_version_arch.tar.ext
        pattern = r'^([a-z]+)-([0-9.]+)-.*_([a-z0-9]+)\.(tar\.[a-z]+|tar)$'
        match = re.match(pattern, self.name.lower())

        if match:
            self.os_type = match.group(1)
            self.os_version = match.group(2)
            self.architecture = match.group(3)
        else:
            # Try simpler pattern for custom templates
            simple_pattern = r'^([a-z]+)-?([0-9.]*)'
            simple_match = re.match(simple_pattern, self.name.lower())
            if simple_match:
                self.os_type = simple_match.group(1)
                if simple_match.group(2):
                    self.os_version = simple_match.group(2)

    def validate(self):
        """Validate template configuration.

        Raises:
            ValueError: If any validation rule is violated
        """
        # Validate required fields
        if not self.storage:
            raise ValueError("Template storage location is required")

        if not self.name:
            raise ValueError("Template name is required")

        # Validate format
        valid_formats = ["vztmpl", "iso", "qcow2", "raw", "tzst"]
        if self.format and self.format not in valid_formats:
            raise ValueError(f"Invalid template format: {self.format}")

        # Validate size
        if self.size < 0:
            raise ValueError(f"Template size cannot be negative: {self.size}")

        # Validate architecture
        valid_architectures = ["amd64", "arm64", "i386", "armhf"]
        if self.architecture and self.architecture not in valid_architectures:
            raise ValueError(f"Invalid architecture: {self.architecture}")

    @property
    def full_path(self) -> str:
        """Get full template path.

        Returns:
            Full path including storage and format
        """
        # LXC templates always use 'vztmpl' format in their path regardless of file extension
        return f"{self.storage}:vztmpl/{self.name}"

    @property
    def display_name(self) -> str:
        """Get human-readable template name.

        Returns:
            Formatted display name
        """
        if self.os_type and self.os_version:
            return f"{self.os_type.title()} {self.os_version} ({self.architecture})"
        return self.name

    @property
    def size_mb(self) -> float:
        """Get template size in MB.

        Returns:
            Size in megabytes
        """
        return self.size / (1024 * 1024)

    @property
    def size_gb(self) -> float:
        """Get template size in GB.

        Returns:
            Size in gigabytes
        """
        return self.size / (1024 * 1024 * 1024)

    def is_available_on_node(self, node_name: str) -> bool:
        """Check if template is available on specific node.

        Args:
            node_name: Name of the node to check

        Returns:
            True if template is available on node, False otherwise
        """
        return node_name in self.available_on_nodes

    def matches_search(self, search_term: str) -> bool:
        """Check if template matches search term.

        Args:
            search_term: Term to search for (case-insensitive)

        Returns:
            True if template matches search term
        """
        search_lower = search_term.lower()
        return (
            search_lower in self.name.lower() or
            search_lower in self.os_type.lower() or
            search_lower in self.os_version.lower() or
            search_lower in self.architecture.lower()
        )

    @classmethod
    def from_api_response(cls, data: dict, storage: str = "local") -> 'Template':
        """Create Template instance from Proxmox API response.

        Args:
            data: API response data
            storage: Storage location

        Returns:
            Template instance
        """
        # API returns volid like "local:vztmpl/debian-13-standard_13.0-1_amd64.tar.zst"
        volid = data.get('volid', '')
        parts = volid.split('/')
        name = parts[-1] if parts else data.get('name', '')

        # Parse storage from volid if available
        if ':' in volid:
            storage_part = volid.split(':')[0]
            if storage_part:
                storage = storage_part

        return cls(
            storage=storage,
            format=data.get('format', 'vztmpl'),
            name=name,
            size=data.get('size', 0),
            available_on_nodes=[data.get('node')] if data.get('node') else []
        )

    @classmethod
    def from_shorthand(cls, shorthand: str, storage: str = "local") -> 'Template':
        """Create Template from shorthand notation.

        Args:
            shorthand: Shorthand like "debian-13" or full path
            storage: Default storage location

        Returns:
            Template instance
        """
        # Check if it's already a full path
        if ':' in shorthand:
            parts = shorthand.split(':', 1)
            storage = parts[0]
            rest = parts[1]
            if '/' in rest:
                format_part, name = rest.split('/', 1)
                return cls(storage=storage, format=format_part, name=name)
            else:
                return cls(storage=storage, format="vztmpl", name=rest)

        # Otherwise treat as template name, need to find full name
        # This would typically search for matching templates
        return cls(
            storage=storage,
            format="vztmpl",
            name=shorthand
        )

    def to_dict(self) -> dict:
        """Convert template to dictionary representation.

        Returns:
            Dictionary representation of the template
        """
        return {
            'storage': self.storage,
            'format': self.format,
            'name': self.name,
            'full_path': self.full_path,
            'display_name': self.display_name,
            'size': self.size,
            'size_mb': self.size_mb,
            'size_gb': self.size_gb,
            'os_type': self.os_type,
            'os_version': self.os_version,
            'architecture': self.architecture,
            'available_on_nodes': self.available_on_nodes
        }