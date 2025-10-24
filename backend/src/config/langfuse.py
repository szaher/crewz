"""
Langfuse configuration for LLM execution tracing.

Provides async client initialization and configuration management.
Environment variables control Langfuse connection settings.
"""

import os
from typing import Optional
from langfuse import Langfuse


# Langfuse Configuration
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

# Feature flag to enable/disable tracing
LANGFUSE_ENABLED = os.getenv("LANGFUSE_ENABLED", "true").lower() == "true"

# Flush configuration
LANGFUSE_FLUSH_INTERVAL_MS = int(os.getenv("LANGFUSE_FLUSH_INTERVAL_MS", "1000"))  # 1 second
LANGFUSE_FLUSH_AT = int(os.getenv("LANGFUSE_FLUSH_AT", "15"))  # Batch size before flush


# Global Langfuse client instance
_langfuse_client: Optional[Langfuse] = None


def get_langfuse_client() -> Optional[Langfuse]:
    """
    Get or initialize the global Langfuse client.

    Returns:
        Optional[Langfuse]: Langfuse client instance, or None if tracing is disabled

    Note:
        Returns None if LANGFUSE_ENABLED=false or if credentials are missing.
        This allows graceful degradation when tracing is unavailable.
    """
    global _langfuse_client

    # Return None if tracing is disabled
    if not LANGFUSE_ENABLED:
        return None

    # Return existing client if already initialized
    if _langfuse_client is not None:
        return _langfuse_client

    # Initialize client if credentials are available
    if LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY:
        try:
            _langfuse_client = Langfuse(
                public_key=LANGFUSE_PUBLIC_KEY,
                secret_key=LANGFUSE_SECRET_KEY,
                host=LANGFUSE_HOST,
                flush_interval=LANGFUSE_FLUSH_INTERVAL_MS / 1000,  # Convert to seconds
                flush_at=LANGFUSE_FLUSH_AT,
            )
            return _langfuse_client

        except Exception as e:
            # Log error but don't fail - graceful degradation
            print(f"Warning: Failed to initialize Langfuse client: {e}")
            return None

    else:
        # Credentials not configured
        if LANGFUSE_ENABLED:
            print(
                "Warning: Langfuse tracing is enabled but credentials are missing. "
                "Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY environment variables."
            )
        return None


def validate_langfuse_config() -> bool:
    """
    Validate Langfuse configuration at startup.

    Returns:
        bool: True if configuration is valid (or if tracing is disabled)

    Note:
        If tracing is enabled but credentials are missing, this returns True
        to allow graceful degradation. Warnings are logged instead.
    """
    if not LANGFUSE_ENABLED:
        return True

    if not LANGFUSE_PUBLIC_KEY or not LANGFUSE_SECRET_KEY:
        print(
            "Warning: Langfuse tracing is enabled but credentials are not configured. "
            "Tracing will be disabled. Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY."
        )
        return True

    # Test connection
    try:
        client = get_langfuse_client()
        if client is None:
            return True  # Graceful degradation

        # Verify client can connect (flush will test connection)
        client.flush()
        return True

    except Exception as e:
        print(f"Warning: Langfuse connection validation failed: {e}")
        return True  # Allow graceful degradation


def shutdown_langfuse():
    """
    Shutdown Langfuse client and flush pending traces.

    Should be called on application shutdown to ensure all traces are sent.
    """
    global _langfuse_client

    if _langfuse_client is not None:
        try:
            _langfuse_client.flush()
        except Exception as e:
            print(f"Warning: Error flushing Langfuse traces on shutdown: {e}")

        _langfuse_client = None
