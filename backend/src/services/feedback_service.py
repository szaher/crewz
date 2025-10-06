"""Feedback service for managing user feedback and sentiment analysis."""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc
from fastapi import HTTPException, status
from datetime import datetime, timedelta
import structlog
import json

from ..models import Feedback, User
from ..schemas.feedback import (
    FeedbackCreate,
    FeedbackUpdate,
    FeedbackResponse,
    FeedbackListResponse,
    FeedbackType,
    SentimentType
)

logger = structlog.get_logger()


class FeedbackService:
    """Service for feedback lifecycle management and sentiment analysis."""

    def __init__(
        self,
        db: Session,
        redis_client=None
    ):
        self.db = db
        self.redis = redis_client

    def analyze_sentiment(self, text: Optional[str]) -> tuple[Optional[SentimentType], Optional[float]]:
        """
        Analyze sentiment of feedback comment using TextBlob.

        Args:
            text: Feedback comment text

        Returns:
            Tuple of (sentiment_type, sentiment_score)
        """
        if not text or not text.strip():
            return None, None

        try:
            from textblob import TextBlob

            blob = TextBlob(text)
            polarity = blob.sentiment.polarity  # -1 (negative) to 1 (positive)

            # Categorize sentiment
            if polarity > 0.1:
                sentiment = SentimentType.POSITIVE
            elif polarity < -0.1:
                sentiment = SentimentType.NEGATIVE
            else:
                sentiment = SentimentType.NEUTRAL

            logger.info(
                "sentiment_analyzed",
                polarity=polarity,
                sentiment=sentiment.value,
                text_length=len(text)
            )

            return sentiment, polarity

        except Exception as e:
            logger.error("sentiment_analysis_failed", error=str(e))
            return None, None

    async def create_feedback(
        self,
        data: FeedbackCreate,
        user_id: int,
        tenant_id: int
    ) -> Feedback:
        """
        Create new feedback with sentiment analysis.

        Args:
            data: Feedback creation data
            user_id: User submitting feedback
            tenant_id: Tenant ID

        Returns:
            Created Feedback model
        """
        # Validate target exists based on feedback type
        await self._validate_feedback_target(data, tenant_id)

        # Analyze sentiment if comment provided
        sentiment, sentiment_score = self.analyze_sentiment(data.comment)

        # Create feedback record
        feedback = Feedback(
            tenant_id=tenant_id,
            user_id=user_id,
            feedback_type=data.feedback_type.value,
            execution_id=data.execution_id,
            agent_id=data.agent_id,
            chat_session_id=data.chat_session_id,
            rating=data.rating,
            comment=data.comment,
            sentiment=sentiment.value if sentiment else None,
            sentiment_score=sentiment_score,
            tags=data.tags,
            extra_data=data.extra_data
        )

        self.db.add(feedback)
        self.db.commit()
        self.db.refresh(feedback)

        logger.info(
            "feedback_created",
            feedback_id=feedback.id,
            tenant_id=tenant_id,
            user_id=user_id,
            feedback_type=data.feedback_type.value,
            rating=data.rating,
            sentiment=sentiment.value if sentiment else None
        )

        # Publish event to Redis for ClickHouse ingestion
        await self._publish_feedback_event(feedback)

        return feedback

    async def _validate_feedback_target(self, data: FeedbackCreate, tenant_id: int):
        """Validate that the feedback target exists."""
        from ..models import Execution, Agent

        if data.feedback_type == FeedbackType.EXECUTION and data.execution_id:
            execution = self.db.query(Execution).filter(
                Execution.id == data.execution_id,
                Execution.tenant_id == tenant_id
            ).first()
            if not execution:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Execution {data.execution_id} not found"
                )

        elif data.feedback_type == FeedbackType.AGENT and data.agent_id:
            agent = self.db.query(Agent).filter(
                Agent.id == data.agent_id,
                Agent.tenant_id == tenant_id
            ).first()
            if not agent:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Agent {data.agent_id} not found"
                )

    async def _publish_feedback_event(self, feedback: Feedback):
        """Publish feedback event to Redis for real-time processing."""
        if not self.redis:
            logger.warning("redis_client_not_available_skipping_event_publish")
            return

        try:
            event = {
                "id": feedback.id,
                "tenant_id": feedback.tenant_id,
                "user_id": feedback.user_id,
                "feedback_type": feedback.feedback_type,
                "execution_id": feedback.execution_id,
                "agent_id": feedback.agent_id,
                "chat_session_id": feedback.chat_session_id,
                "rating": feedback.rating,
                "sentiment": feedback.sentiment,
                "sentiment_score": feedback.sentiment_score,
                "tags": feedback.tags,
                "created_at": feedback.created_at.isoformat(),
                "date": feedback.created_at.date().isoformat()
            }

            await self.redis.publish(
                "feedback:submitted",
                json.dumps(event)
            )

            logger.info(
                "feedback_event_published",
                feedback_id=feedback.id,
                channel="feedback:submitted"
            )

        except Exception as e:
            logger.error(
                "feedback_event_publish_failed",
                feedback_id=feedback.id,
                error=str(e)
            )

    def get_feedback(
        self,
        feedback_id: int,
        tenant_id: int
    ) -> Feedback:
        """Get feedback by ID."""
        feedback = self.db.query(Feedback).filter(
            Feedback.id == feedback_id,
            Feedback.tenant_id == tenant_id
        ).first()

        if not feedback:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Feedback {feedback_id} not found"
            )

        return feedback

    def list_feedback(
        self,
        tenant_id: int,
        feedback_type: Optional[FeedbackType] = None,
        execution_id: Optional[int] = None,
        agent_id: Optional[int] = None,
        user_id: Optional[int] = None,
        min_rating: Optional[int] = None,
        max_rating: Optional[int] = None,
        sentiment: Optional[SentimentType] = None,
        tags: Optional[List[str]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 50
    ) -> FeedbackListResponse:
        """
        List feedback with filters.

        Args:
            tenant_id: Tenant ID
            feedback_type: Filter by feedback type
            execution_id: Filter by execution
            agent_id: Filter by agent
            user_id: Filter by user
            min_rating: Minimum rating (1-5)
            max_rating: Maximum rating (1-5)
            sentiment: Filter by sentiment
            tags: Filter by tags (contains any)
            start_date: Filter by created_at >= start_date
            end_date: Filter by created_at <= end_date
            page: Page number (1-indexed)
            page_size: Results per page

        Returns:
            FeedbackListResponse with pagination
        """
        query = self.db.query(Feedback).filter(Feedback.tenant_id == tenant_id)

        # Apply filters
        if feedback_type:
            query = query.filter(Feedback.feedback_type == feedback_type.value)

        if execution_id:
            query = query.filter(Feedback.execution_id == execution_id)

        if agent_id:
            query = query.filter(Feedback.agent_id == agent_id)

        if user_id:
            query = query.filter(Feedback.user_id == user_id)

        if min_rating is not None:
            query = query.filter(Feedback.rating >= min_rating)

        if max_rating is not None:
            query = query.filter(Feedback.rating <= max_rating)

        if sentiment:
            query = query.filter(Feedback.sentiment == sentiment.value)

        if tags:
            # PostgreSQL JSON contains operator
            for tag in tags:
                query = query.filter(Feedback.tags.contains([tag]))

        if start_date:
            query = query.filter(Feedback.created_at >= start_date)

        if end_date:
            query = query.filter(Feedback.created_at <= end_date)

        # Get total count
        total = query.count()

        # Apply pagination
        offset = (page - 1) * page_size
        feedback_list = query.order_by(desc(Feedback.created_at)).offset(offset).limit(page_size).all()

        return FeedbackListResponse(
            feedback=[FeedbackResponse.model_validate(f) for f in feedback_list],
            total=total,
            page=page,
            page_size=page_size
        )

    def update_feedback(
        self,
        feedback_id: int,
        tenant_id: int,
        user_id: int,
        data: FeedbackUpdate
    ) -> Feedback:
        """
        Update feedback (only by owner).

        Args:
            feedback_id: Feedback ID to update
            tenant_id: Tenant ID
            user_id: User ID (must be feedback owner)
            data: Update data

        Returns:
            Updated Feedback model
        """
        feedback = self.db.query(Feedback).filter(
            Feedback.id == feedback_id,
            Feedback.tenant_id == tenant_id,
            Feedback.user_id == user_id  # Only owner can update
        ).first()

        if not feedback:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Feedback {feedback_id} not found or access denied"
            )

        # Update fields if provided
        if data.rating is not None:
            feedback.rating = data.rating

        if data.comment is not None:
            feedback.comment = data.comment
            # Re-analyze sentiment
            sentiment, sentiment_score = self.analyze_sentiment(data.comment)
            feedback.sentiment = sentiment.value if sentiment else None
            feedback.sentiment_score = sentiment_score

        if data.tags is not None:
            feedback.tags = data.tags

        if data.extra_data is not None:
            feedback.extra_data = data.extra_data

        self.db.commit()
        self.db.refresh(feedback)

        logger.info(
            "feedback_updated",
            feedback_id=feedback_id,
            user_id=user_id
        )

        return feedback

    def delete_feedback(
        self,
        feedback_id: int,
        tenant_id: int,
        user_id: int,
        is_admin: bool = False
    ):
        """
        Delete feedback.

        Args:
            feedback_id: Feedback ID to delete
            tenant_id: Tenant ID
            user_id: User ID
            is_admin: Whether user is admin (can delete any feedback)
        """
        query = self.db.query(Feedback).filter(
            Feedback.id == feedback_id,
            Feedback.tenant_id == tenant_id
        )

        # Non-admins can only delete their own feedback
        if not is_admin:
            query = query.filter(Feedback.user_id == user_id)

        feedback = query.first()

        if not feedback:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Feedback {feedback_id} not found or access denied"
            )

        self.db.delete(feedback)
        self.db.commit()

        logger.info(
            "feedback_deleted",
            feedback_id=feedback_id,
            user_id=user_id,
            is_admin=is_admin
        )

    def get_feedback_stats(
        self,
        tenant_id: int,
        feedback_type: Optional[FeedbackType] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get quick stats for feedback.

        Args:
            tenant_id: Tenant ID
            feedback_type: Filter by feedback type
            days: Number of days to look back

        Returns:
            Dict with stats (avg_rating, total_count, sentiment_breakdown)
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        query = self.db.query(Feedback).filter(
            Feedback.tenant_id == tenant_id,
            Feedback.created_at >= cutoff_date
        )

        if feedback_type:
            query = query.filter(Feedback.feedback_type == feedback_type.value)

        feedback_list = query.all()

        if not feedback_list:
            return {
                "avg_rating": 0,
                "total_count": 0,
                "sentiment_breakdown": {"positive": 0, "neutral": 0, "negative": 0},
                "rating_distribution": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            }

        avg_rating = sum(f.rating for f in feedback_list) / len(feedback_list)

        sentiment_breakdown = {
            "positive": sum(1 for f in feedback_list if f.sentiment == "positive"),
            "neutral": sum(1 for f in feedback_list if f.sentiment == "neutral"),
            "negative": sum(1 for f in feedback_list if f.sentiment == "negative")
        }

        rating_distribution = {
            1: sum(1 for f in feedback_list if f.rating == 1),
            2: sum(1 for f in feedback_list if f.rating == 2),
            3: sum(1 for f in feedback_list if f.rating == 3),
            4: sum(1 for f in feedback_list if f.rating == 4),
            5: sum(1 for f in feedback_list if f.rating == 5)
        }

        return {
            "avg_rating": round(avg_rating, 2),
            "total_count": len(feedback_list),
            "sentiment_breakdown": sentiment_breakdown,
            "rating_distribution": rating_distribution,
            "days": days
        }
