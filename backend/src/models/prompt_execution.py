"""Prompt execution model for tracking usage."""

from sqlalchemy import Column, String, Text, Boolean, Integer, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from .base import Base
import uuid
from datetime import datetime


class PromptExecution(Base):
    """Detailed tracking of prompt executions."""

    __tablename__ = "prompt_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prompt_id = Column(UUID(as_uuid=True), ForeignKey("prompt_templates.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)

    # Execution context
    context_type = Column(String(50), nullable=False)  # 'chat', 'task', 'direct', 'command'
    context_id = Column(UUID(as_uuid=True), nullable=True)  # Reference ID

    # Execution details
    variables_used = Column(JSONB, nullable=True)
    model_used = Column(String(100), nullable=True)
    parameters_used = Column(JSONB, nullable=True)

    # Results
    rendered_content = Column(Text, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)

    # User feedback on this execution
    user_satisfaction = Column(Integer, nullable=True)  # 1-5

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    prompt = relationship("PromptTemplate", back_populates="executions")
    user = relationship("User")

    def __repr__(self):
        return f"<PromptExecution(id={self.id}, context={self.context_type}, success={self.success})>"
