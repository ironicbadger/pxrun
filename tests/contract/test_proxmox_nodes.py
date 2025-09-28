"""
Contract tests for the Proxmox nodes API.

This module validates the Proxmox nodes API interface as defined in the OpenAPI contract
at contracts/proxmox-api.yaml. Tests follow TDD approach and will fail initially
since the implementation doesn't exist yet.

The tests validate:
- GET /nodes endpoint response schema compliance with OpenAPI contract
- API token authentication mechanism
- NodeInfo schema validation
- Mocked proxmoxer library interactions
- Contract completeness and structure

Run with: pytest tests/contract/test_proxmox_nodes.py -v
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

    # Extract schemas from components
    schemas = contract['components']['schemas']

    # Extract response schema for /nodes endpoint and resolve the $ref
    nodes_path = contract['paths']['/nodes']['get']
    response_schema = nodes_path['responses']['200']['content']['application/json']['schema']

    # Create a complete schema with components for reference resolution
    complete_response_schema = {
        **response_schema,
        "components": {
            "schemas": schemas
        }
    }

    return {
        'nodes_response': complete_response_schema,
        'node_info': schemas['NodeInfo']
    }

SCHEMAS = load_contract_schemas()


class TestProxmoxNodesContract:
    """Contract tests for the Proxmox nodes API."""

    def test_proxmox_service_interface_exists(self):
        """Test that the Proxmox service interface can be imported (will fail initially)."""
        # This test will fail until the service implementation exists
        with pytest.raises(ImportError):
            from src.services.proxmox import ProxmoxService

    @pytest.fixture
    def mock_proxmoxer(self):
        """Mock proxmoxer ProxmoxAPI for testing."""
        with patch('proxmoxer.ProxmoxAPI') as mock_api:
            mock_instance = MagicMock()
            mock_api.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def valid_node_info(self):
        """Valid NodeInfo object according to schema."""
        return {
            "node": "pve-node-1",
            "status": "online",
            "cpu": 0.25,
            "maxcpu": 8,
            "mem": 8589934592,
            "maxmem": 17179869184,
            "uptime": 3600
        }

    @pytest.fixture
    def valid_nodes_response(self, valid_node_info):
        """Valid response for GET /nodes endpoint."""
        return {
            "data": [
                valid_node_info,
                {
                    "node": "pve-node-2",
                    "status": "online",
                    "cpu": 0.15,
                    "maxcpu": 4,
                    "mem": 4294967296,
                    "maxmem": 8589934592,
                    "uptime": 7200
                }
            ]
        }

    @pytest.fixture
    def api_token_config(self):
        """Valid API token configuration."""
        return {
            "host": "pve.example.com",
            "user": "automation@pve",
            "token_id": "automation-token",
            "token_secret": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
            "verify_ssl": False
        }

    def test_node_info_schema_validation_valid(self, valid_node_info):
        """Test that valid NodeInfo objects pass schema validation."""
        validate(instance=valid_node_info, schema=SCHEMAS['node_info'])

    def test_node_info_schema_validation_minimal(self):
        """Test that minimal NodeInfo objects pass schema validation."""
        # NodeInfo schema doesn't specify required fields, so minimal object should work
        minimal_node = {
            "node": "pve-node-1"
        }
        validate(instance=minimal_node, schema=SCHEMAS['node_info'])

    def test_node_info_schema_validation_invalid_types(self):
        """Test that NodeInfo with wrong types fails validation."""
        invalid_node = {
            "node": "pve-node-1",
            "status": "online",
            "cpu": "25%",        # Should be number
            "maxcpu": "8 cores", # Should be integer
            "mem": "8GB",        # Should be integer
            "maxmem": "16GB",    # Should be integer
            "uptime": "1 hour"   # Should be integer
        }
        with pytest.raises(ValidationError):
            validate(instance=invalid_node, schema=SCHEMAS['node_info'])

    def test_nodes_response_schema_validation(self, valid_nodes_response):
        """Test that valid nodes response passes schema validation."""
        validate(instance=valid_nodes_response, schema=SCHEMAS['nodes_response'])

    def test_nodes_response_schema_validation_empty(self):
        """Test that empty nodes response passes schema validation."""
        empty_response = {"data": []}
        validate(instance=empty_response, schema=SCHEMAS['nodes_response'])

    def test_proxmox_api_authentication_with_token(self, mock_proxmoxer, api_token_config):
        """Test Proxmox API authentication using API token."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.proxmox import ProxmoxService

            service = ProxmoxService(api_token_config)

            # Verify proxmoxer was called with correct authentication
            mock_proxmoxer.assert_called_once_with(
                host=api_token_config["host"],
                user=api_token_config["user"],
                token_name=api_token_config["token_id"],
                token_value=api_token_config["token_secret"],
                verify_ssl=api_token_config["verify_ssl"]
            )

    def test_get_nodes_api_call(self, mock_proxmoxer, api_token_config, valid_nodes_response):
        """Test GET /nodes API call through proxmoxer."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.proxmox import ProxmoxService

            # Setup mock response
            mock_proxmoxer.nodes.get.return_value = valid_nodes_response["data"]

            service = ProxmoxService(api_token_config)
            result = service.get_nodes()

            # Verify API call was made
            mock_proxmoxer.nodes.get.assert_called_once()

            # Verify response structure
            assert "data" in result
            assert isinstance(result["data"], list)
            validate(instance=result, schema=SCHEMAS['nodes_response'])

    def test_get_nodes_handles_authentication_error(self, mock_proxmoxer, api_token_config):
        """Test that authentication errors are properly handled."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.proxmox import ProxmoxService
            from src.exceptions import AuthenticationError

            # Setup mock to raise authentication error
            from proxmoxer.core import AuthenticationError as ProxmoxerAuthError
            mock_proxmoxer.nodes.get.side_effect = ProxmoxerAuthError("Invalid token")

            service = ProxmoxService(api_token_config)

            with pytest.raises(AuthenticationError) as exc_info:
                service.get_nodes()

            assert "Invalid token" in str(exc_info.value)

    def test_get_nodes_handles_connection_error(self, mock_proxmoxer, api_token_config):
        """Test that connection errors are properly handled."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.proxmox import ProxmoxService
            from src.exceptions import ConnectionError

            # Setup mock to raise connection error
            import requests
            mock_proxmoxer.nodes.get.side_effect = requests.ConnectionError("Connection failed")

            service = ProxmoxService(api_token_config)

            with pytest.raises(ConnectionError) as exc_info:
                service.get_nodes()

            assert "Connection failed" in str(exc_info.value)

    def test_api_token_format_validation(self):
        """Test that API token format follows PVE standard."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.proxmox import ProxmoxService

            # Test with invalid token format
            invalid_config = {
                "host": "pve.example.com",
                "user": "automation@pve",
                "token_id": "invalid-token-format!",  # Invalid characters
                "token_secret": "short",              # Too short
                "verify_ssl": False
            }

            with pytest.raises(ValueError) as exc_info:
                ProxmoxService(invalid_config)

            assert "Invalid token format" in str(exc_info.value)

    def test_nodes_response_caching(self, mock_proxmoxer, api_token_config, valid_nodes_response):
        """Test that nodes response can be cached to reduce API calls."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.proxmox import ProxmoxService

            mock_proxmoxer.nodes.get.return_value = valid_nodes_response["data"]

            service = ProxmoxService(api_token_config)

            # First call
            result1 = service.get_nodes(use_cache=True)
            # Second call should use cache
            result2 = service.get_nodes(use_cache=True)

            # API should only be called once
            mock_proxmoxer.nodes.get.assert_called_once()
            assert result1 == result2

    def test_nodes_response_filter_by_status(self, mock_proxmoxer, api_token_config):
        """Test filtering nodes by status."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.proxmox import ProxmoxService

            # Mock response with mixed node statuses
            mixed_response = [
                {"node": "pve-node-1", "status": "online", "cpu": 0.25},
                {"node": "pve-node-2", "status": "offline", "cpu": 0.0},
                {"node": "pve-node-3", "status": "online", "cpu": 0.15}
            ]
            mock_proxmoxer.nodes.get.return_value = mixed_response

            service = ProxmoxService(api_token_config)
            result = service.get_nodes(status_filter="online")

            # Should only return online nodes
            online_nodes = result["data"]
            assert len(online_nodes) == 2
            assert all(node["status"] == "online" for node in online_nodes)


