"""Integration test for real-time trace streaming via SSE (Scenario 2 from quickstart.md)."""

import pytest
from httpx import AsyncClient
import asyncio
from datetime import datetime
import json


@pytest.mark.asyncio
async def test_real_time_trace_streaming_via_sse(
    authed_client: AsyncClient,
    test_crew_id: str,
    auth_token: str
):
    """
    Test Scenario 2: Real-time Trace Streaming via SSE.

    Given: An execution is started
    When: SSE client connects to /executions/{id}/traces/stream
    Then: Events are received in real-time (connected, trace_started, trace_completed)
    """
    # Arrange: Start crew execution
    crew_payload = {
        "crew_id": test_crew_id,
        "inputs": {"topic": "Real-time monitoring test"}
    }

    response = await authed_client.post("/api/v1/executions", json=crew_payload)
    assert response.status_code == 201
    execution_id = response.json()["id"]

    # Act: Connect SSE client and collect events
    events_received = []
    trace_events = []

    async def collect_events():
        """Connect to SSE stream and collect events for 10 seconds."""
        import httpx

        async with httpx.AsyncClient() as sse_client:
            # SSE doesn't support auth headers, use query param
            url = f"{authed_client.base_url}/api/v1/executions/{execution_id}/traces/stream?token={auth_token}"

            async with sse_client.stream("GET", url) as response:
                assert response.status_code == 200
                assert response.headers["content-type"] == "text/event-stream"

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]  # Strip "data: " prefix
                        try:
                            event = json.loads(data)
                            events_received.append(event)

                            # Categorize event types
                            event_type = event.get("type")
                            if event_type in ["trace_started", "trace_completed", "trace_failed"]:
                                trace_events.append(event)

                            # Stop after receiving stream_closed event
                            if event_type == "stream_closed":
                                break

                        except json.JSONDecodeError:
                            continue

                    # Safety timeout after 15 seconds
                    if len(events_received) > 0 and (datetime.utcnow() - start_time).total_seconds() > 15:
                        break

    start_time = datetime.utcnow()

    # Run SSE collection with timeout
    try:
        await asyncio.wait_for(collect_events(), timeout=20)
    except asyncio.TimeoutError:
        pass  # It's ok if we timeout, just check what we collected

    # Assert: Verify events received
    assert len(events_received) > 0, "No SSE events received"

    # Verify connected event
    connected_events = [e for e in events_received if e.get("type") == "connected"]
    assert len(connected_events) >= 1, "No 'connected' event received"

    # Verify trace events (should be at least some trace_completed events)
    trace_completed_events = [e for e in trace_events if e.get("type") == "trace_completed"]
    assert len(trace_completed_events) > 0, "No 'trace_completed' events received"

    # Verify trace event structure
    for event in trace_completed_events:
        assert "data" in event
        trace_data = event["data"]
        assert "id" in trace_data
        assert "execution_id" in trace_data
        assert trace_data["execution_id"] == execution_id
        assert "prompt" in trace_data
        assert "response" in trace_data
        assert "total_tokens" in trace_data
        assert "latency_ms" in trace_data

    print(f"✓ SSE streaming successful: {len(events_received)} events, {len(trace_completed_events)} traces")


