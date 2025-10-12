"""Authorization audit log model for compliance and debugging."""

from sqlalchemy import Column, String, Enum, ForeignKey, Index, Text, Integer, DateTime
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from .base import Base


class AuditDecision(str, enum.Enum):
    """Authorization decision."""
    ALLOW = "allow"
    DENY = "deny"


class AuthorizationAuditLog(Base):
    """
    Authorization audit log model.

    Records all authorization checks for compliance and debugging.
    Uses partitioning by timestamp for efficient archival.
    """

    __tablename__ = "authorization_audit_logs"

    # Primary key
    id = Column(
        postgresql.UUID(as_uuid=True),
        primary_key=True,
    )

    # Tenant isolation
    tenant_id = Column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # User making request
    user_id = Column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Resource being accessed
    resource_type = Column(
        String(50),
        nullable=False,
    )
    resource_id = Column(
        postgresql.UUID(as_uuid=True),
        nullable=True,  # NULL if not specific resource
    )

    # Action attempted
    action = Column(
        String(50),
        nullable=False,
    )

    # Authorization decision
    decision = Column(
        Enum(AuditDecision),
        nullable=False,
        index=True,
    )

    # Decision reason
    reason = Column(
        Text,
        nullable=False,
    )

    # Performance metrics
    latency_ms = Column(
        Integer,
        nullable=False,
    )

    # Request metadata
    ip_address = Column(
        postgresql.INET,
        nullable=True,
    )
    user_agent = Column(
        Text,
        nullable=True,
    )

    # Timestamp (for partitioning)
    timestamp = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )

    # Relationships
    tenant = relationship("Tenant")
    user = relationship("User")

    # Indexes
    __table_args__ = (
        Index("idx_authz_audit_tenant", "tenant_id"),
        Index("idx_authz_audit_user", "user_id"),
        Index("idx_authz_audit_timestamp", "timestamp", postgresql_using="btree", postgresql_ops={"timestamp": "DESC"}),
        Index("idx_authz_audit_decision", "decision"),
    )

    def __repr__(self):
        return (
            f"<AuthorizationAuditLog user={self.user_id} "
            f"resource={self.resource_type}:{self.resource_id} "
            f"action={self.action} decision={self.decision}>"
        )
