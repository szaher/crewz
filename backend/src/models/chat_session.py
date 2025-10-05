"""Chat session model for conversational AI interactions."""

from sqlalchemy import Column, String, Text, Integer, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from .base import BaseModel


class ChatSession(BaseModel):
    """
    Chat session model for multi-turn conversations.

    Chat messages are stored in MongoDB, this tracks session metadata.
    """

    __tablename__ = "chat_sessions"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=True)

    # LLM configuration for this session
    llm_provider_id = Column(
        Integer, ForeignKey("llm_providers.id"), nullable=False, index=True
    )
    system_prompt = Column(Text, nullable=True)

    # Session state
    is_active = Column(Boolean, nullable=False, default=True)

    # MongoDB reference for messages
    mongo_messages_collection = Column(String(255), nullable=True)

    # Relationships
    user = relationship("User", back_populates="chat_sessions")
    llm_provider = relationship("LLMProvider")

    def __repr__(self):
        return f"<ChatSession(id={self.id}, user_id={self.user_id}, active={self.is_active})>"
