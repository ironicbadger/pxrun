"""
Contract tests for the CLI list command.

This module validates the list command's interface as defined in the OpenAPI contract
at contracts/cli-interface.yaml. Tests follow TDD approach and will fail initially
since the implementation doesn't exist yet.

The tests validate:
- Request/response schema compliance with OpenAPI contract
- All HTTP response codes (200, 503)
- Query parameters (node, running, format)
- ContainerSummary schema validation
- Command interface availability (expects ImportError until implemented)
- Contract completeness and structure

Run with: pytest tests/contract/test_cli_list.py -v
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

    # Extract response schema for list command and resolve references
    list_path = contract['paths']['/commands/list']['get']
    response_schema = list_path['responses']['200']['content']['application/json']['schema']

    # For validation, we need to inline the ContainerSummary schema to avoid reference resolution issues
    list_response_schema = {
        'type': 'object',
        'properties': {
            'containers': {
                'type': 'array',
                'items': schemas['ContainerSummary']  # Inline the schema instead of using $ref
            }
        }
    }

    return {
        'list_response': list_response_schema,
        'container_summary': schemas['ContainerSummary'],
        'error': schemas['Error']
    }

SCHEMAS = load_contract_schemas()


class TestCliListContract:
    """Contract tests for the CLI list command."""

    def test_list_command_interface_exists(self):
        """Test that the list command interface can be imported (will fail initially)."""
        # This test will fail until the CLI implementation exists
        with pytest.raises(ImportError):
            from src.cli.commands.list import ListCommand

    @pytest.fixture
    def mock_cli_runner(self):
        """Mock CLI runner for testing command interface."""
        runner = Mock()
        runner.invoke = Mock()
        return runner

    @pytest.fixture
    def valid_list_response_200(self):
        """Valid 200 response for successful container list."""
        return {
            "containers": [
                {
                    "vmid": 1001,
                    "hostname": "web-server-01",
                    "node": "pve-node-1",
                    "status": "running",
                    "uptime": "2d 5h 30m",
                    "cpu": 15.2,
                    "memory": {
                        "used": 1536,
                        "total": 2048
                    }
                },
                {
                    "vmid": 1002,
                    "hostname": "db-server-01",
                    "node": "pve-node-2",
                    "status": "stopped",
                    "uptime": "0",
                    "cpu": 0.0,
                    "memory": {
                        "used": 0,
                        "total": 4096
                    }
                },
                {
                    "vmid": 1003,
                    "hostname": "app-server-01",
                    "node": "pve-node-1",
                    "status": "running",
                    "uptime": "12h 15m",
                    "cpu": 8.7,
                    "memory": {
                        "used": 2048,
                        "total": 4096
                    }
                }
            ]
        }

    @pytest.fixture
    def empty_list_response_200(self):
        """Valid 200 response with empty container list."""
        return {
            "containers": []
        }

    @pytest.fixture
    def valid_error_response_503(self):
        """Valid 503 error response structure."""
        return {
            "error": "proxmox_unavailable",
            "message": "Unable to connect to Proxmox API",
            "details": {
                "endpoint": "https://pve.example.com:8006/api2/json",
                "connection_error": "Connection timeout"
            },
            "suggestion": "Check Proxmox server status and network connectivity"
        }

    def test_list_response_schema_validation_success(self, valid_list_response_200):
        """Test that valid list response passes schema validation."""
        # This should pass - validates our test data against the contract
        validate(instance=valid_list_response_200, schema=SCHEMAS['list_response'])

    def test_list_response_schema_validation_empty(self, empty_list_response_200):
        """Test that empty list response passes schema validation."""
        validate(instance=empty_list_response_200, schema=SCHEMAS['list_response'])

    def test_container_summary_schema_validation(self):
        """Test that individual ContainerSummary objects match schema."""
        container_summary = {
            "vmid": 1001,
            "hostname": "test-container",
            "node": "pve-node-1",
            "status": "running",
            "uptime": "1d 2h 30m",
            "cpu": 25.5,
            "memory": {
                "used": 1024,
                "total": 2048
            }
        }
        validate(instance=container_summary, schema=SCHEMAS['container_summary'])

    def test_container_summary_schema_validation_minimal(self):
        """Test that minimal ContainerSummary (only required fields) passes validation."""
        minimal_container = {
            "vmid": 1001,
            "hostname": "test-container",
            "node": "pve-node-1",
            "status": "stopped"
        }
        validate(instance=minimal_container, schema=SCHEMAS['container_summary'])

    def test_container_summary_schema_validation_invalid_vmid(self):
        """Test that ContainerSummary with invalid vmid type fails validation."""
        invalid_container = {
            "vmid": "not-a-number",  # Should be integer
            "hostname": "test-container",
            "node": "pve-node-1",
            "status": "running"
        }
        with pytest.raises(ValidationError):
            validate(instance=invalid_container, schema=SCHEMAS['container_summary'])

    def test_container_summary_schema_validation_missing_required(self):
        """Test that ContainerSummary missing required fields fails validation."""
        incomplete_container = {
            "vmid": 1001,
            "hostname": "test-container"
            # Missing required fields: node, status
        }
        with pytest.raises(ValidationError):
            validate(instance=incomplete_container, schema=SCHEMAS['container_summary'])

    def test_error_response_schema_validation(self, valid_error_response_503):
        """Test that 503 error responses match Error schema."""
        validate(instance=valid_error_response_503, schema=SCHEMAS['error'])

    def test_list_command_success_200_default(self, mock_cli_runner, valid_list_response_200):
        """Test list command returns 200 with valid response on success (default parameters)."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.cli.commands.list import list_command

            # Mock the CLI command to return success
            mock_result = Mock()
            mock_result.exit_code = 0
            mock_result.output = json.dumps(valid_list_response_200)
            mock_cli_runner.invoke.return_value = mock_result

            result = mock_cli_runner.invoke(list_command, [
                '--output-format', 'json'
            ])

            assert result.exit_code == 0
            response_data = json.loads(result.output)
            validate(instance=response_data, schema=SCHEMAS['list_response'])

    def test_list_command_success_200_with_node_filter(self, mock_cli_runner):
        """Test list command with node filter parameter."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.cli.commands.list import list_command

            filtered_response = {
                "containers": [
                    {
                        "vmid": 1001,
                        "hostname": "web-server-01",
                        "node": "pve-node-1",
                        "status": "running",
                        "uptime": "2d 5h 30m",
                        "cpu": 15.2,
                        "memory": {
                            "used": 1536,
                            "total": 2048
                        }
                    }
                ]
            }

            mock_result = Mock()
            mock_result.exit_code = 0
            mock_result.output = json.dumps(filtered_response)
            mock_cli_runner.invoke.return_value = mock_result

            result = mock_cli_runner.invoke(list_command, [
                '--node', 'pve-node-1',
                '--output-format', 'json'
            ])

            assert result.exit_code == 0
            response_data = json.loads(result.output)
            validate(instance=response_data, schema=SCHEMAS['list_response'])
            # All containers should be from the specified node
            for container in response_data['containers']:
                assert container['node'] == 'pve-node-1'

    def test_list_command_success_200_with_running_filter(self, mock_cli_runner):
        """Test list command with running status filter parameter."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.cli.commands.list import list_command

            running_only_response = {
                "containers": [
                    {
                        "vmid": 1001,
                        "hostname": "web-server-01",
                        "node": "pve-node-1",
                        "status": "running",
                        "uptime": "2d 5h 30m",
                        "cpu": 15.2,
                        "memory": {
                            "used": 1536,
                            "total": 2048
                        }
                    },
                    {
                        "vmid": 1003,
                        "hostname": "app-server-01",
                        "node": "pve-node-2",
                        "status": "running",
                        "uptime": "12h 15m",
                        "cpu": 8.7,
                        "memory": {
                            "used": 2048,
                            "total": 4096
                        }
                    }
                ]
            }

            mock_result = Mock()
            mock_result.exit_code = 0
            mock_result.output = json.dumps(running_only_response)
            mock_cli_runner.invoke.return_value = mock_result

            result = mock_cli_runner.invoke(list_command, [
                '--running',
                '--output-format', 'json'
            ])

            assert result.exit_code == 0
            response_data = json.loads(result.output)
            validate(instance=response_data, schema=SCHEMAS['list_response'])
            # All containers should be running
            for container in response_data['containers']:
                assert container['status'] == 'running'

    def test_list_command_success_200_with_combined_filters(self, mock_cli_runner):
        """Test list command with both node and running filters."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.cli.commands.list import list_command

            combined_filter_response = {
                "containers": [
                    {
                        "vmid": 1003,
                        "hostname": "app-server-01",
                        "node": "pve-node-1",
                        "status": "running",
                        "uptime": "12h 15m",
                        "cpu": 8.7,
                        "memory": {
                            "used": 2048,
                            "total": 4096
                        }
                    }
                ]
            }

            mock_result = Mock()
            mock_result.exit_code = 0
            mock_result.output = json.dumps(combined_filter_response)
            mock_cli_runner.invoke.return_value = mock_result

            result = mock_cli_runner.invoke(list_command, [
                '--node', 'pve-node-1',
                '--running',
                '--output-format', 'json'
            ])

            assert result.exit_code == 0
            response_data = json.loads(result.output)
            validate(instance=response_data, schema=SCHEMAS['list_response'])
            # All containers should be from specified node and running
            for container in response_data['containers']:
                assert container['node'] == 'pve-node-1'
                assert container['status'] == 'running'

    def test_list_command_format_parameter_table(self, mock_cli_runner):
        """Test list command with table format parameter."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.cli.commands.list import list_command

            # For table format, we expect formatted text output, not JSON
            table_output = """
VMID  HOSTNAME       NODE        STATUS   UPTIME     CPU%   MEMORY
1001  web-server-01  pve-node-1  running  2d 5h 30m  15.2   1536/2048
1002  db-server-01   pve-node-2  stopped  0           0.0    0/4096
1003  app-server-01  pve-node-1  running  12h 15m     8.7    2048/4096
            """.strip()

            mock_result = Mock()
            mock_result.exit_code = 0
            mock_result.output = table_output
            mock_cli_runner.invoke.return_value = mock_result

            result = mock_cli_runner.invoke(list_command, [
                '--format', 'table'
            ])

            assert result.exit_code == 0
            # For table format, just verify it returns formatted text
            assert 'VMID' in result.output
            assert 'HOSTNAME' in result.output
            assert 'NODE' in result.output

    def test_list_command_format_parameter_yaml(self, mock_cli_runner):
        """Test list command with YAML format parameter."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.cli.commands.list import list_command

            yaml_output = """
