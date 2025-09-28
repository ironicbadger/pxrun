# pxrun - Proxmox LXC Lifecycle Management Tool

A CLI tool to simplify LXC container lifecycle management on remote Proxmox clusters.

![create](create.png)

## Features

- **Quick Container Creation**: Create containers with < 6 prompts in under 60 seconds
- **YAML Configuration**: Save and reuse container configurations
- **Secure Credentials**: SOPS encryption for sensitive data
- **Docker Support**: Automatic Docker installation and setup
- **Tailscale Integration**: Built-in VPN configuration and automatic node management
- **Stateless Operation**: Always queries Proxmox for current state
- **Smart Cleanup**: Automatically detects and removes associated Tailscale nodes on container destruction
- ~~**Hardware Acceleration**: Support for device passthrough (Intel QSV)~~ not yet
- ~~**Mount Points**: Easy host directory sharing~~ not yet

## Installation

### Via uv (fastest)

```bash
uv pip install pxrun
```

### Via pip (traditional)

```bash
pip install pxrun
```

### From source

```bash
git clone https://github.com/yourusername/pxrun.git
cd pxrun
# Using uv (recommended, 10-100x faster)
uv pip install -e .
# Or using pip
pip install -e .
```

### Using Docker

```bash
docker pull pxrun:latest
docker run -v ~/.env:/home/pxrun/.env pxrun --help
```

### Shell Completions

Enable command-line auto-completion for your shell:

```bash
# Bash
source <(pxrun completion bash)
# Or add to ~/.bashrc:
echo 'source <(pxrun completion bash)' >> ~/.bashrc

# Zsh
source <(pxrun completion zsh)
# Or add to ~/.zshrc:
echo 'source <(pxrun completion zsh)' >> ~/.zshrc

# Fish
pxrun completion fish | source
# Or add to config:
pxrun completion fish > ~/.config/fish/completions/pxrun.fish
```

## Quick Start

### 1. Configure credentials

```bash
cp .env.example .env
# Edit .env with your Proxmox credentials
```

### 2. Create your first container

```bash
# Interactive mode
pxrun create

# From configuration file
pxrun create -f container.yaml
```

### 3. List containers

```bash
pxrun list
```

### 4. Destroy container

```bash
pxrun destroy <vmid>
# Automatically detects and removes associated Tailscale node

# Skip Tailscale node removal
pxrun destroy <vmid> --no-remove-tailscale-node
```

### 5. Manage Tailscale

```bash
# List nodes in your Tailnet
pxrun tailscale list-nodes
# Show only online nodes
pxrun tailscale list-nodes --online-only
# Output in different formats
pxrun tailscale list-nodes --format json

# Generate auth keys (requires API credentials)
pxrun tailscale generate-key
# Generate reusable key
pxrun tailscale generate-key --reusable --expires 86400
```

## Configuration

### Environment Variables

Create a `.env` file with your Proxmox and Tailscale credentials:

```env
# Proxmox Configuration
PROXMOX_HOST=https://proxmox.example.com:8006
PROXMOX_TOKEN_ID=user@pve!pxrun
PROXMOX_TOKEN_SECRET=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

# Tailscale Configuration (optional)
TAILSCALE_API_KEY=tskey-api-xxxxx    # For auth key generation & node management
TAILSCALE_TAILNET=your-org.ts.net    # Your tailnet domain
TAILSCALE_AUTH_KEY=tskey-auth-xxxxx  # Fallback if API not configured (often expired)
```

### Container Configuration

Example `container.yaml`:

```yaml
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
  mount_points:
    - host: /srv/data
      container: /data
provisioning:
  packages:
    - nginx
    - git
  docker: true
  tailscale: true  # Auto-generates auth key if API configured
  # Or with options:
  # tailscale:
  #   hostname: dev-web-1
  #   ephemeral: false  # Persistent node (default)
```

## Tailscale Integration

pxrun provides deep integration with Tailscale for VPN connectivity and node management.

### Features

- **Automatic Auth Key Generation**: Generates fresh, ephemeral auth keys for each container when API credentials are configured
- **Smart Key Management**: Automatically detects expired keys and generates new ones
- **Persistent vs Ephemeral Nodes**: Configure whether nodes persist across reboots (default: persistent for containers)
- **Automatic Node Detection**: When destroying containers, pxrun automatically detects associated Tailscale nodes
- **Smart Matching**: Matches container hostnames to Tailscale nodes, including FQDN matching
- **Safe Removal**: Prompts for confirmation before removing nodes from your Tailnet
- **Node Management**: List and manage Tailscale nodes directly from pxrun

