# Prompt Registry Service - Implementation Tasks

## Overview
This document outlines the detailed implementation tasks for the Prompt Registry Service, a system for managing reusable prompt templates with deep integration into chat and task creation workflows.

---

## Phase 1: Backend Core (Database & Models)

### Task 1.1: Create Database Migration for Prompt Tables
**Objective**: Set up PostgreSQL schema for prompt storage

**Implementation**:
```sql
-- prompt_categories table
CREATE TABLE prompt_categories (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    icon VARCHAR(50),
    color VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- prompt_templates table
CREATE TABLE prompt_templates (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    category_id INTEGER REFERENCES prompt_categories(id),

    -- Core fields
    name VARCHAR(255) NOT NULL,
    description TEXT,
    content TEXT NOT NULL,

    -- Metadata
    tags TEXT[], -- Array of tags for categorization
    variables JSONB, -- Extracted variables with metadata
    is_public BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,

    -- Version control
    version INTEGER DEFAULT 1,
    parent_version_id INTEGER REFERENCES prompt_templates(id),

    -- Usage tracking
    usage_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMP,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT unique_prompt_name_per_tenant UNIQUE(tenant_id, name, version)
);

-- prompt_versions table (history)
CREATE TABLE prompt_versions (
    id SERIAL PRIMARY KEY,
    prompt_id INTEGER NOT NULL REFERENCES prompt_templates(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    content TEXT NOT NULL,
    variables JSONB,
    change_summary TEXT,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT unique_prompt_version UNIQUE(prompt_id, version)
);

-- prompt_favorites table
CREATE TABLE prompt_favorites (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    prompt_id INTEGER NOT NULL REFERENCES prompt_templates(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT unique_user_prompt_favorite UNIQUE(user_id, prompt_id)
);

-- Indexes for performance
CREATE INDEX idx_prompts_tenant ON prompt_templates(tenant_id);
CREATE INDEX idx_prompts_user ON prompt_templates(user_id);
CREATE INDEX idx_prompts_category ON prompt_templates(category_id);
CREATE INDEX idx_prompts_tags ON prompt_templates USING GIN(tags);
CREATE INDEX idx_prompts_public ON prompt_templates(is_public) WHERE is_public = TRUE;
CREATE INDEX idx_prompt_versions_prompt ON prompt_versions(prompt_id);
```

**Files to Create**:
- `backend/alembic/versions/XXXXX_add_prompt_registry_tables.py`

**Acceptance Criteria**:
- [ ] Migration creates all tables successfully
- [ ] All foreign keys are properly set up
- [ ] Indexes are created for performance
- [ ] Migration is reversible (down migration works)

---

### Task 1.2: Create SQLAlchemy Models
**Objective**: Define Python models for prompt entities

**Files to Create**:
- `backend/src/models/prompt_template.py`
- `backend/src/models/prompt_version.py`
- `backend/src/models/prompt_category.py`
- `backend/src/models/prompt_favorite.py`

**Implementation Example** (`prompt_template.py`):
```python
from sqlalchemy import Column, String, Text, Boolean, Integer, ForeignKey, ARRAY, JSON
from sqlalchemy.orm import relationship
from .base import BaseModel

class PromptTemplate(BaseModel):
    """Reusable prompt template with variables."""

    __tablename__ = "prompt_templates"

    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("prompt_categories.id"), nullable=True, index=True)

    # Core fields
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    content = Column(Text, nullable=False)

    # Metadata
    tags = Column(ARRAY(String), nullable=True)
    variables = Column(JSON, nullable=True)  # {var_name: {type, description, default}}
    is_public = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    # Version control
    version = Column(Integer, default=1)
    parent_version_id = Column(Integer, ForeignKey("prompt_templates.id"), nullable=True)

    # Usage tracking
    usage_count = Column(Integer, default=0)
    last_used_at = Column(String, nullable=True)

    # Relationships
    user = relationship("User")
    category = relationship("PromptCategory", back_populates="prompts")
    versions = relationship("PromptVersion", back_populates="prompt")
    favorites = relationship("PromptFavorite", back_populates="prompt")
```

**Acceptance Criteria**:
- [ ] All models inherit from BaseModel
- [ ] Relationships are properly defined
- [ ] Models include __repr__ methods
- [ ] Models are added to `__init__.py`

---

### Task 1.3: Create Pydantic Schemas
**Objective**: Define validation schemas for API

**Files to Create**:
- `backend/src/schemas/prompt.py`

**Implementation**:
```python
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
import re

class PromptVariableSchema(BaseModel):
    """Schema for prompt variable metadata."""
    type: str = "string"  # string, number, boolean, json
    description: Optional[str] = None
    default: Optional[Any] = None
    required: bool = True
    validation_regex: Optional[str] = None

class PromptCategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None

class PromptCategoryCreate(PromptCategoryBase):
    pass

class PromptCategoryResponse(PromptCategoryBase):
    id: int
    tenant_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class PromptTemplateBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    content: str = Field(..., min_length=1)
    category_id: Optional[int] = None
    tags: Optional[List[str]] = []
    is_public: bool = False

    @validator('content')
    def validate_content(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Content cannot be empty')
        return v

class PromptTemplateCreate(PromptTemplateBase):
    pass

class PromptTemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    content: Optional[str] = Field(None, min_length=1)
    category_id: Optional[int] = None
    tags: Optional[List[str]] = None
    is_public: Optional[bool] = None
    is_active: Optional[bool] = None

class PromptTemplateResponse(PromptTemplateBase):
    id: int
    tenant_id: int
    user_id: int
    version: int
    variables: Optional[Dict[str, PromptVariableSchema]] = {}
    usage_count: int
    last_used_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    is_favorited: bool = False  # Computed field

    class Config:
        from_attributes = True

class PromptRenderRequest(BaseModel):
    """Request to render a prompt with variables."""
    prompt_id: int
    variables: Dict[str, Any] = {}

class PromptRenderResponse(BaseModel):
    """Rendered prompt result."""
    rendered_content: str
    missing_variables: List[str] = []
    warnings: List[str] = []

class PromptVersionResponse(BaseModel):
    id: int
    prompt_id: int
    version: int
    content: str
    variables: Optional[Dict[str, PromptVariableSchema]] = {}
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
```

**Acceptance Criteria**:
- [ ] All schemas include proper validation
- [ ] Variable extraction works correctly
- [ ] Response schemas match database models
- [ ] Nested schemas (category, variables) work properly

---

### Task 1.4: Set Up MongoDB Collections for Analytics
**Objective**: Create MongoDB collections for tracking and analytics

**Files to Update**:
- `backend/src/db/mongodb.py` (if needed)

**MongoDB Collections**:

```python
# Collection: prompt_usage_analytics
{
    "_id": ObjectId,
    "prompt_id": int,
    "user_id": int,
    "tenant_id": int,
    "context": str,  # "chat", "task", "direct"
    "variables_used": dict,
    "success": bool,
    "feedback": str,  # Optional user feedback
    "execution_time_ms": int,
    "timestamp": datetime
}

# Collection: prompt_test_results (for A/B testing)
{
    "_id": ObjectId,
    "prompt_id": int,
    "version": int,
    "test_variant": str,  # "A", "B", "C"
    "metrics": {
        "user_satisfaction": float,
        "task_completion_rate": float,
        "average_response_length": int
    },
    "timestamp": datetime
}
```

**Acceptance Criteria**:
- [ ] Collections are automatically created on first use
- [ ] Indexes are set up for common queries
- [ ] Analytics insertion is non-blocking
- [ ] Error handling for MongoDB failures

---

## Phase 2: Backend Services

### Task 2.1: Create PromptService with CRUD Operations
**Objective**: Implement core business logic for prompt management

**Files to Create**:
- `backend/src/services/prompt_service.py`