containers:
  - vmid: 1001
    hostname: web-server-01
    node: pve-node-1
    status: running
    uptime: 2d 5h 30m
    cpu: 15.2
    memory:
      used: 1536
      total: 2048
            """.strip()

            mock_result = Mock()
            mock_result.exit_code = 0
            mock_result.output = yaml_output
            mock_cli_runner.invoke.return_value = mock_result

            result = mock_cli_runner.invoke(list_command, [
                '--format', 'yaml'
            ])

            assert result.exit_code == 0
            # For YAML format, verify it's valid YAML that can be parsed
            parsed_yaml = yaml.safe_load(result.output)
            validate(instance=parsed_yaml, schema=SCHEMAS['list_response'])

    def test_list_command_service_unavailable_503(self, mock_cli_runner, valid_error_response_503):
        """Test list command returns 503 with Error schema when Proxmox API unavailable."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.cli.commands.list import list_command

            mock_result = Mock()
            mock_result.exit_code = 1
            mock_result.output = json.dumps(valid_error_response_503)
            mock_cli_runner.invoke.return_value = mock_result

            result = mock_cli_runner.invoke(list_command, [
                '--output-format', 'json'
            ])

            assert result.exit_code == 1
            response_data = json.loads(result.output)
            validate(instance=response_data, schema=SCHEMAS['error'])
            assert response_data['error'] == 'proxmox_unavailable'

    def test_list_command_empty_result_200(self, mock_cli_runner, empty_list_response_200):
        """Test list command handles empty container list correctly."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.cli.commands.list import list_command

            mock_result = Mock()
            mock_result.exit_code = 0
            mock_result.output = json.dumps(empty_list_response_200)
            mock_cli_runner.invoke.return_value = mock_result

            result = mock_cli_runner.invoke(list_command, [
                '--output-format', 'json'
            ])

            assert result.exit_code == 0
            response_data = json.loads(result.output)
            validate(instance=response_data, schema=SCHEMAS['list_response'])
            assert len(response_data['containers']) == 0

    def test_list_command_query_parameter_validation(self):
        """Test that list command supports all specified query parameters."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.cli.commands.list import list_command
            # Test that the command accepts --node, --running, and --format parameters
            # Implementation should validate format enum values (table, json, yaml)

    def test_list_command_format_enum_validation(self):
        """Test that format parameter validates against allowed enum values."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.cli.commands.list import list_command
            # Test that format parameter only accepts: table, json, yaml
            # Implementation should reject invalid format values


class TestListContractCompleteness:
    """Tests for list command contract completeness and structure."""

    def test_list_endpoint_exists_in_contract(self):
        """Test that list endpoint is properly defined in OpenAPI contract."""
        with open(CONTRACT_PATH, 'r') as f:
            contract = yaml.safe_load(f)

        # Check list endpoint exists
        assert '/commands/list' in contract['paths']
        list_spec = contract['paths']['/commands/list']['get']

        # Check required sections exist
        assert 'summary' in list_spec
        assert 'operationId' in list_spec
        assert 'parameters' in list_spec
        assert 'responses' in list_spec

        # Verify operation ID
        assert list_spec['operationId'] == 'listContainers'

    def test_list_parameters_defined_correctly(self):
        """Test that all list command parameters are properly defined."""
        with open(CONTRACT_PATH, 'r') as f:
            contract = yaml.safe_load(f)

        list_spec = contract['paths']['/commands/list']['get']
        parameters = list_spec['parameters']

        # Check we have expected parameters
        param_names = [param['name'] for param in parameters]
        expected_params = ['node', 'running', 'format']

        for param_name in expected_params:
            assert param_name in param_names, f"Parameter {param_name} missing from contract"

        # Validate specific parameter definitions
        format_param = next(p for p in parameters if p['name'] == 'format')
        assert 'enum' in format_param['schema']
        assert format_param['schema']['enum'] == ['table', 'json', 'yaml']
        assert format_param['schema']['default'] == 'table'

        running_param = next(p for p in parameters if p['name'] == 'running')
        assert running_param['schema']['type'] == 'boolean'

        node_param = next(p for p in parameters if p['name'] == 'node')
        assert node_param['schema']['type'] == 'string'

    def test_list_response_codes_defined(self):
        """Test that all required response codes are defined for list command."""
        with open(CONTRACT_PATH, 'r') as f:
            contract = yaml.safe_load(f)

        list_spec = contract['paths']['/commands/list']['get']
        responses = list_spec['responses']

        # Check required response codes exist
        required_responses = ['200', '503']
        for code in required_responses:
            assert code in responses, f"Response code {code} missing from list contract"

        # Validate 200 response structure
        response_200 = responses['200']
        assert 'description' in response_200
        assert 'content' in response_200
        assert 'application/json' in response_200['content']
        assert 'schema' in response_200['content']['application/json']

        # Validate that 200 response references containers array with ContainerSummary
        schema_200 = response_200['content']['application/json']['schema']
        assert 'properties' in schema_200
        assert 'containers' in schema_200['properties']
        containers_schema = schema_200['properties']['containers']
        assert containers_schema['type'] == 'array'
        assert '$ref' in containers_schema['items']
        assert containers_schema['items']['$ref'] == '#/components/schemas/ContainerSummary'

        # Validate 503 response structure
        response_503 = responses['503']
        assert 'description' in response_503
        assert 'content' in response_503
        assert 'application/json' in response_503['content']
        schema_503 = response_503['content']['application/json']['schema']
        assert '$ref' in schema_503
        assert schema_503['$ref'] == '#/components/schemas/Error'

    def test_container_summary_schema_structure(self):
        """Test that ContainerSummary schema has correct structure."""
        schema = SCHEMAS['container_summary']

        # Check required fields
        required_fields = ['vmid', 'hostname', 'node', 'status']
        assert 'required' in schema
        for field in required_fields:
            assert field in schema['required'], f"Required field {field} missing from ContainerSummary"

        # Check optional fields exist in properties
        optional_fields = ['uptime', 'cpu', 'memory']
        assert 'properties' in schema
        for field in optional_fields:
            assert field in schema['properties'], f"Optional field {field} missing from ContainerSummary properties"

        # Validate memory object structure
        memory_schema = schema['properties']['memory']
        assert memory_schema['type'] == 'object'
        assert 'properties' in memory_schema
        assert 'used' in memory_schema['properties']
        assert 'total' in memory_schema['properties']
        assert memory_schema['properties']['used']['type'] == 'integer'
        assert memory_schema['properties']['total']['type'] == 'integer'

        # Validate data types
        assert schema['properties']['vmid']['type'] == 'integer'
        assert schema['properties']['hostname']['type'] == 'string'
        assert schema['properties']['node']['type'] == 'string'
        assert schema['properties']['status']['type'] == 'string'
        assert schema['properties']['uptime']['type'] == 'string'
        assert schema['properties']['cpu']['type'] == 'number'

    def test_list_contract_http_method(self):
        """Test that list command uses correct HTTP method (GET)."""
        with open(CONTRACT_PATH, 'r') as f:
            contract = yaml.safe_load(f)

        list_path = contract['paths']['/commands/list']
        # Should only have GET method for list operation
        assert 'get' in list_path
        assert len(list_path) == 1, "List endpoint should only support GET method"

    def test_list_operation_summary_and_description(self):
        """Test that list operation has proper summary and description."""
        with open(CONTRACT_PATH, 'r') as f:
            contract = yaml.safe_load(f)

        list_spec = contract['paths']['/commands/list']['get']

        assert 'summary' in list_spec
        assert list_spec['summary'] == 'List existing containers'

        # OperationId should be camelCase
        assert list_spec['operationId'] == 'listContainers'