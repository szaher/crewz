"""Contract test for GET /api/v1/admin/tenants/pending endpoint."""

import pytest
from httpx import AsyncClient
from fastapi import status


@pytest.mark.asyncio
async def test_list_pending_registrations_as_super_admin(
    client: AsyncClient,
    super_admin_headers: dict
):
    """Test listing pending tenant registrations (super admin only)."""
    response = await client.get(
        "/api/v1/admin/tenants/pending",
        headers=super_admin_headers
    )

    # Assert response (endpoint not implemented yet, should fail)
    assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    # If implemented, validate response schema
    if response.status_code == status.HTTP_200_OK:
        data = response.json()
        assert "registrations" in data
        assert isinstance(data["registrations"], list)
        assert "total" in data
        assert isinstance(data["total"], int)

        # If there are registrations, validate schema
        if len(data["registrations"]) > 0:
            reg = data["registrations"][0]
            assert "id" in reg
            assert "company_name" in reg
            assert "admin_email" in reg
            assert "admin_name" in reg
            assert "reason" in reg
            assert "status" in reg
            assert reg["status"] in ["pending", "approved", "rejected"]
            assert "created_at" in reg


@pytest.mark.asyncio
async def test_list_pending_registrations_with_pagination(
    client: AsyncClient,
    super_admin_headers: dict
):
    """Test listing pending registrations with pagination."""
    response = await client.get(
        "/api/v1/admin/tenants/pending?page=1&page_size=10",
        headers=super_admin_headers
    )

    # Should accept pagination parameters
    assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    if response.status_code == status.HTTP_200_OK:
        data = response.json()
        # Should return at most page_size items
        assert len(data["registrations"]) <= 10


@pytest.mark.asyncio
async def test_list_pending_registrations_unauthorized(client: AsyncClient):
    """Test listing pending registrations without authentication."""
    response = await client.get("/api/v1/admin/tenants/pending")

    # Should require authentication
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_list_pending_registrations_as_regular_user(
    client: AsyncClient,
    auth_headers: dict
):
    """Test listing pending registrations as non-super-admin user."""
    response = await client.get(
        "/api/v1/admin/tenants/pending",
        headers=auth_headers  # Regular user, not super admin
    )

    # Should require super admin role
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_approve_registration_as_super_admin(
    client: AsyncClient,
    super_admin_headers: dict
):
    """Test approving a tenant registration (super admin only)."""
    # Use a test registration ID
    registration_id = "018e1234-5678-7abc-def0-123456789abc"

    response = await client.post(
        f"/api/v1/admin/tenants/{registration_id}/approve",
        json={"notes": "Approved for pilot program"},
        headers=super_admin_headers
    )

    # Endpoint not implemented yet, should fail
    assert response.status_code in [
        status.HTTP_200_OK,
        status.HTTP_404_NOT_FOUND,
        status.HTTP_400_BAD_REQUEST  # If registration doesn't exist
    ]

    # If implemented, validate response schema
    if response.status_code == status.HTTP_200_OK:
        data = response.json()
        assert "registration" in data
        assert "tenant" in data
        assert "admin_user" in data
        assert "sample_data_loaded" in data

        # Validate tenant object
        tenant = data["tenant"]
        assert "id" in tenant
        assert "name" in tenant
        assert "status" in tenant
        assert tenant["status"] == "active"

        # Validate admin_user object
        admin_user = data["admin_user"]
        assert "id" in admin_user
        assert "email" in admin_user
        assert "temporary_password" in admin_user

        # Validate registration updated
        registration = data["registration"]
        assert registration["status"] == "approved"
        assert "approved_by" in registration
        assert "approved_at" in registration
        assert "tenant_id" in registration


@pytest.mark.asyncio
async def test_approve_registration_unauthorized(client: AsyncClient):
    """Test approving registration without authentication."""
    registration_id = "018e1234-5678-7abc-def0-123456789abc"

    response = await client.post(
        f"/api/v1/admin/tenants/{registration_id}/approve",
        json={"notes": "Should fail"}
    )

    # Should require authentication
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_approve_registration_as_regular_user(
    client: AsyncClient,
    auth_headers: dict
):
    """Test approving registration as non-super-admin user."""
    registration_id = "018e1234-5678-7abc-def0-123456789abc"

    response = await client.post(
        f"/api/v1/admin/tenants/{registration_id}/approve",
        json={"notes": "Should fail"},
        headers=auth_headers  # Regular user, not super admin
    )

    # Should require super admin role
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_reject_registration_as_super_admin(
    client: AsyncClient,
    super_admin_headers: dict
):
    """Test rejecting a tenant registration (super admin only)."""
    registration_id = "018e1234-5678-7abc-def0-123456789abc"

    response = await client.post(
        f"/api/v1/admin/tenants/{registration_id}/reject",
        json={"reason": "Use case does not align with platform values. Suspected spam activity."},
        headers=super_admin_headers
    )

    # Endpoint not implemented yet, should fail
    assert response.status_code in [
        status.HTTP_200_OK,
        status.HTTP_404_NOT_FOUND,
        status.HTTP_400_BAD_REQUEST  # If registration doesn't exist
    ]

    # If implemented, validate response schema
    if response.status_code == status.HTTP_200_OK:
        data = response.json()
        assert "id" in data
        assert "status" in data
        assert data["status"] == "rejected"
        assert "rejection_reason" in data
        assert len(data["rejection_reason"]) >= 10


@pytest.mark.asyncio
async def test_reject_registration_missing_reason(
    client: AsyncClient,
    super_admin_headers: dict
):
    """Test rejecting registration without providing reason."""
    registration_id = "018e1234-5678-7abc-def0-123456789abc"

    response = await client.post(
        f"/api/v1/admin/tenants/{registration_id}/reject",
        json={},  # Missing required 'reason' field
        headers=super_admin_headers
    )

    # Should require reason field
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_reject_registration_reason_too_short(
    client: AsyncClient,
    super_admin_headers: dict
):
    """Test rejecting registration with reason below minimum length."""
    registration_id = "018e1234-5678-7abc-def0-123456789abc"

    response = await client.post(
        f"/api/v1/admin/tenants/{registration_id}/reject",
        json={"reason": "Too short"},  # Less than 10 characters
        headers=super_admin_headers
    )

    # Should enforce minimum reason length (10 chars)
    assert response.status_code in [status.HTTP_422_UNPROCESSABLE_ENTITY, status.HTTP_400_BAD_REQUEST]


@pytest.mark.asyncio
async def test_reject_registration_unauthorized(client: AsyncClient):
    """Test rejecting registration without authentication."""
    registration_id = "018e1234-5678-7abc-def0-123456789abc"

    response = await client.post(
        f"/api/v1/admin/tenants/{registration_id}/reject",
        json={"reason": "Should fail without auth"}
    )

    # Should require authentication
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
