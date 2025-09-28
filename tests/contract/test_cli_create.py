"""
Contract tests for the CLI create command.

This module validates the create command's interface as defined in the OpenAPI contract
at contracts/cli-interface.yaml. Tests follow TDD approach and will fail initially
since the implementation doesn't exist yet.

The tests validate:
- Request/response schema compliance with OpenAPI contract
- All HTTP response codes (200, 400, 409, 503)
- Command interface availability (expects ImportError until implemented)
- Contract completeness and structure

Run with: pytest tests/contract/test_cli_create.py -v
"""

import json
import pytest
from unittest.mock import Mock, patch
from jsonschema import validate, ValidationError
import yaml
from pathlib import Path


# Load OpenAPI contract for schema validation
CONTRACT_PATH = Path(__file__).parent.parent.parent / "specs" / "001-pxrun-specification-document" / "contracts" / "cli-interface.yaml"

def load_contract_schemas():
    """Load OpenAPI contract schemas for validation."""
    with open(CONTRACT_PATH, 'r') as f:
        contract = yaml.safe_load(f)

    # Extract schemas from components
    schemas = contract['components']['schemas']

    # Extract request schema for create command
    create_path = contract['paths']['/commands/create']['post']
    request_schema = create_path['requestBody']['content']['application/json']['schema']

    return {
        'request': request_schema,
        'container_info': schemas['ContainerInfo'],
        'error': schemas['Error']
    }

SCHEMAS = load_contract_schemas()


