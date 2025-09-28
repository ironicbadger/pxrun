# Research Findings: pxrun Implementation

**Generated**: 2025-09-27
**Phase**: 0 - Technical Research & Decisions

## Executive Summary
Research conducted to resolve technical implementation decisions for the pxrun CLI tool, focusing on Proxmox API integration, SSH-based provisioning, and Python ecosystem choices.

## Key Technical Decisions

### 1. Proxmox API Client Library
**Decision**: proxmoxer library
**Rationale**:
- Most mature and actively maintained Python library for Proxmox API
- Supports Proxmox VE 9.x API endpoints
- Supports both API token and password authentication
- Well-documented with extensive community usage
**Alternatives considered**:
- Direct HTTP requests: Too low-level, would require reimplementing auth handling
- pypve: Less maintained, fewer features
- Custom wrapper: Unnecessary given proxmoxer's maturity

### 2. SSH Implementation for Provisioning
**Decision**: paramiko library for SSH operations
**Rationale**:
- Pure Python implementation (no system SSH dependencies)
- Robust connection pooling and error handling
- Supports key-based and password authentication
- Can execute commands with proper stdin/stdout/stderr capture
**Alternatives considered**:
- subprocess + system SSH: Platform-dependent, harder to control
- fabric: Too heavyweight for simple command execution
- asyncssh: Unnecessary complexity for synchronous CLI tool

### 3. Configuration File Format
**Decision**: YAML with PyYAML library
**Rationale**:
- Human-readable and editable
- Native support for complex data structures
- Industry standard for configuration files
- Clean indentation-based syntax
**Alternatives considered**:
- JSON: Less readable, no comments support
- TOML: Less familiar to most users
- INI: Too limited for nested structures

### 4. Credential Encryption
**Decision**: SOPS (Secrets OPerationS) with age encryption
**Rationale**:
- Designed specifically for encrypting config files
- Supports selective encryption (only encrypts secret values)
- Git-friendly (produces readable diffs)
- age is simpler than GPG while maintaining security
**Alternatives considered**:
- ansible-vault: Requires Ansible ecosystem
- GPG direct: Complex key management
- Keyring library: Platform-dependent storage

### 5. CLI Framework
**Decision**: Click framework
**Rationale**:
- Declarative command structure
- Built-in help generation
- Excellent prompt support for interactive mode
- Parameter validation and type conversion
- Supports command groups for future expansion
**Alternatives considered**:
- argparse: More verbose, less features
- typer: Less mature, fewer prompt features
- fire: Too magic, less explicit

### 6. Container ID Management
**Decision**: Query Proxmox for next available VMID
**Rationale**:
- Avoids race conditions with static allocation
- Proxmox API provides atomic VMID allocation
- No local state required (stateless operation)
**Alternatives considered**:
- Local counter file: Race conditions with multiple users
- UUID generation: Not compatible with Proxmox VMID format
- User-specified: Too error-prone

### 7. Template Discovery
**Decision**: Dynamic query of available templates per node
**Rationale**:
- Templates may vary between nodes
- Avoids hardcoding template names
- Provides real-time availability
- Can show download status if template missing
**Alternatives considered**:
- Static template list: Would become outdated
- Configuration file: Maintenance burden
- Proxmox template API: Limited, node-specific query better

### 8. Mount Point Syntax
**Decision**: Proxmox native syntax (mp0=/host/path,/container/path)
**Rationale**:
- Direct pass-through to Proxmox API
- No translation layer needed
- Users can reference Proxmox documentation
- Supports all mount options
**Alternatives considered**:
- Docker-style (-v host:container): Would require translation
- Custom YAML structure: Adds complexity
- Separate host/container fields: Less flexible

### 9. Hardware Device Access
**Decision**: Device path configuration with automatic major/minor lookup
**Rationale**:
- Proxmox requires major/minor numbers for device passthrough
- Tool can query these from /dev on Proxmox node via SSH
- Simplifies user input (just provide /dev/dri/renderD128)
**Alternatives considered**:
- Manual major/minor input: Too technical for users
- Preset device profiles: Too limiting
- Container capabilities only: Insufficient for hardware access

