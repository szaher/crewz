"""Notifications API endpoints."""

import json
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import redis

from ...db.postgres import get_db
from ...api.middleware.auth import require_auth, get_optional_user
from ...utils.jwt import verify_token
from ...services.notification_service import NotificationService
from ...schemas.notifications import NotificationCreate, NotificationListResponse, NotificationOut

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
    notification_id: int,
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
    redis_client = redis.from_url(
        redis_url,
        decode_responses=True,
        socket_connect_timeout=float(os.getenv("REDIS_CONNECT_TIMEOUT", 0.5)),
        socket_timeout=float(os.getenv("REDIS_SOCKET_TIMEOUT", 0.5)),
        retry_on_timeout=False,
    )

    # Authenticate (Authorization header or token query param)
    user = current_user
    if user is None and token:
        try:
            payload = verify_token(token)
            user = {"id": int(payload.get("sub")) if payload.get("sub") else None}
        except HTTPException:
            user = None
    if user is None or not user.get("id"):
        raise HTTPException(status_code=403, detail="Forbidden")

    user_id = user["id"]

    async def event_generator():
        pubsub = redis_client.pubsub()
        channel = f"notifications:{user_id}"
        pubsub.subscribe(channel)
        try:
            # Send initial ping
            yield f"data: {json.dumps({'type': 'connected'})}\n\n"
            for message in pubsub.listen():
                if message['type'] == 'message':
                    yield f"data: {message['data']}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
        finally:
            try:
                pubsub.unsubscribe(channel)
                pubsub.close()
            except Exception:
                pass

    return StreamingResponse(event_generator(), media_type="text/event-stream")