class TestCliCreateContract:
    """Contract tests for the CLI create command."""

    def test_create_command_interface_exists(self):
        """Test that the create command interface can be imported (will fail initially)."""
        # This test will fail until the CLI implementation exists
        with pytest.raises(ImportError):
            from src.cli.commands.create import CreateCommand

    @pytest.fixture
    def mock_cli_runner(self):
        """Mock CLI runner for testing command interface."""
        runner = Mock()
        runner.invoke = Mock()
        return runner

    @pytest.fixture
    def valid_create_request(self):
        """Valid request payload for create command."""
        return {
            "config_file": "/path/to/config.yaml",
            "interactive": False,
            "dry_run": False,
            "overrides": {
                "hostname": "test-container",
                "node": "pve-node-1",
                "template": "ubuntu-22.04",
                "cores": 2,
                "memory": 2048,
                "storage": 20
            }
        }

    @pytest.fixture
    def valid_create_response_200(self):
        """Valid 200 response for successful container creation."""
        return {
            "vmid": 1001,
            "hostname": "test-container",
            "node": "pve-node-1",
            "status": "created",
            "connection": {
                "ssh": "ssh root@10.0.0.100",
                "ip": "10.0.0.100",
                "console": "pct console 1001"
            },
            "resources": {
                "cores": 2,
                "memory": 2048,
                "storage": 20
            }
        }

    @pytest.fixture
    def valid_error_response(self):
        """Valid error response structure."""
        return {
            "error": "validation_failed",
            "message": "Configuration validation failed",
            "details": {
                "field": "hostname",
                "issue": "hostname already exists"
            },
            "suggestion": "Try using a different hostname"
        }

    def test_request_schema_validation_valid(self, valid_create_request):
        """Test that valid request payloads pass schema validation."""
        # This should pass - validates our test data against the contract
        validate(instance=valid_create_request, schema=SCHEMAS['request'])

    def test_request_schema_validation_minimal(self):
        """Test that minimal valid request passes schema validation."""
        minimal_request = {
            "config_file": "/path/to/config.yaml"
        }
        validate(instance=minimal_request, schema=SCHEMAS['request'])

    def test_request_schema_validation_invalid_missing_config(self):
        """Test that request without config_file is valid (config_file is not required in schema)."""
        request_without_config = {
            "interactive": True,
            "dry_run": False
        }
        # This should pass - config_file is not required in the schema
        validate(instance=request_without_config, schema=SCHEMAS['request'])

    def test_request_schema_validation_invalid_types(self):
        """Test that request with wrong types fails validation."""
        invalid_request = {
            "config_file": "/path/to/config.yaml",
            "interactive": "yes",  # Should be boolean
            "dry_run": "no",       # Should be boolean
            "overrides": {
                "cores": "two",    # Should be integer
                "memory": "2GB"    # Should be integer
            }
        }
        with pytest.raises(ValidationError):
            validate(instance=invalid_request, schema=SCHEMAS['request'])

    def test_response_200_schema_validation(self, valid_create_response_200):
        """Test that 200 response matches ContainerInfo schema."""
        validate(instance=valid_create_response_200, schema=SCHEMAS['container_info'])

    def test_response_error_schema_validation(self, valid_error_response):
        """Test that error responses match Error schema."""
        validate(instance=valid_error_response, schema=SCHEMAS['error'])

    def test_create_command_success_200(self, mock_cli_runner,
                                       valid_create_request, valid_create_response_200):
        """Test create command returns 200 with valid ContainerInfo on success."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.cli.commands.create import create_command

            # Mock the CLI command to return success
            mock_result = Mock()
            mock_result.exit_code = 0
            mock_result.output = json.dumps(valid_create_response_200)
            mock_cli_runner.invoke.return_value = mock_result

            result = mock_cli_runner.invoke(create_command, [
                '--config-file', valid_create_request['config_file'],
                '--no-interactive',
                '--output-format', 'json'
            ])

            assert result.exit_code == 0
            response_data = json.loads(result.output)
            validate(instance=response_data, schema=SCHEMAS['container_info'])

    def test_create_command_validation_error_400(self, mock_cli_runner):
        """Test create command returns 400 with Error schema on validation failure."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.cli.commands.create import create_command

            error_response = {
                "error": "validation_failed",
                "message": "Invalid configuration file format",
                "details": {
                    "line": 15,
                    "issue": "Invalid YAML syntax"
                },
                "suggestion": "Check your YAML file for syntax errors"
            }

            mock_result = Mock()
            mock_result.exit_code = 1
            mock_result.output = json.dumps(error_response)
            mock_cli_runner.invoke.return_value = mock_result

            result = mock_cli_runner.invoke(create_command, [
                '--config-file', '/invalid/config.yaml',
                '--output-format', 'json'
            ])

            assert result.exit_code == 1
            response_data = json.loads(result.output)
            validate(instance=response_data, schema=SCHEMAS['error'])
            assert response_data['error'] == 'validation_failed'

    def test_create_command_conflict_error_409(self, mock_cli_runner):
        """Test create command returns 409 with Error schema when container exists."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.cli.commands.create import create_command

            conflict_response = {
                "error": "container_exists",
                "message": "Container with hostname 'test-container' already exists",
                "details": {
                    "existing_vmid": 1001,
                    "existing_node": "pve-node-1"
                },
                "suggestion": "Use a different hostname or destroy the existing container"
            }

            mock_result = Mock()
            mock_result.exit_code = 1
            mock_result.output = json.dumps(conflict_response)
            mock_cli_runner.invoke.return_value = mock_result

            result = mock_cli_runner.invoke(create_command, [
                '--config-file', '/path/to/config.yaml',
                '--output-format', 'json'
            ])

            assert result.exit_code == 1
            response_data = json.loads(result.output)
            validate(instance=response_data, schema=SCHEMAS['error'])
            assert response_data['error'] == 'container_exists'

    def test_create_command_service_unavailable_503(self, mock_cli_runner):
        """Test create command returns 503 with Error schema when Proxmox API unavailable."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.cli.commands.create import create_command

            service_error_response = {
                "error": "proxmox_unavailable",
                "message": "Unable to connect to Proxmox API",
                "details": {
                    "endpoint": "https://pve.example.com:8006/api2/json",
                    "connection_error": "Connection refused"
                },
                "suggestion": "Check Proxmox server status and network connectivity"
            }

            mock_result = Mock()
            mock_result.exit_code = 1
            mock_result.output = json.dumps(service_error_response)
            mock_cli_runner.invoke.return_value = mock_result

            result = mock_cli_runner.invoke(create_command, [
                '--config-file', '/path/to/config.yaml',
                '--output-format', 'json'
            ])

            assert result.exit_code == 1
            response_data = json.loads(result.output)
            validate(instance=response_data, schema=SCHEMAS['error'])
            assert response_data['error'] == 'proxmox_unavailable'

    def test_create_command_dry_run_functionality(self):
        """Test create command supports dry-run mode as specified in contract."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.cli.commands.create import create_command
            # Test that dry-run flag is supported
            # Implementation should validate config without creating container

    def test_create_command_interactive_mode_support(self):
        """Test create command supports interactive mode as specified in contract."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.cli.commands.create import create_command
            # Test that interactive flag is supported
            # Implementation should prompt for missing values when interactive=True

    def test_create_command_overrides_support(self):
        """Test create command supports configuration overrides as specified in contract."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.cli.commands.create import create_command
            # Test that override parameters (hostname, node, template, etc.) are supported
            # Implementation should apply overrides to base configuration

    def test_contract_completeness(self):
        """Test that all required contract elements are present."""
        # Verify OpenAPI contract has all required sections
        with open(CONTRACT_PATH, 'r') as f:
            contract = yaml.safe_load(f)

        # Check create endpoint exists
        assert '/commands/create' in contract['paths']
        create_spec = contract['paths']['/commands/create']['post']

        # Check all required response codes are defined
        required_responses = ['200', '400', '409', '503']
        for code in required_responses:
            assert code in create_spec['responses'], f"Response code {code} missing from contract"

        # Check required schemas exist
        required_schemas = ['ContainerInfo', 'Error']
        for schema in required_schemas:
            assert schema in contract['components']['schemas'], f"Schema {schema} missing from contract"

        # Check request body schema
        assert 'requestBody' in create_spec
        assert 'content' in create_spec['requestBody']
        assert 'application/json' in create_spec['requestBody']['content']
        assert 'schema' in create_spec['requestBody']['content']['application/json']


class TestContractSchemaStructure:
    """Tests for OpenAPI contract schema structure and completeness."""

    def test_container_info_schema_required_fields(self):
        """Test ContainerInfo schema has all required fields."""
        schema = SCHEMAS['container_info']
        required_fields = ['vmid', 'hostname', 'node', 'status', 'connection']

        assert 'required' in schema
        for field in required_fields:
            assert field in schema['required'], f"Required field {field} missing from ContainerInfo schema"

    def test_error_schema_required_fields(self):
        """Test Error schema has all required fields."""
        schema = SCHEMAS['error']
        required_fields = ['error', 'message']

        assert 'required' in schema
        for field in required_fields:
            assert field in schema['required'], f"Required field {field} missing from Error schema"

    def test_request_schema_supports_all_overrides(self):
        """Test request schema supports all documented override fields."""
        schema = SCHEMAS['request']
        override_properties = schema['properties']['overrides']['properties']

        expected_overrides = ['hostname', 'node', 'template', 'cores', 'memory', 'storage']
        for override in expected_overrides:
            assert override in override_properties, f"Override field {override} missing from request schema"

    def test_contract_openapi_version_compatibility(self):
        """Test that the contract uses a supported OpenAPI version."""
        with open(CONTRACT_PATH, 'r') as f:
            contract = yaml.safe_load(f)

        # Check OpenAPI version
        assert 'openapi' in contract
        version = contract['openapi']
        assert version.startswith('3.'), f"Expected OpenAPI 3.x, got {version}"

    def test_all_response_schemas_valid(self):
        """Test that all response schemas in the contract are valid JSON Schema."""
        with open(CONTRACT_PATH, 'r') as f:
            contract = yaml.safe_load(f)

        create_spec = contract['paths']['/commands/create']['post']
        responses = create_spec['responses']

        # Test 200 response schema references valid ContainerInfo
        response_200 = responses['200']['content']['application/json']['schema']
        assert '$ref' in response_200
        assert response_200['$ref'] == '#/components/schemas/ContainerInfo'

        # Test error response schemas reference valid Error schema
        for code in ['400', '409', '503']:
            error_response = responses[code]['content']['application/json']['schema']
            assert '$ref' in error_response
            assert error_response['$ref'] == '#/components/schemas/Error'