@pytest.mark.asyncio
async def test_sse_stream_handles_multiple_clients(
    authed_client: AsyncClient,
    test_crew_id: str,
    auth_token: str
):
    """Test that multiple SSE clients can connect to the same execution stream."""
    # Start execution
    crew_payload = {"crew_id": test_crew_id, "inputs": {"topic": "Multi-client test"}}
    response = await authed_client.post("/api/v1/executions", json=crew_payload)
    execution_id = response.json()["id"]

    # Connect two SSE clients simultaneously
    events_client1 = []
    events_client2 = []

    async def collect_events_client1():
        import httpx
        async with httpx.AsyncClient() as client:
            url = f"{authed_client.base_url}/api/v1/executions/{execution_id}/traces/stream?token={auth_token}"
            async with client.stream("GET", url) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            event = json.loads(line[6:])
                            events_client1.append(event)
                            if event.get("type") == "stream_closed":
                                break
                        except json.JSONDecodeError:
                            continue
                    if len(events_client1) > 10:  # Collect some events
                        break

    async def collect_events_client2():
        import httpx
        async with httpx.AsyncClient() as client:
            url = f"{authed_client.base_url}/api/v1/executions/{execution_id}/traces/stream?token={auth_token}"
            async with client.stream("GET", url) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            event = json.loads(line[6:])
                            events_client2.append(event)
                            if event.get("type") == "stream_closed":
                                break
                        except json.JSONDecodeError:
                            continue
                    if len(events_client2) > 10:
                        break

    # Run both clients concurrently
    await asyncio.gather(
        asyncio.wait_for(collect_events_client1(), timeout=15),
        asyncio.wait_for(collect_events_client2(), timeout=15),
        return_exceptions=True
    )

    # Both clients should receive events
    assert len(events_client1) > 0
    assert len(events_client2) > 0


@pytest.mark.asyncio
async def test_sse_stream_authentication_required(authed_client: AsyncClient, test_execution_id: str):
    """Test that SSE endpoint requires authentication token."""
    import httpx

    async with httpx.AsyncClient() as client:
        # Try without token
        url = f"{authed_client.base_url}/api/v1/executions/{test_execution_id}/traces/stream"

        async with client.stream("GET", url) as response:
            assert response.status_code == 401


@pytest.mark.asyncio
async def test_sse_stream_404_for_nonexistent_execution(
    authed_client: AsyncClient,
    auth_token: str
):
    """Test that SSE endpoint returns 404 for non-existent execution."""
    import httpx
    from uuid import uuid4

    non_existent_id = str(uuid4())

    async with httpx.AsyncClient() as client:
        url = f"{authed_client.base_url}/api/v1/executions/{non_existent_id}/traces/stream?token={auth_token}"

        async with client.stream("GET", url) as response:
            assert response.status_code == 404


@pytest.mark.asyncio
async def test_sse_stream_event_ordering(
    authed_client: AsyncClient,
    test_crew_id: str,
    auth_token: str
):
    """Test that SSE events are delivered in correct order."""
    crew_payload = {"crew_id": test_crew_id, "inputs": {"topic": "Event ordering test"}}
    response = await authed_client.post("/api/v1/executions", json=crew_payload)
    execution_id = response.json()["id"]

    events_received = []

    async def collect_events():
        import httpx
        async with httpx.AsyncClient() as client:
            url = f"{authed_client.base_url}/api/v1/executions/{execution_id}/traces/stream?token={auth_token}"
            async with client.stream("GET", url) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            event = json.loads(line[6:])
                            events_received.append(event)
                            if event.get("type") == "stream_closed" or len(events_received) > 20:
                                break
                        except json.JSONDecodeError:
                            continue

    try:
        await asyncio.wait_for(collect_events(), timeout=15)
    except asyncio.TimeoutError:
        pass

    # First event should be 'connected'
    if len(events_received) > 0:
        assert events_received[0]["type"] == "connected"

    # trace_started should come before trace_completed for same trace
    trace_events = {}
    for event in events_received:
        if event.get("type") in ["trace_started", "trace_completed"]:
            trace_id = event.get("data", {}).get("id")
            if trace_id:
                if trace_id not in trace_events:
                    trace_events[trace_id] = []
                trace_events[trace_id].append(event["type"])

    # For each trace, started should come before completed
    for trace_id, event_types in trace_events.items():
        if "trace_started" in event_types and "trace_completed" in event_types:
            started_idx = event_types.index("trace_started")
            completed_idx = event_types.index("trace_completed")
            assert started_idx < completed_idx, f"Trace {trace_id}: completed before started"
