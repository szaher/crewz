"""
Chat message streaming service using Socket.IO
Handles real-time bidirectional communication for chat sessions
"""

import socketio
from typing import Dict, Set
from .chat_service import ChatService
from ..db.mongodb import get_mongodb

# Create Socket.IO async server
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',
    logger=True,
    engineio_logger=True
)

# Track connected clients per session
session_clients: Dict[int, Set[str]] = {}


@sio.event
async def connect(sid: str, environ: dict, auth: dict):
    """Handle client connection"""
    # TODO: Verify JWT token from auth
    token = auth.get('token')
    if not token:
        return False

    print(f"Client connected: {sid}")
    return True


@sio.event
async def disconnect(sid: str):
    """Handle client disconnection"""
    # Remove from all sessions
    for session_id, clients in session_clients.items():
        if sid in clients:
            clients.remove(sid)

    print(f"Client disconnected: {sid}")


@sio.event
async def join_session(sid: str, data: dict):
    """Join a chat session room"""
    session_id = data.get('session_id')
    if not session_id:
        return

    # Join Socket.IO room
    await sio.enter_room(sid, f"session_{session_id}")

    # Track client
    if session_id not in session_clients:
        session_clients[session_id] = set()
    session_clients[session_id].add(sid)

    print(f"Client {sid} joined session {session_id}")


@sio.event
async def leave_session(sid: str, data: dict):
    """Leave a chat session room"""
    session_id = data.get('session_id')
    if not session_id:
        return

    # Leave Socket.IO room
    await sio.leave_room(sid, f"session_{session_id}")

    # Untrack client
    if session_id in session_clients and sid in session_clients[session_id]:
        session_clients[session_id].remove(sid)

    print(f"Client {sid} left session {session_id}")


@sio.event
async def send_message(sid: str, data: dict):
    """Handle incoming message from client"""
    session_id = data.get('session_id')
    content = data.get('content')

    if not session_id or not content:
        await sio.emit('error', {'error': 'Missing session_id or content'}, to=sid)
        return

    try:
        # Save message to database
        mongodb = get_mongodb()
        chat_service = ChatService(mongodb)

        # Create user message
        user_message = await chat_service.create_message(
            session_id=session_id,
            role='user',
            content=content
        )

        # Broadcast user message to all clients in session
        await sio.emit(
            'message',
            user_message,
            room=f"session_{session_id}"
        )

        # TODO: Process message with crew/agent and generate response
        # For now, echo back as assistant
        assistant_response = await chat_service.create_message(
            session_id=session_id,
            role='assistant',
            content=f"Echo: {content}"
        )

        # Broadcast assistant response
        await sio.emit(
            'message',
            assistant_response,
            room=f"session_{session_id}"
        )

    except Exception as e:
        await sio.emit('error', {'error': str(e)}, to=sid)


@sio.event
async def typing(sid: str, data: dict):
    """Handle typing indicator"""
    session_id = data.get('session_id')
    is_typing = data.get('typing', False)

    if not session_id:
        return

    # Broadcast typing status to other clients in session (except sender)
    await sio.emit(
        'typing',
        {'session_id': session_id, 'typing': is_typing},
        room=f"session_{session_id}",
        skip_sid=sid
    )


# Create ASGI app
app = socketio.ASGIApp(sio)
