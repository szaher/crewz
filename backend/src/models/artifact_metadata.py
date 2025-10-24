"""ArtifactMetadata model for enriching artifacts with searchable information."""

from sqlalchemy import Column, String, Text, ForeignKey, Index
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import relationship
from .base import BaseModel


class ArtifactMetadata(BaseModel):
    """
    ArtifactMetadata model for enriching artifacts with user-provided metadata.

    Supports tagging, categorization, and full-text search.
    Tracks file integrity with SHA-256 checksum.
    """

    __tablename__ = "file_artifact_metadata"  # Renamed to match file_artifacts table

    # Foreign key (one-to-one with Artifact)
    artifact_id = Column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("file_artifacts.id"),
        nullable=False,
        unique=True,
        index=True
    )

    # User-provided metadata
    tags = Column(postgresql.ARRAY(String(50)), nullable=True)  # Max 20 tags, 50 chars each
    description = Column(Text, nullable=True)  # User-provided description
    category = Column(String(100), nullable=True)  # Custom category

    # System metadata
    checksum_sha256 = Column(String(64), nullable=False)  # File integrity verification
    compression_type = Column(String(20), nullable=True)  # If file is compressed (e.g., "gzip", "zip")

    # Relationships
    related_artifacts = Column(
        postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
        nullable=True
    )  # Links to related artifacts

    # Relationships
    artifact = relationship("Artifact", foreign_keys=[artifact_id])

    # Indexes and constraints
    # Note: GIN indexes for full-text search are created in migration
    # (idx_file_metadata_tags, idx_file_metadata_description)
    __table_args__ = (
        Index("idx_file_metadata_artifact", "artifact_id"),
    )

    def __repr__(self):
        return (
            f"<ArtifactMetadata(id={self.id}, artifact_id={self.artifact_id}, "
            f"tags={len(self.tags) if self.tags else 0})>"
        )