**Implementation**:
```python
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import re

from ..models import PromptTemplate, PromptVersion, PromptCategory, PromptFavorite, User
from ..schemas.prompt import (
    PromptTemplateCreate, PromptTemplateUpdate, PromptTemplateResponse,
    PromptCategoryCreate, PromptCategoryResponse
)
from ..db.mongodb import get_mongo_collection

class PromptService:
    """Service for managing prompt templates."""

    def __init__(self, db: Session):
        self.db = db

    async def create_prompt(
        self,
        data: PromptTemplateCreate,
        user_id: int,
        tenant_id: int
    ) -> PromptTemplate:
        """Create a new prompt template."""

        # Extract variables from content
        variables = self._extract_variables(data.content)

        # Create prompt
        prompt = PromptTemplate(
            tenant_id=tenant_id,
            user_id=user_id,
            name=data.name,
            description=data.description,
            content=data.content,
            category_id=data.category_id,
            tags=data.tags,
            variables=variables,
            is_public=data.is_public,
            version=1
        )

        self.db.add(prompt)
        self.db.commit()
        self.db.refresh(prompt)

        # Create initial version
        await self._create_version(prompt, "Initial version", user_id)

        return prompt

    async def list_prompts(
        self,
        tenant_id: int,
        user_id: int,
        page: int = 1,
        page_size: int = 10,
        category_id: Optional[int] = None,
        search: Optional[str] = None,
        tags: Optional[List[str]] = None,
        only_favorites: bool = False
    ) -> Dict[str, Any]:
        """List prompts with filtering and pagination."""

        query = self.db.query(PromptTemplate).filter(
            PromptTemplate.tenant_id == tenant_id,
            PromptTemplate.is_active == True
        )

        # Filter by public or owned
        if not only_favorites:
            from sqlalchemy import or_
            query = query.filter(
                or_(
                    PromptTemplate.user_id == user_id,
                    PromptTemplate.is_public == True
                )
            )

        # Apply filters
        if category_id:
            query = query.filter(PromptTemplate.category_id == category_id)

        if search:
            from sqlalchemy import or_
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    PromptTemplate.name.ilike(search_pattern),
                    PromptTemplate.description.ilike(search_pattern),
                    PromptTemplate.content.ilike(search_pattern)
                )
            )

        if tags:
            query = query.filter(PromptTemplate.tags.contains(tags))

        if only_favorites:
            query = query.join(PromptFavorite).filter(
                PromptFavorite.user_id == user_id
            )

        # Get total count
        total = query.count()

        # Apply pagination
        prompts = query.order_by(PromptTemplate.created_at.desc())\
            .offset((page - 1) * page_size)\
            .limit(page_size)\
            .all()

        # Check favorites for current user
        favorite_ids = self._get_user_favorites(user_id)

        return {
            "prompts": prompts,
            "total": total,
            "page": page,
            "page_size": page_size,
            "favorite_ids": favorite_ids
        }

    async def get_prompt(
        self,
        prompt_id: int,
        tenant_id: int
    ) -> PromptTemplate:
        """Get a specific prompt by ID."""

        prompt = self.db.query(PromptTemplate).filter(
            PromptTemplate.id == prompt_id,
            PromptTemplate.tenant_id == tenant_id,
            PromptTemplate.is_active == True
        ).first()

        if not prompt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prompt not found"
            )

        return prompt

    async def update_prompt(
        self,
        prompt_id: int,
        data: PromptTemplateUpdate,
        user_id: int,
        tenant_id: int,
        create_version: bool = True
    ) -> PromptTemplate:
        """Update a prompt template."""

        prompt = await self.get_prompt(prompt_id, tenant_id)

        # Check ownership
        if prompt.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this prompt"
            )

        # Update fields
        if data.name is not None:
            prompt.name = data.name
        if data.description is not None:
            prompt.description = data.description
        if data.content is not None:
            prompt.content = data.content
            # Re-extract variables
            prompt.variables = self._extract_variables(data.content)
        if data.category_id is not None:
            prompt.category_id = data.category_id
        if data.tags is not None:
            prompt.tags = data.tags
        if data.is_public is not None:
            prompt.is_public = data.is_public
        if data.is_active is not None:
            prompt.is_active = data.is_active

        self.db.commit()
        self.db.refresh(prompt)

        # Create version if content changed
        if create_version and data.content is not None:
            await self._create_version(prompt, "Updated", user_id)

        return prompt

    async def delete_prompt(
        self,
        prompt_id: int,
        user_id: int,
        tenant_id: int
    ) -> None:
        """Soft delete a prompt."""

        prompt = await self.get_prompt(prompt_id, tenant_id)

        if prompt.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this prompt"
            )

        prompt.is_active = False
        self.db.commit()

    def _extract_variables(self, content: str) -> Dict[str, Any]:
        """Extract {variable} placeholders from content."""

        # Find all {variable_name} patterns
        pattern = r'\{([a-zA-Z_][a-zA-Z0-9_]*)\}'
        matches = re.findall(pattern, content)

        # Create variable metadata
        variables = {}
        for var_name in set(matches):
            variables[var_name] = {
                "type": "string",
                "description": f"Variable: {var_name}",
                "required": True,
                "default": None
            }

        return variables

    async def _create_version(
        self,
        prompt: PromptTemplate,
        change_summary: str,
        user_id: int
    ) -> PromptVersion:
        """Create a version snapshot."""

        version = PromptVersion(
            prompt_id=prompt.id,
            version=prompt.version,
            content=prompt.content,
            variables=prompt.variables,
            change_summary=change_summary,
            created_by=user_id
        )

        self.db.add(version)
        self.db.commit()

        return version

    def _get_user_favorites(self, user_id: int) -> List[int]:
        """Get IDs of user's favorite prompts."""

        favorites = self.db.query(PromptFavorite.prompt_id).filter(
            PromptFavorite.user_id == user_id
        ).all()

        return [f[0] for f in favorites]
```

**Acceptance Criteria**:
- [ ] All CRUD operations work correctly
- [ ] Proper error handling and validation
- [ ] Tenant isolation is enforced
- [ ] Pagination works correctly
- [ ] Variable extraction is accurate

---

### Task 2.2: Implement Variable Extraction and Validation
**Objective**: Robust system for extracting and validating prompt variables

**Implementation Details**:
- Support `{variable_name}` syntax
- Detect variable types (string, number, boolean, json)
- Validate variable names (alphanumeric + underscore)
- Support optional variables with defaults
- Generate variable metadata automatically

**Files to Update**:
- `backend/src/services/prompt_service.py`

**Enhanced Variable Extraction**:
```python
def _extract_variables(self, content: str) -> Dict[str, Any]:
    """
    Extract and analyze variables from prompt content.

    Supports:
    - {variable_name} - Basic variable
    - {variable_name:type} - Type hint (string, number, boolean, json)
    - {variable_name=default} - Default value
    - {variable_name:type=default} - Both
    """

    # Enhanced pattern with optional type and default
    pattern = r'\{([a-zA-Z_][a-zA-Z0-9_]*)(?::(\w+))?(?:=([^\}]+))?\}'
    matches = re.finditer(pattern, content)

    variables = {}
    for match in matches:
        var_name = match.group(1)
        var_type = match.group(2) or "string"
        default_value = match.group(3)

        # Convert default value to appropriate type
        if default_value:
            try:
                if var_type == "number":
                    default_value = float(default_value)
                elif var_type == "boolean":
                    default_value = default_value.lower() in ("true", "1", "yes")
                elif var_type == "json":
                    import json
                    default_value = json.loads(default_value)
            except:
                default_value = None

        variables[var_name] = {
            "type": var_type,
            "description": f"Variable: {var_name}",
            "required": default_value is None,
            "default": default_value
        }

    return variables

def validate_variables(
    self,
    variables: Dict[str, Any],
    required_vars: Dict[str, Any]
) -> Dict[str, List[str]]:
    """Validate provided variables against requirements."""

    errors = {}
    missing = []

    for var_name, var_meta in required_vars.items():
        if var_meta["required"] and var_name not in variables:
            missing.append(var_name)

        if var_name in variables:
            value = variables[var_name]
            var_type = var_meta["type"]

            # Type validation
            if var_type == "number" and not isinstance(value, (int, float)):
                errors.setdefault(var_name, []).append("Must be a number")
            elif var_type == "boolean" and not isinstance(value, bool):
                errors.setdefault(var_name, []).append("Must be a boolean")
            elif var_type == "json":
                import json
                try:
                    if isinstance(value, str):
                        json.loads(value)
                except:
                    errors.setdefault(var_name, []).append("Must be valid JSON")

            # Custom regex validation
            if var_meta.get("validation_regex"):
                pattern = var_meta["validation_regex"]
                if not re.match(pattern, str(value)):
                    errors.setdefault(var_name, []).append(f"Does not match pattern: {pattern}")

    if missing:
        errors["_missing"] = missing

    return errors
```

**Acceptance Criteria**:
- [ ] Extracts all variable types correctly
- [ ] Handles default values properly
- [ ] Validates variable values against types
- [ ] Returns clear error messages
- [ ] Supports complex patterns

---

### Task 2.3: Implement Prompt Rendering Engine
**Objective**: Render prompts with variable substitution

**Files to Update**:
- `backend/src/services/prompt_service.py`

**Implementation**:
```python
async def render_prompt(
    self,
    prompt_id: int,
    variables: Dict[str, Any],
    tenant_id: int,
    user_id: int,
    track_usage: bool = True
) -> Dict[str, Any]:
    """Render a prompt by substituting variables."""

    prompt = await self.get_prompt(prompt_id, tenant_id)

    # Validate variables
    validation_errors = self.validate_variables(variables, prompt.variables or {})

    if validation_errors:
        return {
            "success": False,
            "errors": validation_errors,
            "rendered_content": None
        }

    # Apply defaults for missing optional variables
    full_variables = {}
    for var_name, var_meta in (prompt.variables or {}).items():
        if var_name in variables:
            full_variables[var_name] = variables[var_name]
        elif var_meta.get("default") is not None:
            full_variables[var_name] = var_meta["default"]

    # Render content
    rendered_content = prompt.content
    missing_variables = []
    warnings = []

    for var_name, value in full_variables.items():
        placeholder = f"{{{var_name}}}"
        if placeholder in rendered_content:
            # Convert value to string representation
            if isinstance(value, dict) or isinstance(value, list):
                import json
                value_str = json.dumps(value, indent=2)
            else:
                value_str = str(value)

            rendered_content = rendered_content.replace(placeholder, value_str)
        else:
            warnings.append(f"Variable '{var_name}' provided but not used in prompt")

    # Check for unsubstituted variables
    remaining_vars = re.findall(r'\{([a-zA-Z_][a-zA-Z0-9_]*)\}', rendered_content)
    if remaining_vars:
        missing_variables = list(set(remaining_vars))

    # Track usage
    if track_usage:
        await self._track_usage(prompt_id, user_id, tenant_id, variables, True)

        # Update usage count
        prompt.usage_count += 1
        prompt.last_used_at = datetime.utcnow().isoformat()
        self.db.commit()

    return {
        "success": True,
        "rendered_content": rendered_content,
        "missing_variables": missing_variables,
        "warnings": warnings
    }

async def _track_usage(
    self,
    prompt_id: int,
    user_id: int,
    tenant_id: int,
    variables: Dict[str, Any],
    success: bool,
    context: str = "direct"
):
    """Track prompt usage in MongoDB analytics."""

    try:
        analytics_col = get_mongo_collection("prompt_usage_analytics")

        await analytics_col.insert_one({
            "prompt_id": prompt_id,
            "user_id": user_id,
            "tenant_id": tenant_id,
            "context": context,
            "variables_used": variables,
            "success": success,
            "timestamp": datetime.utcnow()
        })
    except Exception as e:
        # Non-fatal, just log
        print(f"Failed to track prompt usage: {e}")
```

