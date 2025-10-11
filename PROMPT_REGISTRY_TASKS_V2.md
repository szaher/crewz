# Prompt Registry Service - Implementation Tasks (Enhanced V2)

## Overview
This document outlines the enhanced implementation tasks for the Prompt Registry Service with advanced features including UUID-based IDs, model suggestions, execution parameters, feedback/ranking, chat commands, and deep workflow integration.

## 🆕 Enhanced Features

### 1. **UUID-based IDs**
All entities use UUIDs for better distribution, security, and external integrations

### 2. **Model Suggestions & Parameters**
Each prompt can specify recommended LLM model and execution parameters (temperature, top_k, max_tokens, etc.)

### 3. **Feedback & Ranking System**
Users can rate prompts, leave feedback, and see community rankings

### 4. **Chat Commands**
Quick execution via `/prompt-name` syntax in chat input

### 5. **Workflow Integration**
Smart suggestions for creating tasks from prompts when building crews, flows, or executing agents

---

## Phase 1: Backend Core (Database & Models)

### Task 1.1: Create Enhanced Database Migration for Prompt Tables
**Objective**: Set up PostgreSQL schema with UUIDs and advanced features

**Implementation**:
```sql
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- prompt_categories table
CREATE TABLE prompt_categories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    icon VARCHAR(50),
    color VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- prompt_templates table (ENHANCED)
CREATE TABLE prompt_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    category_id UUID REFERENCES prompt_categories(id),

    -- Core fields
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL, -- For /slug chat commands
    description TEXT,
    content TEXT NOT NULL,

    -- Model recommendations (NEW)
    suggested_model VARCHAR(100), -- e.g., "gpt-4", "claude-3-opus"
    suggested_provider_id INTEGER REFERENCES llm_providers(id),

    -- Execution parameters (NEW)
    default_temperature DECIMAL(3,2) DEFAULT 0.7,
    default_top_p DECIMAL(3,2) DEFAULT 1.0,
    default_top_k INTEGER DEFAULT NULL,
    default_max_tokens INTEGER DEFAULT NULL,
    default_frequency_penalty DECIMAL(3,2) DEFAULT 0.0,
    default_presence_penalty DECIMAL(3,2) DEFAULT 0.0,

    -- Metadata
    tags TEXT[], -- Array of tags
    variables JSONB, -- {var_name: {type, description, default, required}}
    is_public BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    is_command_enabled BOOLEAN DEFAULT TRUE, -- Enable /slug execution (NEW)

    -- Version control
    version INTEGER DEFAULT 1,
    parent_version_id UUID REFERENCES prompt_templates(id),

    -- Usage and ranking (ENHANCED)
    usage_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMP,
    average_rating DECIMAL(3,2) DEFAULT 0.0, -- NEW
    total_ratings INTEGER DEFAULT 0, -- NEW
    total_feedback INTEGER DEFAULT 0, -- NEW

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT unique_prompt_slug_per_tenant UNIQUE(tenant_id, slug),
    CONSTRAINT unique_prompt_name_per_tenant UNIQUE(tenant_id, name, version)
);

-- prompt_versions table (history)
CREATE TABLE prompt_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prompt_id UUID NOT NULL REFERENCES prompt_templates(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    content TEXT NOT NULL,
    variables JSONB,
    model_params JSONB, -- Store all model parameters (NEW)
    change_summary TEXT,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT unique_prompt_version UNIQUE(prompt_id, version)
);

-- prompt_favorites table
CREATE TABLE prompt_favorites (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id INTEGER NOT NULL REFERENCES users(id),
    prompt_id UUID NOT NULL REFERENCES prompt_templates(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT unique_user_prompt_favorite UNIQUE(user_id, prompt_id)
);

-- prompt_ratings table (NEW)
CREATE TABLE prompt_ratings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prompt_id UUID NOT NULL REFERENCES prompt_templates(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id),
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT unique_user_prompt_rating UNIQUE(user_id, prompt_id)
);

-- prompt_feedback table (NEW)
CREATE TABLE prompt_feedback (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prompt_id UUID NOT NULL REFERENCES prompt_templates(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id),
    feedback_type VARCHAR(50) NOT NULL, -- 'comment', 'improvement', 'bug'
    content TEXT NOT NULL,
    is_resolved BOOLEAN DEFAULT FALSE,
    resolved_by INTEGER REFERENCES users(id),
    resolved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- prompt_executions table (NEW - for detailed tracking)
CREATE TABLE prompt_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prompt_id UUID NOT NULL REFERENCES prompt_templates(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),

    -- Execution context
    context_type VARCHAR(50) NOT NULL, -- 'chat', 'task', 'direct', 'command'
    context_id UUID, -- Reference to chat session, task, etc.

    -- Execution details
    variables_used JSONB,
    model_used VARCHAR(100),
    parameters_used JSONB, -- temperature, top_k, etc.

    -- Results
    rendered_content TEXT,
    execution_time_ms INTEGER,
    success BOOLEAN,
    error_message TEXT,

    -- User feedback on this execution
    user_satisfaction INTEGER CHECK (user_satisfaction >= 1 AND user_satisfaction <= 5),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_prompts_tenant ON prompt_templates(tenant_id);
CREATE INDEX idx_prompts_user ON prompt_templates(user_id);
CREATE INDEX idx_prompts_category ON prompt_templates(category_id);
CREATE INDEX idx_prompts_slug ON prompt_templates(slug);
CREATE INDEX idx_prompts_tags ON prompt_templates USING GIN(tags);
CREATE INDEX idx_prompts_public ON prompt_templates(is_public) WHERE is_public = TRUE;
CREATE INDEX idx_prompts_commands ON prompt_templates(slug, is_command_enabled) WHERE is_command_enabled = TRUE;
CREATE INDEX idx_prompts_rating ON prompt_templates(average_rating DESC);
CREATE INDEX idx_prompt_versions_prompt ON prompt_versions(prompt_id);
CREATE INDEX idx_prompt_ratings_prompt ON prompt_ratings(prompt_id);
CREATE INDEX idx_prompt_feedback_prompt ON prompt_feedback(prompt_id);
CREATE INDEX idx_prompt_executions_prompt ON prompt_executions(prompt_id);
CREATE INDEX idx_prompt_executions_user ON prompt_executions(user_id);
CREATE INDEX idx_prompt_executions_context ON prompt_executions(context_type, context_id);
```

**Files to Create**:
- `backend/alembic/versions/XXXXX_add_enhanced_prompt_registry.py`

**Acceptance Criteria**:
- [ ] All tables use UUID primary keys
- [ ] Model parameter fields are added
- [ ] Rating and feedback tables created
- [ ] Slug field with unique constraint
- [ ] Execution tracking table created
- [ ] All indexes are created
- [ ] Migration is reversible

---

### Task 1.2: Create Enhanced SQLAlchemy Models
**Objective**: Define Python models with UUID support and new features

