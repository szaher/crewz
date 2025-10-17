"""
Rate limiting middleware for execution queue.

Enforces per-tenant and per-user concurrent execution limits.
Prevents queue overload and ensures fair resource distribution.
"""

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session
from typing import Optional

from ..models.execution_queue import ExecutionQueue, ExecutionStatus
from ..db import get_db


class RateLimitConfig:
    """Rate limit configuration (can be loaded from database)"""

    def __init__(self, db: Session, tenant_id: Optional[str] = None):
        self.db = db
        self.tenant_id = tenant_id

        # Default limits (can be overridden by tenant settings)
        self.concurrent_executions_per_tenant = 10
        self.concurrent_executions_per_user = 5
        self.max_executions_per_hour = None  # Unlimited by default
        self.max_executions_per_day = None  # Unlimited by default

        # Load tenant-specific limits from database if available
        if tenant_id:
            self._load_tenant_limits()

    def _load_tenant_limits(self):
        """Load rate limits from tenant settings (if configured)"""
        try:
            # Query tenant settings from database
            # This would fetch from a tenant_settings table if it exists
            # For now, use defaults
            pass
        except Exception as e:
            print(f"Failed to load tenant limits: {e}")


def check_rate_limit(
    tenant_id: str,
    user_id: str,
    db: Session
) -> tuple[bool, Optional[dict]]:
    """
    Check if execution can be submitted without exceeding rate limits.

    Args:
        tenant_id: Tenant ID
        user_id: User ID
        db: Database session

    Returns:
        Tuple of (allowed: bool, error_info: Optional[dict])
        If not allowed, error_info contains limit details
    """

    config = RateLimitConfig(db, tenant_id)

    # Check tenant-level limit
    tenant_active_count = db.query(ExecutionQueue).filter(
        ExecutionQueue.tenant_id == tenant_id,
        ExecutionQueue.status.in_([ExecutionStatus.PENDING, ExecutionStatus.RUNNING])
    ).count()

    if tenant_active_count >= config.concurrent_executions_per_tenant:
        return False, {
            "error": "Tenant rate limit exceeded",
            "limit": config.concurrent_executions_per_tenant,
            "current": tenant_active_count,
            "retry_after": 60  # Suggest retry in 60 seconds
        }

    # Check user-level limit
    user_active_count = db.query(ExecutionQueue).filter(
        ExecutionQueue.user_id == user_id,
        ExecutionQueue.status.in_([ExecutionStatus.PENDING, ExecutionStatus.RUNNING])
    ).count()

    if user_active_count >= config.concurrent_executions_per_user:
        return False, {
            "error": "User rate limit exceeded",
            "limit": config.concurrent_executions_per_user,
            "current": user_active_count,
            "retry_after": 30  # Suggest retry in 30 seconds
        }

    # Check hourly limit (if configured)
    if config.max_executions_per_hour:
        from datetime import datetime, timedelta

        hour_ago = datetime.utcnow() - timedelta(hours=1)
        hourly_count = db.query(ExecutionQueue).filter(
            ExecutionQueue.user_id == user_id,
            ExecutionQueue.scheduled_at >= hour_ago
        ).count()

        if hourly_count >= config.max_executions_per_hour:
            return False, {
                "error": "Hourly execution limit exceeded",
                "limit": config.max_executions_per_hour,
                "current": hourly_count,
                "retry_after": 3600  # Retry in 1 hour
            }

    # Check daily limit (if configured)
    if config.max_executions_per_day:
        from datetime import datetime, timedelta

        day_ago = datetime.utcnow() - timedelta(days=1)
        daily_count = db.query(ExecutionQueue).filter(
            ExecutionQueue.user_id == user_id,
            ExecutionQueue.scheduled_at >= day_ago
        ).count()

        if daily_count >= config.max_executions_per_day:
            return False, {
                "error": "Daily execution limit exceeded",
                "limit": config.max_executions_per_day,
                "current": daily_count,
                "retry_after": 86400  # Retry in 24 hours
            }

    # All checks passed
    return True, None


def enforce_rate_limit(tenant_id: str, user_id: str, db: Session):
    """
    Enforce rate limits and raise HTTPException if exceeded.

    Args:
        tenant_id: Tenant ID
        user_id: User ID
        db: Database session

    Raises:
        HTTPException: 429 Too Many Requests if rate limit exceeded
    """

    allowed, error_info = check_rate_limit(tenant_id, user_id, db)

    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=error_info,
            headers={"Retry-After": str(error_info["retry_after"])}
        )


def get_rate_limits(tenant_id: str, db: Session) -> dict:
    """
    Get current rate limit configuration for tenant.

    Args:
        tenant_id: Tenant ID
        db: Database session

    Returns:
        Dict with rate limit configuration
    """

    config = RateLimitConfig(db, tenant_id)

    return {
        "tenant_id": tenant_id,
        "concurrent_executions_per_tenant": config.concurrent_executions_per_tenant,
        "concurrent_executions_per_user": config.concurrent_executions_per_user,
        "max_executions_per_hour": config.max_executions_per_hour,
        "max_executions_per_day": config.max_executions_per_day
    }


def update_rate_limits(
    tenant_id: str,
    concurrent_per_tenant: Optional[int] = None,
    concurrent_per_user: Optional[int] = None,
    max_per_hour: Optional[int] = None,
    max_per_day: Optional[int] = None,
    db: Session = None
) -> dict:
    """
    Update rate limit configuration for tenant.

    Args:
        tenant_id: Tenant ID
        concurrent_per_tenant: New concurrent execution limit per tenant
        concurrent_per_user: New concurrent execution limit per user
        max_per_hour: New hourly limit
        max_per_day: New daily limit
        db: Database session

    Returns:
        Updated rate limit configuration
    """

    # In production, this would update tenant_settings table
    # For now, return the requested values

    return {
        "tenant_id": tenant_id,
        "concurrent_executions_per_tenant": concurrent_per_tenant or 10,
        "concurrent_executions_per_user": concurrent_per_user or 5,
        "max_executions_per_hour": max_per_hour,
        "max_executions_per_day": max_per_day
    }
