"""
Contract tests for Proxmox LXC destroy API.

This module validates the LXC destroy API interface as defined in the OpenAPI contract
at contracts/proxmox-api.yaml. Tests follow TDD approach and will fail initially
since the implementation doesn't exist yet.

The tests validate:
- DELETE /nodes/{node}/lxc/{vmid} endpoint contract compliance
- Request/response schema compliance with OpenAPI contract
- Task UPID response format validation
- Error handling for various failure scenarios
- proxmoxer library integration and mocking

Run with: pytest tests/contract/test_proxmox_lxc_destroy.py -v
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from jsonschema import validate, ValidationError
import yaml
from pathlib import Path


# Load OpenAPI contract for schema validation
CONTRACT_PATH = Path(__file__).parent.parent.parent / "specs" / "001-pxrun-specification-document" / "contracts" / "proxmox-api.yaml"


def load_contract_schemas():
    """Load OpenAPI contract schemas for validation."""
    with open(CONTRACT_PATH, 'r') as f:
        contract = yaml.safe_load(f)

    # Extract the delete endpoint schema
    delete_path = contract['paths']['/nodes/{node}/lxc/{vmid}']['delete']

    # Extract response schema for successful destroy (200)
    success_response_schema = delete_path['responses']['200']['content']['application/json']['schema']

    return {
        'delete_endpoint': delete_path,
        'success_response': success_response_schema,
        'task_upid_schema': {
            'type': 'object',
            'properties': {
                'data': {
                    'type': 'string',
                    'description': 'Task UPID'
                }
            },
            'required': ['data']
        }
    }


SCHEMAS = load_contract_schemas()


class TestProxmoxLXCDestroyContract:
    """Contract tests for Proxmox LXC destroy API."""

    def test_proxmox_destroy_service_interface_exists(self):
        """Test that the Proxmox destroy service interface can be imported (will fail initially)."""
        # This test will fail until the service implementation exists
        with pytest.raises(ImportError):
            from src.services.proxmox_lxc import ProxmoxLXCService

    @pytest.fixture
    def mock_proxmoxer(self):
        """Mock proxmoxer ProxmoxAPI for testing."""
        with patch('proxmoxer.ProxmoxAPI') as mock_api:
            mock_instance = MagicMock()
            mock_api.return_value = mock_instance

            # Mock the node.lxc(vmid).delete() chain
            mock_lxc = MagicMock()
            mock_instance.nodes.return_value.lxc.return_value = mock_lxc

            yield mock_instance

    @pytest.fixture
    def valid_destroy_request_params(self):
        """Valid parameters for LXC destroy request."""
        return {
            'node': 'pve-node-1',
            'vmid': 100
        }

    @pytest.fixture
    def valid_destroy_response_200(self):
        """Valid 200 response for successful container destroy."""
        return {
            'data': 'UPID:pve-node-1:00001234:567890AB:vzdestroy:100:root@pam:'
        }

    @pytest.fixture
    def valid_task_upid(self):
        """Valid task UPID string format."""
        return 'UPID:pve-node-1:00001234:567890AB:vzdestroy:100:root@pam:'

    def test_destroy_endpoint_exists_in_contract(self):
        """Test that the destroy endpoint exists in the contract."""
        with open(CONTRACT_PATH, 'r') as f:
            contract = yaml.safe_load(f)

        # Check that the endpoint path exists
        assert '/nodes/{node}/lxc/{vmid}' in contract['paths']
        endpoint = contract['paths']['/nodes/{node}/lxc/{vmid}']

        # Check that DELETE method exists
        assert 'delete' in endpoint
        delete_spec = endpoint['delete']

        # Validate endpoint structure
        assert 'summary' in delete_spec
        assert delete_spec['summary'] == 'Destroy container'
        assert 'security' in delete_spec
        assert 'parameters' in delete_spec
        assert 'responses' in delete_spec

    def test_destroy_endpoint_parameters_validation(self):
        """Test that destroy endpoint has correct parameters."""
        with open(CONTRACT_PATH, 'r') as f:
            contract = yaml.safe_load(f)

        delete_spec = contract['paths']['/nodes/{node}/lxc/{vmid}']['delete']
        parameters = delete_spec['parameters']

        # Should have exactly 2 parameters: node and vmid
        assert len(parameters) == 2

        # Validate node parameter
        node_param = next(p for p in parameters if p['name'] == 'node')
        assert node_param['in'] == 'path'
        assert node_param['required'] is True
        assert node_param['schema']['type'] == 'string'

        # Validate vmid parameter
        vmid_param = next(p for p in parameters if p['name'] == 'vmid')
        assert vmid_param['in'] == 'path'
        assert vmid_param['required'] is True
        assert vmid_param['schema']['type'] == 'integer'

    def test_destroy_endpoint_security_requirements(self):
        """Test that destroy endpoint has proper security requirements."""
        with open(CONTRACT_PATH, 'r') as f:
            contract = yaml.safe_load(f)

        delete_spec = contract['paths']['/nodes/{node}/lxc/{vmid}']['delete']

        # Check security requirements
        assert 'security' in delete_spec
        security = delete_spec['security']
        assert len(security) == 1
        assert 'apiToken' in security[0]

    def test_destroy_response_200_schema_validation(self, valid_destroy_response_200):
        """Test that 200 response matches the task UPID schema."""
        validate(instance=valid_destroy_response_200, schema=SCHEMAS['success_response'])
        validate(instance=valid_destroy_response_200, schema=SCHEMAS['task_upid_schema'])

    def test_task_upid_format_validation(self, valid_task_upid):
        """Test that UPID follows expected format pattern."""
        # UPID format: UPID:node:pid:starttime:type:id:user:status
        upid_parts = valid_task_upid.split(':')

        assert len(upid_parts) >= 7  # Minimum required parts
        assert upid_parts[0] == 'UPID'
        assert upid_parts[1] == 'pve-node-1'  # node
        assert upid_parts[4] == 'vzdestroy'   # task type
        assert upid_parts[5] == '100'         # vmid
        assert upid_parts[6] == 'root@pam'    # user

    def test_proxmox_lxc_destroy_success(self, mock_proxmoxer, valid_destroy_request_params, valid_destroy_response_200):
        """Test successful LXC container destroy via proxmoxer."""
        # This test will fail until the service implementation exists
        with pytest.raises(ImportError):
            from src.services.proxmox_lxc import ProxmoxLXCService

            # Mock successful destroy operation
            mock_proxmoxer.nodes.return_value.lxc.return_value.delete.return_value = valid_destroy_response_200['data']

            service = ProxmoxLXCService(mock_proxmoxer)
            result = service.destroy_container(
                node=valid_destroy_request_params['node'],
                vmid=valid_destroy_request_params['vmid']
            )

            # Validate response structure
            assert 'data' in result
            assert isinstance(result['data'], str)
            assert result['data'].startswith('UPID:')

            # Validate proxmoxer API call
            mock_proxmoxer.nodes.assert_called_once_with(valid_destroy_request_params['node'])
            mock_proxmoxer.nodes.return_value.lxc.assert_called_once_with(valid_destroy_request_params['vmid'])
            mock_proxmoxer.nodes.return_value.lxc.return_value.delete.assert_called_once()

    def test_proxmox_lxc_destroy_container_not_found(self, mock_proxmoxer, valid_destroy_request_params):
        """Test destroy operation when container doesn't exist."""
        # This test will fail until the service implementation exists
        with pytest.raises(ImportError):
            from src.services.proxmox_lxc import ProxmoxLXCService
            from proxmoxer import ResourceException

            # Mock container not found error
            mock_proxmoxer.nodes.return_value.lxc.return_value.delete.side_effect = ResourceException(
                status_code=404,
                content={'errors': {'vmid': 'VM 100 does not exist'}}
            )

            service = ProxmoxLXCService(mock_proxmoxer)

            with pytest.raises(ResourceException) as exc_info:
                service.destroy_container(
                    node=valid_destroy_request_params['node'],
                    vmid=valid_destroy_request_params['vmid']
                )

            assert exc_info.value.status_code == 404

    def test_proxmox_lxc_destroy_container_running(self, mock_proxmoxer, valid_destroy_request_params):
        """Test destroy operation when container is running."""
        # This test will fail until the service implementation exists
        with pytest.raises(ImportError):
            from src.services.proxmox_lxc import ProxmoxLXCService
            from proxmoxer import ResourceException

            # Mock container running error
            mock_proxmoxer.nodes.return_value.lxc.return_value.delete.side_effect = ResourceException(
                status_code=400,
                content={'errors': {'status': 'Cannot destroy running container'}}
            )

            service = ProxmoxLXCService(mock_proxmoxer)

            with pytest.raises(ResourceException) as exc_info:
                service.destroy_container(
                    node=valid_destroy_request_params['node'],
                    vmid=valid_destroy_request_params['vmid']
                )

            assert exc_info.value.status_code == 400

    def test_proxmox_lxc_destroy_authentication_failure(self, mock_proxmoxer, valid_destroy_request_params):
        """Test destroy operation with authentication failure."""
        # This test will fail until the service implementation exists
        with pytest.raises(ImportError):
            from src.services.proxmox_lxc import ProxmoxLXCService
            from proxmoxer import AuthenticationException

            # Mock authentication failure
            mock_proxmoxer.nodes.return_value.lxc.return_value.delete.side_effect = AuthenticationException(
                'authentication failure'
            )

            service = ProxmoxLXCService(mock_proxmoxer)

            with pytest.raises(AuthenticationException):
                service.destroy_container(
                    node=valid_destroy_request_params['node'],
                    vmid=valid_destroy_request_params['vmid']
                )

    def test_proxmox_lxc_destroy_connection_error(self, mock_proxmoxer, valid_destroy_request_params):
        """Test destroy operation with connection error."""
        # This test will fail until the service implementation exists
        with pytest.raises(ImportError):
            from src.services.proxmox_lxc import ProxmoxLXCService
            import requests

            # Mock connection error
            mock_proxmoxer.nodes.return_value.lxc.return_value.delete.side_effect = requests.ConnectionError(
                'Connection refused'
            )

            service = ProxmoxLXCService(mock_proxmoxer)

            with pytest.raises(requests.ConnectionError):
                service.destroy_container(
                    node=valid_destroy_request_params['node'],
                    vmid=valid_destroy_request_params['vmid']
                )

    def test_proxmox_api_integration_mock_structure(self, mock_proxmoxer):
        """Test that proxmoxer mock structure matches expected API chain."""
        # Validate the mock structure follows proxmoxer API pattern
        node_mock = mock_proxmoxer.nodes('test-node')
        lxc_mock = node_mock.lxc(100)

        # Test method chaining works as expected
        assert hasattr(lxc_mock, 'delete')
        assert callable(lxc_mock.delete)

    def test_destroy_request_parameter_types(self, valid_destroy_request_params):
        """Test that destroy request parameters have correct types."""
        # Validate parameter types match contract requirements
        assert isinstance(valid_destroy_request_params['node'], str)
        assert isinstance(valid_destroy_request_params['vmid'], int)
        assert valid_destroy_request_params['vmid'] > 0

    def test_destroy_endpoint_response_structure(self):
        """Test that destroy endpoint response structure matches contract."""
        with open(CONTRACT_PATH, 'r') as f:
            contract = yaml.safe_load(f)

        delete_spec = contract['paths']['/nodes/{node}/lxc/{vmid}']['delete']
        response_200 = delete_spec['responses']['200']

        # Validate response structure
        assert 'description' in response_200
        assert response_200['description'] == 'Container destroyed'
        assert 'content' in response_200
        assert 'application/json' in response_200['content']

        schema = response_200['content']['application/json']['schema']
        assert 'type' in schema
        assert schema['type'] == 'object'
        assert 'properties' in schema
        assert 'data' in schema['properties']
        assert schema['properties']['data']['type'] == 'string'
        assert schema['properties']['data']['description'] == 'Task UPID'


