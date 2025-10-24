"""
Artifacts API endpoints for file management.

Provides upload, search, preview, download, and batch operations for execution artifacts.
"""

from typing import List, Optional
from datetime import datetime
from uuid import UUID
import io

from fastapi import APIRouter, Depends, Query, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from ...db import get_db
from ...models.user import User
from ...models.artifact import Artifact, ArtifactType
from ...models.tenant_config import TenantConfig
from ...api.middleware.auth import get_current_user
from ...services.artifact_storage import get_artifact_storage_service
from ...services.artifact_search import get_artifact_search_service, ArtifactSearchFilters
from ...services.preview_generator import get_preview_generator
from ...db.redis import get_redis_client


router = APIRouter(prefix="/artifacts", tags=["artifacts"])


# ============================================================================
# Pydantic Schemas
# ============================================================================

class ArtifactResponse(BaseModel):
    """Single artifact response."""
    id: UUID
    tenant_id: UUID
    execution_id: UUID
    execution_version: int
    file_name: str
    file_extension: str
    file_size_bytes: int
    mime_type: str
    storage_path: str
    artifact_type: str
    has_preview: bool
    preview_url: Optional[str]
    last_accessed_at: Optional[datetime]
    deleted_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ArtifactsListResponse(BaseModel):
    """Paginated artifacts list."""
    artifacts: List[ArtifactResponse]
    total: int
    limit: int
    offset: int
    has_more: bool


class ArtifactUploadResponse(BaseModel):
    """Response for artifact upload."""
    artifact_id: UUID
    file_name: str
    file_size_bytes: int
    artifact_type: str
    storage_path: str
    created_at: datetime


class ArtifactPreviewResponse(BaseModel):
    """Response for artifact preview."""
    artifact_id: UUID
    preview_type: str
    content: dict
    cached: bool
    generated_at: str


class BatchDownloadResponse(BaseModel):
    """Response for batch ZIP download."""
    download_url: str
    expires_at: datetime
    artifact_count: int
    total_size_bytes: int


# ============================================================================
# T040: POST /api/v1/artifacts - Upload artifact
# ============================================================================

