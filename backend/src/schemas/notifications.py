"""Notification schemas."""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class NotificationCreate(BaseModel):
    type: str = "info"
    title: str
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class NotificationOut(BaseModel):
    id: int
    type: str
    title: str
    message: Optional[str]
    data: Optional[Dict[str, Any]]
    is_read: bool
    created_at: datetime
    read_at: Optional[datetime]

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    notifications: List[NotificationOut]
    unread_count: int

