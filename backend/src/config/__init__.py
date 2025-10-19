"""Configuration module for CrewAI Platform."""

from .settings import settings, get_settings, is_worker_architecture_enabled

__all__ = ["settings", "get_settings", "is_worker_architecture_enabled"]
