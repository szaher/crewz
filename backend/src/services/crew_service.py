"""Crew service for CrewAI crew management."""

from typing import List, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from ..models import Crew, Agent
from ..models.task import Task as TaskModel
from ..models.crew import CrewProcess
from ..models.execution import Execution


class CrewService:
    """Service for crew CRUD operations."""

    def __init__(self, db: Session):
        self.db = db

    async def create_crew(
        self,
        name: str,
        description: str,
        process: str,
        agent_ids: List[int],
        task_ids: List[int] = None,
        verbose: bool = False,
        memory: bool = False,
        manager_llm_provider_id: int = None,
    ) -> Crew:
        """
        Create a new crew.

        Args:
            name: Crew name
            description: Crew description
            process: Collaboration pattern (sequential, hierarchical)
            agent_ids: List of agent IDs to include
            task_ids: List of task IDs to assign to this crew
            verbose: Enable verbose logging
            memory: Enable crew memory
            manager_llm_provider_id: LLM provider for hierarchical manager

        Returns:
            Created Crew model
        """
        # Ensure correct enum type for process
        proc = process if isinstance(process, CrewProcess) else CrewProcess(process)

        crew = Crew(
            name=name,
            description=description,
            process=proc,
            verbose=verbose,
            memory=memory,
            manager_llm_provider_id=manager_llm_provider_id,
        )

        self.db.add(crew)
        self.db.flush()

        # Associate agents
        if agent_ids:
            agents = self.db.query(Agent).filter(Agent.id.in_(agent_ids)).all()
            crew.agents = agents

        # Assign tasks to crew
        if task_ids:
            tasks = self.db.query(TaskModel).filter(TaskModel.id.in_(task_ids)).all()
            for task in tasks:
                task.crew_id = crew.id

        self.db.commit()
        self.db.refresh(crew)

        return crew

    async def get_crew(self, crew_id: int) -> Crew:
        """Get crew by ID."""
        crew = self.db.query(Crew).filter(Crew.id == crew_id).first()

        if not crew:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Crew not found",
            )

        return crew

    async def list_crews(self, page: int = 1, page_size: int = 10) -> dict:
        """List crews with pagination."""
        query = self.db.query(Crew)

        total = query.count()
        offset = (page - 1) * page_size
        crews = query.offset(offset).limit(page_size).all()

        return {
            "crews": crews,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def update_crew(
        self,
        crew_id: int,
        name: str = None,
        description: str = None,
        process: str = None,
        agent_ids: List[int] = None,
        task_ids: List[int] = None,
        verbose: bool = None,
        memory: bool = None,
    ) -> Crew:
        """Update an existing crew."""
        crew = await self.get_crew(crew_id)

        if name is not None:
            crew.name = name
        if description is not None:
            crew.description = description
        if process is not None:
            crew.process = process if isinstance(process, CrewProcess) else CrewProcess(process)
        if verbose is not None:
            crew.verbose = verbose
        if memory is not None:
            crew.memory = memory

        # Update agents
        if agent_ids is not None:
            agents = self.db.query(Agent).filter(Agent.id.in_(agent_ids)).all()
            crew.agents = agents

        # Update task assignments
        if task_ids is not None:
            # First, unassign all current tasks from this crew
            current_tasks = self.db.query(TaskModel).filter(TaskModel.crew_id == crew_id).all()
            for task in current_tasks:
                task.crew_id = None

            # Then assign the new tasks
            if task_ids:
                new_tasks = self.db.query(TaskModel).filter(TaskModel.id.in_(task_ids)).all()
                for task in new_tasks:
                    task.crew_id = crew_id

        self.db.commit()
        self.db.refresh(crew)

        return crew

    async def delete_crew(self, crew_id: int) -> None:
        """Delete a crew."""
        crew = await self.get_crew(crew_id)
        self.db.delete(crew)
        self.db.commit()

    def execute_crew(self, crew_id: UUID, payload: Dict[str, Any], execution_id: UUID = None, stream_handler=None) -> Dict[str, Any]:
        """
        Execute a crew with the given inputs.

        Args:
            crew_id: UUID of the crew to execute
            payload: Execution payload containing input_data and config
            execution_id: Optional execution ID for streaming
            stream_handler: Optional StreamHandler for live output

        Returns:
            Dict containing execution results

        Raises:
            HTTPException: If crew not found or execution fails
        """
        from ..crewai.crew_factory import CrewFactory
        from ..crewai.agent_factory import AgentFactory
        from ..crewai.tool_adapter import ToolAdapter
        from ..services.llm_service import LLMService
        from ..services.docker_service import DockerService
        import socket

        # Emit started event if stream handler provided
        if stream_handler:
            worker_id = socket.gethostname()
            stream_handler.emit_started(worker_id)

        # Get crew from database
        crew = self.db.query(Crew).filter(Crew.id == crew_id).first()
        if not crew:
            error_msg = f"Crew {crew_id} not found"
            if stream_handler:
                stream_handler.emit_error("NotFoundError", error_msg)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg
            )

        if stream_handler:
            stream_handler.emit_output(f"Loaded crew: {crew.name}", "stdout")

        # Get crew tasks
        tasks = self.db.query(TaskModel).filter(TaskModel.crew_id == crew_id).order_by(TaskModel.id).all()

        if stream_handler:
            stream_handler.emit_output(f"Found {len(tasks)} tasks for crew", "stdout")

        # Validate required variables are present in input_data
        raw_input_data = payload.get("input_data", {})

        # Handle both flat and nested variable formats
        # Flat: {"topic": "...", "level": "..."}
        # Nested: {"variables": {"topic": "...", "level": "..."}}
        if "variables" in raw_input_data and isinstance(raw_input_data["variables"], dict):
            input_data = raw_input_data["variables"]
        else:
            input_data = raw_input_data

        required_variables = set()

        for task in tasks:
            if task.variables:
                required_variables.update(task.variables)

        if required_variables:
            missing_variables = required_variables - set(input_data.keys())
            if missing_variables:
                error_msg = f"Missing required variables: {', '.join(sorted(missing_variables))}. Required: {', '.join(sorted(required_variables))}"
                if stream_handler:
                    stream_handler.emit_error("ValidationError", error_msg)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error_msg
                )

        if stream_handler and required_variables:
            stream_handler.emit_output(f"Validated input variables: {', '.join(sorted(required_variables))}", "stdout")

        # Initialize execution dependencies
        if stream_handler:
            stream_handler.emit_output("Initializing execution dependencies...", "stdout")

        llm_service = LLMService(self.db)
        docker_service = DockerService()
        tool_adapter = ToolAdapter(docker_service)
        agent_factory = AgentFactory(llm_service, tool_adapter)
        crew_factory = CrewFactory(agent_factory)

        # Create CrewAI crew instance from database model
        if stream_handler:
            stream_handler.emit_output("Building CrewAI crew instance...", "stdout")

        import asyncio
        crewai_crew = asyncio.run(crew_factory.from_db_model(crew))

        # Convert database tasks to CrewAI tasks
        from crewai import Task as CrewAITask
        crewai_tasks = []
        for idx, task in enumerate(tasks):
            if stream_handler:
                stream_handler.emit_progress(
                    percent=int((idx / len(tasks)) * 30),  # 0-30% for setup
                    current_step=f"Preparing task: {task.name or task.description[:50]}",
                    total_steps=len(tasks)
                )

            # Get the agent for this task
            agent = None
            if task.agent_id:
                agent_model = self.db.query(Agent).filter(Agent.id == task.agent_id).first()
                if agent_model:
                    agent = asyncio.run(agent_factory.from_db_model(agent_model))

            if agent:
                crewai_task = CrewAITask(
                    description=task.description,
                    expected_output=task.expected_output,
                    agent=agent
                )
                crewai_tasks.append(crewai_task)

        if stream_handler:
            stream_handler.emit_output(f"Starting execution with inputs: {list(input_data.keys())}", "stdout")
            stream_handler.emit_progress(
                percent=30,
                current_step="Executing crew",
                total_steps=len(tasks)
            )

        # Add tasks to crew
        if crewai_tasks:
            crewai_crew.tasks = crewai_tasks

        # Execute the crew
        try:
            result = crewai_crew.kickoff(inputs=input_data)

            if stream_handler:
                stream_handler.emit_progress(
                    percent=90,
                    current_step="Processing results",
                    total_steps=len(tasks)
                )

            # Convert result to dict
            if hasattr(result, 'raw'):
                result_data = result.raw
            elif hasattr(result, '__dict__'):
                result_data = result.__dict__
            else:
                result_data = str(result)

            # Save artifacts before completing
            saved_artifacts = []
            if stream_handler and execution_id:
                stream_handler.emit_output("Saving execution artifacts...", "stdout")
                # Get execution to retrieve tenant_id (with user relationship)
                from sqlalchemy.orm import joinedload
                execution = self.db.query(Execution).options(joinedload(Execution.user)).filter(Execution.id == execution_id).first()
                if execution:
                    saved_artifacts = self._save_execution_artifacts(
                        execution_id=execution_id,
                        result_data=result_data,
                        stream_handler=stream_handler,
                        crew_name=crew.name,
                        user_id=execution.user_id,
                        tenant_id=execution.user.tenant_id
                    )

            if stream_handler:
                stream_handler.emit_output(f"Execution completed successfully", "stdout")
                stream_handler.emit_completed(
                    status="completed",
                    result_summary=f"Crew execution completed: {len(crewai_tasks)} tasks executed",
                    artifacts=saved_artifacts
                )

            return {
                "status": "success",
                "result": result_data,
                "crew_id": str(crew_id),
                "artifacts": saved_artifacts
            }

        except Exception as e:
            error_msg = f"Crew execution failed: {str(e)}"

            if stream_handler:
                stream_handler.emit_error(
                    error_type=type(e).__name__,
                    message=error_msg,
                    traceback=None
                )

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_msg
            )

    def _save_execution_artifacts(
        self,
        execution_id: UUID,
        result_data: any,
        stream_handler,
        crew_name: str,
        user_id: UUID = None,
        tenant_id: UUID = None
    ) -> list:
        """
        Save execution artifacts (JSON result, logs, markdown summary).

        Args:
            execution_id: Execution UUID
            result_data: Execution result data
            stream_handler: StreamHandler with collected logs
            crew_name: Name of the crew
            user_id: User UUID
            tenant_id: Tenant UUID

        Returns:
            List of artifact metadata dicts
        """
        import json
        import os
        from pathlib import Path
        from ..services.artifact_service import ArtifactService
        from ..models.execution_artifact import ArtifactType

        artifacts = []

        try:
            # Create artifacts directory if it doesn't exist
            artifacts_dir = Path("/app/artifacts") if os.path.exists("/app") else Path("./artifacts")
            artifacts_dir.mkdir(parents=True, exist_ok=True)

            execution_dir = artifacts_dir / str(execution_id)
            execution_dir.mkdir(parents=True, exist_ok=True)

            artifact_service = ArtifactService(self.db)

            # 1. Save result as JSON
            result_file = execution_dir / "result.json"
            with open(result_file, "w") as f:
                json.dump(result_data, f, indent=2, default=str)

            result_artifact = artifact_service.create_artifact_record(
                execution_id=execution_id,
                tenant_id=tenant_id,
                file_name="result.json",
                file_size=os.path.getsize(result_file),
                file_path=str(result_file),
                artifact_type=ArtifactType.OUTPUT_FILE,
                mime_type="application/json"
            )
            artifacts.append({"id": str(result_artifact.id), "name": "result.json", "type": "json"})

            # 2. Save logs as text file
            logs_content = stream_handler.get_all_logs()
            logs_file = execution_dir / "execution.log"
            with open(logs_file, "w") as f:
                f.write(logs_content)

            logs_artifact = artifact_service.create_artifact_record(
                execution_id=execution_id,
                tenant_id=tenant_id,
                file_name="execution.log",
                file_size=os.path.getsize(logs_file),
                file_path=str(logs_file),
                artifact_type=ArtifactType.LOG_FILE,
                mime_type="text/plain"
            )
            artifacts.append({"id": str(logs_artifact.id), "name": "execution.log", "type": "log"})

            # 3. Save summary as markdown
            summary_content = self._generate_summary_markdown(
                execution_id, crew_name, result_data, logs_content
            )
            summary_file = execution_dir / "summary.md"
            with open(summary_file, "w") as f:
                f.write(summary_content)

            summary_artifact = artifact_service.create_artifact_record(
                execution_id=execution_id,
                tenant_id=tenant_id,
                file_name="summary.md",
                file_size=os.path.getsize(summary_file),
                file_path=str(summary_file),
                artifact_type=ArtifactType.OUTPUT_FILE,
                mime_type="text/markdown"
            )
            artifacts.append({"id": str(summary_artifact.id), "name": "summary.md", "type": "markdown"})

        except Exception as e:
            # Log error but don't fail execution
            print(f"Failed to save artifacts: {e}")

        return artifacts

    def _generate_summary_markdown(
        self,
        execution_id: UUID,
        crew_name: str,
        result_data: any,
        logs: str
    ) -> str:
        """Generate markdown summary of execution."""
        import json
        from datetime import datetime

        summary = f"""# Execution Summary

## Metadata
- **Execution ID**: `{execution_id}`
- **Crew**: {crew_name}
- **Completed**: {datetime.utcnow().isoformat()}

## Result

```json
{json.dumps(result_data, indent=2, default=str)}
```

## Execution Logs

```
{logs}
```

---
*Generated by CrewAI Platform*
"""
        return summary
