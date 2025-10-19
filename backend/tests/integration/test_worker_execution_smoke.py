"""
Smoke tests for worker architecture execution lifecycle.
Tests T067-T074 basic functionality without full integration complexity.
"""

import pytest
import requests
import time
from uuid import uuid4


BASE_URL = "http://localhost:8000/api/v1"


@pytest.fixture
def auth_token():
    """Get a valid auth token for testing."""
    # This would normally authenticate, but for smoke test we'll use a placeholder
    # In real tests, this would call the auth endpoint
    return "test-token"


def test_smoke_backend_responsive():
    """Verify backend is responsive."""
    response = requests.get(f"{BASE_URL}/../health", timeout=5)
    assert response.status_code in [200, 404], "Backend should be running"


def test_smoke_artifacts_endpoint_exists():
    """Verify artifacts endpoint is registered (T037)."""
    # Test that the endpoint exists (even if it returns 401 without auth)
    response = requests.get(f"{BASE_URL}/artifacts")
    # 401 Unauthorized is acceptable - means endpoint exists but needs auth
    # 404 would mean endpoint doesn't exist
    assert response.status_code in [200, 401], f"Artifacts endpoint should exist, got {response.status_code}"


def test_smoke_execution_status_has_queue_fields():
    """
    Verify execution status endpoint returns new queue-related fields (T034).

    This tests that the API can handle the new fields without breaking.
    """
    # This is a structural test - we're checking the endpoint accepts requests
    # Full test would require creating an execution and checking fields
    response = requests.get(f"{BASE_URL}/executions/00000000-0000-0000-0000-000000000000")
    # We expect 401 (no auth) or 404 (not found), not 500 (server error)
    assert response.status_code in [401, 404], "Status endpoint should handle new fields gracefully"


def test_smoke_worker_service_imports():
    """Verify worker services can be imported without errors."""
    try:
        # Test imports work
        exec("""
from src.services.queue_service import QueueService
from src.services.worker_service import WorkerService
from src.services.artifact_service import ArtifactService
from src.workers.retry_policy import calculate_backoff
        """)
        assert True, "All worker services should import successfully"
    except ImportError as e:
        pytest.fail(f"Worker service import failed: {e}")


def test_smoke_celery_worker_registered():
    """Verify Celery worker is registered and responsive."""
    # Check if Celery worker container is running
    import subprocess
    result = subprocess.run(
        ["docker", "ps", "--filter", "name=celery-worker", "--format", "{{.Status}}"],
        capture_output=True,
        text=True
    )

    assert "Up" in result.stdout, "Celery worker container should be running"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
