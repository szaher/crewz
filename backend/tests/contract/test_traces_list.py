"""Contract test for GET /api/v1/traces endpoint."""

import pytest
from httpx import AsyncClient
from fastapi import status
from datetime import datetime, timedelta


@pytest.mark.asyncio
async def test_list_traces_success(authed_client: AsyncClient):
    """Test successful trace listing with pagination."""
    response = await authed_client.get(
        "/api/v1/traces",
        params={"limit": 10, "offset": 0}
    )

    # Assert status code
    assert response.status_code == status.HTTP_200_OK

    # Assert response schema per traces-api.yaml
    data = response.json()
    assert "traces" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    assert isinstance(data["traces"], list)
    assert isinstance(data["total"], int)
    assert data["limit"] == 10
    assert data["offset"] == 0


@pytest.mark.asyncio
async def test_list_traces_with_execution_id_filter(authed_client: AsyncClient, test_execution_id: str):
    """Test filtering traces by execution_id."""
    response = await authed_client.get(
        "/api/v1/traces",
        params={"execution_id": test_execution_id}
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # All traces should have matching execution_id
    for trace in data["traces"]:
        assert trace["execution_id"] == test_execution_id


@pytest.mark.asyncio
async def test_list_traces_with_date_range_filter(authed_client: AsyncClient):
    """Test filtering traces by date range."""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=7)

    response = await authed_client.get(
        "/api/v1/traces",
        params={
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Verify traces are within date range
    for trace in data["traces"]:
        trace_time = datetime.fromisoformat(trace["created_at"].replace("Z", "+00:00"))
        assert start_date <= trace_time <= end_date


@pytest.mark.asyncio
async def test_list_traces_with_provider_filter(authed_client: AsyncClient):
    """Test filtering traces by LLM provider."""
    response = await authed_client.get(
        "/api/v1/traces",
        params={"provider": "openai"}
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # All traces should have matching provider
    for trace in data["traces"]:
        assert trace["provider"] == "openai"


@pytest.mark.asyncio
async def test_list_traces_with_cost_range_filter(authed_client: AsyncClient):
    """Test filtering traces by cost range."""
    response = await authed_client.get(
        "/api/v1/traces",
        params={"min_cost": 0.001, "max_cost": 0.1}
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # All traces should be within cost range
    for trace in data["traces"]:
        assert 0.001 <= trace["cost_usd"] <= 0.1


@pytest.mark.asyncio
async def test_list_traces_with_error_filter(authed_client: AsyncClient):
    """Test filtering traces with errors."""
    response = await authed_client.get(
        "/api/v1/traces",
        params={"has_error": True}
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # All traces should have error_message
    for trace in data["traces"]:
        assert trace["error_message"] is not None


@pytest.mark.asyncio
async def test_list_traces_pagination_limits(authed_client: AsyncClient):
    """Test pagination limits enforcement."""
    # Test exceeding max limit
    response = await authed_client.get(
        "/api/v1/traces",
        params={"limit": 2000}  # Exceeds max of 1000
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_list_traces_invalid_uuid(authed_client: AsyncClient):
    """Test validation of UUID format."""
    response = await authed_client.get(
        "/api/v1/traces",
        params={"execution_id": "not-a-uuid"}
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_list_traces_response_schema(authed_client: AsyncClient):
    """Test that trace response matches schema from traces-api.yaml."""
    response = await authed_client.get("/api/v1/traces", params={"limit": 1})

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    if len(data["traces"]) > 0:
        trace = data["traces"][0]

        # Required fields per OpenAPI spec
        assert "id" in trace
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

        # Token sum validation
        assert trace["total_tokens"] == trace["prompt_tokens"] + trace["completion_tokens"]

        # Value constraints
        assert trace["latency_ms"] > 0
        assert trace["cost_usd"] >= 0
        assert trace["provider"] in ["openai", "anthropic", "cohere", "local"]


@pytest.mark.asyncio
async def test_list_traces_unauthorized(client: AsyncClient):
    """Test that endpoint requires authentication."""
    response = await client.get("/api/v1/traces")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
