"""Worker resource configuration for Celery execution workers."""

import os


class WorkerConfig:
    """Worker resource limits and execution settings."""

    # ===== Resource Limits =====
    # CPU limits (cores)
    WORKER_CPU_LIMIT: float = float(os.getenv("WORKER_CPU_LIMIT", "2.0"))  # 2 CPU cores per worker
    WORKER_CPU_REQUEST: float = float(os.getenv("WORKER_CPU_REQUEST", "1.0"))  # Minimum 1 CPU

    # Memory limits (MB)
    WORKER_MEMORY_LIMIT_MB: int = int(os.getenv("WORKER_MEMORY_LIMIT_MB", "4096"))  # 4GB per worker
    WORKER_MEMORY_REQUEST_MB: int = int(os.getenv("WORKER_MEMORY_REQUEST_MB", "2048"))  # Minimum 2GB

    # Worker concurrency (gevent greenlets for I/O-bound tasks)
    # Formula: CPU cores × 2 greenlets/core = 2 × 2 = 4 concurrent tasks
    WORKER_CONCURRENCY: int = int(os.getenv("WORKER_CONCURRENCY", "4"))

    # ===== Execution Timeout Settings =====
    # Default execution timeout (seconds) - 10 minutes
    DEFAULT_EXECUTION_TIMEOUT_SECONDS: int = int(os.getenv("DEFAULT_EXECUTION_TIMEOUT_SECONDS", "600"))

    # Soft time limit (raises SoftTimeLimitExceeded, sends SIGTERM for graceful shutdown)
    SOFT_TIME_LIMIT_SECONDS: int = int(os.getenv("SOFT_TIME_LIMIT_SECONDS", "600"))

    # Hard time limit (kills task with SIGKILL)
    HARD_TIME_LIMIT_SECONDS: int = int(os.getenv("HARD_TIME_LIMIT_SECONDS", "660"))

    # ===== Retry Policy Settings =====
    # Maximum number of retry attempts before sending to DLQ
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))

    # Initial retry delay (seconds) before exponential backoff
    RETRY_INITIAL_DELAY_SECONDS: int = int(os.getenv("RETRY_INITIAL_DELAY_SECONDS", "5"))

    # Maximum retry delay with backoff (seconds) - 10 minutes cap
    RETRY_MAX_DELAY_SECONDS: int = int(os.getenv("RETRY_MAX_DELAY_SECONDS", "600"))

    # Enable jitter in retry backoff to prevent thundering herd
    RETRY_JITTER_ENABLED: bool = os.getenv("RETRY_JITTER_ENABLED", "true").lower() == "true"

    # Jitter range: random multiplier between (1 - jitter_factor, 1 + jitter_factor)
    RETRY_JITTER_FACTOR: float = float(os.getenv("RETRY_JITTER_FACTOR", "0.5"))  # ±50%

    # ===== Queue Settings =====
    # Priority range: 1 (highest) to 10 (lowest)
    QUEUE_PRIORITY_HIGH: int = 1
    QUEUE_PRIORITY_NORMAL: int = 5
    QUEUE_PRIORITY_LOW: int = 10

    # Queue depth warning threshold (alert if queue > threshold)
    QUEUE_DEPTH_WARNING_THRESHOLD: int = int(os.getenv("QUEUE_DEPTH_WARNING_THRESHOLD", "100"))

    # ===== Health Check Settings =====
    # Worker heartbeat interval (seconds)
    WORKER_HEARTBEAT_INTERVAL_SECONDS: int = int(os.getenv("WORKER_HEARTBEAT_INTERVAL_SECONDS", "30"))

    # Worker considered crashed if no heartbeat for this duration (seconds)
    WORKER_HEARTBEAT_TIMEOUT_SECONDS: int = int(os.getenv("WORKER_HEARTBEAT_TIMEOUT_SECONDS", "90"))

    # Health check task interval (Celery beat)
    HEALTH_CHECK_INTERVAL_SECONDS: int = int(os.getenv("HEALTH_CHECK_INTERVAL_SECONDS", "30"))

    # ===== Artifact Storage Settings =====
    # S3/MinIO bucket for execution artifacts
    ARTIFACT_BUCKET_NAME: str = os.getenv("ARTIFACT_BUCKET_NAME", "crewai-execution-artifacts")

    # Artifact retention period (days)
    ARTIFACT_RETENTION_DAYS: int = int(os.getenv("ARTIFACT_RETENTION_DAYS", "30"))

    # Maximum artifact file size (MB) - 100MB default
    ARTIFACT_MAX_SIZE_MB: int = int(os.getenv("ARTIFACT_MAX_SIZE_MB", "100"))

    # Presigned URL expiration (seconds) - 1 hour
    ARTIFACT_PRESIGNED_URL_EXPIRY_SECONDS: int = int(os.getenv("ARTIFACT_PRESIGNED_URL_EXPIRY_SECONDS", "3600"))

    # ===== Autoscaling Settings (K8s HPA) =====
    # Minimum number of worker replicas
    AUTOSCALE_MIN_WORKERS: int = int(os.getenv("AUTOSCALE_MIN_WORKERS", "2"))

    # Maximum number of worker replicas
    AUTOSCALE_MAX_WORKERS: int = int(os.getenv("AUTOSCALE_MAX_WORKERS", "500"))

    # Target CPU utilization percentage for scaling
    AUTOSCALE_TARGET_CPU_PERCENT: int = int(os.getenv("AUTOSCALE_TARGET_CPU_PERCENT", "80"))

    # Target memory utilization percentage for scaling
    AUTOSCALE_TARGET_MEMORY_PERCENT: int = int(os.getenv("AUTOSCALE_TARGET_MEMORY_PERCENT", "80"))

    # Scale down stabilization window (seconds) - conservative scale down
    AUTOSCALE_SCALE_DOWN_STABILIZATION_SECONDS: int = int(
        os.getenv("AUTOSCALE_SCALE_DOWN_STABILIZATION_SECONDS", "300")  # 5 minutes
    )

    # Scale up stabilization window (seconds) - aggressive scale up
    AUTOSCALE_SCALE_UP_STABILIZATION_SECONDS: int = int(
        os.getenv("AUTOSCALE_SCALE_UP_STABILIZATION_SECONDS", "60")  # 1 minute
    )

    # ===== WebSocket Streaming Settings =====
    # Output buffer size (lines) kept in Redis for late joiners
    STREAM_BUFFER_SIZE: int = int(os.getenv("STREAM_BUFFER_SIZE", "100"))

    # Stream buffer TTL (seconds) after execution completes
    STREAM_BUFFER_TTL_SECONDS: int = int(os.getenv("STREAM_BUFFER_TTL_SECONDS", "3600"))  # 1 hour

    @classmethod
    def get_resource_limits(cls) -> dict:
        """Get Docker/K8s resource limits dictionary."""
        return {
            "cpu": {
                "limit": cls.WORKER_CPU_LIMIT,
                "request": cls.WORKER_CPU_REQUEST,
            },
            "memory": {
                "limit_mb": cls.WORKER_MEMORY_LIMIT_MB,
                "request_mb": cls.WORKER_MEMORY_REQUEST_MB,
            },
            "concurrency": cls.WORKER_CONCURRENCY,
        }

    @classmethod
    def get_retry_settings(cls) -> dict:
        """Get retry policy settings dictionary."""
        return {
            "max_retries": cls.MAX_RETRIES,
            "initial_delay_seconds": cls.RETRY_INITIAL_DELAY_SECONDS,
            "max_delay_seconds": cls.RETRY_MAX_DELAY_SECONDS,
            "jitter_enabled": cls.RETRY_JITTER_ENABLED,
            "jitter_factor": cls.RETRY_JITTER_FACTOR,
        }

    @classmethod
    def get_timeout_settings(cls) -> dict:
        """Get execution timeout settings dictionary."""
        return {
            "default_timeout_seconds": cls.DEFAULT_EXECUTION_TIMEOUT_SECONDS,
            "soft_time_limit_seconds": cls.SOFT_TIME_LIMIT_SECONDS,
            "hard_time_limit_seconds": cls.HARD_TIME_LIMIT_SECONDS,
        }


# Global instance
worker_config = WorkerConfig()


def get_worker_config() -> WorkerConfig:
    """Get worker configuration instance."""
    return worker_config
