"""User-Role association table for many-to-many relationship."""

from sqlalchemy import Column, ForeignKey, Table, Index, DateTime
from sqlalchemy.dialects import postgresql
from datetime import datetime

from .base import Base


# Many-to-many association table for User <-> Role
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column(
        "user_id",
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    Column(
        "role_id",
        postgresql.UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    Column(
        "assigned_by",
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    ),
    Column(
        "assigned_at",
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    ),
    Index("idx_user_roles_user", "user_id"),
    Index("idx_user_roles_role", "role_id"),
)
