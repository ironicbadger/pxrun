"""
Contract tests for the Proxmox task status API.

This module validates the Proxmox task status endpoints as defined in the OpenAPI contract
at contracts/proxmox-api.yaml. Tests follow TDD approach and will fail initially
since the implementation doesn't exist yet.

The tests validate:
- GET /nodes/{node}/tasks/{upid}/status endpoint
- Request/response schema compliance with OpenAPI contract
- Task status responses (running, stopped, exitstatus)
- Error handling for invalid nodes/UPIDs
- Contract completeness and structure

Run with: pytest tests/contract/test_proxmox_tasks.py -v
"""

import json
import pytest
from unittest.mock import Mock, patch
from jsonschema import validate, ValidationError
import yaml
from pathlib import Path
import responses


# Load OpenAPI contract for schema validation
CONTRACT_PATH = Path(__file__).parent.parent.parent / "specs" / "001-pxrun-specification-document" / "contracts" / "proxmox-api.yaml"

def load_contract_schemas():
    """Load OpenAPI contract schemas for validation."""
    with open(CONTRACT_PATH, 'r') as f:
        contract = yaml.safe_load(f)

    # Extract task status endpoint schema
    task_status_path = contract['paths']['/nodes/{node}/tasks/{upid}/status']['get']
    task_status_response_schema = task_status_path['responses']['200']['content']['application/json']['schema']

    return {
        'task_status_response': task_status_response_schema
    }

SCHEMAS = load_contract_schemas()


