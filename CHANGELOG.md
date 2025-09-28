# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Tailscale Subcommand Group**: Reorganized Tailscale commands under `pxrun tailscale` for better organization
  - `pxrun tailscale list-nodes` - List nodes in your Tailnet
  - `pxrun tailscale generate-key` - Generate auth keys programmatically
  - `pxrun tailscale refresh` - Quick refresh of local Tailscale connection
- **Automatic Auth Key Generation**: Automatically generates fresh Tailscale auth keys when API credentials are configured
  - Detects expired keys and generates new ones
  - Each container gets its own unique auth key
  - No more manual key management
- **Persistent vs Ephemeral Nodes**: Configure whether Tailscale nodes persist across container reboots
  - Default: persistent (nodes survive reboots)
  - Configurable via `ephemeral: true/false` in YAML
- **Enhanced YAML Configuration**: Simplified Tailscale configuration in container YAML files
  - Simple: `tailscale: true` for automatic setup
  - Advanced: Configure hostname, ephemeral status, and routing options
- **Beautiful Terminal UI**: Complete overhaul of command output using Rich library
  - Real-time streaming output for Docker and Tailscale installation
  - Progress indicators showing [step/total] for each provisioning phase
  - Clean, contained panels with 80-column width for better readability
  - Live output windows showing last 8 lines of command execution
  - Indented task lists showing what will be installed
  - Consistent green checkmarks for successful operations
  - Tailscale connection info (FQDN and IP) displayed after provisioning
- **Improved Provisioning Feedback**: Clear visual feedback during container setup
  - Shows number of steps upfront (e.g., "Starting container provisioning (3 steps)")
  - Lists all tasks that will be performed as bullet points
  - Real-time progress for package installation, Docker setup, and Tailscale configuration
  - Transient displays that disappear after completion to keep output clean

### Changed
- **Command Structure**: `pxrun list-tailscale-nodes` is now `pxrun tailscale list-nodes`
- **Default Behavior**: Tailscale nodes are now persistent by default (previously ephemeral)
- **Auth Key Priority**: When API credentials are available, always generates fresh keys instead of using potentially expired ones from environment
- **Package Manager**: Switched from `apt-get` to `apt` for all Debian/Ubuntu operations (modern best practice)

### Fixed
- **Expired Auth Keys**: System now automatically detects and replaces expired auth keys
- **Key Description Validation**: Fixed "invalid characters" error when generating auth keys
- **Container Name Sanitization**: Properly sanitizes container names for Tailscale API compatibility
- **SSH Locale Errors**: Fixed locale configuration issues that caused SSH warnings on first login
  - Containers now automatically configure `en_US.UTF-8` locale during creation
  - Properly sets `/etc/default/locale` using Debian's `update-locale` tool
  - Eliminates "setlocale: LC_CTYPE: cannot change locale" warnings
- **Live Display Conflicts**: Resolved "Only one live display may be active at once" errors
  - Fixed nested spinner conflicts during provisioning
  - Properly handles concurrent Live displays for streaming output
- **Output Formatting**: Cleaned up unnecessary line gaps in terminal output
- **Duplicate Tailscale Checks**: Fixed duplicate node checking in destroy command
- **500 Errors**: Suppressed harmless 500 errors when checking container info immediately after creation

### Documentation
- Updated README with new Tailscale features and configuration options
- Updated QUICKSTART guide with auth key generation examples
- Added comprehensive examples for YAML configuration options

## [0.1.0] - Previous Release

### Initial Features
- Container lifecycle management (create, list, destroy)
- Proxmox API integration
- Basic Tailscale support
- YAML configuration support
- SSH provisioning
- Docker installation support