**Acceptance Criteria**:
- [ ] Variables are substituted correctly
- [ ] Default values are applied
- [ ] Missing variables are detected
- [ ] Usage is tracked in MongoDB
- [ ] Error messages are clear

---

### Task 2.4: Add Version Control Logic
**Objective**: Manage prompt versions and history

**Implementation**:
```python
async def create_new_version(
    self,
    prompt_id: int,
    content: str,
    change_summary: str,
    user_id: int,
    tenant_id: int
) -> PromptTemplate:
    """Create a new version of a prompt."""

    prompt = await self.get_prompt(prompt_id, tenant_id)

    if prompt.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized"
        )

    # Increment version
    prompt.version += 1
    prompt.content = content
    prompt.variables = self._extract_variables(content)

    self.db.commit()
    self.db.refresh(prompt)

    # Create version record
    await self._create_version(prompt, change_summary, user_id)

    return prompt

async def get_version_history(
    self,
    prompt_id: int,
    tenant_id: int
) -> List[PromptVersion]:
    """Get version history for a prompt."""

    prompt = await self.get_prompt(prompt_id, tenant_id)

    versions = self.db.query(PromptVersion).filter(
        PromptVersion.prompt_id == prompt_id
    ).order_by(PromptVersion.version.desc()).all()

    return versions

async def restore_version(
    self,
    prompt_id: int,
    version_number: int,
    user_id: int,
    tenant_id: int
) -> PromptTemplate:
    """Restore a prompt to a specific version."""

    prompt = await self.get_prompt(prompt_id, tenant_id)

    if prompt.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized"
        )

    # Get the version
    version = self.db.query(PromptVersion).filter(
        PromptVersion.prompt_id == prompt_id,
        PromptVersion.version == version_number
    ).first()

    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Version not found"
        )

    # Restore content
    prompt.content = version.content
    prompt.variables = version.variables
    prompt.version += 1  # Create new version

    self.db.commit()
    self.db.refresh(prompt)

    # Create version record
    await self._create_version(prompt, f"Restored from version {version_number}", user_id)

    return prompt
```

**Acceptance Criteria**:
- [ ] Versions are created automatically
- [ ] Version history is retrievable
- [ ] Versions can be restored
- [ ] Version numbers increment correctly
- [ ] Change summaries are stored

---

### Task 2.5: Add MongoDB Analytics Tracking
**Objective**: Track prompt usage and effectiveness

**Files to Update**:
- `backend/src/services/prompt_service.py`

**Analytics Methods**:
```python
async def get_prompt_analytics(
    self,
    prompt_id: int,
    tenant_id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> Dict[str, Any]:
    """Get analytics for a prompt."""

    prompt = await self.get_prompt(prompt_id, tenant_id)

    analytics_col = get_mongo_collection("prompt_usage_analytics")

    # Build query
    query = {"prompt_id": prompt_id, "tenant_id": tenant_id}
    if start_date:
        query["timestamp"] = {"$gte": start_date}
    if end_date:
        query.setdefault("timestamp", {})["$lte"] = end_date

    # Get usage records
    usage_records = await analytics_col.find(query).to_list(length=1000)

    # Calculate metrics
    total_uses = len(usage_records)
    successful_uses = sum(1 for r in usage_records if r.get("success"))
    success_rate = (successful_uses / total_uses * 100) if total_uses > 0 else 0

    # Context breakdown
    context_breakdown = {}
    for record in usage_records:
        context = record.get("context", "unknown")
        context_breakdown[context] = context_breakdown.get(context, 0) + 1

    # Variable usage frequency
    variable_usage = {}
    for record in usage_records:
        for var_name in record.get("variables_used", {}).keys():
            variable_usage[var_name] = variable_usage.get(var_name, 0) + 1

    # Most active users
    user_usage = {}
    for record in usage_records:
        user_id = record.get("user_id")
        user_usage[user_id] = user_usage.get(user_id, 0) + 1

    top_users = sorted(user_usage.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "prompt_id": prompt_id,
        "total_uses": total_uses,
        "successful_uses": successful_uses,
        "success_rate": round(success_rate, 2),
        "context_breakdown": context_breakdown,
        "variable_usage": variable_usage,
        "top_users": [{"user_id": uid, "count": count} for uid, count in top_users],
        "last_used_at": prompt.last_used_at
    }

async def get_tenant_analytics(
    self,
    tenant_id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> Dict[str, Any]:
    """Get overall analytics for tenant."""

    analytics_col = get_mongo_collection("prompt_usage_analytics")

    query = {"tenant_id": tenant_id}
    if start_date:
        query["timestamp"] = {"$gte": start_date}
    if end_date:
        query.setdefault("timestamp", {})["$lte"] = end_date

    usage_records = await analytics_col.find(query).to_list(length=10000)

    # Most used prompts
    prompt_usage = {}
    for record in usage_records:
        pid = record.get("prompt_id")
        prompt_usage[pid] = prompt_usage.get(pid, 0) + 1

    top_prompts = sorted(prompt_usage.items(), key=lambda x: x[1], reverse=True)[:10]

    # Context usage
    context_breakdown = {}
    for record in usage_records:
        context = record.get("context", "unknown")
        context_breakdown[context] = context_breakdown.get(context, 0) + 1

    # Success metrics
    total_uses = len(usage_records)
    successful = sum(1 for r in usage_records if r.get("success"))

    return {
        "total_prompts_used": len(set(prompt_usage.keys())),
        "total_uses": total_uses,
        "successful_uses": successful,
        "success_rate": round((successful / total_uses * 100) if total_uses > 0 else 0, 2),
        "top_prompts": [{"prompt_id": pid, "uses": count} for pid, count in top_prompts],
        "context_breakdown": context_breakdown
    }
```

**Acceptance Criteria**:
- [ ] Usage tracking is non-blocking
- [ ] Analytics queries are efficient
- [ ] Metrics are accurate
- [ ] Date filtering works
- [ ] Top users/prompts are calculated correctly

---

## Phase 3: Backend API

### Task 3.1: Create Prompt CRUD Endpoints
**Objective**: Expose prompt management via REST API

**Files to Create**:
- `backend/src/api/v1/prompts.py`

**Implementation**:
```python
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from ...db.postgres import get_db
from ...schemas.prompt import (
    PromptTemplateCreate,
    PromptTemplateUpdate,
    PromptTemplateResponse,
    PromptListResponse,
    PromptCategoryCreate,
    PromptCategoryResponse,
    PromptRenderRequest,
    PromptRenderResponse,
    PromptVersionResponse
)
from ...services.prompt_service import PromptService
from ...api.middleware.auth import require_auth

router = APIRouter()

@router.post("", response_model=PromptTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_prompt(
    request: PromptTemplateCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Create a new prompt template.

    - **name**: Unique prompt name
    - **description**: Optional description
    - **content**: Prompt content with {variables}
    - **category_id**: Optional category
    - **tags**: Optional list of tags
    - **is_public**: Make available to all users
    """
    service = PromptService(db)
    prompt = await service.create_prompt(
        request,
        user_id=current_user["user_id"],
        tenant_id=current_user["tenant_id"]
    )
    return PromptTemplateResponse.from_orm(prompt)

@router.get("", response_model=PromptListResponse)
async def list_prompts(
    page: int = 1,
    page_size: int = 20,
    category_id: Optional[int] = None,
    search: Optional[str] = None,
    tags: Optional[str] = Query(None, description="Comma-separated tags"),
    only_favorites: bool = False,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    List prompt templates with filtering and pagination.

    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20, max: 100)
    - **category_id**: Filter by category
    - **search**: Search in name, description, content
    - **tags**: Filter by tags (comma-separated)
    - **only_favorites**: Show only favorited prompts
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
        only_favorites=only_favorites
    )

    # Map prompts to responses with favorite status
    prompts_response = []
    for prompt in result["prompts"]:
        p_response = PromptTemplateResponse.from_orm(prompt)
        p_response.is_favorited = prompt.id in result["favorite_ids"]
        prompts_response.append(p_response)

    return PromptListResponse(
        prompts=prompts_response,
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"]
    )

@router.get("/{prompt_id}", response_model=PromptTemplateResponse)
async def get_prompt(
    prompt_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Get a prompt template by ID."""
    service = PromptService(db)
    prompt = await service.get_prompt(prompt_id, current_user["tenant_id"])

    # Check favorite status
    response = PromptTemplateResponse.from_orm(prompt)
    favorites = service._get_user_favorites(current_user["user_id"])
    response.is_favorited = prompt_id in favorites

    return response

@router.put("/{prompt_id}", response_model=PromptTemplateResponse)
async def update_prompt(
    prompt_id: int,
    request: PromptTemplateUpdate,
    create_version: bool = Query(True, description="Create version on content change"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Update a prompt template."""
    service = PromptService(db)
    prompt = await service.update_prompt(
        prompt_id=prompt_id,
        data=request,
        user_id=current_user["user_id"],
        tenant_id=current_user["tenant_id"],
        create_version=create_version
    )
    return PromptTemplateResponse.from_orm(prompt)

@router.delete("/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prompt(
    prompt_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Soft delete a prompt template."""
    service = PromptService(db)
    await service.delete_prompt(
        prompt_id=prompt_id,
        user_id=current_user["user_id"],
        tenant_id=current_user["tenant_id"]
    )
```

