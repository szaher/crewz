"""Feedback API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from ...db.postgres import get_db
from ...db.redis import get_redis
from ...schemas.feedback import (
    FeedbackCreate,
    FeedbackUpdate,
    FeedbackResponse,
    FeedbackListResponse,
    FeedbackType,
    SentimentType
)
from ...services.feedback_service import FeedbackService
from ...api.middleware.auth import require_auth

router = APIRouter()


@router.post("", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def create_feedback(
    request: FeedbackCreate,
    db: Session = Depends(get_db),
    redis_client = Depends(get_redis),
    current_user: dict = Depends(require_auth),
):
    """
    Submit feedback on an execution, agent, or chat interaction.

    - **feedback_type**: Type of feedback (execution, agent, chat, general)
    - **execution_id**: Execution ID (required if feedback_type=execution)
    - **agent_id**: Agent ID (required if feedback_type=agent)
    - **chat_session_id**: Chat session ID (required if feedback_type=chat)
    - **rating**: Rating from 1-5 stars
    - **comment**: Optional comment (will be analyzed for sentiment)
    - **tags**: Optional tags for categorization
    - **metadata**: Optional additional metadata
    """
    feedback_service = FeedbackService(db, redis_client)
    feedback = await feedback_service.create_feedback(
        data=request,
        user_id=current_user["user_id"],
        tenant_id=current_user["tenant_id"]
    )
    return FeedbackResponse.model_validate(feedback)


@router.get("", response_model=FeedbackListResponse)
async def list_feedback(
    feedback_type: Optional[FeedbackType] = None,
    execution_id: Optional[int] = None,
    agent_id: Optional[int] = None,
    user_id: Optional[int] = None,
    min_rating: Optional[int] = Query(None, ge=1, le=5),
    max_rating: Optional[int] = Query(None, ge=1, le=5),
    sentiment: Optional[SentimentType] = None,
    tags: Optional[str] = None,  # Comma-separated tags
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    List feedback with filters and pagination.

    - **feedback_type**: Filter by feedback type
    - **execution_id**: Filter by execution
    - **agent_id**: Filter by agent
    - **user_id**: Filter by user
    - **min_rating**: Minimum rating (1-5)
    - **max_rating**: Maximum rating (1-5)
    - **sentiment**: Filter by sentiment (positive, neutral, negative)
    - **tags**: Comma-separated tags to filter by
    - **start_date**: Filter feedback created after this date
    - **end_date**: Filter feedback created before this date
    - **page**: Page number (default: 1)
    - **page_size**: Results per page (default: 50, max: 100)
    """
    # Parse tags if provided
    tag_list = tags.split(",") if tags else None

    feedback_service = FeedbackService(db)
    return feedback_service.list_feedback(
        tenant_id=current_user["tenant_id"],
        feedback_type=feedback_type,
        execution_id=execution_id,
        agent_id=agent_id,
        user_id=user_id,
        min_rating=min_rating,
        max_rating=max_rating,
        sentiment=sentiment,
        tags=tag_list,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size
    )


@router.get("/{feedback_id}", response_model=FeedbackResponse)
async def get_feedback(
    feedback_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Get feedback by ID."""
    feedback_service = FeedbackService(db)
    feedback = feedback_service.get_feedback(
        feedback_id=feedback_id,
        tenant_id=current_user["tenant_id"]
    )
    return FeedbackResponse.model_validate(feedback)


@router.put("/{feedback_id}", response_model=FeedbackResponse)
async def update_feedback(
    feedback_id: int,
    request: FeedbackUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Update feedback (only by owner).

    Users can only update their own feedback.
    - **rating**: Updated rating (1-5)
    - **comment**: Updated comment
    - **tags**: Updated tags
    - **metadata**: Updated metadata
    """
    feedback_service = FeedbackService(db)
    feedback = feedback_service.update_feedback(
        feedback_id=feedback_id,
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"],
        data=request
    )
    return FeedbackResponse.model_validate(feedback)


@router.delete("/{feedback_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_feedback(
    feedback_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Delete feedback.

    Users can delete their own feedback. Admins can delete any feedback.
    """
    feedback_service = FeedbackService(db)
    feedback_service.delete_feedback(
        feedback_id=feedback_id,
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"],
        is_admin=current_user.get("role") == "ADMIN"
    )


@router.get("/stats/summary")
async def get_feedback_stats(
    feedback_type: Optional[FeedbackType] = None,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Get feedback statistics summary.

    - **feedback_type**: Filter by feedback type
    - **days**: Number of days to look back (default: 30, max: 365)

    Returns:
    - Average rating
    - Total feedback count
    - Sentiment breakdown
    - Rating distribution
    """
    feedback_service = FeedbackService(db)
    return feedback_service.get_feedback_stats(
        tenant_id=current_user["tenant_id"],
        feedback_type=feedback_type,
        days=days
    )