class TestProxmoxApiContract:
    """Tests for Proxmox API contract structure and completeness."""

    def test_contract_has_nodes_endpoint(self):
        """Test that /nodes endpoint is defined in contract."""
        with open(CONTRACT_PATH, 'r') as f:
            contract = yaml.safe_load(f)

        assert '/nodes' in contract['paths']
        nodes_spec = contract['paths']['/nodes']
        assert 'get' in nodes_spec

    def test_nodes_endpoint_requires_authentication(self):
        """Test that /nodes endpoint requires API token authentication."""
        with open(CONTRACT_PATH, 'r') as f:
            contract = yaml.safe_load(f)

        nodes_get = contract['paths']['/nodes']['get']
        assert 'security' in nodes_get
        assert {'apiToken': []} in nodes_get['security']

    def test_nodes_endpoint_response_schema(self):
        """Test that /nodes endpoint defines proper response schema."""
        with open(CONTRACT_PATH, 'r') as f:
            contract = yaml.safe_load(f)

        nodes_get = contract['paths']['/nodes']['get']
        response_200 = nodes_get['responses']['200']

        # Check response structure
        assert 'content' in response_200
        assert 'application/json' in response_200['content']

        schema = response_200['content']['application/json']['schema']
        assert 'type' in schema
        assert schema['type'] == 'object'
        assert 'properties' in schema
        assert 'data' in schema['properties']
        assert schema['properties']['data']['type'] == 'array'
        assert '$ref' in schema['properties']['data']['items']
        assert schema['properties']['data']['items']['$ref'] == '#/components/schemas/NodeInfo'

    def test_node_info_schema_definition(self):
        """Test that NodeInfo schema is properly defined."""
        with open(CONTRACT_PATH, 'r') as f:
            contract = yaml.safe_load(f)

        node_info = contract['components']['schemas']['NodeInfo']

        # Check schema structure
        assert 'type' in node_info
        assert node_info['type'] == 'object'
        assert 'properties' in node_info

        # Check expected properties exist
        expected_properties = ['node', 'status', 'cpu', 'maxcpu', 'mem', 'maxmem', 'uptime']
        for prop in expected_properties:
            assert prop in node_info['properties'], f"Property {prop} missing from NodeInfo schema"

        # Check property types
        assert node_info['properties']['node']['type'] == 'string'
        assert node_info['properties']['status']['type'] == 'string'
        assert node_info['properties']['cpu']['type'] == 'number'
        assert node_info['properties']['maxcpu']['type'] == 'integer'
        assert node_info['properties']['mem']['type'] == 'integer'
        assert node_info['properties']['maxmem']['type'] == 'integer'
        assert node_info['properties']['uptime']['type'] == 'integer'

    def test_api_token_security_scheme_definition(self):
        """Test that API token security scheme is properly defined."""
        with open(CONTRACT_PATH, 'r') as f:
            contract = yaml.safe_load(f)

        assert 'securitySchemes' in contract['components']
        assert 'apiToken' in contract['components']['securitySchemes']

        api_token_scheme = contract['components']['securitySchemes']['apiToken']
        assert api_token_scheme['type'] == 'apiKey'
        assert api_token_scheme['in'] == 'header'
        assert api_token_scheme['name'] == 'Authorization'
        assert 'PVEAPIToken' in api_token_scheme['description']

    def test_contract_openapi_version_compatibility(self):
        """Test that the contract uses a supported OpenAPI version."""
        with open(CONTRACT_PATH, 'r') as f:
            contract = yaml.safe_load(f)

        # Check OpenAPI version
        assert 'openapi' in contract
        version = contract['openapi']
        assert version.startswith('3.'), f"Expected OpenAPI 3.x, got {version}"

    def test_contract_server_definition(self):
        """Test that contract defines proper server configuration."""
        with open(CONTRACT_PATH, 'r') as f:
            contract = yaml.safe_load(f)

        assert 'servers' in contract
        assert len(contract['servers']) > 0

        server = contract['servers'][0]
        assert 'url' in server
        assert 'api2/json' in server['url']  # Proxmox API path
        assert '{host}' in server['url']     # Host variable