**Files to Create**:
- `backend/src/models/prompt_template.py`
- `backend/src/models/prompt_version.py`
- `backend/src/models/prompt_category.py`
- `backend/src/models/prompt_favorite.py`
- `backend/src/models/prompt_rating.py` (NEW)
- `backend/src/models/prompt_feedback.py` (NEW)
- `backend/src/models/prompt_execution.py` (NEW)

**Implementation Example** (`prompt_template.py`):
```python
from sqlalchemy import Column, String, Text, Boolean, Integer, ForeignKey, ARRAY, JSON, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import BaseModel
import uuid

class PromptTemplate(BaseModel):
    """Reusable prompt template with variables and model recommendations."""

    __tablename__ = "prompt_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    category_id = Column(UUID(as_uuid=True), ForeignKey("prompt_categories.id"), nullable=True, index=True)

    # Core fields
    name = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False, index=True)  # For /slug commands
    description = Column(Text, nullable=True)
    content = Column(Text, nullable=False)

    # Model recommendations (NEW)
    suggested_model = Column(String(100), nullable=True)
    suggested_provider_id = Column(Integer, ForeignKey("llm_providers.id"), nullable=True)

    # Execution parameters (NEW)
    default_temperature = Column(Numeric(3, 2), default=0.7)
    default_top_p = Column(Numeric(3, 2), default=1.0)
    default_top_k = Column(Integer, nullable=True)
    default_max_tokens = Column(Integer, nullable=True)
    default_frequency_penalty = Column(Numeric(3, 2), default=0.0)
    default_presence_penalty = Column(Numeric(3, 2), default=0.0)

    # Metadata
    tags = Column(ARRAY(String), nullable=True)
    variables = Column(JSON, nullable=True)
    is_public = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    is_command_enabled = Column(Boolean, default=True)

    # Version control
    version = Column(Integer, default=1)
    parent_version_id = Column(UUID(as_uuid=True), ForeignKey("prompt_templates.id"), nullable=True)

    # Usage and ranking
    usage_count = Column(Integer, default=0)
    last_used_at = Column(String, nullable=True)
    average_rating = Column(Numeric(3, 2), default=0.0)
    total_ratings = Column(Integer, default=0)
    total_feedback = Column(Integer, default=0)

    # Relationships
    user = relationship("User")
    category = relationship("PromptCategory", back_populates="prompts")
    suggested_provider = relationship("LLMProvider", foreign_keys=[suggested_provider_id])
    versions = relationship("PromptVersion", back_populates="prompt", cascade="all, delete-orphan")
    favorites = relationship("PromptFavorite", back_populates="prompt", cascade="all, delete-orphan")
    ratings = relationship("PromptRating", back_populates="prompt", cascade="all, delete-orphan")
    feedback = relationship("PromptFeedback", back_populates="prompt", cascade="all, delete-orphan")
    executions = relationship("PromptExecution", back_populates="prompt")

    def __repr__(self):
        return f"<PromptTemplate(id={self.id}, name={self.name}, slug={self.slug})>"

    @property
    def command(self):
        """Return the chat command for this prompt."""
        return f"/{self.slug}"

    def get_model_params(self) -> dict:
        """Get all model parameters as a dictionary."""
        return {
            "temperature": float(self.default_temperature) if self.default_temperature else 0.7,
            "top_p": float(self.default_top_p) if self.default_top_p else 1.0,
            "top_k": self.default_top_k,
            "max_tokens": self.default_max_tokens,
            "frequency_penalty": float(self.default_frequency_penalty) if self.default_frequency_penalty else 0.0,
            "presence_penalty": float(self.default_presence_penalty) if self.default_presence_penalty else 0.0,
        }

class PromptRating(BaseModel):
    """User ratings for prompts."""

    __tablename__ = "prompt_ratings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prompt_id = Column(UUID(as_uuid=True), ForeignKey("prompt_templates.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rating = Column(Integer, nullable=False)  # 1-5 stars

    # Relationships
    prompt = relationship("PromptTemplate", back_populates="ratings")
    user = relationship("User")

    def __repr__(self):
        return f"<PromptRating(prompt_id={self.prompt_id}, user_id={self.user_id}, rating={self.rating})>"

class PromptFeedback(BaseModel):
    """User feedback on prompts."""

    __tablename__ = "prompt_feedback"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prompt_id = Column(UUID(as_uuid=True), ForeignKey("prompt_templates.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    feedback_type = Column(String(50), nullable=False)  # comment, improvement, bug
    content = Column(Text, nullable=False)
    is_resolved = Column(Boolean, default=False)
    resolved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolved_at = Column(String, nullable=True)

    # Relationships
    prompt = relationship("PromptTemplate", back_populates="feedback")
    user = relationship("User", foreign_keys=[user_id])
    resolver = relationship("User", foreign_keys=[resolved_by])

    def __repr__(self):
        return f"<PromptFeedback(id={self.id}, type={self.feedback_type}, resolved={self.is_resolved})>"

class PromptExecution(BaseModel):
    """Detailed tracking of prompt executions."""

    __tablename__ = "prompt_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prompt_id = Column(UUID(as_uuid=True), ForeignKey("prompt_templates.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)

    # Execution context
    context_type = Column(String(50), nullable=False)  # chat, task, direct, command
    context_id = Column(UUID(as_uuid=True), nullable=True)  # Reference ID

    # Execution details
    variables_used = Column(JSON, nullable=True)
    model_used = Column(String(100), nullable=True)
    parameters_used = Column(JSON, nullable=True)

    # Results
    rendered_content = Column(Text, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)

    # User feedback
    user_satisfaction = Column(Integer, nullable=True)  # 1-5

    # Relationships
    prompt = relationship("PromptTemplate", back_populates="executions")
    user = relationship("User")

    def __repr__(self):
        return f"<PromptExecution(id={self.id}, context={self.context_type}, success={self.success})>"
```

**Acceptance Criteria**:
- [ ] All models use UUID primary keys
- [ ] Model parameter properties work
- [ ] Rating and feedback relationships defined
- [ ] Execution tracking model complete
- [ ] Helper methods for model params
- [ ] Models added to `__init__.py`

---

### Task 1.3: Create Enhanced Pydantic Schemas
**Objective**: Define validation schemas with new features

**Files to Create**:
- `backend/src/schemas/prompt.py`

