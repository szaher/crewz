"""Trace model for LLM execution monitoring."""

import enum
from sqlalchemy import Column, String, Integer, BigInteger, ForeignKey, Text, Index, CheckConstraint
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import relationship
from decimal import Decimal
from .base import BaseModel


class Trace(BaseModel):
    """
    Trace model representing a single LLM interaction during execution.

    Captures prompt, response, tokens, latency, and cost for observability.
    Linked to executions, agents, and tools for debugging context.
    """

    __tablename__ = "traces"

    # Foreign keys
    tenant_id = Column(postgresql.UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    execution_id = Column(postgresql.UUID(as_uuid=True), ForeignKey("executions.id"), nullable=False, index=True)
    agent_id = Column(postgresql.UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True)
    tool_id = Column(postgresql.UUID(as_uuid=True), ForeignKey("tools.id"), nullable=True)

    # Trace content
    prompt = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    model_name = Column(String(100), nullable=False)
    provider = Column(String(50), nullable=False)

    # Metrics
    prompt_tokens = Column(Integer, nullable=False)
    completion_tokens = Column(Integer, nullable=False)
    total_tokens = Column(Integer, nullable=False)
    latency_ms = Column(Integer, nullable=False)
    cost_usd = Column(postgresql.NUMERIC(10, 6), nullable=False, default=0)

    # Metadata
    langfuse_trace_id = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    trace_metadata = Column(postgresql.JSONB, nullable=True)  # Renamed from 'metadata' (SQLAlchemy reserved)

    # Relationships
    execution = relationship("Execution", foreign_keys=[execution_id])

    # Indexes
    __table_args__ = (
        Index("idx_trace_tenant_created", "tenant_id", "created_at"),
        Index("idx_trace_execution", "execution_id"),
        Index("idx_trace_created", "created_at"),

        # Constraints
        CheckConstraint(
            "total_tokens = prompt_tokens + completion_tokens",
            name="chk_trace_token_sum"
        ),
        CheckConstraint("latency_ms > 0", name="chk_trace_latency_positive"),
        CheckConstraint("cost_usd >= 0", name="chk_trace_cost_non_negative"),
        CheckConstraint(
            "(agent_id IS NOT NULL AND tool_id IS NULL) OR (agent_id IS NULL AND tool_id IS NOT NULL)",
            name="chk_trace_entity_xor"
        ),
    )

    def __repr__(self):
        return f"<Trace(id={self.id}, execution_id={self.execution_id}, model={self.model_name}, tokens={self.total_tokens})>"
