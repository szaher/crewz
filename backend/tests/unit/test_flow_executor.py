"""Unit tests for FlowExecutor - topological sort and execution order."""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from src.crewai.flow_executor import FlowExecutor
from src.models.flow import Flow
from src.models.execution import Execution


@pytest.fixture
def mock_crew_factory():
    """Create a mock CrewFactory."""
    return Mock()


@pytest.fixture
def mock_event_publisher():
    """Create a mock ExecutionEventPublisher."""
    publisher = Mock()
    publisher.publish_node_started = AsyncMock()
    publisher.publish_node_completed = AsyncMock()
    publisher.publish_node_failed = AsyncMock()
    return publisher


@pytest.fixture
def flow_executor(mock_crew_factory, mock_event_publisher):
    """Create a FlowExecutor instance with mocked dependencies."""
    return FlowExecutor(
        crew_factory=mock_crew_factory,
        event_publisher=mock_event_publisher,
    )


@pytest.fixture
def simple_flow():
    """Create a simple flow: input -> agent -> output."""
    flow = Mock(spec=Flow)
    flow.id = 1
    flow.nodes = [
        {"id": "input", "type": "input", "data": {}},
        {"id": "agent", "type": "agent", "data": {"agent_id": 1}},
        {"id": "output", "type": "output", "data": {}},
    ]
    flow.edges = [
        {"id": "e1", "source": "input", "target": "agent"},
        {"id": "e2", "source": "agent", "target": "output"},
    ]
    return flow


@pytest.fixture
def branching_flow():
    """Create a branching flow: input -> [agent1, agent2] -> output."""
    flow = Mock(spec=Flow)
    flow.id = 2
    flow.nodes = [
        {"id": "input", "type": "input", "data": {}},
        {"id": "agent1", "type": "agent", "data": {"agent_id": 1}},
        {"id": "agent2", "type": "agent", "data": {"agent_id": 2}},
        {"id": "output", "type": "output", "data": {}},
    ]
    flow.edges = [
        {"id": "e1", "source": "input", "target": "agent1"},
        {"id": "e2", "source": "input", "target": "agent2"},
        {"id": "e3", "source": "agent1", "target": "output"},
        {"id": "e4", "source": "agent2", "target": "output"},
    ]
    return flow


@pytest.fixture
def mock_execution():
    """Create a mock Execution."""
    execution = Mock(spec=Execution)
    execution.id = 1
    return execution


class TestExecuteFlow:
    """Tests for execute_flow method."""

    @pytest.mark.asyncio
    async def test_execute_simple_flow(
        self, flow_executor, simple_flow, mock_execution, mock_event_publisher
    ):
        """Test execution of a simple linear flow."""
        # Arrange
        input_data = {"message": "Hello"}

        # Act
        result = await flow_executor.execute_flow(
            flow=simple_flow,
            execution=mock_execution,
            input_data=input_data,
        )

        # Assert
        # Verify node started events were published in order
        assert mock_event_publisher.publish_node_started.call_count == 3
        calls = mock_event_publisher.publish_node_started.call_args_list
        assert calls[0][1]["node_id"] == "input"
        assert calls[1][1]["node_id"] == "agent"
        assert calls[2][1]["node_id"] == "output"

        # Verify node completed events were published
        assert mock_event_publisher.publish_node_completed.call_count == 3

    @pytest.mark.asyncio
    async def test_execute_flow_topological_order(
        self, flow_executor, branching_flow, mock_execution, mock_event_publisher
    ):
        """Test flow execution respects topological order."""
        # Arrange
        input_data = {"message": "Hello"}

        # Act
        await flow_executor.execute_flow(
            flow=branching_flow,
            execution=mock_execution,
            input_data=input_data,
        )

        # Assert
        calls = mock_event_publisher.publish_node_started.call_args_list

        # Input must be first
        assert calls[0][1]["node_id"] == "input"

        # Output must be last
        assert calls[-1][1]["node_id"] == "output"

        # Agent1 and agent2 must be between input and output
        agent_indices = [i for i, call in enumerate(calls)
                        if call[1]["node_id"] in ["agent1", "agent2"]]
        assert len(agent_indices) == 2
        assert all(0 < idx < len(calls) - 1 for idx in agent_indices)

    @pytest.mark.asyncio
    async def test_execute_flow_node_failure(
        self, flow_executor, simple_flow, mock_execution, mock_event_publisher
    ):
        """Test flow execution handles node failures."""
        # Arrange
        input_data = {"message": "Hello"}

        # Mock _execute_node to fail on agent node
        original_execute_node = flow_executor._execute_node

        async def mock_execute_node(node, input_data):
            if node["type"] == "agent":
                raise Exception("Agent execution failed")
            return await original_execute_node(node, input_data)

        flow_executor._execute_node = mock_execute_node

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await flow_executor.execute_flow(
                flow=simple_flow,
                execution=mock_execution,
                input_data=input_data,
            )

        assert "Agent execution failed" in str(exc_info.value)

        # Verify node failed event was published
        mock_event_publisher.publish_node_failed.assert_called_once()
        call_args = mock_event_publisher.publish_node_failed.call_args[1]
        assert call_args["node_id"] == "agent"


