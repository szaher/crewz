"""Contract test for POST /api/v1/auth/login endpoint."""

import pytest
from httpx import AsyncClient
from fastapi import status


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_user: dict):
    """Test successful login with valid credentials."""
    payload = {
        "email": test_user["email"],
        "password": test_user["password"],
    }

    response = await client.post("/api/v1/auth/login", json=payload)

    # Assert status code
    assert response.status_code == status.HTTP_200_OK

    # Assert response schema
    data = response.json()
    assert "access_token" in data
    assert "token_type" in data
    assert "user_id" in data
    assert "tenant_id" in data
    assert "role" in data
    assert data["token_type"] == "bearer"
    assert isinstance(data["access_token"], str)
    assert len(data["access_token"]) > 0


@pytest.mark.asyncio
async def test_login_invalid_email(client: AsyncClient):
    """Test login with non-existent email."""
    payload = {
        "email": "nonexistent@example.com",
        "password": "password123",
    }

    response = await client.post("/api/v1/auth/login", json=payload)

    # Assert unauthorized
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "detail" in response.json()


@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient, test_user: dict):
    """Test login with incorrect password."""
    payload = {
        "email": test_user["email"],
        "password": "wrongpassword",
    }

    response = await client.post("/api/v1/auth/login", json=payload)

    # Assert unauthorized
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_login_missing_fields(client: AsyncClient):
    """Test login with missing required fields."""
    # Missing password
    response1 = await client.post("/api/v1/auth/login", json={"email": "test@example.com"})
    assert response1.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Missing email
    response2 = await client.post("/api/v1/auth/login", json={"password": "password123"})
    assert response2.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
