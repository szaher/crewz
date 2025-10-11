"""Notification service for creating and listing notifications."""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime

from ..models.notification import Notification
from ..schemas.notifications import NotificationCreate, NotificationOut


class NotificationService:
    def __init__(self, db: Session):
        self.db = db

    async def create_notification(
        self,
        user_id: int,
        tenant_id: int,
        data: NotificationCreate,
    ) -> Notification:
        n = Notification(
            tenant_id=tenant_id,
            user_id=user_id,
            type=data.type,
            title=data.title,
            message=data.message,
            data=data.data,
        )
        self.db.add(n)
        self.db.commit()
        self.db.refresh(n)
        return n

    async def list_notifications(
        self, user_id: int, unread_only: bool = False, limit: int = 50
    ) -> List[Notification]:
        q = self.db.query(Notification).filter(Notification.user_id == user_id)
        if unread_only:
            q = q.filter(Notification.is_read == False)  # noqa: E712
        return (
            q.order_by(Notification.created_at.desc()).limit(limit).all()
        )

    async def unread_count(self, user_id: int) -> int:
        return (
            self.db.query(Notification)
            .filter(Notification.user_id == user_id, Notification.is_read == False)  # noqa: E712
            .count()
        )

    async def mark_read(self, notification_id: int, user_id: int) -> Notification:
        n = (
            self.db.query(Notification)
            .filter(Notification.id == notification_id, Notification.user_id == user_id)
            .first()
        )
        if not n:
            raise ValueError("Notification not found")
        if not n.is_read:
            n.is_read = True
            n.read_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(n)
        return n

    async def mark_all_read(self, user_id: int) -> int:
        updated = (
            self.db.query(Notification)
            .filter(Notification.user_id == user_id, Notification.is_read == False)  # noqa: E712
            .update({"is_read": True, "read_at": datetime.utcnow()}, synchronize_session=False)
        )
        self.db.commit()
        return updated

