"""
WebSocket connection manager for real-time notifications.

Manages WebSocket connections per user and tenant, handles reconnection,
and routes notifications from Redis pub/sub to connected clients.
"""

from typing import Dict, Set, Optional
from fastapi import WebSocket, WebSocketDisconnect
from uuid import UUID
import json
import asyncio
from datetime import datetime


class ConnectionManager:
    """
    Manages WebSocket connections for real-time notifications.

    Features:
    - Per-user connection tracking
    - Per-tenant connection tracking
    - Broadcast to user/tenant/all
    - Automatic cleanup on disconnect
    - Heartbeat/ping support
    """

    def __init__(self):
        # user_id -> Set[WebSocket]
        self.user_connections: Dict[str, Set[WebSocket]] = {}

        # tenant_id -> Set[WebSocket]
        self.tenant_connections: Dict[str, Set[WebSocket]] = {}

        # websocket -> (user_id, tenant_id)
        self.connection_metadata: Dict[WebSocket, tuple[str, str]] = {}

    async def connect(
        self,
        websocket: WebSocket,
        user_id: UUID,
        tenant_id: UUID
    ):
        """
        Accept and register a new WebSocket connection.

        Args:
            websocket: WebSocket connection
            user_id: User ID
            tenant_id: Tenant ID
        """
        await websocket.accept()

        user_id_str = str(user_id)
        tenant_id_str = str(tenant_id)

        # Register connection
        if user_id_str not in self.user_connections:
            self.user_connections[user_id_str] = set()
        self.user_connections[user_id_str].add(websocket)

        if tenant_id_str not in self.tenant_connections:
            self.tenant_connections[tenant_id_str] = set()
        self.tenant_connections[tenant_id_str].add(websocket)

        self.connection_metadata[websocket] = (user_id_str, tenant_id_str)

        # Send connection acknowledgment
        await self.send_to_connection(websocket, {
            "type": "connection",
            "status": "connected",
            "user_id": user_id_str,
            "tenant_id": tenant_id_str,
            "timestamp": datetime.utcnow().isoformat()
        })

    def disconnect(self, websocket: WebSocket):
        """
        Remove a WebSocket connection and cleanup.

        Args:
            websocket: WebSocket to disconnect
        """
        if websocket not in self.connection_metadata:
            return

        user_id, tenant_id = self.connection_metadata[websocket]

        # Remove from user connections
        if user_id in self.user_connections:
            self.user_connections[user_id].discard(websocket)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]

        # Remove from tenant connections
        if tenant_id in self.tenant_connections:
            self.tenant_connections[tenant_id].discard(websocket)
            if not self.tenant_connections[tenant_id]:
                del self.tenant_connections[tenant_id]

        # Remove metadata
        del self.connection_metadata[websocket]

    async def send_to_connection(
        self,
        websocket: WebSocket,
        message: dict
    ):
        """
        Send message to a specific connection.

        Args:
            websocket: Target WebSocket
            message: Message dict (will be JSON serialized)
        """
        try:
            await websocket.send_json(message)
        except Exception as e:
            print(f"Failed to send to connection: {e}")
            self.disconnect(websocket)

    async def send_to_user(
        self,
        user_id: UUID,
        message: dict
    ):
        """
        Send message to all connections for a user.

        Args:
            user_id: Target user ID
            message: Message to send
        """
        user_id_str = str(user_id)

        if user_id_str not in self.user_connections:
            return

        # Send to all user's connections
        disconnected = []
        for websocket in self.user_connections[user_id_str]:
            try:
                await websocket.send_json(message)
            except Exception as e:
                print(f"Failed to send to user {user_id_str}: {e}")
                disconnected.append(websocket)

        # Cleanup disconnected
        for websocket in disconnected:
            self.disconnect(websocket)

    async def send_to_tenant(
        self,
        tenant_id: UUID,
        message: dict
    ):
        """
        Send message to all connections for a tenant.

        Args:
            tenant_id: Target tenant ID
            message: Message to send
        """
        tenant_id_str = str(tenant_id)

        if tenant_id_str not in self.tenant_connections:
            return

        # Send to all tenant's connections
        disconnected = []
        for websocket in self.tenant_connections[tenant_id_str]:
            try:
                await websocket.send_json(message)
            except Exception as e:
                print(f"Failed to send to tenant {tenant_id_str}: {e}")
                disconnected.append(websocket)

        # Cleanup disconnected
        for websocket in disconnected:
            self.disconnect(websocket)

    async def broadcast_all(self, message: dict):
        """
        Broadcast message to all connected clients.

        Args:
            message: Message to broadcast
        """
        disconnected = []

        for websocket in self.connection_metadata.keys():
            try:
                await websocket.send_json(message)
            except Exception as e:
                print(f"Failed to broadcast: {e}")
                disconnected.append(websocket)

        # Cleanup disconnected
        for websocket in disconnected:
            self.disconnect(websocket)

    def get_user_connection_count(self, user_id: UUID) -> int:
        """Get number of active connections for a user"""
        return len(self.user_connections.get(str(user_id), set()))

    def get_tenant_connection_count(self, tenant_id: UUID) -> int:
        """Get number of active connections for a tenant"""
        return len(self.tenant_connections.get(str(tenant_id), set()))

    def get_total_connections(self) -> int:
        """Get total number of active connections"""
        return len(self.connection_metadata)

    async def ping_all(self):
        """
        Send ping to all connections (heartbeat).
        Should be called periodically to detect dead connections.
        """
        disconnected = []

        ping_message = {
            "type": "ping",
            "timestamp": datetime.utcnow().isoformat()
        }

        for websocket in self.connection_metadata.keys():
            try:
                await websocket.send_json(ping_message)
            except Exception:
                disconnected.append(websocket)

        # Cleanup disconnected
        for websocket in disconnected:
            self.disconnect(websocket)


# Global connection manager instance
connection_manager = ConnectionManager()
