"""
Integration Test: Chat Streaming

This test validates:
1. WebSocket connection for chat
2. Real-time message streaming from crew
3. Server-Sent Events for execution updates
4. Message persistence in MongoDB
5. Tool invocation visibility in chat
"""

import pytest
import asyncio
import json
from datetime import datetime

from src.services.chat_service import ChatService
from src.services.chat_stream import ChatStreamService
from src.models import ChatSession, Crew, Agent


class TestChatStreaming:
    """Test suite for real-time chat streaming."""

    @pytest.fixture
    async def test_crew(self, db_session, test_tenant, test_llm_provider):
        """Create test crew with agent."""
        agent = Agent(
            id="agent-1",
            tenant_id=test_tenant.id,
            name="Chat Agent",
            system_prompt="You are a helpful assistant",
            llm_provider_id=test_llm_provider.id,
            config={"temperature": 0.7},
            status="active",
        )
        db_session.add(agent)

        crew = Crew(
            id="crew-1",
            tenant_id=test_tenant.id,
            name="Test Crew",
            collaboration_pattern="sequential",
            config={},
            status="active",
        )
        crew.agents.append(agent)
        db_session.add(crew)

        await db_session.commit()
        return crew

    @pytest.fixture
    async def chat_session(self, db_session, test_tenant, test_user, test_crew):
        """Create chat session."""
        session = ChatSession(
            id="session-1",
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            crew_id=test_crew.id,
            messages_ref=f"chat_messages_{test_tenant.slug}",
        )
        db_session.add(session)
        await db_session.commit()
        return session

    @pytest.mark.asyncio
    async def test_send_message_and_receive_stream(
        self, db_session, chat_session, test_crew
    ):
        """Test sending message and receiving streaming response."""
        chat_service = ChatService(db_session)
        stream_service = ChatStreamService()

        # Send user message
        user_message = await chat_service.send_message(
            session_id=chat_session.id,
            role="user",
            content="What is multi-tenant architecture?",
        )

        assert user_message["role"] == "user"
        assert user_message["content"] == "What is multi-tenant architecture?"

        # Simulate streaming response from crew
        response_chunks = []

        async for chunk in stream_service.stream_crew_response(
            session_id=chat_session.id,
            message="What is multi-tenant architecture?",
            crew_id=test_crew.id,
        ):
            response_chunks.append(chunk)

            # Verify chunk structure
            assert "type" in chunk
            assert chunk["type"] in ["agent_thinking", "content", "tool_call", "complete"]

            if chunk["type"] == "content":
                assert "content" in chunk
            elif chunk["type"] == "tool_call":
                assert "tool_name" in chunk
                assert "tool_inputs" in chunk

        # Should have received multiple chunks
        assert len(response_chunks) > 0

        # Last chunk should be completion
        assert response_chunks[-1]["type"] == "complete"

    @pytest.mark.asyncio
    async def test_message_persistence(self, db_session, chat_session):
        """Test that messages are persisted to MongoDB."""
        from src.db.mongodb import get_mongodb

        chat_service = ChatService(db_session)

        # Send message
        await chat_service.send_message(
            session_id=chat_session.id, role="user", content="Test message"
        )

        # Verify message in MongoDB
        mongo_db = await get_mongodb()
        collection = mongo_db[chat_session.messages_ref]

        messages = await collection.find({"session_id": chat_session.id}).to_list(length=100)

        assert len(messages) >= 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Test message"
        assert "timestamp" in messages[0]

    @pytest.mark.asyncio
    async def test_websocket_connection(self, client, chat_session):
        """Test WebSocket connection for real-time chat."""
        async with client.websocket_connect(
            f"/api/v1/chat/sessions/{chat_session.id}/ws"
        ) as websocket:
            # Send message via WebSocket
            await websocket.send_json(
                {"type": "message", "content": "Hello via WebSocket"}
            )

            # Receive streaming response
            chunks_received = 0
            while chunks_received < 10:  # Receive up to 10 chunks
                data = await websocket.receive_json()

                assert "type" in data

                if data["type"] == "complete":
                    break

                chunks_received += 1

            assert chunks_received > 0

    @pytest.mark.asyncio
    async def test_tool_invocation_in_chat(self, db_session, chat_session, test_crew):
        """Test tool invocation visibility during chat."""
        chat_service = ChatService(db_session)
        stream_service = ChatStreamService()

        # Create tool for crew to use
        from src.models import Tool

        tool = Tool(
            id="tool-1",
            tenant_id=chat_session.tenant_id,
            name="Search Tool",
            description="Search for information",
            input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
            output_schema={"type": "object", "properties": {"results": {"type": "array"}}},
            execution_config={
                "docker_image": "python:3.11-slim",
                "entrypoint": ["echo", '{"results": ["result1", "result2"]}'],
                "timeout_seconds": 10,
            },
            status="active",
        )
        db_session.add(tool)
        await db_session.commit()

        # Attach tool to agent
        test_crew.agents[0].tools.append(tool)
        await db_session.commit()

        # Send message that would trigger tool use
        tool_calls = []

        async for chunk in stream_service.stream_crew_response(
            session_id=chat_session.id,
            message="Search for information about Docker",
            crew_id=test_crew.id,
        ):
            if chunk["type"] == "tool_call":
                tool_calls.append(chunk)

        # Should have captured tool invocation
        assert len(tool_calls) > 0
        assert tool_calls[0]["tool_name"] == "Search Tool"

    @pytest.mark.asyncio
    async def test_concurrent_chat_sessions(self, db_session, test_tenant, test_user, test_crew):
        """Test multiple concurrent chat sessions."""
        chat_service = ChatService(db_session)

        # Create 3 sessions
        sessions = []
        for i in range(3):
            session = ChatSession(
                id=f"session-{i}",
                tenant_id=test_tenant.id,
                user_id=test_user.id,
                crew_id=test_crew.id,
                messages_ref=f"chat_messages_{test_tenant.slug}",
            )
            db_session.add(session)
            sessions.append(session)

        await db_session.commit()

        # Send messages concurrently to all sessions
        tasks = [
            chat_service.send_message(
                session_id=session.id, role="user", content=f"Message to session {i}"
            )
            for i, session in enumerate(sessions)
        ]

        results = await asyncio.gather(*tasks)

        assert len(results) == 3
        for i, result in enumerate(results):
            assert result["content"] == f"Message to session {i}"

    @pytest.mark.asyncio
    async def test_execution_trace_in_chat(self, db_session, chat_session):
        """Test that execution trace is visible in chat."""
        chat_service = ChatService(db_session)

        # Send message
        user_msg = await chat_service.send_message(
            session_id=chat_session.id, role="user", content="Complex question"
        )

        # Get execution trace
        trace = await chat_service.get_execution_trace(
            session_id=chat_session.id, message_id=user_msg["id"]
        )

        # Trace should show agent steps
        assert "steps" in trace
        # Each step should have timestamp, agent, action
        for step in trace["steps"]:
            assert "timestamp" in step
            assert "agent_id" in step or "tool_id" in step
            assert "action" in step

    @pytest.mark.asyncio
    async def test_chat_session_history(self, db_session, chat_session):
        """Test retrieving chat history."""
        chat_service = ChatService(db_session)

        # Send multiple messages
        for i in range(5):
            await chat_service.send_message(
                session_id=chat_session.id,
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}",
            )

        # Retrieve history
        history = await chat_service.get_chat_history(
            session_id=chat_session.id, limit=10
        )

        assert len(history) == 5
        assert history[0]["content"] == "Message 0"
        assert history[-1]["content"] == "Message 4"

        # Verify chronological order
        timestamps = [msg["timestamp"] for msg in history]
        assert timestamps == sorted(timestamps)

    @pytest.mark.asyncio
    async def test_sse_for_execution_updates(self, client, chat_session):
        """Test Server-Sent Events for execution updates."""
        # Start a long-running crew interaction
        response = await client.post(
            f"/api/v1/chat/sessions/{chat_session.id}/messages",
            json={"content": "Start complex task"},
        )

        message_id = response.json()["id"]

        # Connect to SSE stream
        async with client.stream(
            "GET", f"/api/v1/chat/sessions/{chat_session.id}/messages/{message_id}/stream"
        ) as stream:
            events = []
            async for line in stream.aiter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    events.append(data)

                    if data.get("type") == "complete":
                        break

            # Should have received multiple events
            assert len(events) > 0
            assert events[-1]["type"] == "complete"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