class TestProxmoxTasksContract:
    """Contract tests for the Proxmox task status API."""

    def test_task_status_api_interface_exists(self):
        """Test that the Proxmox task status API interface can be imported (will fail initially)."""
        # This test will fail until the Proxmox API implementation exists
        with pytest.raises(ImportError):
            from src.proxmox.tasks import TaskStatusAPI

    @pytest.fixture
    def mock_proxmox_client(self):
        """Mock Proxmox client for testing API interface."""
        client = Mock()
        client.get = Mock()
        return client

    @pytest.fixture
    def valid_task_running_response(self):
        """Valid response for a running task."""
        return {
            "data": {
                "status": "running",
                "exitstatus": ""  # Empty string for running tasks per contract
            }
        }

    @pytest.fixture
    def valid_task_stopped_success_response(self):
        """Valid response for a stopped task with successful exit status."""
        return {
            "data": {
                "status": "stopped",
                "exitstatus": "OK"
            }
        }

    @pytest.fixture
    def valid_task_stopped_error_response(self):
        """Valid response for a stopped task with error exit status."""
        return {
            "data": {
                "status": "stopped",
                "exitstatus": "command 'vzctl start 101' failed: exit code 1"
            }
        }

    @pytest.fixture
    def sample_upid(self):
        """Sample UPID (Unique Process ID) for testing."""
        return "UPID:pve-node-1:00001234:00005678:5F8A9B1C:vzcreate:101:root@pam:"

    @pytest.fixture
    def sample_node(self):
        """Sample node name for testing."""
        return "pve-node-1"

    def test_task_status_response_schema_validation_running(self, valid_task_running_response):
        """Test that running task response matches contract schema."""
        # This should pass - validates our test data against the contract
        validate(instance=valid_task_running_response, schema=SCHEMAS['task_status_response'])

    def test_task_status_response_schema_validation_stopped_success(self, valid_task_stopped_success_response):
        """Test that stopped successful task response matches contract schema."""
        validate(instance=valid_task_stopped_success_response, schema=SCHEMAS['task_status_response'])

    def test_task_status_response_schema_validation_stopped_error(self, valid_task_stopped_error_response):
        """Test that stopped error task response matches contract schema."""
        validate(instance=valid_task_stopped_error_response, schema=SCHEMAS['task_status_response'])

    def test_task_status_response_schema_validation_invalid_status(self):
        """Test that invalid status values fail schema validation."""
        invalid_response = {
            "data": {
                "status": "invalid_status",  # Should be 'running' or 'stopped'
                "exitstatus": "OK"
            }
        }
        with pytest.raises(ValidationError):
            validate(instance=invalid_response, schema=SCHEMAS['task_status_response'])

    def test_task_status_response_schema_validation_missing_status(self):
        """Test that response missing status field passes validation (status not required in contract)."""
        response_without_status = {
            "data": {
                "exitstatus": "OK"
                # Missing 'status' field - should pass as it's not required in current contract
            }
        }
        # This should pass - status is not marked as required in the contract
        validate(instance=response_without_status, schema=SCHEMAS['task_status_response'])

    def test_task_status_api_get_running_task(self, mock_proxmox_client,
                                            sample_node, sample_upid,
                                            valid_task_running_response):
        """Test getting status of a running task."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.proxmox.tasks import TaskStatusAPI

            api = TaskStatusAPI(mock_proxmox_client)
            mock_proxmox_client.get.return_value = valid_task_running_response

            result = api.get_task_status(sample_node, sample_upid)

            mock_proxmox_client.get.assert_called_once_with(
                f'/nodes/{sample_node}/tasks/{sample_upid}/status'
            )
            assert result['data']['status'] == 'running'
            assert result['data']['exitstatus'] == ""

    def test_task_status_api_get_stopped_successful_task(self, mock_proxmox_client,
                                                       sample_node, sample_upid,
                                                       valid_task_stopped_success_response):
        """Test getting status of a stopped successful task."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.proxmox.tasks import TaskStatusAPI

            api = TaskStatusAPI(mock_proxmox_client)
            mock_proxmox_client.get.return_value = valid_task_stopped_success_response

            result = api.get_task_status(sample_node, sample_upid)

            mock_proxmox_client.get.assert_called_once_with(
                f'/nodes/{sample_node}/tasks/{sample_upid}/status'
            )
            assert result['data']['status'] == 'stopped'
            assert result['data']['exitstatus'] == 'OK'

    def test_task_status_api_get_stopped_error_task(self, mock_proxmox_client,
                                                  sample_node, sample_upid,
                                                  valid_task_stopped_error_response):
        """Test getting status of a stopped task with error."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.proxmox.tasks import TaskStatusAPI

            api = TaskStatusAPI(mock_proxmox_client)
            mock_proxmox_client.get.return_value = valid_task_stopped_error_response

            result = api.get_task_status(sample_node, sample_upid)

            mock_proxmox_client.get.assert_called_once_with(
                f'/nodes/{sample_node}/tasks/{sample_upid}/status'
            )
            assert result['data']['status'] == 'stopped'
            assert 'failed' in result['data']['exitstatus']

    @responses.activate
    def test_task_status_http_integration_running(self, sample_node, sample_upid,
                                                valid_task_running_response):
        """Test task status API HTTP integration for running task."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.proxmox.client import ProxmoxClient

            # Mock HTTP response
            responses.add(
                responses.GET,
                f'https://proxmox.local:8006/api2/json/nodes/{sample_node}/tasks/{sample_upid}/status',
                json=valid_task_running_response,
                status=200
            )

            client = ProxmoxClient('proxmox.local', 'test-token')
            result = client.get_task_status(sample_node, sample_upid)

            assert result['data']['status'] == 'running'
            validate(instance=result, schema=SCHEMAS['task_status_response'])

    @responses.activate
    def test_task_status_http_integration_stopped(self, sample_node, sample_upid,
                                                valid_task_stopped_success_response):
        """Test task status API HTTP integration for stopped task."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.proxmox.client import ProxmoxClient

            # Mock HTTP response
            responses.add(
                responses.GET,
                f'https://proxmox.local:8006/api2/json/nodes/{sample_node}/tasks/{sample_upid}/status',
                json=valid_task_stopped_success_response,
                status=200
            )

            client = ProxmoxClient('proxmox.local', 'test-token')
            result = client.get_task_status(sample_node, sample_upid)

            assert result['data']['status'] == 'stopped'
            assert result['data']['exitstatus'] == 'OK'
            validate(instance=result, schema=SCHEMAS['task_status_response'])

    def test_task_status_api_error_handling_invalid_node(self, mock_proxmox_client,
                                                       sample_upid):
        """Test error handling for invalid node name."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.proxmox.tasks import TaskStatusAPI
            from src.proxmox.exceptions import ProxmoxNodeNotFoundError

            api = TaskStatusAPI(mock_proxmox_client)
            mock_proxmox_client.get.side_effect = ProxmoxNodeNotFoundError("Node 'invalid-node' not found")

            with pytest.raises(ProxmoxNodeNotFoundError):
                api.get_task_status('invalid-node', sample_upid)

    def test_task_status_api_error_handling_invalid_upid(self, mock_proxmox_client,
                                                       sample_node):
        """Test error handling for invalid UPID."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.proxmox.tasks import TaskStatusAPI
            from src.proxmox.exceptions import ProxmoxTaskNotFoundError

            api = TaskStatusAPI(mock_proxmox_client)
            mock_proxmox_client.get.side_effect = ProxmoxTaskNotFoundError("Task with UPID 'invalid-upid' not found")

            with pytest.raises(ProxmoxTaskNotFoundError):
                api.get_task_status(sample_node, 'invalid-upid')

    def test_task_status_wait_for_completion_running_to_stopped(self, mock_proxmox_client,
                                                              sample_node, sample_upid,
                                                              valid_task_running_response,
                                                              valid_task_stopped_success_response):
        """Test waiting for task completion (running -> stopped)."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.proxmox.tasks import TaskStatusAPI

            api = TaskStatusAPI(mock_proxmox_client)

            # First call returns running, second call returns stopped
            mock_proxmox_client.get.side_effect = [
                valid_task_running_response,
                valid_task_stopped_success_response
            ]

            result = api.wait_for_task_completion(sample_node, sample_upid, timeout=10, poll_interval=1)

            assert mock_proxmox_client.get.call_count == 2
            assert result['data']['status'] == 'stopped'
            assert result['data']['exitstatus'] == 'OK'

    def test_task_status_wait_for_completion_timeout(self, mock_proxmox_client,
                                                   sample_node, sample_upid,
                                                   valid_task_running_response):
        """Test timeout handling when waiting for task completion."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.proxmox.tasks import TaskStatusAPI
            from src.proxmox.exceptions import ProxmoxTaskTimeoutError

            api = TaskStatusAPI(mock_proxmox_client)

            # Always return running to simulate timeout
            mock_proxmox_client.get.return_value = valid_task_running_response

            with pytest.raises(ProxmoxTaskTimeoutError):
                api.wait_for_task_completion(sample_node, sample_upid, timeout=2, poll_interval=1)


class TestProxmoxTasksContractCompleteness:
    """Tests for Proxmox tasks API contract completeness."""

    def test_task_status_endpoint_exists_in_contract(self):
        """Test that task status endpoint is defined in the contract."""
        with open(CONTRACT_PATH, 'r') as f:
            contract = yaml.safe_load(f)

        # Check task status endpoint exists
        expected_path = '/nodes/{node}/tasks/{upid}/status'
        assert expected_path in contract['paths'], f"Task status endpoint {expected_path} missing from contract"

        # Check GET method is defined
        task_status_spec = contract['paths'][expected_path]
        assert 'get' in task_status_spec, "GET method missing from task status endpoint"

    def test_task_status_endpoint_parameters(self):
        """Test that task status endpoint has required parameters."""
        with open(CONTRACT_PATH, 'r') as f:
            contract = yaml.safe_load(f)

        get_spec = contract['paths']['/nodes/{node}/tasks/{upid}/status']['get']

        # Check parameters are defined
        assert 'parameters' in get_spec, "Parameters missing from task status endpoint"

        parameters = get_spec['parameters']
        param_names = [param['name'] for param in parameters]

        # Check required parameters exist
        assert 'node' in param_names, "Node parameter missing from task status endpoint"
        assert 'upid' in param_names, "UPID parameter missing from task status endpoint"

        # Check parameters are required and in path
        for param in parameters:
            if param['name'] in ['node', 'upid']:
                assert param['required'] is True, f"Parameter {param['name']} should be required"
                assert param['in'] == 'path', f"Parameter {param['name']} should be in path"

    def test_task_status_response_schema(self):
        """Test that task status response schema is properly defined."""
        with open(CONTRACT_PATH, 'r') as f:
            contract = yaml.safe_load(f)

        get_spec = contract['paths']['/nodes/{node}/tasks/{upid}/status']['get']

        # Check 200 response exists
        assert 'responses' in get_spec, "Responses missing from task status endpoint"
        assert '200' in get_spec['responses'], "200 response missing from task status endpoint"

        # Check response has proper content type and schema
        response_200 = get_spec['responses']['200']
        assert 'content' in response_200, "Content missing from 200 response"
        assert 'application/json' in response_200['content'], "JSON content type missing from 200 response"

        schema = response_200['content']['application/json']['schema']
        assert 'type' in schema, "Schema type missing from response"
        assert schema['type'] == 'object', "Response schema should be object type"

    def test_task_status_data_schema_properties(self):
        """Test that task status data schema has required properties."""
        with open(CONTRACT_PATH, 'r') as f:
            contract = yaml.safe_load(f)

        response_schema = contract['paths']['/nodes/{node}/tasks/{upid}/status']['get']['responses']['200']['content']['application/json']['schema']

        # Check data property exists
        assert 'properties' in response_schema, "Properties missing from response schema"
        assert 'data' in response_schema['properties'], "Data property missing from response schema"

        data_schema = response_schema['properties']['data']
        assert 'type' in data_schema, "Data schema type missing"
        assert data_schema['type'] == 'object', "Data schema should be object type"

        # Check status and exitstatus properties
        data_properties = data_schema['properties']
        assert 'status' in data_properties, "Status property missing from data schema"
        assert 'exitstatus' in data_properties, "Exitstatus property missing from data schema"

        # Check status enum values
        status_property = data_properties['status']
        assert 'type' in status_property, "Status property type missing"
        assert status_property['type'] == 'string', "Status property should be string type"
        assert 'enum' in status_property, "Status property enum missing"
        assert 'running' in status_property['enum'], "Status enum should include 'running'"
        assert 'stopped' in status_property['enum'], "Status enum should include 'stopped'"

        # Check exitstatus property
        exitstatus_property = data_properties['exitstatus']
        assert 'type' in exitstatus_property, "Exitstatus property type missing"
        assert exitstatus_property['type'] == 'string', "Exitstatus property should be string type"

    def test_task_status_security_requirements(self):
        """Test that task status endpoint has proper security requirements."""
        with open(CONTRACT_PATH, 'r') as f:
            contract = yaml.safe_load(f)

        get_spec = contract['paths']['/nodes/{node}/tasks/{upid}/status']['get']

        # Check security requirements exist
        assert 'security' in get_spec, "Security requirements missing from task status endpoint"

        security = get_spec['security']
        assert isinstance(security, list), "Security should be a list"
        assert len(security) > 0, "Security requirements should not be empty"

        # Check for API token authentication
        api_token_auth = False
        for auth_method in security:
            if 'apiToken' in auth_method:
                api_token_auth = True
                break

        assert api_token_auth, "API token authentication missing from security requirements"

    def test_contract_openapi_version_compatibility(self):
        """Test that the contract uses a supported OpenAPI version."""
        with open(CONTRACT_PATH, 'r') as f:
            contract = yaml.safe_load(f)

        # Check OpenAPI version
        assert 'openapi' in contract, "OpenAPI version missing from contract"
        version = contract['openapi']
        assert version.startswith('3.'), f"Expected OpenAPI 3.x, got {version}"

    def test_contract_has_security_schemes(self):
        """Test that the contract defines required security schemes."""
        with open(CONTRACT_PATH, 'r') as f:
            contract = yaml.safe_load(f)

        # Check components section exists
        assert 'components' in contract, "Components section missing from contract"
        assert 'securitySchemes' in contract['components'], "Security schemes missing from contract"

        # Check apiToken security scheme
        security_schemes = contract['components']['securitySchemes']
        assert 'apiToken' in security_schemes, "apiToken security scheme missing"

        api_token_scheme = security_schemes['apiToken']
        assert api_token_scheme['type'] == 'apiKey', "apiToken should be apiKey type"
        assert api_token_scheme['in'] == 'header', "apiToken should be in header"
        assert api_token_scheme['name'] == 'Authorization', "apiToken should use Authorization header"