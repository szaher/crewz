"""Flow execution engine for visual workflows."""

from typing import Dict, Any, List, Optional
import asyncio

from ..models import Flow, Execution
from ..services.flow_validator import FlowValidator
from ..services.execution_events import ExecutionEventPublisher
from .crew_factory import CrewFactory
from .agent_factory import AgentFactory


class FlowExecutor:
    """
    Executor for visual flows using topological sort.

    Executes nodes in dependency order and manages data flow between nodes.
    """

    def __init__(
        self,
        crew_factory: CrewFactory,
        agent_factory: AgentFactory,
        event_publisher: ExecutionEventPublisher,
    ):
        self.crew_factory = crew_factory
        self.agent_factory = agent_factory
        self.event_publisher = event_publisher
        self.validator = FlowValidator()
        self.langfuse_handler = None  # Set during execution

    async def execute_flow(
        self,
        flow: Flow,
        execution: Execution,
        input_data: Dict[str, Any],
        langfuse_handler: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Execute a flow end-to-end.

        Args:
            flow: Flow to execute
            execution: Execution record
            input_data: Input data for the flow
            langfuse_handler: Optional Langfuse callback handler for LLM tracing

        Returns:
            Output data from the flow

        Raises:
            Exception: If execution fails
        """
        # Store handler for use in node execution
        self.langfuse_handler = langfuse_handler

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
            expected_output = node_data.get("expected_output", "A detailed response to the task")

            # Check if agent_id is an integer (old data before UUID migration)
            if isinstance(agent_id, int):
                raise ValueError(
                    f"Agent node uses old integer ID ({agent_id}). "
                    f"Please re-edit this flow and select the agent again to use UUID IDs."
                )

            # Convert string UUID to UUID object if needed
            from uuid import UUID
            if isinstance(agent_id, str):
                try:
                    agent_id = UUID(agent_id)
                except ValueError:
                    raise ValueError(f"Invalid agent UUID: {agent_id}")

            # Extract variables from input_data
            variables = input_data.get("variables", {})

            # Load agent from database
            from ..db import SessionLocal
            from ..models import Agent
            from crewai import Task as CrewTask, Crew
            db = SessionLocal()
            try:
                db_agent = db.query(Agent).filter(Agent.id == agent_id).first()
                if not db_agent:
                    raise ValueError(f"Agent not found: {agent_id}")

                # Create CrewAI agent with Langfuse handler
                crewai_agent = await self.agent_factory.from_db_model(
                    db_agent,
                    langfuse_handler=self.langfuse_handler
                )

                # Variable substitution helper
                def substitute_variables(text: str, vars: dict) -> str:
                    if not text or not vars:
                        return text
                    result = text
                    for k, v in vars.items():
                        result = result.replace(f'{{{k}}}', str(v))
                    return result

                # Substitute variables in task description and expected output
                task_desc = substitute_variables(task_description, variables)
                expected_out = substitute_variables(expected_output, variables)

                # Create a single task for the agent
                task = CrewTask(
                    description=task_desc,
                    agent=crewai_agent,
                    expected_output=expected_out,
                )

                # Create a crew with this single agent and task
                crew = Crew(
                    agents=[crewai_agent],
                    tasks=[task],
                    verbose=True
                )

                # Execute crew in a separate thread to avoid blocking
                result = await asyncio.to_thread(crew.kickoff)

                return {
                    "result": str(result),
                    "metadata": {"agent_id": agent_id, "agent_name": db_agent.name}
                }
            finally:
                db.close()

        elif node_type == "crew":
            # Crew execution node
            crew_id = node_data.get("crew_id")

            # Extract variables from input_data
            variables = input_data.get("variables", {})
            tasks_input = input_data.get("tasks", [])

            # Load crew from database
            from ..db import SessionLocal
            from ..models import Crew
            from ..services.task_service import TaskService
            from ..services.llm_service import LLMService
            from ..services.docker_service import DockerService
            from ..crewai.tool_adapter import ToolAdapter
            from ..models.agent import Agent
            from crewai import Task as CrewTask
            import json

            db = SessionLocal()
            try:
                db_crew = db.query(Crew).filter(Crew.id == crew_id).first()
                if not db_crew:
                    raise ValueError(f"Crew not found: {crew_id}")

                # Create CrewAI crew with Langfuse handler
                crewai_crew = await self.crew_factory.from_db_model(db_crew, langfuse_handler=self.langfuse_handler)

                # Build tasks from database
                task_service = TaskService(db)
                stored_tasks = await task_service.get_crew_tasks(crew_id)

                def substitute_variables(text: str, vars: dict) -> str:
                    if not text or not vars:
                        return text
                    result = text
                    for k, v in vars.items():
                        result = result.replace(f'{{{k}}}', str(v))
                    return result

                tasks = []
                task_map = {}

                if stored_tasks:
                    # Use stored tasks from database
                    for db_task in stored_tasks:
                        # Resolve agent with Langfuse handler
                        agent_instance = None
                        if db_task.agent_id:
                            agent_model = db.query(Agent).filter(Agent.id == db_task.agent_id).first()
                            if agent_model:
                                agent_instance = await self.agent_factory.from_db_model(
                                    agent_model,
                                    langfuse_handler=self.langfuse_handler
                                )
                        else:
                            agents = getattr(crewai_crew, 'agents', [])
                            agent_instance = agents[0] if agents else None

                        # Context refs
                        context_tasks = []
                        if db_task.context:
                            try:
                                context_data = json.loads(db_task.context) if isinstance(db_task.context, str) else db_task.context
                                if isinstance(context_data, dict) and 'task_ids' in context_data:
                                    for tid in context_data['task_ids']:
                                        if tid in task_map:
                                            context_tasks.append(task_map[tid])
                            except Exception:
                                pass

                        # Tools (basic: reuse agent tools if any)
                        task_tools = []
                        if db_task.tools_config and agent_instance and hasattr(agent_instance, 'tools'):
                            task_tools = agent_instance.tools

                        description = substitute_variables(db_task.description, variables)
                        expected_output = substitute_variables(db_task.expected_output, variables)

                        task_kwargs = {
                            'description': description,
                            'agent': agent_instance,
                            'expected_output': expected_output,
                            'async_execution': db_task.async_execution,
                        }
                        if context_tasks:
                            task_kwargs['context'] = context_tasks
                        if task_tools:
                            task_kwargs['tools'] = task_tools
                        if db_task.output_file:
                            task_kwargs['output_file'] = db_task.output_file

                        t = CrewTask(**task_kwargs)
                        tasks.append(t)
                        task_map[db_task.id] = t
                else:
                    # Use tasks from input_data or node config
                    if not tasks_input:
                        task_description = node_data.get("task", "Complete the assigned objectives")
                        tasks_input = [task_description]

                    agents = getattr(crewai_crew, 'agents', [])
                    for i, task_desc in enumerate(tasks_input):
                        agent_instance = agents[i % len(agents)] if agents else None
                        t = CrewTask(
                            description=substitute_variables(task_desc, variables),
                            agent=agent_instance,
                            expected_output=f"Completion of: {task_desc}",
                        )
                        tasks.append(t)

                crewai_crew.tasks = tasks

                # Execute crew in a separate thread to avoid blocking
                result = await asyncio.to_thread(crewai_crew.kickoff)

                return {
                    "result": str(result),
                    "task_count": len(tasks),
                    "metadata": {"crew_id": crew_id, "crew_name": db_crew.name}
                }
            finally:
                db.close()

        elif node_type == "tool":
            # Tool execution node
            tool_id = node_data.get("tool_id")
            tool_inputs = node_data.get("inputs", {})

            # Merge node config inputs with runtime inputs
            merged_inputs = {**tool_inputs, **input_data}

            # Load tool from DB
            from ..db import SessionLocal
            from ..models.tool import Tool
            from ..services.docker_service import DockerService
            from ..crewai.tool_adapter import ToolAdapter
            import json
            db = SessionLocal()
            try:
                db_tool = db.query(Tool).filter(Tool.id == tool_id).first()
                if not db_tool:
                    raise ValueError(f"Tool not found: {tool_id}")

                # Prepare input payload as string
                try:
                    input_str = json.dumps(merged_inputs)
                except Exception:
                    input_str = str(merged_inputs)

                if db_tool.tool_type == "docker":
                    docker_service = DockerService()
                    result = await docker_service.execute_tool(
                        tool_id=db_tool.id,
                        input_data=input_str,
                        docker_image=db_tool.docker_image,
                        docker_command=getattr(db_tool, 'docker_command', None),
                    )
                else:
                    # Use ToolAdapter for builtin/custom tools
                    adapter = ToolAdapter(DockerService())
                    crew_tool = await adapter.from_db_model(db_tool)
                    maybe = crew_tool.run(input_str) if hasattr(crew_tool, 'run') else crew_tool(input_str)
                    result = await maybe if hasattr(maybe, '__await__') else maybe

                return {"result": result, "metadata": {"tool_id": tool_id}}
            finally:
                db.close()

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
