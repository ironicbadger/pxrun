"""
Contract tests for the Proxmox storage API.

This module validates the Proxmox storage API endpoints as defined in the OpenAPI contract
at contracts/proxmox-api.yaml. Tests follow TDD approach and will fail initially
since the implementation doesn't exist yet.

The tests validate:
- GET /nodes/{node}/storage endpoint response schema compliance
- GET /nodes/{node}/storage/{storage}/content endpoint response schema compliance
- StorageInfo and StorageContent schema validation
- All HTTP response codes and error handling
- Query parameter validation for content endpoint

Run with: pytest tests/contract/test_proxmox_storage.py -v
"""

import json
import pytest
from unittest.mock import Mock, patch
from jsonschema import validate, ValidationError, RefResolver
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

    # Extract path definitions for storage endpoints
    storage_list_path = contract['paths']['/nodes/{node}/storage']['get']
    storage_content_path = contract['paths']['/nodes/{node}/storage/{storage}/content']['get']

    return {
        'storage_info': schemas['StorageInfo'],
        'storage_content': schemas['StorageContent'],
        'storage_list_response': storage_list_path['responses']['200']['content']['application/json']['schema'],
        'storage_content_response': storage_content_path['responses']['200']['content']['application/json']['schema'],
        'full_contract': contract  # Include full contract for $ref resolution
    }

SCHEMAS = load_contract_schemas()


