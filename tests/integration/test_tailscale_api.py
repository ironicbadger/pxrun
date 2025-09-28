"""Integration tests for Tailscale API client."""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
import requests

from src.services.tailscale import (
    TailscaleAPIClient, 
    TailscaleNode,
    TailscaleNodeManager
)


class TestTailscaleAPIClient:
    """Test Tailscale API client functionality."""
    
    @pytest.fixture
    def mock_env_vars(self):
        """Mock environment variables for Tailscale API."""
        with patch.dict(os.environ, {
            'TAILSCALE_API_KEY': 'test-api-key',
            'TAILSCALE_TAILNET': 'test-org.ts.net'
        }):
            yield
    
    @pytest.fixture
    def api_client(self, mock_env_vars):
        """Create API client with mocked env vars."""
        return TailscaleAPIClient()
    
    def test_init_with_env_vars(self, mock_env_vars):
        """Test API client initialization with environment variables."""
        client = TailscaleAPIClient()
        assert client.api_key == 'test-api-key'
        assert client.tailnet == 'test-org.ts.net'
    
    def test_init_without_api_key(self):
        """Test that API client raises error without API key."""
        with patch.dict(os.environ, {'TAILSCALE_TAILNET': 'test-org.ts.net'}, clear=True):
            with pytest.raises(ValueError, match="Tailscale API key not provided"):
                TailscaleAPIClient()
    
    def test_init_without_tailnet(self):
        """Test that API client raises error without tailnet."""
        with patch.dict(os.environ, {'TAILSCALE_API_KEY': 'test-key'}, clear=True):
            with pytest.raises(ValueError, match="Tailnet not provided"):
                TailscaleAPIClient()
    
    @patch('requests.get')
    def test_list_nodes(self, mock_get, api_client):
        """Test listing Tailscale nodes."""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            'devices': [
                {
                    'id': 'node1',
                    'name': 'test-node-1',
                    'hostName': 'test-host-1',
                    'addresses': ['100.64.0.1'],
                    'os': 'linux',
                    'user': 'user@example.com',
                    'created': '2024-01-01T00:00:00Z',
                    'lastSeen': '2024-01-01T12:00:00Z',
                    'online': True,
                    'keyExpiryDisabled': False
                },
                {
                    'id': 'node2',
                    'name': 'test-node-2',
                    'hostName': 'test-host-2',
                    'addresses': ['100.64.0.2'],
                    'os': 'linux',
                    'user': 'user@example.com',
                    'created': '2024-01-01T00:00:00Z',
                    'lastSeen': '2024-01-01T11:00:00Z',
                    'online': False,
                    'keyExpiryDisabled': False
                }
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # Get nodes
        nodes = api_client.list_nodes()
        
        # Verify
        assert len(nodes) == 2
        assert nodes[0].name == 'test-node-1'
        assert nodes[0].online == True
        assert nodes[1].name == 'test-node-2'
        assert nodes[1].online == False
        
        # Verify API call
        mock_get.assert_called_once_with(
            'https://api.tailscale.com/api/v2/tailnet/test-org.ts.net/devices',
            headers={
                'Authorization': 'Bearer test-api-key',
                'Content-Type': 'application/json'
            },
            timeout=30
        )
    
    @patch('requests.get')
    def test_get_node_by_hostname(self, mock_get, api_client):
        """Test finding node by hostname."""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            'devices': [
                {
                    'id': 'node1',
                    'name': 'test-container',
                    'hostName': 'test-container',
                    'addresses': ['100.64.0.1'],
                    'os': 'linux',
                    'user': 'user@example.com',
                    'created': '2024-01-01T00:00:00Z',
                    'lastSeen': '2024-01-01T12:00:00Z',
                    'online': True,
                    'keyExpiryDisabled': False
                }
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # Find node
        node = api_client.get_node_by_hostname('test-container')
        
        # Verify
        assert node is not None
        assert node.hostname == 'test-container'
        assert node.id == 'node1'
    
    @patch('requests.get')
    def test_get_node_by_hostname_not_found(self, mock_get, api_client):
        """Test finding non-existent node by hostname."""
        # Mock empty response
        mock_response = Mock()
        mock_response.json.return_value = {'devices': []}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # Find node
        node = api_client.get_node_by_hostname('non-existent')
        
        # Verify
        assert node is None
    
    @patch('requests.delete')
    def test_delete_node(self, mock_delete, api_client):
        """Test deleting a Tailscale node."""
        # Mock successful deletion
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_delete.return_value = mock_response
        
        # Delete node
        success = api_client.delete_node('node123')
        
        # Verify
        assert success == True
        mock_delete.assert_called_once_with(
            'https://api.tailscale.com/api/v2/device/node123',
            headers={
                'Authorization': 'Bearer test-api-key',
                'Content-Type': 'application/json'
            },
            timeout=30
        )
    
    @patch('requests.delete')
    def test_delete_node_failure(self, mock_delete, api_client):
        """Test handling deletion failure."""
        # Mock failed deletion
        mock_delete.side_effect = requests.RequestException("API Error")
        
        # Delete node
        success = api_client.delete_node('node123')
        
        # Verify
        assert success == False


class TestTailscaleNodeManager:
    """Test Tailscale node manager functionality."""
    
    @pytest.fixture
    def mock_api_client(self):
        """Mock API client."""
        return Mock(spec=TailscaleAPIClient)
    
    @pytest.fixture
    def node_manager(self, mock_api_client):
        """Create node manager with mocked API client."""
        return TailscaleNodeManager(api_client=mock_api_client)
    
    def test_find_container_node_exact_match(self, node_manager, mock_api_client):
        """Test finding container node with exact hostname match."""
        # Mock node
        mock_node = TailscaleNode(
            id='node1',
            name='test-container',
            hostname='test-container',
            addresses=['100.64.0.1'],
            os='linux',
            user='user@example.com',
            created='2024-01-01T00:00:00Z',
            last_seen='2024-01-01T12:00:00Z',
            online=True,
            key_expiry_disabled=False
        )
        mock_api_client.get_node_by_hostname.return_value = mock_node
        
        # Find node
        node = node_manager.find_container_node('test-container', vmid=100)
        
        # Verify
        assert node == mock_node
        mock_api_client.get_node_by_hostname.assert_called_with('test-container')
    
    def test_find_container_node_with_suffix(self, node_manager, mock_api_client):
        """Test finding container node with VMID suffix."""
        # Mock node with suffix
        mock_node = TailscaleNode(
            id='node1',
            name='test-container-100',
            hostname='test-container-100',
            addresses=['100.64.0.1'],
            os='linux',
            user='user@example.com',
            created='2024-01-01T00:00:00Z',
            last_seen='2024-01-01T12:00:00Z',
            online=True,
            key_expiry_disabled=False
        )
        
        # First call returns None, second returns the node
        mock_api_client.get_node_by_hostname.side_effect = [None, None, mock_node]
        
        # Find node
        node = node_manager.find_container_node('test-container', vmid=100)
        
        # Verify
        assert node == mock_node
        assert mock_api_client.get_node_by_hostname.call_count == 3
    
    @patch('src.cli.prompts.confirm_tailscale_node_removal')
    def test_remove_container_node_with_confirmation(self, mock_confirm, node_manager, mock_api_client):
        """Test removing container node with user confirmation."""
        # Mock node
        mock_node = TailscaleNode(
            id='node1',
            name='test-container',
            hostname='test-container',
            addresses=['100.64.0.1'],
            os='linux',
            user='user@example.com',
            created='2024-01-01T00:00:00Z',
            last_seen='2024-01-01T12:00:00Z',
            online=True,
            key_expiry_disabled=False
        )
        mock_api_client.get_node_by_hostname.return_value = mock_node
        mock_api_client.delete_node.return_value = True
        mock_confirm.return_value = True
        
        # Remove node
        success = node_manager.remove_container_node('test-container', vmid=100, force=False)
        
        # Verify
        assert success == True
        mock_confirm.assert_called_once_with('test-container', 'node1')
        mock_api_client.delete_node.assert_called_once_with('node1')
    
    def test_remove_container_node_forced(self, node_manager, mock_api_client):
        """Test removing container node with force flag."""
        # Mock node
        mock_node = TailscaleNode(
            id='node1',
            name='test-container',
            hostname='test-container',
            addresses=['100.64.0.1'],
            os='linux',
            user='user@example.com',
            created='2024-01-01T00:00:00Z',
            last_seen='2024-01-01T12:00:00Z',
            online=True,
            key_expiry_disabled=False
        )
        mock_api_client.get_node_by_hostname.return_value = mock_node
        mock_api_client.delete_node.return_value = True
        
        # Remove node with force
        with patch('src.cli.prompts.confirm_tailscale_node_removal') as mock_confirm:
            success = node_manager.remove_container_node('test-container', vmid=100, force=True)
            
            # Verify confirmation was not called
            mock_confirm.assert_not_called()
        
        # Verify
        assert success == True
        mock_api_client.delete_node.assert_called_once_with('node1')
    
    def test_remove_container_node_not_found(self, node_manager, mock_api_client):
        """Test removing non-existent container node."""
        # Mock no node found
        mock_api_client.get_node_by_hostname.return_value = None
        
        # Remove node
        success = node_manager.remove_container_node('non-existent', vmid=100, force=False)
        
        # Verify - should return True since node doesn't exist
        assert success == True
        mock_api_client.delete_node.assert_not_called()


class TestTailscaleNode:
    """Test TailscaleNode data class."""
    
    def test_from_api_response(self):
        """Test creating TailscaleNode from API response."""
        api_data = {
            'id': 'node123',
            'name': 'test-node',
            'hostName': 'test-hostname',
            'addresses': ['100.64.0.1', '100.64.0.2'],
            'os': 'linux',
            'user': 'user@example.com',
            'created': '2024-01-01T00:00:00Z',
            'lastSeen': '2024-01-01T12:00:00Z',
            'online': True,
            'keyExpiryDisabled': False
        }
        
        node = TailscaleNode.from_api_response(api_data)
        
        assert node.id == 'node123'
        assert node.name == 'test-node'
        assert node.hostname == 'test-hostname'
        assert node.addresses == ['100.64.0.1', '100.64.0.2']
        assert node.os == 'linux'
        assert node.user == 'user@example.com'
        assert node.online == True
    
    def test_from_api_response_with_missing_fields(self):
        """Test creating TailscaleNode with missing optional fields."""
        api_data = {
            'id': 'node123',
            'name': 'test-node'
        }
        
        node = TailscaleNode.from_api_response(api_data)
        
        assert node.id == 'node123'
        assert node.name == 'test-node'
        assert node.hostname == ''
        assert node.addresses == []
        assert node.online == False