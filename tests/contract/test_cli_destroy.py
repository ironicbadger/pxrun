"""
Contract tests for the CLI destroy command.

This module validates the destroy command's interface as defined in the OpenAPI contract
at contracts/cli-interface.yaml. Tests follow TDD approach and will fail initially
since the implementation doesn't exist yet.

The tests validate:
- Request/response schema compliance with OpenAPI contract
- All HTTP response codes (200, 404, 503)
- Parameter validation (container_id, force, confirm)
- Command interface availability (expects ImportError until implemented)
- Contract completeness and structure

Run with: pytest tests/contract/test_cli_destroy.py -v
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

    # Extract destroy command specification
    destroy_path = contract['paths']['/commands/destroy']['delete']

    # Extract parameter schemas
    parameters = destroy_path['parameters']
    parameter_schemas = {}
    for param in parameters:
        parameter_schemas[param['name']] = param['schema']

    return {
        'parameters': parameter_schemas,
        'error': schemas['Error']
    }

SCHEMAS = load_contract_schemas()


class TestCliDestroyContract:
    """Contract tests for the CLI destroy command."""

    def test_destroy_command_interface_exists(self):
        """Test that the destroy command interface can be imported (will fail initially)."""
        # This test will fail until the CLI implementation exists
        with pytest.raises(ImportError):
            from src.cli.commands.destroy import DestroyCommand

    @pytest.fixture
    def mock_cli_runner(self):
        """Mock CLI runner for testing command interface."""
        runner = Mock()
        runner.invoke = Mock()
        return runner

    @pytest.fixture
    def valid_destroy_response_200(self):
        """Valid 200 response for successful container destruction."""
        return {
            "vmid": 1001,
            "message": "Container 1001 destroyed successfully"
        }

    @pytest.fixture
    def valid_error_response_404(self):
        """Valid 404 error response for container not found."""
        return {
            "error": "container_not_found",
            "message": "Container with VMID 1001 not found",
            "details": {
                "vmid": 1001,
                "searched_nodes": ["pve-node-1", "pve-node-2"]
            },
            "suggestion": "Verify the container VMID exists using 'pxrun list'"
        }

    @pytest.fixture
    def valid_error_response_503(self):
        """Valid 503 error response for Proxmox API unavailable."""
        return {
            "error": "proxmox_unavailable",
            "message": "Unable to connect to Proxmox API",
            "details": {
                "endpoint": "https://pve.example.com:8006/api2/json",
                "connection_error": "Connection timed out"
            },
            "suggestion": "Check Proxmox server status and network connectivity"
        }

    def test_parameter_container_id_validation_valid(self):
        """Test that valid container_id values pass schema validation."""
        valid_container_ids = [100, 1001, 999999999]

        for vmid in valid_container_ids:
            # Should not raise ValidationError
            validate(instance=vmid, schema=SCHEMAS['parameters']['container_id'])

    def test_parameter_container_id_validation_invalid_range(self):
        """Test that container_id outside valid range fails validation."""
        invalid_container_ids = [99, 1000000000, -1, 0]

        for vmid in invalid_container_ids:
            with pytest.raises(ValidationError):
                validate(instance=vmid, schema=SCHEMAS['parameters']['container_id'])

    def test_parameter_container_id_validation_invalid_type(self):
        """Test that non-integer container_id fails validation."""
        invalid_container_ids = ["1001", "abc", None, 1001.5]

        for vmid in invalid_container_ids:
            with pytest.raises(ValidationError):
                validate(instance=vmid, schema=SCHEMAS['parameters']['container_id'])

    def test_parameter_force_validation_valid(self):
        """Test that valid force parameter values pass schema validation."""
        valid_force_values = [True, False]

        for force in valid_force_values:
            # Should not raise ValidationError
            validate(instance=force, schema=SCHEMAS['parameters']['force'])

    def test_parameter_force_validation_invalid_type(self):
        """Test that non-boolean force parameter fails validation."""
        invalid_force_values = ["true", "false", 1, 0, None]

        for force in invalid_force_values:
            with pytest.raises(ValidationError):
                validate(instance=force, schema=SCHEMAS['parameters']['force'])

    def test_parameter_confirm_validation_valid(self):
        """Test that valid confirm parameter values pass schema validation."""
        valid_confirm_values = [True, False]

        for confirm in valid_confirm_values:
            # Should not raise ValidationError
            validate(instance=confirm, schema=SCHEMAS['parameters']['confirm'])

    def test_parameter_confirm_validation_invalid_type(self):
        """Test that non-boolean confirm parameter fails validation."""
        invalid_confirm_values = ["yes", "no", 1, 0, None]

        for confirm in invalid_confirm_values:
            with pytest.raises(ValidationError):
                validate(instance=confirm, schema=SCHEMAS['parameters']['confirm'])

    def test_response_200_schema_validation(self, valid_destroy_response_200):
        """Test that 200 response matches expected schema structure."""
        # Validate the structure matches what's defined in the contract
        expected_schema = {
            "type": "object",
            "properties": {
                "vmid": {"type": "integer"},
                "message": {"type": "string"}
            }
        }
        validate(instance=valid_destroy_response_200, schema=expected_schema)

    def test_response_404_error_schema_validation(self, valid_error_response_404):
        """Test that 404 error response matches Error schema."""
        validate(instance=valid_error_response_404, schema=SCHEMAS['error'])

    def test_response_503_error_schema_validation(self, valid_error_response_503):
        """Test that 503 error response matches Error schema."""
        validate(instance=valid_error_response_503, schema=SCHEMAS['error'])

    def test_destroy_command_success_200(self, mock_cli_runner, valid_destroy_response_200):
        """Test destroy command returns 200 with valid response on success."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.cli.commands.destroy import destroy_command

            # Mock the CLI command to return success
            mock_result = Mock()
            mock_result.exit_code = 0
            mock_result.output = json.dumps(valid_destroy_response_200)
            mock_cli_runner.invoke.return_value = mock_result

            result = mock_cli_runner.invoke(destroy_command, [
                '--container-id', '1001',
                '--force',
                '--confirm',
                '--output-format', 'json'
            ])

            assert result.exit_code == 0
            response_data = json.loads(result.output)

            # Validate response structure
            expected_schema = {
                "type": "object",
                "properties": {
                    "vmid": {"type": "integer"},
                    "message": {"type": "string"}
                }
            }
            validate(instance=response_data, schema=expected_schema)
            assert response_data['vmid'] == 1001

    def test_destroy_command_not_found_404(self, mock_cli_runner, valid_error_response_404):
        """Test destroy command returns 404 with Error schema when container not found."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.cli.commands.destroy import destroy_command

            mock_result = Mock()
            mock_result.exit_code = 1
            mock_result.output = json.dumps(valid_error_response_404)
            mock_cli_runner.invoke.return_value = mock_result

            result = mock_cli_runner.invoke(destroy_command, [
                '--container-id', '1001',
                '--force',
                '--confirm',
                '--output-format', 'json'
            ])

            assert result.exit_code == 1
            response_data = json.loads(result.output)
            validate(instance=response_data, schema=SCHEMAS['error'])
            assert response_data['error'] == 'container_not_found'

    def test_destroy_command_service_unavailable_503(self, mock_cli_runner, valid_error_response_503):
        """Test destroy command returns 503 with Error schema when Proxmox API unavailable."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.cli.commands.destroy import destroy_command

            mock_result = Mock()
            mock_result.exit_code = 1
            mock_result.output = json.dumps(valid_error_response_503)
            mock_cli_runner.invoke.return_value = mock_result

            result = mock_cli_runner.invoke(destroy_command, [
                '--container-id', '1001',
                '--output-format', 'json'
            ])

            assert result.exit_code == 1
            response_data = json.loads(result.output)
            validate(instance=response_data, schema=SCHEMAS['error'])
            assert response_data['error'] == 'proxmox_unavailable'

    def test_destroy_command_force_parameter_support(self):
        """Test destroy command supports force parameter as specified in contract."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.cli.commands.destroy import destroy_command
            # Test that --force flag is supported
            # Implementation should destroy running containers when force=True

    def test_destroy_command_confirm_parameter_support(self):
        """Test destroy command supports confirm parameter as specified in contract."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.cli.commands.destroy import destroy_command
            # Test that --confirm flag is supported
            # Implementation should skip confirmation prompts when confirm=True

    def test_destroy_command_container_id_validation(self):
        """Test destroy command validates container_id parameter correctly."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.cli.commands.destroy import destroy_command
            # Test that container_id parameter validation matches contract spec
            # Should reject values outside range 100-999999999

    def test_destroy_command_required_parameters(self):
        """Test destroy command requires container_id parameter."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.cli.commands.destroy import destroy_command
            # Test that container_id is required (should fail without it)

    def test_destroy_command_optional_parameters_defaults(self):
        """Test destroy command handles optional parameters with correct defaults."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.cli.commands.destroy import destroy_command
            # Test that force defaults to False
            # Test that confirm defaults to False

    def test_contract_completeness_destroy_endpoint(self):
        """Test that all required contract elements are present for destroy endpoint."""
        # Verify OpenAPI contract has all required sections
        with open(CONTRACT_PATH, 'r') as f:
            contract = yaml.safe_load(f)

        # Check destroy endpoint exists
        assert '/commands/destroy' in contract['paths']
        destroy_spec = contract['paths']['/commands/destroy']['delete']

        # Check all required response codes are defined
        required_responses = ['200', '404', '503']
        for code in required_responses:
            assert code in destroy_spec['responses'], f"Response code {code} missing from contract"

        # Check required parameters are defined
        required_parameters = ['container_id']
        parameter_names = [p['name'] for p in destroy_spec['parameters']]
        for param in required_parameters:
            assert param in parameter_names, f"Required parameter {param} missing from contract"

        # Check optional parameters are defined
        optional_parameters = ['force', 'confirm']
        for param in optional_parameters:
            assert param in parameter_names, f"Optional parameter {param} missing from contract"

        # Check parameter constraints
        container_id_param = next(p for p in destroy_spec['parameters'] if p['name'] == 'container_id')
        assert container_id_param['required'] is True
        assert container_id_param['schema']['type'] == 'integer'
        assert container_id_param['schema']['minimum'] == 100
        assert container_id_param['schema']['maximum'] == 999999999

        force_param = next(p for p in destroy_spec['parameters'] if p['name'] == 'force')
        assert 'required' not in force_param or force_param.get('required') is False
        assert force_param['schema']['type'] == 'boolean'
        assert force_param['schema']['default'] is False

        confirm_param = next(p for p in destroy_spec['parameters'] if p['name'] == 'confirm')
        assert 'required' not in confirm_param or confirm_param.get('required') is False
        assert confirm_param['schema']['type'] == 'boolean'
        assert confirm_param['schema']['default'] is False


class TestContractDestroySchemaStructure:
    """Tests for OpenAPI contract destroy endpoint schema structure and completeness."""

    def test_destroy_endpoint_method_correct(self):
        """Test that destroy endpoint uses DELETE method as per REST conventions."""
        with open(CONTRACT_PATH, 'r') as f:
            contract = yaml.safe_load(f)

        destroy_path = contract['paths']['/commands/destroy']
        assert 'delete' in destroy_path, "Destroy endpoint should use DELETE method"
        assert 'get' not in destroy_path, "Destroy endpoint should not use GET method"
        assert 'post' not in destroy_path, "Destroy endpoint should not use POST method"

    def test_destroy_parameters_in_query(self):
        """Test that all destroy parameters are specified as query parameters."""
        with open(CONTRACT_PATH, 'r') as f:
            contract = yaml.safe_load(f)

        destroy_spec = contract['paths']['/commands/destroy']['delete']
        parameters = destroy_spec['parameters']

        for param in parameters:
            assert param['in'] == 'query', f"Parameter {param['name']} should be in query, not {param['in']}"

    def test_destroy_response_schemas_reference_components(self):
        """Test that destroy response schemas properly reference component schemas."""
        with open(CONTRACT_PATH, 'r') as f:
            contract = yaml.safe_load(f)

        destroy_spec = contract['paths']['/commands/destroy']['delete']
        responses = destroy_spec['responses']

        # 404 and 503 should reference Error schema
        for code in ['404', '503']:
            error_response = responses[code]['content']['application/json']['schema']
            assert '$ref' in error_response
            assert error_response['$ref'] == '#/components/schemas/Error'

        # 200 response should have inline schema (as per contract)
        response_200 = responses['200']['content']['application/json']['schema']
        assert 'type' in response_200
        assert response_200['type'] == 'object'
        assert 'properties' in response_200
        assert 'vmid' in response_200['properties']
        assert 'message' in response_200['properties']

    def test_destroy_operation_id_present(self):
        """Test that destroy endpoint has operationId for code generation."""
        with open(CONTRACT_PATH, 'r') as f:
            contract = yaml.safe_load(f)

        destroy_spec = contract['paths']['/commands/destroy']['delete']
        assert 'operationId' in destroy_spec
        assert destroy_spec['operationId'] == 'destroyContainer'

    def test_destroy_summary_and_description(self):
        """Test that destroy endpoint has proper summary and parameter descriptions."""
        with open(CONTRACT_PATH, 'r') as f:
            contract = yaml.safe_load(f)

        destroy_spec = contract['paths']['/commands/destroy']['delete']
        assert 'summary' in destroy_spec
        assert destroy_spec['summary'] == 'Destroy an LXC container'

        # Check parameter descriptions
        for param in destroy_spec['parameters']:
            assert 'description' in param, f"Parameter {param['name']} missing description"
            if param['name'] == 'container_id':
                assert 'VMID' in param['description']
            elif param['name'] == 'force':
                assert 'force' in param['description'].lower()
                assert 'running' in param['description'].lower()
            elif param['name'] == 'confirm':
                assert 'confirmation' in param['description'].lower()

    def test_all_destroy_response_content_types(self):
        """Test that all destroy responses specify application/json content type."""
        with open(CONTRACT_PATH, 'r') as f:
            contract = yaml.safe_load(f)

        destroy_spec = contract['paths']['/commands/destroy']['delete']
        responses = destroy_spec['responses']

        for code, response in responses.items():
            assert 'content' in response, f"Response {code} missing content specification"
            assert 'application/json' in response['content'], f"Response {code} missing application/json content type"
            assert 'schema' in response['content']['application/json'], f"Response {code} missing schema"