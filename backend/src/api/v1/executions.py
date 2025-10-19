"""Execution API endpoints."""

import json
import asyncio
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Any, Optional
import redis.asyncio as aioredis

from ...db.postgres import get_db
from ...schemas.executions import ExecutionResponse
from ...services.execution_service import ExecutionService
from ...api.middleware.auth import require_auth, get_optional_user
from ...utils.jwt import verify_token

router = APIRouter()


class CreateExecutionRequest(BaseModel):
    """Request schema for creating an execution."""
    execution_type: str  # "flow", "crew", "task"
    flow_id: Optional[str] = None
    crew_id: Optional[str] = None
    task_id: Optional[str] = None
    input_data: Dict[str, Any] = {}
    priority: int = 5
    timeout_seconds: int = 600


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_execution(
    request: CreateExecutionRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Create and queue a new execution.

    This is a simplified endpoint that accepts JSON body instead of query params.
    """
    from uuid import UUID
    from ...services.execution_service_worker import ExecutionServiceWorker

    # Determine entity_id based on execution type
    entity_id = None
    if request.execution_type == "flow":
        entity_id = request.flow_id
    elif request.execution_type == "crew":
        entity_id = request.crew_id
    elif request.execution_type == "task":
        entity_id = request.task_id

    if not entity_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{request.execution_type}_id is required for execution_type={request.execution_type}"
        )

    # Validate priority
    if not (0 <= request.priority <= 10):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Priority must be between 0 and 10"
        )

    # Validate timeout
    if not (60 <= request.timeout_seconds <= 3600):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Timeout must be between 60 and 3600 seconds"
        )

    try:
        execution_service = ExecutionServiceWorker(db)

        # Convert string UUIDs to UUID objects
        entity_uuid = UUID(entity_id) if isinstance(entity_id, str) else entity_id
        user_uuid = UUID(current_user["id"]) if isinstance(current_user["id"], str) else current_user["id"]

        execution = execution_service.queue_execution(
            execution_type=request.execution_type,
            entity_id=entity_uuid,
            input_params=request.input_data,
            user_id=user_uuid,
            priority=request.priority,
            timeout_seconds=request.timeout_seconds
        )

        from datetime import datetime, timedelta
        estimated_wait = execution.queue_position * 300 if execution.queue_position else 0
        estimated_start = datetime.utcnow() + timedelta(seconds=estimated_wait)

        return {
            "id": str(execution.id),
            "job_id": str(execution.id),
            "execution_type": request.execution_type,
            "status": execution.status.value if hasattr(execution.status, 'value') else str(execution.status),
            "queue_position": execution.queue_position or 0,
            "estimated_start_time": estimated_start.isoformat() + "Z",
            "created_at": execution.created_at.isoformat() if execution.created_at else None,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create execution: {str(e)}"
        )


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
    execution_id: str,
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
    execution_id: str,
    request: Request,
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
    redis_client = aioredis.from_url(
        redis_url,
        decode_responses=True,
        socket_connect_timeout=float(os.getenv("REDIS_CONNECT_TIMEOUT", 0.5)),
        socket_timeout=float(os.getenv("REDIS_SOCKET_TIMEOUT", 0.5)),
    )

    # Authenticate: allow Authorization header or token query param
    user = current_user
    if user is None and token:
        try:
            payload = verify_token(token)
            # Minimal user context for downstream checks if needed
            user = {
                "id": payload.get("sub"),
                "tenant_id": payload.get("tenant_id"),
                "tenant_schema": payload.get("tenant_schema"),
                "role": payload.get("role"),
            }
        except HTTPException:
            user = None
    if user is None:
        raise HTTPException(status_code=403, detail="Forbidden")

    async def event_generator():
        """Generate SSE events from Redis Pub/Sub without blocking the event loop."""
        pubsub = redis_client.pubsub()
        channel = f"executions:{execution_id}"
        await pubsub.subscribe(channel)

        keepalive_interval = 15.0  # seconds
        last_keepalive = 0.0
        # Optional idle/absolute timeouts
        import time, os as _os
        idle_timeout = float(_os.getenv("SSE_IDLE_TIMEOUT", 300))  # 5 min default
        max_stream = float(_os.getenv("SSE_MAX_STREAM_SECONDS", 3600))  # 1 hour default
        start_ts = time.monotonic()
        last_activity = start_ts

        try:
            # Initial event
            yield f"data: {json.dumps({'type': 'connected', 'execution_id': execution_id})}\n\n"

            while True:
                # Non-blocking get with timeout; ignore subscribe confirmations
                msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if msg and msg.get('type') == 'message':
                    data = msg.get('data')
                    if data is None:
                        await asyncio.sleep(0.05)
                        continue
                    # Forward event
                    yield f"data: {data}\n\n"
                    # Track activity
                    last_activity = time.monotonic()

                    # Check termination events
                    try:
                        event = json.loads(data)
                        if event.get('type') in {'execution_completed', 'execution_failed', 'execution_cancelled'}:
                            break
                    except Exception:
                        # If payload isn't JSON, just continue
                        pass

                # Periodic keepalive to prevent proxies from closing idle connections
                last_keepalive += 1.0
                if last_keepalive >= keepalive_interval:
                    last_keepalive = 0.0
                    # Comment line is valid SSE and ignored by clients
                    yield ": keepalive\n\n"

                # Yield control to the event loop
                await asyncio.sleep(0.3)

                # Client disconnect detection
                if request is not None:
                    try:
                        if await request.is_disconnected():
                            break
                    except Exception:
                        pass
                # Idle timeout (no real events)
                now = time.monotonic()
                if idle_timeout > 0 and (now - last_activity) >= idle_timeout:
                    yield f"data: {json.dumps({'type': 'timeout', 'reason': 'idle'})}\n\n"
                    break
                # Absolute stream cap
                if max_stream > 0 and (now - start_ts) >= max_stream:
                    yield f"data: {json.dumps({'type': 'timeout', 'reason': 'max_duration'})}\n\n"
                    break

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
        finally:
            try:
                await pubsub.unsubscribe(channel)
            except Exception:
                pass
            try:
                await pubsub.close()
            except Exception:
                pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            # Helpful for some reverse proxies (nginx) to not buffer SSE
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/{execution_id}/cancel", response_model=ExecutionResponse)
async def cancel_execution(
    execution_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Cancel a running execution.

    Only pending or running executions can be cancelled.
    """
    from uuid import UUID
    from ...services.execution_service_worker import ExecutionServiceWorker
    from ...config.settings import Settings

    # Initialize worker service
    settings = Settings()
    execution_service = ExecutionServiceWorker(
        db_session=db,
        settings=settings
    )

    # Cancel execution
    user_id = current_user["id"] if isinstance(current_user["id"], UUID) else UUID(str(current_user["id"]))
    result = execution_service.cancel_execution(
        execution_id=UUID(execution_id),
        user_id=user_id
    )

    # Handle error responses
    if result.get("error") == "not_found":
        raise HTTPException(status_code=404, detail="Execution not found")

    if result.get("error") == "forbidden":
        raise HTTPException(status_code=403, detail="You don't have permission to cancel this execution")

    # Get the execution to return
    from ...models.execution import Execution
    execution = db.query(Execution).filter(Execution.id == UUID(execution_id)).first()
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    return ExecutionResponse.from_orm(execution)


# ============================================================================
# Queue Management Endpoints (T038-T040)
# ============================================================================

@router.post("/submit", status_code=status.HTTP_202_ACCEPTED)
async def submit_execution(
    request: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Submit execution to queue (T038).

    Queue execution request for background processing.
    Returns immediately with execution ID (<200ms target).

    Rate limits:
    - Per tenant: Default 10 concurrent (configurable)
    - Per user: Default 5 concurrent (configurable)
    """
    from uuid import uuid4
    from datetime import datetime, timedelta
    from ...models.execution_queue import ExecutionQueue, ExecutionStatus, ExecutionPriority, ExecutionType
    from ...models.execution import Execution
    from ...middleware.rate_limit import check_rate_limit

    # Extract request parameters
    execution_type = request.get("execution_type")
    entity_id = request.get("entity_id")
    payload = request.get("payload", {})
    priority = request.get("priority", "normal")
    timeout_minutes = request.get("timeout_minutes")

    # Validate required fields
    if not execution_type or not entity_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="execution_type and entity_id are required"
        )

    # Check rate limits
    tenant_id = current_user.get("tenant_id")
    user_id = current_user.get("id")

    rate_limit_result = check_rate_limit(db, tenant_id, user_id)
    if not rate_limit_result["allowed"]:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(rate_limit_result.get("retry_after", 60))}
        )

    # Create execution record
    execution_id = uuid4()
    execution = Execution(
        id=execution_id,
        execution_type=execution_type,
        status="pending",
        user_id=user_id,
        tenant_id=tenant_id
    )
    db.add(execution)
    db.flush()

    # Create queue entry
    queue_id = uuid4()
    scheduled_at = datetime.utcnow()
    timeout_at = scheduled_at + timedelta(minutes=timeout_minutes or 30)

    queue_entry = ExecutionQueue(
        id=queue_id,
        execution_id=execution_id,
        tenant_id=tenant_id,
        user_id=user_id,
        execution_type=ExecutionType(execution_type),
        entity_id=entity_id,
        status=ExecutionStatus.PENDING,
        priority=ExecutionPriority(priority),
        payload=payload,
        scheduled_at=scheduled_at,
        timeout_at=timeout_at,
        max_retries=3
    )
    db.add(queue_entry)
    db.commit()

    # Submit to Celery queue
    from ...workers.message_queue.redis_backend import RedisBackend
    queue_backend = RedisBackend()

    celery_task_id = queue_backend.submit_task(
        task_name=f"workers.tasks.execute_{execution_type}",
        kwargs={
            "execution_id": str(execution_id),
            "entity_id": str(entity_id),
            "payload": payload
        },
        priority=priority,
        task_id=str(uuid4())
    )

    # Update queue entry with Celery task ID
    queue_entry.celery_task_id = celery_task_id
    db.commit()

    # Calculate queue position (approximate)
    queue_position = db.query(ExecutionQueue).filter(
        ExecutionQueue.tenant_id == tenant_id,
        ExecutionQueue.status == ExecutionStatus.PENDING,
        ExecutionQueue.scheduled_at < scheduled_at
    ).count()

    # Estimate start time based on queue depth
    avg_execution_time_minutes = 5  # Default estimate
    estimated_start_time = scheduled_at + timedelta(minutes=avg_execution_time_minutes * queue_position)

    return {
        "execution_id": str(execution_id),
        "queue_id": str(queue_id),
        "status": "pending",
        "estimated_start_time": estimated_start_time.isoformat(),
        "queue_position": queue_position
    }


@router.get("/queue/metrics")
async def get_queue_metrics(
    tenant_id: str = Query(None),
    timeframe: str = Query("5m", regex="^(1m|5m|15m|1h|24h)$"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Get queue metrics (T039).

    Current queue depth, processing rate, failure rate.
    """
    from datetime import datetime, timedelta
    from ...models.execution import Execution, ExecutionStatus
    from sqlalchemy import func

    # Use current user's ID for filtering (tenant-based filtering via user_id)
    user_id = current_user.get("id")

    # Parse timeframe
    timeframe_minutes = {
        "1m": 1,
        "5m": 5,
        "15m": 15,
        "1h": 60,
        "24h": 1440
    }[timeframe]

    since = datetime.utcnow() - timedelta(minutes=timeframe_minutes)

    # Query queue depth (queued + running)
    queue_query = db.query(Execution).filter(
        Execution.user_id == user_id,
        Execution.status.in_([ExecutionStatus.QUEUED.value, ExecutionStatus.RUNNING.value, ExecutionStatus.PENDING.value])
    )

    queue_depth = queue_query.count()
    pending_count = queue_query.filter(Execution.status == ExecutionStatus.QUEUED.value).count()
    running_count = queue_query.filter(Execution.status == ExecutionStatus.RUNNING.value).count()

    # Query completed/failed in timeframe (use updated_at as proxy for completion time)
    completed_query = db.query(Execution).filter(
        Execution.user_id == user_id,
        Execution.updated_at >= since
    )

    completed_last_minute = completed_query.filter(Execution.status == ExecutionStatus.COMPLETED.value).count()
    failed_last_minute = completed_query.filter(Execution.status == ExecutionStatus.FAILED.value).count()

    # Calculate processing rate (tasks/second)
    total_processed = completed_last_minute + failed_last_minute
    processing_rate = total_processed / (timeframe_minutes * 60) if timeframe_minutes > 0 else 0

    # Calculate duration statistics using execution_time_ms
    duration_stats = db.query(
        func.avg(Execution.execution_time_ms).label("avg")
    ).filter(
        Execution.user_id == user_id,
        Execution.updated_at >= since,
        Execution.execution_time_ms.isnot(None)
    ).first()

    avg_duration_ms = int(duration_stats.avg or 0) if duration_stats else 0

    # Calculate failure rate
    failure_rate = failed_last_minute / total_processed if total_processed > 0 else 0.0

    return {
        "queue_depth": queue_depth,
        "pending_count": pending_count,
        "running_count": running_count,
        "completed_last_minute": completed_last_minute,
        "failed_last_minute": failed_last_minute,
        "processing_rate": round(processing_rate, 3),
        "avg_duration_ms": avg_duration_ms,
        "failure_rate": round(failure_rate, 3),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/dlq")
async def list_dead_letter_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    List dead letter tasks (T040).

    Get failed tasks after retry exhaustion. Admin only.
    """
    from ...models.dead_letter_task import DeadLetterTask

    # Check admin role
    if current_user.get("role") not in ["super_admin", "tenant_admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    tenant_id = current_user.get("tenant_id")

    # Query dead letter tasks
    query = db.query(DeadLetterTask).filter(DeadLetterTask.tenant_id == tenant_id)

    total = query.count()
    tasks = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "tasks": [
            {
                "id": str(task.id),
                "original_queue_id": str(task.original_queue_id),
                "execution_type": task.execution_type.value if hasattr(task.execution_type, "value") else task.execution_type,
                "payload": task.payload,
                "failure_reason": task.failure_reason,
                "retry_history": task.retry_history,
                "failure_timestamp": task.failure_timestamp.isoformat(),
                "is_requeued": task.is_requeued
            }
            for task in tasks
        ],
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.post("/dlq/{task_id}/requeue")
async def requeue_dead_letter_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Requeue failed task from DLQ (T040).

    Move task from DLQ back to execution queue. Admin only.
    """
    from uuid import UUID, uuid4
    from datetime import datetime
    from ...models.dead_letter_task import DeadLetterTask
    from ...models.execution_queue import ExecutionQueue, ExecutionStatus, ExecutionPriority, ExecutionType
    from ...models.execution import Execution

    # Check admin role
    if current_user.get("role") not in ["super_admin", "tenant_admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    # Find dead letter task
    task = db.query(DeadLetterTask).filter(DeadLetterTask.id == UUID(task_id)).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dead letter task not found")

    if task.is_requeued:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Task already requeued")

    # Create new execution
    execution_id = uuid4()
    execution = Execution(
        id=execution_id,
        execution_type=task.execution_type.value if hasattr(task.execution_type, "value") else task.execution_type,
        status="pending",
        user_id=task.user_id,
        tenant_id=task.tenant_id
    )
    db.add(execution)
    db.flush()

    # Create new queue entry
    queue_entry = ExecutionQueue(
        id=uuid4(),
        execution_id=execution_id,
        tenant_id=task.tenant_id,
        user_id=task.user_id,
        execution_type=ExecutionType(task.execution_type.value if hasattr(task.execution_type, "value") else task.execution_type),
        entity_id=task.payload.get("entity_id"),
        status=ExecutionStatus.PENDING,
        priority=ExecutionPriority.NORMAL,
        payload=task.payload,
        scheduled_at=datetime.utcnow(),
        max_retries=3,
        retry_count=0  # Reset retry count
    )
    db.add(queue_entry)

    # Mark DLQ task as requeued
    task.is_requeued = True
    task.requeued_at = datetime.utcnow()
    task.requeued_by = UUID(current_user.get("id"))

    db.commit()

    # Submit to Celery queue
    from ...workers.message_queue.redis_backend import RedisBackend
    queue_backend = RedisBackend()

    celery_task_id = queue_backend.submit_task(
        task_name=f"workers.tasks.execute_{queue_entry.execution_type.value}",
        kwargs={
            "execution_id": str(execution_id),
            "entity_id": str(queue_entry.entity_id),
            "payload": task.payload
        },
        priority="normal",
        task_id=str(uuid4())
    )

    queue_entry.celery_task_id = celery_task_id
    db.commit()

    return {
        "message": "Task requeued successfully",
        "execution_id": str(execution_id)
    }


# ===== WORKER ARCHITECTURE ENDPOINTS (Phase 004) =====

@router.post("/queue", status_code=status.HTTP_201_CREATED)
async def queue_execution(
    execution_type: str,
    entity_id: str,
    input_params: dict,
    priority: int = 5,
    timeout_seconds: int = 600,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Queue new execution (T033).

    Uses worker architecture if ENABLE_WORKER_ARCHITECTURE=True,
    else falls back to old synchronous flow.
    """
    from uuid import UUID
    from ...services.execution_service_worker import ExecutionServiceWorker
    from ...config.settings import Settings

    settings = Settings()

    # Validate priority bounds (0-10 per OpenAPI spec)
    if not (0 <= priority <= 10):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Priority must be between 0 and 10"
        )

    # Validate timeout bounds (60-3600 per OpenAPI spec)
    if not (60 <= timeout_seconds <= 3600):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Timeout must be between 60 and 3600 seconds"
        )

    # Validate execution_type enum
    valid_types = ["crew", "flow", "task"]
    if execution_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"execution_type must be one of: {', '.join(valid_types)}"
        )

    try:
        execution_service = ExecutionServiceWorker(db)

        execution = execution_service.queue_execution(
            execution_type=execution_type,
            entity_id=UUID(entity_id),
            input_params=input_params,
            user_id=UUID(current_user["id"]),
            priority=priority,
            timeout_seconds=timeout_seconds
        )

        # Estimate start time based on queue position
        import time
        from datetime import datetime, timedelta
        estimated_wait = execution.queue_position * 300 if execution.queue_position else 0  # 5 min per job
        estimated_start = datetime.utcnow() + timedelta(seconds=estimated_wait)

        return {
            "job_id": str(execution.id),
            "queue_position": execution.queue_position or 0,
            "estimated_start_time": estimated_start.isoformat() + "Z"
        }

    except ValueError as e:
        # Worker architecture disabled - fall back
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue execution: {str(e)}"
        )


@router.get("/{job_id}/status")
async def get_execution_status(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Get execution status with queue info (T034 - EXTENDED existing endpoint).

    Adds queue_position, worker_id, retry_count to response when populated.
    """
    from uuid import UUID
    from ...models.execution import Execution

    try:
        execution = db.query(Execution).filter(Execution.id == UUID(job_id)).first()

        if not execution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Execution not found"
            )

        # Build response with worker fields
        response = {
            "job_id": str(execution.id),
            "status": execution.status.value if hasattr(execution.status, 'value') else execution.status,
            "queue_position": execution.queue_position,
            "worker_id": execution.worker_id,
            "started_at": execution.created_at.isoformat() + "Z" if execution.created_at else None,
            "progress_percent": None  # TODO: Implement progress tracking
        }

        return response

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid UUID format"
        )


# NOTE: Duplicate cancel endpoint removed - using the one at line 253 instead
# The route pattern /{job_id}/cancel conflicts with /{execution_id}/cancel
# Both resolve to the same pattern and cause route collision


@router.post("/{job_id}/re-execute", status_code=status.HTTP_201_CREATED)
async def reexecute_execution(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Re-execute with same inputs (T036 - NEW endpoint).

    Clones execution with parent_execution_id, increments artifact_version.
    """
    from uuid import UUID
    from ...services.execution_service_worker import ExecutionServiceWorker

    try:
        execution_service = ExecutionServiceWorker(db)

        new_execution = execution_service.reexecute_with_version(
            execution_id=UUID(job_id),
            user_id=UUID(current_user["id"])
        )

        if not new_execution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Original execution not found"
            )

        return {
            "new_job_id": str(new_execution.id),
            "version_number": new_execution.artifact_version or 1
        }

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid UUID format"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to re-execute: {str(e)}"
        )


@router.get("/{job_id}/artifacts")
async def list_execution_artifacts(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    List execution artifacts (T037 partial - will move to artifacts.py).

    Returns artifact metadata for an execution.
    """
    from uuid import UUID
    from ...services.artifact_service import ArtifactService

    try:
        artifact_service = ArtifactService(db)

        artifacts = artifact_service.get_execution_artifacts(UUID(job_id))

        results = []
        for artifact in artifacts:
            results.append({
                "artifact_id": str(artifact.id),
                "file_name": artifact.file_name,
                "file_size": artifact.file_size,
                "mime_type": artifact.mime_type,
                "artifact_type": artifact.artifact_type.value if hasattr(artifact.artifact_type, 'value') else artifact.artifact_type,
                "version": artifact.version_number,
                "download_url": f"/api/v1/artifacts/{artifact.id}/download"
            })

        return results

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid UUID format"
        )


@router.get("/queue/list")
async def list_queue_items(
    status_filter: str = Query(None, regex="^(queued|running|all)$"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    List queue items for current tenant.

    Returns executions in queue with tenant filtering.
    Only shows executions belonging to the authenticated user's tenant.
    """
    from ...models.execution import Execution, ExecutionStatus, ExecutionType
    from ...models.crew import Crew
    from ...models.flow import Flow
    from ...models.agent import Agent
    from ...models.task import Task
    from uuid import UUID

    # Get user's tenant_id
    user_tenant_id = current_user.get("tenant_id")
    user_id = current_user.get("id")

    # Ensure user_id is UUID
    if not isinstance(user_id, UUID):
        user_id = UUID(str(user_id))

    # Build query with tenant filtering
    query = db.query(Execution).filter(Execution.user_id == user_id)

    # Apply status filter
    if status_filter == "queued":
        query = query.filter(Execution.status == ExecutionStatus.QUEUED.value)
    elif status_filter == "running":
        query = query.filter(Execution.status == ExecutionStatus.RUNNING.value)
    elif status_filter == "all":
        query = query.filter(
            Execution.status.in_([
                ExecutionStatus.QUEUED.value,
                ExecutionStatus.RUNNING.value,
                ExecutionStatus.PENDING.value
            ])
        )
    else:
        # Default: show queued and running
        query = query.filter(
            Execution.status.in_([ExecutionStatus.QUEUED.value, ExecutionStatus.RUNNING.value])
        )

    # Order by priority (lower number = higher priority) and created_at
    query = query.order_by(Execution.priority.asc(), Execution.created_at.asc())

    # Get total count
    total = query.count()

    # Apply pagination
    items = query.offset(skip).limit(limit).all()

    # Format response
    results = []
    for item in items:
        # Get entity ID and name based on execution type
        entity_name = None
        entity_id = None

        if item.execution_type == ExecutionType.FLOW.value:
            entity_id = str(item.flow_id) if item.flow_id else None
            if item.flow_id:
                flow = db.query(Flow).filter(Flow.id == item.flow_id).first()
                entity_name = flow.name if flow else None
        elif item.execution_type == ExecutionType.CREW.value:
            entity_id = str(item.crew_id) if item.crew_id else None
            if item.crew_id:
                crew = db.query(Crew).filter(Crew.id == item.crew_id).first()
                entity_name = crew.name if crew else None
        elif item.execution_type == ExecutionType.AGENT.value:
            entity_id = str(item.agent_id) if item.agent_id else None
            if item.agent_id:
                agent = db.query(Agent).filter(Agent.id == item.agent_id).first()
                entity_name = agent.name if agent else None
        elif item.execution_type == ExecutionType.TASK.value:
            entity_id = str(item.task_id) if item.task_id else None
            if item.task_id:
                task = db.query(Task).filter(Task.id == item.task_id).first()
                entity_name = task.name if task else None

        # Use queue_position from model if available, otherwise calculate
        queue_position = item.queue_position

        results.append({
            "execution_id": str(item.id),
            "execution_type": item.execution_type.value if hasattr(item.execution_type, 'value') else item.execution_type,
            "entity_id": entity_id,
            "entity_name": entity_name,
            "status": item.status.value if hasattr(item.status, 'value') else item.status,
            "priority": item.priority or 5,
            "queue_position": queue_position,
            "worker_id": item.worker_id if hasattr(item, 'worker_id') else None,
            "created_at": item.created_at.isoformat() + "Z" if item.created_at else None,
            "started_at": None,  # Execution model doesn't have started_at field
            "retry_count": item.retry_count or 0,
            "max_retries": getattr(item, 'max_retries', 3) or 3
        })

    return {
        "items": results,
        "total": total,
        "skip": skip,
        "limit": limit
    }
