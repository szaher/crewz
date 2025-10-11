"""Execution API endpoints."""

import json
import asyncio
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import redis

from ...db.postgres import get_db
from ...schemas.executions import ExecutionResponse
from ...services.execution_service import ExecutionService
from ...api.middleware.auth import require_auth, get_optional_user
from ...utils.jwt import verify_token

router = APIRouter()


@router.get("", response_model=dict)
async def list_executions(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    List all executions for the current tenant.

    Returns a list of execution records with pagination.
    """
    from ...models.execution import Execution

    executions = (
        db.query(Execution)
        .offset(skip)
        .limit(limit)
        .all()
    )

    results = []
    for e in executions:
        # Normalize enums to values
        status_val = getattr(e.status, "value", e.status if e.status is not None else "unknown")
        type_val = getattr(e.execution_type, "value", e.execution_type if e.execution_type is not None else None)

        # Best-effort entity name
        entity_name = None
        try:
            if type_val == "flow" and getattr(e, "flow", None):
                entity_name = getattr(e.flow, "name", None)
        except Exception:
            entity_name = None

        results.append(
            {
                "id": e.id,
                "execution_type": type_val,
                "status": status_val,
                # Related ids
                "flow_id": getattr(e, "flow_id", None),
                "crew_id": getattr(e, "crew_id", None),
                "agent_id": getattr(e, "agent_id", None),
                "tool_id": getattr(e, "tool_id", None),
                "task_id": getattr(e, "task_id", None),
                # Entity name if available
                "entity_name": entity_name,
                # Timestamps and metrics (optional)
                "created_at": e.created_at.isoformat() if getattr(e, "created_at", None) else None,
                "updated_at": e.updated_at.isoformat() if getattr(e, "updated_at", None) else None,
                "started_at": e.started_at.isoformat() if getattr(e, "started_at", None) else None,
                "completed_at": e.completed_at.isoformat() if getattr(e, "completed_at", None) else None,
                "execution_time_ms": getattr(e, "execution_time_ms", None),
            }
        )
    return {"executions": results, "total": len(results), "skip": skip, "limit": limit}


@router.get("/{execution_id}", response_model=ExecutionResponse)
async def get_execution(
    execution_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Get execution status and results.

    Returns current execution state, input/output data, and any errors.
    """
    # Initialize services with proper dependencies
    from ...services.flow_service import FlowService
    from ...crewai.flow_executor import FlowExecutor
    from ...crewai.crew_factory import CrewFactory
    from ...crewai.agent_factory import AgentFactory
    from ...services.execution_events import ExecutionEventPublisher
    from ...services.llm_service import LLMService
    from ...services.docker_service import DockerService
    from ...crewai.tool_adapter import ToolAdapter

    flow_service = FlowService(db)

    # Initialize factories with dependencies
    llm_service = LLMService(db)
    docker_service = DockerService()
    tool_adapter = ToolAdapter(docker_service)
    agent_factory = AgentFactory(llm_service, tool_adapter)
    crew_factory = CrewFactory(agent_factory)
    event_publisher = ExecutionEventPublisher()
    flow_executor = FlowExecutor(crew_factory, agent_factory, event_publisher)

    execution_service = ExecutionService(db, flow_service, flow_executor)
    execution = await execution_service.get_execution(execution_id)
    return ExecutionResponse.from_orm(execution)


@router.get("/{execution_id}/stream")
async def stream_execution(
    execution_id: int,
    token: str | None = Query(None),
    current_user: dict | None = Depends(get_optional_user),
):
    """
    Stream execution events via Server-Sent Events (SSE).

    Subscribe to real-time execution progress updates.

    Event types:
    - execution_started
    - node_started
    - node_completed
    - node_failed
    - execution_completed
    - execution_failed
    """
    import os
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    redis_client = redis.from_url(redis_url, decode_responses=True)

    # Authenticate: allow Authorization header or token query param
    user = current_user
    if user is None and token:
        try:
            payload = verify_token(token)
            # Minimal user context for downstream checks if needed
            user = {
                "id": int(payload.get("sub")) if payload.get("sub") else None,
                "tenant_id": payload.get("tenant_id"),
                "tenant_schema": payload.get("tenant_schema"),
                "role": payload.get("role"),
            }
        except HTTPException:
            user = None
    if user is None:
        raise HTTPException(status_code=403, detail="Forbidden")

    async def event_generator():
        """Generate SSE events from Redis Pub/Sub."""
        pubsub = redis_client.pubsub()
        channel = f"executions:{execution_id}"
        pubsub.subscribe(channel)

        try:
            # Send initial connection event
            yield f"data: {json.dumps({'type': 'connected', 'execution_id': execution_id})}\n\n"

            # Listen for events
            for message in pubsub.listen():
                if message['type'] == 'message':
                    # Forward event to client
                    yield f"data: {message['data']}\n\n"

                    # Check if execution is complete
                    event = json.loads(message['data'])
                    if event['type'] in ['execution_completed', 'execution_failed', 'execution_cancelled']:
                        break

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
        finally:
            pubsub.unsubscribe(channel)
            pubsub.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.post("/{execution_id}/cancel", response_model=ExecutionResponse)
async def cancel_execution(
    execution_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Cancel a running execution.

    Only pending or running executions can be cancelled.
    """
    # Initialize services with proper dependencies
    from ...services.flow_service import FlowService
    from ...crewai.flow_executor import FlowExecutor
    from ...crewai.crew_factory import CrewFactory
    from ...crewai.agent_factory import AgentFactory
    from ...services.execution_events import ExecutionEventPublisher
    from ...services.llm_service import LLMService
    from ...services.docker_service import DockerService
    from ...crewai.tool_adapter import ToolAdapter

    flow_service = FlowService(db)

    # Initialize factories with dependencies
    llm_service = LLMService(db)
    docker_service = DockerService()
    tool_adapter = ToolAdapter(docker_service)
    agent_factory = AgentFactory(llm_service, tool_adapter)
    crew_factory = CrewFactory(agent_factory)
    event_publisher = ExecutionEventPublisher()
    flow_executor = FlowExecutor(crew_factory, agent_factory, event_publisher)

    execution_service = ExecutionService(db, flow_service, flow_executor)
    execution = await execution_service.cancel_execution(execution_id)
    return ExecutionResponse.from_orm(execution)
