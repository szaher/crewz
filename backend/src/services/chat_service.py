"""Chat service for conversational AI interactions."""

from typing import List, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime

from ..models import ChatSession
from ..schemas.chat import (
    ChatSessionCreate,
    ChatSessionResponse,
    ChatMessageCreate,
    ChatMessageResponse,
)
from ..db.mongodb import get_mongo_collection
from ..services.llm_service import LLMService


class ChatService:
    """Service for chat session and message management."""

    def __init__(self, db: Session, llm_service: LLMService):
        self.db = db
        self.llm_service = llm_service

    async def create_session(
        self, data: ChatSessionCreate, user_id: int
    ) -> ChatSession:
        """
        Create a new chat session.

        Args:
            data: Session creation data
            user_id: User creating the session

        Returns:
            Created ChatSession model
        """
        session = ChatSession(
            user_id=user_id,
            title=data.title,
            llm_provider_id=data.llm_provider_id,
            system_prompt=data.system_prompt,
            is_active=True,
        )

        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)

        return session

    async def get_session(self, session_id: int) -> ChatSession:
        """Get chat session by ID."""
        session = (
            self.db.query(ChatSession).filter(ChatSession.id == session_id).first()
        )

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found",
            )

        return session

    async def list_sessions(self, user_id: int) -> List[ChatSession]:
        """List all chat sessions for a user."""
        return (
            self.db.query(ChatSession)
            .filter(ChatSession.user_id == user_id)
            .filter(ChatSession.is_active == True)
            .all()
        )

    async def delete_session(self, session_id: int) -> None:
        """Delete (deactivate) a chat session."""
        session = await self.get_session(session_id)
        session.is_active = False
        self.db.commit()

    async def send_message(
        self, data: ChatMessageCreate
    ) -> ChatMessageResponse:
        """
        Send a message in a chat session.

        Args:
            data: Message data

        Returns:
            Created message response
        """
        session = await self.get_session(data.session_id)

        # Store message in MongoDB
        mongo_collection = get_mongo_collection("chat_messages")

        message_doc = {
            "session_id": data.session_id,
            "role": data.role,
            "content": data.content,
            "metadata": data.metadata,
            "created_at": datetime.utcnow(),
        }

        result = await mongo_collection.insert_one(message_doc)

        # Return response
        return ChatMessageResponse(
            id=str(result.inserted_id),
            session_id=data.session_id,
            role=data.role,
            content=data.content,
            metadata=data.metadata,
            created_at=message_doc["created_at"],
        )

    async def get_messages(
        self, session_id: int, limit: int = 100
    ) -> List[ChatMessageResponse]:
        """
        Get messages from a chat session.

        Args:
            session_id: Session ID
            limit: Maximum messages to return

        Returns:
            List of messages
        """
        # Verify session exists
        await self.get_session(session_id)

        # Fetch from MongoDB
        mongo_collection = get_mongo_collection("chat_messages")

        cursor = (
            mongo_collection.find({"session_id": session_id})
            .sort("created_at", 1)
            .limit(limit)
        )

        messages = []
        async for doc in cursor:
            messages.append(
                ChatMessageResponse(
                    id=str(doc["_id"]),
                    session_id=doc["session_id"],
                    role=doc["role"],
                    content=doc["content"],
                    metadata=doc.get("metadata", {}),
                    created_at=doc["created_at"],
                )
            )

        return messages

    async def generate_response(
        self, session_id: int, user_message: str
    ) -> str:
        """
        Generate AI response for a user message.

        Args:
            session_id: Session ID
            user_message: User's message

        Returns:
            AI response text
        """
        session = await self.get_session(session_id)

        # Get conversation history
        messages = await self.get_messages(session_id)

        # Build messages for LLM
        llm_messages = []

        if session.system_prompt:
            llm_messages.append(
                {"role": "system", "content": session.system_prompt}
            )

        for msg in messages:
            llm_messages.append({"role": msg.role, "content": msg.content})

        # Add user message
        llm_messages.append({"role": "user", "content": user_message})

        # Generate response
        response = await self.llm_service.chat_completion(
            provider_id=session.llm_provider_id,
            messages=llm_messages,
        )

        assistant_message = response.choices[0].message.content

        return assistant_message
