
# Implementation Plan: pxrun - Proxmox LXC Lifecycle Management Tool

**Branch**: `001-pxrun-specification-document` | **Date**: 2025-09-27 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-pxrun-specification-document/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path
   → If not found: ERROR "No feature spec at {path}"
2. Fill Technical Context (scan for NEEDS CLARIFICATION)
   → Detect Project Type from file system structure or context (web=frontend+backend, mobile=app+api)
   → Set Structure Decision based on project type
3. Fill the Constitution Check section based on the content of the constitution document.
4. Evaluate Constitution Check section below
   → If violations exist: Document in Complexity Tracking
   → If no justification possible: ERROR "Simplify approach first"
   → Update Progress Tracking: Initial Constitution Check
5. Execute Phase 0 → research.md
   → If NEEDS CLARIFICATION remain: ERROR "Resolve unknowns"
6. Execute Phase 1 → contracts, data-model.md, quickstart.md, agent-specific template file (e.g., `CLAUDE.md` for Claude Code, `.github/copilot-instructions.md` for GitHub Copilot, `GEMINI.md` for Gemini CLI, `QWEN.md` for Qwen Code or `AGENTS.md` for opencode).
7. Re-evaluate Constitution Check section
   → If new violations: Refactor design, return to Phase 1
   → Update Progress Tracking: Post-Design Constitution Check
