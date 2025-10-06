"""Redis connection and client management."""

import os
import redis
from typing import Optional

# Redis client singleton
_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> redis.Redis:
    """
    Get Redis client instance (singleton).

    Returns:
        Redis client instance
    """
    global _redis_client

    if _redis_client is None:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        _redis_client = redis.from_url(redis_url, decode_responses=True)

    return _redis_client


def get_redis():
    """
    FastAPI dependency for Redis client.

    Returns:
        Redis client instance
    """
    return get_redis_client()
