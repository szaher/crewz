"""Contract test for GET/POST /api/v1/flows endpoints."""

import pytest
from httpx import AsyncClient
from fastapi import status


@pytest.mark.asyncio
async def test_create_flow_success(authed_client: AsyncClient):
    """Test successful flow creation."""
    payload = {
        "name": "Test Flow",
        "description": "A test flow for contract testing",
        "nodes": [
            {
                "id": "node1",
                "type": "input",
                "position": {"x": 100, "y": 100},
                "data": {"label": "Start"},
            },
            {
                "id": "node2",
                "type": "agent",
                "position": {"x": 300, "y": 100},
                "data": {"agent_id": 1},
            },
        ],
        "edges": [
            {
                "id": "edge1",
                "source": "node1",
                "target": "node2",
            }
        ],
        "tags": ["test", "sample"],
    }

    response = await authed_client.post("/api/v1/flows", json=payload)

    # Assert status code
    assert response.status_code == status.HTTP_201_CREATED

    # Assert response schema
    data = response.json()
    assert "id" in data
    assert data["name"] == payload["name"]
    assert data["description"] == payload["description"]
    assert data["status"] == "draft"
    assert len(data["nodes"]) == 2
    assert len(data["edges"]) == 1
    assert data["tags"] == payload["tags"]
    assert "created_at" in data
    assert "updated_at" in data


@pytest.mark.asyncio
async def test_list_flows(authed_client: AsyncClient):
    """Test listing flows with pagination."""
    response = await authed_client.get("/api/v1/flows?page=1&page_size=10")

    # Assert status code
    assert response.status_code == status.HTTP_200_OK

    # Assert response schema
    data = response.json()
    assert "flows" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert isinstance(data["flows"], list)
    assert isinstance(data["total"], int)


@pytest.mark.asyncio
async def test_get_flow_by_id(authed_client: AsyncClient, test_flow: dict):
    """Test getting a specific flow by ID."""
    flow_id = test_flow["id"]
    response = await authed_client.get(f"/api/v1/flows/{flow_id}")

    # Assert status code
    assert response.status_code == status.HTTP_200_OK

    # Assert response matches created flow
    data = response.json()
    assert data["id"] == flow_id
    assert "name" in data
    assert "nodes" in data
    assert "edges" in data


@pytest.mark.asyncio
async def test_update_flow(authed_client: AsyncClient, test_flow: dict):
    """Test updating a flow."""
    flow_id = test_flow["id"]
    update_payload = {
        "name": "Updated Flow Name",
        "status": "active",
    }

    response = await authed_client.put(f"/api/v1/flows/{flow_id}", json=update_payload)

    # Assert status code
    assert response.status_code == status.HTTP_200_OK

    # Assert updates applied
    data = response.json()
    assert data["name"] == update_payload["name"]
    assert data["status"] == update_payload["status"]


@pytest.mark.asyncio
async def test_delete_flow(authed_client: AsyncClient, test_flow: dict):
    """Test deleting a flow."""
    flow_id = test_flow["id"]
    response = await authed_client.delete(f"/api/v1/flows/{flow_id}")

    # Assert status code
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Verify deletion
    get_response = await authed_client.get(f"/api/v1/flows/{flow_id}")
    assert get_response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_create_flow_unauthenticated(client: AsyncClient):
    """Test flow creation without authentication."""
    payload = {"name": "Test Flow", "nodes": [], "edges": []}
    response = await client.post("/api/v1/flows", json=payload)

    # Assert unauthorized
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