8. Plan Phase 2 → Describe task generation approach (DO NOT create tasks.md)
9. STOP - Ready for /tasks command
```

**IMPORTANT**: The /plan command STOPS at step 7. Phases 2-4 are executed by other commands:
- Phase 2: /tasks command creates tasks.md
- Phase 3-4: Implementation execution (manual or via tools)

## Summary
A CLI tool to simplify LXC container lifecycle management on remote Proxmox clusters, reducing container creation from multiple manual steps to a single command with YAML-based configuration reproducibility. The tool uses SSH-based provisioning via Proxmox nodes to work around API limitations.

## Technical Context
**Language/Version**: Python 3.11+ (preferred for Proxmox API integration)
**Primary Dependencies**: proxmoxer (Proxmox API), PyYAML, SOPS, paramiko (SSH), click (CLI)
**Storage**: YAML configuration files (individual per container), SOPS-encrypted credentials
**Testing**: pytest with mock Proxmox API responses
**Target Platform**: Linux/macOS developer machines (client), Proxmox VE 9.x clusters (server)
**Project Type**: single - CLI tool
**Performance Goals**: < 60 seconds container creation, < 200ms local operations
**Constraints**: < 6 user prompts for basic creation, SSH-compatible UI, stateless operation
**Scale/Scope**: Single-user CLI, managing 10-50 containers per developer

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Note**: Constitution file contains only placeholder template. Proceeding with standard best practices:
- [x] Single-purpose tool principle: PASS - Tool focuses solely on LXC lifecycle management
- [x] CLI-first design: PASS - Sequential inline prompts for SSH compatibility
- [x] Test coverage requirement: Will implement pytest suite with mocked API calls
- [x] Documentation completeness: Will provide comprehensive CLI docs and quickstart
- [x] Security considerations: PASS - SOPS encryption for credentials, no credential exposure

## Project Structure

### Documentation (this feature)
```
specs/[###-feature]/
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output (/plan command)
├── data-model.md        # Phase 1 output (/plan command)
├── quickstart.md        # Phase 1 output (/plan command)
├── contracts/           # Phase 1 output (/plan command)
└── tasks.md             # Phase 2 output (/tasks command - NOT created by /plan)
```

### Source Code (repository root)
```
src/
├── models/
│   ├── container.py      # Container configuration model
│   ├── cluster.py        # Cluster and node models
│   └── template.py       # Template management
├── services/
│   ├── proxmox.py        # Proxmox API client wrapper
│   ├── ssh_provisioner.py # SSH-based container provisioning
│   ├── config_manager.py  # YAML configuration handling
│   └── credentials.py     # SOPS credential management
├── cli/
│   ├── __main__.py       # Entry point
│   ├── commands/
│   │   ├── create.py     # Container creation command
│   │   ├── destroy.py    # Container destruction command
│   │   └── list.py       # List containers command
│   └── prompts.py        # Interactive prompt handlers
└── lib/
    ├── validators.py     # Input validation utilities
    └── formatters.py     # Output formatting helpers

tests/
├── contract/
│   └── test_proxmox_api.py
├── integration/
│   └── test_container_lifecycle.py
└── unit/
    ├── test_models.py
    ├── test_config_manager.py
    └── test_validators.py
```

**Structure Decision**: Single project structure selected as this is a standalone CLI tool with no web or mobile components. The structure follows Python packaging conventions with clear separation of models, services, CLI interface, and supporting libraries.

## Phase 0: Outline & Research
1. **Extract unknowns from Technical Context** above:
   - For each NEEDS CLARIFICATION → research task
   - For each dependency → best practices task
   - For each integration → patterns task

2. **Generate and dispatch research agents**:
   ```
   For each unknown in Technical Context:
     Task: "Research {unknown} for {feature context}"
   For each technology choice:
     Task: "Find best practices for {tech} in {domain}"
   ```

3. **Consolidate findings** in `research.md` using format:
   - Decision: [what was chosen]
   - Rationale: [why chosen]
   - Alternatives considered: [what else evaluated]

**Output**: research.md with all NEEDS CLARIFICATION resolved

## Phase 1: Design & Contracts
*Prerequisites: research.md complete*

1. **Extract entities from feature spec** → `data-model.md`:
   - Entity name, fields, relationships
   - Validation rules from requirements
   - State transitions if applicable

2. **Generate API contracts** from functional requirements:
   - For each user action → endpoint
   - Use standard REST/GraphQL patterns
   - Output OpenAPI/GraphQL schema to `/contracts/`

3. **Generate contract tests** from contracts:
   - One test file per endpoint
   - Assert request/response schemas
   - Tests must fail (no implementation yet)

4. **Extract test scenarios** from user stories:
   - Each story → integration test scenario
   - Quickstart test = story validation steps

5. **Update agent file incrementally** (O(1) operation):
   - Run `.specify/scripts/bash/update-agent-context.sh claude`
     **IMPORTANT**: Execute it exactly as specified above. Do not add or remove any arguments.
   - If exists: Add only NEW tech from current plan
   - Preserve manual additions between markers
   - Update recent changes (keep last 3)
   - Keep under 150 lines for token efficiency
   - Output to repository root

**Output**: data-model.md, /contracts/*, failing tests, quickstart.md, agent-specific file

## Phase 2: Task Planning Approach
*This section describes what the /tasks command will do - DO NOT execute during /plan*

**Task Generation Strategy**:
- Load `.specify/templates/tasks-template.md` as base
- Generate tasks from Phase 1 design docs (contracts, data model, quickstart)
- Group tasks by component:
  - Project setup and dependencies (1-3 tasks)
  - Data models from entities (5-6 tasks) [P]
  - Service layer for Proxmox/SSH (4-5 tasks)
  - CLI commands implementation (3-4 tasks)
  - Configuration management (2-3 tasks)
  - Contract tests from API specs (3-4 tasks) [P]
  - Integration tests from user stories (5 tasks)
  - Documentation and packaging (2 tasks)

**Ordering Strategy**:
- TDD order: Tests before implementation
- Dependency order: Models → Services → CLI → Tests
- Parallel markers [P] for independent components
- Critical path: Setup → Models → Proxmox Service → Create Command

**Task Breakdown Example**:
1. Initialize Python project structure
2. Install core dependencies (proxmoxer, click, PyYAML)
3. [P] Create Container model with validation
4. [P] Create ClusterNode model
5. [P] Create Template model
6. [P] Create MountPoint and Device models
7. Implement ProxmoxService wrapper
8. Implement SSHProvisioner service
9. Implement ConfigManager for YAML handling
10. Create CLI entry point and command structure
11. Implement 'create' command with prompts
12. Implement 'destroy' command
13. Implement 'list' command
14. [P] Write contract tests for Proxmox API
15. [P] Write unit tests for models
16. Write integration test for container lifecycle
17. Write quickstart validation tests
18. Create setup.py and package configuration

**Estimated Output**: 25-30 numbered, ordered tasks in tasks.md

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation
*These phases are beyond the scope of the /plan command*

**Phase 3**: Task execution (/tasks command creates tasks.md)  
**Phase 4**: Implementation (execute tasks.md following constitutional principles)  
**Phase 5**: Validation (run tests, execute quickstart.md, performance validation)

## Complexity Tracking
*Fill ONLY if Constitution Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |


## Progress Tracking
*This checklist is updated during execution flow*

**Phase Status**:
- [x] Phase 0: Research complete (/plan command)
- [x] Phase 1: Design complete (/plan command)
- [x] Phase 2: Task planning complete (/plan command - describe approach only)
- [ ] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS
- [x] Post-Design Constitution Check: PASS
- [x] All NEEDS CLARIFICATION resolved
- [x] Complexity deviations documented (none required)

---
*Based on Constitution v2.1.1 - See `/memory/constitution.md`*
