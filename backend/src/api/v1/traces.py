"""
Traces API endpoints for LLM execution monitoring.

Provides trace listing, filtering, export, and real-time streaming.
"""

from typing import List, Optional
from datetime import datetime
from uuid import UUID
import csv
import io
import json

from fastapi import APIRouter, Depends, Query, HTTPException, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ...db import get_db
from ...models.trace import Trace
from ...models.user import User
from ...api.middleware.auth import get_current_user
from ...services.trace_service import TraceService
from ...services.artifact_storage import get_artifact_storage_service
from ...db.redis import get_redis_client


router = APIRouter(prefix="/traces", tags=["traces"])


# ============================================================================
# Pydantic Schemas
# ============================================================================

from pydantic import BaseModel, Field


class TraceResponse(BaseModel):
    """Single trace response schema."""
    id: UUID
    tenant_id: UUID
    execution_id: Optional[UUID]
    agent_id: Optional[UUID]
    tool_id: Optional[UUID]
    prompt: str
    response: str
    model_name: str
    provider: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: int
    cost_usd: float
    langfuse_trace_id: Optional[str]
    error_message: Optional[str]
    trace_metadata: Optional[dict]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TracesListResponse(BaseModel):
    """Paginated traces list response."""
    traces: List[TraceResponse]
    total: int
    limit: int
    offset: int
    has_more: bool


class TraceExportRequest(BaseModel):
    """Request body for trace export."""
    execution_id: Optional[UUID] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    has_error: Optional[bool] = None
    format: str = Field("json", pattern="^(json|csv)$")


class TraceExportResponse(BaseModel):
    """Response for trace export."""
    download_url: str
    expires_at: datetime
    format: str
    trace_count: int


# ============================================================================
# T035: GET /api/v1/traces - List traces with filtering
# ============================================================================

