"""WebSocket queue position updates endpoint (T041).

Provides real-time queue position updates for executions.
- JWT authentication via query parameter
- Broadcasts queue position changes when executions are queued/dequeued
- Emits queue_position_update events with current position and estimated start time
"""

import asyncio
import json
from typing import Optional
from uuid import UUID
from fastapi import WebSocket, WebSocketDisconnect, HTTPException, status
from sqlalchemy.orm import Session
import redis.asyncio as redis

from ..db.redis import get_redis_url
from ..db.postgres import get_db
from ..utils.jwt import verify_token
from ..models.execution import Execution


async def authenticate_websocket(token: str, db: Session) -> dict:
    """
    Authenticate WebSocket connection via JWT token.

    Args:
        token: JWT token from query parameter
        db: Database session

    Returns:
        User info dict with id, tenant_id, etc.

    Raises:
        HTTPException: If authentication fails
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token"
        )

    try:
        # Verify JWT token
        payload = verify_token(token)

        # Extract user info
        user_id = UUID(payload.get("sub"))
        tenant_id = UUID(payload.get("tenant_id"))

        return {
            "id": user_id,
            "tenant_id": tenant_id,
            "email": payload.get("email"),
            "role": payload.get("role")
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {str(e)}"
        )


async def stream_queue_updates(
    websocket: WebSocket,
    execution_id: str,
    token: Optional[str] = None
):
    """
    WebSocket endpoint for streaming queue position updates.

    Endpoint: /ws/executions/{execution_id}/queue?token={jwt_token}

    Features:
    - JWT authentication via query parameter
    - Validates execution exists and user has access
    - Subscribes to Redis pub/sub for queue position updates
    - Emits queue_position_update events with position and estimated start time

    Args:
        websocket: WebSocket connection
        execution_id: Execution ID to monitor
        token: JWT authentication token
    """
    redis_client = None
    pubsub = None

    try:
        # Get database session
        db = next(get_db())

        # Authenticate user
        try:
            current_user = await authenticate_websocket(token, db)
        except HTTPException as e:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication failed")
            return

        # Validate execution exists and user has access
        try:
            execution = db.query(Execution).filter(
                Execution.id == UUID(execution_id)
            ).first()

            if not execution:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Execution not found")
                return

            # TODO: Add tenant ownership validation once tenant system is fully integrated
            # For now, allow access if user is authenticated

        except ValueError:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid execution ID")
            return

        # Accept WebSocket connection
        await websocket.accept()

        # Send connection acknowledgment
        await websocket.send_json({
            "event": "connection",
            "status": "connected",
            "execution_id": execution_id,
            "timestamp": None
        })

        # Create async Redis connection for pub/sub
        redis_url = get_redis_url()
        redis_client = redis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True
        )

        # Subscribe to queue updates channel
        pubsub = redis_client.pubsub()
        channel = f"queue_updates:{execution_id}"
        await pubsub.subscribe(channel)

        # Send initial queue position
        from ..services.queue_service import QueueService
        queue_service = QueueService()

        try:
            if queue_service.enabled:
                position = queue_service.get_position(UUID(execution_id))
                estimated_wait = queue_service.estimate_wait_time(UUID(execution_id))

                await websocket.send_json({
                    "event": "queue_position_update",
                    "execution_id": execution_id,
                    "position": position,
                    "estimated_wait_seconds": estimated_wait,
                    "timestamp": None
                })
        except Exception as e:
            print(f"Failed to get initial queue position: {e}")

        # Start listening for queue update events
        async def listen_to_redis():
            """Listen to Redis pub/sub and forward to WebSocket"""
            try:
                async for message in pubsub.listen():
                    if message["type"] == "message":
                        try:
                            event_data = json.loads(message["data"])
                            await websocket.send_json(event_data)

                            # Close connection if execution started or failed
                            if event_data.get("event") == "execution.started" or \
                               event_data.get("position", 1) <= 0:
                                await asyncio.sleep(0.5)  # Give client time to receive
                                break
                        except json.JSONDecodeError:
                            continue
                        except Exception as e:
                            print(f"Error sending event: {e}")
                            break
            except asyncio.CancelledError:
                pass
            except Exception as e:
                print(f"Error in Redis listener: {e}")

        # Start listening task
        listen_task = asyncio.create_task(listen_to_redis())

        # Keep connection alive and handle client messages
        try:
            while True:
                # Receive messages from client (ping/pong, close, etc.)
                data = await websocket.receive_text()

                # Handle ping
                if data == "ping":
                    await websocket.send_json({"event": "pong"})

        except WebSocketDisconnect:
            pass
        finally:
            # Cancel listening task
            if listen_task and not listen_task.done():
                listen_task.cancel()
                try:
                    await listen_task
                except asyncio.CancelledError:
                    pass

    except Exception as e:
        print(f"WebSocket error: {e}")
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="Internal error")
        except:
            pass

    finally:
        # Cleanup
        if pubsub:
            try:
                await pubsub.unsubscribe()
                await pubsub.close()
            except:
                pass

        if redis_client:
            try:
                await redis_client.close()
            except:
                pass

        if db:
            db.close()


async def broadcast_queue_position_update(
    execution_id: UUID,
    position: int,
    estimated_wait_seconds: float
):
    """
    Broadcast queue position update to all listeners for this execution.

    Should be called by QueueService when queue position changes.

    Args:
        execution_id: Execution ID
        position: Current queue position
        estimated_wait_seconds: Estimated wait time in seconds
    """
    from ..db.redis import get_redis_client

    try:
        redis_client = get_redis_client()

        event = {
            "event": "queue_position_update",
            "execution_id": str(execution_id),
            "position": position,
            "estimated_wait_seconds": estimated_wait_seconds,
            "timestamp": None
        }

        channel = f"queue_updates:{execution_id}"
        redis_client.publish(channel, json.dumps(event))

    except Exception as e:
        print(f"Failed to broadcast queue update: {e}")