**Implementation**:
```python
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
import re

class ModelParameters(BaseModel):
    """Schema for LLM model execution parameters."""
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=2.0)
    top_p: Optional[float] = Field(default=1.0, ge=0.0, le=1.0)
    top_k: Optional[int] = Field(default=None, ge=1)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    frequency_penalty: Optional[float] = Field(default=0.0, ge=-2.0, le=2.0)
    presence_penalty: Optional[float] = Field(default=0.0, ge=-2.0, le=2.0)

class PromptVariableSchema(BaseModel):
    """Schema for prompt variable metadata."""
    type: str = "string"  # string, number, boolean, json, array
    description: Optional[str] = None
    default: Optional[Any] = None
    required: bool = True
    validation_regex: Optional[str] = None
    options: Optional[List[Any]] = None  # For enum-like variables

class PromptCategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None

class PromptCategoryCreate(PromptCategoryBase):
    pass

class PromptCategoryResponse(PromptCategoryBase):
    id: UUID
    tenant_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class PromptTemplateBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: Optional[str] = Field(None, min_length=1, max_length=255, regex=r'^[a-z0-9-]+$')
    description: Optional[str] = None
    content: str = Field(..., min_length=1)
    category_id: Optional[UUID] = None
    tags: Optional[List[str]] = []
    is_public: bool = False
    is_command_enabled: bool = True

    # Model recommendations (NEW)
    suggested_model: Optional[str] = None
    suggested_provider_id: Optional[int] = None

    # Model parameters (NEW)
    model_parameters: Optional[ModelParameters] = Field(default_factory=ModelParameters)

    @validator('slug', always=True)
    def generate_slug(cls, v, values):
        """Auto-generate slug from name if not provided."""
        if not v and 'name' in values:
            slug = values['name'].lower()
            slug = re.sub(r'[^a-z0-9]+', '-', slug)
            slug = slug.strip('-')
            return slug
        return v

    @validator('content')
    def validate_content(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Content cannot be empty')
        return v

class PromptTemplateCreate(PromptTemplateBase):
    pass

class PromptTemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    slug: Optional[str] = Field(None, min_length=1, max_length=255, regex=r'^[a-z0-9-]+$')
    description: Optional[str] = None
    content: Optional[str] = Field(None, min_length=1)
    category_id: Optional[UUID] = None
    tags: Optional[List[str]] = None
    is_public: Optional[bool] = None
    is_active: Optional[bool] = None
    is_command_enabled: Optional[bool] = None
    suggested_model: Optional[str] = None
    suggested_provider_id: Optional[int] = None
    model_parameters: Optional[ModelParameters] = None

class PromptTemplateResponse(PromptTemplateBase):
    id: UUID
    tenant_id: int
    user_id: int
    version: int
    variables: Optional[Dict[str, PromptVariableSchema]] = {}
    usage_count: int
    last_used_at: Optional[datetime] = None
    average_rating: float
    total_ratings: int
    total_feedback: int
    created_at: datetime
    updated_at: datetime
    is_favorited: bool = False  # Computed field
    user_rating: Optional[int] = None  # Current user's rating

    class Config:
        from_attributes = True

    @property
    def command(self) -> str:
        """Get the chat command for this prompt."""
        return f"/{self.slug}"

class PromptRenderRequest(BaseModel):
    """Request to render a prompt with variables."""
    variables: Dict[str, Any] = {}
    override_parameters: Optional[ModelParameters] = None  # Override default params

class PromptRenderResponse(BaseModel):
    """Rendered prompt result."""
    rendered_content: str
    missing_variables: List[str] = []
    warnings: List[str] = []
    model_parameters: ModelParameters  # Final parameters to use

class PromptExecuteRequest(BaseModel):
    """Request to execute a prompt (render + send to LLM)."""
    variables: Dict[str, Any] = {}
    override_parameters: Optional[ModelParameters] = None
    context_type: str = "direct"  # chat, task, direct, command
    context_id: Optional[UUID] = None

class PromptExecuteResponse(BaseModel):
    """Result of prompt execution."""
    execution_id: UUID
    rendered_content: str
    llm_response: Optional[str] = None
    model_used: str
    parameters_used: ModelParameters
    execution_time_ms: int
    success: bool
    error_message: Optional[str] = None

class PromptRatingCreate(BaseModel):
    """Create or update a rating."""
    rating: int = Field(..., ge=1, le=5)

class PromptRatingResponse(BaseModel):
    id: UUID
    prompt_id: UUID
    user_id: int
    rating: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class PromptFeedbackCreate(BaseModel):
    """Create feedback."""
    feedback_type: str = Field(..., regex=r'^(comment|improvement|bug)$')
    content: str = Field(..., min_length=1)

class PromptFeedbackResponse(BaseModel):
    id: UUID
    prompt_id: UUID
    user_id: int
    feedback_type: str
    content: str
    is_resolved: bool
    resolved_by: Optional[int] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class PromptVersionResponse(BaseModel):
    id: UUID
    prompt_id: UUID
    version: int
    content: str
    variables: Optional[Dict[str, PromptVariableSchema]] = {}
    model_params: Optional[Dict[str, Any]] = {}
    change_summary: Optional[str] = None
    created_by: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True

class PromptListResponse(BaseModel):
    prompts: List[PromptTemplateResponse]
    total: int
    page: int = 1
    page_size: int = 10

class PromptCommandInfo(BaseModel):
    """Info about available chat commands."""
    slug: str
    command: str
    name: str
    description: Optional[str]
    variables: Dict[str, PromptVariableSchema]
    example: Optional[str] = None

class PromptSuggestion(BaseModel):
    """Prompt suggestion for workflow integration."""
    prompt_id: UUID
    name: str
    description: str
    reason: str  # Why this prompt is suggested
    confidence: float  # 0.0-1.0
    context: str  # crew, flow, agent, task
```

**Acceptance Criteria**:
- [ ] UUID fields properly defined
- [ ] Model parameters schema complete
- [ ] Rating and feedback schemas added
- [ ] Command info schema for chat integration
- [ ] Suggestion schema for workflow integration
- [ ] All validators work correctly

---

## Phase 2: Backend Services (Enhanced)

### Task 2.1: Create Enhanced PromptService
**Objective**: Core business logic with new features

**Files to Create**:
- `backend/src/services/prompt_service.py`

**Key Methods to Implement**:

