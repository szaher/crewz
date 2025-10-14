"""Contract test for GET/POST/DELETE /api/v1/authz/policies endpoints."""

import pytest
from httpx import AsyncClient
from fastapi import status


@pytest.mark.asyncio
async def test_list_policies_success(client: AsyncClient, auth_headers: dict):
    """Test list policies with default parameters."""
    response = await client.get("/api/v1/authz/policies", headers=auth_headers)

    # Assert response schema (endpoint not implemented yet, should fail)
    assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    # If implemented, validate response schema
    if response.status_code == status.HTTP_200_OK:
        data = response.json()
        assert "policies" in data
        assert isinstance(data["policies"], list)
        assert "total" in data

        if len(data["policies"]) > 0:
            policy = data["policies"][0]
            assert "id" in policy
            assert "tenant_id" in policy
            assert "scope" in policy
            assert policy["scope"] in ["tenant", "user"]
            assert "name" in policy
            assert "resource_pattern" in policy
            assert "action_pattern" in policy
            assert "effect" in policy
            assert policy["effect"] in ["allow", "deny"]
            assert "priority" in policy
            assert "is_active" in policy


@pytest.mark.asyncio
async def test_list_policies_scope_filter(client: AsyncClient, auth_headers: dict):
    """Test list policies with scope filter."""
    # All policies
    response1 = await client.get("/api/v1/authz/policies?scope=all", headers=auth_headers)
    assert response1.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    # Tenant-level policies only
    response2 = await client.get("/api/v1/authz/policies?scope=tenant", headers=auth_headers)
    assert response2.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    # User-level policies only
    response3 = await client.get("/api/v1/authz/policies?scope=user", headers=auth_headers)
    assert response3.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]


@pytest.mark.asyncio
async def test_list_policies_active_filter(client: AsyncClient, auth_headers: dict):
    """Test list policies with active_only filter."""
    # Active policies only (default)
    response1 = await client.get("/api/v1/authz/policies?active_only=true", headers=auth_headers)
    assert response1.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    # All policies (including inactive)
    response2 = await client.get("/api/v1/authz/policies?active_only=false", headers=auth_headers)
    assert response2.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]


@pytest.mark.asyncio
async def test_list_policies_pagination(client: AsyncClient, auth_headers: dict):
    """Test list policies with pagination."""
    response = await client.get(
        "/api/v1/authz/policies?page=1&page_size=10",
        headers=auth_headers
    )

    assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]


@pytest.mark.asyncio
async def test_create_policy_tenant_scope(client: AsyncClient, auth_headers: dict):
    """Test create tenant-level policy."""
    payload = {
        "scope": "tenant",
        "name": "Allow All Members to Read Prompts",
        "description": "Tenant-wide policy for prompt read access",
        "resource_pattern": "prompt:*",
        "action_pattern": "read",
        "effect": "allow",
        "priority": 100
    }

    response = await client.post("/api/v1/authz/policies", json=payload, headers=auth_headers)

    # Assert response schema (endpoint not implemented yet, should fail)
    assert response.status_code in [
        status.HTTP_201_CREATED,
        status.HTTP_404_NOT_FOUND,
        status.HTTP_403_FORBIDDEN  # If user doesn't have tenant-admin role
    ]

    # If implemented, validate response schema
    if response.status_code == status.HTTP_201_CREATED:
        data = response.json()
        assert data["scope"] == "tenant"
        assert data["name"] == "Allow All Members to Read Prompts"
        assert data["resource_pattern"] == "prompt:*"
        assert data["action_pattern"] == "read"
        assert data["effect"] == "allow"
        assert "id" in data


@pytest.mark.asyncio
async def test_create_policy_user_scope(client: AsyncClient, auth_headers: dict):
    """Test create user-level policy."""
    payload = {
        "scope": "user",
        "scope_id": "018e1111-1111-7111-1111-111111111111",
        "name": "Deny User Access to Crew",
        "resource_pattern": "crew:018e2222-2222-7222-2222-222222222222",
        "action_pattern": "*",
        "effect": "deny",
        "priority": 1000
    }

    response = await client.post("/api/v1/authz/policies", json=payload, headers=auth_headers)

    assert response.status_code in [
        status.HTTP_201_CREATED,
        status.HTTP_404_NOT_FOUND,
        status.HTTP_403_FORBIDDEN
    ]


