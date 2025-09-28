# Data Model: pxrun

**Generated**: 2025-09-27
**Phase**: 1 - Design & Contracts

## Overview
Data structures and relationships for the pxrun LXC container management tool. All models are designed for stateless operation, with Proxmox as the source of truth.

## Core Entities

### Container Configuration
Represents all settings needed to create an LXC container.

**Attributes**:
- `vmid`: integer (100-999999999) - Unique container identifier
- `hostname`: string - Container hostname (alphanumeric + dash, max 63 chars)
- `template`: string - Template identifier (e.g., "local:vztmpl/debian-13-standard_13.0-1_amd64.tar.zst")
- `node`: string - Target Proxmox node name
- `cores`: integer (1-128) - Number of CPU cores (default: 2)
- `memory`: integer (16-524288) - Memory in MB (default: 1024)
- `storage`: integer (1-8192) - Root disk size in GB (default: 10)
- `storage_pool`: string - Storage pool name (e.g., "local-lvm")
- `network_bridge`: string - Network bridge (default: "vmbr0")
- `network_ip`: string (optional) - Static IP in CIDR notation or "dhcp"
- `network_gateway`: string (optional) - Gateway IP address
- `start_on_boot`: boolean - Auto-start container (default: false)
- `unprivileged`: boolean - Run as unprivileged container (default: true)
- `features`: dict - Container features (nesting, keyctl, etc.)
- `mount_points`: list[MountPoint] - Host directory mappings
- `devices`: list[Device] - Hardware device passthrough
- `provisioning`: ProvisioningConfig - Post-creation setup

**Validation Rules**:
- vmid must be unique across cluster
- hostname must be valid DNS name
- template must exist on target node
- cores + memory must not exceed node capacity
- storage_pool must exist on node
- mount point paths must be absolute
- network IP must be valid CIDR or "dhcp"

**State Transitions**:
- None → Created (via Proxmox API)
- Created → Provisioning (SSH connection established)
- Provisioning → Running (provisioning complete)
- Running → Stopped (via stop command)
- Any → Destroyed (via destroy command)

### Container Template
Pre-built OS images available on Proxmox nodes.

**Attributes**:
- `storage`: string - Storage location (e.g., "local")
- `format`: string - Template format (e.g., "vztmpl")
- `name`: string - Template filename
- `size`: integer - Size in bytes
- `os_type`: string - OS type (debian, ubuntu, alpine, etc.)
- `os_version`: string - OS version string
- `architecture`: string - Architecture (amd64, arm64)
- `available_on_nodes`: list[string] - Nodes with this template

**Validation Rules**:
- Template must be accessible from target node
- Architecture must match node capabilities
- Size must fit in available storage

### Cluster Node
Individual Proxmox server in the cluster.

**Attributes**:
- `name`: string - Node identifier
- `status`: string - online/offline
- `cpu_total`: integer - Total CPU cores
- `cpu_used`: float - Used CPU percentage
- `memory_total`: integer - Total memory in bytes
- `memory_used`: integer - Used memory in bytes
- `storage_pools`: list[StoragePool] - Available storage
- `networks`: list[string] - Available network bridges
- `version`: string - Proxmox VE version

**Validation Rules**:
- Node must be online for operations
- Available resources must satisfy container requirements

### Storage Pool
Named storage location on cluster nodes.

**Attributes**:
- `name`: string - Pool identifier
- `type`: string - Storage type (lvm, zfs, directory, etc.)
- `total`: integer - Total space in bytes
- `used`: integer - Used space in bytes
- `available`: integer - Available space in bytes
- `content_types`: list[string] - Supported content (rootdir, images, vztmpl)
- `nodes`: list[string] - Nodes with this pool

**Validation Rules**:
- Pool must support "rootdir" for containers
- Available space must exceed container requirements

### Mount Point
Mapping between host directories and container paths.

**Attributes**:
- `id`: string - Mount point identifier (mp0, mp1, etc.)
- `host_path`: string - Absolute path on Proxmox host
- `container_path`: string - Absolute path in container
- `read_only`: boolean - Read-only mount (default: false)
- `size`: string (optional) - Size limit (e.g., "10G")
- `backup`: boolean - Include in backups (default: true)

**Validation Rules**:
- Paths must be absolute
- Host path must exist or be creatable
- Container path must not conflict with system paths
- Mount ID must be unique (mp0-mp255)

### Device
Hardware device passthrough configuration.

**Attributes**:
- `path`: string - Device path (e.g., "/dev/dri/renderD128")
- `major`: integer - Device major number
- `minor`: integer - Device minor number
- `mode`: string - Access mode (rw, r, w)
- `uid`: integer - User ID in container (default: 0)
- `gid`: integer - Group ID in container (default: 0)

**Validation Rules**:
- Device must exist on host
- Major/minor numbers must match device
- Container must be privileged for some devices

### Provisioning Config
Post-creation setup configuration.

