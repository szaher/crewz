"""User model for authentication and authorization."""

from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, Enum, DateTime
from sqlalchemy.orm import relationship, deferred
from .base import BaseModel
import enum
from datetime import datetime


class UserRole(str, enum.Enum):
    """User role enumeration."""

    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class User(BaseModel):
    """
    User model with tenant association.

    Users belong to a single tenant and have role-based permissions.
    """

    __tablename__ = "users"

    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.MEMBER)
    is_active = Column(Boolean, nullable=False, default=True)
    # Invitation / password reset
    password_reset_token = deferred(Column(String(255), nullable=True))
    password_reset_expires = deferred(Column(DateTime, nullable=True))
    require_password_change = deferred(Column(Boolean, nullable=False, default=False))

    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    chat_sessions = relationship(
        "ChatSession", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
