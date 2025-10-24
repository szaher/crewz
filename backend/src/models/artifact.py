"""Artifact model for execution output files."""

import enum
from sqlalchemy import Column, String, Integer, BigInteger, ForeignKey, DateTime, Boolean, Index, CheckConstraint
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import relationship
from .base import BaseModel


class ArtifactType(str, enum.Enum):
    """Classification of artifact file types."""

    DOCUMENT = "document"
    IMAGE = "image"
    DATA = "data"
    CODE = "code"
    OTHER = "other"


class Artifact(BaseModel):
    """
    Artifact model representing a file produced by an execution.

    Supports hierarchical storage with S3/local filesystem backend.
    Implements soft delete and LRU tracking for storage quota management.
    """

    __tablename__ = "file_artifacts"  # Renamed to avoid conflict with existing artifacts table

    # Foreign keys
    tenant_id = Column(postgresql.UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    execution_id = Column(postgresql.UUID(as_uuid=True), ForeignKey("executions.id"), nullable=False, index=True)
    execution_version = Column(Integer, nullable=False)

    # File information
    file_name = Column(String(255), nullable=False)
    file_extension = Column(String(10), nullable=False)
    file_size_bytes = Column(BigInteger, nullable=False)
    mime_type = Column(String(100), nullable=False)
    storage_path = Column(String(500), nullable=False)  # S3 key or filesystem path

    # Artifact classification
    artifact_type = Column(
        postgresql.ENUM(ArtifactType, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )

    # Preview support
    has_preview = Column(Boolean, nullable=False, default=False)
    preview_url = Column(String(500), nullable=True)  # Pre-signed URL or cache key

    # Soft delete and LRU tracking
    last_accessed_at = Column(DateTime, nullable=True, index=True)  # For LRU cleanup
    deleted_at = Column(DateTime, nullable=True, index=True)  # Soft delete

    # Relationships
    execution = relationship("Execution", foreign_keys=[execution_id])

    # Indexes and constraints
    __table_args__ = (
        Index("idx_artifact_tenant_created", "tenant_id", "created_at"),
        Index("idx_artifact_execution", "execution_id", "execution_version"),
        Index("idx_artifact_type", "tenant_id", "artifact_type"),
        Index("idx_artifact_deleted", "deleted_at"),  # For cleanup workers
        Index("idx_artifact_lru", "tenant_id", "last_accessed_at"),  # LRU cleanup

        # Constraints
        CheckConstraint("file_size_bytes > 0", name="chk_artifact_size_positive"),
        CheckConstraint("execution_version >= 1", name="chk_artifact_version_positive"),
    )

    def __repr__(self):
        return (
            f"<Artifact(id={self.id}, execution_id={self.execution_id}, "
            f"file_name={self.file_name}, size={self.file_size_bytes})>"
        )
