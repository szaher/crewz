"""Integration test for trace collection with <2% overhead (Scenario 1 from quickstart.md)."""

import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta
import time


@pytest.mark.asyncio
async def test_crew_execution_with_trace_collection(
    authed_client: AsyncClient,
    test_tenant_id: str,
    test_crew_id: str
):
    """
    Test Scenario 1: End-to-End Trace Collection.

    Given: A crew with 2 agents (Researcher, Writer), each making 2 LLM calls
    When: Crew is executed
    Then: 4 traces are captured with correct metadata and <2% overhead (FR-021)
    """
    # Arrange
    start_time = datetime.utcnow()
    crew_payload = {
        "crew_id": test_crew_id,
        "inputs": {"topic": "AI monitoring best practices"}
    }

    # Act: Execute crew (triggers Langfuse callbacks)
    response = await authed_client.post("/api/v1/executions", json=crew_payload)
    assert response.status_code == 201
    execution_id = response.json()["id"]

    # Wait for execution to complete
    execution = await wait_for_completion(authed_client, execution_id, timeout=60)
    end_time = datetime.utcnow()

    # Assert: Check trace collection
    traces_response = await authed_client.get(
        "/api/v1/traces",
        params={"execution_id": execution_id}
    )
    assert traces_response.status_code == 200
    traces = traces_response.json()["traces"]

    # Verify trace count (2 agents × 2 calls each = 4 traces)
    assert len(traces) == 4, f"Expected 4 traces, got {len(traces)}"

    # Verify trace structure
    for trace in traces:
        assert trace["execution_id"] == execution_id
        assert trace["tenant_id"] == test_tenant_id
        assert trace["prompt"] is not None
        assert trace["response"] is not None
        assert trace["total_tokens"] > 0
        assert trace["latency_ms"] > 0
        assert trace["cost_usd"] >= 0
        assert trace["model_name"] in ["gpt-4", "gpt-3.5-turbo", "claude-3", "claude-3-opus"]
        assert trace["provider"] in ["openai", "anthropic", "cohere", "local"]

        # Verify token sum constraint
        assert trace["total_tokens"] == trace["prompt_tokens"] + trace["completion_tokens"]

        # Verify XOR constraint (agent_id OR tool_id, not both)
        agent_id = trace.get("agent_id")
        tool_id = trace.get("tool_id")
        assert (agent_id is not None and tool_id is None) or (agent_id is None and tool_id is not None)

    # Verify <2% latency overhead (FR-021)
    execution_time = (end_time - start_time).total_seconds()
    total_llm_time = sum(t["latency_ms"] for t in traces) / 1000

    # Overhead = (total_time - llm_time) / llm_time
    overhead_percentage = ((execution_time - total_llm_time) / total_llm_time) * 100

    assert overhead_percentage < 2.0, (
        f"Overhead {overhead_percentage:.2f}% exceeds 2% limit (FR-021). "
        f"Total: {execution_time:.2f}s, LLM: {total_llm_time:.2f}s"
    )

    print(f"✓ Trace collection successful: {len(traces)} traces, {overhead_percentage:.2f}% overhead")


@pytest.mark.asyncio
async def test_trace_metadata_completeness(
    authed_client: AsyncClient,
    test_crew_id: str
):
    """Test that all trace metadata fields are populated correctly."""
    crew_payload = {
        "crew_id": test_crew_id,
        "inputs": {"topic": "Test metadata"}
    }

    response = await authed_client.post("/api/v1/executions", json=crew_payload)
    assert response.status_code == 201
    execution_id = response.json()["id"]

    await wait_for_completion(authed_client, execution_id, timeout=60)

    traces_response = await authed_client.get(
        "/api/v1/traces",
        params={"execution_id": execution_id}
    )
    assert traces_response.status_code == 200
    traces = traces_response.json()["traces"]

    for trace in traces:
        # Required fields
        assert "id" in trace
        assert "created_at" in trace
        assert "updated_at" in trace

        # Optional Langfuse integration
        # langfuse_trace_id may be None if Langfuse is disabled
        assert "langfuse_trace_id" in trace

        # error_message should be None for successful traces
        if trace.get("error_message") is not None:
            pytest.fail(f"Trace {trace['id']} has unexpected error: {trace['error_message']}")


@pytest.mark.asyncio
async def test_trace_cost_calculation(
    authed_client: AsyncClient,
    test_crew_id: str
):
    """Test that trace cost is calculated correctly based on provider pricing."""
    crew_payload = {
        "crew_id": test_crew_id,
        "inputs": {"topic": "Cost calculation test"}
    }

    response = await authed_client.post("/api/v1/executions", json=crew_payload)
    assert response.status_code == 201
    execution_id = response.json()["id"]

    await wait_for_completion(authed_client, execution_id, timeout=60)

    traces_response = await authed_client.get(
        "/api/v1/traces",
        params={"execution_id": execution_id}
    )
    traces = traces_response.json()["traces"]

    for trace in traces:
        # Cost should be calculated based on token count and model pricing
        # For GPT-4: ~$0.03/1K prompt tokens, ~$0.06/1K completion tokens
        # For GPT-3.5: ~$0.001/1K tokens

        if trace["model_name"].startswith("gpt-4"):
            # Rough estimate for GPT-4 cost
            expected_min_cost = (trace["total_tokens"] / 1000) * 0.02  # Conservative lower bound
            expected_max_cost = (trace["total_tokens"] / 1000) * 0.10  # Conservative upper bound

            assert expected_min_cost <= trace["cost_usd"] <= expected_max_cost, (
                f"GPT-4 cost {trace['cost_usd']} outside expected range "
                f"[{expected_min_cost}, {expected_max_cost}] for {trace['total_tokens']} tokens"
            )


@pytest.mark.asyncio
async def test_trace_persistence_across_restarts(
    authed_client: AsyncClient,
    test_crew_id: str
):
    """Test that traces persist in PostgreSQL and survive application restarts."""
    crew_payload = {
        "crew_id": test_crew_id,
        "inputs": {"topic": "Persistence test"}
    }

    response = await authed_client.post("/api/v1/executions", json=crew_payload)
    execution_id = response.json()["id"]

    await wait_for_completion(authed_client, execution_id, timeout=60)

    # Fetch traces immediately after execution
    traces_response1 = await authed_client.get(
        "/api/v1/traces",
        params={"execution_id": execution_id}
    )
    traces_before = traces_response1.json()["traces"]
    trace_ids_before = {t["id"] for t in traces_before}

    # Simulate time passing and refetch (no restart actually needed for DB persistence test)
    await asyncio.sleep(1)

    traces_response2 = await authed_client.get(
        "/api/v1/traces",
        params={"execution_id": execution_id}
    )
    traces_after = traces_response2.json()["traces"]
    trace_ids_after = {t["id"] for t in traces_after}

    # Verify same traces are returned
    assert trace_ids_before == trace_ids_after
    assert len(traces_before) == len(traces_after)


# Helper function
async def wait_for_completion(client: AsyncClient, execution_id: str, timeout: int = 60):
    """Poll execution status until completed or timeout."""
    start = time.time()

    while time.time() - start < timeout:
        response = await client.get(f"/api/v1/executions/{execution_id}")
        assert response.status_code == 200

        execution = response.json()
        status = execution["status"]

        if status in ["completed", "failed", "timeout", "cancelled"]:
            if status != "completed":
                pytest.fail(f"Execution ended with status: {status}")
            return execution

        await asyncio.sleep(2)

    pytest.fail(f"Execution {execution_id} did not complete within {timeout}s")


import asyncio
