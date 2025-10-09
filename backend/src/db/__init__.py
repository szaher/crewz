"""Database connection and session management."""

from .postgres import get_db, get_tenant_db, init_db
from .mongodb import get_mongo_db, get_mongo_collection
from .redis import get_redis, get_redis_client
from .clickhouse import get_clickhouse, get_clickhouse_client
import asyncio
from sqlalchemy import text
from .postgres import SessionLocal
from .redis import get_redis_client as _redis


async def check_db_health() -> bool:
    """Lightweight DB health check (SELECT 1)."""
    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            return True
        finally:
            db.close()
    except Exception:
        return False


async def check_redis_health() -> bool:
    """Lightweight Redis ping with timeout."""
    try:
        r = _redis()
        loop = asyncio.get_event_loop()
        # Run ping in a thread to avoid blocking
        return await loop.run_in_executor(None, r.ping)
    except Exception:
        return False

__all__ = [
    "get_db",
    "get_tenant_db",
    "init_db",
    "get_mongo_db",
    "get_mongo_collection",
    "get_redis",
    "get_redis_client",
    "get_clickhouse",
    "get_clickhouse_client",
    "check_db_health",
    "check_redis_health",
]
