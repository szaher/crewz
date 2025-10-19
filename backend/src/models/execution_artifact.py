"""Execution artifact model for storing execution output files."""

import enum
from datetime import datetime, timedelta
from sqlalchemy import Column, String, Integer, ForeignKey, Enum, DateTime, BigInteger
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import relationship
from .base import BaseModel


class ArtifactType(str, enum.Enum):
    """Artifact type enumeration."""

    OUTPUT_FILE = "output_file"  # General output file
    LOG_FILE = "log_file"  # Execution log
    RESULT_JSON = "result_json"  # JSON result data
    ERROR_LOG = "error_log"  # Error/traceback log
    METRICS_FILE = "metrics_file"  # Performance metrics
    CUSTOM = "custom"  # Custom artifact type


class ExecutionArtifact(BaseModel):
    """
    Execution artifact model for storing files generated during execution.

    Artifacts are versioned and stored in S3/MinIO with metadata in PostgreSQL.
    Supports automatic cleanup based on retention policy.
    """

    __tablename__ = "execution_artifacts"

    # Foreign keys
    execution_id = Column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("executions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    tenant_id = Column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # File information
    file_path = Column(String(1024), nullable=False)  # S3/MinIO path: s3://bucket/tenant/execution/version/file
    file_name = Column(String(255), nullable=False)  # Original filename
    file_size = Column(BigInteger, nullable=False)  # File size in bytes
    mime_type = Column(String(127), nullable=True)  # MIME type (e.g., application/json, text/plain)

    # Artifact metadata
    artifact_type = Column(
        Enum(ArtifactType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=ArtifactType.OUTPUT_FILE.value,
        index=True
    )
    version_number = Column(Integer, nullable=False, default=1, index=True)  # Artifact version (for re-executions)

    # Expiration
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)  # Auto-cleanup after this date

    # Relationships
    execution = relationship("Execution", back_populates="artifacts")
    tenant = relationship("Tenant")

    def __repr__(self):
        return f"<ExecutionArtifact(id={self.id}, execution_id={self.execution_id}, file_name={self.file_name}, version={self.version_number})>"

    @classmethod
    def calculate_expiration(cls, retention_days: int = 30) -> datetime:
        """
        Calculate expiration timestamp based on retention policy.

        Args:
            retention_days: Number of days to retain artifact (default 30)

        Returns:
            Expiration datetime (UTC)
        """
        return datetime.utcnow() + timedelta(days=retention_days)

    def is_expired(self) -> bool:
        """
        Check if artifact has expired.

        Returns:
            True if artifact should be deleted
        """
        return datetime.utcnow() >= self.expires_at

    def get_download_key(self) -> str:
        """
        Get S3 object key for download.

        Returns:
            S3 object key without bucket name
        """
        # file_path format: s3://bucket/tenant/execution/version/file
        # Extract: tenant/execution/version/file
        if self.file_path.startswith("s3://"):
            parts = self.file_path.split("/", 3)
            if len(parts) >= 4:
                return parts[3]  # Everything after bucket name
        return self.file_path