@router.post("", response_model=ArtifactUploadResponse, status_code=201)
async def upload_artifact(
    execution_id: UUID = Form(...),
    version: int = Form(1),
    file: UploadFile = File(...),
    tags: Optional[str] = Form(None, description="Comma-separated tags"),
    description: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload an artifact file.

    Validates file size against tenant quota and uploads to configured storage backend.

    Returns 507 Insufficient Storage if quota exceeded.
    """
    # Get tenant config
    tenant_config = db.query(TenantConfig).filter(
        TenantConfig.tenant_id == current_user.tenant_id
    ).first()

    if not tenant_config:
        raise HTTPException(status_code=500, detail="Tenant configuration not found")

    # Read file content
    file_content = await file.read()
    file_size = len(file_content)

    # Validate file size against tenant limits
    if file_size > tenant_config.max_artifact_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum: {tenant_config.max_artifact_size_bytes} bytes"
        )

    # Check storage quota
    if tenant_config.current_storage_used_bytes + file_size > tenant_config.total_storage_quota_bytes:
        raise HTTPException(
            status_code=507,
            detail="Storage quota exceeded. Please delete old artifacts or upgrade your plan."
        )

    # Upload file
    storage_service = get_artifact_storage_service()
    file_io = io.BytesIO(file_content)

    artifact = await storage_service.upload_file(
        db=db,
        tenant_id=current_user.tenant_id,
        execution_id=execution_id,
        version=version,
        file=file_io,
        file_name=file.filename,
        mime_type=file.content_type
    )

    # Create metadata if provided
    if tags or description or category:
        from ...models.artifact_metadata import ArtifactMetadata
        import hashlib

        # Calculate checksum
        checksum = hashlib.sha256(file_content).hexdigest()

        # Parse tags
        tag_list = [t.strip() for t in tags.split(",")] if tags else []

        metadata = ArtifactMetadata(
            artifact_id=artifact.id,
            tags=tag_list,
            description=description,
            category=category,
            checksum_sha256=checksum
        )
        db.add(metadata)
        db.commit()

    # Update tenant storage usage
    tenant_config.current_storage_used_bytes += file_size
    db.commit()

    return ArtifactUploadResponse(
        artifact_id=artifact.id,
        file_name=artifact.file_name,
        file_size_bytes=artifact.file_size_bytes,
        artifact_type=artifact.artifact_type.value,
        storage_path=artifact.storage_path,
        created_at=artifact.created_at
    )


# ============================================================================
# T041: GET /api/v1/artifacts - Search/list artifacts
# ============================================================================

@router.get("", response_model=ArtifactsListResponse)
async def list_artifacts(
    execution_id: Optional[UUID] = Query(None),
    artifact_type: Optional[str] = Query(None, regex="^(document|image|data|code|other)$"),
    tags: Optional[str] = Query(None, description="Comma-separated tags (OR logic)"),
    search_query: Optional[str] = Query(None, description="Full-text search"),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    min_size: Optional[int] = Query(None, ge=0),
    max_size: Optional[int] = Query(None, ge=0),
    category: Optional[str] = Query(None),
    file_extension: Optional[str] = Query(None),
    sort_by: str = Query("created_at", regex="^(created_at|updated_at|file_name|file_size_bytes|last_accessed_at)$"),
    sort_desc: bool = Query(True),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Search and list artifacts with full-text search and filtering.

    Optimized for <2s response with 10k+ artifacts (NFR-004).

    Filters:
    - execution_id: Filter by specific execution
    - artifact_type: document, image, data, code, other
    - tags: Comma-separated tags (OR logic - any matching tag)
    - search_query: Full-text search in file name and description
    - date_from/date_to: Date range filter
    - min_size/max_size: File size range in bytes
    - category: Custom category filter
    - file_extension: Filter by extension (e.g., "json", "csv")

    Sorting:
    - sort_by: Field to sort by
    - sort_desc: Sort descending (default: true)
    """
    # Parse filters
    tag_list = [t.strip() for t in tags.split(",")] if tags else None
    artifact_type_enum = ArtifactType(artifact_type) if artifact_type else None

    filters = ArtifactSearchFilters(
        tenant_id=current_user.tenant_id,
        execution_id=execution_id,
        artifact_type=artifact_type_enum,
        tags=tag_list,
        search_query=search_query,
        date_from=date_from,
        date_to=date_to,
        min_size_bytes=min_size,
        max_size_bytes=max_size,
        category=category,
        file_extension=file_extension,
        include_deleted=False
    )

    # Search artifacts
    search_service = get_artifact_search_service(db)
    artifacts, total = search_service.search_artifacts(
        filters=filters,
        sort_by=sort_by,
        sort_desc=sort_desc,
        limit=limit,
        offset=offset
    )

    return ArtifactsListResponse(
        artifacts=[ArtifactResponse.from_orm(a) for a in artifacts],
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + len(artifacts)) < total
    )


# ============================================================================
# T042: GET /api/v1/artifacts/{id}/download - Download artifact
# ============================================================================

