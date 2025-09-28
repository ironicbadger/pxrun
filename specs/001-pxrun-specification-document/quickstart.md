# pxrun Quickstart Guide

## Installation

```bash
# Install via pip
pip install pxrun

# Or install from source
git clone https://github.com/yourusername/pxrun.git
cd pxrun
pip install -e .
```

## Initial Setup

### 1. Configure Proxmox Credentials

```bash
# Set up API token (recommended)
export PROXMOX_HOST="https://proxmox.example.com:8006"
export PROXMOX_TOKEN_ID="user@pve!pxrun"
export PROXMOX_TOKEN_SECRET="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

# Or use password authentication
export PROXMOX_USER="user@pve"
export PROXMOX_PASSWORD="your-password"
```

### 2. Configure SSH Access

```bash
# Add Proxmox node to SSH config
cat >> ~/.ssh/config <<EOF
Host pve01
    Hostname proxmox1.example.com
    User root
    IdentityFile ~/.ssh/proxmox_key
EOF

# Test SSH connection
ssh pve01 "pct list"
```

## Basic Usage

### Create Your First Container (Interactive)

```bash
# Run pxrun in interactive mode
pxrun create

# You'll be prompted for:
# 1. Container hostname: dev-test-1
# 2. Select node: pve01
# 3. Select template: debian-13
# 4. CPU cores [2]: <enter>
# 5. Memory MB [1024]: <enter>
# 6. Storage GB [10]: <enter>

# Output:
# ✓ Container created: 101
# ✓ Provisioning completed
#
# Connection details:
# SSH: ssh root@192.168.1.101
# Console: ssh pve01 "pct console 101"
```

### Create Container from Config File

```bash
# Create a configuration file
cat > dev-container.yaml <<EOF
version: "1.0"
container:
  hostname: dev-web-1
  template: debian-13
  resources:
    cores: 4
    memory: 2048
    storage: 20
  network:
    ip: dhcp
provisioning:
  packages:
    - nginx
    - git
  docker: true
EOF

# Create container from config
pxrun create -f dev-container.yaml

# With overrides
pxrun create -f dev-container.yaml --node pve02 --cores 8
```

### List Containers

```bash
# List all containers
pxrun list

# Output:
# VMID  HOSTNAME     NODE   STATUS   CPU    MEMORY      UPTIME
# 101   dev-test-1   pve01  running  0.5%   512M/1024M  2h 15m
# 102   dev-web-1    pve01  running  1.2%   1024M/2048M 45m

# JSON output
pxrun list --format json

# Filter by node
pxrun list --node pve01
```

### Destroy Container

```bash
# Destroy by VMID
pxrun destroy 101

# Confirm: Destroy container 101 (dev-test-1)? [y/N]: y
# ✓ Container 101 destroyed

# Skip confirmation
pxrun destroy 101 --yes

# Force destroy (even if running)
pxrun destroy 101 --force --yes
```

## Advanced Features

### Hardware Acceleration

```yaml
# Enable Intel QSV for media processing
container:
  hostname: media-processor
  features:
    nesting: true
  devices:
    - path: /dev/dri/renderD128
      mode: rw
```

### Mount Points

```yaml
# Share directories with container
container:
  mount_points:
    - host: /srv/data
      container: /data
      read_only: false
    - host: /home/user/code
      container: /workspace
      read_only: false
```

### Tailscale Integration

```bash
# Set Tailscale auth key
export TAILSCALE_AUTH_KEY="tskey-auth-..."

# Configure in YAML
cat > tailscale-container.yaml <<EOF
container:
  hostname: dev-vpn-1
provisioning:
  tailscale:
    auth_key: \${TAILSCALE_AUTH_KEY}
    accept_routes: true
EOF

pxrun create -f tailscale-container.yaml
```

### Docker Installation

```yaml
# Automatic Docker setup
provisioning:
  docker: true
  scripts:
    - name: docker-compose
      content: |
        curl -L https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 -o /usr/local/bin/docker-compose
        chmod +x /usr/local/bin/docker-compose
```

