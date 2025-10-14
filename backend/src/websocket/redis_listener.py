"""
Redis pub/sub listener for routing notifications to WebSocket clients.

Listens to Redis channels and forwards notifications to connected WebSocket clients
via the ConnectionManager.
"""

import asyncio
import json
from uuid import UUID
from typing import Optional
import redis.asyncio as redis

from .connection_manager import connection_manager
from ..db.redis import get_redis_url


class RedisNotificationListener:
    """
    Listens to Redis pub/sub channels and routes notifications to WebSocket clients.

    Channels:
    - notifications:user:{user_id} - User-specific notifications
    - notifications:tenant:{tenant_id} - Tenant-wide notifications
    - notifications:admins:* - Admin notifications
    - notifications:broadcast - System-wide broadcasts
    """

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or get_redis_url()
        self.redis_client: Optional[redis.Redis] = None
        self.pubsub = None
        self.listen_task: Optional[asyncio.Task] = None

    async def start(self):
        """
        Start listening to Redis pub/sub channels.
        """
        try:
            # Create async Redis connection
            self.redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )

            self.pubsub = self.redis_client.pubsub()

            # Subscribe to all notification channels using pattern
            await self.pubsub.psubscribe(
                "notifications:user:*",
                "notifications:tenant:*",
                "notifications:admins:*",
                "notifications:broadcast"
            )

            print("Redis notification listener started")

            # Start listening loop
            self.listen_task = asyncio.create_task(self._listen_loop())

        except Exception as e:
            print(f"Failed to start Redis listener: {e}")
            raise

    async def stop(self):
        """
        Stop listening and cleanup.
        """
        if self.listen_task:
            self.listen_task.cancel()
            try:
                await self.listen_task
            except asyncio.CancelledError:
                pass

        if self.pubsub:
            await self.pubsub.unsubscribe()
            await self.pubsub.close()

        if self.redis_client:
            await self.redis_client.close()

        print("Redis notification listener stopped")

    async def _listen_loop(self):
        """
        Main listening loop - processes messages from Redis pub/sub.
        """
        try:
            async for message in self.pubsub.listen():
                if message["type"] == "pmessage":
                    await self._handle_message(
                        message["channel"],
                        message["data"]
                    )
        except asyncio.CancelledError:
            print("Redis listener loop cancelled")
        except Exception as e:
            print(f"Error in Redis listener loop: {e}")

    async def _handle_message(self, channel: str, data: str):
        """
        Handle incoming Redis pub/sub message and route to WebSocket clients.

        Args:
            channel: Redis channel name (e.g., "notifications:user:abc123")
            data: Message data (JSON string)
        """
        try:
            # Parse message data
            message_data = json.loads(data) if isinstance(data, str) else data

            # Route based on channel pattern
            if channel.startswith("notifications:user:"):
                # Extract user_id from channel
                user_id_str = channel.split(":")[-1]
                user_id = UUID(user_id_str)

                # Send to user's WebSocket connections
                await connection_manager.send_to_user(user_id, message_data)

            elif channel.startswith("notifications:tenant:"):
                # Extract tenant_id from channel
                tenant_id_str = channel.split(":")[-1]
                tenant_id = UUID(tenant_id_str)

                # Send to tenant's WebSocket connections
                await connection_manager.send_to_tenant(tenant_id, message_data)

            elif channel.startswith("notifications:admins:"):
                # Admin notifications - for now, just log
                # In production, send to admin dashboard connections
                print(f"Admin notification: {message_data}")

            elif channel == "notifications:broadcast":
                # System-wide broadcast
                await connection_manager.broadcast_all(message_data)

        except Exception as e:
            print(f"Failed to handle message from {channel}: {e}")


# Global listener instance
redis_listener = RedisNotificationListener()


async def start_notification_listener():
    """
    Start the Redis notification listener.
    Should be called on application startup.
    """
    await redis_listener.start()


async def stop_notification_listener():
    """
    Stop the Redis notification listener.
    Should be called on application shutdown.
    """
    await redis_listener.stop()
