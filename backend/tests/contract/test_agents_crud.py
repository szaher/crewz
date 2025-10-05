"""Contract test for /api/v1/agents CRUD endpoints."""

import pytest
from httpx import AsyncClient
from fastapi import status


@pytest.mark.asyncio
async def test_create_agent_success(authed_client: AsyncClient, test_llm_provider: dict):
    """Test successful agent creation."""
    payload = {
        "name": "Research Agent",
        "role": "Senior Researcher",
        "goal": "Conduct thorough research on given topics",
        "backstory": "An experienced researcher with deep domain knowledge",
        "llm_provider_id": test_llm_provider["id"],
        "temperature": 0.7,
        "allow_delegation": True,
        "verbose": False,
        "tool_ids": [],
    }

    response = await authed_client.post("/api/v1/agents", json=payload)

    # Assert status code
    assert response.status_code == status.HTTP_201_CREATED

    # Assert response schema
    data = response.json()
    assert "id" in data
    assert data["name"] == payload["name"]
    assert data["role"] == payload["role"]
    assert data["goal"] == payload["goal"]
    assert data["backstory"] == payload["backstory"]
    assert data["llm_provider_id"] == payload["llm_provider_id"]
    assert data["temperature"] == payload["temperature"]
    assert "created_at" in data
    assert "updated_at" in data


@pytest.mark.asyncio
async def test_list_agents(authed_client: AsyncClient):
    """Test listing agents with pagination."""
    response = await authed_client.get("/api/v1/agents?page=1&page_size=10")

    # Assert status code
    assert response.status_code == status.HTTP_200_OK

    # Assert response schema
    data = response.json()
    assert "agents" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert isinstance(data["agents"], list)


@pytest.mark.asyncio
async def test_get_agent_by_id(authed_client: AsyncClient, test_agent: dict):
    """Test getting a specific agent by ID."""
    agent_id = test_agent["id"]
    response = await authed_client.get(f"/api/v1/agents/{agent_id}")

    # Assert status code
    assert response.status_code == status.HTTP_200_OK

    # Assert response matches created agent
    data = response.json()
    assert data["id"] == agent_id
    assert "name" in data
    assert "role" in data


@pytest.mark.asyncio
async def test_update_agent(authed_client: AsyncClient, test_agent: dict):
    """Test updating an agent."""
    agent_id = test_agent["id"]
    update_payload = {
        "name": "Updated Agent Name",
        "temperature": 0.9,
    }

    response = await authed_client.put(f"/api/v1/agents/{agent_id}", json=update_payload)

    # Assert status code
    assert response.status_code == status.HTTP_200_OK

    # Assert updates applied
    data = response.json()
    assert data["name"] == update_payload["name"]
    assert data["temperature"] == update_payload["temperature"]


@pytest.mark.asyncio
async def test_delete_agent(authed_client: AsyncClient, test_agent: dict):
    """Test deleting an agent."""
    agent_id = test_agent["id"]
    response = await authed_client.delete(f"/api/v1/agents/{agent_id}")

    # Assert status code
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Verify deletion
    get_response = await authed_client.get(f"/api/v1/agents/{agent_id}")
    assert get_response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_create_agent_invalid_temperature(authed_client: AsyncClient, test_llm_provider: dict):
    """Test agent creation with invalid temperature."""
    payload = {
        "name": "Test Agent",
        "role": "Tester",
        "goal": "Test things",
        "backstory": "A tester",
        "llm_provider_id": test_llm_provider["id"],
        "temperature": 3.0,  # Invalid: must be 0.0-2.0
    }

    response = await authed_client.post("/api/v1/agents", json=payload)

    # Assert validation error
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