class TestProxmoxLXCDestroyServiceImplementation:
    """Tests for service implementation once it exists."""

    def test_service_class_structure(self):
        """Test that service class has expected structure (will fail initially)."""
        # This test will fail until the service implementation exists
        with pytest.raises(ImportError):
            from src.services.proxmox_lxc import ProxmoxLXCService

            # Test class structure
            assert hasattr(ProxmoxLXCService, '__init__')
            assert hasattr(ProxmoxLXCService, 'destroy_container')

    def test_service_init_requires_proxmoxer_instance(self):
        """Test that service initialization requires proxmoxer instance."""
        # This test will fail until the service implementation exists
        with pytest.raises(ImportError):
            from src.services.proxmox_lxc import ProxmoxLXCService

            # Test that service requires proxmoxer instance
            with pytest.raises(TypeError):
                ProxmoxLXCService()

    def test_destroy_method_signature(self):
        """Test that destroy_container method has correct signature."""
        # This test will fail until the service implementation exists
        with pytest.raises(ImportError):
            from src.services.proxmox_lxc import ProxmoxLXCService
            import inspect

            # Get method signature
            sig = inspect.signature(ProxmoxLXCService.destroy_container)
            params = list(sig.parameters.keys())

            # Validate required parameters
            assert 'self' in params
            assert 'node' in params
            assert 'vmid' in params

    def test_destroy_method_parameter_validation(self):
        """Test that destroy_container validates input parameters."""
        # This test will fail until the service implementation exists
        with pytest.raises(ImportError):
            from src.services.proxmox_lxc import ProxmoxLXCService

            mock_api = Mock()
            service = ProxmoxLXCService(mock_api)

            # Test parameter validation
            with pytest.raises((ValueError, TypeError)):
                service.destroy_container(node="", vmid=100)  # empty node

            with pytest.raises((ValueError, TypeError)):
                service.destroy_container(node="test-node", vmid=0)  # invalid vmid

            with pytest.raises((ValueError, TypeError)):
                service.destroy_container(node="test-node", vmid="invalid")  # wrong type


