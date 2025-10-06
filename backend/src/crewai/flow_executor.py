"""Flow execution engine for visual workflows."""

from typing import Dict, Any, List
import asyncio

from ..models import Flow, Execution
from ..services.flow_validator import FlowValidator
from ..services.execution_events import ExecutionEventPublisher
from .crew_factory import CrewFactory


class FlowExecutor:
    """
    Executor for visual flows using topological sort.

    Executes nodes in dependency order and manages data flow between nodes.
    """

    def __init__(
        self,
        crew_factory: CrewFactory,
        event_publisher: ExecutionEventPublisher,
    ):
        self.crew_factory = crew_factory
        self.event_publisher = event_publisher
        self.validator = FlowValidator()

    async def execute_flow(
        self,
        flow: Flow,
        execution: Execution,
        input_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute a flow end-to-end.

        Args:
            flow: Flow to execute
            execution: Execution record
            input_data: Input data for the flow

        Returns:
            Output data from the flow

        Raises:
            Exception: If execution fails
        """
        # Get execution order via topological sort
        execution_order = self.validator.topological_sort(flow.nodes, flow.edges)

        # Track node outputs
        node_outputs = {"__input__": input_data}

        # Execute nodes in order
        for node_id in execution_order:
            node = self._get_node_by_id(flow.nodes, node_id)

            # Get inputs from upstream nodes
            node_input = self._collect_node_inputs(
                node_id, flow.edges, node_outputs
            )

            # Publish node started event
            await self.event_publisher.publish_node_started(
                execution_id=execution.id,
                node_id=node_id,
                node_type=node["type"],
            )

            try:
                # Execute node based on type
                output = await self._execute_node(node, node_input)

                # Store output
                node_outputs[node_id] = output

                # Publish node completed event
                await self.event_publisher.publish_node_completed(
                    execution_id=execution.id,
                    node_id=node_id,
                    output=output,
                )

            except Exception as e:
                # Publish node failed event
                await self.event_publisher.publish_node_failed(
                    execution_id=execution.id,
                    node_id=node_id,
                    error=str(e),
                )
                raise

        # Return outputs from output nodes
        return self._collect_flow_outputs(flow, node_outputs)

    def _get_node_by_id(
        self, nodes: List[Dict[str, Any]], node_id: str
    ) -> Dict[str, Any]:
        """Get node by ID."""
        for node in nodes:
            if node["id"] == node_id:
                return node
        raise ValueError(f"Node not found: {node_id}")

    def _collect_node_inputs(
        self,
        node_id: str,
        edges: List[Dict[str, Any]],
        node_outputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Collect inputs for a node from upstream edges."""
        inputs = {}

        for edge in edges:
            if edge["target"] == node_id:
                source_id = edge["source"]
                if source_id in node_outputs:
                    # Use edge label as input key, or default to "input"
                    key = edge.get("label", "input")
                    inputs[key] = node_outputs[source_id]

        return inputs

    async def _execute_node(
        self, node: Dict[str, Any], input_data: Dict[str, Any]
    ) -> Any:
        """
        Execute a single node based on its type.

        Args:
            node: Node configuration
            input_data: Input data for the node

        Returns:
            Node output
        """
        node_type = node["type"]
        node_data = node.get("data", {})

        if node_type == "input":
            # Input node - just pass through
            return input_data

        elif node_type == "output":
            # Output node - return input as-is
            return input_data

        elif node_type == "agent":
            # Agent execution node
            agent_id = node_data.get("agent_id")
            task_description = node_data.get("task", "")
            expected_output = node_data.get("expected_output", "")

            # Execute agent via CrewAI
            agent = await self.crew_factory.create_agent_from_db(agent_id)
            result = await agent.execute_task(task_description, input_data)
            return {"result": result, "metadata": {"agent_id": agent_id}}

        elif node_type == "crew":
            # Crew execution node
            crew_id = node_data.get("crew_id")
            task_description = node_data.get("task", "")

            # Execute crew via CrewAI
            crew = await self.crew_factory.create_crew_from_db(crew_id)
            result = await crew.kickoff(task_description, input_data)
            return {"result": result, "metadata": {"crew_id": crew_id}}

        elif node_type == "tool":
            # Tool execution node
            tool_id = node_data.get("tool_id")
            tool_inputs = node_data.get("inputs", {})

            # Merge node config inputs with runtime inputs
            merged_inputs = {**tool_inputs, **input_data}

            # Execute tool via Docker service
            from ..services.docker_service import DockerService
            docker_service = DockerService()
            result = await docker_service.execute_tool(tool_id, merged_inputs)
            return {"result": result, "metadata": {"tool_id": tool_id}}

        elif node_type == "llm":
            # Direct LLM call node
            provider_id = node_data.get("llm_provider_id")
            prompt_template = node_data.get("prompt", "")

            # Format prompt with input data
            prompt = prompt_template.format(**input_data)

            # Execute LLM via LLM service
            from ..services.llm_service import LLMService
            llm_service = LLMService()
            result = await llm_service.complete(provider_id, prompt)
            return {"result": result, "metadata": {"provider_id": provider_id}}

        elif node_type == "condition":
            # Conditional branching node
            condition_expr = node_data.get("condition", "")

            # Evaluate condition expression
            # Simple evaluation - in production, use safe evaluator
            try:
                # Create evaluation context from input data
                context = {**input_data}
                result = eval(condition_expr, {"__builtins__": {}}, context)
                branch = "true" if result else "false"
            except Exception as e:
                # Default to false branch on error
                branch = "false"

            return {"branch": branch, "metadata": {"condition": condition_expr}}

        else:
            raise ValueError(f"Unknown node type: {node_type}")

    def _collect_flow_outputs(
        self, flow: Flow, node_outputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Collect outputs from all output nodes."""
        outputs = {}

        for node in flow.nodes:
            if node["type"] == "output":
                node_id = node["id"]
                if node_id in node_outputs:
                    output_key = node.get("data", {}).get("name", node_id)
                    outputs[output_key] = node_outputs[node_id]

        return outputs
