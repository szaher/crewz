"""Contract test for POST /api/v1/auth/register endpoint."""

import pytest
from httpx import AsyncClient
from fastapi import status


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    """Test successful user registration."""
    payload = {
        "email": "test@example.com",
        "password": "securepass123",
        "full_name": "Test User",
        "tenant_name": "Test Org",
    }

    response = await client.post("/api/v1/auth/register", json=payload)

    # Assert status code
    assert response.status_code == status.HTTP_201_CREATED

    # Assert response schema
    data = response.json()
    assert "user_id" in data
    assert "tenant_id" in data
    assert "email" in data
    assert "message" in data
    assert data["email"] == payload["email"]
    assert isinstance(data["user_id"], int)
    assert isinstance(data["tenant_id"], int)


@pytest.mark.asyncio
async def test_register_invalid_email(client: AsyncClient):
    """Test registration with invalid email."""
    payload = {
        "email": "invalid-email",
        "password": "securepass123",
        "full_name": "Test User",
    }

    response = await client.post("/api/v1/auth/register", json=payload)

    # Assert validation error
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_register_short_password(client: AsyncClient):
    """Test registration with password too short."""
    payload = {
        "email": "test@example.com",
        "password": "short",
        "full_name": "Test User",
    }

    response = await client.post("/api/v1/auth/register", json=payload)

    # Assert validation error
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    """Test registration with duplicate email."""
    payload = {
        "email": "duplicate@example.com",
        "password": "securepass123",
        "full_name": "Test User",
    }

    # First registration
    response1 = await client.post("/api/v1/auth/register", json=payload)
    assert response1.status_code == status.HTTP_201_CREATED

    # Duplicate registration
    response2 = await client.post("/api/v1/auth/register", json=payload)
    assert response2.status_code == status.HTTP_400_BAD_REQUEST
    assert "email" in response2.json()["detail"].lower()
