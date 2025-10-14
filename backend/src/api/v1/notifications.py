"""Notifications API endpoints."""

import json
import asyncio
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import redis.asyncio as aioredis
from uuid import UUID

from ...db.postgres import get_db
from ...api.middleware.auth import require_auth, get_optional_user
from ...utils.jwt import verify_token
from ...services.notification_service import NotificationService
from ...schemas.notifications import NotificationCreate, NotificationListResponse, NotificationOut
from ...websocket.connection_manager import connection_manager

router = APIRouter()


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    unread_only: bool = False,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    import os
    if os.getenv("NOTIFICATIONS_ENABLED", "0").lower() in ("0", "false"):
        return NotificationListResponse(notifications=[], unread_count=0)
    service = NotificationService(db)
    items = await service.list_notifications(current_user["id"], unread_only=unread_only, limit=limit)
    unread = await service.unread_count(current_user["id"])
    return NotificationListResponse(
        notifications=[NotificationOut.from_orm(n) for n in items],
        unread_count=unread,
    )


@router.post("/{notification_id}/read", response_model=NotificationOut)
async def mark_read(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    service = NotificationService(db)
    try:
        n = await service.mark_read(notification_id, current_user["id"])
        return NotificationOut.from_orm(n)
    except ValueError:
        raise HTTPException(status_code=404, detail="Notification not found")


@router.post("/read-all", response_model=dict)
async def mark_all_read(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    service = NotificationService(db)
    count = await service.mark_all_read(current_user["id"])
    return {"updated": count}


@router.get("/stream")
async def stream_notifications(
    request: Request,
    token: str | None = Query(None),
    current_user: dict | None = Depends(get_optional_user),
):
    """Stream notifications for the authenticated user via SSE."""
    import os
    if os.getenv("NOTIFICATIONS_ENABLED", "0").lower() in ("0", "false"):
        async def noop():
            yield "data: {\"type\": \"connected\"}\n\n"
        return StreamingResponse(noop(), media_type="text/event-stream")
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    redis_client = aioredis.from_url(
        redis_url,
        decode_responses=True,
        socket_connect_timeout=float(os.getenv("REDIS_CONNECT_TIMEOUT", 0.5)),
        socket_timeout=float(os.getenv("REDIS_SOCKET_TIMEOUT", 0.5)),
    )

    # Authenticate (Authorization header or token query param)
    user = current_user
    if user is None and token:
        try:
            payload = verify_token(token)
            user = {"id": payload.get("sub")}
        except HTTPException:
            user = None
    if user is None or not user.get("id"):
        raise HTTPException(status_code=403, detail="Forbidden")

    user_id = user["id"]

    async def event_generator():
        pubsub = redis_client.pubsub()
        channel = f"notifications:{user_id}"
        await pubsub.subscribe(channel)
        keepalive_interval = 15.0
        last_keepalive = 0.0
        import time, os as _os
        idle_timeout = float(_os.getenv("SSE_IDLE_TIMEOUT", 300))
        max_stream = float(_os.getenv("SSE_MAX_STREAM_SECONDS", 3600))
        start_ts = time.monotonic()
        last_activity = start_ts
        try:
            yield f"data: {json.dumps({'type': 'connected'})}\n\n"
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message.get('type') == 'message':
                    yield f"data: {message['data']}\n\n"
                    last_activity = time.monotonic()

                last_keepalive += 1.0
                if last_keepalive >= keepalive_interval:
                    last_keepalive = 0.0
                    yield ": keepalive\n\n"
                await asyncio.sleep(0.3)
                # Client disconnect
                if request is not None:
                    try:
                        if await request.is_disconnected():
                            break
                    except Exception:
                        pass
                # Timeouts
                now = time.monotonic()
                if idle_timeout > 0 and (now - last_activity) >= idle_timeout:
                    yield f"data: {json.dumps({'type': 'timeout', 'reason': 'idle'})}\n\n"
                    break
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
            "X-Accel-Buffering": "no",
        },
    )


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT auth token"),
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for real-time notifications.

    Usage:
        ws://localhost:8000/api/v1/notifications/ws?token=<jwt_token>

    Messages sent to client:
        - connection: Connection established
        - execution_update: Execution status changed
        - execution_failed: Execution moved to DLQ
        - ping: Heartbeat message

    Client should respond to ping messages to keep connection alive.
    """
    # Validate token and get user
    try:
        payload = verify_token(token)
        user_id = UUID(payload["sub"])

        # Get user from database (including tenant_id)
        from backend.src.models.user import User
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            await websocket.close(code=1008, reason="User not found")
            return

        tenant_id = user.tenant_id

    except Exception as e:
        await websocket.close(code=1008, reason=f"Authentication failed: {str(e)}")
        return

    # Connect to connection manager
    await connection_manager.connect(websocket, user_id, tenant_id)

    try:
        # Keep connection alive and handle incoming messages
        while True:
            # Receive messages from client (e.g., pong responses)
            data = await websocket.receive_json()

            # Handle client messages
            if data.get("type") == "pong":
                # Client responded to ping - connection is alive
                pass
            elif data.get("type") == "subscribe":
                # Client wants to subscribe to specific channels
                # Could be used for fine-grained notification filtering
                pass

    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        connection_manager.disconnect(websocket)


@router.get("/preferences")
async def get_notification_preferences(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Get notification preferences for current user.

    Returns:
        User's notification preferences (channels, types, frequency)
    """
    # In production, query from user_notification_preferences table
    # For now, return defaults
    from datetime import datetime

    return {
        "user_id": str(current_user["id"]),
        "preferences": {
            "websocket": {
                "enabled": True,
                "types": [
                    "execution_update",
                    "execution_failed",
                    "execution_completed"
                ]
            },
            "email": {
                "enabled": False,
                "types": [
                    "execution_failed",
                    "daily_summary"
                ],
                "frequency": "immediate"
            },
            "webhook": {
                "enabled": False,
                "url": None,
                "types": []
            }
        }
    }


