# Feature Specification: pxrun - Proxmox LXC Lifecycle Management Tool

**Feature Branch**: `001-pxrun-specification-document`
**Created**: 2025-09-27
**Status**: Draft
**Input**: User description: "pxrun - Specification Document"

## Execution Flow (main)
```
1. Parse user description from Input
   → Tool to simplify LXC container lifecycle management on remote Proxmox cluster
2. Extract key concepts from description
   → Identified: developer users, LXC containers, Proxmox cluster, interactive/declarative modes
3. For each unclear aspect:
   → Marked critical decision points requiring clarification
4. Fill User Scenarios & Testing section
   → Three primary user stories identified with acceptance criteria
5. Generate Functional Requirements
   → Requirements organized by category (core, config, provisioning, operational)
6. Identify Key Entities
   → Container configuration, templates, cluster nodes, storage pools
7. Run Review Checklist
   → Multiple clarifications needed on technical decisions
8. Return: SUCCESS (spec ready for planning phase)
```

## Clarifications

### Session 2025-09-27

- Q: Which UI paradigm for SSH-based usage? → A: Sequential inline prompts (SSH-friendly)
- Q: Configuration management approach? → A: Individual YAML files per container
- Q: Container provisioning method? → A: SSH-based provisioning via Proxmox node
- Q: Default container resources? → A: 2 cores, 1GB memory, 10GB storage
- Q: Node selection strategy? → A: User selects from list with --node flag override

---

## ⚡ Quick Guidelines
- ✅ Focus on WHAT users need and WHY
- ❌ Avoid HOW to implement (no tech stack, APIs, code structure)
- 👥 Written for business stakeholders, not developers

---

## User Scenarios & Testing

### Primary User Story
A developer working from their laptop needs to quickly create temporary LXC containers on a remote Proxmox cluster for testing purposes. They want to reduce the complexity from multiple manual steps to a single command, with the ability to save and reuse configurations for common development patterns.

### Acceptance Scenarios

1. **Given** a developer with access to a Proxmox cluster, **When** they run the tool for the first time, **Then** they can create a basic Debian container with minimal inputs (< 6 prompts) in under 2 minutes

2. **Given** a developer has created a container configuration, **When** they want to create similar containers, **Then** they can save the configuration to YAML and reuse it with optional overrides

3. **Given** a developer needs hardware acceleration for media processing, **When** they create a container, **Then** they can enable QSV/hardware access with proper device permissions automatically configured

4. **Given** a developer has finished testing, **When** they want to clean up, **Then** they can destroy containers by ID with a single command

5. **Given** a developer accesses Proxmox via HTTPS reverse proxy, **When** they use the tool, **Then** all operations work correctly over high-latency connections

### Edge Cases
- What happens when the Proxmox API is unavailable or times out?
- How does system handle when requested resources exceed cluster capacity?
- What occurs when multiple users try to allocate the same VMID simultaneously?
- How does the tool behave when network provisioning commands fail inside the container?
- What happens when a template is not available on the selected node?

## Requirements

### Functional Requirements

#### Core Container Management
- **FR-001**: System MUST allow users to create LXC containers on remote Proxmox clusters
- **FR-002**: System MUST allow users to destroy LXC containers by container ID
- **FR-003**: System MUST list existing containers for user selection
- **FR-004**: System MUST display available templates from the cluster
- **FR-005**: System MUST support operation across multi-node clusters (minimum 2 nodes)

#### Configuration & Reproducibility
- **FR-006**: System MUST allow saving container configurations to YAML format
- **FR-007**: System MUST allow loading configurations from saved YAML files
- **FR-008**: System MUST allow overriding specific configuration values when loading from YAML
- **FR-009**: System MUST provide sensible defaults for all optional parameters
- **FR-010**: System MUST use individual YAML configuration files for each container configuration

#### Container Provisioning
- **FR-011**: System MUST support automatic provisioning of common development tools
- **FR-012**: System MUST handle Docker installation in containers
- **FR-013**: System MUST handle Tailscale installation with authentication key support
- **FR-014**: System MUST support hardware acceleration enablement (QSV/device passthrough)
- **FR-015**: System MUST configure mount points for host directory access
- **FR-016**: System MUST provision containers via SSH connection to Proxmox node using pct exec commands

