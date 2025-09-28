# pxrun Quick Start Guide

## Current Status: MVP Working! 🎉

The tool is now functional and connects to your Proxmox server at px.wd.ktz.me.

## Setup (Already Done)

Your `.env` file is already configured with:
- Proxmox host: px.wd.ktz.me (via reverse proxy on port 443)
- API token authentication
- Default storage pool: nvmeu2-vmstore

## Basic Usage

Since the package isn't installed yet, run commands using Python:

```bash
# Use python3 -m src.cli instead of pxrun
python3 -m src.cli [command]
```

## Commands

### 1. List Containers

```bash
# Show all containers in a nice table
python3 -m src.cli list

# Filter by node
python3 -m src.cli list --node c137
python3 -m src.cli list --node ms01

# Filter by status
python3 -m src.cli list --status running
python3 -m src.cli list --status stopped

# Different output formats
python3 -m src.cli list --format json
python3 -m src.cli list --format yaml
```

### 2. Create a Container

#### Interactive Mode (Easiest)

```bash
python3 -m src.cli create
```

This will prompt you for:
1. Container hostname
2. Template selection (from available templates)
3. Node selection (or auto-select least loaded)
4. Storage pool
5. Resources (CPU, Memory, Storage)
6. Network configuration (DHCP or static IP)
7. SSH key (optional)
8. Provisioning options (optional)

#### With Command Line Options

```bash
# Create with specific options
python3 -m src.cli create \
  --hostname mytest \
  --cores 2 \
  --memory 2048 \
  --storage 10 \
  --ip dhcp
```

#### From Configuration File

First, save a container config:
```bash
# Export existing container config
python3 -m src.cli save-config 120 -o mycontainer.yaml
```

Then create from it:
```bash
python3 -m src.cli create --config mycontainer.yaml
```

### 3. Destroy a Container

```bash
# With confirmation prompt
python3 -m src.cli destroy 120

# Force without confirmation
python3 -m src.cli destroy 120 --force
```

### 4. Export Container Configuration

```bash
# Save to file with container hostname
python3 -m src.cli save-config 120

# Save to specific file
python3 -m src.cli save-config 120 -o myconfig.yaml
```

## Example: Create a Test Container

Here's a complete example to create a test container:

```bash
# 1. List available templates and nodes
python3 -m src.cli list

# 2. Create container interactively
python3 -m src.cli create

# Example inputs:
#   Hostname: test-container
#   Template: Select Debian or Alpine (small)
#   Node: Let it auto-select or choose
#   Cores: 1
#   Memory: 512
#   Storage: 8
#   Network: dhcp
#   SSH key: Skip or add yours
#   Provisioning: Skip for now

# 3. Check it was created
python3 -m src.cli list

# 4. Clean up when done
python3 -m src.cli destroy <vmid>
```

## Container Configuration File Format

Example `container.yaml`:

```yaml
version: "1.0"
container:
  hostname: dev-container
  template: debian-13  # or full path
  node: c137  # optional, will auto-select if not specified
  resources:
    cores: 2
    memory: 1024  # MB
    storage: 10   # GB
    storage_pool: nvmeu2-vmstore
  network:
    bridge: vmbr0
    ip: dhcp  # or "192.168.1.100/24"
    gateway: 192.168.1.1  # for static IP
  features:
    nesting: true  # Enable for Docker
provisioning:
  packages:
    - curl
    - git
    - vim
  docker: true
  ssh_keys:
    - ssh-rsa AAAAB3... user@host
```

## Tips

1. **Templates**: Your server has several templates available. Alpine is smallest/fastest for testing.

2. **Nodes**: You have two nodes:
   - `ms01` - Less loaded, good for small containers
   - `c137` - More powerful, good for larger workloads

3. **Storage**: Default pool is `nvmeu2-vmstore` which appears to be NVMe storage

4. **Debugging**: Add `--debug` flag for verbose output:
   ```bash
   python3 -m src.cli --debug list
   ```

## Current Limitations

- Provisioning via SSH requires containers to have static IPs (DHCP containers can't be provisioned yet)
- Default root password for LXC containers needs to be set manually after creation
- Mount points and device passthrough need to be added via Proxmox UI for now

## Troubleshooting

If you see SSL warnings, they're harmless (cert verification is disabled in .env).

If connection fails:
1. Check your internet connection
2. Verify px.wd.ktz.me is accessible
3. Check the API token hasn't expired

## Next Steps

To make it easier to use:

```bash
# Create an alias
alias pxrun='python3 -m src.cli'

# Then use:
pxrun list
pxrun create
# etc.
```

Or properly install it:

```bash
# In the project directory
pip3 install -e .

# Then use directly:
pxrun list
```