```python
class PromptService:
    """Enhanced service for managing prompt templates."""

    def __init__(self, db: Session):
        self.db = db

    # ===== CRUD Operations =====

    async def create_prompt(
        self,
        data: PromptTemplateCreate,
        user_id: int,
        tenant_id: int
    ) -> PromptTemplate:
        """Create a new prompt template with model parameters."""

        # Extract variables
        variables = self._extract_variables(data.content)

        # Ensure slug is unique
        slug = data.slug or self._generate_slug(data.name)
        slug = await self._ensure_unique_slug(slug, tenant_id)

        # Extract model parameters
        model_params = data.model_parameters.dict() if data.model_parameters else {}

        prompt = PromptTemplate(
            tenant_id=tenant_id,
            user_id=user_id,
            name=data.name,
            slug=slug,
            description=data.description,
            content=data.content,
            category_id=data.category_id,
            tags=data.tags,
            variables=variables,
            is_public=data.is_public,
            is_command_enabled=data.is_command_enabled,
            suggested_model=data.suggested_model,
            suggested_provider_id=data.suggested_provider_id,
            default_temperature=model_params.get('temperature', 0.7),
            default_top_p=model_params.get('top_p', 1.0),
            default_top_k=model_params.get('top_k'),
            default_max_tokens=model_params.get('max_tokens'),
            default_frequency_penalty=model_params.get('frequency_penalty', 0.0),
            default_presence_penalty=model_params.get('presence_penalty', 0.0),
            version=1
        )

        self.db.add(prompt)
        self.db.commit()
        self.db.refresh(prompt)

        # Create initial version
        await self._create_version(prompt, "Initial version", user_id)

        return prompt

    def _generate_slug(self, name: str) -> str:
        """Generate URL-safe slug from name."""
        slug = name.lower()
        slug = re.sub(r'[^a-z0-9]+', '-', slug)
        slug = slug.strip('-')
        return slug

    async def _ensure_unique_slug(self, slug: str, tenant_id: int, exclude_id: UUID = None) -> str:
        """Ensure slug is unique within tenant."""
        base_slug = slug
        counter = 1

        while True:
            query = self.db.query(PromptTemplate).filter(
                PromptTemplate.tenant_id == tenant_id,
                PromptTemplate.slug == slug,
                PromptTemplate.is_active == True
            )

            if exclude_id:
                query = query.filter(PromptTemplate.id != exclude_id)

            exists = query.first()

            if not exists:
                return slug

            slug = f"{base_slug}-{counter}"
            counter += 1

    # ===== Rating & Feedback =====

    async def rate_prompt(
        self,
        prompt_id: UUID,
        user_id: int,
        rating: int
    ) -> PromptRating:
        """Rate a prompt (1-5 stars). Updates existing rating if present."""

        # Check if user already rated
        existing = self.db.query(PromptRating).filter(
            PromptRating.prompt_id == prompt_id,
            PromptRating.user_id == user_id
        ).first()

        if existing:
            existing.rating = rating
            self.db.commit()
            self.db.refresh(existing)
            rating_obj = existing
        else:
            rating_obj = PromptRating(
                prompt_id=prompt_id,
                user_id=user_id,
                rating=rating
            )
            self.db.add(rating_obj)
            self.db.commit()
            self.db.refresh(rating_obj)

        # Update prompt average rating
        await self._update_prompt_rating(prompt_id)

        return rating_obj

    async def _update_prompt_rating(self, prompt_id: UUID):
        """Recalculate and update prompt average rating."""
        from sqlalchemy import func

        result = self.db.query(
            func.avg(PromptRating.rating).label('avg'),
            func.count(PromptRating.id).label('count')
        ).filter(
            PromptRating.prompt_id == prompt_id
        ).first()

        prompt = self.db.query(PromptTemplate).filter(
            PromptTemplate.id == prompt_id
        ).first()

        if prompt:
            prompt.average_rating = float(result.avg) if result.avg else 0.0
            prompt.total_ratings = result.count or 0
            self.db.commit()

    async def add_feedback(
        self,
        prompt_id: UUID,
        user_id: int,
        feedback_type: str,
        content: str
    ) -> PromptFeedback:
        """Add feedback to a prompt."""

        feedback = PromptFeedback(
            prompt_id=prompt_id,
            user_id=user_id,
            feedback_type=feedback_type,
            content=content
        )

        self.db.add(feedback)
        self.db.commit()
        self.db.refresh(feedback)

        # Update feedback count
        prompt = self.db.query(PromptTemplate).filter(
            PromptTemplate.id == prompt_id
        ).first()
        if prompt:
            prompt.total_feedback = self.db.query(PromptFeedback).filter(
                PromptFeedback.prompt_id == prompt_id
            ).count()
            self.db.commit()

        return feedback

    async def get_feedback(
        self,
        prompt_id: UUID,
        feedback_type: Optional[str] = None,
        unresolved_only: bool = False
    ) -> List[PromptFeedback]:
        """Get feedback for a prompt."""

        query = self.db.query(PromptFeedback).filter(
            PromptFeedback.prompt_id == prompt_id
        )

        if feedback_type:
            query = query.filter(PromptFeedback.feedback_type == feedback_type)

        if unresolved_only:
            query = query.filter(PromptFeedback.is_resolved == False)

        return query.order_by(PromptFeedback.created_at.desc()).all()

    # ===== Command Integration =====

    async def get_command_prompts(
        self,
        tenant_id: int,
        user_id: int
    ) -> List[PromptTemplate]:
        """Get all prompts available as chat commands."""

        from sqlalchemy import or_

        return self.db.query(PromptTemplate).filter(
            PromptTemplate.tenant_id == tenant_id,
            PromptTemplate.is_active == True,
            PromptTemplate.is_command_enabled == True,
            or_(
                PromptTemplate.user_id == user_id,
                PromptTemplate.is_public == True
            )
        ).all()

    async def get_prompt_by_slug(
        self,
        slug: str,
        tenant_id: int,
        user_id: int
    ) -> PromptTemplate:
        """Get prompt by slug for command execution."""

        from sqlalchemy import or_

        prompt = self.db.query(PromptTemplate).filter(
            PromptTemplate.slug == slug,
            PromptTemplate.tenant_id == tenant_id,
            PromptTemplate.is_active == True,
            PromptTemplate.is_command_enabled == True,
            or_(
                PromptTemplate.user_id == user_id,
                PromptTemplate.is_public == True
            )
        ).first()

        if not prompt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Command '/{slug}' not found"
            )

        return prompt

    async def parse_command(self, message: str) -> Optional[Dict[str, Any]]:
        """
        Parse chat message for prompt command.

        Supported formats:
        - /slug
        - /slug var1=value1 var2=value2
        - /slug "var1=value with spaces" var2=value2

        Returns:
            {
                "slug": "prompt-slug",
                "variables": {"var1": "value1", "var2": "value2"}
            }
            or None if not a command
        """

        if not message.startswith('/'):
            return None

        # Remove leading slash
        message = message[1:].strip()

        # Extract slug (first word)
        parts = message.split(None, 1)
        slug = parts[0]

        variables = {}

        if len(parts) > 1:
            # Parse variables
            var_string = parts[1]

            # Handle quoted values: var="value with spaces"
            pattern = r'(\w+)=(?:"([^"]*)"|\'([^\']*)\'|([^\s]+))'
            matches = re.finditer(pattern, var_string)

            for match in matches:
                var_name = match.group(1)
                var_value = match.group(2) or match.group(3) or match.group(4)
                variables[var_name] = var_value

        return {
            "slug": slug,
            "variables": variables
        }

    # ===== Execution & Tracking =====

    async def execute_prompt(
        self,
        prompt_id: UUID,
        variables: Dict[str, Any],
        user_id: int,
        tenant_id: int,
        override_parameters: Optional[Dict[str, Any]] = None,
        context_type: str = "direct",
        context_id: Optional[UUID] = None
    ) -> PromptExecuteResponse:
        """
        Execute a prompt: render + send to LLM.

        Returns both rendered content and LLM response.
        """

        import time
        from ..services.llm_service import LLMService

        start_time = time.time()

        prompt = await self.get_prompt(prompt_id, tenant_id)

        # Render prompt
        render_result = await self.render_prompt(
            prompt_id=prompt_id,
            variables=variables,
            tenant_id=tenant_id,
            user_id=user_id,
            track_usage=False  # We'll track in execution
        )

        if not render_result["success"]:
            # Track failed execution
            await self._track_execution(
                prompt_id=prompt_id,
                user_id=user_id,
                tenant_id=tenant_id,
                variables=variables,
                context_type=context_type,
                context_id=context_id,
                success=False,
                error_message=str(render_result["errors"])
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=render_result["errors"]
            )

        rendered_content = render_result["rendered_content"]

        # Determine model and parameters
        model_params = prompt.get_model_params()
        if override_parameters:
            model_params.update(override_parameters)

        provider_id = prompt.suggested_provider_id
        if not provider_id:
            # Use default provider
            from ..models import LLMProvider
            default_provider = self.db.query(LLMProvider).filter(
                LLMProvider.is_default == True
            ).first()
            provider_id = default_provider.id if default_provider else None

        if not provider_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No LLM provider configured"
            )

        # Call LLM
        llm_service = LLMService(self.db)
        try:
            llm_response = await llm_service.chat_completion(
                provider_id=provider_id,
                messages=[{"role": "user", "content": rendered_content}],
                **model_params
            )
            success = True
            error_message = None
        except Exception as e:
            llm_response = None
            success = False
            error_message = str(e)

        execution_time_ms = int((time.time() - start_time) * 1000)

        # Track execution
        execution = await self._track_execution(
            prompt_id=prompt_id,
            user_id=user_id,
            tenant_id=tenant_id,
            variables=variables,
            model_used=prompt.suggested_model or "default",
            parameters_used=model_params,
            rendered_content=rendered_content,
            context_type=context_type,
            context_id=context_id,
            execution_time_ms=execution_time_ms,
            success=success,
            error_message=error_message
        )

        # Update usage count
        prompt.usage_count += 1
        prompt.last_used_at = datetime.utcnow().isoformat()
        self.db.commit()

        return PromptExecuteResponse(
            execution_id=execution.id,
            rendered_content=rendered_content,
            llm_response=llm_response,
            model_used=prompt.suggested_model or "default",
            parameters_used=ModelParameters(**model_params),
            execution_time_ms=execution_time_ms,
            success=success,
            error_message=error_message
        )

    async def _track_execution(
        self,
        prompt_id: UUID,
        user_id: int,
        tenant_id: int,
        variables: Dict[str, Any],
        context_type: str,
        context_id: Optional[UUID] = None,
        model_used: Optional[str] = None,
        parameters_used: Optional[Dict[str, Any]] = None,
        rendered_content: Optional[str] = None,
        execution_time_ms: Optional[int] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> PromptExecution:
        """Track prompt execution in database."""

        execution = PromptExecution(
            prompt_id=prompt_id,
            user_id=user_id,
            tenant_id=tenant_id,
            context_type=context_type,
            context_id=context_id,
            variables_used=variables,
            model_used=model_used,
            parameters_used=parameters_used,
            rendered_content=rendered_content,
            execution_time_ms=execution_time_ms,
            success=success,
            error_message=error_message
        )

        self.db.add(execution)
        self.db.commit()
        self.db.refresh(execution)

        return execution

    # ===== Workflow Suggestions =====

    async def suggest_prompts_for_crew(
        self,
        crew_id: int,
        tenant_id: int,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Suggest prompts for creating tasks in a crew.

        Analyzes crew agents, tasks, and common patterns to suggest relevant prompts.
        """

        from ..models import Crew, Task, Agent

        # Get crew info
        crew = self.db.query(Crew).filter(Crew.id == crew_id).first()
        if not crew:
            return []

        # Get crew tasks and agents for context
        tasks = self.db.query(Task).filter(Task.crew_id == crew_id).all()
        agent_ids = crew.agent_ids or []

        # Build relevance scoring
        suggestions = []

        # Get prompts with "task" tag
        task_prompts = self.db.query(PromptTemplate).filter(
            PromptTemplate.tenant_id == tenant_id,
            PromptTemplate.is_active == True,
            PromptTemplate.tags.contains(["task"])
        ).all()

        for prompt in task_prompts:
            confidence = 0.5  # Base confidence
            reason = "Tagged for task creation"

            # Boost confidence if prompt has high rating
            if prompt.average_rating > 4.0:
                confidence += 0.2
                reason += ", highly rated"

            # Boost if prompt has been used frequently
            if prompt.usage_count > 10:
                confidence += 0.1
                reason += ", popular"

            # Check for matching tags with existing tasks
            if tasks:
                existing_tags = set()
                for task in tasks:
                    if hasattr(task, 'tags') and task.tags:
                        existing_tags.update(task.tags)

                prompt_tags = set(prompt.tags or [])
                overlap = existing_tags & prompt_tags
                if overlap:
                    confidence += 0.2
                    reason += f", matches tags: {', '.join(list(overlap)[:2])}"

            confidence = min(confidence, 1.0)

            suggestions.append({
                "prompt_id": prompt.id,
                "name": prompt.name,
                "description": prompt.description,
                "reason": reason,
                "confidence": round(confidence, 2),
                "context": "crew",
                "tags": prompt.tags,
                "average_rating": float(prompt.average_rating)
            })

        # Sort by confidence
        suggestions.sort(key=lambda x: x["confidence"], reverse=True)

        return suggestions[:limit]

    async def suggest_prompts_for_agent(
        self,
        agent_id: int,
        tenant_id: int,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Suggest prompts relevant to agent's role and capabilities."""

        from ..models import Agent

        agent = self.db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            return []

        # Extract keywords from agent role and goal
        keywords = []
        if agent.role:
            keywords.extend(agent.role.lower().split())
        if agent.goal:
            keywords.extend(agent.goal.lower().split())

        # Remove common words
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for"}
        keywords = [k for k in keywords if k not in stop_words and len(k) > 3]

        # Find prompts with matching tags or content
        suggestions = []

        prompts = self.db.query(PromptTemplate).filter(
            PromptTemplate.tenant_id == tenant_id,
            PromptTemplate.is_active == True
        ).all()

        for prompt in prompts:
            confidence = 0.3  # Base confidence
            reason = "General recommendation"

            # Check tag matches
            prompt_tags = [t.lower() for t in (prompt.tags or [])]
            matches = [k for k in keywords if any(k in tag for tag in prompt_tags)]

            if matches:
                confidence += 0.3 + (0.1 * min(len(matches), 3))
                reason = f"Matches: {', '.join(matches[:3])}"

            # Check content matches
            content_lower = prompt.content.lower()
            content_matches = sum(1 for k in keywords if k in content_lower)
            if content_matches > 0:
                confidence += 0.1 * min(content_matches, 3)

            # Boost for ratings
            if prompt.average_rating > 4.0:
                confidence += 0.1

            confidence = min(confidence, 1.0)

            if confidence > 0.4:  # Only include if reasonably confident
                suggestions.append({
                    "prompt_id": prompt.id,
                    "name": prompt.name,
                    "description": prompt.description,
                    "reason": reason,
                    "confidence": round(confidence, 2),
                    "context": "agent",
                    "tags": prompt.tags,
                    "average_rating": float(prompt.average_rating)
                })

        suggestions.sort(key=lambda x: x["confidence"], reverse=True)

        return suggestions[:limit]
```