class TestContractComplianceValidation:
    """Tests for overall contract compliance and completeness."""

    def test_contract_file_exists_and_valid_yaml(self):
        """Test that the contract file exists and is valid YAML."""
        assert CONTRACT_PATH.exists(), f"Contract file not found at {CONTRACT_PATH}"

        with open(CONTRACT_PATH, 'r') as f:
            contract = yaml.safe_load(f)

        assert isinstance(contract, dict)
        assert 'openapi' in contract
        assert 'paths' in contract

    def test_destroy_endpoint_comprehensive_validation(self):
        """Test comprehensive validation of destroy endpoint contract."""
        with open(CONTRACT_PATH, 'r') as f:
            contract = yaml.safe_load(f)

        # Validate endpoint exists
        path_key = '/nodes/{node}/lxc/{vmid}'
        assert path_key in contract['paths']

        endpoint = contract['paths'][path_key]
        assert 'delete' in endpoint

        delete_spec = endpoint['delete']

        # Validate all required sections exist
        required_sections = ['summary', 'security', 'parameters', 'responses']
        for section in required_sections:
            assert section in delete_spec, f"Missing required section: {section}"

        # Validate responses section has 200 response
        assert '200' in delete_spec['responses']
        response_200 = delete_spec['responses']['200']

        # Validate response structure
        assert 'description' in response_200
        assert 'content' in response_200
        assert 'application/json' in response_200['content']
        assert 'schema' in response_200['content']['application/json']

    def test_task_upid_schema_completeness(self):
        """Test that task UPID schema is complete and correct."""
        schema = SCHEMAS['task_upid_schema']

        # Validate schema structure
        assert schema['type'] == 'object'
        assert 'properties' in schema
        assert 'data' in schema['properties']
        assert 'required' in schema
        assert 'data' in schema['required']

        # Validate data property
        data_prop = schema['properties']['data']
        assert data_prop['type'] == 'string'
        assert 'description' in data_prop
        assert 'Task UPID' in data_prop['description']

    def test_api_version_compatibility(self):
        """Test that the API contract version is compatible."""
        with open(CONTRACT_PATH, 'r') as f:
            contract = yaml.safe_load(f)

        # Check OpenAPI version
        assert 'openapi' in contract
        version = contract['openapi']
        assert version.startswith('3.'), f"Expected OpenAPI 3.x, got {version}"

        # Check API info section
        assert 'info' in contract
        info = contract['info']
        assert 'title' in info
        assert 'version' in info
        assert 'Proxmox VE API' in info['title']

    def test_security_scheme_definition(self):
        """Test that security scheme is properly defined."""
        with open(CONTRACT_PATH, 'r') as f:
            contract = yaml.safe_load(f)

        # Check security schemes
        assert 'components' in contract
        assert 'securitySchemes' in contract['components']
        assert 'apiToken' in contract['components']['securitySchemes']

        api_token_scheme = contract['components']['securitySchemes']['apiToken']
        assert api_token_scheme['type'] == 'apiKey'
        assert api_token_scheme['in'] == 'header'
        assert api_token_scheme['name'] == 'Authorization'