"""Feedback schemas for request/response validation."""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


class FeedbackType(str, Enum):
    """Feedback type enumeration."""
    EXECUTION = "execution"
    AGENT = "agent"
    CHAT = "chat"
    GENERAL = "general"


class SentimentType(str, Enum):
    """Sentiment type enumeration."""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class FeedbackCreate(BaseModel):
    """Create feedback request schema."""

    feedback_type: FeedbackType = Field(..., description="Type of feedback")
    execution_id: Optional[int] = Field(None, description="Execution ID (if feedback on execution)")
    agent_id: Optional[int] = Field(None, description="Agent ID (if feedback on agent)")
    chat_session_id: Optional[str] = Field(None, description="Chat session ID (if feedback on chat)")

    rating: int = Field(..., ge=1, le=5, description="Rating (1-5 stars)")
    comment: Optional[str] = Field(None, max_length=5000, description="Optional comment")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    extra_data: dict = Field(default_factory=dict, description="Additional metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "feedback_type": "execution",
                "execution_id": 123,
                "rating": 4,
                "comment": "Great execution, but took a bit longer than expected",
                "tags": ["performance", "accuracy"],
                "extra_data": {"execution_duration": 45.2}
            }
        }


class FeedbackUpdate(BaseModel):
    """Update feedback request schema."""

    rating: Optional[int] = Field(None, ge=1, le=5)
    comment: Optional[str] = Field(None, max_length=5000)
    tags: Optional[List[str]] = None
    extra_data: Optional[dict] = None


class FeedbackResponse(BaseModel):
    """Feedback response schema."""

    id: int
    tenant_id: int
    user_id: int
    feedback_type: str
    execution_id: Optional[int]
    agent_id: Optional[int]
    chat_session_id: Optional[str]
    rating: int
    comment: Optional[str]
    sentiment: Optional[str]
    sentiment_score: Optional[float]
    tags: List[str]
    extra_data: dict
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FeedbackListResponse(BaseModel):
    """Feedback list response schema."""

    feedback: List[FeedbackResponse]
    total: int
    page: int
    page_size: int


# Analytics Schemas

class RatingsAnalytics(BaseModel):
    """Rating analytics response."""

    avg_rating: float
    total_feedback: int
    rating_distribution: dict  # {1: count, 2: count, ...}
    trend: List[dict]  # [{date, avg_rating, count}]


class SentimentAnalytics(BaseModel):
    """Sentiment analytics response."""

    positive_count: int
    neutral_count: int
    negative_count: int
    avg_sentiment_score: float
    sentiment_trend: List[dict]  # [{date, positive, neutral, negative}]
    top_positive_themes: List[str]
    top_negative_themes: List[str]


class UsageTrends(BaseModel):
    """Usage trends analytics response."""

    feedback_volume: List[dict]  # [{date, count}]
    active_users_count: int
    most_rated_executions: List[dict]  # [{execution_id, count, avg_rating}]
    most_rated_agents: List[dict]  # [{agent_id, name, count, avg_rating}]
    popular_tags: List[dict]  # [{tag, count}]


class FeedbackExport(BaseModel):
    """Feedback export response."""

    export_format: str  # "json" or "csv"
    total_records: int
    date_range: dict  # {start_date, end_date}
    download_url: Optional[str]
    data: Optional[List[FeedbackResponse]]
