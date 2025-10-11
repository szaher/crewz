"""Notification event publisher via Redis Pub/Sub."""

import json
import os
import redis
from typing import Dict, Any
from datetime import datetime


class NotificationPublisher:
    def __init__(self):
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
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

    def publish(self, user_id: int, payload: Dict[str, Any]) -> None:
        # Feature flag to disable notifications entirely
        if os.getenv("NOTIFICATIONS_ENABLED", "0").lower() in ("0", "false"):  # pragma: no cover
            return
        event = {
            "type": payload.get("type", "info"),
            "title": payload.get("title"),
            "message": payload.get("message"),
            "data": payload.get("data", {}),
            "timestamp": datetime.utcnow().isoformat(),
        }
        if not getattr(self, 'redis_client', None):
            return
        try:
            channel = f"notifications:{user_id}"
            self.redis_client.publish(channel, json.dumps(event))
        except Exception:
            pass
