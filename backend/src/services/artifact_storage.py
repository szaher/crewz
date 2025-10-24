"""
Artifact storage service with S3/local filesystem abstraction.

Implements hierarchical storage, pre-signed URLs, and graceful degradation.
"""

import os
import shutil
import mimetypes
from pathlib import Path
from typing import BinaryIO, Optional, Tuple
from uuid import UUID
from datetime import datetime, timedelta
import logging

from sqlalchemy.orm import Session

from ..config.storage import get_storage_config, PRESIGNED_URL_EXPIRATION
from ..models.artifact import Artifact, ArtifactType


logger = logging.getLogger(__name__)


class ArtifactStorageService:
    """
    Unified storage service supporting S3 and local filesystem.

    Path format: {tenant_id}/{execution_id}/{version}/{artifact_id}.{ext}

    Features:
    - Hierarchical path organization
    - Pre-signed URL generation
    - Graceful degradation (fallback to local if S3 fails)
    - Atomic uploads with validation
    """

    def __init__(self):
        """Initialize storage backend based on configuration."""
        self.config = get_storage_config()
        self.storage_type = self.config["type"]

        # Initialize S3 client if using S3
        if self.storage_type == "s3":
            try:
                import boto3
                self.s3_client = boto3.client(
                    "s3",
                    aws_access_key_id=self.config["access_key_id"],
                    aws_secret_access_key=self.config["secret_access_key"],
                    region_name=self.config.get("region"),
                    endpoint_url=self.config.get("endpoint_url")
                )
                self.bucket_name = self.config["bucket_name"]
                logger.info(f"Initialized S3 storage backend (bucket: {self.bucket_name})")
            except Exception as e:
                logger.error(f"Failed to initialize S3 client: {e}. Falling back to local storage.")
                self.storage_type = "local"
                self.config["type"] = "local"
                self.config["storage_path"] = "/var/crewai/artifacts"

        # Initialize local filesystem if using local storage
        if self.storage_type == "local":
            self.local_storage_path = Path(self.config["storage_path"])
            self.local_storage_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Initialized local filesystem storage (path: {self.local_storage_path})")


    def _generate_storage_path(
        self,
        tenant_id: UUID,
        execution_id: UUID,
        version: int,
        artifact_id: UUID,
        file_extension: str
    ) -> str:
        """
        Generate hierarchical storage path.

        Format: {tenant_id}/{execution_id}/{version}/{artifact_id}.{ext}

        Args:
            tenant_id: Tenant UUID
            execution_id: Execution UUID
            version: Execution version number
            artifact_id: Artifact UUID
            file_extension: File extension (e.g., "json", "csv", "png")

        Returns:
            str: Storage path
        """
        # Remove leading dot from extension if present
        ext = file_extension.lstrip(".")

        path = f"{tenant_id}/{execution_id}/{version}/{artifact_id}.{ext}"
        return path


    def _detect_artifact_type(self, mime_type: str, file_extension: str) -> ArtifactType:
        """
        Classify artifact based on MIME type and extension.

        Args:
            mime_type: File MIME type
            file_extension: File extension

        Returns:
            ArtifactType: Classified artifact type
        """
        mime_lower = mime_type.lower()
        ext_lower = file_extension.lower().lstrip(".")

        # Document types
        if any(x in mime_lower for x in ["pdf", "word", "document", "text/plain"]):
            return ArtifactType.DOCUMENT
        if ext_lower in ["txt", "md", "doc", "docx", "pdf"]:
            return ArtifactType.DOCUMENT

        # Image types
        if "image/" in mime_lower:
            return ArtifactType.IMAGE
        if ext_lower in ["jpg", "jpeg", "png", "gif", "bmp", "svg", "webp"]:
            return ArtifactType.IMAGE

        # Data types
        if any(x in mime_lower for x in ["json", "csv", "xml", "yaml"]):
            return ArtifactType.DATA
        if ext_lower in ["json", "csv", "xml", "yaml", "yml", "xlsx", "parquet"]:
            return ArtifactType.DATA

        # Code types
        if any(x in mime_lower for x in ["python", "javascript", "text/x-"]):
            return ArtifactType.CODE
        if ext_lower in ["py", "js", "ts", "java", "cpp", "c", "go", "rs", "sh", "sql"]:
            return ArtifactType.CODE

        return ArtifactType.OTHER


    async def upload_file(
        self,
        db: Session,
        tenant_id: UUID,
        execution_id: UUID,
        version: int,
        file: BinaryIO,
        file_name: str,
        mime_type: Optional[str] = None
    ) -> Artifact:
        """
        Upload artifact file to storage backend.

        Args:
            db: Database session
            tenant_id: Tenant UUID
            execution_id: Execution UUID
            version: Execution version number
            file: File-like object (binary mode)
            file_name: Original file name
            mime_type: MIME type (auto-detected if None)

        Returns:
            Artifact: Created artifact record

        Raises:
            ValueError: If file validation fails
            Exception: If upload fails
        """
        # Extract file information
        file_extension = Path(file_name).suffix or ".bin"
        if mime_type is None:
            mime_type, _ = mimetypes.guess_type(file_name)
            if mime_type is None:
                mime_type = "application/octet-stream"

        # Get file size
        file.seek(0, os.SEEK_END)
        file_size_bytes = file.tell()
        file.seek(0)

        if file_size_bytes == 0:
            raise ValueError("Cannot upload empty file")

        # Create artifact record (without committing yet)
        from ..models.artifact import Artifact
        artifact = Artifact(
            tenant_id=tenant_id,
            execution_id=execution_id,
            execution_version=version,
            file_name=file_name,
            file_extension=file_extension,
            file_size_bytes=file_size_bytes,
            mime_type=mime_type,
            storage_path="",  # Will be set after ID is generated
            artifact_type=self._detect_artifact_type(mime_type, file_extension),
            has_preview=False,
            last_accessed_at=datetime.utcnow()
        )

        # Flush to get artifact ID
        db.add(artifact)
        db.flush()

        # Generate storage path
        storage_path = self._generate_storage_path(
            tenant_id=tenant_id,
            execution_id=execution_id,
            version=version,
            artifact_id=artifact.id,
            file_extension=file_extension
        )
        artifact.storage_path = storage_path

        # Upload to storage backend
        try:
            if self.storage_type == "s3":
                await self._upload_to_s3(storage_path, file, mime_type)
            else:
                await self._upload_to_local(storage_path, file)

            db.commit()
            logger.info(f"Uploaded artifact {artifact.id} to {storage_path} ({file_size_bytes} bytes)")
            return artifact

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to upload artifact: {e}")
            raise


    async def _upload_to_s3(self, storage_path: str, file: BinaryIO, mime_type: str):
        """Upload file to S3."""
        try:
            self.s3_client.upload_fileobj(
                file,
                self.bucket_name,
                storage_path,
                ExtraArgs={
                    "ContentType": mime_type,
                    "ServerSideEncryption": "AES256"
                }
            )
        except Exception as e:
            logger.error(f"S3 upload failed for {storage_path}: {e}")
            raise


    async def _upload_to_local(self, storage_path: str, file: BinaryIO):
        """Upload file to local filesystem."""
        try:
            local_path = self.local_storage_path / storage_path
            local_path.parent.mkdir(parents=True, exist_ok=True)

            with open(local_path, "wb") as dest:
                shutil.copyfileobj(file, dest)
        except Exception as e:
            logger.error(f"Local upload failed for {storage_path}: {e}")
            raise


    async def download_file(self, db: Session, artifact_id: UUID) -> str:
        """
        Generate download URL for artifact.

        For S3: Returns pre-signed URL
        For local: Returns file:// URL or HTTP endpoint URL

        Args:
            db: Database session
            artifact_id: Artifact UUID

        Returns:
            str: Download URL

        Raises:
            ValueError: If artifact not found
        """
        artifact = db.query(Artifact).filter(Artifact.id == artifact_id).first()
        if not artifact:
            raise ValueError(f"Artifact {artifact_id} not found")

        if artifact.deleted_at is not None:
            raise ValueError(f"Artifact {artifact_id} has been deleted")

        # Update last accessed timestamp
        artifact.last_accessed_at = datetime.utcnow()
        db.commit()

        # Generate download URL
        if self.storage_type == "s3":
            return self._generate_s3_presigned_url(artifact.storage_path)
        else:
            return self._generate_local_url(artifact.storage_path)


    def _generate_s3_presigned_url(self, storage_path: str) -> str:
        """Generate S3 pre-signed URL."""
        try:
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self.bucket_name,
                    "Key": storage_path
                },
                ExpiresIn=PRESIGNED_URL_EXPIRATION
            )
            return url
        except Exception as e:
            logger.error(f"Failed to generate pre-signed URL for {storage_path}: {e}")
            raise


    def _generate_local_url(self, storage_path: str) -> str:
        """
        Generate local file URL.

        Returns a path that can be served by the API endpoint.
        The actual file serving should be handled by the API layer.
        """
        # Return a relative URL that will be handled by the download endpoint
        # The API layer will serve the file from the local filesystem
        return f"/api/v1/artifacts/files/{storage_path}"


    async def delete_file(self, db: Session, artifact_id: UUID) -> bool:
        """
        Soft delete artifact (sets deleted_at timestamp).

        Hard deletion is handled by the cleanup worker after grace period.

        Args:
            db: Database session
            artifact_id: Artifact UUID

        Returns:
            bool: True if deleted successfully

        Raises:
            ValueError: If artifact not found
        """
        artifact = db.query(Artifact).filter(Artifact.id == artifact_id).first()
        if not artifact:
            raise ValueError(f"Artifact {artifact_id} not found")

        if artifact.deleted_at is not None:
            logger.warning(f"Artifact {artifact_id} already marked as deleted")
            return True

        artifact.deleted_at = datetime.utcnow()
        db.commit()
        logger.info(f"Soft deleted artifact {artifact_id}")
        return True


    async def hard_delete_file(self, db: Session, artifact_id: UUID) -> bool:
        """
        Permanently delete artifact from storage and database.

        Called by cleanup worker after grace period.

        Args:
            db: Database session
            artifact_id: Artifact UUID

        Returns:
            bool: True if deleted successfully
        """
        artifact = db.query(Artifact).filter(Artifact.id == artifact_id).first()
        if not artifact:
            logger.warning(f"Artifact {artifact_id} not found for hard deletion")
            return False

        # Delete from storage backend
        try:
            if self.storage_type == "s3":
                self.s3_client.delete_object(
                    Bucket=self.bucket_name,
                    Key=artifact.storage_path
                )
            else:
                local_path = self.local_storage_path / artifact.storage_path
                if local_path.exists():
                    local_path.unlink()

            # Delete database record
            db.delete(artifact)
            db.commit()
            logger.info(f"Hard deleted artifact {artifact_id} from storage and database")
            return True

        except Exception as e:
            logger.error(f"Failed to hard delete artifact {artifact_id}: {e}")
            db.rollback()
            raise


    async def get_local_file_path(self, artifact_id: UUID, db: Session) -> Path:
        """
        Get local filesystem path for artifact (local storage only).

        Used by preview generator and file serving endpoints.

        Args:
            artifact_id: Artifact UUID
            db: Database session

        Returns:
            Path: Local file path

        Raises:
            ValueError: If artifact not found or not using local storage
        """
        if self.storage_type != "local":
            raise ValueError("get_local_file_path only supported for local storage backend")

        artifact = db.query(Artifact).filter(Artifact.id == artifact_id).first()
        if not artifact:
            raise ValueError(f"Artifact {artifact_id} not found")

        local_path = self.local_storage_path / artifact.storage_path
        if not local_path.exists():
            raise ValueError(f"Artifact file not found at {local_path}")

        return local_path


# Singleton instance
_artifact_storage_service: Optional[ArtifactStorageService] = None


def get_artifact_storage_service() -> ArtifactStorageService:
    """Get or create singleton artifact storage service."""
    global _artifact_storage_service
    if _artifact_storage_service is None:
        _artifact_storage_service = ArtifactStorageService()
    return _artifact_storage_service
