"""Prompt Registry API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID

from ...db.postgres import get_db
from ...schemas.prompt import (
    PromptTemplateCreate,
    PromptTemplateUpdate,
    PromptTemplateResponse,
    PromptTemplateListResponse,
    PromptCategoryCreate,
    PromptCategoryUpdate,
    PromptCategoryResponse,
    PromptExecutionRequest,
    PromptExecutionResponse,
    PromptRatingCreate,
    PromptRatingResponse,
    PromptFeedbackCreate,
    PromptFeedbackResponse,
    PromptCommandListResponse,
)
from ...services.prompt_service import PromptService
from ...services.chat_command_handler import ChatCommandHandler
from ...api.middleware.auth import require_auth

router = APIRouter()


# ==================== Prompt Templates ====================

@router.get("", response_model=PromptTemplateListResponse)
async def list_prompts(
    category_id: Optional[UUID] = Query(None, description="Filter by category UUID"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags"),
    search: Optional[str] = Query(None, description="Search in name, description, content"),
    public_only: bool = Query(False, description="Show only public prompts"),
    min_rating: Optional[float] = Query(None, ge=0.0, le=5.0, description="Minimum average rating"),
    sort_by: str = Query("created_at", description="Sort by: created_at, rating, usage, name"),
    sort_order: str = Query("desc", description="Sort order: asc, desc"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    List prompt templates with filtering, search, and pagination.

    - **category_id**: Filter by category UUID
    - **tags**: Filter by one or more tags
    - **search**: Search text in name, description, or content
    - **public_only**: Show only publicly accessible prompts
    - **min_rating**: Minimum average rating (0-5)
    - **sort_by**: Sort field (created_at, rating, usage, name)
    - **sort_order**: Sort direction (asc, desc)
    - **page**: Page number (starting from 1)
    - **page_size**: Items per page (max 100)
    """
    prompt_service = PromptService(db)

    prompts, total = await prompt_service.list_prompts(
        tenant_id=current_user["tenant_id"],
        category_id=category_id,
        tags=tags,
        search=search,
        public_only=public_only,
        min_rating=min_rating,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=page_size,
        offset=(page - 1) * page_size,
    )

    return PromptTemplateListResponse(
        prompts=[PromptTemplateResponse.from_orm(p) for p in prompts],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=PromptTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_prompt(
    request: PromptTemplateCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Create a new prompt template.

    - **name**: Prompt name (required)
    - **slug**: URL-safe slug for /commands (auto-generated if not provided)
    - **content**: Prompt template with {variable} placeholders (required)
    - **description**: Optional description
    - **category_id**: Optional category UUID
    - **tags**: Optional list of tags
    - **suggested_model**: Recommended LLM model (e.g., 'gpt-4', 'claude-3-opus')
    - **suggested_provider_id**: Recommended LLM provider ID
    - **model_parameters**: Default execution parameters (temperature, top_k, etc.)
    - **is_public**: Make publicly accessible (default: false)
    - **is_command_enabled**: Enable /slug command execution (default: true)
    """
    prompt_service = PromptService(db)
    prompt = await prompt_service.create_prompt(
        data=request,
        user_id=current_user["id"],
        tenant_id=current_user["tenant_id"],
    )
    return PromptTemplateResponse.from_orm(prompt)


@router.get("/{prompt_id}", response_model=PromptTemplateResponse)
async def get_prompt(
    prompt_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Get prompt template details by UUID."""
    prompt_service = PromptService(db)
    prompt = await prompt_service.get_prompt(
        prompt_id=prompt_id,
        tenant_id=current_user["tenant_id"],
    )
    return PromptTemplateResponse.from_orm(prompt)


@router.put("/{prompt_id}", response_model=PromptTemplateResponse)
async def update_prompt(
    prompt_id: UUID,
    request: PromptTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Update an existing prompt template.

    Updating the content will automatically create a new version.
    All fields are optional - only provided fields will be updated.
    """
    prompt_service = PromptService(db)
    prompt = await prompt_service.update_prompt(
        prompt_id=prompt_id,
        data=request,
        user_id=current_user["id"],
        tenant_id=current_user["tenant_id"],
    )
    return PromptTemplateResponse.from_orm(prompt)


@router.delete("/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prompt(
    prompt_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Soft delete a prompt template (sets is_active = false)."""
    prompt_service = PromptService(db)
    await prompt_service.delete_prompt(
        prompt_id=prompt_id,
        tenant_id=current_user["tenant_id"],
    )


# ==================== Execution ====================

@router.post("/{prompt_id}/execute", response_model=PromptExecutionResponse)
async def execute_prompt(
    prompt_id: UUID,
    request: PromptExecutionRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Execute a prompt with variables.

    - **variables**: Dict of variable values to render in the prompt
    - **model**: Optional override for suggested model
    - **provider_id**: Optional override for suggested provider
    - **parameters**: Optional override for model parameters
    - **context_type**: Execution context (chat, task, direct, command)
    - **context_id**: Optional reference ID for the context

    Returns the rendered prompt content and execution metadata.
    """
    prompt_service = PromptService(db)
    result = await prompt_service.execute_prompt(
        prompt_id=prompt_id,
        request=request,
        user_id=current_user["id"],
        tenant_id=current_user["tenant_id"],
    )
    return PromptExecutionResponse(**result)


# ==================== Rating ====================

@router.post("/{prompt_id}/rate", response_model=PromptRatingResponse)
async def rate_prompt(
    prompt_id: UUID,
    request: PromptRatingCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Rate a prompt (1-5 stars).

    If the user has already rated this prompt, the rating will be updated.
    The prompt's average rating is automatically recalculated.

    - **rating**: Star rating from 1 to 5 (required)
    """
    prompt_service = PromptService(db)
    rating = await prompt_service.rate_prompt(
        prompt_id=prompt_id,
        user_id=current_user["id"],
        tenant_id=current_user["tenant_id"],
        rating=request.rating,
    )
    return PromptRatingResponse.from_orm(rating)


# ==================== Feedback ====================

@router.post("/{prompt_id}/feedback", response_model=PromptFeedbackResponse, status_code=status.HTTP_201_CREATED)
async def add_feedback(
    prompt_id: UUID,
    request: PromptFeedbackCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Add feedback to a prompt.

    - **feedback_type**: Type of feedback (comment, improvement, bug)
    - **content**: Feedback text (required)
    """
    prompt_service = PromptService(db)
    feedback = await prompt_service.add_feedback(
        prompt_id=prompt_id,
        user_id=current_user["id"],
        tenant_id=current_user["tenant_id"],
        feedback_type=request.feedback_type,
        content=request.content,
    )
    return PromptFeedbackResponse.from_orm(feedback)


# ==================== Commands ====================

@router.get("/commands/list", response_model=PromptCommandListResponse)
async def list_commands(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    List all available prompt commands for the tenant.

    Returns all active, command-enabled prompts with their:
    - Slug (used as /slug in chat)
    - Name and description
    - Required and optional variables
    - Example usage
    """
    command_handler = ChatCommandHandler(db)
    commands = await command_handler.list_available_commands(
        tenant_id=current_user["tenant_id"]
    )
    return PromptCommandListResponse(
        commands=commands,
        total=len(commands),
    )


# ==================== Categories ====================

@router.post("/categories", response_model=PromptCategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    request: PromptCategoryCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Create a new prompt category.

    - **name**: Category name (required)
    - **description**: Optional description
    - **icon**: Optional icon identifier
    - **color**: Optional color code
    """
    from ...models import PromptCategory
    from datetime import datetime

    category = PromptCategory(
        tenant_id=current_user["tenant_id"],
        name=request.name,
        description=request.description,
        icon=request.icon,
        color=request.color,
    )

    db.add(category)
    db.commit()
    db.refresh(category)

    return PromptCategoryResponse.from_orm(category)


@router.get("/categories/list")
async def list_categories(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """List all prompt categories for the tenant."""
    from ...models import PromptCategory

    categories = (
        db.query(PromptCategory)
        .filter(PromptCategory.tenant_id == current_user["tenant_id"])
        .order_by(PromptCategory.name)
        .all()
    )

    return {
        "categories": [PromptCategoryResponse.from_orm(c) for c in categories],
        "total": len(categories),
    }