**Files to Update**:
- `backend/src/api/v1/__init__.py` - Register prompts router

**Acceptance Criteria**:
- [ ] All CRUD endpoints work
- [ ] Proper authentication/authorization
- [ ] Tenant isolation enforced
- [ ] API documentation is generated
- [ ] Response models match schemas

---

### Task 3.2: Add Prompt Rendering Endpoint
**Objective**: Expose prompt rendering via API

**Implementation**:
```python
@router.post("/{prompt_id}/render", response_model=PromptRenderResponse)
async def render_prompt(
    prompt_id: int,
    request: PromptRenderRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Render a prompt by substituting variables.

    - **variables**: Dictionary of variable values

    Returns rendered content with any warnings or missing variables.
    """
    service = PromptService(db)
    result = await service.render_prompt(
        prompt_id=prompt_id,
        variables=request.variables,
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"],
        track_usage=True
    )

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"errors": result["errors"]}
        )

    return PromptRenderResponse(
        rendered_content=result["rendered_content"],
        missing_variables=result["missing_variables"],
        warnings=result["warnings"]
    )
```

**Acceptance Criteria**:
- [ ] Renders prompts correctly
- [ ] Validates variables
- [ ] Returns clear error messages
- [ ] Tracks usage in analytics

---

### Task 3.3: Add Version Management Endpoints
**Objective**: Manage prompt versions via API

**Implementation**:
```python
@router.get("/{prompt_id}/versions", response_model=List[PromptVersionResponse])
async def get_version_history(
    prompt_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Get version history for a prompt."""
    service = PromptService(db)
    versions = await service.get_version_history(
        prompt_id=prompt_id,
        tenant_id=current_user["tenant_id"]
    )
    return [PromptVersionResponse.from_orm(v) for v in versions]

@router.post("/{prompt_id}/versions", response_model=PromptTemplateResponse)
async def create_new_version(
    prompt_id: int,
    content: str,
    change_summary: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Create a new version of a prompt."""
    service = PromptService(db)
    prompt = await service.create_new_version(
        prompt_id=prompt_id,
        content=content,
        change_summary=change_summary,
        user_id=current_user["user_id"],
        tenant_id=current_user["tenant_id"]
    )
    return PromptTemplateResponse.from_orm(prompt)

@router.post("/{prompt_id}/versions/{version}/restore", response_model=PromptTemplateResponse)
async def restore_version(
    prompt_id: int,
    version: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Restore a prompt to a specific version."""
    service = PromptService(db)
    prompt = await service.restore_version(
        prompt_id=prompt_id,
        version_number=version,
        user_id=current_user["user_id"],
        tenant_id=current_user["tenant_id"]
    )
    return PromptTemplateResponse.from_orm(prompt)
```

**Acceptance Criteria**:
- [ ] Version history retrieval works
- [ ] New versions can be created
- [ ] Versions can be restored
- [ ] Change summaries are preserved

---

### Task 3.4: Add Category Management Endpoints
**Objective**: Manage prompt categories

**Implementation**:
```python
@router.post("/categories", response_model=PromptCategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    request: PromptCategoryCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Create a new prompt category."""
    service = PromptService(db)
    category = await service.create_category(
        request,
        tenant_id=current_user["tenant_id"]
    )
    return PromptCategoryResponse.from_orm(category)

@router.get("/categories", response_model=List[PromptCategoryResponse])
async def list_categories(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """List all prompt categories."""
    service = PromptService(db)
    categories = await service.list_categories(tenant_id=current_user["tenant_id"])
    return [PromptCategoryResponse.from_orm(c) for c in categories]
```

**Acceptance Criteria**:
- [ ] Categories can be created
- [ ] Categories can be listed
- [ ] Categories can be updated/deleted
- [ ] Tenant isolation works

---

### Task 3.5: Add Favorite Management Endpoints
**Objective**: Allow users to favorite prompts

**Implementation**:
```python
@router.post("/{prompt_id}/favorite", status_code=status.HTTP_204_NO_CONTENT)
async def add_favorite(
    prompt_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Add prompt to favorites."""
    service = PromptService(db)
    await service.add_favorite(
        prompt_id=prompt_id,
        user_id=current_user["user_id"],
        tenant_id=current_user["tenant_id"]
    )

@router.delete("/{prompt_id}/favorite", status_code=status.HTTP_204_NO_CONTENT)
async def remove_favorite(
    prompt_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Remove prompt from favorites."""
    service = PromptService(db)
    await service.remove_favorite(
        prompt_id=prompt_id,
        user_id=current_user["user_id"]
    )
```

**Acceptance Criteria**:
- [ ] Favorites can be added
- [ ] Favorites can be removed
- [ ] Duplicate favorites are prevented
- [ ] Only user's own favorites are affected

---

### Task 3.6: Add Analytics Endpoints
**Objective**: Expose prompt analytics

**Implementation**:
```python
@router.get("/{prompt_id}/analytics")
async def get_prompt_analytics(
    prompt_id: int,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Get analytics for a specific prompt."""
    from datetime import datetime

    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None

    service = PromptService(db)
    analytics = await service.get_prompt_analytics(
        prompt_id=prompt_id,
        tenant_id=current_user["tenant_id"],
        start_date=start,
        end_date=end
    )
    return analytics

@router.get("/analytics/tenant")
async def get_tenant_analytics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Get overall analytics for tenant."""
    from datetime import datetime

    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None

    service = PromptService(db)
    analytics = await service.get_tenant_analytics(
        tenant_id=current_user["tenant_id"],
        start_date=start,
        end_date=end
    )
    return analytics
```

**Acceptance Criteria**:
- [ ] Prompt-specific analytics work
- [ ] Tenant-wide analytics work
- [ ] Date filtering is accurate
- [ ] Metrics are calculated correctly

---

## Phase 4: Chat Integration

### Task 4.1: Extend ChatService for Prompt Support
**Objective**: Allow using prompts in chat conversations

**Files to Update**:
- `backend/src/services/chat_service.py`

**Implementation**:
```python
async def send_message_from_prompt(
    self,
    session_id: int,
    prompt_id: int,
    variables: Dict[str, Any],
    user_id: int,
    tenant_id: int,
    store_user_message: bool = True
) -> ChatMessageResponse:
    """
    Send a chat message using a prompt template.

    Args:
        session_id: Chat session ID
        prompt_id: Prompt template ID
        variables: Variable values for rendering
        user_id: Current user ID
        tenant_id: Current tenant ID
        store_user_message: Whether to store rendered content as user message

    Returns:
        ChatMessageResponse with AI response
    """
    from ..services.prompt_service import PromptService

    prompt_service = PromptService(self.db)

    # Render prompt
    render_result = await prompt_service.render_prompt(
        prompt_id=prompt_id,
        variables=variables,
        tenant_id=tenant_id,
        user_id=user_id,
        track_usage=True
    )

    if not render_result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"errors": render_result["errors"]}
        )

    rendered_content = render_result["rendered_content"]

    # Store user message if requested
    if store_user_message:
        await self.send_message(ChatMessageCreate(
            session_id=session_id,
            role="user",
            content=rendered_content,
            metadata={"source": "prompt", "prompt_id": prompt_id}
        ))

    # Get chat history
    history = await self.get_messages(session_id)
    session = await self.get_session(session_id)

    # Build LLM messages
    llm_messages = []
    if session.system_prompt:
        llm_messages.append({"role": "system", "content": session.system_prompt})
    for msg in history:
        if msg.role in ("user", "assistant"):
            llm_messages.append({"role": msg.role, "content": msg.content})

    # Generate AI response
    response_text = await self.llm_service.chat_completion(
        provider_id=session.llm_provider_id,
        messages=llm_messages
    )

    # Store assistant response
    return await self.send_message(ChatMessageCreate(
        session_id=session_id,
        role="assistant",
        content=response_text,
        metadata={"prompt_id": prompt_id}
    ))
```