class TestGetNodeById:
    """Tests for _get_node_by_id method."""

    def test_get_existing_node(self, flow_executor):
        """Test retrieving an existing node."""
        nodes = [
            {"id": "A", "type": "agent", "data": {}},
            {"id": "B", "type": "tool", "data": {}},
        ]

        result = flow_executor._get_node_by_id(nodes, "B")
        assert result["id"] == "B"
        assert result["type"] == "tool"

    def test_get_nonexistent_node(self, flow_executor):
        """Test retrieving a non-existent node raises error."""
        nodes = [
            {"id": "A", "type": "agent", "data": {}},
        ]

        with pytest.raises(ValueError) as exc_info:
            flow_executor._get_node_by_id(nodes, "Z")

        assert "not found" in str(exc_info.value)


class TestCollectNodeInputs:
    """Tests for _collect_node_inputs method."""

    def test_collect_single_input(self, flow_executor):
        """Test collecting input from single upstream node."""
        edges = [
            {"id": "e1", "source": "A", "target": "B", "label": "data"},
        ]
        node_outputs = {"A": {"result": "output from A"}}

        inputs = flow_executor._collect_node_inputs("B", edges, node_outputs)

        assert inputs == {"data": {"result": "output from A"}}

    def test_collect_multiple_inputs(self, flow_executor):
        """Test collecting inputs from multiple upstream nodes."""
        edges = [
            {"id": "e1", "source": "A", "target": "C", "label": "input1"},
            {"id": "e2", "source": "B", "target": "C", "label": "input2"},
        ]
        node_outputs = {
            "A": {"result": "output A"},
            "B": {"result": "output B"},
        }

        inputs = flow_executor._collect_node_inputs("C", edges, node_outputs)

        assert inputs == {
            "input1": {"result": "output A"},
            "input2": {"result": "output B"},
        }

    def test_collect_default_label(self, flow_executor):
        """Test default label when not specified."""
        edges = [
            {"id": "e1", "source": "A", "target": "B"},  # No label
        ]
        node_outputs = {"A": {"result": "output"}}

        inputs = flow_executor._collect_node_inputs("B", edges, node_outputs)

        assert inputs == {"input": {"result": "output"}}

    def test_collect_no_inputs(self, flow_executor):
        """Test node with no incoming edges."""
        edges = [
            {"id": "e1", "source": "A", "target": "B"},
        ]
        node_outputs = {"A": {"result": "output"}}

        inputs = flow_executor._collect_node_inputs("C", edges, node_outputs)

        assert inputs == {}


