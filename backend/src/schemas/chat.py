"""Chat schemas for conversational AI."""

from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum


class ChatRole(str, Enum):
    """Chat message role enumeration."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatSessionCreate(BaseModel):
    """Create chat session request schema."""

    title: Optional[str] = Field(None, max_length=255)
    llm_provider_id: int
    system_prompt: Optional[str] = None


class ChatSessionResponse(BaseModel):
    """Chat session response schema."""

    id: int
    user_id: int
    title: Optional[str]
    llm_provider_id: int
    system_prompt: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChatMessageCreate(BaseModel):
    """Create chat message request schema."""

    session_id: int
    role: ChatRole
    content: str = Field(..., min_length=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChatMessageResponse(BaseModel):
    """Chat message response schema."""

    id: str  # MongoDB ObjectId as string
    session_id: int
    role: ChatRole
    content: str
    metadata: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True