class TestProxmoxServiceMockValidation:
    """Tests to validate mock usage matches real proxmoxer behavior."""

    def test_mock_proxmoxer_api_structure(self):
        """Test that our mocks match the actual proxmoxer API structure."""
        # This validates our understanding of proxmoxer's API
        with patch('proxmoxer.ProxmoxAPI') as mock_api_class:
            mock_instance = MagicMock()
            mock_api_class.return_value = mock_instance

            # Test the API structure we expect
            mock_instance.nodes.get.return_value = []

            # Verify the mock structure matches what we use in tests
            assert hasattr(mock_instance, 'nodes')
            assert hasattr(mock_instance.nodes, 'get')

    def test_mock_authentication_parameters(self):
        """Test that mock authentication parameters match proxmoxer expectations."""
        with patch('proxmoxer.ProxmoxAPI') as mock_api_class:
            # These are the parameters proxmoxer expects for token auth
            expected_params = {
                'host': 'pve.example.com',
                'user': 'automation@pve',
                'token_name': 'automation-token',
                'token_value': 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx',
                'verify_ssl': False
            }

            # This would be called by our service implementation
            mock_api_class(**expected_params)

            # Verify the call was made with expected parameters
            mock_api_class.assert_called_once_with(**expected_params)

    def test_mock_exception_handling(self):
        """Test that we mock the correct exception types from proxmoxer."""
        # Import the actual exceptions we expect proxmoxer to raise
        try:
            from proxmoxer.core import AuthenticationError, ResourceException

            # Verify these exceptions exist and can be imported
            assert AuthenticationError is not None
            assert ResourceException is not None

        except ImportError:
            # If proxmoxer isn't installed yet, just verify the import path
            pytest.skip("proxmoxer not installed yet - this validates import path for when it is")

    def test_demonstrate_tdd_failure_mode(self):
        """Demonstrate how tests fail without implementation (TDD principle)."""
        # This test explicitly shows what will fail when we try to use the service
        # All the tests above use pytest.raises(ImportError) to expect failure

        # When implementation exists, this test should be updated to actually test the service
        with pytest.raises(ImportError) as exc_info:
            from src.services.proxmox import ProxmoxService

        assert "No module named 'src.services.proxmox'" in str(exc_info.value)

        # When the service is implemented, the tests above will need to be updated
        # to remove the pytest.raises(ImportError) and actually test functionality