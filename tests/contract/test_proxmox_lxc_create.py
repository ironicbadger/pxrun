"""
Contract tests for the Proxmox LXC create API.

This module validates the Proxmox API LXC creation endpoint's interface as defined
in the OpenAPI contract at contracts/proxmox-api.yaml. Tests follow TDD approach
and will fail initially since the implementation doesn't exist yet.

The tests validate:
- POST /nodes/{node}/lxc endpoint request/response schema compliance
- All required fields (vmid, ostemplate, hostname, storage)
- All optional fields (cores, memory, rootfs, net0, mp0, features, start, unprivileged)
- HTTP response codes (200, 400, 401, 409, 503)
- proxmoxer API client integration
- Contract completeness and structure

Run with: pytest tests/contract/test_proxmox_lxc_create.py -v
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

    # Extract request/response schemas for LXC create endpoint
    lxc_create_path = contract['paths']['/nodes/{node}/lxc']['post']
    request_schema = lxc_create_path['requestBody']['content']['application/json']['schema']

    # Extract response schema (data field contains task UPID)
    response_schema = lxc_create_path['responses']['200']['content']['application/json']['schema']

    return {
        'lxc_create_request': request_schema,
        'lxc_create_response': response_schema,
        'node_info': schemas['NodeInfo'],
        'lxc_info': schemas['LXCInfo'],
        'lxc_config': schemas['LXCConfig']
    }

SCHEMAS = load_contract_schemas()


class TestProxmoxLXCCreateContract:
    """Contract tests for the Proxmox LXC create API endpoint."""

    def test_proxmox_lxc_service_interface_exists(self):
        """Test that the Proxmox LXC service interface can be imported (will fail initially)."""
        # This test will fail until the service implementation exists
        with pytest.raises(ImportError):
            from src.services.proxmox_lxc import ProxmoxLXCService

    @pytest.fixture
    def mock_proxmoxer(self):
        """Mock proxmoxer ProxmoxAPI client."""
        mock_proxmox = Mock()
        mock_node = Mock()
        mock_lxc = Mock()

        # Set up the nested structure: proxmox.nodes('node-name').lxc
        mock_proxmox.nodes.return_value = mock_node
        mock_node.lxc = mock_lxc

        return mock_proxmox

    @pytest.fixture
    def valid_lxc_create_request_minimal(self):
        """Valid minimal request payload for LXC create with only required fields."""
        return {
            "vmid": 1001,
            "ostemplate": "local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst",
            "hostname": "test-container",
            "storage": "local-lvm"
        }

    @pytest.fixture
    def valid_lxc_create_request_full(self):
        """Valid full request payload for LXC create with all optional fields."""
        return {
            "vmid": 1001,
            "ostemplate": "local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst",
            "hostname": "test-container",
            "storage": "local-lvm",
            "cores": 2,
            "memory": 2048,
            "rootfs": "local-lvm:20",
            "net0": "name=eth0,bridge=vmbr0,firewall=1,ip=dhcp,type=veth",
            "mp0": "local-lvm:10,mp=/mnt/data",
            "features": "nesting=1,keyctl=1",
            "start": True,
            "unprivileged": True
        }

    @pytest.fixture
    def valid_lxc_create_response_200(self):
        """Valid 200 response for successful LXC creation."""
        return {
            "data": "UPID:pve-node-1:00001234:56789ABC:qmcreate:1001:root@pam:"
        }

    @pytest.fixture
    def mock_lxc_service(self, mock_proxmoxer):
        """Mock LXC service with mocked proxmoxer client."""
        service = Mock()
        service.proxmox = mock_proxmoxer
        return service

    def test_request_schema_validation_minimal_valid(self, valid_lxc_create_request_minimal):
        """Test that minimal valid request payload passes schema validation."""
        validate(instance=valid_lxc_create_request_minimal, schema=SCHEMAS['lxc_create_request'])

    def test_request_schema_validation_full_valid(self, valid_lxc_create_request_full):
        """Test that full valid request payload passes schema validation."""
        validate(instance=valid_lxc_create_request_full, schema=SCHEMAS['lxc_create_request'])

    def test_request_schema_validation_missing_required_vmid(self):
        """Test that request without required vmid fails validation."""
        invalid_request = {
            "ostemplate": "local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst",
            "hostname": "test-container",
            "storage": "local-lvm"
        }
        with pytest.raises(ValidationError):
            validate(instance=invalid_request, schema=SCHEMAS['lxc_create_request'])

    def test_request_schema_validation_missing_required_ostemplate(self):
        """Test that request without required ostemplate fails validation."""
        invalid_request = {
            "vmid": 1001,
            "hostname": "test-container",
            "storage": "local-lvm"
        }
        with pytest.raises(ValidationError):
            validate(instance=invalid_request, schema=SCHEMAS['lxc_create_request'])

    def test_request_schema_validation_missing_required_hostname(self):
        """Test that request without required hostname fails validation."""
        invalid_request = {
            "vmid": 1001,
            "ostemplate": "local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst",
            "storage": "local-lvm"
        }
        with pytest.raises(ValidationError):
            validate(instance=invalid_request, schema=SCHEMAS['lxc_create_request'])

    def test_request_schema_validation_missing_required_storage(self):
        """Test that request without required storage fails validation."""
        invalid_request = {
            "vmid": 1001,
            "ostemplate": "local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst",
            "hostname": "test-container"
        }
        with pytest.raises(ValidationError):
            validate(instance=invalid_request, schema=SCHEMAS['lxc_create_request'])

    def test_request_schema_validation_invalid_types(self):
        """Test that request with wrong field types fails validation."""
        invalid_request = {
            "vmid": "1001",  # Should be integer
            "ostemplate": "local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst",
            "hostname": "test-container",
            "storage": "local-lvm",
            "cores": "2",      # Should be integer
            "memory": "2048",  # Should be integer
            "start": "true",   # Should be boolean
            "unprivileged": "true"  # Should be boolean
        }
        with pytest.raises(ValidationError):
            validate(instance=invalid_request, schema=SCHEMAS['lxc_create_request'])

    def test_response_200_schema_validation(self, valid_lxc_create_response_200):
        """Test that 200 response matches schema."""
        validate(instance=valid_lxc_create_response_200, schema=SCHEMAS['lxc_create_response'])

    def test_lxc_create_success_200_minimal(self, mock_lxc_service,
                                          valid_lxc_create_request_minimal,
                                          valid_lxc_create_response_200):
        """Test LXC create with minimal required fields returns 200 with task UPID."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.proxmox_lxc import ProxmoxLXCService

            # Mock successful API call
            mock_lxc_service.proxmox.nodes('pve-node-1').lxc.post.return_value = valid_lxc_create_response_200['data']

            service = ProxmoxLXCService(mock_lxc_service.proxmox)
            result = service.create_container('pve-node-1', valid_lxc_create_request_minimal)

            # Verify response matches schema
            response = {"data": result}
            validate(instance=response, schema=SCHEMAS['lxc_create_response'])

            # Verify proxmoxer was called correctly
            mock_lxc_service.proxmox.nodes.assert_called_with('pve-node-1')
            mock_lxc_service.proxmox.nodes('pve-node-1').lxc.post.assert_called_once_with(**valid_lxc_create_request_minimal)

    def test_lxc_create_success_200_full(self, mock_lxc_service,
                                       valid_lxc_create_request_full,
                                       valid_lxc_create_response_200):
        """Test LXC create with all optional fields returns 200 with task UPID."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.proxmox_lxc import ProxmoxLXCService

            # Mock successful API call
            mock_lxc_service.proxmox.nodes('pve-node-1').lxc.post.return_value = valid_lxc_create_response_200['data']

            service = ProxmoxLXCService(mock_lxc_service.proxmox)
            result = service.create_container('pve-node-1', valid_lxc_create_request_full)

            # Verify response matches schema
            response = {"data": result}
            validate(instance=response, schema=SCHEMAS['lxc_create_response'])

            # Verify proxmoxer was called with all parameters
            mock_lxc_service.proxmox.nodes('pve-node-1').lxc.post.assert_called_once_with(**valid_lxc_create_request_full)

    def test_lxc_create_validation_error_400(self, mock_lxc_service):
        """Test LXC create returns 400 on validation error."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.proxmox_lxc import ProxmoxLXCService
            from proxmoxer import ProxmoxAPIException

            # Mock API validation error
            mock_lxc_service.proxmox.nodes('pve-node-1').lxc.post.side_effect = ProxmoxAPIException(
                "400 Bad Request: invalid parameter 'vmid': value must be unique"
            )

            invalid_request = {
                "vmid": 1001,  # Already exists
                "ostemplate": "local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst",
                "hostname": "test-container",
                "storage": "local-lvm"
            }

            service = ProxmoxLXCService(mock_lxc_service.proxmox)

            with pytest.raises(ProxmoxAPIException) as exc_info:
                service.create_container('pve-node-1', invalid_request)

            assert "400 Bad Request" in str(exc_info.value)

    def test_lxc_create_unauthorized_401(self, mock_lxc_service):
        """Test LXC create returns 401 on authentication failure."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.proxmox_lxc import ProxmoxLXCService
            from proxmoxer import ProxmoxAPIException

            # Mock authentication error
            mock_lxc_service.proxmox.nodes('pve-node-1').lxc.post.side_effect = ProxmoxAPIException(
                "401 Unauthorized: authentication failure"
            )

            valid_request = {
                "vmid": 1001,
                "ostemplate": "local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst",
                "hostname": "test-container",
                "storage": "local-lvm"
            }

            service = ProxmoxLXCService(mock_lxc_service.proxmox)

            with pytest.raises(ProxmoxAPIException) as exc_info:
                service.create_container('pve-node-1', valid_request)

            assert "401 Unauthorized" in str(exc_info.value)

    def test_lxc_create_conflict_409(self, mock_lxc_service):
        """Test LXC create returns 409 when container with same hostname exists."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.proxmox_lxc import ProxmoxLXCService
            from proxmoxer import ProxmoxAPIException

            # Mock conflict error
            mock_lxc_service.proxmox.nodes('pve-node-1').lxc.post.side_effect = ProxmoxAPIException(
                "409 Conflict: container with hostname 'test-container' already exists"
            )

            conflict_request = {
                "vmid": 1002,
                "ostemplate": "local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst",
                "hostname": "test-container",  # Already exists
                "storage": "local-lvm"
            }

            service = ProxmoxLXCService(mock_lxc_service.proxmox)

            with pytest.raises(ProxmoxAPIException) as exc_info:
                service.create_container('pve-node-1', conflict_request)

            assert "409 Conflict" in str(exc_info.value)

    def test_lxc_create_service_unavailable_503(self, mock_lxc_service):
        """Test LXC create returns 503 when Proxmox API is unavailable."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.proxmox_lxc import ProxmoxLXCService
            from proxmoxer import ProxmoxAPIException

            # Mock service unavailable error
            mock_lxc_service.proxmox.nodes('pve-node-1').lxc.post.side_effect = ProxmoxAPIException(
                "503 Service Unavailable: Proxmox VE API service temporarily unavailable"
            )

            valid_request = {
                "vmid": 1001,
                "ostemplate": "local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst",
                "hostname": "test-container",
                "storage": "local-lvm"
            }

            service = ProxmoxLXCService(mock_lxc_service.proxmox)

            with pytest.raises(ProxmoxAPIException) as exc_info:
                service.create_container('pve-node-1', valid_request)

            assert "503 Service Unavailable" in str(exc_info.value)

    @patch('proxmoxer.ProxmoxAPI')
    def test_proxmoxer_integration_mock(self, mock_proxmox_api_class):
        """Test integration with mocked proxmoxer library."""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from src.services.proxmox_lxc import ProxmoxLXCService

            # Setup mock ProxmoxAPI instance
            mock_proxmox_instance = Mock()
            mock_proxmox_api_class.return_value = mock_proxmox_instance

            # Setup nested mock structure
            mock_node = Mock()
            mock_proxmox_instance.nodes.return_value = mock_node
            mock_node.lxc.post.return_value = "UPID:pve-node-1:00001234:56789ABC:qmcreate:1001:root@pam:"

            # Test service initialization and usage
            service = ProxmoxLXCService(
                host="pve.example.com",
                user="root@pam",
                password="secret",
                verify_ssl=False
            )

            request = {
                "vmid": 1001,
                "ostemplate": "local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst",
                "hostname": "test-container",
                "storage": "local-lvm"
            }

            result = service.create_container('pve-node-1', request)

            # Verify proxmoxer was called correctly
            mock_proxmox_api_class.assert_called_once_with(
                'pve.example.com',
                user='root@pam',
                password='secret',
                verify_ssl=False
            )
            mock_proxmox_instance.nodes.assert_called_with('pve-node-1')
            mock_node.lxc.post.assert_called_once_with(**request)
            assert result == "UPID:pve-node-1:00001234:56789ABC:qmcreate:1001:root@pam:"

    def test_contract_completeness_lxc_create_endpoint(self):
        """Test that LXC create endpoint contract has all required elements."""
        with open(CONTRACT_PATH, 'r') as f:
            contract = yaml.safe_load(f)

        # Check LXC create endpoint exists
        assert '/nodes/{node}/lxc' in contract['paths']
        lxc_path = contract['paths']['/nodes/{node}/lxc']
        assert 'post' in lxc_path

        lxc_create_spec = lxc_path['post']

        # Check endpoint has required elements
        assert 'summary' in lxc_create_spec
        assert 'security' in lxc_create_spec
        assert 'parameters' in lxc_create_spec
        assert 'requestBody' in lxc_create_spec
        assert 'responses' in lxc_create_spec

        # Check node parameter
        node_param = lxc_create_spec['parameters'][0]
        assert node_param['name'] == 'node'
        assert node_param['in'] == 'path'
        assert node_param['required'] == True

        # Check request body schema
        request_body = lxc_create_spec['requestBody']
        assert request_body['required'] == True
        assert 'application/json' in request_body['content']
        assert 'schema' in request_body['content']['application/json']

        # Check required response codes
        responses = lxc_create_spec['responses']
        assert '200' in responses

        # Check 200 response structure
        response_200 = responses['200']
        assert 'description' in response_200
        assert 'content' in response_200
        assert 'application/json' in response_200['content']
        assert 'schema' in response_200['content']['application/json']


class TestContractSchemaStructureLXC:
    """Tests for Proxmox API LXC contract schema structure and completeness."""

    def test_lxc_create_request_schema_required_fields(self):
        """Test LXC create request schema has all required fields."""
        schema = SCHEMAS['lxc_create_request']
        required_fields = ['vmid', 'ostemplate', 'hostname', 'storage']

        assert 'required' in schema
        for field in required_fields:
            assert field in schema['required'], f"Required field {field} missing from LXC create request schema"

        # Verify all required fields are defined in properties
        properties = schema['properties']
        for field in required_fields:
            assert field in properties, f"Required field {field} not defined in properties"

    def test_lxc_create_request_schema_optional_fields(self):
        """Test LXC create request schema includes all optional fields."""
        schema = SCHEMAS['lxc_create_request']
        optional_fields = ['cores', 'memory', 'rootfs', 'net0', 'mp0', 'features', 'start', 'unprivileged']

        properties = schema['properties']
        for field in optional_fields:
            assert field in properties, f"Optional field {field} missing from LXC create request schema"

    def test_lxc_create_request_schema_field_types(self):
        """Test LXC create request schema has correct field types."""
        schema = SCHEMAS['lxc_create_request']
        properties = schema['properties']

        # Test integer fields
        integer_fields = ['vmid', 'cores', 'memory']
        for field in integer_fields:
            if field in properties:
                assert properties[field]['type'] == 'integer', f"Field {field} should be integer type"

        # Test string fields
        string_fields = ['ostemplate', 'hostname', 'storage', 'rootfs', 'net0', 'mp0', 'features']
        for field in string_fields:
            if field in properties:
                assert properties[field]['type'] == 'string', f"Field {field} should be string type"

        # Test boolean fields
        boolean_fields = ['start', 'unprivileged']
        for field in boolean_fields:
            if field in properties:
                assert properties[field]['type'] == 'boolean', f"Field {field} should be boolean type"

    def test_lxc_create_response_schema_structure(self):
        """Test LXC create response schema has correct structure."""
        schema = SCHEMAS['lxc_create_response']

        assert 'type' in schema
        assert schema['type'] == 'object'
        assert 'properties' in schema
        assert 'data' in schema['properties']

        data_schema = schema['properties']['data']
        assert data_schema['type'] == 'string'
        assert 'description' in data_schema
        assert data_schema['description'] == 'Task UPID'

    def test_contract_openapi_version_compatibility(self):
        """Test that the contract uses a supported OpenAPI version."""
        with open(CONTRACT_PATH, 'r') as f:
            contract = yaml.safe_load(f)

        # Check OpenAPI version
        assert 'openapi' in contract
        version = contract['openapi']
        assert version.startswith('3.'), f"Expected OpenAPI 3.x, got {version}"

    def test_security_scheme_defined(self):
        """Test that API token security scheme is properly defined."""
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

    def test_lxc_create_endpoint_security_requirement(self):
        """Test that LXC create endpoint requires API token authentication."""
        with open(CONTRACT_PATH, 'r') as f:
            contract = yaml.safe_load(f)

        lxc_create_spec = contract['paths']['/nodes/{node}/lxc']['post']
        assert 'security' in lxc_create_spec

        security_requirements = lxc_create_spec['security']
        assert len(security_requirements) == 1
        assert 'apiToken' in security_requirements[0]
        assert security_requirements[0]['apiToken'] == []