### Custom Provisioning

```yaml
# Run custom setup scripts
provisioning:
  scripts:
    - name: setup-dev-environment
      content: |
        #!/bin/bash
        # Install development tools
        apt-get update
        apt-get install -y build-essential python3-pip nodejs npm

        # Setup project
        git clone https://github.com/myproject/repo.git /app
        cd /app
        npm install
      timeout: 600
```

## Testing Workflow

### Scenario 1: Quick Development Container

```bash
# Create a temporary dev container
pxrun create --hostname dev-quick --template debian-13

# Work in container
ssh root@<container-ip>

# Destroy when done
pxrun destroy <vmid> --yes
```

### Scenario 2: Reproducible Test Environment

```bash
# Save configuration after creating
pxrun create --hostname test-env-1
pxrun save-config <vmid> -o test-env.yaml

# Create identical containers
pxrun create -f test-env.yaml --hostname test-env-2
pxrun create -f test-env.yaml --hostname test-env-3
```

### Scenario 3: CI/CD Integration

```bash
#!/bin/bash
# ci-test.sh

# Create test container
VMID=$(pxrun create -f ci-container.yaml --json | jq -r .vmid)

# Run tests
ssh root@$(pxrun list --vmid $VMID --json | jq -r .ip) "cd /app && npm test"

# Cleanup
pxrun destroy $VMID --yes
```

## Troubleshooting

### Connection Issues

```bash
# Test Proxmox API connection
pxrun test-connection

# Verbose output
pxrun create -v

# Debug SSH provisioning
pxrun create --debug
```

### Common Errors

**"Template not found"**
```bash
# List available templates
pxrun templates --node pve01

# Download template on Proxmox node
ssh pve01 "pveam download local debian-13-standard_13.0-1_amd64.tar.zst"
```

**"Insufficient resources"**
```bash
# Check node resources
pxrun nodes --details

# Use different node
pxrun create --node pve02
```

**"VMID already exists"**
```bash
# Let pxrun auto-allocate VMID
pxrun create  # Don't specify --vmid
```

## Best Practices

### 1. Use Configuration Files
- Store container configs in version control
- Use environment variables for secrets
- Create templates for common patterns

### 2. Resource Management
- Start with minimal resources (2 CPU, 1GB RAM)
- Monitor actual usage with `pxrun list`
- Scale up only when needed

### 3. Security
- Always use API tokens over passwords
- Encrypt sensitive data with SOPS
- Use unprivileged containers when possible
- Limit mount points to necessary directories

### 4. Naming Conventions
```yaml
# Use descriptive hostnames
hostname: dev-webapp-nodejs-01
hostname: test-db-postgres-01
hostname: ci-runner-01
```

## Complete Example

```bash
# 1. Setup project configuration
cat > project.yaml <<EOF
version: "1.0"
container:
  hostname: myapp-dev
  template: debian-13
  resources:
    cores: 4
    memory: 4096
    storage: 50
  network:
    ip: dhcp
  mount_points:
    - host: /srv/projects/myapp
      container: /app
  features:
    nesting: true
provisioning:
  packages:
    - curl
    - git
    - build-essential
  docker: true
  scripts:
    - name: setup-app
      content: |
        #!/bin/bash
        cd /app
        docker-compose up -d
  ssh_keys:
    - ssh-rsa AAAAB3... developer@laptop
EOF

# 2. Create development container
pxrun create -f project.yaml

# 3. Get connection details
pxrun list --hostname myapp-dev

# 4. Connect and work
ssh root@192.168.1.105

# 5. Save state before destroying
pxrun save-config 105 -o myapp-dev-final.yaml

# 6. Cleanup
pxrun destroy 105 --yes
```

## Next Steps

- Read the full documentation: `pxrun --help`
- Explore configuration options: `pxrun create --help`
- Check examples: `/usr/share/doc/pxrun/examples/`
- Join the community: https://github.com/yourusername/pxrun/discussions