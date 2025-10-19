"""Pytest configuration for contract tests."""
import pytest
from fastapi.testclient import TestClient
from typing import Generator


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Create FastAPI test client."""
    from src.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers() -> dict:
    """
    Provide authentication headers for contract tests.

    Note: This is a placeholder. In production, this should generate
    a valid JWT token for a test user.
    """
    # TODO: Generate actual JWT token once auth system is in place
    return {
        "Authorization": "Bearer test-token",
        "Content-Type": "application/json"
    }


@pytest.fixture
def test_tenant_id() -> str:
    """Provide test tenant ID for multi-tenant tests."""
    return "00000000-0000-0000-0000-000000000001"


@pytest.fixture
def test_user_id() -> str:
    """Provide test user ID."""
    return "00000000-0000-0000-0000-000000000002"