**Attributes**:
- `scripts`: list[ProvisioningScript] - Scripts to execute
- `packages`: list[string] - System packages to install
- `docker`: boolean - Install Docker (default: false)
- `tailscale`: TailscaleConfig (optional) - Tailscale setup
- `ssh_keys`: list[string] - SSH public keys to add
- `users`: list[UserConfig] - Additional users to create

### Provisioning Script
Individual provisioning command or script.

**Attributes**:
- `name`: string - Script identifier
- `interpreter`: string - Script interpreter (bash, sh, python)
- `content`: string - Script content
- `run_as`: string - User to run as (default: root)
- `working_dir`: string - Working directory
- `environment`: dict - Environment variables
- `timeout`: integer - Timeout in seconds (default: 300)
- `continue_on_error`: boolean - Continue if script fails

**Validation Rules**:
- Interpreter must be available in container
- User must exist before script runs
- Working directory must exist or be creatable

### Tailscale Config
Tailscale VPN configuration.

**Attributes**:
- `auth_key`: string - Authentication key (encrypted)
- `hostname`: string (optional) - Tailscale hostname
- `accept_routes`: boolean - Accept advertised routes
- `advertise_routes`: list[string] - Routes to advertise
- `shields_up`: boolean - Block incoming connections

**Validation Rules**:
- Auth key must be valid Tailscale key
- Routes must be valid CIDR notation

### User Config
Additional user account configuration.

**Attributes**:
- `username`: string - Linux username
- `uid`: integer (optional) - User ID
- `gid`: integer (optional) - Group ID
- `groups`: list[string] - Additional groups
- `shell`: string - Login shell (default: /bin/bash)
- `home`: string - Home directory
- `ssh_keys`: list[string] - SSH public keys

**Validation Rules**:
- Username must be valid Linux username
- UID/GID must not conflict with existing
- Shell must exist in container
- Groups must exist or be creatable

## Relationships

### Container ↔ Node
- A Container is created on exactly one Node
- A Node can host multiple Containers
- Container resources are allocated from Node capacity

### Container ↔ Template
- A Container is created from exactly one Template
- A Template can be used by multiple Containers
- Template must be available on Container's Node

### Container ↔ Storage Pool
- A Container's root filesystem resides in one Storage Pool
- A Storage Pool can host multiple Containers
- Mount points may reference different Storage Pools

### Container ↔ Mount Points
- A Container can have 0-256 Mount Points (mp0-mp255)
- Each Mount Point belongs to exactly one Container
- Mount Points are destroyed with Container

### Container ↔ Devices
- A Container can have 0-n Device passthroughs
- Devices are exclusively assigned to one Container
- Devices are released when Container is destroyed

### Node ↔ Storage Pool
- A Node can have multiple Storage Pools
- A Storage Pool may be shared across Nodes
- Pool availability determines container placement

## Configuration File Schema

### YAML Structure
```yaml
# Container configuration file
version: "1.0"
container:
  hostname: dev-container-1
  template: debian-13  # Can be full path or shorthand
  node: pve01  # Optional, prompts if not specified
  resources:
    cores: 2
    memory: 1024  # MB
    storage: 10  # GB
  network:
    bridge: vmbr0
    ip: dhcp  # or "192.168.1.100/24"
    gateway: 192.168.1.1  # Optional for static IP
  features:
    nesting: true
    keyctl: false
  mount_points:
    - host: /srv/data
      container: /data
      read_only: false
  devices:
    - path: /dev/dri/renderD128
      mode: rw
provisioning:
  packages:
    - curl
    - git
    - vim
  docker: true
  tailscale:
    auth_key: ${TAILSCALE_AUTH_KEY}  # From environment
  scripts:
    - name: setup-environment
      content: |
        #!/bin/bash
        echo "Container ready" > /etc/motd
  ssh_keys:
    - ssh-rsa AAAAB3... user@host
```

## State Management

### Stateless Operation
- No local database or state files
- All state queried from Proxmox API
- Configuration files are templates, not state
- VMID allocation handled by Proxmox

### Proxmox as Source of Truth
- Container existence verified via API
- Resource availability checked real-time
- Template availability queried per operation
- Network configuration validated against cluster

### Error Recovery
- Failed creation: No partial containers left
- Failed provisioning: Container marked, can retry
- Network failures: Graceful timeout and retry
- Conflict resolution: Clear error messages

## Performance Characteristics

### Data Size Estimates
- Configuration file: ~1-2 KB per container
- API responses: ~5-10 KB per container listing
- SSH commands: ~100 bytes per command
- Provisioning scripts: ~1-10 KB typical

### Operation Complexity
- Create: O(1) API calls + O(n) provisioning commands
- List: O(1) API call for all containers
- Destroy: O(1) API call
- Template query: O(nodes) API calls

### Caching Strategy
- Node list: Cache for session duration
- Templates: Cache for 5 minutes
- Storage pools: Cache for session
- No persistent cache between runs