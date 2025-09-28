"""Tailscale API client for managing nodes in a Tailnet."""

import os
import sys
import json
import logging
import time
import requests
from typing import List, Dict, Optional, Any
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass
class TailscaleNode:
    """Represents a Tailscale node."""
    
    id: str
    name: str
    hostname: str
    addresses: List[str]
    os: str
    user: str
    created: str
    last_seen: str
    online: bool
    key_expiry_disabled: bool
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'TailscaleNode':
        """Create TailscaleNode from API response data."""
        return cls(
            id=data.get('id', ''),
            name=data.get('name', ''),
            hostname=data.get('hostName', ''),
            addresses=data.get('addresses', []),
            os=data.get('os', ''),
            user=data.get('user', ''),
            created=data.get('created', ''),
            last_seen=data.get('lastSeen', ''),
            online=data.get('online', False),
            key_expiry_disabled=data.get('keyExpiryDisabled', False)
        )


class TailscaleAPIClient:
    """Client for interacting with Tailscale API."""
    
    BASE_URL = "https://api.tailscale.com/api/v2"
    
    def __init__(self, api_key: Optional[str] = None, tailnet: Optional[str] = None):
        """Initialize Tailscale API client.
        
        Args:
            api_key: Tailscale API key (if not provided, uses TAILSCALE_API_KEY env var)
            tailnet: Tailnet organization (if not provided, uses TAILSCALE_TAILNET env var)
        """
        self.api_key = api_key or os.getenv('TAILSCALE_API_KEY')
        self.tailnet = tailnet or os.getenv('TAILSCALE_TAILNET')
        
        if not self.api_key:
            raise ValueError("Tailscale API key not provided. Set TAILSCALE_API_KEY environment variable.")
        
        if not self.tailnet:
            raise ValueError("Tailnet not provided. Set TAILSCALE_TAILNET environment variable.")
        
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        # Cache for nodes list to avoid redundant API calls
        self._nodes_cache = None
        self._cache_timestamp = None
        self._cache_ttl = 60  # Cache TTL in seconds
        
        logger.debug(f"Initialized Tailscale API client for tailnet: {self.tailnet}")
    
    def list_nodes(self, use_cache: bool = True) -> List[TailscaleNode]:
        """List all nodes in the Tailnet.
        
        Args:
            use_cache: Whether to use cached results if available
        
        Returns:
            List of TailscaleNode objects
        """
        # Check cache if enabled
        if use_cache and self._nodes_cache is not None and self._cache_timestamp is not None:
            cache_age = time.time() - self._cache_timestamp
            if cache_age < self._cache_ttl:
                logger.debug(f"Using cached nodes (age: {cache_age:.1f}s)")
                return self._nodes_cache
        
        url = f"{self.BASE_URL}/tailnet/{self.tailnet}/devices"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            devices = data.get('devices', [])
            
            nodes = []
            for device in devices:
                try:
                    node = TailscaleNode.from_api_response(device)
                    nodes.append(node)
                except Exception as e:
                    logger.warning(f"Failed to parse device data: {e}")
                    continue
            
            # Update cache
            self._nodes_cache = nodes
            self._cache_timestamp = time.time()
            
            logger.info(f"Retrieved {len(nodes)} nodes from Tailnet")
            return nodes
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to list Tailscale nodes: {e}")
            raise
    
    def get_node_by_hostname(self, hostname: str) -> Optional[TailscaleNode]:
        """Find a node by hostname.
        
        Args:
            hostname: The hostname to search for
            
        Returns:
            TailscaleNode if found, None otherwise
        """
        nodes = self.list_nodes()
        hostname_lower = hostname.lower()
        
        for node in nodes:
            node_hostname_lower = node.hostname.lower()
            node_name_lower = node.name.lower()
            
            # Exact match
            if node_hostname_lower == hostname_lower or node_name_lower == hostname_lower:
                return node
            
            # Match without domain suffix (e.g., "testlxc2" matches "testlxc2.ktz.ts.net")
            if '.' in node_hostname_lower:
                hostname_part = node_hostname_lower.split('.')[0]
                if hostname_part == hostname_lower:
                    return node
            
            if '.' in node_name_lower:
                name_part = node_name_lower.split('.')[0]
                if name_part == hostname_lower:
                    return node
        
        return None
    
    def get_node_by_id(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific node.
        
        Args:
            node_id: The node ID
            
        Returns:
            Node details as dictionary
        """
        url = f"{self.BASE_URL}/device/{node_id}"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get node {node_id}: {e}")
            return None
    
    def delete_node(self, node_id: str) -> bool:
        """Delete a node from the Tailnet.
        
        Args:
            node_id: The node ID to delete
            
        Returns:
            True if deletion was successful, False otherwise
        """
        url = f"{self.BASE_URL}/device/{node_id}"
        
        try:
            response = requests.delete(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            # Clear cache after successful deletion
            self._nodes_cache = None
            self._cache_timestamp = None
            
            logger.info(f"Successfully deleted node {node_id} from Tailnet")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to delete node {node_id}: {e}")
            return False
    
    def expire_node_key(self, node_id: str) -> bool:
        """Expire the key for a node, effectively disabling it.
        
        Args:
            node_id: The node ID to expire
            
        Returns:
            True if expiration was successful, False otherwise
        """
        url = f"{self.BASE_URL}/device/{node_id}/key"
        data = {"keyExpiryDisabled": False}
        
        try:
            response = requests.post(url, headers=self.headers, json=data, timeout=30)
            response.raise_for_status()
            
            logger.info(f"Successfully expired key for node {node_id}")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to expire key for node {node_id}: {e}")
            return False
    
    def set_authorized(self, node_id: str, authorized: bool = True) -> bool:
        """Set the authorization status of a node.
        
        Args:
            node_id: The node ID
            authorized: Whether to authorize or deauthorize the node
            
        Returns:
            True if operation was successful, False otherwise
        """
        url = f"{self.BASE_URL}/device/{node_id}/authorized"
        data = {"authorized": authorized}
        
        try:
            response = requests.post(url, headers=self.headers, json=data, timeout=30)
            response.raise_for_status()
            
            status = "authorized" if authorized else "deauthorized"
            logger.info(f"Successfully {status} node {node_id}")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to set authorization for node {node_id}: {e}")
            return False


class TailscaleProvisioningService:
    """Service for provisioning Tailscale on containers via SSH."""
    
    def __init__(self):
        """Initialize the provisioning service."""
        pass
    
    def get_auth_key(self) -> str:
        """Get Tailscale auth key from environment.
        
        Returns:
            Tailscale auth key
            
        Raises:
            TailscaleConfigError: If auth key is not set
        """
        auth_key = os.getenv('TAILSCALE_AUTH_KEY')
        if not auth_key:
            from src.exceptions import TailscaleConfigError
            raise TailscaleConfigError("TAILSCALE_AUTH_KEY environment variable not set")
        return auth_key


class TailscaleNodeManager:
    """Manages Tailscale node lifecycle for containers."""
    
    def __init__(self, api_client: Optional[TailscaleAPIClient] = None):
        """Initialize the node manager.
        
        Args:
            api_client: Optional API client instance
        """
        self.api_client = api_client or TailscaleAPIClient()
    
    def find_container_node(self, container_hostname: str, vmid: Optional[int] = None) -> Optional[TailscaleNode]:
        """Find a Tailscale node matching a container.
        
        Args:
            container_hostname: The hostname of the container
            vmid: Optional container VMID for additional matching
            
        Returns:
            TailscaleNode if found, None otherwise
        """
        # First try exact hostname match (this now also handles FQDN matching)
        node = self.api_client.get_node_by_hostname(container_hostname)
        if node:
            logger.debug(f"Found exact match for hostname: {container_hostname}")
            return node
        
        # Try with common suffixes
        suffixes = ['-ct', f'-{vmid}' if vmid else None, f'-ct{vmid}' if vmid else None]
        for suffix in suffixes:
            if suffix is None:
                continue
            test_hostname = f"{container_hostname}{suffix}"
            node = self.api_client.get_node_by_hostname(test_hostname)
            if node:
                logger.debug(f"Found match with suffix: {test_hostname}")
                return node
        
        # Try removing common suffixes from container hostname
        # (in case container is named "test-ct100" but Tailscale node is just "test")
        if vmid:
            patterns_to_remove = [f'-{vmid}', f'-ct{vmid}', '-ct', f'ct{vmid}']
            for pattern in patterns_to_remove:
                if container_hostname.endswith(pattern):
                    base_hostname = container_hostname[:-len(pattern)]
                    node = self.api_client.get_node_by_hostname(base_hostname)
                    if node:
                        logger.debug(f"Found match by removing suffix: {base_hostname}")
                        return node
        
        logger.debug(f"No Tailscale node found for container: {container_hostname} (VMID: {vmid})")
        return None
    
    def remove_container_node(self, container_hostname: str, vmid: Optional[int] = None, 
                              force: bool = False) -> bool:
        """Remove a container's Tailscale node from the Tailnet.
        
        Args:
            container_hostname: The hostname of the container
            vmid: Optional container VMID for additional matching
            force: Skip confirmation prompt
            
        Returns:
            True if node was removed or not found, False on error
        """
        node = self.find_container_node(container_hostname, vmid)
        
        if not node:
            logger.info(f"No Tailscale node found for container {container_hostname}")
            return True
        
        logger.info(f"Found Tailscale node: {node.name}")
        
        # Confirm deletion unless forced
        if not force:
            from src.cli.prompts import confirm_tailscale_node_removal
            if not confirm_tailscale_node_removal(node.name, node.id):
                logger.info("Tailscale node removal cancelled by user")
                return False
        
        # Delete the node
        success = self.api_client.delete_node(node.id)
        
        if success:
            logger.info(f"Successfully removed Tailscale node {node.name}")
        else:
            logger.error(f"Failed to remove Tailscale node {node.name}")
        
        return success