### 10. Error Handling Strategy
**Decision**: Fail-fast with detailed error messages
**Rationale**:
- Clear indication of what went wrong
- No partial container creation
- Includes recovery suggestions
- Preserves configuration for retry
**Alternatives considered**:
- Retry with backoff: Could hide underlying issues
- Partial success: Leaves system in unclear state
- Silent fallback: Unexpected behavior

## Proxmox API Limitations Discovered

### Critical Finding: No Direct Container Exec API
**Issue**: Proxmox API does not provide container command execution endpoint for API tokens
**Details**:
- `/nodes/{node}/lxc/{vmid}/exec` endpoint does not exist
- `/nodes/{node}/execute` requires root@pam authentication (not API tokens)
- No cloud-init support for LXC containers (only VMs)

**Solution**: SSH to Proxmox node and use `pct exec` command
- Requires SSH access to at least one cluster node
- Uses `pct exec <vmid> -- <command>` for container provisioning
- Maintains security through SSH key authentication

## Python Package Dependencies

### Core Dependencies
```
proxmoxer==2.0.1       # Proxmox API client
paramiko==3.3.1        # SSH client library
PyYAML==6.0.1          # YAML parsing
click==8.1.7           # CLI framework
sops==3.8.1            # Secret encryption
python-dotenv==1.0.0   # Environment variable loading
```

### Development Dependencies
```
pytest==7.4.3          # Testing framework
pytest-mock==3.12.0    # Mock fixtures
pytest-cov==4.1.0      # Coverage reporting
black==23.12.0         # Code formatting
ruff==0.1.9            # Linting
mypy==1.7.1            # Type checking
```

## Performance Considerations

### API Call Optimization
- Batch container listings in single API call
- Cache node information for session duration
- Minimize API calls during interactive prompts
- Use API filters where available

### SSH Connection Management
- Reuse SSH connections for multiple commands
- Implement connection pooling for provisioning
- Set reasonable timeout values (30s default)
- Handle high-latency connections gracefully

### Local Operation Performance
- Lazy import of heavy dependencies
- Minimize startup time (< 100ms target)
- Efficient YAML parsing for large configs
- In-memory config caching during session

## Security Best Practices

### Credential Handling
- Never log credentials or tokens
- Use SOPS for at-rest encryption
- Support environment variables for CI/CD
- Implement secure prompt for sensitive input
- Clear credentials from memory after use

### SSH Security
- Prefer key-based authentication
- Verify host keys on first connection
- Support SSH config file settings
- Disable agent forwarding by default

### API Token Permissions
- Document minimum required permissions
- Support read-only operations with limited tokens
- Validate token permissions on startup
- Provide clear permission error messages

## Testing Strategy

### Unit Testing
- Mock all external dependencies (API, SSH)
- Test configuration parsing and validation
- Test error handling paths
- Achieve 80%+ code coverage

### Integration Testing
- Test against Proxmox test cluster
- Verify container lifecycle operations
- Test provisioning script execution
- Validate network connectivity

### Contract Testing
- Verify Proxmox API response schemas
- Test API error responses
- Validate SSH command outputs
- Ensure backwards compatibility

## Future Considerations

### Potential Enhancements
- Async operations for parallel container creation
- Template management (download, update)
- Container migration between nodes
- Resource usage monitoring
- Backup/restore functionality

### Scalability Planning
- Connection pooling for multiple operations
- Bulk operations support
- Progress indicators for long operations
- Queueing system for large deployments

## Conclusion
All technical decisions have been researched and resolved. The implementation can proceed with Python 3.11+, using established libraries for Proxmox API interaction, SSH provisioning, and CLI construction. The SSH-based provisioning approach successfully works around Proxmox API limitations while maintaining security and reliability.