**Acceptance Criteria**:
- [ ] Enhanced CRUD with UUID support
- [ ] Rating and feedback methods work
- [ ] Command parsing handles all formats
- [ ] Execute method calls LLM with proper params
- [ ] Execution tracking saves to database
- [ ] Workflow suggestions calculate confidence correctly
- [ ] All helper methods tested

---

### Task 2.2: Implement Chat Command Handler
**Objective**: Process /prompt-name commands in chat

**Files to Create**:
- `backend/src/services/chat_command_handler.py`

**Implementation**:
```python
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from ..services.prompt_service import PromptService
from ..services.llm_service import LLMService
from uuid import UUID

class ChatCommandHandler:
    """Handle chat commands for prompt execution."""

    def __init__(self, db: Session):
        self.db = db
        self.prompt_service = PromptService(db)
        self.llm_service = LLMService(db)

    async def handle_message(
        self,
        message: str,
        session_id: int,
        user_id: int,
        tenant_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Check if message is a command and handle it.

        Returns:
            {
                "is_command": True,
                "prompt_id": UUID,
                "prompt_name": str,
                "rendered_content": str,
                "llm_response": str,
                "execution_id": UUID
            }
            or None if not a command
        """

        # Parse command
        parsed = await self.prompt_service.parse_command(message)
        if not parsed:
            return None

        slug = parsed["slug"]
        variables = parsed["variables"]

        try:
            # Get prompt by slug
            prompt = await self.prompt_service.get_prompt_by_slug(
                slug=slug,
                tenant_id=tenant_id,
                user_id=user_id
            )

            # Execute prompt
            result = await self.prompt_service.execute_prompt(
                prompt_id=prompt.id,
                variables=variables,
                user_id=user_id,
                tenant_id=tenant_id,
                context_type="command",
                context_id=UUID(int=session_id)  # Chat session ID
            )

            return {
                "is_command": True,
                "prompt_id": str(prompt.id),
                "prompt_name": prompt.name,
                "slug": prompt.slug,
                "rendered_content": result.rendered_content,
                "llm_response": result.llm_response,
                "execution_id": str(result.execution_id),
                "model_used": result.model_used,
                "success": result.success,
                "error_message": result.error_message
            }

        except Exception as e:
            return {
                "is_command": True,
                "error": str(e),
                "success": False
            }

    async def get_available_commands(
        self,
        tenant_id: int,
        user_id: int
    ) -> List[Dict[str, Any]]:
        """Get list of available commands for autocomplete."""

        prompts = await self.prompt_service.get_command_prompts(
            tenant_id=tenant_id,
            user_id=user_id
        )

        commands = []
        for prompt in prompts:
            # Generate example usage
            example_vars = []
            if prompt.variables:
                for var_name, var_meta in prompt.variables.items():
                    if var_meta.get("required"):
                        default = var_meta.get("default", "value")
                        example_vars.append(f"{var_name}={default}")

            example = f"/{prompt.slug}"
            if example_vars:
                example += " " + " ".join(example_vars[:2])  # Show max 2 vars

            commands.append({
                "slug": prompt.slug,
                "command": f"/{prompt.slug}",
                "name": prompt.name,
                "description": prompt.description,
                "variables": prompt.variables or {},
                "example": example,
                "rating": float(prompt.average_rating),
                "usage_count": prompt.usage_count
            })

        return commands
```

