"""Permission model for fine-grained authorization."""

from sqlalchemy import Column, String, Enum, ForeignKey, Index
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import relationship
import enum

from .base import BaseModel


class SubjectType(str, enum.Enum):
    """Subject type for permissions."""
    USER = "user"
    ROLE = "role"


class Action(str, enum.Enum):
    """Allowed actions for permissions."""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    DELETE = "delete"
    ALL = "*"


class Effect(str, enum.Enum):
    """Permission effect."""
    ALLOW = "allow"
    DENY = "deny"


class Permission(BaseModel):
    """
    Permission model for fine-grained access control.

    Represents a permission grant for a subject (user or role) on a resource.
    Supports both RBAC (role-based) and ABAC (attribute-based) access control.
    """

    __tablename__ = "permissions"

    # Tenant isolation
    tenant_id = Column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Subject (who)
    subject_type = Column(
        Enum(SubjectType),
        nullable=False,
    )
    subject_id = Column(
        postgresql.UUID(as_uuid=True),
        nullable=False,
    )

    # Resource (what)
    resource_type = Column(
        String(50),
        nullable=False,
    )
    resource_id = Column(
        postgresql.UUID(as_uuid=True),
        nullable=True,  # NULL means applies to all resources of this type
    )

    # Action (how)
    action = Column(
        Enum(Action),
        nullable=False,
    )

    # Effect (allow/deny)
    effect = Column(
        Enum(Effect),
        nullable=False,
        default=Effect.ALLOW,
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
    tenant = relationship("Tenant", back_populates="permissions")
    creator = relationship("User", foreign_keys=[created_by])

    # Indexes
    __table_args__ = (
        Index("idx_permissions_subject", "subject_type", "subject_id"),
        Index("idx_permissions_resource", "resource_type", "resource_id"),
        Index("idx_permissions_tenant", "tenant_id"),
        # Prevent duplicate permissions
        # Note: Use COALESCE for nullable resource_id
        # This will be added in the Alembic migration with proper SQL
    )

    def __repr__(self):
        return (
            f"<Permission {self.subject_type}:{self.subject_id} "
            f"{self.action} {self.resource_type}:{self.resource_id or '*'} "
            f"effect={self.effect}>"
        )