**Acceptance Criteria**:
- [ ] Prompts render correctly in chat context
- [ ] Variables are properly substituted
- [ ] Chat history is maintained
- [ ] Usage is tracked with "chat" context
- [ ] Error handling works

---

### Task 4.2: Add Chat Prompt Endpoints
**Objective**: API endpoints for using prompts in chat

**Files to Update**:
- `backend/src/api/v1/chat.py`

**Implementation**:
```python
from ..schemas.prompt import PromptRenderRequest

@router.post("/sessions/{session_id}/from-prompt", response_model=ChatMessageResponse)
async def send_message_from_prompt(
    session_id: int,
    prompt_id: int,
    variables: Dict[str, Any],
    store_user_message: bool = True,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Send a chat message using a prompt template.

    - **prompt_id**: ID of prompt template to use
    - **variables**: Variable values for rendering
    - **store_user_message**: Whether to store rendered prompt as user message
    """
    llm_service = LLMService(db)
    chat_service = ChatService(db, llm_service)

    response = await chat_service.send_message_from_prompt(
        session_id=session_id,
        prompt_id=prompt_id,
        variables=variables,
        user_id=current_user["user_id"],
        tenant_id=current_user["tenant_id"],
        store_user_message=store_user_message
    )

    return response

@router.get("/sessions/{session_id}/suggested-prompts")
async def get_suggested_prompts(
    session_id: int,
    limit: int = 5,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Get suggested prompts based on chat context.

    Uses chat history and common patterns to suggest relevant prompts.
    """
    from ..services.prompt_service import PromptService

    chat_service = ChatService(db, None)
    prompt_service = PromptService(db)

    # Get recent messages
    messages = await chat_service.get_messages(session_id)
    recent_messages = messages[-3:] if len(messages) >= 3 else messages

    # Extract keywords/topics from recent messages
    keywords = []
    for msg in recent_messages:
        # Simple keyword extraction (could be enhanced with NLP)
        words = msg.content.lower().split()
        keywords.extend([w for w in words if len(w) > 4])

    # Find prompts with matching tags or content
    result = await prompt_service.list_prompts(
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"],
        page=1,
        page_size=limit,
        tags=list(set(keywords[:5]))  # Top 5 keywords
    )

    return {"suggested_prompts": result["prompts"][:limit]}
```

**Acceptance Criteria**:
- [ ] Prompt can be used in chat
- [ ] Variables are validated
- [ ] Chat history is preserved
- [ ] Suggestions are contextually relevant

---

### Task 4.3: Add Prompt Quick Actions in Chat
**Objective**: UI integration for quick prompt usage

**Implementation Strategy**:
- Add "Use Prompt" button in chat interface
- Modal to select prompt and fill variables
- Auto-populate chat input with rendered content
- Track prompt usage in chat context

**Files to Create** (Frontend):
- `frontend/src/components/prompts/PromptSelectorModal.tsx`
- `frontend/src/components/prompts/PromptVariableForm.tsx`

*Note: Frontend implementation details in Phase 6*

**Acceptance Criteria**:
- [ ] Button appears in chat interface
- [ ] Modal opens with prompt list
- [ ] Variables can be filled
- [ ] Rendered content populates chat input

---

## Phase 5: Task Integration

### Task 5.1: Extend TaskService for Prompt Support
**Objective**: Generate task fields from prompts

**Files to Update**:
- `backend/src/services/task_service.py`

**Implementation**:
```python
async def create_task_from_prompt(
    self,
    prompt_id: int,
    variables: Dict[str, Any],
    user_id: int,
    tenant_id: int,
    crew_id: Optional[int] = None,
    agent_id: Optional[int] = None,
    additional_fields: Optional[Dict[str, Any]] = None
) -> Task:
    """
    Create a task using a prompt template.

    The prompt content is used to generate task description and expected output.
    Supports special format:

    DESCRIPTION:
    {task description content}

    EXPECTED OUTPUT:
    {expected output content}

    Or just uses entire content as description if no markers found.
    """
    from ..services.prompt_service import PromptService

    prompt_service = PromptService(self.db)

    # Render prompt
    render_result = await prompt_service.render_prompt(
        prompt_id=prompt_id,
        variables=variables,
        tenant_id=tenant_id,
        user_id=user_id,
        track_usage=True
    )

    if not render_result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"errors": render_result["errors"]}
        )

    rendered_content = render_result["rendered_content"]

    # Parse content for description and expected output
    description, expected_output = self._parse_task_content(rendered_content)

    # Create task
    task_data = {
        "name": additional_fields.get("name", f"Task from prompt {prompt_id}"),
        "description": description,
        "expected_output": expected_output,
        "crew_id": crew_id,
        "agent_id": agent_id,
        **(additional_fields or {})
    }

    task = await self.create_task(TaskCreate(**task_data))

    return task

def _parse_task_content(self, content: str) -> tuple[str, str]:
    """
    Parse rendered prompt content into description and expected output.

    Supports formats:
    1. DESCRIPTION: ... EXPECTED OUTPUT: ...
    2. ## Description ... ## Expected Output ...
    3. Just content (uses first 70% as description, rest as expected output)
    """

    # Try format 1: DESCRIPTION: ... EXPECTED OUTPUT: ...
    pattern1 = r'DESCRIPTION:\s*(.+?)\s*EXPECTED\s+OUTPUT:\s*(.+)'
    match = re.search(pattern1, content, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip(), match.group(2).strip()

    # Try format 2: ## Description ... ## Expected Output ...
    pattern2 = r'##\s*Description\s*(.+?)\s*##\s*Expected\s+Output\s*(.+)'
    match = re.search(pattern2, content, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip(), match.group(2).strip()

    # Fallback: Split content (70/30)
    lines = content.split('\n')
    split_point = int(len(lines) * 0.7)
    description = '\n'.join(lines[:split_point]).strip()
    expected_output = '\n'.join(lines[split_point:]).strip()

    if not expected_output:
        expected_output = "Complete the task as described above."

    return description, expected_output
```

**Acceptance Criteria**:
- [ ] Tasks can be created from prompts
- [ ] Content parsing works for all formats
- [ ] Variables are substituted correctly
- [ ] Additional task fields can be provided
- [ ] Usage is tracked with "task" context

---

### Task 5.2: Add Task Creation from Prompt Endpoint
**Objective**: API endpoint for creating tasks from prompts

**Files to Update**:
- `backend/src/api/v1/tasks.py`

**Implementation**:
```python
from ..schemas.prompt import PromptRenderRequest

@router.post("/from-prompt", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task_from_prompt(
    prompt_id: int,
    variables: Dict[str, Any],
    crew_id: Optional[int] = None,
    agent_id: Optional[int] = None,
    name: Optional[str] = None,
    order: int = 0,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Create a task using a prompt template.

    - **prompt_id**: ID of prompt template
    - **variables**: Variable values for rendering
    - **crew_id**: Optional crew to assign to
    - **agent_id**: Optional agent to assign to
    - **name**: Optional task name (defaults to prompt-based name)
    - **order**: Task order in crew

    The prompt content should contain DESCRIPTION and EXPECTED OUTPUT sections,
    or the content will be intelligently split.
    """
    task_service = TaskService(db)

    additional_fields = {}
    if name:
        additional_fields["name"] = name
    if order:
        additional_fields["order"] = order

    task = await task_service.create_task_from_prompt(
        prompt_id=prompt_id,
        variables=variables,
        user_id=current_user["user_id"],
        tenant_id=current_user["tenant_id"],
        crew_id=crew_id,
        agent_id=agent_id,
        additional_fields=additional_fields
    )

    return TaskResponse.from_orm(task)

@router.get("/prompt-templates")
async def get_task_prompt_templates(
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Get prompt templates suitable for task creation.

    Filters prompts by 'task' category or tag.
    """
    from ..services.prompt_service import PromptService

    prompt_service = PromptService(db)

    result = await prompt_service.list_prompts(
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"],
        page=1,
        page_size=50,
        tags=["task"] if not category else [category, "task"]
    )

    return {"templates": result["prompts"]}
```

**Acceptance Criteria**:
- [ ] Tasks are created successfully
- [ ] Prompt variables are validated
- [ ] Description and expected output are parsed
- [ ] Task can be assigned to crew/agent
- [ ] Error handling works

---

### Task 5.3: Add Bulk Task Creation from Prompts
**Objective**: Create multiple tasks from a workflow prompt

**Implementation**:
```python
@router.post("/from-prompt/bulk", response_model=List[TaskResponse])
async def create_tasks_from_prompt_workflow(
    prompt_id: int,
    crew_id: int,
    variables: Dict[str, Any],
    agent_ids: Optional[List[int]] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Create multiple tasks from a workflow prompt.

    The prompt content should contain multiple task definitions:

    TASK 1:
    DESCRIPTION: ...
    EXPECTED OUTPUT: ...

    TASK 2:
    DESCRIPTION: ...
    EXPECTED OUTPUT: ...
    """
    from ..services.prompt_service import PromptService

    prompt_service = PromptService(db)
    task_service = TaskService(db)

    # Render prompt
    render_result = await prompt_service.render_prompt(
        prompt_id=prompt_id,
        variables=variables,
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"],
        track_usage=True
    )

    if not render_result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"errors": render_result["errors"]}
        )

    rendered_content = render_result["rendered_content"]

    # Parse multiple tasks
    task_sections = re.split(r'TASK\s+\d+:', rendered_content, flags=re.IGNORECASE)
    task_sections = [s.strip() for s in task_sections if s.strip()]

    created_tasks = []
    for i, section in enumerate(task_sections):
        description, expected_output = task_service._parse_task_content(section)

        task_data = TaskCreate(
            name=f"Task {i+1} from prompt {prompt_id}",
            description=description,
            expected_output=expected_output,
            crew_id=crew_id,
            agent_id=agent_ids[i % len(agent_ids)] if agent_ids else None,
            order=i
        )

        task = await task_service.create_task(task_data)
        created_tasks.append(TaskResponse.from_orm(task))

    return created_tasks
```

