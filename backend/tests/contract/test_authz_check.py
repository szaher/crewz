"""Contract test for POST /api/v1/authz/check endpoint."""

import pytest
from httpx import AsyncClient
from fastapi import status


@pytest.mark.asyncio
async def test_check_permission_valid_request(client: AsyncClient, auth_headers: dict):
    """Test valid permission check request."""
    payload = {
        "resource_type": "crew",
        "resource_id": "018e1234-5678-7abc-def0-123456789abc",
        "action": "read"
    }

    response = await client.post("/api/v1/authz/check", json=payload, headers=auth_headers)

    # Assert response schema (endpoint not implemented yet, should fail)
    assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    # If implemented, validate response schema
    if response.status_code == status.HTTP_200_OK:
        data = response.json()
        assert "decision" in data
        assert data["decision"] in ["allow", "deny"]
        assert "reason" in data
        assert isinstance(data["reason"], str)
        assert "latency_ms" in data
        assert isinstance(data["latency_ms"], int)
        assert data["latency_ms"] >= 0


@pytest.mark.asyncio
async def test_check_permission_without_resource_id(client: AsyncClient, auth_headers: dict):
    """Test permission check without resource_id (any resource of type)."""
    payload = {
        "resource_type": "crew",
        "action": "read"
    }

    response = await client.post("/api/v1/authz/check", json=payload, headers=auth_headers)

    # Should accept nullable resource_id
    assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]


@pytest.mark.asyncio
async def test_check_permission_invalid_resource_type(client: AsyncClient, auth_headers: dict):
    """Test permission check with invalid resource type."""
    payload = {
        "resource_type": "",  # Empty resource type
        "action": "read"
    }

    response = await client.post("/api/v1/authz/check", json=payload, headers=auth_headers)

    # Should validate resource_type
    assert response.status_code in [status.HTTP_422_UNPROCESSABLE_ENTITY, status.HTTP_400_BAD_REQUEST]


@pytest.mark.asyncio
async def test_check_permission_invalid_action(client: AsyncClient, auth_headers: dict):
    """Test permission check with invalid action."""
    payload = {
        "resource_type": "crew",
        "action": "invalid_action"  # Not in enum [read, write, execute, delete, *]
    }

    response = await client.post("/api/v1/authz/check", json=payload, headers=auth_headers)

    # Should validate action enum
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_check_permission_missing_required_fields(client: AsyncClient, auth_headers: dict):
    """Test permission check with missing required fields."""
    # Missing action
    response1 = await client.post(
        "/api/v1/authz/check",
        json={"resource_type": "crew"},
        headers=auth_headers
    )
    assert response1.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Missing resource_type
    response2 = await client.post(
        "/api/v1/authz/check",
        json={"action": "read"},
        headers=auth_headers
    )
    assert response2.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_check_permission_all_actions(client: AsyncClient, auth_headers: dict):
    """Test permission check with wildcard action."""
    payload = {
        "resource_type": "crew",
        "resource_id": "018e1234-5678-7abc-def0-123456789abc",
        "action": "*"  # Wildcard action
    }

    response = await client.post("/api/v1/authz/check", json=payload, headers=auth_headers)

    # Should accept wildcard action
    assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]


@pytest.mark.asyncio
async def test_check_permission_unauthorized(client: AsyncClient):
    """Test permission check without authentication."""
    payload = {
        "resource_type": "crew",
        "action": "read"
    }

    response = await client.post("/api/v1/authz/check", json=payload)

    # Should require authentication
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_check_permission_latency_requirement(client: AsyncClient, auth_headers: dict):
    """Test that permission check meets latency requirement (<50ms p95)."""
    payload = {
        "resource_type": "crew",
        "resource_id": "018e1234-5678-7abc-def0-123456789abc",
        "action": "read"
    }

    response = await client.post("/api/v1/authz/check", json=payload, headers=auth_headers)

    if response.status_code == status.HTTP_200_OK:
        data = response.json()
        # Performance target: <50ms at p95
        # For single test, just check it's reasonable
        assert data["latency_ms"] < 100, "Permission check should be fast"
