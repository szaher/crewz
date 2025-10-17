"""Chat folder model for organizing chat sessions."""

from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import relationship
from .base import BaseModel


class ChatFolder(BaseModel):
    """Folders owned by a user to organize chat sessions."""

    __tablename__ = "chat_folders"

    tenant_id = Column(postgresql.UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    user_id = Column(postgresql.UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)

    # Relationships
    sessions = relationship("ChatSession", back_populates="folder")

    def __repr__(self):
        return f"<ChatFolder(id={self.id}, name={self.name})>"