**Acceptance Criteria**:
- [ ] Multiple tasks can be created from one prompt
- [ ] Tasks are ordered correctly
- [ ] Agents are assigned round-robin
- [ ] All tasks are associated with crew

---

## Phase 6: Frontend UI

### Task 6.1: Create Prompts List Page
**Objective**: Main page for browsing and managing prompts

**Files to Create**:
- `frontend/src/app/prompts/page.tsx`
- `frontend/src/components/prompts/PromptsList.tsx`
- `frontend/src/components/prompts/PromptCard.tsx`

**Implementation Structure**:
```typescript
// frontend/src/app/prompts/page.tsx
'use client';

import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api-client';
import ProtectedRoute from '@/components/auth/ProtectedRoute';
import Navigation from '@/components/shared/Navigation';
import PromptsList from '@/components/prompts/PromptsList';
import PromptEditor from '@/components/prompts/PromptEditor';
import { Plus, Search, Filter } from 'lucide-react';

export default function PromptsPage() {
  const [prompts, setPrompts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<number | null>(null);
  const [showEditor, setShowEditor] = useState(false);
  const [editingPrompt, setEditingPrompt] = useState(null);

  // Load prompts, filters, etc.
  // ...

  return (
    <ProtectedRoute>
      <div className="flex h-screen">
        <Navigation />
        <div className="flex-1 overflow-auto">
          {/* Header */}
          <div className="border-b px-6 py-4">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-2xl font-bold">Prompts</h1>
                <p className="text-gray-500">Reusable prompt templates for chat and tasks</p>
              </div>
              <button
                onClick={() => { setEditingPrompt(null); setShowEditor(true); }}
                className="btn-primary"
              >
                <Plus size={20} />
                New Prompt
              </button>
            </div>

            {/* Search and Filters */}
            <div className="mt-4 flex gap-4">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={20} />
                <input
                  type="text"
                  placeholder="Search prompts..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border rounded-lg"
                />
              </div>
              <select
                value={selectedCategory || ''}
                onChange={(e) => setSelectedCategory(e.target.value ? parseInt(e.target.value) : null)}
                className="px-4 py-2 border rounded-lg"
              >
                <option value="">All Categories</option>
                {/* Map categories */}
              </select>
            </div>
          </div>

          {/* Prompts List */}
          <div className="p-6">
            <PromptsList
              prompts={prompts}
              onEdit={(p) => { setEditingPrompt(p); setShowEditor(true); }}
              onDelete={handleDelete}
              onToggleFavorite={handleToggleFavorite}
            />
          </div>
        </div>
      </div>

      {/* Editor Modal */}
      {showEditor && (
        <PromptEditor
          prompt={editingPrompt}
          onClose={() => setShowEditor(false)}
          onSave={handleSave}
        />
      )}
    </ProtectedRoute>
  );
}
```

**Features**:
- Grid/list view toggle
- Search by name, description, content
- Filter by category, tags
- Sort by name, created date, usage
- Favorite indicators
- Quick actions (edit, delete, duplicate, use)

**Acceptance Criteria**:
- [ ] Prompts load and display correctly
- [ ] Search works in real-time
- [ ] Filters apply correctly
- [ ] Pagination works
- [ ] Responsive design

---

### Task 6.2: Create Prompt Editor Modal
**Objective**: Form for creating/editing prompts

**Files to Create**:
- `frontend/src/components/prompts/PromptEditor.tsx`
- `frontend/src/components/prompts/VariablePreview.tsx`

**Features**:
- Name, description, content fields
- Category selector
- Tags input (comma-separated or chips)
- Variable preview (auto-detected)
- Content preview with sample variables
- Version history viewer
- Public/private toggle
- Save, cancel, save as new version

**Implementation Highlights**:
```typescript
export default function PromptEditor({ prompt, onClose, onSave }) {
  const [form, setForm] = useState({
    name: prompt?.name || '',
    description: prompt?.description || '',
    content: prompt?.content || '',
    category_id: prompt?.category_id || null,
    tags: prompt?.tags || [],
    is_public: prompt?.is_public || false
  });

  const [variables, setVariables] = useState([]);
  const [previewVariables, setPreviewVariables] = useState({});
  const [renderedPreview, setRenderedPreview] = useState('');

  // Auto-detect variables on content change
  useEffect(() => {
    const detected = extractVariables(form.content);
    setVariables(detected);
  }, [form.content]);

  // Render preview with sample values
  const updatePreview = () => {
    const rendered = renderPrompt(form.content, previewVariables);
    setRenderedPreview(rendered);
  };

  const handleSave = async () => {
    if (prompt) {
      await apiClient.put(`/api/v1/prompts/${prompt.id}`, form);
    } else {
      await apiClient.post('/api/v1/prompts', form);
    }
    onSave();
    onClose();
  };

  return (
    <Modal isOpen onClose={onClose} size="xl">
      <div className="p-6">
        <h2 className="text-xl font-bold mb-4">
          {prompt ? 'Edit Prompt' : 'New Prompt'}
        </h2>

        {/* Form fields */}
        <div className="space-y-4">
          <div>
            <label>Name</label>
            <input
              type="text"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="w-full px-4 py-2 border rounded"
            />
          </div>

          <div>
            <label>Content</label>
            <textarea
              value={form.content}
              onChange={(e) => setForm({ ...form, content: e.target.value })}
              rows={10}
              placeholder="Enter prompt content with {variables}..."
              className="w-full px-4 py-2 border rounded font-mono"
            />
          </div>

          {/* Variable Preview */}
          {variables.length > 0 && (
            <div className="p-4 bg-gray-50 rounded">
              <h3 className="font-medium mb-2">Detected Variables:</h3>
              <div className="space-y-2">
                {variables.map(v => (
                  <div key={v.name} className="flex items-center gap-2">
                    <code className="text-sm bg-white px-2 py-1 rounded">{`{${v.name}}`}</code>
                    <input
                      type="text"
                      placeholder="Sample value for preview"
                      onChange={(e) => setPreviewVariables({ ...previewVariables, [v.name]: e.target.value })}
                      className="flex-1 px-2 py-1 border rounded text-sm"
                    />
                  </div>
                ))}
              </div>
              <button
                onClick={updatePreview}
                className="mt-2 text-sm text-blue-600 hover:text-blue-700"
              >
                Update Preview
              </button>
            </div>
          )}

          {/* Rendered Preview */}
          {renderedPreview && (
            <div className="p-4 border rounded">
              <h3 className="font-medium mb-2">Preview:</h3>
              <div className="prose prose-sm">{renderedPreview}</div>
            </div>
          )}

          {/* Actions */}
          <div className="flex justify-end gap-2">
            <button onClick={onClose} className="btn-secondary">Cancel</button>
            <button onClick={handleSave} className="btn-primary">Save</button>
          </div>
        </div>
      </div>
    </Modal>
  );
}
```

**Acceptance Criteria**:
- [ ] Form validates input
- [ ] Variables are auto-detected
- [ ] Preview updates correctly
- [ ] Save/update works
- [ ] Modal closes on save or cancel

---

### Task 6.3: Add Prompt Selector to Chat
**Objective**: Quick access to prompts in chat interface

**Files to Update**:
- `frontend/src/components/chat/ChatWindow.tsx`
- `frontend/src/components/chat/PromptQuickPicker.tsx`

**Features**:
- "Use Prompt" button near chat input
- Dropdown or modal with prompt list
- Search/filter prompts
- Variable input form
- Preview rendered content
- Insert into chat input

**Implementation**:
```typescript
// In ChatWindow.tsx
<div className="chat-input-area">
  <PromptQuickPicker
    onSelect={async (prompt, variables) => {
      const rendered = await renderPrompt(prompt.id, variables);
      setInput(rendered.rendered_content);
    }}
  />

  <textarea
    value={input}
    onChange={(e) => setInput(e.target.value)}
    placeholder="Message..."
  />

  <button onClick={handleSend}>Send</button>
</div>
```

**Acceptance Criteria**:
- [ ] Button is accessible
- [ ] Prompt list loads quickly
- [ ] Variables can be filled
- [ ] Rendered content populates input
- [ ] User can edit before sending

---

### Task 6.4: Add Prompt Selector to Task Form
**Objective**: Create tasks from prompts

**Files to Update**:
- `frontend/src/components/tasks/TaskForm.tsx`
- `frontend/src/components/tasks/PromptTaskGenerator.tsx`

