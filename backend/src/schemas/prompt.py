"""Prompt registry schemas."""

from pydantic import BaseModel, Field, validator, field_validator, model_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
import re


# Model Parameters Schema
class ModelParameters(BaseModel):
    """Schema for LLM model execution parameters."""

    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    top_p: Optional[float] = Field(default=1.0, ge=0.0, le=1.0, description="Nucleus sampling parameter")
    top_k: Optional[int] = Field(default=None, ge=1, description="Top-k sampling parameter")
    max_tokens: Optional[int] = Field(default=None, ge=1, description="Maximum tokens to generate")
    frequency_penalty: Optional[float] = Field(default=0.0, ge=-2.0, le=2.0, description="Frequency penalty")
    presence_penalty: Optional[float] = Field(default=0.0, ge=-2.0, le=2.0, description="Presence penalty")


# Variable Schema
class PromptVariableSchema(BaseModel):
    """Schema for prompt variable metadata."""

    name: str = Field(..., description="Variable name")
    type: str = Field(default="string", description="Variable type: string, number, boolean, json, array")
    description: Optional[str] = Field(None, description="Variable description")
    default: Optional[Any] = Field(None, description="Default value")
    required: bool = Field(default=True, description="Is variable required")
    validation_regex: Optional[str] = Field(None, description="Regex pattern for validation")
    options: Optional[List[Any]] = Field(None, description="Enum-like options for the variable")


# Category Schemas
class PromptCategoryBase(BaseModel):
    """Base prompt category schema."""

    name: str = Field(..., min_length=1, max_length=255, description="Category name")
    description: Optional[str] = Field(None, description="Category description")
    icon: Optional[str] = Field(None, max_length=50, description="Icon identifier")
    color: Optional[str] = Field(None, max_length=20, description="Color code")


class PromptCategoryCreate(PromptCategoryBase):
    """Create prompt category request schema."""
    pass


class PromptCategoryUpdate(BaseModel):
    """Update prompt category request schema."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    icon: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field(None, max_length=20)


class PromptCategoryResponse(PromptCategoryBase):
    """Prompt category response schema."""

    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Template Schemas
class PromptTemplateBase(BaseModel):
    """Base prompt template schema."""

    name: str = Field(..., min_length=1, max_length=255, description="Prompt name")
    slug: Optional[str] = Field(None, min_length=1, max_length=255, pattern=r'^[a-z0-9-]+$', description="URL-safe slug for /commands")
    description: Optional[str] = Field(None, description="Prompt description")
    content: str = Field(..., min_length=1, description="Prompt template content with {variable} placeholders")
    category_id: Optional[UUID] = Field(None, description="Category UUID")
    tags: Optional[List[str]] = Field(default_factory=list, description="Tags for categorization")
    is_public: bool = Field(default=False, description="Is prompt publicly accessible")
    is_command_enabled: bool = Field(default=True, description="Enable /slug command execution")

    # Model recommendations
    suggested_model: Optional[str] = Field(None, max_length=100, description="Suggested LLM model (e.g., 'gpt-4', 'claude-3-opus')")
    suggested_provider_id: Optional[UUID] = Field(None, description="Suggested LLM provider ID")

    # Model parameters
    model_parameters: Optional[ModelParameters] = Field(default_factory=ModelParameters, description="Default model parameters")

    @field_validator('slug', mode='before')
    @classmethod
    def generate_slug(cls, v, info):
        """Auto-generate slug from name if not provided."""
        if not v and 'name' in info.data:
            slug = info.data['name'].lower()
            slug = re.sub(r'[^a-z0-9]+', '-', slug)
            slug = slug.strip('-')
            return slug
        return v

    @field_validator('content')
    @classmethod
    def validate_content(cls, v):
        """Validate content is not empty."""
        if not v or len(v.strip()) == 0:
            raise ValueError('Content cannot be empty')
        return v


class PromptTemplateCreate(PromptTemplateBase):
    """Create prompt template request schema."""
    pass


class PromptTemplateUpdate(BaseModel):
    """Update prompt template request schema."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    slug: Optional[str] = Field(None, min_length=1, max_length=255, pattern=r'^[a-z0-9-]+$')
    description: Optional[str] = None
    content: Optional[str] = Field(None, min_length=1)
    category_id: Optional[UUID] = None
    tags: Optional[List[str]] = None
    is_public: Optional[bool] = None
    is_active: Optional[bool] = None
    is_command_enabled: Optional[bool] = None
    suggested_model: Optional[str] = Field(None, max_length=100)
    suggested_provider_id: Optional[UUID] = None
    model_parameters: Optional[ModelParameters] = None


