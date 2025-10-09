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
from ..models import Tool
from .docker_service import DockerService
from .custom_tool_runner import CustomToolRunner
import json
import re


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
            folder_id=data.folder_id,
        )

        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)

        # Also persist lightweight session metadata in MongoDB for quick access
        try:
            sessions_col = get_mongo_collection("chat_sessions")
            await sessions_col.insert_one({
                "session_id": session.id,
                "user_id": user_id,
                "llm_provider_id": data.llm_provider_id,
                "title": data.title,
                "system_prompt": data.system_prompt,
                "tool_ids": data.tool_ids or [],
                "folder_id": data.folder_id,
                "is_active": True,
                "created_at": datetime.utcnow(),
            })
        except Exception:
            # Non-fatal: SQL remains source of truth
            pass
        return session

    async def list_sessions(
        self,
        user_id: int,
        q: str | None = None,
        folder_id: int | None = None,
    ) -> List[ChatSession]:
        """List sessions for a user with optional search and folder filter."""
        query = (
            self.db.query(ChatSession)
            .filter(ChatSession.user_id == user_id)
            .filter(ChatSession.is_active == True)
        )
        if folder_id is not None:
            query = query.filter(ChatSession.folder_id == folder_id)
        if q:
            like = f"%{q}%"
            from sqlalchemy import or_
            query = query.filter(or_(ChatSession.title.ilike(like), ChatSession.system_prompt.ilike(like)))
        return query.order_by(ChatSession.created_at.desc()).all()

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

    # Note: list_sessions with filters defined above is the canonical one.

    async def delete_session(self, session_id: int) -> None:
        """Delete (deactivate) a chat session."""
        session = await self.get_session(session_id)
        session.is_active = False
        self.db.commit()

        # Soft-delete in Mongo index as well
        try:
            sessions_col = get_mongo_collection("chat_sessions")
            await sessions_col.update_one({"session_id": session_id}, {"$set": {"is_active": False, "deleted_at": datetime.utcnow()}})
        except Exception:
            pass

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

        # Augment with tool instructions if any tools configured for session (from Mongo metadata)
        try:
            sessions_col = get_mongo_collection("chat_sessions")
            sess_doc = await sessions_col.find_one({"session_id": session_id})
            tool_ids = (sess_doc or {}).get("tool_ids", []) if sess_doc else []
        except Exception:
            tool_ids = []

        tools_for_session = []
        if tool_ids:
            try:
                tools_for_session = self.db.query(Tool).filter(Tool.id.in_(tool_ids)).all()
            except Exception:
                tools_for_session = []

        if tools_for_session:
            # Describe available tools and the invocation protocol
            tool_lines = []
            for t in tools_for_session:
                tool_lines.append(f"- id={t.id}, name={t.name}: {t.description}")
            tool_instruction = (
                "When a tool is helpful, call it using ONE of the strict formats (no extra text):\n"
                "Preferred JSON only: {\\\"tool_call\\\": {\\\"tool_id\\\": <id>, \\\"input\\\": <string or JSON>}}\n"
                "Alternate tag: <tool>{\\\"tool_id\\\": <id>, \\\"input\\\": <string or JSON>}</tool>\n"
                "Return exactly one of the above with no surrounding commentary. Available tools:\n"
                + "\n".join(tool_lines)
            )
            llm_messages.append({"role": "system", "content": tool_instruction})

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

        # Preferred JSON: {"tool_call": {"tool_id": ..., "input": ...}}
        tool_payload = None
        try:
            parsed = json.loads((assistant_message or '').strip())
            if isinstance(parsed, dict) and 'tool_call' in parsed and isinstance(parsed['tool_call'], dict):
                tc = parsed['tool_call']
                tool_payload = { 'tool_id': tc.get('tool_id'), 'input': tc.get('input') }
        except Exception:
            tool_payload = None

        # Fallback: <tool>{json}</tool>
        if tool_payload is None:
            tool_match = None
            try:
                tool_match = re.search(r"<tool>([\s\S]*?)</tool>", assistant_message)
            except Exception:
                tool_match = None
            if tool_match:
                payload_raw = tool_match.group(1).strip()
                try:
                    tool_payload = json.loads(payload_raw)
                except Exception:
                    payload_clean = re.sub(r"^```[a-zA-Z0-9_-]*\n|```$", "", payload_raw).strip()
                    tool_payload = json.loads(payload_clean)

        if tool_payload is not None:
            tool_id = int(tool_payload.get("tool_id"))
            tool_input = tool_payload.get("input")
            if isinstance(tool_input, (dict, list)):
                tool_input_str = json.dumps(tool_input)
            else:
                tool_input_str = str(tool_input or "")

            # Execute tool for JSON function-call path
            tool = self.db.query(Tool).filter(Tool.id == tool_id).first()
            if not tool:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Requested tool not found")
            if tools_for_session and tool_id not in [t.id for t in tools_for_session]:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tool not allowed for this session")
            output: str = ""
            if str(tool.tool_type).lower().endswith("docker") and tool.docker_image:
                docker_runner = DockerService()
                output = await docker_runner.execute_tool(
                    tool_id=tool.id,
                    input_data=tool_input_str,
                    docker_image=tool.docker_image,
                    docker_command=tool.docker_command or None,
                )
            elif str(tool.tool_type).lower().endswith("custom") and tool.code:
                runner = CustomToolRunner()
                output = await runner.execute(tool.code, tool_input_str)
            else:
                output = f"Tool type '{tool.tool_type}' is not executable in this environment."

            metadata = {
                "tool_invocations": [
                    {
                        "tool_id": tool.id,
                        "tool_name": tool.name,
                        "input": tool_input,
                        "output": output,
                        "status": "completed",
                    }
                ]
            }
            await self.send_message(
                ChatMessageCreate(
                    session_id=session_id,
                    role="assistant",
                    content=output,
                    metadata=metadata,
                )
            )
            return output

        # Check for tool invocation pattern: <tool>{json}</tool>
        tool_match = None
        try:
            tool_match = re.search(r"<tool>([\s\S]*?)</tool>", assistant_message)
        except Exception:
            tool_match = None

        if tool_match:
            payload_raw = tool_match.group(1).strip()
            # Try to parse JSON payload
            try:
                tool_payload = json.loads(payload_raw)
            except Exception:
                # Sometimes the model may double encode; try to strip code fences
                payload_clean = re.sub(r"^```[a-zA-Z0-9_-]*\n|```$", "", payload_raw).strip()
                tool_payload = json.loads(payload_clean)

            tool_id = int(tool_payload.get("tool_id"))
            tool_input = tool_payload.get("input")
            if isinstance(tool_input, (dict, list)):
                tool_input_str = json.dumps(tool_input)
            else:
                tool_input_str = str(tool_input or "")

        # Check for tool invocation pattern: <tool>{json}</tool>
        tool_match = None
        try:
            tool_match = re.search(r"<tool>([\s\S]*?)</tool>", assistant_message)
        except Exception:
            tool_match = None

        if tool_match:
            payload_raw = tool_match.group(1).strip()
            # Try to parse JSON payload
            try:
                tool_payload = json.loads(payload_raw)
            except Exception:
                # Sometimes the model may double encode; try to strip code fences
                payload_clean = re.sub(r"^```[a-zA-Z0-9_-]*\n|```$", "", payload_raw).strip()
                tool_payload = json.loads(payload_clean)

            tool_id = int(tool_payload.get("tool_id"))
            tool_input = tool_payload.get("input")
            if isinstance(tool_input, (dict, list)):
                tool_input_str = json.dumps(tool_input)
            else:
                tool_input_str = str(tool_input or "")

            # Execute tool (currently supports Docker tools)
            tool = self.db.query(Tool).filter(Tool.id == tool_id).first()
            if not tool:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Requested tool not found")

            # Restrict to session's allowed tools if configured
            if tools_for_session and tool_id not in [t.id for t in tools_for_session]:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tool not allowed for this session")

            output: str = ""
            if str(tool.tool_type).lower().endswith("docker") and tool.docker_image:
                docker_runner = DockerService()
                output = await docker_runner.execute_tool(
                    tool_id=tool.id,
                    input_data=tool_input_str,
                    docker_image=tool.docker_image,
                    docker_command=tool.docker_command or None,
                )
            elif str(tool.tool_type).lower().endswith("custom") and tool.code:
                # Run custom tool code via subprocess wrapper
                runner = CustomToolRunner()
                output = await runner.execute(tool.code, tool_input_str)
            else:
                # Not implemented tool type; surface message
                output = f"Tool type '{tool.tool_type}' is not executable in this environment."

            # Store AI tool invocation message with metadata
            metadata = {
                "tool_invocations": [
                    {
                        "tool_id": tool.id,
                        "tool_name": tool.name,
                        "input": tool_input,
                        "output": output,
                        "status": "completed",
                    }
                ]
            }
            await self.send_message(
                ChatMessageCreate(
                    session_id=session_id,
                    role="assistant",
                    content=output,
                    metadata=metadata,
                )
            )
            return output

        return assistant_message
