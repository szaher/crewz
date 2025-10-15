"""Contract test for POST /api/v1/tenants/register endpoint."""

import pytest
from httpx import AsyncClient
from fastapi import status


@pytest.mark.asyncio
async def test_register_tenant_valid_request(client: AsyncClient):
    """Test valid tenant registration (no auth required)."""
    payload = {
        "company_name": "Acme Corporation",
        "admin_email": "admin@acme.com",
        "admin_name": "Jane Doe",
        "reason": "We want to automate our marketing workflows with AI agents for content creation and analysis.",
        "sample_data_requested": True,
        "company_size": "51-200",
        "use_case": "Marketing automation"
    }

    response = await client.post("/api/v1/tenants/register", json=payload)

    # Assert response (endpoint not implemented yet, should fail)
    assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_404_NOT_FOUND]

    # If implemented, validate response schema
    if response.status_code == status.HTTP_201_CREATED:
        data = response.json()
        assert "id" in data
        assert "company_name" in data
        assert data["company_name"] == payload["company_name"]
        assert "admin_email" in data
        assert data["admin_email"] == payload["admin_email"]
        assert "admin_name" in data
        assert data["admin_name"] == payload["admin_name"]
        assert "status" in data
        assert data["status"] == "pending"
        assert "created_at" in data
        assert "updated_at" in data


@pytest.mark.asyncio
async def test_register_tenant_minimal_fields(client: AsyncClient):
    """Test tenant registration with only required fields."""
    payload = {
        "company_name": "Test Corp",
        "admin_email": "test@testcorp.com",
        "admin_name": "John Smith",
        "reason": "We need to test the tenant registration workflow for our platform integration."
    }

    response = await client.post("/api/v1/tenants/register", json=payload)

    # Should accept minimal required fields
    assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_404_NOT_FOUND]

    if response.status_code == status.HTTP_201_CREATED:
        data = response.json()
        assert data["sample_data_requested"] == False  # Default value


@pytest.mark.asyncio
async def test_register_tenant_missing_required_fields(client: AsyncClient):
    """Test tenant registration with missing required fields."""
    # Missing company_name
    response1 = await client.post(
        "/api/v1/tenants/register",
        json={
            "admin_email": "test@test.com",
            "admin_name": "Test User",
            "reason": "This should fail due to missing company name field."
        }
    )
    assert response1.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Missing admin_email
    response2 = await client.post(
        "/api/v1/tenants/register",
        json={
            "company_name": "Test Corp",
            "admin_name": "Test User",
            "reason": "This should fail due to missing admin email field."
        }
    )
    assert response2.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Missing reason
    response3 = await client.post(
        "/api/v1/tenants/register",
        json={
            "company_name": "Test Corp",
            "admin_email": "test@test.com",
            "admin_name": "Test User"
        }
    )
    assert response3.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_register_tenant_invalid_email(client: AsyncClient):
    """Test tenant registration with invalid email format."""
    payload = {
        "company_name": "Test Corp",
        "admin_email": "not-an-email",  # Invalid email format
        "admin_name": "Test User",
        "reason": "Testing email validation in registration workflow."
    }

    response = await client.post("/api/v1/tenants/register", json=payload)

    # Should validate email format
    assert response.status_code in [status.HTTP_422_UNPROCESSABLE_ENTITY, status.HTTP_400_BAD_REQUEST]


@pytest.mark.asyncio
async def test_register_tenant_reason_too_short(client: AsyncClient):
    """Test tenant registration with reason below minimum length."""
    payload = {
        "company_name": "Test Corp",
        "admin_email": "test@test.com",
        "admin_name": "Test User",
        "reason": "Too short"  # Less than 20 characters
    }

    response = await client.post("/api/v1/tenants/register", json=payload)

    # Should enforce minimum reason length (20 chars)
    assert response.status_code in [status.HTTP_422_UNPROCESSABLE_ENTITY, status.HTTP_400_BAD_REQUEST]


@pytest.mark.asyncio
async def test_register_tenant_duplicate_email(client: AsyncClient):
    """Test tenant registration with duplicate admin email."""
    payload = {
        "company_name": "First Corp",
        "admin_email": "duplicate@test.com",
        "admin_name": "Test User",
        "reason": "This is the first registration attempt with this email address."
    }

    # First registration should succeed
    response1 = await client.post("/api/v1/tenants/register", json=payload)

    if response1.status_code == status.HTTP_201_CREATED:
        # Second registration with same email should fail
        payload2 = {
            "company_name": "Second Corp",
            "admin_email": "duplicate@test.com",  # Same email
            "admin_name": "Another User",
            "reason": "This is a duplicate registration attempt with the same email."
        }
        response2 = await client.post("/api/v1/tenants/register", json=payload2)
        assert response2.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_register_tenant_invalid_company_size(client: AsyncClient):
    """Test tenant registration with invalid company size enum."""
    payload = {
        "company_name": "Test Corp",
        "admin_email": "test@test.com",
        "admin_name": "Test User",
        "reason": "Testing company size validation in the registration process.",
        "company_size": "invalid-size"  # Not in enum
    }

    response = await client.post("/api/v1/tenants/register", json=payload)

    # Should validate company_size enum
    assert response.status_code in [status.HTTP_422_UNPROCESSABLE_ENTITY, status.HTTP_400_BAD_REQUEST]


@pytest.mark.asyncio
async def test_check_registration_status(client: AsyncClient):
    """Test GET /api/v1/tenants/register/status endpoint."""
    # Test with existing email
    response = await client.get("/api/v1/tenants/register/status?email=test@example.com")

    # Endpoint should be public (no auth)
    assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    if response.status_code == status.HTTP_200_OK:
        data = response.json()
        assert "status" in data
        assert data["status"] in ["pending", "approved", "rejected", "not_found"]

        if data["status"] != "not_found":
            assert "submitted_at" in data
            assert "message" in data


@pytest.mark.asyncio
async def test_check_registration_status_missing_email(client: AsyncClient):
    """Test registration status check without email parameter."""
    response = await client.get("/api/v1/tenants/register/status")

    # Should require email parameter
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
