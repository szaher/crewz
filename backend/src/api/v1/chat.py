"""Chat API endpoints."""

from typing import List, Optional
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
    q: Optional[str] = None,
    folder_id: Optional[int] = None,
):
    """
    List all chat sessions for the current user.

    Returns active chat sessions only.
    """
    llm_service = LLMService(db)
    chat_service = ChatService(db, llm_service)
    try:
      sessions = await chat_service.list_sessions(user_id=current_user["id"], q=q, folder_id=folder_id)  # type: ignore[call-arg]
    except TypeError:
      # Backward compatibility if service signature lacks filters
      sessions = await chat_service.list_sessions(user_id=current_user["id"])  # type: ignore[call-arg]
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
    # Resolve provider: use provided or tenant default
    provider_id = request.llm_provider_id
    if provider_id is None:
        from ...models.llm_provider import LLMProvider
        default_provider = (
            db.query(LLMProvider)
            .filter(
                LLMProvider.tenant_id == current_user["tenant_id"],
                LLMProvider.is_default == True,
                LLMProvider.is_active == True,
            )
            .first()
        )
        if not default_provider:
            raise HTTPException(
                status_code=400,
                detail="No default LLM provider configured. Please select a provider or set a default one.",
            )
        provider_id = default_provider.id

    # Build request with resolved provider
    # Validate folder if provided (must belong to user)
    if request.folder_id is not None:
        from ...models.chat_folder import ChatFolder
        folder = (
            db.query(ChatFolder)
            .filter(ChatFolder.id == request.folder_id, ChatFolder.user_id == current_user["id"])
            .first()
        )
        if not folder:
            raise HTTPException(status_code=400, detail="Invalid folder_id")

    resolved = ChatSessionCreate(
        title=request.title,
        llm_provider_id=provider_id,
        system_prompt=request.system_prompt,
        tool_ids=request.tool_ids,
        folder_id=request.folder_id,
    )

    llm_service = LLMService(db)
    chat_service = ChatService(db, llm_service)
    session = await chat_service.create_session(resolved, user_id=current_user["id"])
    return ChatSessionResponse.from_orm(session)


@router.put("/sessions/{session_id}", response_model=ChatSessionResponse)
async def update_session(
    session_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Update a chat session (title, system_prompt, folder_id, is_active)."""
    llm_service = LLMService(db)
    chat_service = ChatService(db, llm_service)
    session = await chat_service.get_session(session_id)
    if session.user_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Forbidden")

    title = payload.get("title")
    system_prompt = payload.get("system_prompt")
    folder_id = payload.get("folder_id")
    is_active = payload.get("is_active")

    if title is not None:
        session.title = title
    if system_prompt is not None:
        session.system_prompt = system_prompt
    if folder_id is not None:
        if folder_id is not None:
            from ...models.chat_folder import ChatFolder
            folder = (
                db.query(ChatFolder)
                .filter(ChatFolder.id == folder_id, ChatFolder.user_id == current_user["id"])
                .first()
            )
            if not folder and folder_id is not None:
                raise HTTPException(status_code=400, detail="Invalid folder_id")
        session.folder_id = folder_id
    if is_active is not None:
        session.is_active = bool(is_active)

    db.commit()
    db.refresh(session)
    return ChatSessionResponse.from_orm(session)


@router.put("/sessions/{session_id}/tools", response_model=dict)
async def update_session_tools(
    session_id: int,
    body: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Update allowed tool IDs for a chat session (stored in Mongo)."""
    tool_ids = body.get("tool_ids")
    if not isinstance(tool_ids, list):
        raise HTTPException(status_code=400, detail="tool_ids must be a list of integers")

    llm_service = LLMService(db)
    chat_service = ChatService(db, llm_service)
    session = await chat_service.get_session(session_id)
    if session.user_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Forbidden")

    # Validate tools exist
    from ...models.tool import Tool
    if tool_ids:
        count = db.query(Tool).filter(Tool.id.in_(tool_ids)).count()
        if count != len(set(tool_ids)):
            raise HTTPException(status_code=400, detail="One or more tool_ids are invalid")

    # Update Mongo doc
    from ...db.mongodb import get_mongo_collection
    col = get_mongo_collection("chat_sessions")
    await col.update_one({"session_id": session_id}, {"$set": {"tool_ids": tool_ids}}, upsert=True)

    return {"ok": True, "tool_ids": tool_ids}


@router.get("/sessions/{session_id}/tools", response_model=dict)
async def get_session_tools(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Return allowed tool IDs for a session (from Mongo)."""
    llm_service = LLMService(db)
    chat_service = ChatService(db, llm_service)
    session = await chat_service.get_session(session_id)
    if session.user_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Forbidden")

    from ...db.mongodb import get_mongo_collection
    col = get_mongo_collection("chat_sessions")
    doc = await col.find_one({"session_id": session_id})
    tool_ids = (doc or {}).get("tool_ids", [])
    return {"tool_ids": tool_ids}


@router.get("/folders", response_model=List[dict])
async def list_folders(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    from ...models.chat_folder import ChatFolder
    folders = (
        db.query(ChatFolder)
        .filter(ChatFolder.user_id == current_user["id"])
        .order_by(ChatFolder.created_at.desc())
        .all()
    )
    return [
        {"id": f.id, "name": f.name, "created_at": f.created_at, "updated_at": f.updated_at}
        for f in folders
    ]


@router.post("/folders", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_folder(
    body: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    from ...models.chat_folder import ChatFolder
    name = (body.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Folder name is required")
    folder = ChatFolder(tenant_id=current_user["tenant_id"], user_id=current_user["id"], name=name)
    db.add(folder)
    db.commit()
    db.refresh(folder)
    return {"id": folder.id, "name": folder.name, "created_at": folder.created_at, "updated_at": folder.updated_at}


@router.put("/folders/{folder_id}", response_model=dict)
async def rename_folder(
    folder_id: int,
    body: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    from ...models.chat_folder import ChatFolder
    folder = db.query(ChatFolder).filter(ChatFolder.id == folder_id, ChatFolder.user_id == current_user["id"]).first()
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
    name = (body.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Folder name is required")
    folder.name = name
    db.commit()
    db.refresh(folder)
    return {"id": folder.id, "name": folder.name, "created_at": folder.created_at, "updated_at": folder.updated_at}


@router.delete("/folders/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_folder(
    folder_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    from ...models.chat_folder import ChatFolder
    from ...models.chat_session import ChatSession
    folder = db.query(ChatFolder).filter(ChatFolder.id == folder_id, ChatFolder.user_id == current_user["id"]).first()
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
    # Unassign sessions from this folder
    db.query(ChatSession).filter(ChatSession.folder_id == folder_id, ChatSession.user_id == current_user["id"]).update({ChatSession.folder_id: None}, synchronize_session=False)
    db.delete(folder)
    db.commit()
    return None


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
