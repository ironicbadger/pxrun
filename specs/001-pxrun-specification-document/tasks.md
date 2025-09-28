# Tasks: pxrun - Proxmox LXC Lifecycle Management Tool

**Input**: Design documents from `/specs/001-pxrun-specification-document/`
**Prerequisites**: plan.md (required), research.md, data-model.md, contracts/

## Execution Flow (main)
```
1. Load plan.md from feature directory
   → If not found: ERROR "No implementation plan found"
   → Extract: tech stack, libraries, structure
2. Load optional design documents:
   → data-model.md: Extract entities → model tasks
   → contracts/: Each file → contract test task
   → research.md: Extract decisions → setup tasks
3. Generate tasks by category:
   → Setup: project init, dependencies, linting
   → Tests: contract tests, integration tests
   → Core: models, services, CLI commands
   → Integration: DB, middleware, logging
   → Polish: unit tests, performance, docs
4. Apply task rules:
   → Different files = mark [P] for parallel
   → Same file = sequential (no [P])
   → Tests before implementation (TDD)
5. Number tasks sequentially (T001, T002...)
6. Generate dependency graph
7. Create parallel execution examples
8. Validate task completeness:
   → All contracts have tests? YES
   → All entities have models? YES
   → All endpoints implemented? YES (CLI commands)
9. Return: SUCCESS (tasks ready for execution)
```

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

## Path Conventions
- **Single project**: `src/`, `tests/` at repository root
- Paths shown below follow single project structure from plan.md

## Phase 3.1: Setup
- [ ] T001 Create Python project structure with src/, tests/, and config directories
- [ ] T002 Initialize Python package with setup.py and requirements.txt for proxmoxer, click, PyYAML, paramiko, sops, python-dotenv
- [ ] T003 [P] Configure pytest, black, ruff, and mypy in pyproject.toml
- [ ] T004 [P] Create .env.example with PROXMOX_HOST, PROXMOX_TOKEN_ID, PROXMOX_TOKEN_SECRET placeholders
- [ ] T005 [P] Create GitHub Actions CI/CD workflow in .github/workflows/ci.yml

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3
**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**

### Contract Tests
- [ ] T006 [P] Contract test for Proxmox API authentication in tests/contract/test_proxmox_api.py::test_auth_token
- [ ] T007 [P] Contract test for list nodes endpoint in tests/contract/test_proxmox_api.py::test_list_nodes
- [ ] T008 [P] Contract test for create container endpoint in tests/contract/test_proxmox_api.py::test_create_lxc
- [ ] T009 [P] Contract test for destroy container endpoint in tests/contract/test_proxmox_api.py::test_destroy_lxc
- [ ] T010 [P] Contract test for list containers endpoint in tests/contract/test_proxmox_api.py::test_list_lxc
- [ ] T011 [P] Contract test for get storage pools in tests/contract/test_proxmox_api.py::test_get_storage
- [ ] T012 [P] Contract test for get templates in tests/contract/test_proxmox_api.py::test_get_templates

### CLI Contract Tests
- [ ] T013 [P] Contract test for create command interface in tests/contract/test_cli_interface.py::test_create_command
- [ ] T014 [P] Contract test for destroy command interface in tests/contract/test_cli_interface.py::test_destroy_command
- [ ] T015 [P] Contract test for list command interface in tests/contract/test_cli_interface.py::test_list_command
- [ ] T016 [P] Contract test for save-config command in tests/contract/test_cli_interface.py::test_save_config

### Integration Tests
- [ ] T017 [P] Integration test for interactive container creation in tests/integration/test_container_lifecycle.py::test_create_interactive
- [ ] T018 [P] Integration test for config file creation in tests/integration/test_container_lifecycle.py::test_create_from_config
- [ ] T019 [P] Integration test for container provisioning in tests/integration/test_container_lifecycle.py::test_provisioning
- [ ] T020 [P] Integration test for container destruction in tests/integration/test_container_lifecycle.py::test_destroy
- [ ] T021 [P] Integration test for SSH provisioning workflow in tests/integration/test_ssh_provisioning.py
- [ ] T022 [P] Integration test for YAML config management in tests/integration/test_config_management.py

## Phase 3.3: Core Implementation (ONLY after tests are failing)

### Data Models
- [ ] T023 [P] Container model with validation in src/models/container.py
- [ ] T024 [P] ClusterNode model in src/models/cluster.py
- [ ] T025 [P] Template model in src/models/template.py
- [ ] T026 [P] StoragePool model in src/models/storage.py
- [ ] T027 [P] MountPoint and Device models in src/models/mount.py
- [ ] T028 [P] ProvisioningConfig and Script models in src/models/provisioning.py
- [ ] T029 [P] TailscaleConfig model in src/models/tailscale.py
- [ ] T030 [P] UserConfig model in src/models/user.py

### Service Layer
- [ ] T031 ProxmoxService wrapper for API operations in src/services/proxmox.py
- [ ] T032 SSHProvisioner for container provisioning in src/services/ssh_provisioner.py
- [ ] T033 ConfigManager for YAML handling in src/services/config_manager.py
- [ ] T034 CredentialsManager for SOPS encryption in src/services/credentials.py
- [ ] T035 NodeSelector for cluster node management in src/services/node_selector.py

### CLI Commands
- [ ] T036 CLI entry point and main command group in src/cli/__main__.py
- [ ] T037 Create command with interactive prompts in src/cli/commands/create.py
- [ ] T038 Destroy command with confirmation in src/cli/commands/destroy.py
- [ ] T039 List command with table/json output in src/cli/commands/list.py
- [ ] T040 Save-config command for export in src/cli/commands/save_config.py
- [ ] T041 Interactive prompt handlers in src/cli/prompts.py