@router.put("/preferences")
async def update_notification_preferences(
    preferences: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Update notification preferences for current user.

    Request Body:
        preferences: Dict with notification channel preferences

    Returns:
        Updated preferences
    """
    from datetime import datetime

    # In production, update user_notification_preferences table
    # For now, just validate and return

    # Validate structure
    valid_channels = ["websocket", "email", "webhook"]
    for channel in preferences.get("preferences", {}).keys():
        if channel not in valid_channels:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid channel: {channel}. Must be one of {valid_channels}"
            )

    return {
        "user_id": str(current_user["id"]),
        "preferences": preferences.get("preferences", {}),
        "updated_at": datetime.utcnow().isoformat()
    }


@router.get("/stats")
async def get_notification_stats(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Get notification statistics for current user.

    Returns:
        - Total notifications
        - Unread count
        - By type breakdown
    """
    from backend.src.models.execution_queue import ExecutionQueue, ExecutionStatus
    from datetime import datetime, timedelta

    user_id = UUID(current_user["id"])

    # Get execution counts by status
    total_executions = db.query(ExecutionQueue).filter(
        ExecutionQueue.user_id == user_id
    ).count()

    failed_count = db.query(ExecutionQueue).filter(
        ExecutionQueue.user_id == user_id,
        ExecutionQueue.status == ExecutionStatus.FAILED
    ).count()

    completed_count = db.query(ExecutionQueue).filter(
        ExecutionQueue.user_id == user_id,
        ExecutionQueue.status == ExecutionStatus.COMPLETED
    ).count()

    running_count = db.query(ExecutionQueue).filter(
        ExecutionQueue.user_id == user_id,
        ExecutionQueue.status == ExecutionStatus.RUNNING
    ).count()

    # Get recent activity (last 24 hours)
    day_ago = datetime.utcnow() - timedelta(days=1)
    recent_count = db.query(ExecutionQueue).filter(
        ExecutionQueue.user_id == user_id,
        ExecutionQueue.scheduled_at >= day_ago
    ).count()

    return {
        "user_id": str(user_id),
        "total_executions": total_executions,
        "by_status": {
            "completed": completed_count,
            "failed": failed_count,
            "running": running_count,
            "pending": total_executions - completed_count - failed_count - running_count
        },
        "recent_24h": recent_count,
        "active_connections": connection_manager.get_user_connection_count(user_id)
    }


@router.post("/test")
async def send_test_notification(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth)
):
    """
    Send a test notification to current user's WebSocket connections.

    Useful for testing WebSocket connectivity.
    """
    from datetime import datetime

    user_id = UUID(current_user["id"])

    test_message = {
        "type": "test",
        "message": "This is a test notification",
        "timestamp": datetime.utcnow().isoformat(),
        "user_id": str(user_id)
    }

    await connection_manager.send_to_user(user_id, test_message)

    return {
        "status": "sent",
        "connections": connection_manager.get_user_connection_count(user_id)
    }
