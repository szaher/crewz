"""Unit tests for FlowValidator - DAG cycle detection and validation."""

import pytest
from src.services.flow_validator import FlowValidator


@pytest.fixture
def validator():
    """Create a FlowValidator instance."""
    return FlowValidator()


@pytest.fixture
def valid_linear_flow():
    """Create a valid linear flow: A -> B -> C."""
    nodes = [
        {"id": "A", "type": "agent", "data": {}},
        {"id": "B", "type": "tool", "data": {}},
        {"id": "C", "type": "output", "data": {}},
    ]
    edges = [
        {"id": "e1", "source": "A", "target": "B"},
        {"id": "e2", "source": "B", "target": "C"},
    ]
    return nodes, edges


@pytest.fixture
def valid_branching_flow():
    """Create a valid branching flow: A -> [B, C] -> D."""
    nodes = [
        {"id": "A", "type": "input", "data": {}},
        {"id": "B", "type": "agent", "data": {}},
        {"id": "C", "type": "agent", "data": {}},
        {"id": "D", "type": "output", "data": {}},
    ]
    edges = [
        {"id": "e1", "source": "A", "target": "B"},
        {"id": "e2", "source": "A", "target": "C"},
        {"id": "e3", "source": "B", "target": "D"},
        {"id": "e4", "source": "C", "target": "D"},
    ]
    return nodes, edges


@pytest.fixture
def cyclic_flow():
    """Create a flow with a cycle: A -> B -> C -> A."""
    nodes = [
        {"id": "A", "type": "agent", "data": {}},
        {"id": "B", "type": "tool", "data": {}},
        {"id": "C", "type": "agent", "data": {}},
    ]
    edges = [
        {"id": "e1", "source": "A", "target": "B"},
        {"id": "e2", "source": "B", "target": "C"},
        {"id": "e3", "source": "C", "target": "A"},  # Creates cycle
    ]
    return nodes, edges


@pytest.fixture
def self_loop_flow():
    """Create a flow with a self-loop: A -> A."""
    nodes = [
        {"id": "A", "type": "agent", "data": {}},
    ]
    edges = [
        {"id": "e1", "source": "A", "target": "A"},  # Self-loop
    ]
    return nodes, edges


class TestValidateFlow:
    """Tests for basic flow validation."""

    def test_valid_linear_flow(self, validator, valid_linear_flow):
        """Test validation of a valid linear flow."""
        nodes, edges = valid_linear_flow
        result = validator.validate_flow(nodes, edges)

        assert result["valid"] is True
        assert len(result["errors"]) == 0

    def test_valid_branching_flow(self, validator, valid_branching_flow):
        """Test validation of a valid branching flow."""
        nodes, edges = valid_branching_flow
        result = validator.validate_flow(nodes, edges)

        assert result["valid"] is True
        assert len(result["errors"]) == 0

    def test_empty_flow(self, validator):
        """Test validation fails for empty flow."""
        result = validator.validate_flow([], [])

        assert result["valid"] is False
        assert "at least one node" in result["errors"][0]

    def test_duplicate_node_ids(self, validator):
        """Test validation fails with duplicate node IDs."""
        nodes = [
            {"id": "A", "type": "agent", "data": {}},
            {"id": "A", "type": "tool", "data": {}},  # Duplicate ID
        ]
        edges = []
        result = validator.validate_flow(nodes, edges)

        assert result["valid"] is False
        assert any("unique" in error.lower() for error in result["errors"])

    def test_invalid_edge_source(self, validator):
        """Test validation fails with invalid edge source."""
        nodes = [
            {"id": "A", "type": "agent", "data": {}},
            {"id": "B", "type": "tool", "data": {}},
        ]
        edges = [
            {"id": "e1", "source": "X", "target": "B"},  # Invalid source
        ]
        result = validator.validate_flow(nodes, edges)

        assert result["valid"] is False
        assert any("source" in error.lower() and "not found" in error.lower() for error in result["errors"])

    def test_invalid_edge_target(self, validator):
        """Test validation fails with invalid edge target."""
        nodes = [
            {"id": "A", "type": "agent", "data": {}},
            {"id": "B", "type": "tool", "data": {}},
        ]
        edges = [
            {"id": "e1", "source": "A", "target": "Y"},  # Invalid target
        ]
        result = validator.validate_flow(nodes, edges)

        assert result["valid"] is False
        assert any("target" in error.lower() and "not found" in error.lower() for error in result["errors"])


class TestCycleDetection:
    """Tests for DAG cycle detection."""

    def test_detects_simple_cycle(self, validator, cyclic_flow):
        """Test detection of a simple cycle."""
        nodes, edges = cyclic_flow
        result = validator.validate_flow(nodes, edges)

        assert result["valid"] is False
        assert any("cycle" in error.lower() for error in result["errors"])

    def test_detects_self_loop(self, validator, self_loop_flow):
        """Test detection of self-loop."""
        nodes, edges = self_loop_flow
        result = validator.validate_flow(nodes, edges)

        assert result["valid"] is False
        assert any("cycle" in error.lower() for error in result["errors"])

    def test_no_cycle_in_linear_flow(self, validator, valid_linear_flow):
        """Test no false positive for linear flow."""
        nodes, edges = valid_linear_flow
        has_cycle = validator._has_cycle(nodes, edges)

        assert has_cycle is False

    def test_no_cycle_in_branching_flow(self, validator, valid_branching_flow):
        """Test no false positive for branching flow."""
        nodes, edges = valid_branching_flow
        has_cycle = validator._has_cycle(nodes, edges)

        assert has_cycle is False

    def test_detects_cycle_in_complex_graph(self, validator):
        """Test detection of cycle in complex graph with multiple paths."""
        nodes = [
            {"id": "A", "type": "input", "data": {}},
            {"id": "B", "type": "agent", "data": {}},
            {"id": "C", "type": "agent", "data": {}},
            {"id": "D", "type": "tool", "data": {}},
            {"id": "E", "type": "output", "data": {}},
        ]
        edges = [
            {"id": "e1", "source": "A", "target": "B"},
            {"id": "e2", "source": "B", "target": "C"},
            {"id": "e3", "source": "C", "target": "D"},
            {"id": "e4", "source": "D", "target": "E"},
            {"id": "e5", "source": "D", "target": "B"},  # Creates cycle: B -> C -> D -> B
        ]
        result = validator.validate_flow(nodes, edges)

        assert result["valid"] is False
        assert any("cycle" in error.lower() for error in result["errors"])


class TestValidateExecutable:
    """Tests for executable flow validation."""

    def test_valid_executable_flow(self, validator, valid_linear_flow):
        """Test validation of executable flow with input and output."""
        nodes, edges = valid_linear_flow
        result = validator.validate_executable(nodes, edges)

        assert result["valid"] is True
        assert len(result["errors"]) == 0

    def test_missing_input_node(self, validator):
        """Test validation fails when all nodes have incoming edges."""
        nodes = [
            {"id": "A", "type": "agent", "data": {}},
            {"id": "B", "type": "tool", "data": {}},
        ]
        edges = [
            {"id": "e1", "source": "A", "target": "B"},
            {"id": "e2", "source": "B", "target": "A"},  # No node without incoming edge
        ]
        result = validator.validate_executable(nodes, edges)

        assert result["valid"] is False
        assert any("input node" in error.lower() for error in result["errors"])

    def test_missing_output_node(self, validator):
        """Test validation fails when all nodes have outgoing edges."""
        nodes = [
            {"id": "A", "type": "agent", "data": {}},
            {"id": "B", "type": "tool", "data": {}},
        ]
        edges = [
            {"id": "e1", "source": "A", "target": "B"},
            {"id": "e2", "source": "B", "target": "A"},  # No node without outgoing edge
        ]
        result = validator.validate_executable(nodes, edges)

        assert result["valid"] is False
        assert any("output node" in error.lower() for error in result["errors"])

    def test_unreachable_nodes(self, validator):
        """Test detection of unreachable nodes."""
        nodes = [
            {"id": "A", "type": "input", "data": {}},
            {"id": "B", "type": "agent", "data": {}},
            {"id": "C", "type": "output", "data": {}},  # Unreachable
        ]
        edges = [
            {"id": "e1", "source": "A", "target": "B"},
            # C has no incoming edges but is not connected
        ]
        result = validator.validate_executable(nodes, edges)

        assert result["valid"] is False
        assert any("unreachable" in error.lower() for error in result["errors"])


class TestTopologicalSort:
    """Tests for topological sort algorithm."""

    def test_topological_sort_linear(self, validator, valid_linear_flow):
        """Test topological sort of linear flow."""
        nodes, edges = valid_linear_flow
        result = validator.topological_sort(nodes, edges)

        assert result == ["A", "B", "C"]

    def test_topological_sort_branching(self, validator, valid_branching_flow):
        """Test topological sort of branching flow."""
        nodes, edges = valid_branching_flow
        result = validator.topological_sort(nodes, edges)

        # A must be first, D must be last
        assert result[0] == "A"
        assert result[-1] == "D"
        # B and C can be in any order but both before D
        assert set(result[1:3]) == {"B", "C"}

    def test_topological_sort_fails_on_cycle(self, validator, cyclic_flow):
        """Test topological sort raises error for cyclic graph."""
        nodes, edges = cyclic_flow

        with pytest.raises(ValueError) as exc_info:
            validator.topological_sort(nodes, edges)

        assert "cycle" in str(exc_info.value).lower()

    def test_topological_sort_complex_dag(self, validator):
        """Test topological sort of complex DAG."""
        nodes = [
            {"id": "A", "type": "input", "data": {}},
            {"id": "B", "type": "agent", "data": {}},
            {"id": "C", "type": "agent", "data": {}},
            {"id": "D", "type": "tool", "data": {}},
            {"id": "E", "type": "agent", "data": {}},
            {"id": "F", "type": "output", "data": {}},
        ]
        edges = [
            {"id": "e1", "source": "A", "target": "B"},
            {"id": "e2", "source": "A", "target": "C"},
            {"id": "e3", "source": "B", "target": "D"},
            {"id": "e4", "source": "C", "target": "D"},
            {"id": "e5", "source": "D", "target": "E"},
            {"id": "e6", "source": "E", "target": "F"},
        ]
        result = validator.topological_sort(nodes, edges)

        # Verify topological ordering constraints
        assert result.index("A") < result.index("B")
        assert result.index("A") < result.index("C")
        assert result.index("B") < result.index("D")
        assert result.index("C") < result.index("D")
        assert result.index("D") < result.index("E")
        assert result.index("E") < result.index("F")

    def test_topological_sort_disconnected_components(self, validator):
        """Test topological sort handles disconnected components."""
        nodes = [
            {"id": "A", "type": "agent", "data": {}},
            {"id": "B", "type": "tool", "data": {}},
            {"id": "C", "type": "agent", "data": {}},  # Disconnected
        ]
        edges = [
            {"id": "e1", "source": "A", "target": "B"},
        ]
        result = validator.topological_sort(nodes, edges)

        # All nodes should be in result
        assert set(result) == {"A", "B", "C"}
        # A must come before B
        assert result.index("A") < result.index("B")


class TestGetReachableNodes:
    """Tests for reachable nodes detection."""

    def test_reachable_linear(self, validator, valid_linear_flow):
        """Test all nodes reachable in linear flow."""
        nodes, edges = valid_linear_flow
        start_nodes = {"A"}
        reachable = validator._get_reachable_nodes(start_nodes, edges)

        assert reachable == {"A", "B", "C"}

    def test_reachable_branching(self, validator, valid_branching_flow):
        """Test all nodes reachable in branching flow."""
        nodes, edges = valid_branching_flow
        start_nodes = {"A"}
        reachable = validator._get_reachable_nodes(start_nodes, edges)

        assert reachable == {"A", "B", "C", "D"}

    def test_partial_reachability(self, validator):
        """Test partial reachability in disconnected graph."""
        edges = [
            {"id": "e1", "source": "A", "target": "B"},
            {"id": "e2", "source": "C", "target": "D"},
        ]
        start_nodes = {"A"}
        reachable = validator._get_reachable_nodes(start_nodes, edges)

        assert reachable == {"A", "B"}
        assert "C" not in reachable
        assert "D" not in reachable

    def test_no_edges(self, validator):
        """Test reachability with no edges."""
        edges = []
        start_nodes = {"A"}
        reachable = validator._get_reachable_nodes(start_nodes, edges)

        assert reachable == {"A"}
