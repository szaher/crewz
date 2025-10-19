"""
Configuration settings for CrewAI Platform.

Centralized configuration loaded from environment variables.
"""

import os
from typing import Optional


class Settings:
    """Application settings loaded from environment variables."""

    # ===== Worker Architecture Feature Flag =====
    # Set to True to enable isolated worker architecture with Celery
    # When False, executions run synchronously in the main API process (legacy mode)
    ENABLE_WORKER_ARCHITECTURE: bool = os.getenv("ENABLE_WORKER_ARCHITECTURE", "false").lower() == "true"

    # ===== Database Configuration =====
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    MONGODB_URL: str = os.getenv("MONGODB_URL", "")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")

    # ===== ClickHouse Configuration =====
    CLICKHOUSE_HOST: str = os.getenv("CLICKHOUSE_HOST", "clickhouse")
    CLICKHOUSE_PORT: int = int(os.getenv("CLICKHOUSE_PORT", "9000"))
    CLICKHOUSE_USER: str = os.getenv("CLICKHOUSE_USER", "crewai")
    CLICKHOUSE_PASSWORD: str = os.getenv("CLICKHOUSE_PASSWORD", "")
    CLICKHOUSE_DATABASE: str = os.getenv("CLICKHOUSE_DATABASE", "crewai_analytics")

    # ===== Security =====
    JWT_SECRET: str = os.getenv("JWT_SECRET", "dev_secret_change_in_production")
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "")

    # ===== CORS Configuration =====
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:3001")
    ALLOW_ALL_ORIGINS: bool = os.getenv("ALLOW_ALL_ORIGINS", "false").lower() == "true"

    # ===== Application Configuration =====
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")

    # ===== Logging Configuration =====
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "json")
    SQL_ECHO: bool = os.getenv("SQL_ECHO", "false").lower() == "true"

    # ===== Notifications =====
    NOTIFICATIONS_ENABLED: bool = os.getenv("NOTIFICATIONS_ENABLED", "1") == "1"


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings instance."""
    return settings


def is_worker_architecture_enabled() -> bool:
    """
    Check if worker architecture is enabled.

    Returns:
        bool: True if isolated worker architecture should be used, False for legacy sync execution.

    Usage:
        >>> from src.config.settings import is_worker_architecture_enabled
        >>> if is_worker_architecture_enabled():
        >>>     # Queue execution to Celery worker
        >>>     task.apply_async(args=[...])
        >>> else:
        >>>     # Execute synchronously in current process
        >>>     execute_directly(...)
    """
    return settings.ENABLE_WORKER_ARCHITECTURE
