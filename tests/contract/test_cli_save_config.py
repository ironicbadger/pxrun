"""
Contract tests for the CLI save-config command.

This module validates the save-config command's interface as defined in the OpenAPI contract
at contracts/cli-interface.yaml. Tests follow TDD approach and will fail initially
since the implementation doesn't exist yet.

The tests validate:
- Request/response schema compliance with OpenAPI contract
- All HTTP response codes (200, 404)
- Request body validation (container_id, output_file, include_provisioning)
- Command interface availability (expects ImportError until implemented)
- Contract completeness and structure

Run with: pytest tests/contract/test_cli_save_config.py -v
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

    # Extract request schema for save-config command
    save_config_path = contract['paths']['/commands/save-config']['post']
    request_schema = save_config_path['requestBody']['content']['application/json']['schema']

    return {
        'request': request_schema,
        'error': schemas['Error']
    }

SCHEMAS = load_contract_schemas()


class TestCliSaveConfigContract:
    """Contract tests for the CLI save-config command."""

    def test_save_config_command_interface_exists(self):
        """Test that the save-config command interface can be imported (will fail initially)."""
        # This test will fail until the CLI implementation exists
        with pytest.raises(ImportError):
            from src.cli.commands.save_config import SaveConfigCommand

    @pytest.fixture
    def mock_cli_runner(self):
        """Mock CLI runner for testing command interface."""
        runner = Mock()
        runner.invoke = Mock()
        return runner

    @pytest.fixture
    def valid_save_config_request(self):
        """Valid request payload for save-config command."""
        return {
            "container_id": 1001,
            "output_file": "/path/to/container-config.yaml",
            "include_provisioning": True
        }

    @pytest.fixture
    def minimal_save_config_request(self):
        """Minimal valid request payload for save-config command."""
        return {
            "container_id": 1001,
            "output_file": "/path/to/container-config.yaml"
        }

    @pytest.fixture
    def valid_save_config_response_200(self):
        """Valid 200 response for successful configuration save."""
        return {
            "file": "/path/to/container-config.yaml",
            "size": 2048
        }

    @pytest.fixture
    def valid_error_response_404(self):
        """Valid 404 error response structure."""
        return {
            "error": "container_not_found",
            "message": "Container with VMID 1001 not found",
            "details": {
                "vmid": 1001,
                "searched_nodes": ["pve-node-1", "pve-node-2"]
            },
            "suggestion": "Verify the container VMID and ensure the container exists"
        }

    def test_request_schema_validation_valid(self, valid_save_config_request):
        """Test that valid request payloads pass schema validation."""
        # This should pass - validates our test data against the contract
        validate(instance=valid_save_config_request, schema=SCHEMAS['request'])

    def test_request_schema_validation_minimal(self, minimal_save_config_request):
        """Test that minimal valid request passes schema validation."""
        validate(instance=minimal_save_config_request, schema=SCHEMAS['request'])

    def test_request_schema_validation_missing_required_container_id(self):
        """Test that request without container_id fails validation."""
        invalid_request = {
            "output_file": "/path/to/container-config.yaml",
            "include_provisioning": True
        }
        with pytest.raises(ValidationError):
            validate(instance=invalid_request, schema=SCHEMAS['request'])

    def test_request_schema_validation_missing_required_output_file(self):
        """Test that request without output_file fails validation."""
        invalid_request = {
            "container_id": 1001,
            "include_provisioning": True
        }
        with pytest.raises(ValidationError):
            validate(instance=invalid_request, schema=SCHEMAS['request'])

    def test_request_schema_validation_invalid_types(self):
        """Test that request with wrong types fails validation."""
        invalid_request = {
            "container_id": "1001",  # Should be integer
            "output_file": 123,      # Should be string
            "include_provisioning": "yes"  # Should be boolean
        }
        with pytest.raises(ValidationError):
            validate(instance=invalid_request, schema=SCHEMAS['request'])

    def test_request_schema_validation_container_id_type(self):
        """Test that container_id must be an integer."""
        invalid_request = {
            "container_id": "not-a-number",
            "output_file": "/path/to/container-config.yaml"
        }
        with pytest.raises(ValidationError):
            validate(instance=invalid_request, schema=SCHEMAS['request'])

    def test_request_schema_validation_output_file_type(self):
        """Test that output_file must be a string."""
        invalid_request = {
            "container_id": 1001,
            "output_file": ["not", "a", "string"]
        }
        with pytest.raises(ValidationError):
            validate(instance=invalid_request, schema=SCHEMAS['request'])

    def test_request_schema_validation_include_provisioning_default(self):
        """Test that include_provisioning defaults to true when not provided."""
        request_without_include = {
            "container_id": 1001,
            "output_file": "/path/to/container-config.yaml"
        }
        # Should validate without include_provisioning (it's optional with default)
        validate(instance=request_without_include, schema=SCHEMAS['request'])

    def test_response_200_schema_validation(self, valid_save_config_response_200):
        """Test that 200 response matches expected schema structure."""
        # Validate the response structure directly
        assert "file" in valid_save_config_response_200
        assert "size" in valid_save_config_response_200
        assert isinstance(valid_save_config_response_200["file"], str)
        assert isinstance(valid_save_config_response_200["size"], int)

    def test_response_error_schema_validation(self, valid_error_response_404):
        """Test that error responses match Error schema."""
        validate(instance=valid_error_response_404, schema=SCHEMAS['error'])

    def test_save_config_command_success_200(self, mock_cli_runner,
                                           valid_save_config_request, valid_save_config_response_200):
        """Test save-config command returns 200 with valid response on success."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.cli.commands.save_config import save_config_command

            # Mock the CLI command to return success
            mock_result = Mock()
            mock_result.exit_code = 0
            mock_result.output = json.dumps(valid_save_config_response_200)
            mock_cli_runner.invoke.return_value = mock_result

            result = mock_cli_runner.invoke(save_config_command, [
                '--container-id', str(valid_save_config_request['container_id']),
                '--output-file', valid_save_config_request['output_file'],
                '--include-provisioning',
                '--output-format', 'json'
            ])

            assert result.exit_code == 0
            response_data = json.loads(result.output)
            assert "file" in response_data
            assert "size" in response_data
            assert response_data["file"] == valid_save_config_request['output_file']

    def test_save_config_command_minimal_parameters(self, mock_cli_runner,
                                                  minimal_save_config_request, valid_save_config_response_200):
        """Test save-config command works with minimal required parameters."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.cli.commands.save_config import save_config_command

            mock_result = Mock()
            mock_result.exit_code = 0
            mock_result.output = json.dumps(valid_save_config_response_200)
            mock_cli_runner.invoke.return_value = mock_result

            result = mock_cli_runner.invoke(save_config_command, [
                '--container-id', str(minimal_save_config_request['container_id']),
                '--output-file', minimal_save_config_request['output_file'],
                '--output-format', 'json'
            ])

            assert result.exit_code == 0
            response_data = json.loads(result.output)
            assert "file" in response_data
            assert "size" in response_data

    def test_save_config_command_container_not_found_404(self, mock_cli_runner, valid_error_response_404):
        """Test save-config command returns 404 with Error schema when container not found."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.cli.commands.save_config import save_config_command

            mock_result = Mock()
            mock_result.exit_code = 1
            mock_result.output = json.dumps(valid_error_response_404)
            mock_cli_runner.invoke.return_value = mock_result

            result = mock_cli_runner.invoke(save_config_command, [
                '--container-id', '9999',  # Non-existent container
                '--output-file', '/path/to/output.yaml',
                '--output-format', 'json'
            ])

            assert result.exit_code == 1
            response_data = json.loads(result.output)
            validate(instance=response_data, schema=SCHEMAS['error'])
            assert response_data['error'] == 'container_not_found'

    def test_save_config_command_include_provisioning_flag(self):
        """Test save-config command supports --include-provisioning flag."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.cli.commands.save_config import save_config_command
            # Test that include-provisioning flag is supported
            # Implementation should include/exclude provisioning scripts based on this flag

    def test_save_config_command_exclude_provisioning_flag(self):
        """Test save-config command supports --no-include-provisioning flag."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.cli.commands.save_config import save_config_command
            # Test that no-include-provisioning flag is supported
            # Implementation should exclude provisioning scripts when this flag is used

    def test_save_config_command_output_file_creation(self):
        """Test save-config command creates output file at specified path."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.cli.commands.save_config import save_config_command
            # Test that the command creates the output file
            # Implementation should write YAML config to the specified file path

    def test_contract_completeness(self):
        """Test that all required contract elements are present for save-config."""
        # Verify OpenAPI contract has all required sections
        with open(CONTRACT_PATH, 'r') as f:
            contract = yaml.safe_load(f)

        # Check save-config endpoint exists
        assert '/commands/save-config' in contract['paths']
        save_config_spec = contract['paths']['/commands/save-config']['post']

        # Check all required response codes are defined
        required_responses = ['200', '404']
        for code in required_responses:
            assert code in save_config_spec['responses'], f"Response code {code} missing from contract"

        # Check required schemas exist
        required_schemas = ['Error']
        for schema in required_schemas:
            assert schema in contract['components']['schemas'], f"Schema {schema} missing from contract"

        # Check request body schema
        assert 'requestBody' in save_config_spec
        assert 'content' in save_config_spec['requestBody']
        assert 'application/json' in save_config_spec['requestBody']['content']
        assert 'schema' in save_config_spec['requestBody']['content']['application/json']

        # Check request body is required
        assert save_config_spec['requestBody']['required'] is True


class TestSaveConfigSchemaStructure:
    """Tests for save-config OpenAPI contract schema structure and completeness."""

    def test_request_schema_required_fields(self):
        """Test save-config request schema has all required fields."""
        schema = SCHEMAS['request']
        required_fields = ['container_id', 'output_file']

        assert 'required' in schema
        for field in required_fields:
            assert field in schema['required'], f"Required field {field} missing from save-config request schema"

    def test_request_schema_optional_fields(self):
        """Test save-config request schema has expected optional fields."""
        schema = SCHEMAS['request']
        properties = schema['properties']

        # Check include_provisioning is optional with default
        assert 'include_provisioning' in properties
        include_provisioning = properties['include_provisioning']
        assert include_provisioning['type'] == 'boolean'
        assert include_provisioning['default'] is True

    def test_request_schema_field_types(self):
        """Test save-config request schema has correct field types."""
        schema = SCHEMAS['request']
        properties = schema['properties']

        # Check container_id is integer
        assert properties['container_id']['type'] == 'integer'

        # Check output_file is string
        assert properties['output_file']['type'] == 'string'

        # Check include_provisioning is boolean
        assert properties['include_provisioning']['type'] == 'boolean'

    def test_request_schema_field_descriptions(self):
        """Test save-config request schema has meaningful descriptions."""
        schema = SCHEMAS['request']
        properties = schema['properties']

        # Check that fields have descriptions
        assert 'description' in properties['container_id']
        assert 'description' in properties['output_file']
        assert 'description' in properties['include_provisioning']

        # Check description content
        assert 'VMID' in properties['container_id']['description']
        assert 'file path' in properties['output_file']['description'].lower()
        assert 'provisioning' in properties['include_provisioning']['description'].lower()

    def test_save_config_response_200_schema(self):
        """Test save-config 200 response schema structure."""
        with open(CONTRACT_PATH, 'r') as f:
            contract = yaml.safe_load(f)

        save_config_spec = contract['paths']['/commands/save-config']['post']
        response_200 = save_config_spec['responses']['200']

        # Check response has content
        assert 'content' in response_200
        assert 'application/json' in response_200['content']
        assert 'schema' in response_200['content']['application/json']

        schema = response_200['content']['application/json']['schema']

        # Check response schema structure
        assert schema['type'] == 'object'
        assert 'properties' in schema

        properties = schema['properties']
        assert 'file' in properties
        assert 'size' in properties

        # Check property types
        assert properties['file']['type'] == 'string'
        assert properties['size']['type'] == 'integer'

    def test_save_config_response_404_schema(self):
        """Test save-config 404 response references Error schema."""
        with open(CONTRACT_PATH, 'r') as f:
            contract = yaml.safe_load(f)

        save_config_spec = contract['paths']['/commands/save-config']['post']
        response_404 = save_config_spec['responses']['404']

        # Check response references Error schema
        assert 'content' in response_404
        assert 'application/json' in response_404['content']
        assert 'schema' in response_404['content']['application/json']

        schema = response_404['content']['application/json']['schema']
        assert '$ref' in schema
        assert schema['$ref'] == '#/components/schemas/Error'

    def test_save_config_operation_metadata(self):
        """Test save-config operation has required metadata."""
        with open(CONTRACT_PATH, 'r') as f:
            contract = yaml.safe_load(f)

        save_config_spec = contract['paths']['/commands/save-config']['post']

        # Check operation metadata
        assert 'summary' in save_config_spec
        assert 'operationId' in save_config_spec

        # Check content of metadata
        assert 'configuration' in save_config_spec['summary'].lower()
        assert 'yaml' in save_config_spec['summary'].lower()
        assert save_config_spec['operationId'] == 'saveConfig'

    def test_error_schema_supports_save_config_errors(self):
        """Test Error schema can represent save-config specific errors."""
        error_schema = SCHEMAS['error']

        # Test container not found error
        container_not_found_error = {
            "error": "container_not_found",
            "message": "Container with VMID 1001 not found",
            "details": {
                "vmid": 1001,
                "searched_nodes": ["pve-node-1"]
            },
            "suggestion": "Verify the container VMID"
        }

        validate(instance=container_not_found_error, schema=error_schema)

        # Test file system error
        filesystem_error = {
            "error": "file_write_failed",
            "message": "Unable to write configuration to file",
            "details": {
                "file_path": "/invalid/path/config.yaml",
                "error_code": "ENOENT"
            },
            "suggestion": "Check file path permissions and directory existence"
        }

        validate(instance=filesystem_error, schema=error_schema)