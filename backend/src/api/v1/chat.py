"""Chat API endpoints."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...db.postgres import get_db
from ...schemas.chat import (
    ChatSessionCreate,
    ChatSessionResponse,
    ChatMessageCreate,
    ChatMessageResponse,
    ChatDirectRequest,
    ChatDirectResponse,
)
from ...services.chat_service import ChatService
from ...services.llm_service import LLMService
from ...api.middleware.auth import require_auth

router = APIRouter()


@router.get("/sessions", response_model=List[ChatSessionResponse])
async def list_sessions(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    List all chat sessions for the current user.

    Returns active chat sessions only.
    """
    llm_service = LLMService(db)
    chat_service = ChatService(db, llm_service)
    sessions = await chat_service.list_sessions(user_id=current_user["id"])
    return [ChatSessionResponse.from_orm(s) for s in sessions]


@router.post("/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    request: ChatSessionCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Create a new chat session.

    - **title**: Optional session title
    - **llm_provider_id**: LLM provider to use for this session
    - **system_prompt**: Optional system prompt to set context
    """
    llm_service = LLMService(db)
    chat_service = ChatService(db, llm_service)
    session = await chat_service.create_session(request, user_id=current_user["id"])
    return ChatSessionResponse.from_orm(session)


@router.post("/direct", response_model=ChatDirectResponse)
async def direct_chat(
    payload: ChatDirectRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Direct chat with the default or specified LLM provider without creating a session.

    - If `provider_id` is omitted, uses the tenant's default active provider.
    - Does not persist messages.
    """
    # Resolve provider
    provider_id = payload.provider_id
    if provider_id is None:
        from ...models.llm_provider import LLMProvider
        provider = (
            db.query(LLMProvider)
            .filter(
                LLMProvider.tenant_id == current_user["tenant_id"],
                LLMProvider.is_default == True,
                LLMProvider.is_active == True,
            )
            .first()
        )
        if not provider:
            raise HTTPException(
                status_code=400,
                detail=(
                    "No default LLM provider configured. "
                    "Create a chat session (which can choose a provider) or set a default provider."
                ),
            )
        provider_id = provider.id

    llm_service = LLMService(db)
    result = await llm_service.chat_completion(
        provider_id=provider_id,
        messages=payload.messages,
        temperature=payload.temperature,
        max_tokens=payload.max_tokens,
    )

    try:
        content = result.choices[0].message.content
    except Exception:
        raise HTTPException(status_code=500, detail="Unexpected LLM response format")

    return ChatDirectResponse(content=content)


@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessageResponse])
async def get_messages(
    session_id: int,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Get messages from a chat session.

    - **limit**: Maximum number of messages to return (default: 100)
    """
    llm_service = LLMService(db)
    chat_service = ChatService(db, llm_service)
    messages = await chat_service.get_messages(session_id, limit=limit)
    return messages


@router.post("/messages", response_model=ChatMessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    request: ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Send a message in a chat session.

    - **session_id**: Chat session ID
    - **role**: Message role (user, assistant, system)
    - **content**: Message content
    - **metadata**: Optional metadata
    """
    llm_service = LLMService(db)
    chat_service = ChatService(db, llm_service)
    message = await chat_service.send_message(request)
    return message


@router.post("/sessions/{session_id}/generate")
async def generate_response(
    session_id: int,
    user_message: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Send user message and get AI response.

    Convenience endpoint that:
    1. Stores user message
    2. Generates AI response
    3. Stores AI response
    4. Returns AI response
    """
    llm_service = LLMService(db)
    chat_service = ChatService(db, llm_service)

    # Store user message
    user_msg = await chat_service.send_message(
        ChatMessageCreate(
            session_id=session_id,
            role="user",
            content=user_message,
        )
    )

    # Generate AI response
    ai_response = await chat_service.generate_response(session_id, user_message)

    # Store AI message
    ai_msg = await chat_service.send_message(
        ChatMessageCreate(
            session_id=session_id,
            role="assistant",
            content=ai_response,
        )
    )

    return {
        "user_message": user_msg,
        "ai_response": ai_msg,
    }


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Delete (deactivate) a chat session.

    Session is soft-deleted by setting is_active to false.
    """
    llm_service = LLMService(db)
    chat_service = ChatService(db, llm_service)
    await chat_service.delete_session(session_id)


@router.get("/ws")
async def websocket_endpoint():
    """
    WebSocket endpoint for real-time chat.

    Placeholder for future WebSocket implementation.
    Use POST /sessions/{session_id}/generate for now.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="WebSocket chat not yet implemented. Use POST /sessions/{session_id}/generate",
    )