class TestExecuteNode:
    """Tests for _execute_node method."""

    @pytest.mark.asyncio
    async def test_execute_input_node(self, flow_executor):
        """Test execution of input node."""
        node = {"id": "input", "type": "input", "data": {}}
        input_data = {"message": "test"}

        result = await flow_executor._execute_node(node, input_data)

        assert result == input_data

    @pytest.mark.asyncio
    async def test_execute_output_node(self, flow_executor):
        """Test execution of output node."""
        node = {"id": "output", "type": "output", "data": {}}
        input_data = {"result": "final output"}

        result = await flow_executor._execute_node(node, input_data)

        assert result == input_data

    @pytest.mark.asyncio
    async def test_execute_agent_node(self, flow_executor):
        """Test execution of agent node."""
        node = {"id": "agent", "type": "agent", "data": {"agent_id": 1}}
        input_data = {"task": "analyze data"}

        result = await flow_executor._execute_node(node, input_data)

        # Currently returns placeholder - verify structure
        assert "result" in result

    @pytest.mark.asyncio
    async def test_execute_crew_node(self, flow_executor):
        """Test execution of crew node."""
        node = {"id": "crew", "type": "crew", "data": {"crew_id": 1}}
        input_data = {"task": "research topic"}

        result = await flow_executor._execute_node(node, input_data)

        # Currently returns placeholder - verify structure
        assert "result" in result

    @pytest.mark.asyncio
    async def test_execute_tool_node(self, flow_executor):
        """Test execution of tool node."""
        node = {"id": "tool", "type": "tool", "data": {"tool_id": 1}}
        input_data = {"parameters": "test"}

        result = await flow_executor._execute_node(node, input_data)

        # Currently returns placeholder - verify structure
        assert "result" in result

    @pytest.mark.asyncio
    async def test_execute_llm_node(self, flow_executor):
        """Test execution of LLM node."""
        node = {
            "id": "llm",
            "type": "llm",
            "data": {"llm_provider_id": 1, "prompt": "Analyze: {input}"}
        }
        input_data = {"input": "test data"}

        result = await flow_executor._execute_node(node, input_data)

        # Currently returns placeholder - verify structure
        assert "result" in result

    @pytest.mark.asyncio
    async def test_execute_condition_node(self, flow_executor):
        """Test execution of condition node."""
        node = {
            "id": "condition",
            "type": "condition",
            "data": {"condition": "value > 10"}
        }
        input_data = {"value": 15}

        result = await flow_executor._execute_node(node, input_data)

        # Currently returns placeholder - verify structure
        assert "branch" in result

    @pytest.mark.asyncio
    async def test_execute_unknown_node_type(self, flow_executor):
        """Test execution of unknown node type raises error."""
        node = {"id": "unknown", "type": "custom_type", "data": {}}
        input_data = {}

        with pytest.raises(ValueError) as exc_info:
            await flow_executor._execute_node(node, input_data)

        assert "Unknown node type" in str(exc_info.value)