**Acceptance Criteria**:
- [ ] Command detection works
- [ ] Variable parsing handles quotes
- [ ] Prompt execution succeeds
- [ ] Errors are handled gracefully
- [ ] Available commands list includes examples
- [ ] Integration with chat service

---

## Phase 3: Backend API (Enhanced)

### Task 3.1: Create Enhanced Prompt CRUD Endpoints
**Objective**: REST API with new features

**Files to Update**:
- `backend/src/api/v1/prompts.py`

**Key Endpoints**:

```python
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID

from ...db.postgres import get_db
from ...schemas.prompt import *
from ...services.prompt_service import PromptService
from ...api.middleware.auth import require_auth

router = APIRouter()

# ===== CRUD Endpoints =====

@router.post("", response_model=PromptTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_prompt(
    request: PromptTemplateCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Create a new prompt template.

    Features:
    - Auto-generates slug from name if not provided
    - Extracts variables from content
    - Supports model recommendations and parameters
    - Command-enabled for chat integration
    """
    service = PromptService(db)
    prompt = await service.create_prompt(
        request,
        user_id=current_user["user_id"],
        tenant_id=current_user["tenant_id"]
    )

    # Add user rating if exists
    response = PromptTemplateResponse.from_orm(prompt)
    user_rating = await service.get_user_rating(prompt.id, current_user["user_id"])
    response.user_rating = user_rating

    return response

@router.get("", response_model=PromptListResponse)
async def list_prompts(
    page: int = 1,
    page_size: int = 20,
    category_id: Optional[UUID] = None,
    search: Optional[str] = None,
    tags: Optional[str] = Query(None, description="Comma-separated tags"),
    only_favorites: bool = False,
    only_commands: bool = False,
    min_rating: Optional[float] = Query(None, ge=0.0, le=5.0),
    sort_by: str = Query("created_at", regex="^(created_at|updated_at|usage_count|average_rating|name)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    List prompt templates with advanced filtering and sorting.

    Sort options:
    - created_at: Newest first
    - updated_at: Recently updated
    - usage_count: Most used
    - average_rating: Highest rated
    - name: Alphabetical
    """
    if page_size > 100:
        page_size = 100

    tag_list = tags.split(",") if tags else None

    service = PromptService(db)
    result = await service.list_prompts(
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"],
        page=page,
        page_size=page_size,
        category_id=category_id,
        search=search,
        tags=tag_list,
        only_favorites=only_favorites,
        only_commands=only_commands,
        min_rating=min_rating,
        sort_by=sort_by,
        sort_order=sort_order
    )

    return PromptListResponse(**result)

@router.get("/commands", response_model=List[PromptCommandInfo])
async def get_available_commands(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Get all available chat commands.

    Returns prompts that have is_command_enabled=True with usage examples.
    Used for chat autocomplete and help.
    """
    from ...services.chat_command_handler import ChatCommandHandler

    handler = ChatCommandHandler(db)
    commands = await handler.get_available_commands(
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"]
    )

    return commands

# ===== Rating & Feedback =====

@router.post("/{prompt_id}/rate", response_model=PromptRatingResponse)
async def rate_prompt(
    prompt_id: UUID,
    request: PromptRatingCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Rate a prompt (1-5 stars). Updates existing rating if present."""
    service = PromptService(db)
    rating = await service.rate_prompt(
        prompt_id=prompt_id,
        user_id=current_user["user_id"],
        rating=request.rating
    )
    return PromptRatingResponse.from_orm(rating)

@router.post("/{prompt_id}/feedback", response_model=PromptFeedbackResponse, status_code=status.HTTP_201_CREATED)
async def add_feedback(
    prompt_id: UUID,
    request: PromptFeedbackCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Add feedback to a prompt (comment, improvement suggestion, or bug report)."""
    service = PromptService(db)
    feedback = await service.add_feedback(
        prompt_id=prompt_id,
        user_id=current_user["user_id"],
        feedback_type=request.feedback_type,
        content=request.content
    )
    return PromptFeedbackResponse.from_orm(feedback)

@router.get("/{prompt_id}/feedback", response_model=List[PromptFeedbackResponse])
async def get_feedback(
    prompt_id: UUID,
    feedback_type: Optional[str] = Query(None, regex="^(comment|improvement|bug)$"),
    unresolved_only: bool = False,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Get feedback for a prompt."""
    service = PromptService(db)
    feedback_list = await service.get_feedback(
        prompt_id=prompt_id,
        feedback_type=feedback_type,
        unresolved_only=unresolved_only
    )
    return [PromptFeedbackResponse.from_orm(f) for f in feedback_list]

# ===== Execution =====

@router.post("/{prompt_id}/execute", response_model=PromptExecuteResponse)
async def execute_prompt(
    prompt_id: UUID,
    request: PromptExecuteRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Execute a prompt: render with variables + send to LLM.

    Returns both the rendered prompt and the LLM response.
    Tracks execution for analytics.
    """
    service = PromptService(db)
    result = await service.execute_prompt(
        prompt_id=prompt_id,
        variables=request.variables,
        user_id=current_user["user_id"],
        tenant_id=current_user["tenant_id"],
        override_parameters=request.override_parameters.dict() if request.override_parameters else None,
        context_type=request.context_type,
        context_id=request.context_id
    )
    return result

# ===== Workflow Suggestions =====

@router.get("/suggestions/crew/{crew_id}", response_model=List[PromptSuggestion])
async def get_crew_prompt_suggestions(
    crew_id: int,
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Get prompt suggestions for creating tasks in a crew.

    Analyzes crew context and suggests relevant prompts with confidence scores.
    """
    service = PromptService(db)
    suggestions = await service.suggest_prompts_for_crew(
        crew_id=crew_id,
        tenant_id=current_user["tenant_id"],
        limit=limit
    )
    return suggestions

@router.get("/suggestions/agent/{agent_id}", response_model=List[PromptSuggestion])
async def get_agent_prompt_suggestions(
    agent_id: int,
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Get prompt suggestions relevant to an agent.

    Matches prompts to agent role and capabilities.
    """
    service = PromptService(db)
    suggestions = await service.suggest_prompts_for_agent(
        agent_id=agent_id,
        tenant_id=current_user["tenant_id"],
        limit=limit
    )
    return suggestions

@router.get("/suggestions/flow/{flow_id}", response_model=List[PromptSuggestion])
async def get_flow_prompt_suggestions(
    flow_id: int,
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Get prompt suggestions for flow nodes."""
    service = PromptService(db)
    suggestions = await service.suggest_prompts_for_flow(
        flow_id=flow_id,
        tenant_id=current_user["tenant_id"],
        limit=limit
    )
    return suggestions
```

