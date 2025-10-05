"""Contract test for POST /api/v1/flows/{flow_id}/execute endpoint."""

import pytest
from httpx import AsyncClient
from fastapi import status


@pytest.mark.asyncio
async def test_execute_flow_success(authed_client: AsyncClient, test_flow: dict):
    """Test successful flow execution."""
    flow_id = test_flow["id"]
    payload = {
        "input_data": {
            "task": "Test task",
            "context": "Test context",
        }
    }

    response = await authed_client.post(f"/api/v1/flows/{flow_id}/execute", json=payload)

    # Assert status code (execution started)
    assert response.status_code == status.HTTP_201_CREATED

    # Assert response schema
    data = response.json()
    assert "id" in data  # execution_id
    assert "execution_type" in data
    assert data["execution_type"] == "flow"
    assert "status" in data
    assert data["status"] in ["pending", "running"]
    assert data["flow_id"] == flow_id
    assert "input_data" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_execute_flow_not_found(authed_client: AsyncClient):
    """Test execution of non-existent flow."""
    response = await authed_client.post(
        "/api/v1/flows/99999/execute", json={"input_data": {}}
    )

    # Assert not found
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_execute_flow_draft_status(authed_client: AsyncClient, test_flow: dict):
    """Test execution of draft flow (should succeed)."""
    flow_id = test_flow["id"]

    # Ensure flow is in draft status
    await authed_client.put(f"/api/v1/flows/{flow_id}", json={"status": "draft"})

    response = await authed_client.post(
        f"/api/v1/flows/{flow_id}/execute", json={"input_data": {"test": "data"}}
    )

    # Draft flows should be executable
    assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.asyncio
async def test_execute_flow_archived_status(authed_client: AsyncClient, test_flow: dict):
    """Test execution of archived flow (should fail)."""
    flow_id = test_flow["id"]

    # Archive the flow
    await authed_client.put(f"/api/v1/flows/{flow_id}", json={"status": "archived"})

    response = await authed_client.post(
        f"/api/v1/flows/{flow_id}/execute", json={"input_data": {}}
    )

    # Archived flows should not be executable
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "archived" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_execution_status(authed_client: AsyncClient, test_execution: dict):
    """Test getting execution status."""
    execution_id = test_execution["id"]
    response = await authed_client.get(f"/api/v1/executions/{execution_id}")

    # Assert status code
    assert response.status_code == status.HTTP_200_OK

    # Assert response schema
    data = response.json()
    assert data["id"] == execution_id
    assert "status" in data
    assert data["status"] in ["pending", "running", "completed", "failed", "cancelled"]
    assert "input_data" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_execute_flow_unauthenticated(client: AsyncClient):
    """Test flow execution without authentication."""
    response = await client.post("/api/v1/flows/1/execute", json={"input_data": {}})

    # Assert unauthorized
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