### Configuration

Set the following environment variables in your `.env` file:

```env
# Recommended: API credentials for automatic auth key generation
TAILSCALE_API_KEY=tskey-api-xxxxx
TAILSCALE_TAILNET=your-org.ts.net

# Optional: Fallback auth key (often expired, API is preferred)
TAILSCALE_AUTH_KEY=tskey-auth-xxxxx
```

With API credentials configured, pxrun will:
- Automatically generate fresh auth keys for each container
- Skip expired keys in your .env file
- Create persistent nodes by default (survive container reboots)

### Usage

```bash
# Create container with Tailscale (auto-generates auth key)
pxrun create --provision tailscale

# Or from YAML with simple config
# tailscale: true  # Uses auto-generated key

# List all Tailscale nodes
pxrun tailscale list-nodes

# Generate auth keys manually
pxrun tailscale generate-key
pxrun tailscale generate-key --reusable --expires 86400

# Destroy container and remove Tailscale node
pxrun destroy 100  # Prompts for Tailscale node removal

# Force destroy without prompts
pxrun destroy 100 --force

# Destroy without removing Tailscale node
pxrun destroy 100 --no-remove-tailscale-node
```

## Development

### Setup development environment

#### Option 1: Using Virtual Environment (Recommended for local development)

```bash
# Clone repository
git clone https://github.com/yourusername/pxrun.git
cd pxrun

# Setup virtual environment automatically
make venv
# Or manually:
./scripts/setup-venv.sh

# Activate virtual environment
source .venv/bin/activate

# Your prompt should now show (.venv)
```

#### Option 2: Using Docker (Recommended for consistent testing)

```bash
# Build test container
make docker-test-build

# Run all tests in Docker
make docker-test

# Run specific test suites
make docker-test-contract     # Contract tests only
make docker-test-integration  # Integration tests only
make docker-test-unit         # Unit tests only

# Interactive shell in test container
make docker-test-shell
```

### Run tests

#### In Virtual Environment

```bash
# Activate virtual environment first
source .venv/bin/activate

# All tests
pytest

# With coverage
pytest --cov=src --cov-report=html

# Specific test types
pytest tests/unit
pytest tests/contract
pytest tests/integration -m "not slow"
```

#### Using Docker (Isolated Environment)

```bash
# Run all tests in Docker container
make docker-test

# Or using docker compose directly
docker compose -f docker-compose.test.yml run --rm test

# Run specific test suites
docker compose -f docker-compose.test.yml run --rm test-contract
docker compose -f docker-compose.test.yml run --rm test-integration
docker compose -f docker-compose.test.yml run --rm test-unit
```

### Code quality

```bash
# Format code
black src tests

# Lint
ruff check src tests

# Type checking
mypy src
```

### Packaging and Distribution

#### Building the Package

```bash
# Build distribution packages
python -m build

# Or using the test script
./scripts/build_test.sh
```

#### Testing Package Installation

```bash
# Test in a virtual environment
python3 -m venv test_env
source test_env/bin/activate
pip install dist/*.whl
pxrun --version
deactivate
```

#### Publishing to PyPI

```bash
# Use the publish script (includes test PyPI option)
./scripts/publish.sh

# Or manually:
# 1. Build the package
python -m build

# 2. Check package quality
twine check dist/*

# 3. Upload to Test PyPI first (optional)
twine upload --repository testpypi dist/*

# 4. Upload to PyPI
twine upload dist/*
```

#### Docker Image

```bash
# Build Docker image
docker build -t pxrun:latest .

# Test the image
docker run --rm pxrun:latest --version
docker run --rm -v ~/.env:/home/pxrun/.env pxrun:latest list

# Push to registry
docker tag pxrun:latest yourusername/pxrun:latest
docker push yourusername/pxrun:latest
```

## Documentation

Full documentation available at [https://pxrun.readthedocs.io](https://pxrun.readthedocs.io)

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Requirements

- Python 3.11+
- Proxmox VE 9.x
- SSH access to at least one Proxmox node

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- 📚 [Documentation](https://pxrun.readthedocs.io)
- 🐛 [Issue Tracker](https://github.com/yourusername/pxrun/issues)
- 💬 [Discussions](https://github.com/yourusername/pxrun/discussions)

## Acknowledgments

- Built with [Click](https://click.palletsprojects.com/) for CLI interface
- Uses [proxmoxer](https://github.com/proxmoxer/proxmoxer) for API integration
- Inspired by the need for simpler container management