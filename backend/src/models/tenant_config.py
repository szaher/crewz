"""TenantConfig model for per-tenant storage quotas and retention policies."""

import enum
from sqlalchemy import Column, Integer, BigInteger, ForeignKey, CheckConstraint, Index
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import relationship
from .base import BaseModel


class CleanupStrategy(str, enum.Enum):
    """Storage cleanup strategy when quota is exceeded."""

    OLDEST_FIRST = "oldest_first"  # Delete oldest artifacts first
    LARGEST_FIRST = "largest_first"  # Delete largest artifacts first
    LRU = "lru"  # Least Recently Used (based on last_accessed_at)
    BLOCK_UPLOADS = "block_uploads"  # Block new uploads until space is freed


class TenantConfig(BaseModel):
    """
    TenantConfig model for per-tenant storage quotas and retention policies.

    Configurable storage limits, cleanup strategies, and retention periods.
    Supports quota alerts and automatic cleanup policies.
    """

    __tablename__ = "tenant_configs"

    # Foreign key (one-to-one with Tenant)
    tenant_id = Column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
        unique=True,
        index=True
    )

    # Storage quotas
    total_storage_quota_bytes = Column(BigInteger, nullable=False)
    max_artifact_size_bytes = Column(BigInteger, nullable=False)
    current_storage_used_bytes = Column(BigInteger, nullable=False, default=0)

    # Retention policies (tier-based defaults)
    trace_retention_days = Column(Integer, nullable=False)  # Free: 7, Pro: 30, Enterprise: 90
    artifact_retention_days = Column(Integer, nullable=False)  # Free: 30, Pro: 90, Enterprise: 180

    # Cleanup policy
    cleanup_strategy = Column(
        postgresql.ENUM(CleanupStrategy, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=CleanupStrategy.LRU
    )

    # Quota alerts (as decimal percentages, e.g., 0.80 = 80%)
    quota_warning_threshold = Column(postgresql.NUMERIC(3, 2), nullable=False, default=0.80)
    quota_alert_threshold = Column(postgresql.NUMERIC(3, 2), nullable=False, default=0.95)

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])

    # Indexes and constraints
    __table_args__ = (
        Index("idx_tenant_config_tenant", "tenant_id"),

        # Constraints
        CheckConstraint(
            "current_storage_used_bytes <= total_storage_quota_bytes",
            name="chk_tenant_config_quota_not_exceeded"
        ),
        CheckConstraint(
            "max_artifact_size_bytes <= total_storage_quota_bytes",
            name="chk_tenant_config_max_size_valid"
        ),
        CheckConstraint(
            "trace_retention_days >= 1",
            name="chk_tenant_config_trace_retention_positive"
        ),
        CheckConstraint(
            "artifact_retention_days >= 1",
            name="chk_tenant_config_artifact_retention_positive"
        ),
        CheckConstraint(
            "quota_warning_threshold > 0 AND quota_warning_threshold < quota_alert_threshold AND quota_alert_threshold <= 1.0",
            name="chk_tenant_config_quota_thresholds_valid"
        ),
    )

    def __repr__(self):
        return (
            f"<TenantConfig(id={self.id}, tenant_id={self.tenant_id}, "
            f"quota={self.total_storage_quota_bytes}, used={self.current_storage_used_bytes})>"
        )
