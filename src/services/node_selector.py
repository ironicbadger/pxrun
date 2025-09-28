"""Node selector for intelligent cluster node selection."""

import logging
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum

from src.models.cluster import ClusterNode
from src.models.container import Container

logger = logging.getLogger(__name__)


class SelectionStrategy(Enum):
    """Node selection strategies."""

    LEAST_LOADED = "least_loaded"  # Select node with lowest resource usage
    MOST_MEMORY = "most_memory"     # Select node with most free memory
    MOST_CPU = "most_cpu"          # Select node with most free CPU
    ROUND_ROBIN = "round_robin"     # Rotate through available nodes
    RANDOM = "random"               # Random selection
    SPECIFIC = "specific"           # Specific node only


class NodeSelector:
    """Service for intelligent node selection in cluster."""

    def __init__(self, nodes: Optional[List[ClusterNode]] = None):
        """Initialize node selector.

        Args:
            nodes: List of cluster nodes
        """
        self.nodes = nodes or []
        self._last_selected_index = -1

    def update_nodes(self, nodes: List[ClusterNode]):
        """Update the list of cluster nodes.

        Args:
            nodes: Updated list of nodes
        """
        self.nodes = nodes
        logger.info(f"Updated node list with {len(nodes)} nodes")

    def select_node(self,
                   requirements: Dict[str, Any],
                   strategy: SelectionStrategy = SelectionStrategy.LEAST_LOADED,
                   preferred_node: Optional[str] = None) -> Optional[ClusterNode]:
        """Select best node for container based on requirements and strategy.

        Args:
            requirements: Resource requirements (cores, memory_mb, storage_gb, storage_pool)
            strategy: Selection strategy to use
            preferred_node: Preferred node name (for SPECIFIC strategy)

        Returns:
            Selected node or None if no suitable node found
        """
        # Filter available nodes
        available_nodes = self._filter_available_nodes(requirements, preferred_node)

        if not available_nodes:
            logger.warning("No nodes available that meet requirements")
            return None

        # Apply selection strategy
        if strategy == SelectionStrategy.SPECIFIC:
            # Return preferred node if available
            for node in available_nodes:
                if node.name == preferred_node:
                    logger.info(f"Selected specific node: {node.name}")
                    return node
            logger.warning(f"Preferred node {preferred_node} not available")
            return None

        elif strategy == SelectionStrategy.LEAST_LOADED:
            selected = self._select_least_loaded(available_nodes)

        elif strategy == SelectionStrategy.MOST_MEMORY:
            selected = self._select_most_memory(available_nodes)

        elif strategy == SelectionStrategy.MOST_CPU:
            selected = self._select_most_cpu(available_nodes)

        elif strategy == SelectionStrategy.ROUND_ROBIN:
            selected = self._select_round_robin(available_nodes)

        elif strategy == SelectionStrategy.RANDOM:
            selected = self._select_random(available_nodes)

        else:
            logger.warning(f"Unknown strategy {strategy}, using least loaded")
            selected = self._select_least_loaded(available_nodes)

        if selected:
            logger.info(f"Selected node: {selected.name} (strategy: {strategy.value})")
        else:
            logger.warning("Failed to select node")

        return selected

    def _filter_available_nodes(self,
                               requirements: Dict[str, Any],
                               preferred_node: Optional[str] = None) -> List[ClusterNode]:
        """Filter nodes that meet requirements.

        Args:
            requirements: Resource requirements
            preferred_node: Optional specific node to check

        Returns:
            List of suitable nodes
        """
        available = []

        cores_required = requirements.get('cores', 1)
        memory_mb = requirements.get('memory_mb', 512)
        storage_gb = requirements.get('storage_gb', 10)
        storage_pool = requirements.get('storage_pool')
        network_bridge = requirements.get('network_bridge', 'vmbr0')

        for node in self.nodes:
            # Skip offline nodes
            if not node.is_online:
                logger.debug(f"Node {node.name} is offline, skipping")
                continue

            # If specific node requested, only check that one
            if preferred_node and node.name != preferred_node:
                continue

            # Check resource availability
            if not node.can_allocate(cores_required, memory_mb):
                logger.debug(f"Node {node.name} lacks resources: {cores_required} cores, {memory_mb} MB")
                continue

            # Check storage pool if specified
            if storage_pool:
                has_pool = False
                pool_has_space = False

                for pool in node.storage_pools:
                    if pool.name == storage_pool:
                        has_pool = True
                        if pool.can_allocate(storage_gb):
                            pool_has_space = True
                        break

                if not has_pool:
                    logger.debug(f"Node {node.name} doesn't have storage pool {storage_pool}")
                    continue

                if not pool_has_space:
                    logger.debug(f"Storage pool {storage_pool} on {node.name} lacks space for {storage_gb} GB")
                    continue

            # Check network bridge
            if network_bridge and not node.has_network_bridge(network_bridge):
                logger.debug(f"Node {node.name} doesn't have network bridge {network_bridge}")
                continue

            available.append(node)

        logger.debug(f"Found {len(available)} suitable nodes out of {len(self.nodes)} total")
        return available

    def _select_least_loaded(self, nodes: List[ClusterNode]) -> Optional[ClusterNode]:
        """Select node with lowest overall load.

        Args:
            nodes: List of available nodes

        Returns:
            Selected node
        """
        if not nodes:
            return None

        # Calculate combined load score (lower is better)
        def load_score(node: ClusterNode) -> float:
            cpu_load = node.cpu_used
            memory_load = node.memory_usage_percent
            # Weight memory slightly higher as it's often the limiting factor
            return cpu_load * 0.4 + memory_load * 0.6

        sorted_nodes = sorted(nodes, key=load_score)
        selected = sorted_nodes[0]

        logger.debug(f"Least loaded node: {selected.name} "
                    f"(CPU: {selected.cpu_used:.1f}%, Memory: {selected.memory_usage_percent:.1f}%)")

        return selected

    def _select_most_memory(self, nodes: List[ClusterNode]) -> Optional[ClusterNode]:
        """Select node with most free memory.

        Args:
            nodes: List of available nodes

        Returns:
            Selected node
        """
        if not nodes:
            return None

        sorted_nodes = sorted(nodes, key=lambda n: n.memory_free, reverse=True)
        selected = sorted_nodes[0]

        logger.debug(f"Most memory node: {selected.name} "
                    f"(Free: {selected.memory_free / (1024**3):.1f} GB)")

        return selected

    def _select_most_cpu(self, nodes: List[ClusterNode]) -> Optional[ClusterNode]:
        """Select node with most free CPU.

        Args:
            nodes: List of available nodes

        Returns:
            Selected node
        """
        if not nodes:
            return None

        sorted_nodes = sorted(nodes, key=lambda n: n.cpu_free_percent, reverse=True)
        selected = sorted_nodes[0]

        logger.debug(f"Most CPU node: {selected.name} "
                    f"(Free: {selected.cpu_free_percent:.1f}%)")

        return selected

    def _select_round_robin(self, nodes: List[ClusterNode]) -> Optional[ClusterNode]:
        """Select next node in round-robin fashion.

        Args:
            nodes: List of available nodes

        Returns:
            Selected node
        """
        if not nodes:
            return None

        # Find current index in available nodes
        if self._last_selected_index >= 0:
            # Try to find the last selected node in current list
            for i, node in enumerate(nodes):
                if i > self._last_selected_index:
                    self._last_selected_index = i
                    logger.debug(f"Round-robin selected: {node.name} (index {i})")
                    return node

        # Start from beginning
        self._last_selected_index = 0
        selected = nodes[0]
        logger.debug(f"Round-robin selected: {selected.name} (index 0)")
        return selected

    def _select_random(self, nodes: List[ClusterNode]) -> Optional[ClusterNode]:
        """Select random node from available.

        Args:
            nodes: List of available nodes

        Returns:
            Selected node
        """
        if not nodes:
            return None

        import random
        selected = random.choice(nodes)
        logger.debug(f"Random selected: {selected.name}")
        return selected

    def recommend_node(self, container: Container) -> Optional[ClusterNode]:
        """Recommend best node for a container configuration.

        Args:
            container: Container configuration

        Returns:
            Recommended node or None
        """
        requirements = {
            'cores': container.cores,
            'memory_mb': container.memory,
            'storage_gb': container.storage,
            'storage_pool': container.storage_pool,
            'network_bridge': container.network_bridge
        }

        # If container specifies a node, use SPECIFIC strategy
        if container.node:
            return self.select_node(
                requirements,
                strategy=SelectionStrategy.SPECIFIC,
                preferred_node=container.node
            )

        # Otherwise use least loaded strategy
        return self.select_node(
            requirements,
            strategy=SelectionStrategy.LEAST_LOADED
        )

    def get_node_statistics(self) -> Dict[str, Any]:
        """Get statistics about all nodes.

        Returns:
            Dictionary with cluster statistics
        """
        stats = {
            'total_nodes': len(self.nodes),
            'online_nodes': 0,
            'total_cores': 0,
            'used_cores': 0,
            'total_memory_gb': 0,
            'used_memory_gb': 0,
            'nodes': []
        }

        for node in self.nodes:
            if node.is_online:
                stats['online_nodes'] += 1
                stats['total_cores'] += node.cpu_total
                stats['used_cores'] += int(node.cpu_total * node.cpu_used / 100)
                stats['total_memory_gb'] += node.memory_total / (1024**3)
                stats['used_memory_gb'] += node.memory_used / (1024**3)

            node_stats = {
                'name': node.name,
                'status': node.status,
                'cpu_usage': node.cpu_used,
                'memory_usage': node.memory_usage_percent,
                'free_memory_gb': node.memory_free / (1024**3),
                'storage_pools': len(node.storage_pools)
            }
            stats['nodes'].append(node_stats)

        if stats['total_cores'] > 0:
            stats['cpu_usage_percent'] = (stats['used_cores'] / stats['total_cores']) * 100
        else:
            stats['cpu_usage_percent'] = 0

        if stats['total_memory_gb'] > 0:
            stats['memory_usage_percent'] = (stats['used_memory_gb'] / stats['total_memory_gb']) * 100
        else:
            stats['memory_usage_percent'] = 0

        return stats

    def find_nodes_with_storage(self, storage_pool: str) -> List[ClusterNode]:
        """Find all nodes that have a specific storage pool.

        Args:
            storage_pool: Name of storage pool

        Returns:
            List of nodes with the storage pool
        """
        nodes_with_storage = []

        for node in self.nodes:
            if node.has_storage_pool(storage_pool):
                nodes_with_storage.append(node)

        logger.debug(f"Found {len(nodes_with_storage)} nodes with storage pool {storage_pool}")
        return nodes_with_storage

    def validate_placement(self, node: ClusterNode, container: Container) -> Tuple[bool, List[str]]:
        """Validate if container can be placed on node.

        Args:
            node: Target node
            container: Container to place

        Returns:
            Tuple of (valid, list_of_issues)
        """
        issues = []

        # Check node is online
        if not node.is_online:
            issues.append(f"Node {node.name} is offline")

        # Check CPU
        if not node.can_allocate(container.cores, container.memory):
            issues.append(f"Insufficient resources: {container.cores} cores, {container.memory} MB")

        # Check storage pool
        if container.storage_pool:
            has_pool = False
            for pool in node.storage_pools:
                if pool.name == container.storage_pool:
                    has_pool = True
                    if not pool.can_allocate(container.storage):
                        issues.append(f"Storage pool {container.storage_pool} lacks {container.storage} GB")
                    break

            if not has_pool:
                issues.append(f"Storage pool {container.storage_pool} not found on node")

        # Check network bridge
        if container.network_bridge:
            if not node.has_network_bridge(container.network_bridge):
                issues.append(f"Network bridge {container.network_bridge} not found on node")

        valid = len(issues) == 0
        if valid:
            logger.debug(f"Container can be placed on node {node.name}")
        else:
            logger.debug(f"Container cannot be placed on node {node.name}: {', '.join(issues)}")

        return valid, issues