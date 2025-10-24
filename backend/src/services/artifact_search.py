"""
Artifact metadata search service with full-text search capabilities.

Implements PostgreSQL GIN index-based search with filtering, sorting, and pagination.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
import logging

from sqlalchemy import and_, or_, func, text
from sqlalchemy.orm import Session, joinedload

from ..models.artifact import Artifact, ArtifactType
from ..models.artifact_metadata import ArtifactMetadata


logger = logging.getLogger(__name__)


class ArtifactSearchFilters:
    """Data class for artifact search filters."""

    def __init__(
        self,
        tenant_id: UUID,
        execution_id: Optional[UUID] = None,
        artifact_type: Optional[ArtifactType] = None,
        tags: Optional[List[str]] = None,
        search_query: Optional[str] = None,  # Full-text search
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        min_size_bytes: Optional[int] = None,
        max_size_bytes: Optional[int] = None,
        category: Optional[str] = None,
        file_extension: Optional[str] = None,
        include_deleted: bool = False
    ):
        """
        Initialize search filters.

        Args:
            tenant_id: Tenant UUID (required for tenant isolation)
            execution_id: Filter by specific execution
            artifact_type: Filter by artifact type (document, image, data, code, other)
            tags: Filter by tags (OR logic - any matching tag)
            search_query: Full-text search query (searches file_name and description)
            date_from: Created after this date
            date_to: Created before this date
            min_size_bytes: Minimum file size
            max_size_bytes: Maximum file size
            category: Filter by category
            file_extension: Filter by file extension (e.g., "json", "csv")
            include_deleted: Include soft-deleted artifacts
        """
        self.tenant_id = tenant_id
        self.execution_id = execution_id
        self.artifact_type = artifact_type
        self.tags = tags
        self.search_query = search_query
        self.date_from = date_from
        self.date_to = date_to
        self.min_size_bytes = min_size_bytes
        self.max_size_bytes = max_size_bytes
        self.category = category
        self.file_extension = file_extension
        self.include_deleted = include_deleted


class ArtifactSearchService:
    """
    Service for searching and filtering artifacts with metadata.

    Features:
    - Full-text search using PostgreSQL GIN indexes
    - Multi-criteria filtering (tags, type, size, date)
    - Sorting by multiple fields
    - Pagination with total count
    - <2s response time for 10k+ artifacts (NFR-004)
    """

    # Supported sort fields
    SORT_FIELDS = {
        "created_at": Artifact.created_at,
        "updated_at": Artifact.updated_at,
        "file_name": Artifact.file_name,
        "file_size_bytes": Artifact.file_size_bytes,
        "last_accessed_at": Artifact.last_accessed_at,
    }

    def __init__(self, db: Session):
        """
        Initialize artifact search service.

        Args:
            db: Database session
        """
        self.db = db


    def search_artifacts(
        self,
        filters: ArtifactSearchFilters,
        sort_by: str = "created_at",
        sort_desc: bool = True,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Artifact], int]:
        """
        Search artifacts with full-text search and filtering.

        Args:
            filters: Search filters
            sort_by: Field to sort by (default: created_at)
            sort_desc: Sort descending (default: True)
            limit: Maximum results per page
            offset: Pagination offset

        Returns:
            Tuple of (artifacts list, total count)

        Raises:
            ValueError: If sort_by field is invalid
        """
        # Validate sort field
        if sort_by not in self.SORT_FIELDS:
            raise ValueError(f"Invalid sort field: {sort_by}. Must be one of {list(self.SORT_FIELDS.keys())}")

        # Start with base query joining Artifact and ArtifactMetadata
        query = self.db.query(Artifact).outerjoin(
            ArtifactMetadata,
            ArtifactMetadata.artifact_id == Artifact.id
        )

        # Apply filters
        query = self._apply_filters(query, filters)

        # Get total count (before pagination)
        total_count = query.count()

        # Apply sorting
        sort_column = self.SORT_FIELDS[sort_by]
        if sort_desc:
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        # Apply pagination
        query = query.limit(limit).offset(offset)

        # Execute query
        artifacts = query.all()

        logger.info(
            f"Artifact search completed: {len(artifacts)} results (total: {total_count}), "
            f"filters: tenant={filters.tenant_id}, execution={filters.execution_id}, "
            f"query='{filters.search_query}', tags={filters.tags}"
        )

        return artifacts, total_count


    def _apply_filters(self, query, filters: ArtifactSearchFilters):
        """Apply search filters to query."""

        # Tenant isolation (always required)
        query = query.filter(Artifact.tenant_id == filters.tenant_id)

        # Soft delete filter
        if not filters.include_deleted:
            query = query.filter(Artifact.deleted_at.is_(None))

        # Execution ID filter
        if filters.execution_id:
            query = query.filter(Artifact.execution_id == filters.execution_id)

        # Artifact type filter
        if filters.artifact_type:
            query = query.filter(Artifact.artifact_type == filters.artifact_type)

        # File extension filter
        if filters.file_extension:
            ext = filters.file_extension.lstrip(".")
            query = query.filter(Artifact.file_extension == f".{ext}")

        # Date range filters
        if filters.date_from:
            query = query.filter(Artifact.created_at >= filters.date_from)
        if filters.date_to:
            query = query.filter(Artifact.created_at <= filters.date_to)

        # File size filters
        if filters.min_size_bytes is not None:
            query = query.filter(Artifact.file_size_bytes >= filters.min_size_bytes)
        if filters.max_size_bytes is not None:
            query = query.filter(Artifact.file_size_bytes <= filters.max_size_bytes)

        # Category filter (from metadata)
        if filters.category:
            query = query.filter(ArtifactMetadata.category == filters.category)

        # Tags filter (OR logic - any matching tag)
        if filters.tags:
            # Use PostgreSQL array overlap operator (&&)
            query = query.filter(ArtifactMetadata.tags.overlap(filters.tags))

        # Full-text search (searches file_name and description)
        if filters.search_query:
            query = self._apply_fulltext_search(query, filters.search_query)

        return query


    def _apply_fulltext_search(self, query, search_query: str):
        """
        Apply full-text search using PostgreSQL's to_tsvector and to_tsquery.

        Searches across:
        - Artifact.file_name
        - ArtifactMetadata.description

        Args:
            query: SQLAlchemy query
            search_query: Search query string

        Returns:
            Modified query with full-text search
        """
        # Clean search query (remove special characters, convert to PostgreSQL tsquery format)
        # For simple queries, we use plainto_tsquery which handles most text input safely
        search_term = search_query.strip()

        if not search_term:
            return query

        # Create full-text search conditions
        # Search in file_name (from Artifact table)
        filename_search = func.to_tsvector('english', Artifact.file_name).op('@@')(
            func.plainto_tsquery('english', search_term)
        )

        # Search in description (from ArtifactMetadata table, if exists)
        description_search = func.to_tsvector('english', func.coalesce(ArtifactMetadata.description, '')).op('@@')(
            func.plainto_tsquery('english', search_term)
        )

        # Combine with OR logic
        query = query.filter(or_(filename_search, description_search))

        return query


    def get_artifact_with_metadata(self, artifact_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Get single artifact with its metadata.

        Args:
            artifact_id: Artifact UUID

        Returns:
            Dict with artifact and metadata, or None if not found
        """
        artifact = self.db.query(Artifact).filter(Artifact.id == artifact_id).first()
        if not artifact:
            return None

        metadata = self.db.query(ArtifactMetadata).filter(
            ArtifactMetadata.artifact_id == artifact_id
        ).first()

        return {
            "artifact": artifact,
            "metadata": metadata
        }


    def get_artifacts_by_execution(
        self,
        tenant_id: UUID,
        execution_id: UUID,
        version: Optional[int] = None
    ) -> List[Artifact]:
        """
        Get all artifacts for a specific execution.

        Args:
            tenant_id: Tenant UUID
            execution_id: Execution UUID
            version: Optional execution version filter

        Returns:
            List of artifacts
        """
        query = self.db.query(Artifact).filter(
            Artifact.tenant_id == tenant_id,
            Artifact.execution_id == execution_id,
            Artifact.deleted_at.is_(None)
        )

        if version is not None:
            query = query.filter(Artifact.execution_version == version)

        return query.order_by(Artifact.created_at.desc()).all()


    def get_artifacts_by_tag(
        self,
        tenant_id: UUID,
        tag: str,
        limit: int = 100
    ) -> List[Artifact]:
        """
        Get artifacts with a specific tag.

        Args:
            tenant_id: Tenant UUID
            tag: Tag to search for
            limit: Maximum results

        Returns:
            List of artifacts
        """
        query = self.db.query(Artifact).join(
            ArtifactMetadata,
            ArtifactMetadata.artifact_id == Artifact.id
        ).filter(
            Artifact.tenant_id == tenant_id,
            Artifact.deleted_at.is_(None),
            ArtifactMetadata.tags.contains([tag])  # PostgreSQL array contains
        )

        return query.order_by(Artifact.created_at.desc()).limit(limit).all()


    def get_related_artifacts(
        self,
        artifact_id: UUID,
        tenant_id: UUID
    ) -> List[Artifact]:
        """
        Get artifacts related to a specific artifact.

        Args:
            artifact_id: Source artifact UUID
            tenant_id: Tenant UUID

        Returns:
            List of related artifacts
        """
        # Get metadata for source artifact
        metadata = self.db.query(ArtifactMetadata).filter(
            ArtifactMetadata.artifact_id == artifact_id
        ).first()

        if not metadata or not metadata.related_artifacts:
            return []

        # Get related artifacts
        related = self.db.query(Artifact).filter(
            Artifact.id.in_(metadata.related_artifacts),
            Artifact.tenant_id == tenant_id,
            Artifact.deleted_at.is_(None)
        ).all()

        return related


    def get_artifact_statistics(self, tenant_id: UUID) -> Dict[str, Any]:
        """
        Get artifact statistics for a tenant.

        Args:
            tenant_id: Tenant UUID

        Returns:
            Dict with statistics:
                - total_artifacts
                - total_size_bytes
                - artifacts_by_type
                - recent_uploads (last 7 days)
        """
        from datetime import timedelta

        # Total artifacts
        total_artifacts = self.db.query(func.count(Artifact.id)).filter(
            Artifact.tenant_id == tenant_id,
            Artifact.deleted_at.is_(None)
        ).scalar()

        # Total size
        total_size = self.db.query(func.sum(Artifact.file_size_bytes)).filter(
            Artifact.tenant_id == tenant_id,
            Artifact.deleted_at.is_(None)
        ).scalar() or 0

        # Artifacts by type
        artifacts_by_type = {}
        for artifact_type in ArtifactType:
            count = self.db.query(func.count(Artifact.id)).filter(
                Artifact.tenant_id == tenant_id,
                Artifact.artifact_type == artifact_type,
                Artifact.deleted_at.is_(None)
            ).scalar()
            artifacts_by_type[artifact_type.value] = count

        # Recent uploads (last 7 days)
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        recent_uploads = self.db.query(func.count(Artifact.id)).filter(
            Artifact.tenant_id == tenant_id,
            Artifact.created_at >= seven_days_ago,
            Artifact.deleted_at.is_(None)
        ).scalar()

        return {
            "total_artifacts": total_artifacts,
            "total_size_bytes": total_size,
            "artifacts_by_type": artifacts_by_type,
            "recent_uploads": recent_uploads
        }


# Service factory function
def get_artifact_search_service(db: Session) -> ArtifactSearchService:
    """Create artifact search service instance."""
    return ArtifactSearchService(db)
