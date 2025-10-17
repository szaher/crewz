"""Execution API endpoints."""

import json
import asyncio
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import redis.asyncio as aioredis

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
    from ...models.execution_queue import ExecutionQueue, ExecutionStatus
    from ...models.execution_metrics import ExecutionMetrics
    from sqlalchemy import func

    # Use current user's tenant if not admin
    target_tenant_id = tenant_id if current_user.get("role") == "super_admin" else current_user.get("tenant_id")

    # Parse timeframe
    timeframe_minutes = {
        "1m": 1,
        "5m": 5,
        "15m": 15,
        "1h": 60,
        "24h": 1440
    }[timeframe]

    since = datetime.utcnow() - timedelta(minutes=timeframe_minutes)

    # Query queue depth
    queue_query = db.query(ExecutionQueue).filter(
        ExecutionQueue.tenant_id == target_tenant_id,
        ExecutionQueue.status.in_([ExecutionStatus.PENDING, ExecutionStatus.RUNNING])
    )

    queue_depth = queue_query.count()
    pending_count = queue_query.filter(ExecutionQueue.status == ExecutionStatus.PENDING).count()
    running_count = queue_query.filter(ExecutionQueue.status == ExecutionStatus.RUNNING).count()

    # Query completed/failed in timeframe
    completed_query = db.query(ExecutionQueue).filter(
        ExecutionQueue.tenant_id == target_tenant_id,
        ExecutionQueue.completed_at >= since
    )

    completed_last_minute = completed_query.filter(ExecutionQueue.status == ExecutionStatus.COMPLETED).count()
    failed_last_minute = completed_query.filter(ExecutionQueue.status == ExecutionStatus.FAILED).count()

    # Calculate processing rate (tasks/second)
    total_processed = completed_last_minute + failed_last_minute
    processing_rate = total_processed / (timeframe_minutes * 60) if timeframe_minutes > 0 else 0

    # Calculate duration statistics
    duration_stats = db.query(
        func.avg(ExecutionQueue.duration_ms).label("avg"),
        func.percentile_cont(0.95).within_group(ExecutionQueue.duration_ms).label("p95"),
        func.percentile_cont(0.99).within_group(ExecutionQueue.duration_ms).label("p99")
    ).filter(
        ExecutionQueue.tenant_id == target_tenant_id,
        ExecutionQueue.completed_at >= since,
        ExecutionQueue.duration_ms.isnot(None)
    ).first()

    avg_duration_ms = int(duration_stats.avg or 0)
    p95_duration_ms = int(duration_stats.p95 or 0)
    p99_duration_ms = int(duration_stats.p99 or 0)

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
        "p95_duration_ms": p95_duration_ms,
        "p99_duration_ms": p99_duration_ms,
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
