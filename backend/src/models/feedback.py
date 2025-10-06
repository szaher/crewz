"""Feedback model for user feedback on executions and agents."""

from sqlalchemy import Column, String, Text, Integer, Float, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
from .base import BaseModel
import enum


class FeedbackType(str, enum.Enum):
    """Feedback type enumeration."""
    EXECUTION = "execution"  # Feedback on flow execution
    AGENT = "agent"  # Feedback on agent performance
    CHAT = "chat"  # Feedback on chat interaction
    GENERAL = "general"  # General platform feedback


class SentimentType(str, enum.Enum):
    """Sentiment analysis result."""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class Feedback(BaseModel):
    """
    Feedback model for capturing user feedback on executions, agents, and chat.

    Stored in PostgreSQL for transactional queries.
    Synced to ClickHouse for analytics and aggregation.
    """

    __tablename__ = "feedback"

    # Tenant and user
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Feedback type and target
    feedback_type = Column(String(20), nullable=False, index=True)  # FeedbackType enum values
    execution_id = Column(Integer, ForeignKey("executions.id"), nullable=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True, index=True)
    chat_session_id = Column(String(255), nullable=True, index=True)  # MongoDB ID

    # Rating (1-5 stars)
    rating = Column(Integer, nullable=False)  # 1-5

    # Text feedback
    comment = Column(Text, nullable=True)

    # Sentiment analysis (computed)
    sentiment = Column(String(20), nullable=True, index=True)  # SentimentType enum values
    sentiment_score = Column(Float, nullable=True)  # -1.0 to 1.0

    # Tags for categorization
    tags = Column(JSON, nullable=False, default=list)  # ["bug", "performance", "accuracy"]

    # Extra data (renamed from metadata to avoid SQLAlchemy conflict)
    extra_data = Column(JSON, nullable=False, default=dict)  # Additional context

    # Relationships
    tenant = relationship("Tenant")
    user = relationship("User")
    execution = relationship("Execution", foreign_keys=[execution_id])
    agent = relationship("Agent", foreign_keys=[agent_id])

    def __repr__(self):
        return f"<Feedback(id={self.id}, type={self.feedback_type}, rating={self.rating})>"