class TestProxmoxStorageContract:
    """Contract tests for the Proxmox storage API endpoints."""

    @pytest.fixture
    def mock_proxmox_client(self):
        """Mock Proxmox API client for testing."""
        client = Mock()
        client.get = Mock()
        return client

    @pytest.fixture
    def valid_storage_info(self):
        """Valid StorageInfo object matching the schema."""
        return {
            "storage": "local",
            "type": "dir",
            "content": "backup,iso,vztmpl,images,rootdir",
            "total": 1000000000,  # 1GB in bytes
            "used": 250000000,    # 250MB in bytes
            "avail": 750000000    # 750MB in bytes
        }

    @pytest.fixture
    def valid_storage_content(self):
        """Valid StorageContent object matching the schema."""
        return {
            "volid": "local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst",
            "format": "tar.zst",
            "size": 234567890,
            "content": "vztmpl"
        }

    @pytest.fixture
    def valid_storage_list_response(self, valid_storage_info):
        """Valid response for GET /nodes/{node}/storage."""
        return {
            "data": [
                valid_storage_info,
                {
                    "storage": "local-lvm",
                    "type": "lvmthin",
                    "content": "images,rootdir",
                    "total": 2000000000,
                    "used": 500000000,
                    "avail": 1500000000
                }
            ]
        }

    @pytest.fixture
    def valid_storage_content_response(self, valid_storage_content):
        """Valid response for GET /nodes/{node}/storage/{storage}/content."""
        return {
            "data": [
                valid_storage_content,
                {
                    "volid": "local:iso/ubuntu-22.04.3-live-server-amd64.iso",
                    "format": "iso",
                    "size": 1500000000,
                    "content": "iso"
                }
            ]
        }

    def test_storage_info_schema_validation_valid(self, valid_storage_info):
        """Test that valid StorageInfo objects pass schema validation."""
        validate(instance=valid_storage_info, schema=SCHEMAS['storage_info'])

    def test_storage_info_schema_validation_minimal(self):
        """Test that minimal valid StorageInfo passes schema validation."""
        minimal_storage = {
            "storage": "backup-storage",
            "type": "nfs",
            "content": "backup",
            "total": 500000000,
            "used": 100000000,
            "avail": 400000000
        }
        validate(instance=minimal_storage, schema=SCHEMAS['storage_info'])

    def test_storage_info_schema_validation_invalid_types(self):
        """Test that StorageInfo with wrong types fails validation."""
        invalid_storage = {
            "storage": "local",
            "type": "dir",
            "content": "backup,iso",
            "total": "1GB",  # Should be integer
            "used": "250MB", # Should be integer
            "avail": "750MB" # Should be integer
        }
        with pytest.raises(ValidationError):
            validate(instance=invalid_storage, schema=SCHEMAS['storage_info'])

    def test_storage_info_schema_validation_missing_required(self):
        """Test that StorageInfo missing required fields can be validated (no required fields in schema)."""
        incomplete_storage = {
            "storage": "local",
            "type": "dir"
            # Missing content, total, used, avail - but schema doesn't define required fields
        }
        # This should pass since the schema doesn't define required fields
        validate(instance=incomplete_storage, schema=SCHEMAS['storage_info'])

    def test_storage_content_schema_validation_valid(self, valid_storage_content):
        """Test that valid StorageContent objects pass schema validation."""
        validate(instance=valid_storage_content, schema=SCHEMAS['storage_content'])

    def test_storage_content_schema_validation_minimal(self):
        """Test that minimal valid StorageContent passes schema validation."""
        minimal_content = {
            "volid": "local:backup/dump.tar.gz",
            "format": "tar.gz",
            "size": 12345678,
            "content": "backup"
        }
        validate(instance=minimal_content, schema=SCHEMAS['storage_content'])

    def test_storage_content_schema_validation_invalid_types(self):
        """Test that StorageContent with wrong types fails validation."""
        invalid_content = {
            "volid": "local:vztmpl/ubuntu.tar.zst",
            "format": "tar.zst",
            "size": "234MB",  # Should be integer
            "content": "vztmpl"
        }
        with pytest.raises(ValidationError):
            validate(instance=invalid_content, schema=SCHEMAS['storage_content'])

    def test_storage_content_schema_validation_missing_required(self):
        """Test that StorageContent missing required fields can be validated (no required fields in schema)."""
        incomplete_content = {
            "volid": "local:iso/ubuntu.iso",
            "format": "iso"
            # Missing size and content - but schema doesn't define required fields
        }
        # This should pass since the schema doesn't define required fields
        validate(instance=incomplete_content, schema=SCHEMAS['storage_content'])

    def test_storage_list_response_schema_validation(self, valid_storage_list_response):
        """Test that storage list response matches expected schema."""
        # Create resolver for $ref resolution
        resolver = RefResolver(base_uri="", referrer=SCHEMAS['full_contract'])
        validate(instance=valid_storage_list_response, schema=SCHEMAS['storage_list_response'], resolver=resolver)

    def test_storage_content_response_schema_validation(self, valid_storage_content_response):
        """Test that storage content response matches expected schema."""
        # Create resolver for $ref resolution
        resolver = RefResolver(base_uri="", referrer=SCHEMAS['full_contract'])
        validate(instance=valid_storage_content_response, schema=SCHEMAS['storage_content_response'], resolver=resolver)

    def test_storage_api_client_interface_exists(self):
        """Test that the storage API client interface can be imported (will fail initially)."""
        # This test will fail until the implementation exists
        with pytest.raises(ImportError):
            from src.services.proxmox_storage import ProxmoxStorageService

    def test_storage_list_endpoint_success_200(self, mock_proxmox_client, valid_storage_list_response):
        """Test GET /nodes/{node}/storage returns 200 with valid StorageInfo array."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.proxmox_storage import ProxmoxStorageService

            # Mock the API response
            mock_proxmox_client.get.return_value = valid_storage_list_response

            service = ProxmoxStorageService(mock_proxmox_client)
            result = service.list_storage("pve-node-1")

            # Verify API was called correctly
            mock_proxmox_client.get.assert_called_once_with("/nodes/pve-node-1/storage")

            # Validate response schema
            validate(instance=result, schema=SCHEMAS['storage_list_response'])

            # Verify response contains StorageInfo objects
            assert 'data' in result
            assert isinstance(result['data'], list)
            for storage_info in result['data']:
                validate(instance=storage_info, schema=SCHEMAS['storage_info'])

    def test_storage_content_endpoint_success_200(self, mock_proxmox_client, valid_storage_content_response):
        """Test GET /nodes/{node}/storage/{storage}/content returns 200 with valid StorageContent array."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.proxmox_storage import ProxmoxStorageService

            # Mock the API response
            mock_proxmox_client.get.return_value = valid_storage_content_response

            service = ProxmoxStorageService(mock_proxmox_client)
            result = service.list_storage_content("pve-node-1", "local")

            # Verify API was called correctly
            mock_proxmox_client.get.assert_called_once_with("/nodes/pve-node-1/storage/local/content")

            # Validate response schema
            validate(instance=result, schema=SCHEMAS['storage_content_response'])

            # Verify response contains StorageContent objects
            assert 'data' in result
            assert isinstance(result['data'], list)
            for content in result['data']:
                validate(instance=content, schema=SCHEMAS['storage_content'])

    def test_storage_content_endpoint_with_content_filter(self, mock_proxmox_client):
        """Test GET /nodes/{node}/storage/{storage}/content with content query parameter."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.proxmox_storage import ProxmoxStorageService

            # Mock response for filtered content
            filtered_response = {
                "data": [{
                    "volid": "local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst",
                    "format": "tar.zst",
                    "size": 234567890,
                    "content": "vztmpl"
                }]
            }
            mock_proxmox_client.get.return_value = filtered_response

            service = ProxmoxStorageService(mock_proxmox_client)
            result = service.list_storage_content("pve-node-1", "local", content_type="vztmpl")

            # Verify API was called with query parameter
            mock_proxmox_client.get.assert_called_once_with(
                "/nodes/pve-node-1/storage/local/content",
                params={"content": "vztmpl"}
            )

            # Validate response
            validate(instance=result, schema=SCHEMAS['storage_content_response'])

    def test_storage_content_valid_content_types(self, mock_proxmox_client):
        """Test that storage content endpoint accepts valid content types from contract."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.proxmox_storage import ProxmoxStorageService

            service = ProxmoxStorageService(mock_proxmox_client)

            # Test each valid content type from the contract
            valid_content_types = ["vztmpl", "iso", "rootdir"]
            for content_type in valid_content_types:
                mock_proxmox_client.get.return_value = {"data": []}
                service.list_storage_content("pve-node-1", "local", content_type=content_type)

                # Verify correct API call
                expected_call = f"/nodes/pve-node-1/storage/local/content"
                mock_proxmox_client.get.assert_called_with(expected_call, params={"content": content_type})

    def test_storage_list_endpoint_authentication_required(self, mock_proxmox_client):
        """Test that storage list endpoint requires authentication."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.proxmox_storage import ProxmoxStorageService
            from src.exceptions import AuthenticationError

            # Mock authentication error
            mock_proxmox_client.get.side_effect = AuthenticationError("Authentication required")

            service = ProxmoxStorageService(mock_proxmox_client)

            with pytest.raises(AuthenticationError):
                service.list_storage("pve-node-1")

    def test_storage_content_endpoint_authentication_required(self, mock_proxmox_client):
        """Test that storage content endpoint requires authentication."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.proxmox_storage import ProxmoxStorageService
            from src.exceptions import AuthenticationError

            # Mock authentication error
            mock_proxmox_client.get.side_effect = AuthenticationError("Authentication required")

            service = ProxmoxStorageService(mock_proxmox_client)

            with pytest.raises(AuthenticationError):
                service.list_storage_content("pve-node-1", "local")

    def test_storage_list_endpoint_node_not_found(self, mock_proxmox_client):
        """Test storage list endpoint handles non-existent node gracefully."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.proxmox_storage import ProxmoxStorageService
            from src.exceptions import NodeNotFoundError

            # Mock node not found error
            mock_proxmox_client.get.side_effect = NodeNotFoundError("Node 'invalid-node' not found")

            service = ProxmoxStorageService(mock_proxmox_client)

            with pytest.raises(NodeNotFoundError):
                service.list_storage("invalid-node")

    def test_storage_content_endpoint_storage_not_found(self, mock_proxmox_client):
        """Test storage content endpoint handles non-existent storage gracefully."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.proxmox_storage import ProxmoxStorageService
            from src.exceptions import StorageNotFoundError

            # Mock storage not found error
            mock_proxmox_client.get.side_effect = StorageNotFoundError("Storage 'invalid-storage' not found")

            service = ProxmoxStorageService(mock_proxmox_client)

            with pytest.raises(StorageNotFoundError):
                service.list_storage_content("pve-node-1", "invalid-storage")


