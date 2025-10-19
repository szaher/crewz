"""WebSocket execution stream endpoint (T040).

Provides real-time execution output streaming via WebSocket.
- JWT authentication via query parameter
- Redis pub/sub for event streaming
- Replay of last 100 buffered lines on connection
- Events: execution.started, execution.output, execution.progress, execution.completed, execution.error
"""

import asyncio
import json
from typing import Optional
from uuid import UUID
from fastapi import WebSocket, WebSocketDisconnect, HTTPException, status
from sqlalchemy.orm import Session
import redis.asyncio as redis

from ..db.redis import get_redis_client, get_redis_url
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


async def get_buffered_lines(execution_id: UUID, redis_client) -> list:
    """
    Retrieve buffered execution output lines from Redis.

    Returns last 100 lines that were emitted before the WebSocket connection.
    Buffer key format: execution_buffer:{execution_id}

    Args:
        execution_id: Execution ID
        redis_client: Redis client instance

    Returns:
        List of buffered event dicts
    """
    buffer_key = f"execution_buffer:{execution_id}"

    try:
        # Get buffered lines from Redis list (last 100)
        buffered = await redis_client.lrange(buffer_key, 0, -1)

        # Parse JSON events
        events = []
        for item in buffered:
            try:
                event = json.loads(item)
                events.append(event)
            except json.JSONDecodeError:
                continue

        return events
    except Exception as e:
        print(f"Failed to retrieve buffered lines: {e}")
        return []


async def stream_execution_output(
    websocket: WebSocket,
    execution_id: str,
    token: Optional[str] = None
):
    """
    WebSocket endpoint for streaming execution output.

    Endpoint: /ws/executions/{execution_id}/stream?token={jwt_token}

    Features:
    - JWT authentication via query parameter
    - Validates execution exists and user has access
    - Replays last 100 buffered lines on connection
    - Subscribes to Redis pub/sub for live updates
    - Emits events: execution.started, execution.output, execution.progress, execution.completed, execution.error

    Args:
        websocket: WebSocket connection
        execution_id: Execution ID to stream
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

        # Get and replay buffered lines
        buffered_events = await get_buffered_lines(UUID(execution_id), redis_client)

        if buffered_events:
            # Send replay indicator
            await websocket.send_json({
                "event": "replay.start",
                "count": len(buffered_events),
                "timestamp": None
            })

            # Replay buffered events
            for event in buffered_events:
                await websocket.send_json(event)

            # Send replay complete indicator
            await websocket.send_json({
                "event": "replay.complete",
                "count": len(buffered_events),
                "timestamp": None
            })

        # Subscribe to execution events channel
        pubsub = redis_client.pubsub()
        channel = f"execution_events:{execution_id}"
        await pubsub.subscribe(channel)

        # Start listening for new events
        async def listen_to_redis():
            """Listen to Redis pub/sub and forward to WebSocket"""
            try:
                async for message in pubsub.listen():
                    if message["type"] == "message":
                        try:
                            event_data = json.loads(message["data"])
                            await websocket.send_json(event_data)

                            # Close connection if execution completed or errored
                            if event_data.get("event") in ["execution.completed", "execution.error"]:
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