#### Operational Requirements
- **FR-017**: System MUST complete basic container creation in < 60 seconds (excluding template download)
- **FR-018**: System MUST require < 6 user inputs for basic container creation
- **FR-019**: System MUST work reliably over HTTPS reverse proxy connections
- **FR-020**: System MUST handle high-latency network connections gracefully
- **FR-021**: System MUST remain stateless, querying Proxmox for current state
- **FR-022**: System MUST provide dry-run capability for operations
- **FR-023**: System MUST validate all inputs before making API calls
- **FR-024**: System MUST provide clear, actionable error messages
- **FR-025**: System MUST display connection information clearly after container creation

#### Security Requirements
- **FR-026**: System MUST support API token authentication (preferred over passwords)
- **FR-027**: System MUST NOT store credentials in configuration files (use environment variables)
- **FR-028**: System MUST NOT expose credentials in process arguments or logs
- **FR-029**: System MUST handle authentication token refresh appropriately

#### User Interface Requirements
- **FR-030**: System MUST use sequential inline prompts for user interaction (SSH-compatible)
- **FR-031**: System MUST maintain < 200ms response time for local operations
- **FR-032**: System MUST provide copy-paste friendly output for connection details
- **FR-033**: System MUST document mount point syntax clearly
- **FR-034**: System MUST use default resources of 2 CPU cores, 1GB memory, and 10GB storage when not specified
- **FR-035**: System MUST prompt user to select target node from available nodes, with optional --node flag for override

### Key Entities

- **Container Configuration**: Represents all settings needed to create an LXC container including resources (CPU, memory, storage), network settings, mount points, and provisioning scripts

- **Container Template**: Pre-built OS images available on Proxmox nodes that serve as the base for new containers (e.g., Debian 13, Ubuntu 24.04)

- **Cluster Node**: Individual Proxmox server in the cluster where containers can be created and run

- **Storage Pool**: Named storage location on cluster nodes where container root filesystems and data are stored

- **Mount Point**: Mapping between host directories and container paths for shared file access

- **Provisioning Script**: Commands or scripts executed after container creation to install software and configure the environment

---

## Resolved Decisions

### 1. User Interface Paradigm
**Decision**: Sequential inline prompts
**Rationale**: Ensures excellent SSH compatibility and keeps implementation simple, which is critical for the primary use case of remote management from developer laptops.

### 2. Configuration Management Strategy
**Decision**: Individual YAML files per container
**Rationale**: Provides a simple mental model that's easy to understand, share, and version control. Each configuration is self-contained without complex inheritance chains.

### 3. Provisioning Method
**Decision**: SSH-based provisioning via Proxmox node
**Rationale**: Given Proxmox API limitations (no direct exec endpoint for LXC), SSH to the node and using pct exec commands provides the most reliable provisioning path.

### 4. Default Resources
**Decision**: 2 CPU cores, 1GB memory, 10GB storage
**Rationale**: Conservative defaults that work for most development scenarios without overwhelming cluster resources.

### 5. Node Selection
**Decision**: User selection with --node flag override
**Rationale**: Gives users control over placement while allowing automation via command-line flag when needed.

### 6. Scope Boundaries
**Decision**: Focus on core create/destroy operations
**Rationale**: Maintain tool focus on the "spin up and tear down" workflow. Additional features (start/stop, status display, config export, resource modification) are deferred to keep initial implementation focused.

---

## Review & Acceptance Checklist

### Content Quality
- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

### Requirement Completeness
- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

---

## Execution Status

- [x] User description parsed
- [x] Key concepts extracted
- [x] Ambiguities marked
- [x] User scenarios defined
- [x] Requirements generated
- [x] Entities identified
- [x] Review checklist passed

---

## Next Steps

All critical decisions have been resolved and the specification is now complete. The project is ready to proceed to the `/plan` phase for technical design and implementation planning.

**Recommended next command**: `/plan`