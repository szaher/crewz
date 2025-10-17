"""Policy model for authorization."""

from sqlalchemy import Column, String, Enum, ForeignKey, Index, Text, Integer, Boolean
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import relationship
import enum

from .base import BaseModel


class PolicyScope(str, enum.Enum):
    """Scope for policies."""
    TENANT = "tenant"
    USER = "user"


class Effect(str, enum.Enum):
    """Policy effect."""
    ALLOW = "allow"
    DENY = "deny"


class Policy(BaseModel):
    """
    Policy model for tenant-level or user-level authorization rules.

    Supports pattern matching for resource and action authorization with
    priority-based evaluation.
    """

    __tablename__ = "policies"

    # Tenant isolation
    tenant_id = Column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Policy scope
    scope = Column(
        Enum(PolicyScope),
        nullable=False,
    )
    scope_id = Column(
        postgresql.UUID(as_uuid=True),
        nullable=True,  # NULL for tenant scope, user ID for user scope
    )

    # Policy identification
    name = Column(
        String(100),
        nullable=False,
    )
    description = Column(
        Text,
        nullable=True,
    )

    # Pattern matching
    resource_pattern = Column(
        String(100),
        nullable=False,
    )
    action_pattern = Column(
        String(50),
        nullable=False,
    )

    # Effect and priority
    effect = Column(
        Enum(Effect),
        nullable=False,
    )
    priority = Column(
        Integer,
        nullable=False,
        default=0,
    )

    # Policy state
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    # Conditions for ABAC (attribute-based access control)
    conditions = Column(
        postgresql.JSONB,
        nullable=True,
    )

    # Audit fields
    created_by = Column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    tenant = relationship("Tenant", back_populates="policies")
    creator = relationship("User", foreign_keys=[created_by])

    # Indexes
    __table_args__ = (
        Index("idx_policies_tenant", "tenant_id"),
        Index("idx_policies_scope", "scope", "scope_id"),
        Index("idx_policies_active", "is_active"),
    )

    def __repr__(self):
        return (
            f"<Policy {self.name} "
            f"pattern={self.resource_pattern}:{self.action_pattern} "
            f"effect={self.effect} priority={self.priority}>"
        )
