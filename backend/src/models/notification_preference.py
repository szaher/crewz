"""NotificationPreference model for managing user and tenant notification settings."""

from sqlalchemy import Column, String, Boolean, ForeignKey, DateTime, Enum as SQLAEnum, UniqueConstraint, ARRAY
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from .base import BaseModel


class PreferenceScope(str, enum.Enum):
    """Scope of the notification preference (tenant-level or user-level)."""
    TENANT = "tenant"
    USER = "user"


class NotificationPreference(BaseModel):
    """
    Notification preferences at tenant or user level.

    Controls which notification categories are enabled and through which
    delivery channels (websocket, email, webhook).

    Tenant-level preferences serve as defaults for all users in the tenant.
    User-level preferences override tenant defaults.
    """
    __tablename__ = "notification_preferences"

    # Scope (tenant or user level)
    scope = Column(SQLAEnum(PreferenceScope), nullable=False, index=True)
    scope_id = Column(postgresql.UUID(as_uuid=True), nullable=False, index=True)

    # Notification category (e.g., "execution_update", "execution_failed", "execution_completed")
    category = Column(String(100), nullable=False, index=True)

    # Whether this category is enabled
    enabled = Column(Boolean, nullable=False, default=True)

    # Delivery channels (array of: websocket, email, webhook)
    delivery_channels = Column(ARRAY(String), nullable=False, default=list)

    # Timestamps
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Unique constraint: one preference per (scope, scope_id, category)
    __table_args__ = (
        UniqueConstraint('scope', 'scope_id', 'category', name='uq_notification_preference_scope_category'),
    )

    # Polymorphic relationships (optional - can be added if needed)
    # tenant = relationship("Tenant", foreign_keys=[scope_id], primaryjoin="and_(NotificationPreference.scope=='tenant', NotificationPreference.scope_id==Tenant.id)")
    # user = relationship("User", foreign_keys=[scope_id], primaryjoin="and_(NotificationPreference.scope=='user', NotificationPreference.scope_id==User.id)")

    def __repr__(self):
        return f"<NotificationPreference(scope={self.scope}, scope_id={self.scope_id}, category={self.category}, enabled={self.enabled})>"