**Features**:
- "From Prompt" button/tab in task creation
- Prompt selector
- Variable input form
- Auto-populate description and expected_output fields
- User can edit generated fields before saving

**Implementation**:
```typescript
export default function TaskForm({ crew, onSave }) {
  const [mode, setMode] = useState<'manual' | 'prompt'>('manual');
  const [selectedPrompt, setSelectedPrompt] = useState(null);
  const [form, setForm] = useState({
    name: '',
    description: '',
    expected_output: '',
    // ...
  });

  const handlePromptSelect = async (prompt, variables) => {
    const result = await apiClient.post('/api/v1/tasks/from-prompt', {
      prompt_id: prompt.id,
      variables,
      crew_id: crew.id,
      name: form.name || prompt.name
    });

    // Populate form with generated content
    setForm({
      ...form,
      description: result.description,
      expected_output: result.expected_output
    });
  };

  return (
    <div>
      {/* Mode Toggle */}
      <div className="tabs">
        <button onClick={() => setMode('manual')}>Manual</button>
        <button onClick={() => setMode('prompt')}>From Prompt</button>
      </div>

      {mode === 'manual' ? (
        <div>
          {/* Manual form fields */}
        </div>
      ) : (
        <PromptTaskGenerator
          onGenerate={handlePromptSelect}
          initialForm={form}
          onFormChange={setForm}
        />
      )}

      <button onClick={() => onSave(form)}>Save Task</button>
    </div>
  );
}
```

**Acceptance Criteria**:
- [ ] Toggle between manual and prompt modes
- [ ] Prompt generates fields correctly
- [ ] User can edit generated content
- [ ] Task saves with correct data

---

### Task 6.5: Create Prompt Analytics Dashboard
**Objective**: Visualize prompt usage and effectiveness

**Files to Create**:
- `frontend/src/components/prompts/PromptAnalytics.tsx`
- `frontend/src/components/prompts/AnalyticsCharts.tsx`

**Features**:
- Usage metrics (total uses, success rate)
- Context breakdown (chat vs task vs direct)
- Top users
- Variable usage frequency
- Time-series usage chart
- Comparison between prompts

**Implementation**:
```typescript
export default function PromptAnalytics({ promptId }) {
  const [analytics, setAnalytics] = useState(null);
  const [dateRange, setDateRange] = useState({ start: null, end: null });

  useEffect(() => {
    const fetchAnalytics = async () => {
      const params = new URLSearchParams();
      if (dateRange.start) params.append('start_date', dateRange.start);
      if (dateRange.end) params.append('end_date', dateRange.end);

      const res = await apiClient.get(`/api/v1/prompts/${promptId}/analytics?${params}`);
      setAnalytics(res.data);
    };

    fetchAnalytics();
  }, [promptId, dateRange]);

  if (!analytics) return <div>Loading...</div>;

  return (
    <div className="space-y-6">
      {/* Date Range Picker */}
      <DateRangePicker onChange={setDateRange} />

      {/* Metrics Cards */}
      <div className="grid grid-cols-4 gap-4">
        <MetricCard title="Total Uses" value={analytics.total_uses} />
        <MetricCard title="Success Rate" value={`${analytics.success_rate}%`} />
        <MetricCard title="Unique Users" value={analytics.top_users.length} />
        <MetricCard title="Avg. Usage/Day" value={calculateAvg(analytics)} />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-2 gap-6">
        <ContextBreakdownChart data={analytics.context_breakdown} />
        <VariableUsageChart data={analytics.variable_usage} />
      </div>

      {/* Top Users Table */}
      <TopUsersTable users={analytics.top_users} />
    </div>
  );
}
```

**Acceptance Criteria**:
- [ ] Analytics load correctly
- [ ] Charts render properly
- [ ] Date range filtering works
- [ ] Metrics are accurate
- [ ] Responsive design

---

### Task 6.6: Implement Search and Filtering
**Objective**: Powerful search and filter capabilities

**Features**:
- Full-text search across name, description, content
- Filter by category, tags, public/private, favorites
- Sort by name, created date, updated date, usage count
- Debounced search for performance
- Clear filters button

**Implementation** (in PromptsList component):
```typescript
const [filters, setFilters] = useState({
  search: '',
  category_id: null,
  tags: [],
  only_favorites: false,
  sort_by: 'created_at',
  sort_order: 'desc'
});

const debouncedSearch = useDebounce(filters.search, 300);

useEffect(() => {
  const fetchPrompts = async () => {
    const params = new URLSearchParams();
    params.append('page', page);
    params.append('page_size', pageSize);
    if (debouncedSearch) params.append('search', debouncedSearch);
    if (filters.category_id) params.append('category_id', filters.category_id);
    if (filters.tags.length) params.append('tags', filters.tags.join(','));
    if (filters.only_favorites) params.append('only_favorites', 'true');

    const res = await apiClient.get(`/api/v1/prompts?${params}`);
    setPrompts(res.data.prompts);
    setTotal(res.data.total);
  };

  fetchPrompts();
}, [debouncedSearch, filters, page]);
```

**Acceptance Criteria**:
- [ ] Search is debounced
- [ ] Filters apply correctly
- [ ] Sort works as expected
- [ ] Clear filters resets all
- [ ] URL params sync with filters (optional)

---

## Phase 7: Testing & Polish

### Task 7.1: Write Unit Tests for PromptService
**Objective**: Comprehensive unit tests

**Files to Create**:
- `backend/tests/services/test_prompt_service.py`

**Test Coverage**:
```python
import pytest
from unittest.mock import Mock, patch
from backend.src.services.prompt_service import PromptService

class TestPromptService:
    def test_create_prompt(self, db_session):
        """Test creating a new prompt."""
        service = PromptService(db_session)
        # ...

    def test_extract_variables(self):
        """Test variable extraction from content."""
        service = PromptService(Mock())

        content = "Hello {name}, you are {age:number} years old."
        variables = service._extract_variables(content)

        assert "name" in variables
        assert "age" in variables
        assert variables["age"]["type"] == "number"

    def test_render_prompt_with_variables(self, db_session, sample_prompt):
        """Test rendering prompt with variables."""
        service = PromptService(db_session)

        result = await service.render_prompt(
            prompt_id=sample_prompt.id,
            variables={"name": "John", "age": 30},
            tenant_id=1,
            user_id=1
        )

        assert result["success"] == True
        assert "John" in result["rendered_content"]
        assert "30" in result["rendered_content"]

    def test_version_control(self, db_session, sample_prompt):
        """Test creating and restoring versions."""
        service = PromptService(db_session)

        # Create new version
        updated = await service.create_new_version(
            prompt_id=sample_prompt.id,
            content="Updated content",
            change_summary="Test update",
            user_id=1,
            tenant_id=1
        )

        assert updated.version == 2

        # Restore old version
        restored = await service.restore_version(
            prompt_id=sample_prompt.id,
            version_number=1,
            user_id=1,
            tenant_id=1
        )

        assert restored.content == sample_prompt.content
        assert restored.version == 3  # New version created

    # More tests...
```

**Test Coverage Goals**:
- [ ] Create, update, delete prompts
- [ ] Variable extraction and validation
- [ ] Prompt rendering
- [ ] Version control
- [ ] Favorites management
- [ ] Analytics tracking
- [ ] Error handling

---

### Task 7.2: Write Integration Tests for API
**Objective**: End-to-end API tests

**Files to Create**:
- `backend/tests/api/test_prompts_api.py`

**Test Scenarios**:
```python
def test_create_prompt_endpoint(client, auth_headers):
    """Test POST /api/v1/prompts"""
    response = client.post(
        "/api/v1/prompts",
        json={
            "name": "Test Prompt",
            "content": "Hello {name}",
            "category_id": 1,
            "tags": ["test"],
            "is_public": False
        },
        headers=auth_headers
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Prompt"
    assert "name" in data["variables"]

def test_render_prompt_endpoint(client, auth_headers, sample_prompt):
    """Test POST /api/v1/prompts/{id}/render"""
    response = client.post(
        f"/api/v1/prompts/{sample_prompt.id}/render",
        json={
            "variables": {"name": "Alice"}
        },
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert "Alice" in data["rendered_content"]

def test_unauthorized_access(client, sample_prompt):
    """Test that unauthorized users cannot access prompts"""
    response = client.get(f"/api/v1/prompts/{sample_prompt.id}")
    assert response.status_code == 401

# More integration tests...
```

**Test Coverage**:
- [ ] All CRUD endpoints
- [ ] Rendering endpoint
- [ ] Version endpoints
- [ ] Analytics endpoints
- [ ] Authorization checks
- [ ] Validation errors
- [ ] Edge cases

---

### Task 7.3: Add Import/Export Functionality
**Objective**: Allow sharing prompts via JSON

**Implementation**:

