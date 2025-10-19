"""Pytest configuration for integration tests."""
import pytest
from httpx import AsyncClient, ASGITransport
from typing import AsyncGenerator, Dict, Any
import asyncio


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create async test client for integration tests."""
    from src.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def auth_headers() -> Dict[str, str]:
    """
    Provide authentication headers for integration tests.

    Note: This is a placeholder. In production, this should generate
    a valid JWT token for a test user.
    """
    return {
        "Authorization": "Bearer test-token-integration",
        "Content-Type": "application/json"
    }


@pytest.fixture
def test_flow() -> Dict[str, Any]:
    """
    Provide a test flow fixture.

    For integration tests, we use a simplified fixture that doesn't
    require database setup. Tests should handle flow creation if needed.
    """
    from uuid import uuid4

    return {
        "id": str(uuid4()),
        "name": "Test Flow",
        "description": "Integration test flow",
        "status": "active"
    }


@pytest.fixture
def test_user() -> Dict[str, Any]:
    """Provide a test user fixture."""
    from uuid import uuid4

    return {
        "id": str(uuid4()),
        "email": "integration-test@example.com",
        "tenant_id": str(uuid4())
    }
