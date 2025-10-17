"""Chat schemas for conversational AI."""

from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
from uuid import UUID


class ChatRole(str, Enum):
    """Chat message role enumeration."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatSessionCreate(BaseModel):
    """Create chat session request schema."""

    title: Optional[str] = Field(None, max_length=255)
    # If omitted, backend will use tenant's default provider
    llm_provider_id: Optional[UUID] = None
    system_prompt: Optional[str] = None
    # Optional tool IDs to associate with this session (stored in Mongo metadata)
    tool_ids: Optional[List[UUID]] = None
    # Optional folder
    folder_id: Optional[UUID] = None


class ChatSessionResponse(BaseModel):
    """Chat session response schema."""

    id: UUID
    user_id: UUID
    title: Optional[str]
    llm_provider_id: UUID
    system_prompt: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    folder_id: Optional[UUID] = None

    class Config:
        from_attributes = True


class ChatMessageCreate(BaseModel):
    """Create chat message request schema."""

    session_id: UUID
    role: ChatRole
    content: str = Field(..., min_length=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChatMessageResponse(BaseModel):
    """Chat message response schema."""

    id: str  # MongoDB ObjectId as string
    session_id: UUID
    role: ChatRole
    content: str
    metadata: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True


class ChatDirectRequest(BaseModel):
    """Direct chat without creating a session."""

    provider_id: Optional[UUID] = None
    messages: List[Dict[str, str]] = Field(
        ..., description="List of chat messages with role and content"
    )
    temperature: float = 0.7
    max_tokens: Optional[int] = None


class ChatDirectResponse(BaseModel):
    """Direct chat response payload."""

    content: str


class ChatFolderCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class ChatFolderResponse(BaseModel):
    id: UUID
    name: str
    created_at: datetime
    updated_at: datetime
