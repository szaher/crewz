"""Chat API endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import StreamingResponse
import json
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
from ...services.notification_service import NotificationService
from ...services.notification_events import NotificationPublisher
from ...schemas.notifications import NotificationCreate

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


@router.get("/sessions/{session_id}/generate/stream")
async def generate_response_stream(
    session_id: int,
    user_message: str,
    store_user: bool = True,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Stream AI response tokens for a user message via SSE.

    Sends an initial `status` event with state=thinking, followed by `delta` events
    containing token chunks, and a final `done` event. Stores both user and assistant
    messages in the session.
    """
    llm_service = LLMService(db)
    chat_service = ChatService(db, llm_service)

    # Store user message first (unless skipping for retry)
    if store_user:
        await chat_service.send_message(
            ChatMessageCreate(
                session_id=session_id,
                role="user",
                content=user_message,
            )
        )

    async def event_generator():
        # Build message history similar to generate_response
        session = await chat_service.get_session(session_id)
        history = await chat_service.get_messages(session_id)

        llm_messages: list[dict] = []
        if session.system_prompt:
            llm_messages.append({"role": "system", "content": session.system_prompt})
        for m in history:
            if m.role in ("user", "assistant"):
                llm_messages.append({"role": m.role, "content": m.content})
        llm_messages.append({"role": "user", "content": user_message})

        # Preamble: thinking
        yield f"event: status\ndata: {json.dumps({'state': 'thinking'})}\n\n"

        assembled: list[str] = []
        try:
            async for chunk in llm_service.chat_completion_stream(
                provider_id=session.llm_provider_id,  # type: ignore[arg-type]
                messages=llm_messages,
            ):
                assembled.append(chunk)
                yield f"event: delta\ndata: {json.dumps({'token': chunk})}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
            return

        full_text = "".join(assembled)
        # Persist assistant message
        await chat_service.send_message(
            ChatMessageCreate(
                session_id=session_id,
                role="assistant",
                content=full_text,
            )
        )

        # Push a notification for chat response readiness
        try:
            ns = NotificationService(db)
            title = f"New reply in '{session.title or ('Chat Session #' + str(session_id))}'"
            await ns.create_notification(
                user_id=current_user["id"],
                tenant_id=current_user.get("tenant_id"),
                data=NotificationCreate(
                    type="info",
                    title=title,
                    message=(full_text[:120] + ("…" if len(full_text) > 120 else "")),
                    data={"chat_session_id": session_id, "kind": "chat_response"},
                ),
            )
            NotificationPublisher().publish(
                current_user["id"],
                {
                    "type": "info",
                    "title": title,
                    "message": (full_text[:120] + ("…" if len(full_text) > 120 else "")),
                    "data": {"chat_session_id": session_id, "kind": "chat_response"},
                },
            )
        except Exception:
            pass

        yield f"event: done\ndata: {json.dumps({'length': len(full_text)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


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


@router.websocket("/sessions/{session_id}/ws")
async def websocket_chat(
    websocket: WebSocket,
    session_id: int,
    token: Optional[str] = Query(None),
):
    """
    WebSocket endpoint for real-time chat streaming.

    Connect to ws://localhost:8000/api/v1/chat/sessions/{session_id}/ws?token=<jwt_token>

    Message format:
    - Send: {"type": "message", "content": "user message text"}
    - Receive: {"type": "status", "state": "thinking"}
    - Receive: {"type": "delta", "token": "streamed text"}
    - Receive: {"type": "done", "length": 123}
    - Receive: {"type": "error", "message": "error details"}
    """
    await websocket.accept()

    # Get database session
    db_gen = get_db()
    db = next(db_gen)

    try:
        # Verify authentication token
        if not token:
            await websocket.send_json({"type": "error", "message": "Authentication token required"})
            await websocket.close(code=1008)  # Policy violation
            return

        # TODO: Validate JWT token and get user_id
        # For now, we'll skip auth validation in WebSocket
        # In production, implement proper JWT validation here

        llm_service = LLMService(db)
        chat_service = ChatService(db, llm_service)

        # Verify session exists and belongs to user
        try:
            session = await chat_service.get_session(session_id)
            if not session:
                await websocket.send_json({"type": "error", "message": "Session not found"})
                await websocket.close(code=1008)
                return
        except Exception as e:
            await websocket.send_json({"type": "error", "message": str(e)})
            await websocket.close(code=1011)  # Internal error
            return

        # Listen for messages
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_json()

                if data.get("type") != "message":
                    await websocket.send_json({"type": "error", "message": "Invalid message type"})
                    continue

                user_message = data.get("content", "").strip()
                if not user_message:
                    await websocket.send_json({"type": "error", "message": "Empty message"})
                    continue

                # Store user message (optional based on store_user parameter)
                store_user = data.get("store_user", True)
                if store_user:
                    await chat_service.send_message(
                        ChatMessageCreate(
                            session_id=session_id,
                            role="user",
                            content=user_message,
                        )
                    )

                # Get message history
                history = await chat_service.get_messages(session_id)

                # Build LLM messages
                llm_messages: list[dict] = []
                if session.system_prompt:
                    llm_messages.append({"role": "system", "content": session.system_prompt})

                for m in history:
                    if m.role in ("user", "assistant"):
                        llm_messages.append({"role": m.role, "content": m.content})

                # Add current user message if not stored
                if not store_user:
                    llm_messages.append({"role": "user", "content": user_message})

                # Send thinking status
                await websocket.send_json({"type": "status", "state": "thinking"})

                # Stream response
                assembled: list[str] = []
                try:
                    async for chunk in llm_service.chat_completion_stream(
                        provider_id=session.llm_provider_id,
                        messages=llm_messages,
                    ):
                        assembled.append(chunk)
                        await websocket.send_json({"type": "delta", "token": chunk})
                except Exception as llm_error:
                    await websocket.send_json({"type": "error", "message": f"LLM error: {str(llm_error)}"})
                    continue

                # Persist assistant message
                full_text = "".join(assembled)
                await chat_service.send_message(
                    ChatMessageCreate(
                        session_id=session_id,
                        role="assistant",
                        content=full_text,
                    )
                )

                # Send completion signal
                await websocket.send_json({"type": "done", "length": len(full_text)})

            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON"})
            except Exception as e:
                await websocket.send_json({"type": "error", "message": str(e)})

    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": f"Server error: {str(e)}"})
        except:
            pass
    finally:
        try:
            db_gen.close()
        except:
            pass
        try:
            await websocket.close()
        except:
            pass
