"""Artifact service for managing execution output files with S3/MinIO storage.

Handles upload, versioning, presigned URL generation, and cleanup of expired artifacts.
"""
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from src.models.execution_artifact import ExecutionArtifact, ArtifactType
from src.config.worker_config import WorkerConfig


class ArtifactService:
    """Service for managing execution artifacts."""

    def __init__(self, db_session: Session, s3_client=None):
        """
        Initialize artifact service.

        Args:
            db_session: SQLAlchemy database session
            s3_client: Boto3 S3 client (injected for testing)
        """
        self.db = db_session
        self.s3_client = s3_client

        if not s3_client:
            try:
                import boto3
                self.s3_client = boto3.client('s3')
            except ImportError:
                # S3 client will be None if boto3 not available
                pass

    def upload_to_s3(
        self,
        file_path: str,
        bucket_name: str,
        object_key: str
    ) -> str:
        """
        Upload file to S3/MinIO.

        Args:
            file_path: Local file path
            bucket_name: S3 bucket name
            object_key: S3 object key

        Returns:
            S3 URI (s3://bucket/key)

        Raises:
            Exception: If upload fails
        """
        if not self.s3_client:
            raise Exception("S3 client not configured")

        self.s3_client.upload_file(file_path, bucket_name, object_key)
        return f"s3://{bucket_name}/{object_key}"

    def create_artifact_record(
        self,
        execution_id: UUID,
        tenant_id: UUID,
        file_name: str,
        file_size: int,
        file_path: str,
        artifact_type: ArtifactType = ArtifactType.OUTPUT_FILE,
        mime_type: str = None,
        version_number: int = 1,
        retention_days: int = None
    ) -> ExecutionArtifact:
        """
        Create artifact metadata record with versioning.

        Args:
            execution_id: Execution UUID
            tenant_id: Tenant UUID
            file_name: Original filename
            file_size: File size in bytes
            file_path: S3 path
            artifact_type: Type of artifact
            mime_type: MIME type
            version_number: Artifact version
            retention_days: Days to retain (default from WorkerConfig)

        Returns:
            ExecutionArtifact object
        """
        if retention_days is None:
            retention_days = WorkerConfig.ARTIFACT_RETENTION_DAYS

        artifact = ExecutionArtifact(
            execution_id=execution_id,
            tenant_id=tenant_id,
            file_name=file_name,
            file_size=file_size,
            file_path=file_path,
            artifact_type=artifact_type,
            mime_type=mime_type,
            version_number=version_number,
            expires_at=ExecutionArtifact.calculate_expiration(retention_days)
        )

        self.db.add(artifact)
        self.db.commit()
        self.db.refresh(artifact)
        return artifact

    def generate_presigned_url(
        self,
        artifact_id: UUID,
        expiration_seconds: int = 3600
    ) -> Optional[str]:
        """
        Generate presigned URL for artifact download (1 hour expiry per spec).

        Args:
            artifact_id: Artifact UUID
            expiration_seconds: URL expiration time (default 3600s = 1 hour)

        Returns:
            Presigned URL or None if artifact not found
        """
        artifact = self.db.query(ExecutionArtifact).filter(
            ExecutionArtifact.id == artifact_id
        ).first()

        if not artifact:
            return None

        if not self.s3_client:
            # Fallback to file path if S3 not configured
            return artifact.file_path

        # Extract bucket and key from S3 path
        s3_key = artifact.get_download_key()

        # Parse bucket from file_path (format: s3://bucket/key)
        if artifact.file_path.startswith("s3://"):
            parts = artifact.file_path.split("/", 3)
            bucket_name = parts[2] if len(parts) > 2 else "artifacts"
        else:
            bucket_name = "artifacts"  # Default bucket

        try:
            presigned_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket_name, 'Key': s3_key},
                ExpiresIn=expiration_seconds
            )
            return presigned_url
        except Exception as e:
            # Fallback to file path if presigned URL generation fails
            return artifact.file_path

    def get_execution_artifacts(
        self,
        execution_id: UUID,
        version_number: int = None
    ) -> List[ExecutionArtifact]:
        """
        Get all artifacts for an execution.

        Args:
            execution_id: Execution UUID
            version_number: Specific version (optional)

        Returns:
            List of ExecutionArtifact objects
        """
        query = self.db.query(ExecutionArtifact).filter(
            ExecutionArtifact.execution_id == execution_id
        )

        if version_number is not None:
            query = query.filter(ExecutionArtifact.version_number == version_number)

        return query.order_by(ExecutionArtifact.created_at.desc()).all()

    def get_artifact_by_id(self, artifact_id: UUID) -> Optional[ExecutionArtifact]:
        """
        Get artifact by ID.

        Args:
            artifact_id: Artifact UUID

        Returns:
            ExecutionArtifact or None
        """
        return self.db.query(ExecutionArtifact).filter(
            ExecutionArtifact.id == artifact_id
        ).first()

    def cleanup_expired_artifacts(self) -> int:
        """
        Delete expired artifacts (Celery beat task).

        Returns:
            Number of artifacts deleted
        """
        expired_artifacts = self.db.query(ExecutionArtifact).filter(
            ExecutionArtifact.expires_at <= datetime.utcnow()
        ).all()

        deleted_count = 0
        for artifact in expired_artifacts:
            # Delete from S3
            if self.s3_client and artifact.file_path.startswith("s3://"):
                try:
                    s3_key = artifact.get_download_key()
                    parts = artifact.file_path.split("/", 3)
                    bucket_name = parts[2] if len(parts) > 2 else "artifacts"

                    self.s3_client.delete_object(Bucket=bucket_name, Key=s3_key)
                except Exception:
                    pass  # Continue even if S3 deletion fails

            # Delete from database
            self.db.delete(artifact)
            deleted_count += 1

        if deleted_count > 0:
            self.db.commit()

        return deleted_count

    def get_artifacts_by_tenant(
        self,
        tenant_id: UUID,
        limit: int = 100
    ) -> List[ExecutionArtifact]:
        """
        Get artifacts for a tenant.

        Args:
            tenant_id: Tenant UUID
            limit: Maximum artifacts to return

        Returns:
            List of ExecutionArtifact objects
        """
        return self.db.query(ExecutionArtifact).filter(
            ExecutionArtifact.tenant_id == tenant_id
        ).order_by(ExecutionArtifact.created_at.desc()).limit(limit).all()

    def get_artifact_versions(
        self,
        execution_id: UUID,
        file_name: str
    ) -> List[ExecutionArtifact]:
        """
        Get all versions of a specific artifact file.

        Args:
            execution_id: Execution UUID
            file_name: Artifact filename

        Returns:
            List of ExecutionArtifact objects ordered by version
        """
        return self.db.query(ExecutionArtifact).filter(
            ExecutionArtifact.execution_id == execution_id,
            ExecutionArtifact.file_name == file_name
        ).order_by(ExecutionArtifact.version_number.desc()).all()

    def save_output_artifact(
        self,
        execution_id: UUID,
        tenant_id: UUID,
        output_data: any,
        artifact_type: ArtifactType = ArtifactType.RESULT_JSON,
        version_number: int = 1
    ) -> ExecutionArtifact:
        """
        Save execution output as an artifact (in-memory, no S3 upload).

        Stores the output in the file_path field as a local path for now.
        In production, this would upload to S3/MinIO.

        Args:
            execution_id: Execution UUID
            tenant_id: Tenant UUID
            output_data: Output data to save (dict, str, etc.)
            artifact_type: Type of artifact
            version_number: Version number

        Returns:
            Created ExecutionArtifact
        """
        import json
        import tempfile
        import os

        # Convert output to JSON string
        if isinstance(output_data, dict):
            output_str = json.dumps(output_data, indent=2)
            mime_type = "application/json"
            file_name = "output.json"
        else:
            output_str = str(output_data)
            mime_type = "text/plain"
            file_name = "output.txt"

        # For now, save to a temp location (in production, upload to S3)
        # This allows the system to work without S3 configuration
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, f"artifacts/{tenant_id}/{execution_id}")
        os.makedirs(file_path, exist_ok=True)

        full_path = os.path.join(file_path, f"v{version_number}_{file_name}")

        # Write output to file
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(output_str)

        file_size = len(output_str.encode('utf-8'))

        # Create artifact record
        artifact = self.create_artifact_record(
            execution_id=execution_id,
            tenant_id=tenant_id,
            file_name=file_name,
            file_size=file_size,
            file_path=full_path,
            artifact_type=artifact_type,
            mime_type=mime_type,
            version_number=version_number
        )

        return artifact