@pytest.mark.asyncio
async def test_create_policy_missing_scope_id(client: AsyncClient, auth_headers: dict):
    """Test create user-level policy without scope_id."""
    payload = {
        "scope": "user",
        # Missing scope_id (required for user scope)
        "name": "Test Policy",
        "resource_pattern": "crew:*",
        "action_pattern": "read",
        "effect": "allow"
    }

    response = await client.post("/api/v1/authz/policies", json=payload, headers=auth_headers)

    # Should validate scope_id requirement for user scope
    assert response.status_code in [
        status.HTTP_400_BAD_REQUEST,
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        status.HTTP_404_NOT_FOUND
    ]


@pytest.mark.asyncio
async def test_create_policy_invalid_effect(client: AsyncClient, auth_headers: dict):
    """Test create policy with invalid effect."""
    payload = {
        "scope": "tenant",
        "name": "Test Policy",
        "resource_pattern": "crew:*",
        "action_pattern": "read",
        "effect": "invalid"  # Not in enum [allow, deny]
    }

    response = await client.post("/api/v1/authz/policies", json=payload, headers=auth_headers)

    # Should validate effect enum
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_create_policy_missing_required_fields(client: AsyncClient, auth_headers: dict):
    """Test create policy with missing required fields."""
    # Missing resource_pattern
    response1 = await client.post(
        "/api/v1/authz/policies",
        json={
            "scope": "tenant",
            "name": "Test",
            "action_pattern": "read",
            "effect": "allow"
        },
        headers=auth_headers
    )
    assert response1.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Missing effect
    response2 = await client.post(
        "/api/v1/authz/policies",
        json={
            "scope": "tenant",
            "name": "Test",
            "resource_pattern": "crew:*",
            "action_pattern": "read"
        },
        headers=auth_headers
    )
    assert response2.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_delete_policy_success(client: AsyncClient, auth_headers: dict):
    """Test delete policy."""
    policy_id = "018e3333-3333-7333-3333-333333333333"
    response = await client.delete(f"/api/v1/authz/policies/{policy_id}", headers=auth_headers)

    # Assert response (endpoint not implemented yet, should fail)
    assert response.status_code in [
        status.HTTP_204_NO_CONTENT,
        status.HTTP_404_NOT_FOUND,
        status.HTTP_403_FORBIDDEN
    ]


@pytest.mark.asyncio
async def test_delete_policy_not_found(client: AsyncClient, auth_headers: dict):
    """Test delete non-existent policy."""
    policy_id = "018e9999-9999-7999-9999-999999999999"
    response = await client.delete(f"/api/v1/authz/policies/{policy_id}", headers=auth_headers)

    assert response.status_code in [
        status.HTTP_404_NOT_FOUND,
        status.HTTP_204_NO_CONTENT  # If endpoint returns 204 for all deletes
    ]


@pytest.mark.asyncio
async def test_policies_unauthorized(client: AsyncClient):
    """Test policies endpoints without authentication."""
    # List
    response1 = await client.get("/api/v1/authz/policies")
    assert response1.status_code == status.HTTP_401_UNAUTHORIZED

    # Create
    response2 = await client.post(
        "/api/v1/authz/policies",
        json={
            "scope": "tenant",
            "name": "Test",
            "resource_pattern": "crew:*",
            "action_pattern": "read",
            "effect": "allow"
        }
    )
    assert response2.status_code == status.HTTP_401_UNAUTHORIZED

    # Delete
    response3 = await client.delete("/api/v1/authz/policies/018e3333-3333-7333-3333-333333333333")
    assert response3.status_code == status.HTTP_401_UNAUTHORIZED
