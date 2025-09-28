# pxrun - Proxmox LXC Lifecycle Management Tool

[![CI/CD Pipeline](https://github.com/yourusername/pxrun/actions/workflows/ci.yml/badge.svg)](https://github.com/yourusername/pxrun/actions/workflows/ci.yml)
[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A CLI tool to simplify LXC container lifecycle management on remote Proxmox clusters.

## Features

- 🚀 **Quick Container Creation**: Create containers with < 6 prompts in under 60 seconds
- 📝 **YAML Configuration**: Save and reuse container configurations
- 🔒 **Secure Credentials**: SOPS encryption for sensitive data
- 🐳 **Docker Support**: Automatic Docker installation and setup
- 🔗 **Tailscale Integration**: Built-in VPN configuration
- 🎮 **Hardware Acceleration**: Support for device passthrough (Intel QSV)
- 📁 **Mount Points**: Easy host directory sharing
- 🔄 **Stateless Operation**: Always queries Proxmox for current state

## Installation

### Via pip

```bash
pip install pxrun
```

### From source

```bash
git clone https://github.com/yourusername/pxrun.git
cd pxrun
pip install -e .
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
```

## Configuration

### Environment Variables

Create a `.env` file with your Proxmox credentials:

```env
PROXMOX_HOST=https://proxmox.example.com:8006
PROXMOX_TOKEN_ID=user@pve!pxrun
PROXMOX_TOKEN_SECRET=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
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
```

## Development

### Setup development environment

```bash
# Clone repository
git clone https://github.com/yourusername/pxrun.git
cd pxrun

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -r requirements-dev.txt
pip install -e .
```

### Run tests

```bash
# All tests
pytest

# With coverage
pytest --cov=src --cov-report=html

# Specific test types
pytest tests/unit
pytest tests/integration -m "not slow"
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