**Additional Endpoints to Add**:
- Ranking/leaderboard endpoint
- Bulk operations (activate/deactivate multiple)
- Export/import with model params
- Duplicate prompt
- Fork public prompt

**Acceptance Criteria**:
- [ ] All CRUD operations work
- [ ] Rating endpoints update averages correctly
- [ ] Feedback can be filtered
- [ ] Execute endpoint returns LLM response
- [ ] Suggestions endpoints return scored results
- [ ] Commands endpoint works for autocomplete

---

## Phase 4: Chat Integration (Enhanced)

### Task 4.1: Integrate Command Handler into Chat Service
**Objective**: Process commands in chat messages

**Files to Update**:
- `backend/src/services/chat_service.py`
- `backend/src/api/v1/chat.py`

**Implementation**:

In `chat_service.py`:
```python
from ..services.chat_command_handler import ChatCommandHandler

class ChatService:
    # ... existing code ...

    async def handle_message_with_commands(
        self,
        session_id: int,
        message: str,
        user_id: int,
        tenant_id: int,
        store_user_message: bool = True
    ) -> Dict[str, Any]:
        """
        Handle chat message, checking for commands first.

        Returns:
            {
                "is_command": bool,
                "user_message": ChatMessage,
                "assistant_message": ChatMessage,
                "command_info": {...} if is_command
            }
        """

        command_handler = ChatCommandHandler(self.db)

        # Check if message is a command
        command_result = await command_handler.handle_message(
            message=message,
            session_id=session_id,
            user_id=user_id,
            tenant_id=tenant_id
        )

        if command_result and command_result.get("is_command"):
            # Store user message
            if store_user_message:
                user_msg = await self.send_message(ChatMessageCreate(
                    session_id=session_id,
                    role="user",
                    content=message,
                    metadata={
                        "is_command": True,
                        "prompt_slug": command_result.get("slug"),
                        "prompt_id": command_result.get("prompt_id")
                    }
                ))
            else:
                user_msg = None

            # Store assistant response
            if command_result.get("success"):
                assistant_msg = await self.send_message(ChatMessageCreate(
                    session_id=session_id,
                    role="assistant",
                    content=command_result["llm_response"],
                    metadata={
                        "from_command": True,
                        "prompt_id": command_result["prompt_id"],
                        "execution_id": command_result["execution_id"],
                        "model_used": command_result.get("model_used")
                    }
                ))
            else:
                # Command failed
                error_msg = command_result.get("error_message", "Command execution failed")
                assistant_msg = await self.send_message(ChatMessageCreate(
                    session_id=session_id,
                    role="assistant",
                    content=f"❌ Command failed: {error_msg}",
                    metadata={
                        "from_command": True,
                        "command_error": True,
                        "error": error_msg
                    }
                ))

            return {
                "is_command": True,
                "user_message": user_msg,
                "assistant_message": assistant_msg,
                "command_info": command_result
            }

        # Not a command, handle normally
        return {
            "is_command": False,
            "message": message
        }
```