### Support Libraries
- [ ] T042 [P] Input validators for IPs, hostnames, resources in src/lib/validators.py
- [ ] T043 [P] Output formatters for tables and JSON in src/lib/formatters.py
- [ ] T044 [P] Error handlers and custom exceptions in src/lib/exceptions.py

## Phase 3.4: Integration

### Core Integration
- [ ] T045 Wire ProxmoxService to CLI commands in src/cli/commands/
- [ ] T046 Connect SSHProvisioner to create command flow
- [ ] T047 Integrate ConfigManager with save/load operations
- [ ] T048 Add CredentialsManager to environment loading

### Features Integration
- [ ] T049 Implement mount point handling in container creation
- [ ] T050 Implement device passthrough for hardware acceleration
- [ ] T051 Add Docker installation provisioning script
- [ ] T052 Add Tailscale integration with auth key handling
- [ ] T053 Implement dry-run mode for validation

### Error Handling
- [ ] T054 Add comprehensive error messages with recovery suggestions
- [ ] T055 Implement timeout handling for API and SSH operations
- [ ] T056 Add retry logic for transient failures
- [ ] T057 Implement proper logging throughout application

## Phase 3.5: Polish

### Unit Tests
- [ ] T058 [P] Unit tests for all validators in tests/unit/test_validators.py
- [ ] T059 [P] Unit tests for formatters in tests/unit/test_formatters.py
- [ ] T060 [P] Unit tests for models validation in tests/unit/test_models.py
- [ ] T061 [P] Unit tests for config parsing in tests/unit/test_config_manager.py
- [ ] T062 [P] Unit tests for prompt handlers in tests/unit/test_prompts.py

### Performance & Quality
- [ ] T063 Performance test for < 200ms local operations
- [ ] T064 Performance test for < 60s container creation
- [ ] T065 Memory profiling for large container lists
- [ ] T066 Code coverage analysis (target > 80%)

### Documentation
- [ ] T067 [P] Create comprehensive README.md with installation and usage
- [ ] T068 [P] Generate API documentation from docstrings
- [ ] T069 [P] Create man page for CLI commands
- [ ] T070 [P] Add example configurations in examples/ directory

### Packaging
- [ ] T071 Create setup.py with proper metadata and entry points
- [ ] T072 Configure package for PyPI distribution
- [ ] T073 Create Docker image for containerized usage
- [ ] T074 Add shell completions for bash/zsh

## Dependencies
- Setup (T001-T005) must complete first
- All tests (T006-T022) before any implementation (T023-T044)
- Models (T023-T030) can run in parallel
- Services (T031-T035) depend on models
- CLI commands (T036-T041) depend on services
- Integration (T045-T057) depends on core implementation
- Polish (T058-T074) comes last

## Parallel Execution Examples

### Launch all contract tests together (T006-T016):
```
Task: "Contract test for Proxmox API authentication in tests/contract/test_proxmox_api.py::test_auth_token"
Task: "Contract test for list nodes endpoint in tests/contract/test_proxmox_api.py::test_list_nodes"
Task: "Contract test for create container endpoint in tests/contract/test_proxmox_api.py::test_create_lxc"
Task: "Contract test for destroy container endpoint in tests/contract/test_proxmox_api.py::test_destroy_lxc"
Task: "Contract test for create command interface in tests/contract/test_cli_interface.py::test_create_command"
```

### Launch all models together (T023-T030):
```
Task: "Container model with validation in src/models/container.py"
Task: "ClusterNode model in src/models/cluster.py"
Task: "Template model in src/models/template.py"
Task: "StoragePool model in src/models/storage.py"
Task: "MountPoint and Device models in src/models/mount.py"
```

### Launch all unit tests together (T058-T062):
```
Task: "Unit tests for all validators in tests/unit/test_validators.py"
Task: "Unit tests for formatters in tests/unit/test_formatters.py"
Task: "Unit tests for models validation in tests/unit/test_models.py"
Task: "Unit tests for config parsing in tests/unit/test_config_manager.py"
Task: "Unit tests for prompt handlers in tests/unit/test_prompts.py"
```

## Notes
- [P] marks indicate tasks that can run in parallel (different files, no dependencies)
- Verify all tests fail before implementing features (TDD approach)
- Commit after completing each task or logical group
- Use mocked Proxmox API responses for testing
- Ensure SOPS encryption for any stored credentials
- Follow PEP 8 and use type hints throughout

## Validation Checklist
- ✅ All contracts have corresponding test tasks (T006-T016)
- ✅ All entities from data-model have implementation tasks (T023-T030)
- ✅ All CLI commands have implementation tasks (T036-T041)
- ✅ Integration tests cover user scenarios from quickstart (T017-T022)
- ✅ Performance requirements have test tasks (T063-T064)
- ✅ Security requirements addressed (SOPS in T034, T048)

## Execution Status
- [ ] Tasks generated from plan.md
- [ ] Contract tests created for both APIs
- [ ] Model tasks match data-model.md entities
- [ ] Integration tests match quickstart scenarios
- [ ] Dependencies properly ordered
- [ ] Parallel execution opportunities identified

---
**Total Tasks**: 74
**Parallelizable**: 38 tasks marked with [P]
**Critical Path**: Setup → Tests → Models → Services → CLI → Integration → Polish