class PromptTemplateResponse(PromptTemplateBase):
    """Prompt template response schema."""

    id: UUID
    tenant_id: UUID
    user_id: UUID
    version: int
    variables: Optional[Dict[str, PromptVariableSchema]] = Field(default_factory=dict)
    usage_count: int
    last_used_at: Optional[datetime] = None
    average_rating: float
    total_ratings: int
    total_feedback: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @model_validator(mode='wrap')
    @classmethod
    def transform_variables(cls, data: Any, handler):
        """Transform variables dict to inject name field from dict key."""
        # First, get the data in the right format
        # When using from_orm, data will be the ORM object
        # We need to extract and transform variables before validation

        if hasattr(data, 'variables'):
            # It's an ORM object, extract variables
            variables = data.variables
            if variables and isinstance(variables, dict):
                transformed_vars = {}
                for var_name, var_meta in variables.items():
                    if isinstance(var_meta, dict) and 'name' not in var_meta:
                        # Add name field from dict key
                        transformed_vars[var_name] = {**var_meta, 'name': var_name}
                    else:
                        transformed_vars[var_name] = var_meta
                # Replace variables with transformed version
                data.variables = transformed_vars
        elif isinstance(data, dict) and 'variables' in data:
            # It's a dict input
            variables = data['variables']
            if variables and isinstance(variables, dict):
                transformed_vars = {}
                for var_name, var_meta in variables.items():
                    if isinstance(var_meta, dict) and 'name' not in var_meta:
                        # Add name field from dict key
                        transformed_vars[var_name] = {**var_meta, 'name': var_name}
                    else:
                        transformed_vars[var_name] = var_meta
                data['variables'] = transformed_vars

        # Now let Pydantic validate
        return handler(data)

    class Config:
        from_attributes = True


class PromptTemplateListResponse(BaseModel):
    """List of prompt templates response."""

    prompts: List[PromptTemplateResponse]
    total: int
    page: int
    page_size: int


# Execution Schemas
class PromptExecutionRequest(BaseModel):
    """Execute prompt request schema."""

    variables: Dict[str, Any] = Field(default_factory=dict, description="Variables to render in the prompt")
    model: Optional[str] = Field(None, description="Override suggested model")
    provider_id: Optional[UUID] = Field(None, description="Override suggested provider")
    parameters: Optional[ModelParameters] = Field(None, description="Override model parameters")
    context_type: str = Field(default="direct", description="Execution context: chat, task, direct, command")
    context_id: Optional[UUID] = Field(None, description="Context reference ID")


class PromptExecutionResponse(BaseModel):
    """Execute prompt response schema."""

    execution_id: UUID
    rendered_content: str
    execution_time_ms: int
    success: bool
    error_message: Optional[str] = None


# Rating Schemas
class PromptRatingCreate(BaseModel):
    """Create/update rating request schema."""

    rating: int = Field(..., ge=1, le=5, description="Rating from 1-5 stars")


class PromptRatingResponse(BaseModel):
    """Rating response schema."""

    id: UUID
    prompt_id: UUID
    user_id: UUID
    rating: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Feedback Schemas
class PromptFeedbackCreate(BaseModel):
    """Create feedback request schema."""

    feedback_type: str = Field(..., pattern=r'^(comment|improvement|bug)$', description="Feedback type")
    content: str = Field(..., min_length=1, description="Feedback content")


class PromptFeedbackUpdate(BaseModel):
    """Update feedback request schema."""

    content: Optional[str] = Field(None, min_length=1)
    is_resolved: Optional[bool] = None


class PromptFeedbackResponse(BaseModel):
    """Feedback response schema."""

    id: UUID
    prompt_id: UUID
    user_id: UUID
    feedback_type: str
    content: str
    is_resolved: bool
    resolved_by: Optional[UUID] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Command Schemas
class PromptCommandInfo(BaseModel):
    """Command information schema."""

    slug: str
    name: str
    description: Optional[str]
    required_variables: List[str]
    optional_variables: List[str]
    example: str
    variables: List[PromptVariableSchema] = []  # Full variable metadata for UI


class PromptCommandListResponse(BaseModel):
    """List of available commands."""

    commands: List[PromptCommandInfo]
    total: int


# Suggestion Schemas
class PromptSuggestion(BaseModel):
    """Prompt suggestion schema."""

    prompt_id: UUID
    name: str
    description: Optional[str]
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0-1")
    reason: str = Field(..., description="Reason for suggestion")
    context: str = Field(..., description="Suggestion context: crew, agent, flow, task")
    tags: List[str] = Field(default_factory=list)


class PromptSuggestionResponse(BaseModel):
    """Prompt suggestions response."""

    suggestions: List[PromptSuggestion]
    context_type: str
    context_id: Optional[UUID] = None
