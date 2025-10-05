"""Flow validation including DAG cycle detection."""

from typing import List, Dict, Any, Set
from collections import defaultdict, deque


class FlowValidator:
    """Validator for flow structure and execution requirements."""

    def validate_flow(
        self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validate basic flow structure.

        Args:
            nodes: List of flow nodes
            edges: List of flow edges

        Returns:
            Dict with 'valid' boolean and 'errors' list
        """
        errors = []

        # Check for empty flow
        if not nodes:
            errors.append("Flow must have at least one node")
            return {"valid": False, "errors": errors}

        # Validate node IDs are unique
        node_ids = [node["id"] for node in nodes]
        if len(node_ids) != len(set(node_ids)):
            errors.append("Node IDs must be unique")

        # Validate edge references
        for edge in edges:
            if edge["source"] not in node_ids:
                errors.append(f"Edge source '{edge['source']}' not found in nodes")
            if edge["target"] not in node_ids:
                errors.append(f"Edge target '{edge['target']}' not found in nodes")

        # Check for cycles
        if self._has_cycle(nodes, edges):
            errors.append("Flow contains cycles (DAG required)")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
        }

    def validate_executable(
        self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validate flow is executable (has start and end nodes).

        Args:
            nodes: List of flow nodes
            edges: List of flow edges

        Returns:
            Dict with 'valid' boolean and 'errors' list
        """
        errors = []

        # Basic validation first
        basic_validation = self.validate_flow(nodes, edges)
        if not basic_validation["valid"]:
            return basic_validation

        # Check for input nodes (no incoming edges)
        node_ids = {node["id"] for node in nodes}
        target_ids = {edge["target"] for edge in edges}
        input_nodes = node_ids - target_ids

        if not input_nodes:
            errors.append("Flow must have at least one input node (no incoming edges)")

        # Check for output nodes (no outgoing edges)
        source_ids = {edge["source"] for edge in edges}
        output_nodes = node_ids - source_ids

        if not output_nodes:
            errors.append("Flow must have at least one output node (no outgoing edges)")

        # Check all nodes are reachable from input nodes
        reachable = self._get_reachable_nodes(input_nodes, edges)
        unreachable = node_ids - reachable

        if unreachable:
            errors.append(f"Unreachable nodes detected: {unreachable}")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
        }

    def _has_cycle(
        self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]
    ) -> bool:
        """
        Detect cycles using DFS.

        Args:
            nodes: List of flow nodes
            edges: List of flow edges

        Returns:
            True if cycle detected, False otherwise
        """
        # Build adjacency list
        graph = defaultdict(list)
        for edge in edges:
            graph[edge["source"]].append(edge["target"])

        # Track visited and recursion stack
        visited = set()
        rec_stack = set()

        def dfs(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)

            for neighbor in graph[node_id]:
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True  # Back edge = cycle

            rec_stack.remove(node_id)
            return False

        # Check all components
        for node in nodes:
            node_id = node["id"]
            if node_id not in visited:
                if dfs(node_id):
                    return True

        return False

    def _get_reachable_nodes(
        self, start_nodes: Set[str], edges: List[Dict[str, Any]]
    ) -> Set[str]:
        """
        Get all nodes reachable from start nodes using BFS.

        Args:
            start_nodes: Set of starting node IDs
            edges: List of flow edges

        Returns:
            Set of reachable node IDs
        """
        # Build adjacency list
        graph = defaultdict(list)
        for edge in edges:
            graph[edge["source"]].append(edge["target"])

        # BFS from all start nodes
        reachable = set(start_nodes)
        queue = deque(start_nodes)

        while queue:
            current = queue.popleft()
            for neighbor in graph[current]:
                if neighbor not in reachable:
                    reachable.add(neighbor)
                    queue.append(neighbor)

        return reachable

    def topological_sort(
        self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Perform topological sort for execution order.

        Args:
            nodes: List of flow nodes
            edges: List of flow edges

        Returns:
            List of node IDs in topological order

        Raises:
            ValueError: If graph has cycles
        """
        if self._has_cycle(nodes, edges):
            raise ValueError("Cannot topologically sort graph with cycles")

        # Build adjacency list and in-degree count
        graph = defaultdict(list)
        in_degree = defaultdict(int)

        # Initialize all nodes with 0 in-degree
        for node in nodes:
            in_degree[node["id"]] = 0

        # Build graph
        for edge in edges:
            graph[edge["source"]].append(edge["target"])
            in_degree[edge["target"]] += 1

        # Find all nodes with 0 in-degree
        queue = deque([node_id for node_id, degree in in_degree.items() if degree == 0])

        result = []

        while queue:
            current = queue.popleft()
            result.append(current)

            # Reduce in-degree for neighbors
            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return result