**Export**:
```python
@router.get("/{prompt_id}/export")
async def export_prompt(
    prompt_id: int,
    include_versions: bool = False,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Export prompt as JSON."""
    service = PromptService(db)
    prompt = await service.get_prompt(prompt_id, current_user["tenant_id"])

    export_data = {
        "version": "1.0",
        "prompt": {
            "name": prompt.name,
            "description": prompt.description,
            "content": prompt.content,
            "category": prompt.category.name if prompt.category else None,
            "tags": prompt.tags,
            "variables": prompt.variables
        }
    }

    if include_versions:
        versions = await service.get_version_history(prompt_id, current_user["tenant_id"])
        export_data["versions"] = [
            {
                "version": v.version,
                "content": v.content,
                "change_summary": v.change_summary,
                "created_at": v.created_at.isoformat()
            }
            for v in versions
        ]

    return export_data

@router.post("/import")
async def import_prompt(
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Import prompt from JSON file."""
    import json

    content = await file.read()
    data = json.loads(content)

    service = PromptService(db)

    # Validate format
    if data.get("version") != "1.0":
        raise HTTPException(400, "Unsupported format version")

    prompt_data = data["prompt"]

    # Create prompt
    prompt = await service.create_prompt(
        PromptTemplateCreate(**prompt_data),
        user_id=current_user["user_id"],
        tenant_id=current_user["tenant_id"]
    )

    return {"message": "Prompt imported successfully", "prompt_id": prompt.id}
```

**Acceptance Criteria**:
- [ ] Export produces valid JSON
- [ ] Import validates format
- [ ] Variables are preserved
- [ ] Category mapping works
- [ ] File upload works on frontend

---

### Task 7.4: Create Sample Prompts and Templates
**Objective**: Provide starter prompts for users

**Implementation** (seed data script):
```python
# backend/scripts/seed_prompts.py

SAMPLE_PROMPTS = [
    {
        "name": "Code Review Request",
        "description": "Generate a code review request",
        "content": """Please review the following {language} code:

```{language}
{code}
```

Review focus areas:
1. Code quality and maintainability
2. Performance optimization
3. Security considerations
4. Best practices

DESCRIPTION:
Review the provided {language} code for quality, performance, and security.

EXPECTED OUTPUT:
A detailed code review with specific suggestions for improvement, categorized by severity (critical, moderate, minor).
""",
        "category": "Development",
        "tags": ["code", "review", "development"]
    },
    {
        "name": "Task Breakdown",
        "description": "Break down a complex task into subtasks",
        "content": """Main Task: {main_task}

Context: {context}

DESCRIPTION:
Break down the task "{main_task}" into clear, actionable subtasks with estimated effort and dependencies.

EXPECTED OUTPUT:
A numbered list of subtasks with:
- Clear description
- Estimated time
- Dependencies
- Acceptance criteria
""",
        "category": "Project Management",
        "tags": ["task", "planning", "breakdown"]
    },
    {
        "name": "Meeting Summary",
        "description": "Summarize meeting notes",
        "content": """Meeting: {meeting_title}
Date: {date}
Attendees: {attendees}

Notes:
{notes}

DESCRIPTION:
Summarize the meeting notes, extracting key decisions, action items, and next steps.

EXPECTED OUTPUT:
A structured summary with:
1. Key Decisions
2. Action Items (with owners)
3. Next Steps
4. Open Questions
""",
        "category": "Communication",
        "tags": ["meeting", "summary", "communication"]
    },
    # Add more sample prompts...
]

def seed_sample_prompts(db: Session, tenant_id: int, user_id: int):
    """Seed database with sample prompts."""
    from backend.src.services.prompt_service import PromptService
    from backend.src.schemas.prompt import PromptTemplateCreate

    service = PromptService(db)

    for prompt_data in SAMPLE_PROMPTS:
        try:
            await service.create_prompt(
                PromptTemplateCreate(**prompt_data),
                user_id=user_id,
                tenant_id=tenant_id
            )
            print(f"Created prompt: {prompt_data['name']}")
        except Exception as e:
            print(f"Error creating prompt {prompt_data['name']}: {e}")
```

**Categories to Include**:
- Development (code review, debugging, documentation)
- Project Management (planning, task breakdown, status updates)
- Communication (meeting summaries, emails, announcements)
- Data Analysis (SQL queries, data interpretation, reports)
- Content Creation (blog posts, social media, marketing)
- Customer Support (responses, FAQs, troubleshooting)

**Acceptance Criteria**:
- [ ] At least 20 sample prompts
- [ ] Cover diverse use cases
- [ ] All prompts have proper variables
- [ ] Categorized correctly
- [ ] Work with chat and task integration

---

### Task 7.5: Write Documentation
**Objective**: Comprehensive user and developer documentation

**Files to Create**:
- `docs/PROMPT_REGISTRY.md` - User guide
- `docs/PROMPT_API.md` - API reference
- `docs/PROMPT_INTEGRATION.md` - Integration guide

**Documentation Sections**:

**User Guide** (`PROMPT_REGISTRY.md`):
```markdown
# Prompt Registry - User Guide

## Overview
The Prompt Registry allows you to create and manage reusable prompt templates for chat conversations and task creation.

## Creating a Prompt

1. Navigate to the Prompts page
2. Click "New Prompt"
3. Fill in the form:
   - **Name**: A descriptive name for your prompt
   - **Description**: What this prompt is used for
   - **Content**: The actual prompt text with variables
   - **Category**: Organize prompts by category
   - **Tags**: Add tags for easier searching
   - **Public**: Make available to all users in your organization

### Using Variables

Variables allow dynamic content in your prompts. Use `{variable_name}` syntax:

```
Hello {name},

Your order #{order_id} has been {status}.
```

Supported variable types:
- `{name}` - String variable
- `{age:number}` - Number variable
- `{confirmed:boolean}` - Boolean variable
- `{config:json}` - JSON variable
- `{name=John}` - Variable with default value

## Using Prompts in Chat

1. Open a chat session
2. Click the "Use Prompt" button
3. Select a prompt from the list
4. Fill in the required variables
5. Preview the rendered content
6. Click "Insert" to add to chat input
7. Edit if needed and send

## Creating Tasks from Prompts

1. Navigate to Tasks
2. Click "New Task"
3. Select "From Prompt" tab
4. Choose a prompt template
5. Fill in variables
6. Review generated description and expected output
7. Edit if needed and save

### Prompt Format for Tasks

For best results, structure your prompt like this:

```
DESCRIPTION:
{detailed task description}

EXPECTED OUTPUT:
{what the task should produce}
```

## Version Control

Prompts support version control:
- Every content change creates a new version
- View version history from prompt details
- Restore previous versions
- Compare versions

## Analytics

Track prompt performance:
- Usage count and frequency
- Success rate
- Most active users
- Context breakdown (chat vs task)
- Variable usage patterns

## Best Practices

1. **Be Specific**: Clear, detailed prompts get better results
2. **Use Variables**: Make prompts reusable with variables
3. **Add Descriptions**: Help others understand your prompt
4. **Tag Properly**: Use tags for easy discovery
5. **Test Prompts**: Preview with sample data before using
6. **Version Changes**: Use change summaries to track iterations
7. **Share Useful Prompts**: Mark as public to help your team
```

**API Reference** (`PROMPT_API.md`):
- Complete endpoint documentation
- Request/response examples
- Error codes and handling
- Authentication requirements
- Rate limits

**Integration Guide** (`PROMPT_INTEGRATION.md`):
- How to integrate prompts into custom workflows
- Using prompts programmatically
- Webhook integration
- API client examples

**Acceptance Criteria**:
- [ ] All features documented
- [ ] Examples are clear and complete
- [ ] Screenshots/GIFs included
- [ ] Code examples are tested
- [ ] Troubleshooting section included

---

## Summary

### Total Tasks: 31

#### Phase Breakdown:
- **Phase 1** (Backend Core): 4 tasks
- **Phase 2** (Backend Services): 5 tasks
- **Phase 3** (Backend API): 6 tasks
- **Phase 4** (Chat Integration): 3 tasks
- **Phase 5** (Task Integration): 3 tasks
- **Phase 6** (Frontend UI): 6 tasks
- **Phase 7** (Testing & Polish): 5 tasks

### Estimated Timeline:
- **Phase 1-3**: 2-3 weeks (Backend foundation)
- **Phase 4-5**: 1-2 weeks (Integration)
- **Phase 6**: 2-3 weeks (Frontend UI)
- **Phase 7**: 1-2 weeks (Testing & polish)

**Total**: 6-10 weeks depending on team size and parallel work

### Tech Stack:
- **Backend**: FastAPI, SQLAlchemy, PostgreSQL, MongoDB
- **Frontend**: Next.js, React, TypeScript, Tailwind CSS
- **Testing**: Pytest, React Testing Library
- **Tools**: Alembic (migrations), Docker, Git

### Success Metrics:
- [ ] 100% test coverage on critical paths
- [ ] API response time < 200ms
- [ ] Frontend bundle size < 500KB
- [ ] Zero critical bugs in production
- [ ] Positive user feedback on usability

---

## Getting Started

1. Create feature branch: `git checkout -b feature/prompt-registry`
2. Start with Phase 1: Database migration
3. Follow tasks in order within each phase
4. Test thoroughly before moving to next phase
5. Document as you go
6. Submit PR after Phase 3 for backend review
7. Submit separate PR for frontend (Phase 6)

## Notes

- Prioritize user experience in UI design
- Keep API responses consistent with existing patterns
- Ensure tenant isolation in all queries
- Add indexes for performance-critical queries
- Monitor MongoDB analytics performance
- Consider caching for frequently used prompts
- Plan for future features (templates marketplace, AI-generated prompts, etc.)
