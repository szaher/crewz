"""
Cleanup worker service for retention policies and storage quota enforcement.

Runs as Celery Beat periodic tasks to clean up expired data and enforce quotas.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from uuid import UUID

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from ..models.trace import Trace
from ..models.artifact import Artifact
from ..models.tenant_config import TenantConfig, CleanupStrategy
from ..services.artifact_storage import get_artifact_storage_service


logger = logging.getLogger(__name__)


class CleanupWorker:
    """
    Worker service for data retention and storage quota enforcement.

    Features:
    - Automatic trace deletion after retention period
    - Automatic artifact deletion after retention period
    - Storage quota enforcement with multiple cleanup strategies
    - Soft delete grace period (7 days) before hard deletion
    """

    # Grace period for soft-deleted artifacts (before hard deletion)
    SOFT_DELETE_GRACE_DAYS = 7

    def __init__(self, db: Session):
        """
        Initialize cleanup worker.

        Args:
            db: Database session
        """
        self.db = db
        self.storage_service = get_artifact_storage_service()


    def cleanup_expired_traces(self) -> Dict[str, Any]:
        """
        Delete traces older than tenant-specific retention period.

        Runs as Celery Beat task every 6 hours.

        Returns:
            Dict with cleanup statistics
        """
        logger.info("Starting expired traces cleanup")
        stats = {"tenants_processed": 0, "traces_deleted": 0}

        # Get all tenant configs
        tenant_configs = self.db.query(TenantConfig).all()

        for config in tenant_configs:
            # Calculate expiration date
            expiration_date = datetime.utcnow() - timedelta(days=config.trace_retention_days)

            # Query expired traces
            expired_traces = self.db.query(Trace).filter(
                and_(
                    Trace.tenant_id == config.tenant_id,
                    Trace.created_at < expiration_date
                )
            ).all()

            # Delete expired traces
            deleted_count = 0
            for trace in expired_traces:
                self.db.delete(trace)
                deleted_count += 1

            if deleted_count > 0:
                self.db.commit()
                logger.info(
                    f"Deleted {deleted_count} expired traces for tenant {config.tenant_id} "
                    f"(retention: {config.trace_retention_days} days)"
                )

            stats["tenants_processed"] += 1
            stats["traces_deleted"] += deleted_count

        logger.info(
            f"Expired traces cleanup completed: "
            f"{stats['traces_deleted']} traces deleted across {stats['tenants_processed']} tenants"
        )

        return stats


    def cleanup_expired_artifacts(self) -> Dict[str, Any]:
        """
        Delete artifacts older than tenant-specific retention period.

        Runs as Celery Beat task every 6 hours.

        Returns:
            Dict with cleanup statistics
        """
        logger.info("Starting expired artifacts cleanup")
        stats = {"tenants_processed": 0, "artifacts_deleted": 0, "bytes_freed": 0}

        # Get all tenant configs
        tenant_configs = self.db.query(TenantConfig).all()

        for config in tenant_configs:
            # Calculate expiration date
            expiration_date = datetime.utcnow() - timedelta(days=config.artifact_retention_days)

            # Query expired artifacts (not soft-deleted, just old)
            expired_artifacts = self.db.query(Artifact).filter(
                and_(
                    Artifact.tenant_id == config.tenant_id,
                    Artifact.created_at < expiration_date,
                    Artifact.deleted_at.is_(None)  # Not already soft-deleted
                )
            ).all()

            # Soft delete expired artifacts
            deleted_count = 0
            for artifact in expired_artifacts:
                artifact.deleted_at = datetime.utcnow()
                stats["bytes_freed"] += artifact.file_size_bytes
                deleted_count += 1

            if deleted_count > 0:
                self.db.commit()
                logger.info(
                    f"Soft deleted {deleted_count} expired artifacts for tenant {config.tenant_id} "
                    f"(retention: {config.artifact_retention_days} days)"
                )

            stats["tenants_processed"] += 1
            stats["artifacts_deleted"] += deleted_count

        # Hard delete artifacts past grace period
        self._hard_delete_old_soft_deleted_artifacts(stats)

        logger.info(
            f"Expired artifacts cleanup completed: "
            f"{stats['artifacts_deleted']} artifacts deleted, "
            f"{stats['bytes_freed']} bytes freed across {stats['tenants_processed']} tenants"
        )

        return stats


    def _hard_delete_old_soft_deleted_artifacts(self, stats: Dict[str, Any]):
        """
        Permanently delete artifacts that have been soft-deleted for > grace period.

        Args:
            stats: Stats dict to update
        """
        grace_cutoff = datetime.utcnow() - timedelta(days=self.SOFT_DELETE_GRACE_DAYS)

        # Query soft-deleted artifacts past grace period
        old_soft_deleted = self.db.query(Artifact).filter(
            and_(
                Artifact.deleted_at.isnot(None),
                Artifact.deleted_at < grace_cutoff
            )
        ).all()

        hard_deleted_count = 0
        for artifact in old_soft_deleted:
            try:
                # Hard delete from storage and database
                self.storage_service.hard_delete_file(self.db, artifact.id)
                hard_deleted_count += 1
            except Exception as e:
                logger.error(f"Failed to hard delete artifact {artifact.id}: {e}")

        if hard_deleted_count > 0:
            logger.info(
                f"Hard deleted {hard_deleted_count} artifacts past "
                f"{self.SOFT_DELETE_GRACE_DAYS}-day grace period"
            )

        stats["hard_deleted"] = hard_deleted_count


    def enforce_storage_quota(self) -> Dict[str, Any]:
        """
        Enforce storage quotas for tenants using configured cleanup strategy.

        Runs as Celery Beat task every 1 hour.

        Returns:
            Dict with enforcement statistics
        """
        logger.info("Starting storage quota enforcement")
        stats = {"tenants_checked": 0, "tenants_over_quota": 0, "artifacts_cleaned": 0, "bytes_freed": 0}

        # Get all tenant configs
        tenant_configs = self.db.query(TenantConfig).all()

        for config in tenant_configs:
            stats["tenants_checked"] += 1

            # Calculate current storage usage
            current_usage = self.db.query(func.sum(Artifact.file_size_bytes)).filter(
                and_(
                    Artifact.tenant_id == config.tenant_id,
                    Artifact.deleted_at.is_(None)
                )
            ).scalar() or 0

            # Update config with current usage
            config.current_storage_used_bytes = current_usage
            self.db.commit()

            # Check if over quota
            if current_usage > config.total_storage_quota_bytes:
                logger.warning(
                    f"Tenant {config.tenant_id} over quota: "
                    f"{current_usage} / {config.total_storage_quota_bytes} bytes"
                )
                stats["tenants_over_quota"] += 1

                # Calculate how much to free
                bytes_to_free = current_usage - config.total_storage_quota_bytes

                # Apply cleanup strategy
                cleanup_result = self._apply_cleanup_strategy(config, bytes_to_free)
                stats["artifacts_cleaned"] += cleanup_result["artifacts_deleted"]
                stats["bytes_freed"] += cleanup_result["bytes_freed"]

        logger.info(
            f"Storage quota enforcement completed: "
            f"{stats['tenants_over_quota']} tenants over quota, "
            f"{stats['artifacts_cleaned']} artifacts cleaned, "
            f"{stats['bytes_freed']} bytes freed"
        )

        return stats


    def _apply_cleanup_strategy(
        self,
        config: TenantConfig,
        bytes_to_free: int
    ) -> Dict[str, Any]:
        """
        Apply tenant's cleanup strategy to free storage space.

        Args:
            config: Tenant configuration
            bytes_to_free: Number of bytes to free

        Returns:
            Dict with cleanup statistics
        """
        stats = {"artifacts_deleted": 0, "bytes_freed": 0}

        if config.cleanup_strategy == CleanupStrategy.BLOCK_UPLOADS:
            # Don't delete anything, just block uploads
            logger.info(f"Tenant {config.tenant_id} using BLOCK_UPLOADS strategy - no cleanup")
            return stats

        # Get candidates for deletion (not soft-deleted)
        query = self.db.query(Artifact).filter(
            and_(
                Artifact.tenant_id == config.tenant_id,
                Artifact.deleted_at.is_(None)
            )
        )

        # Apply sorting based on strategy
        if config.cleanup_strategy == CleanupStrategy.OLDEST_FIRST:
            query = query.order_by(Artifact.created_at.asc())

        elif config.cleanup_strategy == CleanupStrategy.LARGEST_FIRST:
            query = query.order_by(Artifact.file_size_bytes.desc())

        elif config.cleanup_strategy == CleanupStrategy.LRU:
            # Least Recently Used (last_accessed_at)
            query = query.order_by(Artifact.last_accessed_at.asc().nulls_first())

        else:
            logger.warning(f"Unknown cleanup strategy: {config.cleanup_strategy}, using OLDEST_FIRST")
            query = query.order_by(Artifact.created_at.asc())

        # Delete artifacts until quota is met
        candidates = query.all()
        bytes_freed = 0

        for artifact in candidates:
            if bytes_freed >= bytes_to_free:
                break

            # Soft delete artifact
            artifact.deleted_at = datetime.utcnow()
            bytes_freed += artifact.file_size_bytes
            stats["artifacts_deleted"] += 1

            logger.debug(
                f"Soft deleted artifact {artifact.id} ({artifact.file_size_bytes} bytes) "
                f"using {config.cleanup_strategy.value} strategy"
            )

        if stats["artifacts_deleted"] > 0:
            self.db.commit()
            stats["bytes_freed"] = bytes_freed

            logger.info(
                f"Applied {config.cleanup_strategy.value} cleanup for tenant {config.tenant_id}: "
                f"{stats['artifacts_deleted']} artifacts deleted, {bytes_freed} bytes freed"
            )

        return stats


    def check_quota_alerts(self) -> Dict[str, Any]:
        """
        Check storage quotas and generate alerts for tenants approaching limits.

        Returns:
            Dict with alert statistics
        """
        stats = {"tenants_checked": 0, "warning_alerts": 0, "critical_alerts": 0}

        # Get all tenant configs
        tenant_configs = self.db.query(TenantConfig).all()

        for config in tenant_configs:
            stats["tenants_checked"] += 1

            # Calculate current storage usage
            current_usage = self.db.query(func.sum(Artifact.file_size_bytes)).filter(
                and_(
                    Artifact.tenant_id == config.tenant_id,
                    Artifact.deleted_at.is_(None)
                )
            ).scalar() or 0

            usage_percentage = current_usage / config.total_storage_quota_bytes if config.total_storage_quota_bytes > 0 else 0

            # Check thresholds
            if usage_percentage >= float(config.quota_alert_threshold):
                logger.warning(
                    f"CRITICAL: Tenant {config.tenant_id} at {usage_percentage * 100:.1f}% storage "
                    f"({current_usage} / {config.total_storage_quota_bytes} bytes)"
                )
                stats["critical_alerts"] += 1
                # TODO: Send notification to tenant

            elif usage_percentage >= float(config.quota_warning_threshold):
                logger.warning(
                    f"WARNING: Tenant {config.tenant_id} at {usage_percentage * 100:.1f}% storage "
                    f"({current_usage} / {config.total_storage_quota_bytes} bytes)"
                )
                stats["warning_alerts"] += 1
                # TODO: Send notification to tenant

        return stats


    def get_cleanup_statistics(self, tenant_id: UUID) -> Dict[str, Any]:
        """
        Get cleanup statistics for a tenant.

        Args:
            tenant_id: Tenant UUID

        Returns:
            Dict with statistics
        """
        config = self.db.query(TenantConfig).filter(
            TenantConfig.tenant_id == tenant_id
        ).first()

        if not config:
            raise ValueError(f"No config found for tenant {tenant_id}")

        # Current storage usage
        current_usage = self.db.query(func.sum(Artifact.file_size_bytes)).filter(
            and_(
                Artifact.tenant_id == tenant_id,
                Artifact.deleted_at.is_(None)
            )
        ).scalar() or 0

        # Soft deleted artifacts (pending hard deletion)
        soft_deleted_count = self.db.query(func.count(Artifact.id)).filter(
            and_(
                Artifact.tenant_id == tenant_id,
                Artifact.deleted_at.isnot(None)
            )
        ).scalar() or 0

        soft_deleted_bytes = self.db.query(func.sum(Artifact.file_size_bytes)).filter(
            and_(
                Artifact.tenant_id == tenant_id,
                Artifact.deleted_at.isnot(None)
            )
        ).scalar() or 0

        # Expired traces count
        trace_expiration = datetime.utcnow() - timedelta(days=config.trace_retention_days)
        expired_traces_count = self.db.query(func.count(Trace.id)).filter(
            and_(
                Trace.tenant_id == tenant_id,
                Trace.created_at < trace_expiration
            )
        ).scalar() or 0

        # Expired artifacts count
        artifact_expiration = datetime.utcnow() - timedelta(days=config.artifact_retention_days)
        expired_artifacts_count = self.db.query(func.count(Artifact.id)).filter(
            and_(
                Artifact.tenant_id == tenant_id,
                Artifact.created_at < artifact_expiration,
                Artifact.deleted_at.is_(None)
            )
        ).scalar() or 0

        usage_percentage = current_usage / config.total_storage_quota_bytes if config.total_storage_quota_bytes > 0 else 0

        return {
            "tenant_id": str(tenant_id),
            "current_storage_used_bytes": current_usage,
            "total_storage_quota_bytes": config.total_storage_quota_bytes,
            "usage_percentage": round(usage_percentage * 100, 2),
            "cleanup_strategy": config.cleanup_strategy.value,
            "trace_retention_days": config.trace_retention_days,
            "artifact_retention_days": config.artifact_retention_days,
            "soft_deleted_artifacts": {
                "count": soft_deleted_count,
                "bytes": soft_deleted_bytes,
                "grace_period_days": self.SOFT_DELETE_GRACE_DAYS
            },
            "expired_traces_pending_cleanup": expired_traces_count,
            "expired_artifacts_pending_cleanup": expired_artifacts_count,
            "is_over_warning_threshold": usage_percentage >= float(config.quota_warning_threshold),
            "is_over_alert_threshold": usage_percentage >= float(config.quota_alert_threshold),
            "is_over_quota": current_usage > config.total_storage_quota_bytes
        }


# Service factory function
def get_cleanup_worker(db: Session) -> CleanupWorker:
    """Create cleanup worker instance."""
    return CleanupWorker(db)