In `chat.py`:
```python
@router.post("/sessions/{session_id}/message")
async def send_chat_message(
    session_id: int,
    content: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Send a chat message with command support.

    If message starts with /, it's treated as a command.
    Commands execute prompts with variables inline.
    """
    llm_service = LLMService(db)
    chat_service = ChatService(db, llm_service)

    result = await chat_service.handle_message_with_commands(
        session_id=session_id,
        message=content,
        user_id=current_user["user_id"],
        tenant_id=current_user["tenant_id"]
    )

    if result["is_command"]:
        return {
            "type": "command_response",
            "command_info": result["command_info"],
            "messages": [
                result["user_message"],
                result["assistant_message"]
            ]
        }

    # Normal message flow...
```

**Acceptance Criteria**:
- [ ] Commands are detected and processed
- [ ] Non-command messages work normally
- [ ] Command results are stored in chat
- [ ] Error handling for failed commands
- [ ] Metadata tracks command usage

---

### Task 4.2: Add Command Autocomplete in Chat UI
**Objective**: Frontend autocomplete for /commands

**Files to Create/Update**:
- `frontend/src/components/chat/CommandAutocomplete.tsx`
- `frontend/src/components/chat/ChatWindow.tsx`

**Features**:
- Trigger autocomplete on "/"
- Show available commands with descriptions
- Preview variables needed
- Insert command with placeholder values
- Real-time filtering as user types

**Implementation Sketch**:
```typescript
export default function CommandAutocomplete({ input, onSelect, onClose }) {
  const [commands, setCommands] = useState([]);
  const [filtered, setFiltered] = useState([]);

  useEffect(() => {
    // Fetch available commands
    const fetchCommands = async () => {
      const res = await apiClient.get('/api/v1/prompts/commands');
      setCommands(res.data);
    };
    fetchCommands();
  }, []);

  useEffect(() => {
    if (!input.startsWith('/')) {
      onClose();
      return;
    }

    const query = input.slice(1).toLowerCase();
    const filtered = commands.filter(cmd =>
      cmd.slug.toLowerCase().includes(query) ||
      cmd.name.toLowerCase().includes(query)
    );
    setFiltered(filtered);
  }, [input, commands]);

  return (
    <div className="autocomplete-dropdown">
      {filtered.map(cmd => (
        <div
          key={cmd.slug}
          onClick={() => onSelect(cmd)}
          className="command-item"
        >
          <div className="command-name">
            /{cmd.slug} - {cmd.name}
          </div>
          <div className="command-desc">{cmd.description}</div>
          <div className="command-example">{cmd.example}</div>
        </div>
      ))}
    </div>
  );
}
```

**Acceptance Criteria**:
- [ ] Autocomplete triggers on /
- [ ] Commands filtered as user types
- [ ] Click inserts command
- [ ] Variables shown in preview
- [ ] Keyboard navigation works

---

## Phase 5: Task Integration (Enhanced)

### Task 5.1: Add Prompt Suggestions to Task/Crew/Flow Creation
**Objective**: Suggest prompts when creating workflows

**Files to Update**:
- `frontend/src/components/tasks/TaskForm.tsx`
- `frontend/src/components/crews/CrewForm.tsx`
- `frontend/src/components/flows/FlowEditor.tsx`

**Features**:
- "Suggested Prompts" sidebar/panel
- Show confidence scores
- Preview prompt before using
- One-click to create task from prompt
- Bulk task creation for workflow prompts

**Implementation**:
```typescript
// In CrewForm.tsx
export default function CrewForm({ crew, onSave }) {
  const [suggestions, setSuggestions] = useState([]);

  useEffect(() => {
    if (crew?.id) {
      // Fetch suggestions for this crew
      const fetchSuggestions = async () => {
        const res = await apiClient.get(`/api/v1/prompts/suggestions/crew/${crew.id}`);
        setSuggestions(res.data);
      };
      fetchSuggestions();
    }
  }, [crew]);

  const handleUsePrompt = async (suggestion) => {
    // Show prompt variable form
    // Create task(s) from prompt
  };

  return (
    <div className="flex gap-6">
      <div className="flex-1">
        {/* Main crew form */}
      </div>

      {suggestions.length > 0 && (
        <div className="w-80 bg-gray-50 p-4 rounded">
          <h3 className="font-medium mb-3">Suggested Prompts</h3>
          {suggestions.map(sugg => (
            <div key={sugg.prompt_id} className="mb-3 p-3 bg-white rounded border">
              <div className="flex items-center justify-between mb-1">
                <span className="font-medium text-sm">{sugg.name}</span>
                <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
                  {Math.round(sugg.confidence * 100)}%
                </span>
              </div>
              <p className="text-xs text-gray-600 mb-2">{sugg.reason}</p>
              <button
                onClick={() => handleUsePrompt(sugg)}
                className="btn-sm btn-primary w-full"
              >
                Use Prompt
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

**Acceptance Criteria**:
- [ ] Suggestions load contextually
- [ ] Confidence scores displayed
- [ ] Prompts can be previewed
- [ ] Tasks created correctly
- [ ] UI is non-intrusive

---

## Summary of Enhancements

### New Database Tables:
1. `prompt_ratings` - User ratings (1-5 stars)
2. `prompt_feedback` - Comments, improvements, bugs
3. `prompt_executions` - Detailed execution tracking

### New API Endpoints:
1. `POST /prompts/{id}/rate` - Rate a prompt
2. `POST /prompts/{id}/feedback` - Add feedback
3. `GET /prompts/{id}/feedback` - Get feedback
4. `POST /prompts/{id}/execute` - Execute prompt with LLM
5. `GET /prompts/commands` - Get available chat commands
6. `GET /prompts/suggestions/crew/{id}` - Get suggestions for crew
7. `GET /prompts/suggestions/agent/{id}` - Get suggestions for agent
8. `GET /prompts/suggestions/flow/{id}` - Get suggestions for flow

### New Features:
1. **UUID-based IDs** - All prompt entities use UUIDs
2. **Model Parameters** - Configure temperature, top_k, etc. per prompt
3. **Ratings & Feedback** - Community-driven quality assessment
4. **Chat Commands** - `/prompt-slug var=value` syntax
5. **Workflow Suggestions** - AI-powered prompt recommendations
6. **Execution Tracking** - Detailed analytics on prompt usage

### Enhanced Timeline:
- **Backend Enhancement**: +1 week (rating, feedback, commands)
- **Chat Integration**: +1 week (command handler, autocomplete)
- **Workflow Suggestions**: +1 week (recommendation engine)
- **Frontend Enhancements**: +2 weeks (all new UI components)

**New Total**: 8-12 weeks

---

## Next Steps

1. Review enhanced design
2. Prioritize features if needed
3. Start with Phase 1 enhanced migration
4. Implement rating/feedback system early
5. Command integration in parallel with core features
6. Suggestion engine can be Phase 2 enhancement

This enhanced design provides a production-ready, feature-rich prompt registry that deeply integrates with your platform!
