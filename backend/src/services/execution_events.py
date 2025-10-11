"""Execution event publishing via Redis Pub/Sub."""

import json
import redis
import os
from typing import Dict, Any, Optional
from datetime import datetime


class ExecutionEventPublisher:
    """
    Publisher for execution events to Redis.

    Events are published to channel: executions:{execution_id}
    """

    def __init__(self):
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        # Use short timeouts so missing/slow Redis doesn't stall requests
        try:
            self.redis_client = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=float(os.getenv("REDIS_CONNECT_TIMEOUT", 0.5)),
                socket_timeout=float(os.getenv("REDIS_SOCKET_TIMEOUT", 0.5)),
                retry_on_timeout=False,
            )
        except Exception:
            self.redis_client = None

    def _publish_event(
        self,
        execution_id: int,
        event_type: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Publish an event to Redis.

        Args:
            execution_id: Execution ID
            event_type: Event type
            data: Event data
        """
        event = {
            "type": event_type,
            "execution_id": execution_id,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data or {},
        }

        if not getattr(self, 'redis_client', None):
            return
        try:
            channel = f"executions:{execution_id}"
            self.redis_client.publish(channel, json.dumps(event))
        except Exception:
            # Fail soft when Redis is down/slow
            pass

    async def publish_execution_started(
        self, execution_id: int, input_data: Dict[str, Any]
    ) -> None:
        """Publish execution started event."""
        self._publish_event(
            execution_id=execution_id,
            event_type="execution_started",
            data={"input_data": input_data},
        )

    async def publish_execution_completed(
        self, execution_id: int, output_data: Dict[str, Any]
    ) -> None:
        """Publish execution completed event."""
        self._publish_event(
            execution_id=execution_id,
            event_type="execution_completed",
            data={"output_data": output_data},
        )

    async def publish_execution_failed(
        self, execution_id: int, error: str
    ) -> None:
        """Publish execution failed event."""
        self._publish_event(
            execution_id=execution_id,
            event_type="execution_failed",
            data={"error": error},
        )

    async def publish_node_started(
        self, execution_id: int, node_id: str, node_type: str
    ) -> None:
        """Publish node started event."""
        self._publish_event(
            execution_id=execution_id,
            event_type="node_started",
            data={"node_id": node_id, "node_type": node_type},
        )

    async def publish_node_completed(
        self, execution_id: int, node_id: str, output: Any
    ) -> None:
        """Publish node completed event."""
        self._publish_event(
            execution_id=execution_id,
            event_type="node_completed",
            data={"node_id": node_id, "output": output},
        )

    async def publish_node_failed(
        self, execution_id: int, node_id: str, error: str
    ) -> None:
        """Publish node failed event."""
        self._publish_event(
            execution_id=execution_id,
            event_type="node_failed",
            data={"node_id": node_id, "error": error},
        )
