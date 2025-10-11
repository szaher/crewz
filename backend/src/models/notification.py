"""Notification model for user in-app alerts."""

from sqlalchemy import Column, Integer, String, JSON, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from .base import BaseModel


class Notification(BaseModel):
    __tablename__ = "notifications"

    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Basic contents
    type = Column(String(50), nullable=False, default="info")
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=True)
    data = Column(JSON, nullable=True)

    # Read state
    is_read = Column(Boolean, nullable=False, default=False)
    read_at = Column(DateTime, nullable=True)

    # Relationships (optional, not strictly needed)
    # user = relationship("User")
    # tenant = relationship("Tenant")

    def mark_read(self):
        self.is_read = True
        self.read_at = datetime.utcnow()