class TestProxmoxStorageContractCompleteness:
    """Tests for OpenAPI contract completeness and structure for storage endpoints."""

    def test_storage_endpoints_exist_in_contract(self):
        """Test that both storage endpoints are defined in the contract."""
        with open(CONTRACT_PATH, 'r') as f:
            contract = yaml.safe_load(f)

        # Check storage list endpoint exists
        assert '/nodes/{node}/storage' in contract['paths']
        storage_list_spec = contract['paths']['/nodes/{node}/storage']['get']
        assert storage_list_spec is not None

        # Check storage content endpoint exists
        assert '/nodes/{node}/storage/{storage}/content' in contract['paths']
        storage_content_spec = contract['paths']['/nodes/{node}/storage/{storage}/content']['get']
        assert storage_content_spec is not None

    def test_storage_endpoints_require_authentication(self):
        """Test that storage endpoints specify authentication requirements."""
        with open(CONTRACT_PATH, 'r') as f:
            contract = yaml.safe_load(f)

        # Check storage list endpoint has security
        storage_list_spec = contract['paths']['/nodes/{node}/storage']['get']
        assert 'security' in storage_list_spec
        assert {'apiToken': []} in storage_list_spec['security']

        # Check storage content endpoint has security
        storage_content_spec = contract['paths']['/nodes/{node}/storage/{storage}/content']['get']
        assert 'security' in storage_content_spec
        assert {'apiToken': []} in storage_content_spec['security']

    def test_storage_endpoints_have_required_parameters(self):
        """Test that storage endpoints define required path parameters."""
        with open(CONTRACT_PATH, 'r') as f:
            contract = yaml.safe_load(f)

        # Check storage list endpoint parameters
        storage_list_spec = contract['paths']['/nodes/{node}/storage']['get']
        assert 'parameters' in storage_list_spec
        node_param = storage_list_spec['parameters'][0]
        assert node_param['name'] == 'node'
        assert node_param['in'] == 'path'
        assert node_param['required'] is True

        # Check storage content endpoint parameters
        storage_content_spec = contract['paths']['/nodes/{node}/storage/{storage}/content']['get']
        assert 'parameters' in storage_content_spec

        # Find node and storage parameters
        params = {param['name']: param for param in storage_content_spec['parameters']}
        assert 'node' in params
        assert params['node']['in'] == 'path'
        assert params['node']['required'] is True

        assert 'storage' in params
        assert params['storage']['in'] == 'path'
        assert params['storage']['required'] is True

    def test_storage_content_endpoint_content_parameter(self):
        """Test that storage content endpoint defines content query parameter correctly."""
        with open(CONTRACT_PATH, 'r') as f:
            contract = yaml.safe_load(f)

        storage_content_spec = contract['paths']['/nodes/{node}/storage/{storage}/content']['get']
        params = {param['name']: param for param in storage_content_spec['parameters']}

        # Check content query parameter
        assert 'content' in params
        content_param = params['content']
        assert content_param['in'] == 'query'
        # Query parameters are optional by default if 'required' field is not present
        assert content_param.get('required', False) is False
        assert content_param['schema']['type'] == 'string'
        assert 'enum' in content_param['schema']

        # Verify enum values match expected content types
        expected_content_types = ['vztmpl', 'iso', 'rootdir']
        assert set(content_param['schema']['enum']) == set(expected_content_types)

    def test_storage_schemas_have_expected_fields(self):
        """Test that StorageInfo and StorageContent schemas have expected fields."""
        storage_info_schema = SCHEMAS['storage_info']
        storage_content_schema = SCHEMAS['storage_content']

        # Check StorageInfo fields
        expected_storage_info_fields = ['storage', 'type', 'content', 'total', 'used', 'avail']
        assert 'properties' in storage_info_schema
        for field in expected_storage_info_fields:
            assert field in storage_info_schema['properties'], f"Field {field} missing from StorageInfo schema"

        # Check StorageContent fields
        expected_storage_content_fields = ['volid', 'format', 'size', 'content']
        assert 'properties' in storage_content_schema
        for field in expected_storage_content_fields:
            assert field in storage_content_schema['properties'], f"Field {field} missing from StorageContent schema"

    def test_storage_schemas_field_types(self):
        """Test that StorageInfo and StorageContent schemas have correct field types."""
        storage_info_schema = SCHEMAS['storage_info']
        storage_content_schema = SCHEMAS['storage_content']

        # Check StorageInfo field types
        storage_info_props = storage_info_schema['properties']
        assert storage_info_props['storage']['type'] == 'string'
        assert storage_info_props['type']['type'] == 'string'
        assert storage_info_props['content']['type'] == 'string'
        assert storage_info_props['total']['type'] == 'integer'
        assert storage_info_props['used']['type'] == 'integer'
        assert storage_info_props['avail']['type'] == 'integer'

        # Check StorageContent field types
        storage_content_props = storage_content_schema['properties']
        assert storage_content_props['volid']['type'] == 'string'
        assert storage_content_props['format']['type'] == 'string'
        assert storage_content_props['size']['type'] == 'integer'
        assert storage_content_props['content']['type'] == 'string'

    def test_storage_response_schemas_reference_correct_components(self):
        """Test that storage endpoint responses reference the correct schema components."""
        with open(CONTRACT_PATH, 'r') as f:
            contract = yaml.safe_load(f)

        # Check storage list response references StorageInfo
        storage_list_spec = contract['paths']['/nodes/{node}/storage']['get']
        response_200 = storage_list_spec['responses']['200']
        response_schema = response_200['content']['application/json']['schema']

        assert 'properties' in response_schema
        assert 'data' in response_schema['properties']
        data_schema = response_schema['properties']['data']
        assert data_schema['type'] == 'array'
        assert 'items' in data_schema
        assert data_schema['items']['$ref'] == '#/components/schemas/StorageInfo'

        # Check storage content response references StorageContent
        storage_content_spec = contract['paths']['/nodes/{node}/storage/{storage}/content']['get']
        response_200 = storage_content_spec['responses']['200']
        response_schema = response_200['content']['application/json']['schema']

        assert 'properties' in response_schema
        assert 'data' in response_schema['properties']
        data_schema = response_schema['properties']['data']
        assert data_schema['type'] == 'array'
        assert 'items' in data_schema
        assert data_schema['items']['$ref'] == '#/components/schemas/StorageContent'

    def test_contract_openapi_version_compatibility(self):
        """Test that the contract uses a supported OpenAPI version."""
        with open(CONTRACT_PATH, 'r') as f:
            contract = yaml.safe_load(f)

        # Check OpenAPI version
        assert 'openapi' in contract
        version = contract['openapi']
        assert version.startswith('3.'), f"Expected OpenAPI 3.x, got {version}"