@router.get("", response_model=TracesListResponse)
async def list_traces(
    execution_id: Optional[UUID] = Query(None, description="Filter by execution ID"),
    date_from: Optional[datetime] = Query(None, description="Filter traces created after this date"),
    date_to: Optional[datetime] = Query(None, description="Filter traces created before this date"),
    provider: Optional[str] = Query(None, description="Filter by LLM provider (e.g., 'openai', 'anthropic')"),
    model: Optional[str] = Query(None, description="Filter by model name"),
    min_cost: Optional[float] = Query(None, ge=0, description="Minimum cost in USD"),
    max_cost: Optional[float] = Query(None, ge=0, description="Maximum cost in USD"),
    has_error: Optional[bool] = Query(None, description="Filter by error presence"),
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of traces to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List traces with filtering and pagination.

    Filters:
    - execution_id: Filter by specific execution
    - date_from/date_to: Date range filter
    - provider: LLM provider (openai, anthropic, etc.)
    - model: Model name
    - min_cost/max_cost: Cost range in USD
    - has_error: Show only traces with/without errors

    Pagination:
    - limit: Max results (default 50, max 1000)
    - offset: Skip N results
    """
    # Build query with tenant isolation
    query = db.query(Trace).filter(Trace.tenant_id == current_user.tenant_id)

    # Apply filters
    if execution_id:
        query = query.filter(Trace.execution_id == execution_id)

    if date_from:
        query = query.filter(Trace.created_at >= date_from)

    if date_to:
        query = query.filter(Trace.created_at <= date_to)

    if provider:
        query = query.filter(Trace.provider.ilike(f"%{provider}%"))

    if model:
        query = query.filter(Trace.model_name.ilike(f"%{model}%"))

    if min_cost is not None:
        query = query.filter(Trace.cost_usd >= min_cost)

    if max_cost is not None:
        query = query.filter(Trace.cost_usd <= max_cost)

    if has_error is not None:
        if has_error:
            query = query.filter(Trace.error_message.isnot(None))
        else:
            query = query.filter(Trace.error_message.is_(None))

    # Get total count
    total = query.count()

    # Apply pagination and ordering
    traces = query.order_by(Trace.created_at.desc()).limit(limit).offset(offset).all()

    return TracesListResponse(
        traces=[TraceResponse.from_orm(t) for t in traces],
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + len(traces)) < total
    )


# ============================================================================
# T036: GET /api/v1/traces/{trace_id} - Get single trace
# ============================================================================

@router.get("/{trace_id}", response_model=TraceResponse)
async def get_trace(
    trace_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a single trace by ID.

    Returns full trace details including prompt, response, tokens, cost, and metadata.
    """
    trace = db.query(Trace).filter(
        and_(
            Trace.id == trace_id,
            Trace.tenant_id == current_user.tenant_id
        )
    ).first()

    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")

    return TraceResponse.from_orm(trace)


# ============================================================================
# T037: POST /api/v1/traces/export - Export traces to JSON/CSV
# ============================================================================

@router.post("/export", response_model=TraceExportResponse)
async def export_traces(
    request: TraceExportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Export traces to JSON or CSV format.

    Generates a file with filtered traces and returns a pre-signed URL for download.
    The URL expires after 1 hour.

    Filters:
    - execution_id: Export traces for specific execution
    - date_from/date_to: Date range
    - provider: LLM provider filter
    - model: Model name filter
    - has_error: Include only errored traces

    Format:
    - json: Pretty-printed JSON array
    - csv: CSV with headers
    """
    # Build query
    query = db.query(Trace).filter(Trace.tenant_id == current_user.tenant_id)

    if request.execution_id:
        query = query.filter(Trace.execution_id == request.execution_id)

    if request.date_from:
        query = query.filter(Trace.created_at >= request.date_from)

    if request.date_to:
        query = query.filter(Trace.created_at <= request.date_to)

    if request.provider:
        query = query.filter(Trace.provider.ilike(f"%{request.provider}%"))

    if request.model:
        query = query.filter(Trace.model_name.ilike(f"%{request.model}%"))

    if request.has_error is not None:
        if request.has_error:
            query = query.filter(Trace.error_message.isnot(None))
        else:
            query = query.filter(Trace.error_message.is_(None))

    # Get traces
    traces = query.order_by(Trace.created_at.asc()).all()

    if not traces:
        raise HTTPException(status_code=404, detail="No traces found matching filters")

    # Generate export file
    storage_service = get_artifact_storage_service()

    if request.format == "json":
        # Generate JSON export
        traces_data = [
            {
                "id": str(t.id),
                "execution_id": str(t.execution_id) if t.execution_id else None,
                "agent_id": str(t.agent_id) if t.agent_id else None,
                "tool_id": str(t.tool_id) if t.tool_id else None,
                "model": t.model_name,
                "provider": t.provider,
                "prompt": t.prompt,
                "response": t.response,
                "prompt_tokens": t.prompt_tokens,
                "completion_tokens": t.completion_tokens,
                "total_tokens": t.total_tokens,
                "latency_ms": t.latency_ms,
                "cost_usd": float(t.cost_usd),
                "error_message": t.error_message,
                "langfuse_trace_id": t.langfuse_trace_id,
                "metadata": t.trace_metadata,
                "created_at": t.created_at.isoformat(),
            }
            for t in traces
        ]

        content = json.dumps(traces_data, indent=2)
        file_content = io.BytesIO(content.encode("utf-8"))
        filename = f"traces_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        mime_type = "application/json"

    else:  # CSV
        # Generate CSV export
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow([
            "id", "execution_id", "agent_id", "tool_id", "model", "provider",
            "prompt_tokens", "completion_tokens", "total_tokens",
            "latency_ms", "cost_usd", "error_message", "created_at"
        ])

        # Write rows
        for t in traces:
            writer.writerow([
                str(t.id),
                str(t.execution_id) if t.execution_id else "",
                str(t.agent_id) if t.agent_id else "",
                str(t.tool_id) if t.tool_id else "",
                t.model_name,
                t.provider,
                t.prompt_tokens,
                t.completion_tokens,
                t.total_tokens,
                t.latency_ms,
                float(t.cost_usd),
                t.error_message or "",
                t.created_at.isoformat(),
            ])

        file_content = io.BytesIO(output.getvalue().encode("utf-8"))
        filename = f"traces_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        mime_type = "text/csv"

    # Upload to storage
    file_content.seek(0)
    artifact = await storage_service.upload_file(
        db=db,
        tenant_id=current_user.tenant_id,
        execution_id=request.execution_id or UUID("00000000-0000-0000-0000-000000000000"),  # Use null UUID for non-execution exports
        version=1,
        file=file_content,
        file_name=filename,
        mime_type=mime_type
    )

    # Generate download URL
    download_url = await storage_service.download_file(db, artifact.id)

    # Calculate expiration (1 hour from now)
    from datetime import timedelta
    expires_at = datetime.utcnow() + timedelta(hours=1)

    return TraceExportResponse(
        download_url=download_url,
        expires_at=expires_at,
        format=request.format,
        trace_count=len(traces)
    )


# ============================================================================
# T038: GET /api/v1/executions/{execution_id}/traces/stream - SSE streaming
# ============================================================================

@router.get("/stream/{execution_id}")
async def stream_traces(
    execution_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Stream traces in real-time using Server-Sent Events (SSE).

    Connects to Redis pub/sub channel for live trace updates during execution.

    Events:
    - connected: Initial connection established
    - trace_started: New trace started
    - trace_completed: Trace finished successfully
    - trace_failed: Trace failed with error
    - execution_completed: Execution finished
    """
    redis = get_redis_client()

    async def event_generator():
        """Generate SSE events from Redis pub/sub."""
        # Send initial connection event
        yield f"event: connected\ndata: {json.dumps({'execution_id': str(execution_id), 'timestamp': datetime.utcnow().isoformat()})}\n\n"

        # Subscribe to execution trace channel
        channel_name = f"traces:{execution_id}"
        pubsub = redis.pubsub()
        pubsub.subscribe(channel_name)

        try:
            # Listen for messages
            for message in pubsub.listen():
                if message["type"] == "message":
                    data = json.loads(message["data"])
                    event_type = data.get("event_type", "trace_update")

                    # Send SSE event
                    yield f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

                    # Stop if execution completed
                    if event_type == "execution_completed":
                        break

        except Exception as e:
            # Send error event
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

        finally:
            pubsub.unsubscribe(channel_name)
            pubsub.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )
