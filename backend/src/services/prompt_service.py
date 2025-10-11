"""Prompt registry service for managing prompt templates."""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from fastapi import HTTPException, status
from datetime import datetime
from uuid import UUID
import re

from ..models import (
    PromptTemplate,
    PromptCategory,
    PromptVersion,
    PromptFavorite,
    PromptRating,
    PromptFeedback,
    PromptExecution,
)
from ..schemas.prompt import (
    PromptTemplateCreate,
    PromptTemplateUpdate,
    PromptExecutionRequest,
)


class PromptService:
    """Service for prompt template management."""

    def __init__(self, db: Session):
        self.db = db

    # CRUD Operations
    async def create_prompt(
        self, data: PromptTemplateCreate, user_id: int, tenant_id: int
    ) -> PromptTemplate:
        """Create a new prompt template."""
        # Extract variables from content
        variables = self._extract_variables(data.content)

        # Convert model parameters to dict
        model_params = data.model_parameters.model_dump() if data.model_parameters else {}

        prompt = PromptTemplate(
            tenant_id=tenant_id,
            user_id=user_id,
            category_id=data.category_id,
            name=data.name,
            slug=data.slug or self._generate_slug(data.name),
            description=data.description,
            content=data.content,
            suggested_model=data.suggested_model,
            suggested_provider_id=data.suggested_provider_id,
            default_temperature=model_params.get("temperature", 0.7),
            default_top_p=model_params.get("top_p", 1.0),
            default_top_k=model_params.get("top_k"),
            default_max_tokens=model_params.get("max_tokens"),
            default_frequency_penalty=model_params.get("frequency_penalty", 0.0),
            default_presence_penalty=model_params.get("presence_penalty", 0.0),
            tags=data.tags,
            variables=variables,
            is_public=data.is_public,
            is_command_enabled=data.is_command_enabled,
        )

        self.db.add(prompt)
        self.db.commit()
        self.db.refresh(prompt)

        # Create initial version
        await self._create_version(prompt, user_id, "Initial version")

        return prompt

    async def get_prompt(self, prompt_id: UUID, tenant_id: int) -> PromptTemplate:
        """Get a prompt by ID."""
        prompt = (
            self.db.query(PromptTemplate)
            .filter(
                and_(
                    PromptTemplate.id == prompt_id,
                    PromptTemplate.tenant_id == tenant_id,
                    PromptTemplate.is_active == True,
                )
            )
            .first()
        )

        if not prompt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prompt not found",
            )

        return prompt

    async def list_prompts(
        self,
        tenant_id: int,
        category_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        search: Optional[str] = None,
        public_only: bool = False,
        min_rating: Optional[float] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[List[PromptTemplate], int]:
        """List prompts with filtering and pagination."""
        query = self.db.query(PromptTemplate).filter(
            and_(
                PromptTemplate.tenant_id == tenant_id,
                PromptTemplate.is_active == True,
            )
        )

        if category_id:
            query = query.filter(PromptTemplate.category_id == category_id)

        if tags:
            query = query.filter(PromptTemplate.tags.contains(tags))

        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    PromptTemplate.name.ilike(search_pattern),
                    PromptTemplate.description.ilike(search_pattern),
                    PromptTemplate.content.ilike(search_pattern),
                )
            )

        if public_only:
            query = query.filter(PromptTemplate.is_public == True)

        if min_rating is not None:
            query = query.filter(PromptTemplate.average_rating >= min_rating)

        # Get total count
        total = query.count()

        # Apply sorting
        if sort_by == "rating":
            order_col = PromptTemplate.average_rating
        elif sort_by == "usage":
            order_col = PromptTemplate.usage_count
        elif sort_by == "name":
            order_col = PromptTemplate.name
        else:
            order_col = PromptTemplate.created_at

        if sort_order == "asc":
            query = query.order_by(order_col.asc())
        else:
            query = query.order_by(order_col.desc())

        # Apply pagination
        prompts = query.limit(limit).offset(offset).all()

        return prompts, total

    async def update_prompt(
        self, prompt_id: UUID, data: PromptTemplateUpdate, user_id: int, tenant_id: int
    ) -> PromptTemplate:
        """Update a prompt template."""
        prompt = await self.get_prompt(prompt_id, tenant_id)

        update_data = data.model_dump(exclude_unset=True)

        # Track if content changed for versioning
        content_changed = False

        for field, value in update_data.items():
            if field == "model_parameters" and value:
                # Update individual parameter fields
                for param, param_value in value.items():
                    setattr(prompt, f"default_{param}", param_value)
            elif field == "content" and value != prompt.content:
                content_changed = True
                setattr(prompt, field, value)
                # Re-extract variables
                prompt.variables = self._extract_variables(value)
            else:
                setattr(prompt, field, value)

        prompt.updated_at = datetime.utcnow().isoformat()

        self.db.commit()
        self.db.refresh(prompt)

        # Create new version if content changed
        if content_changed:
            prompt.version += 1
            await self._create_version(prompt, user_id, "Content updated")

        return prompt

    async def delete_prompt(self, prompt_id: UUID, tenant_id: int) -> None:
        """Soft delete a prompt."""
        prompt = await self.get_prompt(prompt_id, tenant_id)
        prompt.is_active = False
        self.db.commit()

    # Rating & Feedback
    async def rate_prompt(
        self, prompt_id: UUID, user_id: int, tenant_id: int, rating: int
    ) -> PromptRating:
        """Rate a prompt (1-5 stars)."""
        prompt = await self.get_prompt(prompt_id, tenant_id)

        # Check if user already rated
        existing = (
            self.db.query(PromptRating)
            .filter(
                and_(
                    PromptRating.prompt_id == prompt_id,
                    PromptRating.user_id == user_id,
                )
            )
            .first()
        )

        if existing:
            # Update existing rating
            existing.rating = rating
            existing.updated_at = datetime.utcnow().isoformat()
            rating_obj = existing
        else:
            # Create new rating
            rating_obj = PromptRating(
                prompt_id=prompt_id,
                user_id=user_id,
                rating=rating,
            )
            self.db.add(rating_obj)
            prompt.total_ratings += 1

        self.db.commit()

        # Recalculate average rating
        await self._recalculate_rating(prompt_id)

        return rating_obj

    async def add_feedback(
        self, prompt_id: UUID, user_id: int, tenant_id: int, feedback_type: str, content: str
    ) -> PromptFeedback:
        """Add feedback to a prompt."""
        prompt = await self.get_prompt(prompt_id, tenant_id)

        feedback = PromptFeedback(
            prompt_id=prompt_id,
            user_id=user_id,
            feedback_type=feedback_type,
            content=content,
        )

        self.db.add(feedback)
        prompt.total_feedback += 1
        self.db.commit()
        self.db.refresh(feedback)

        return feedback

    # Execution
    async def execute_prompt(
        self, prompt_id: UUID, request: PromptExecutionRequest, user_id: int, tenant_id: int
    ) -> Dict[str, Any]:
        """Execute a prompt with variables."""
        import time

        start_time = time.time()

        prompt = await self.get_prompt(prompt_id, tenant_id)

        try:
            # Render content with variables
            rendered_content = self._render_prompt(prompt.content, request.variables)

            execution_time_ms = int((time.time() - start_time) * 1000)

            # Track execution
            execution = PromptExecution(
                prompt_id=prompt_id,
                user_id=user_id,
                tenant_id=tenant_id,
                context_type=request.context_type,
                context_id=request.context_id,
                variables_used=request.variables,
                model_used=request.model or prompt.suggested_model,
                parameters_used=request.parameters.model_dump() if request.parameters else None,
                rendered_content=rendered_content,
                execution_time_ms=execution_time_ms,
                success=True,
            )
            self.db.add(execution)

            # Update usage stats
            prompt.usage_count += 1
            prompt.last_used_at = datetime.utcnow().isoformat()

            self.db.commit()

            return {
                "execution_id": execution.id,
                "rendered_content": rendered_content,
                "execution_time_ms": execution_time_ms,
                "success": True,
            }

        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)

            execution = PromptExecution(
                prompt_id=prompt_id,
                user_id=user_id,
                tenant_id=tenant_id,
                context_type=request.context_type,
                context_id=request.context_id,
                variables_used=request.variables,
                execution_time_ms=execution_time_ms,
                success=False,
                error_message=str(e),
            )
            self.db.add(execution)
            self.db.commit()

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Prompt execution failed: {str(e)}",
            )

    # Helper Methods
    def _extract_variables(self, content: str) -> Dict[str, Any]:
        """Extract variable names from content using {variable_name} syntax."""
        pattern = r'\{(\w+)\}'
        matches = re.findall(pattern, content)
        return {var: {"type": "string", "required": True} for var in set(matches)}

    def _render_prompt(self, content: str, variables: Dict[str, Any]) -> str:
        """Render prompt content with provided variables."""
        rendered = content
        for key, value in variables.items():
            rendered = rendered.replace(f"{{{key}}}", str(value))
        return rendered

    def _generate_slug(self, name: str) -> str:
        """Generate URL-safe slug from name."""
        slug = name.lower()
        slug = re.sub(r'[^a-z0-9]+', '-', slug)
        slug = slug.strip('-')
        return slug

    async def _create_version(
        self, prompt: PromptTemplate, user_id: int, change_summary: str
    ) -> PromptVersion:
        """Create a version snapshot."""
        version = PromptVersion(
            prompt_id=prompt.id,
            version=prompt.version,
            content=prompt.content,
            variables=prompt.variables,
            model_params=prompt.get_model_params(),
            change_summary=change_summary,
            created_by=user_id,
        )
        self.db.add(version)
        self.db.commit()
        return version

    async def _recalculate_rating(self, prompt_id: UUID) -> None:
        """Recalculate average rating for a prompt."""
        result = (
            self.db.query(func.avg(PromptRating.rating))
            .filter(PromptRating.prompt_id == prompt_id)
            .scalar()
        )

        prompt = self.db.query(PromptTemplate).filter(PromptTemplate.id == prompt_id).first()
        if prompt and result:
            prompt.average_rating = round(float(result), 2)
            self.db.commit()
