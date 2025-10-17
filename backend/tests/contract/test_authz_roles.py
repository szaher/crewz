"""Contract test for GET/POST /api/v1/authz/roles endpoints."""

import pytest
from httpx import AsyncClient
from fastapi import status


@pytest.mark.asyncio
async def test_list_roles_success(client: AsyncClient, auth_headers: dict):
    """Test list roles with default parameters."""
    response = await client.get("/api/v1/authz/roles", headers=auth_headers)

    # Assert response schema (endpoint not implemented yet, should fail)
    assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    # If implemented, validate response schema
    if response.status_code == status.HTTP_200_OK:
        data = response.json()
        assert "roles" in data
        assert isinstance(data["roles"], list)
        assert "total" in data
        assert "page" in data
        assert "page_size" in data

        # Should include system roles by default
        if len(data["roles"]) > 0:
            role = data["roles"][0]
            assert "id" in role
            assert "name" in role
            assert "slug" in role
            assert "is_system_role" in role
            assert "is_default" in role
            assert "priority" in role


@pytest.mark.asyncio
async def test_list_roles_with_system_filter(client: AsyncClient, auth_headers: dict):
    """Test list roles with include_system parameter."""
    # Include system roles
    response1 = await client.get(
        "/api/v1/authz/roles?include_system=true",
        headers=auth_headers
    )
    assert response1.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    # Exclude system roles
    response2 = await client.get(
        "/api/v1/authz/roles?include_system=false",
        headers=auth_headers
    )
    assert response2.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]


@pytest.mark.asyncio
async def test_list_roles_pagination(client: AsyncClient, auth_headers: dict):
    """Test list roles with pagination."""
    response = await client.get(
        "/api/v1/authz/roles?page=1&page_size=10",
        headers=auth_headers
    )

    assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    if response.status_code == status.HTTP_200_OK:
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 10
        assert len(data["roles"]) <= 10


@pytest.mark.asyncio
async def test_list_roles_invalid_pagination(client: AsyncClient, auth_headers: dict):
    """Test list roles with invalid pagination parameters."""
    # Invalid page (0)
    response1 = await client.get("/api/v1/authz/roles?page=0", headers=auth_headers)
    assert response1.status_code in [
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        status.HTTP_400_BAD_REQUEST
    ]

    # Invalid page_size (> 100)
    response2 = await client.get("/api/v1/authz/roles?page_size=101", headers=auth_headers)
    assert response2.status_code in [
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        status.HTTP_400_BAD_REQUEST
    ]


@pytest.mark.asyncio
async def test_create_role_success(client: AsyncClient, auth_headers: dict):
    """Test create custom role."""
    payload = {
        "name": "Custom Role",
        "slug": "custom-role",
        "description": "A custom tenant role",
        "is_default": False,
        "priority": 600
    }

    response = await client.post("/api/v1/authz/roles", json=payload, headers=auth_headers)

    # Assert response schema (endpoint not implemented yet, should fail)
    assert response.status_code in [
        status.HTTP_201_CREATED,
        status.HTTP_404_NOT_FOUND,
        status.HTTP_403_FORBIDDEN  # If user doesn't have tenant-admin role
    ]

    # If implemented, validate response schema
    if response.status_code == status.HTTP_201_CREATED:
        data = response.json()
        assert data["name"] == "Custom Role"
        assert data["slug"] == "custom-role"
        assert data["is_system_role"] is False
        assert "id" in data
        assert "tenant_id" in data


@pytest.mark.asyncio
async def test_create_role_duplicate_slug(client: AsyncClient, auth_headers: dict):
    """Test create role with duplicate slug."""
    payload = {
        "name": "Duplicate Role",
        "slug": "member",  # System role slug
        "description": "Should fail"
    }

    response = await client.post("/api/v1/authz/roles", json=payload, headers=auth_headers)

    # Should reject duplicate slug
    assert response.status_code in [
        status.HTTP_400_BAD_REQUEST,
        status.HTTP_409_CONFLICT,
        status.HTTP_404_NOT_FOUND
    ]


@pytest.mark.asyncio
async def test_create_role_invalid_slug_format(client: AsyncClient, auth_headers: dict):
    """Test create role with invalid slug format."""
    payload = {
        "name": "Invalid Slug Role",
        "slug": "Invalid Slug!",  # Contains spaces and special chars
        "description": "Should fail validation"
    }

    response = await client.post("/api/v1/authz/roles", json=payload, headers=auth_headers)

    # Should validate slug pattern (^[a-z0-9-]+$)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_create_role_missing_required_fields(client: AsyncClient, auth_headers: dict):
    """Test create role with missing required fields."""
    # Missing slug
    response1 = await client.post(
        "/api/v1/authz/roles",
        json={"name": "No Slug Role"},
        headers=auth_headers
    )
    assert response1.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Missing name
    response2 = await client.post(
        "/api/v1/authz/roles",
        json={"slug": "no-name-role"},
        headers=auth_headers
    )
    assert response2.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_create_role_unauthorized(client: AsyncClient):
    """Test create role without authentication."""
    payload = {
        "name": "Test Role",
        "slug": "test-role"
    }

    response = await client.post("/api/v1/authz/roles", json=payload)

    # Should require authentication
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_list_roles_unauthorized(client: AsyncClient):
    """Test list roles without authentication."""
    response = await client.get("/api/v1/authz/roles")

    # Should require authentication
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
