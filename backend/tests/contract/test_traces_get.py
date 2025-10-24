"""Contract test for GET /api/v1/traces/{trace_id} endpoint."""

import pytest
from httpx import AsyncClient
from fastapi import status
from uuid import uuid4


@pytest.mark.asyncio
async def test_get_trace_by_id_success(authed_client: AsyncClient, test_trace_id: str):
    """Test successful retrieval of a single trace by ID."""
    response = await authed_client.get(f"/api/v1/traces/{test_trace_id}")

    # Assert status code
    assert response.status_code == status.HTTP_200_OK

    # Assert response schema matches Trace schema from traces-api.yaml
    trace = response.json()

    # Required fields
    assert trace["id"] == test_trace_id
    assert "tenant_id" in trace
    assert "execution_id" in trace
    assert "prompt" in trace
    assert "response" in trace
    assert "model_name" in trace
    assert "provider" in trace
    assert "prompt_tokens" in trace
    assert "completion_tokens" in trace
    assert "total_tokens" in trace
    assert "latency_ms" in trace
    assert "cost_usd" in trace
    assert "created_at" in trace

    # Optional fields (nullable)
    assert "agent_id" in trace
    assert "tool_id" in trace
    assert "langfuse_trace_id" in trace
    assert "error_message" in trace
    assert "metadata" in trace

    # Data type validations
    assert isinstance(trace["prompt"], str)
    assert isinstance(trace["response"], str)
    assert isinstance(trace["prompt_tokens"], int)
    assert isinstance(trace["completion_tokens"], int)
    assert isinstance(trace["total_tokens"], int)
    assert isinstance(trace["latency_ms"], int)
    assert isinstance(trace["cost_usd"], (int, float))


@pytest.mark.asyncio
async def test_get_trace_token_sum_constraint(authed_client: AsyncClient, test_trace_id: str):
    """Test that token sum constraint is enforced (total = prompt + completion)."""
    response = await authed_client.get(f"/api/v1/traces/{test_trace_id}")

    assert response.status_code == status.HTTP_200_OK
    trace = response.json()

    # Verify constraint: total_tokens = prompt_tokens + completion_tokens
    assert trace["total_tokens"] == trace["prompt_tokens"] + trace["completion_tokens"]


@pytest.mark.asyncio
async def test_get_trace_xor_constraint(authed_client: AsyncClient, test_trace_id: str):
    """Test that XOR constraint is enforced (agent_id XOR tool_id)."""
    response = await authed_client.get(f"/api/v1/traces/{test_trace_id}")

    assert response.status_code == status.HTTP_200_OK
    trace = response.json()

    # Either agent_id or tool_id must be set, but not both
    agent_id = trace["agent_id"]
    tool_id = trace["tool_id"]

    assert (agent_id is not None and tool_id is None) or (agent_id is None and tool_id is not None)


@pytest.mark.asyncio
async def test_get_trace_value_constraints(authed_client: AsyncClient, test_trace_id: str):
    """Test that value constraints are enforced."""
    response = await authed_client.get(f"/api/v1/traces/{test_trace_id}")

    assert response.status_code == status.HTTP_200_OK
    trace = response.json()

    # latency_ms > 0
    assert trace["latency_ms"] > 0

    # cost_usd >= 0
    assert trace["cost_usd"] >= 0

    # provider enum
    assert trace["provider"] in ["openai", "anthropic", "cohere", "local"]


@pytest.mark.asyncio
async def test_get_trace_not_found(authed_client: AsyncClient):
    """Test 404 response for non-existent trace."""
    non_existent_id = str(uuid4())
    response = await authed_client.get(f"/api/v1/traces/{non_existent_id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND

    # Assert error response schema
    error = response.json()
    assert "error" in error
    assert "Trace not found" in error["error"] or "not found" in error["error"].lower()


@pytest.mark.asyncio
async def test_get_trace_invalid_uuid(authed_client: AsyncClient):
    """Test 400 response for invalid UUID format."""
    response = await authed_client.get("/api/v1/traces/not-a-uuid")

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_get_trace_unauthorized(client: AsyncClient, test_trace_id: str):
    """Test that endpoint requires authentication."""
    response = await client.get(f"/api/v1/traces/{test_trace_id}")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # Assert error response schema
    error = response.json()
    assert "error" in error
    assert "Unauthorized" in error["error"] or "unauthorized" in error["error"].lower()


@pytest.mark.asyncio
async def test_get_trace_tenant_isolation(authed_client: AsyncClient, other_tenant_trace_id: str):
    """Test that traces from other tenants are not accessible."""
    response = await authed_client.get(f"/api/v1/traces/{other_tenant_trace_id}")

    # Should return 404 (not 403) to avoid leaking existence
    assert response.status_code == status.HTTP_404_NOT_FOUND