class TestCollectFlowOutputs:
    """Tests for _collect_flow_outputs method."""

    def test_collect_single_output(self, flow_executor):
        """Test collecting output from single output node."""
        flow = Mock(spec=Flow)
        flow.nodes = [
            {"id": "output", "type": "output", "data": {"name": "result"}},
        ]
        node_outputs = {
            "output": {"value": "final result"}
        }

        outputs = flow_executor._collect_flow_outputs(flow, node_outputs)

        assert outputs == {"result": {"value": "final result"}}

    def test_collect_multiple_outputs(self, flow_executor):
        """Test collecting outputs from multiple output nodes."""
        flow = Mock(spec=Flow)
        flow.nodes = [
            {"id": "output1", "type": "output", "data": {"name": "result1"}},
            {"id": "output2", "type": "output", "data": {"name": "result2"}},
        ]
        node_outputs = {
            "output1": {"value": "result 1"},
            "output2": {"value": "result 2"},
        }

        outputs = flow_executor._collect_flow_outputs(flow, node_outputs)

        assert outputs == {
            "result1": {"value": "result 1"},
            "result2": {"value": "result 2"},
        }

    def test_collect_output_default_name(self, flow_executor):
        """Test output collection with default name (node ID)."""
        flow = Mock(spec=Flow)
        flow.nodes = [
            {"id": "output", "type": "output", "data": {}},  # No name specified
        ]
        node_outputs = {
            "output": {"value": "result"}
        }

        outputs = flow_executor._collect_flow_outputs(flow, node_outputs)

        assert outputs == {"output": {"value": "result"}}

    def test_collect_no_outputs(self, flow_executor):
        """Test flow with no output nodes."""
        flow = Mock(spec=Flow)
        flow.nodes = [
            {"id": "agent", "type": "agent", "data": {}},
        ]
        node_outputs = {
            "agent": {"value": "result"}
        }

        outputs = flow_executor._collect_flow_outputs(flow, node_outputs)

        assert outputs == {}


class TestTopologicalSortIntegration:
    """Integration tests for topological sort in flow execution."""

    @pytest.mark.asyncio
    async def test_complex_dag_execution_order(
        self, flow_executor, mock_execution, mock_event_publisher
    ):
        """Test execution order for complex DAG."""
        flow = Mock(spec=Flow)
        flow.id = 1
        flow.nodes = [
            {"id": "A", "type": "input", "data": {}},
            {"id": "B", "type": "agent", "data": {}},
            {"id": "C", "type": "agent", "data": {}},
            {"id": "D", "type": "tool", "data": {}},
            {"id": "E", "type": "output", "data": {}},
        ]
        flow.edges = [
            {"id": "e1", "source": "A", "target": "B"},
            {"id": "e2", "source": "A", "target": "C"},
            {"id": "e3", "source": "B", "target": "D"},
            {"id": "e4", "source": "C", "target": "D"},
            {"id": "e5", "source": "D", "target": "E"},
        ]

        input_data = {"test": "data"}

        # Act
        await flow_executor.execute_flow(
            flow=flow,
            execution=mock_execution,
            input_data=input_data,
        )

        # Assert - verify topological order constraints
        calls = mock_event_publisher.publish_node_started.call_args_list
        node_order = [call[1]["node_id"] for call in calls]

        # A must be before B and C
        assert node_order.index("A") < node_order.index("B")
        assert node_order.index("A") < node_order.index("C")

        # B and C must be before D
        assert node_order.index("B") < node_order.index("D")
        assert node_order.index("C") < node_order.index("D")

        # D must be before E
        assert node_order.index("D") < node_order.index("E")

    @pytest.mark.asyncio
    async def test_data_flow_through_nodes(
        self, flow_executor, simple_flow, mock_execution
    ):
        """Test data flows correctly from node to node."""
        # Arrange
        input_data = {"message": "test"}

        # Spy on _execute_node to track inputs
        executed_nodes = []
        original_execute_node = flow_executor._execute_node

        async def spy_execute_node(node, node_input):
            executed_nodes.append({
                "node_id": node["id"],
                "input": node_input
            })
            return await original_execute_node(node, node_input)

        flow_executor._execute_node = spy_execute_node

        # Act
        await flow_executor.execute_flow(
            flow=simple_flow,
            execution=mock_execution,
            input_data=input_data,
        )

        # Assert
        # Input node should receive flow input
        assert executed_nodes[0]["node_id"] == "input"
        assert executed_nodes[0]["input"] == {}  # No upstream nodes

        # Agent node should receive output from input node
        assert executed_nodes[1]["node_id"] == "agent"
        assert "input" in executed_nodes[1]["input"]

        # Output node should receive output from agent node
        assert executed_nodes[2]["node_id"] == "output"
        assert "input" in executed_nodes[2]["input"]