@router.get("/{artifact_id}/download")
async def download_artifact(
    artifact_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Download artifact file.

    Returns pre-signed URL (S3) or direct file download (local storage).
    URL expires after 1 hour.
    """
    # Get artifact
    artifact = db.query(Artifact).filter(
        Artifact.id == artifact_id,
        Artifact.tenant_id == current_user.tenant_id
    ).first()

    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    if artifact.deleted_at:
        raise HTTPException(status_code=410, detail="Artifact has been deleted")

    # Generate download URL
    storage_service = get_artifact_storage_service()
    download_url = await storage_service.download_file(db, artifact_id)

    from datetime import timedelta
    expires_at = datetime.utcnow() + timedelta(hours=1)

    return {
        "download_url": download_url,
        "expires_at": expires_at.isoformat(),
        "file_name": artifact.file_name,
        "file_size_bytes": artifact.file_size_bytes,
        "mime_type": artifact.mime_type
    }


# ============================================================================
# T043: GET /api/v1/artifacts/{id}/preview - Generate preview
# ============================================================================

@router.get("/{artifact_id}/preview", response_model=ArtifactPreviewResponse)
async def get_artifact_preview(
    artifact_id: UUID,
    force_regenerate: bool = Query(False, description="Force regenerate preview (bypass cache)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate artifact preview.

    Supports:
    - JSON: Syntax-highlighted
    - CSV: Table preview (max 100 rows)
    - Images: Thumbnail (800x600px)
    - PDF: First page thumbnail
    - Code: Syntax-highlighted
    - Text: Plain text

    Previews are cached in Redis for 1 hour.
    Generation completes in <3s for files <10MB (NFR-002).
    """
    # Get artifact
    artifact = db.query(Artifact).filter(
        Artifact.id == artifact_id,
        Artifact.tenant_id == current_user.tenant_id
    ).first()

    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    if artifact.deleted_at:
        raise HTTPException(status_code=410, detail="Artifact has been deleted")

    # Get file path (only works for local storage)
    storage_service = get_artifact_storage_service()

    try:
        file_path = await storage_service.get_local_file_path(artifact_id, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Generate preview
    redis_client = get_redis_client()
    preview_service = get_preview_generator(redis_client)

    try:
        preview = await preview_service.generate_preview(
            artifact=artifact,
            file_path=file_path,
            force_regenerate=force_regenerate
        )

        # Update artifact has_preview flag if not set
        if not artifact.has_preview:
            artifact.has_preview = True
            db.commit()

        return ArtifactPreviewResponse(
            artifact_id=artifact_id,
            preview_type=preview["preview_type"],
            content=preview["content"],
            cached=preview.get("cached", False),
            generated_at=preview["generated_at"]
        )

    except ValueError as e:
        raise HTTPException(status_code=415, detail=str(e))


# ============================================================================
# T044: PATCH /api/v1/artifacts/{id} - Update metadata
# ============================================================================

class ArtifactMetadataUpdate(BaseModel):
    """Request body for metadata update."""
    tags: Optional[List[str]] = Field(None, max_items=20)
    description: Optional[str] = None
    category: Optional[str] = None


@router.patch("/{artifact_id}")
async def update_artifact_metadata(
    artifact_id: UUID,
    update: ArtifactMetadataUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update artifact metadata (tags, description, category).

    Tags: Maximum 20 tags, each max 50 characters.
    """
    from ...models.artifact_metadata import ArtifactMetadata

    # Verify artifact ownership
    artifact = db.query(Artifact).filter(
        Artifact.id == artifact_id,
        Artifact.tenant_id == current_user.tenant_id
    ).first()

    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    # Get or create metadata
    metadata = db.query(ArtifactMetadata).filter(
        ArtifactMetadata.artifact_id == artifact_id
    ).first()

    if not metadata:
        import hashlib
        metadata = ArtifactMetadata(
            artifact_id=artifact_id,
            checksum_sha256=hashlib.sha256(b"").hexdigest()  # Placeholder
        )
        db.add(metadata)

    # Update fields
    if update.tags is not None:
        # Validate tag lengths
        for tag in update.tags:
            if len(tag) > 50:
                raise HTTPException(status_code=400, detail=f"Tag too long (max 50 chars): {tag}")
        metadata.tags = update.tags

    if update.description is not None:
        metadata.description = update.description

    if update.category is not None:
        metadata.category = update.category

    db.commit()
    db.refresh(metadata)

    return {"message": "Metadata updated successfully", "artifact_id": str(artifact_id)}


# ============================================================================
# T045: DELETE /api/v1/artifacts/{id} - Soft delete
# ============================================================================

@router.delete("/{artifact_id}")
async def delete_artifact(
    artifact_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Soft delete artifact.

    Sets deleted_at timestamp. Hard deletion occurs after 7-day grace period.
    """
    storage_service = get_artifact_storage_service()

    try:
        success = await storage_service.delete_file(db, artifact_id)
        return {"message": "Artifact deleted successfully", "artifact_id": str(artifact_id)}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ============================================================================
# T046: POST /api/v1/artifacts/batch/download - Batch ZIP download
# ============================================================================

class BatchDownloadRequest(BaseModel):
    """Request body for batch download."""
    artifact_ids: List[UUID] = Field(..., min_items=1, max_items=100)


@router.post("/batch/download", response_model=BatchDownloadResponse)
async def batch_download_artifacts(
    request: BatchDownloadRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Download multiple artifacts as a ZIP file.

    Maximum 100 artifacts, total size up to 1GB (NFR-006).
    """
    # TODO: Implement ZIP generation and upload
    # This is a placeholder implementation
    raise HTTPException(status_code=501, detail="Batch download not yet implemented")


# ============================================================================
# T047: POST /api/v1/artifacts/batch/update - Batch metadata update
# ============================================================================

class BatchMetadataUpdate(BaseModel):
    """Request body for batch metadata update."""
    artifact_ids: List[UUID] = Field(..., min_items=1)
    add_tags: Optional[List[str]] = None
    remove_tags: Optional[List[str]] = None
    category: Optional[str] = None


@router.post("/batch/update")
async def batch_update_metadata(
    request: BatchMetadataUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Batch update artifact metadata.

    Operations:
    - add_tags: Add tags to all artifacts
    - remove_tags: Remove tags from all artifacts
    - category: Set category for all artifacts
    """
    from ...models.artifact_metadata import ArtifactMetadata

    updated_count = 0
    failed_ids = []

    for artifact_id in request.artifact_ids:
        try:
            # Verify artifact ownership
            artifact = db.query(Artifact).filter(
                Artifact.id == artifact_id,
                Artifact.tenant_id == current_user.tenant_id
            ).first()

            if not artifact:
                failed_ids.append(str(artifact_id))
                continue

            # Get or create metadata
            metadata = db.query(ArtifactMetadata).filter(
                ArtifactMetadata.artifact_id == artifact_id
            ).first()

            if not metadata:
                import hashlib
                metadata = ArtifactMetadata(
                    artifact_id=artifact_id,
                    tags=[],
                    checksum_sha256=hashlib.sha256(b"").hexdigest()
                )
                db.add(metadata)

            # Apply updates
            if request.add_tags:
                current_tags = set(metadata.tags or [])
                current_tags.update(request.add_tags)
                metadata.tags = list(current_tags)

            if request.remove_tags:
                current_tags = set(metadata.tags or [])
                current_tags.difference_update(request.remove_tags)
                metadata.tags = list(current_tags)

            if request.category is not None:
                metadata.category = request.category

            updated_count += 1

        except Exception as e:
            failed_ids.append(str(artifact_id))

    db.commit()

    return {
        "updated_count": updated_count,
        "failed_ids": failed_ids
    }


# ============================================================================
# T048: POST /api/v1/artifacts/batch/delete - Batch soft delete
# ============================================================================

class BatchDeleteRequest(BaseModel):
    """Request body for batch delete."""
    artifact_ids: List[UUID] = Field(..., min_items=1)


@router.post("/batch/delete")
async def batch_delete_artifacts(
    request: BatchDeleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Batch soft delete artifacts.

    Sets deleted_at timestamp for all specified artifacts.
    """
    storage_service = get_artifact_storage_service()

    deleted_count = 0
    failed_ids = []

    for artifact_id in request.artifact_ids:
        try:
            await storage_service.delete_file(db, artifact_id)
            deleted_count += 1
        except Exception as e:
            failed_ids.append(str(artifact_id))

    return {
        "deleted_count": deleted_count,
        "failed_ids": failed_ids
    }
