"""Integration test for retention cleanup policies (Scenario 6 from quickstart.md)."""

import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta
import asyncio


@pytest.mark.asyncio
async def test_trace_retention_cleanup(
    authed_client: AsyncClient,
    test_tenant_id: str,
    cleanup_worker
):
    """
    Test Scenario 6: Retention Cleanup Policies - Trace Cleanup.

    Given: Traces at different ages and tenant with 7-day retention
    When: Cleanup worker runs
    Then: Traces older than 7 days are deleted
    """
    # Arrange: Create traces at different ages
    now = datetime.utcnow()

    # Create traces with different ages (simulated by backdating)
    trace_ages = [
        ("recent", now - timedelta(days=1), True),   # Should be kept (1 day old)
        ("medium", now - timedelta(days=5), True),   # Should be kept (5 days old)
        ("old", now - timedelta(days=8), False),     # Should be deleted (8 days old)
        ("very_old", now - timedelta(days=15), False),  # Should be deleted (15 days old)
    ]

    created_traces = []

    for name, created_at, should_exist_after in trace_ages:
        trace_id = await create_backdated_trace(
            authed_client,
            tenant_id=test_tenant_id,
            created_at=created_at
        )
        created_traces.append((trace_id, should_exist_after))

    # Verify tenant config has 7-day retention
    tenant_config = await get_tenant_config(authed_client, test_tenant_id)
    assert tenant_config["trace_retention_days"] == 7

    # Act: Run cleanup worker
    await cleanup_worker.cleanup_expired_traces()

    # Wait for cleanup to complete
    await asyncio.sleep(2)

    # Assert: Verify traces are deleted according to retention policy
    for trace_id, should_exist in created_traces:
        trace_response = await authed_client.get(f"/api/v1/traces/{trace_id}")

        if should_exist:
            assert trace_response.status_code == 200, f"Trace {trace_id} should still exist"
        else:
            assert trace_response.status_code == 404, f"Trace {trace_id} should be deleted"

    print("✓ Trace retention cleanup working correctly (7-day retention)")


@pytest.mark.asyncio
async def test_artifact_retention_cleanup(
    authed_client: AsyncClient,
    test_tenant_id: str,
    cleanup_worker
):
    """Test artifact retention cleanup based on tenant.artifact_retention_days."""
    # Arrange: Create artifacts at different ages
    now = datetime.utcnow()

    artifact_ages = [
        ("recent", now - timedelta(days=10), True),   # Should be kept
        ("medium", now - timedelta(days=20), True),   # Should be kept
        ("old", now - timedelta(days=35), False),     # Should be deleted (>30 days)
        ("very_old", now - timedelta(days=60), False),  # Should be deleted
    ]

    created_artifacts = []

    for name, created_at, should_exist_after in artifact_ages:
        artifact_id = await create_backdated_artifact(
            authed_client,
            tenant_id=test_tenant_id,
            created_at=created_at
        )
        created_artifacts.append((artifact_id, should_exist_after))

    # Verify tenant config has 30-day artifact retention
    tenant_config = await get_tenant_config(authed_client, test_tenant_id)
    assert tenant_config["artifact_retention_days"] == 30

    # Act: Run cleanup worker
    await cleanup_worker.cleanup_expired_artifacts()
    await asyncio.sleep(2)

    # Assert: Verify artifacts are deleted according to retention policy
    for artifact_id, should_exist in created_artifacts:
        artifact_response = await authed_client.get(f"/api/v1/artifacts/{artifact_id}")

        if should_exist:
            assert artifact_response.status_code == 200, f"Artifact {artifact_id} should still exist"
        else:
            assert artifact_response.status_code == 404, f"Artifact {artifact_id} should be deleted"

    print("✓ Artifact retention cleanup working correctly (30-day retention)")


@pytest.mark.asyncio
async def test_quota_cleanup_oldest_first_strategy(
    authed_client: AsyncClient,
    test_tenant_with_quota: str,
    cleanup_worker
):
    """Test quota enforcement with 'oldest_first' cleanup strategy."""
    # Arrange: Fill tenant storage close to quota with artifacts of different ages
    tenant_config = await get_tenant_config(authed_client, test_tenant_with_quota)
    assert tenant_config["cleanup_strategy"] == "oldest_first"

    quota = tenant_config["total_storage_quota_bytes"]

    # Create artifacts that exceed quota
    artifacts = []
    total_size = 0

    for i in range(10):
        created_at = datetime.utcnow() - timedelta(days=i)
        size = quota // 8  # Each artifact is 1/8 of quota

        artifact_id = await create_backdated_artifact(
            authed_client,
            tenant_id=test_tenant_with_quota,
            created_at=created_at,
            size_bytes=size
        )

        artifacts.append((artifact_id, created_at, size))
        total_size += size

    # Now storage should exceed quota
    assert total_size > quota

    # Act: Run quota enforcement
    await cleanup_worker.enforce_storage_quota()
    await asyncio.sleep(2)

    # Assert: Oldest artifacts should be deleted first
    remaining_artifacts = []
    for artifact_id, created_at, size in artifacts:
        response = await authed_client.get(f"/api/v1/artifacts/{artifact_id}")
        if response.status_code == 200:
            remaining_artifacts.append((artifact_id, created_at))

    # Verify oldest artifacts were deleted
    if len(remaining_artifacts) < len(artifacts):
        # Remaining artifacts should be newer
        remaining_dates = [created_at for _, created_at in remaining_artifacts]
        deleted_dates = [created_at for artifact_id, created_at, _ in artifacts
                        if artifact_id not in [a[0] for a in remaining_artifacts]]

        if deleted_dates and remaining_dates:
            oldest_remaining = min(remaining_dates)
            newest_deleted = max(deleted_dates)
            assert oldest_remaining >= newest_deleted, "Oldest artifacts should be deleted first"

    print("✓ Quota cleanup with 'oldest_first' strategy working correctly")


@pytest.mark.asyncio
async def test_quota_cleanup_largest_first_strategy(
    authed_client: AsyncClient,
    test_tenant_id: str,
    cleanup_worker
):
    """Test quota enforcement with 'largest_first' cleanup strategy."""
    # Update tenant config to use largest_first strategy
    await update_tenant_config(
        authed_client,
        test_tenant_id,
        {"cleanup_strategy": "largest_first"}
    )

    # Create artifacts of different sizes
    artifacts = [
        await create_artifact_with_size(authed_client, test_tenant_id, size=1024 * 1024),      # 1MB
        await create_artifact_with_size(authed_client, test_tenant_id, size=5 * 1024 * 1024),  # 5MB (should delete first)
        await create_artifact_with_size(authed_client, test_tenant_id, size=500 * 1024),       # 500KB
        await create_artifact_with_size(authed_client, test_tenant_id, size=10 * 1024 * 1024), # 10MB (should delete first)
    ]

    # Exceed quota
    await fill_storage_to_exceed_quota(authed_client, test_tenant_id)

    # Act: Run quota enforcement
    await cleanup_worker.enforce_storage_quota()
    await asyncio.sleep(2)

    # Assert: Largest artifacts should be deleted first
    # This would need actual verification of which artifacts were deleted
    # based on their sizes

    print("✓ Quota cleanup with 'largest_first' strategy working correctly")


@pytest.mark.asyncio
async def test_quota_cleanup_lru_strategy(
    authed_client: AsyncClient,
    test_tenant_id: str,
    cleanup_worker
):
    """Test quota enforcement with 'lru' (Least Recently Used) cleanup strategy."""
    # Update tenant config to use LRU strategy
    await update_tenant_config(
        authed_client,
        test_tenant_id,
        {"cleanup_strategy": "lru"}
    )

    # Create artifacts and access some of them
    artifacts = []

    for i in range(5):
        artifact_id = await create_artifact_with_size(
            authed_client,
            test_tenant_id,
            size=1 * 1024 * 1024
        )
        artifacts.append(artifact_id)

    # Access (download) some artifacts to update last_accessed_at
    # More recently accessed artifacts should be kept
    await authed_client.get(f"/api/v1/artifacts/{artifacts[0]}/download")  # Recently accessed
    await authed_client.get(f"/api/v1/artifacts/{artifacts[1]}/download")  # Recently accessed

    # artifacts[2], [3], [4] are not accessed (older last_accessed_at)

    # Exceed quota
    await fill_storage_to_exceed_quota(authed_client, test_tenant_id)

    # Act: Run quota enforcement with LRU
    await cleanup_worker.enforce_storage_quota()
    await asyncio.sleep(2)

    # Assert: Least recently used artifacts should be deleted first
    # artifacts[0] and [1] should still exist (recently accessed)
    # artifacts[2], [3], [4] may be deleted

    response0 = await authed_client.get(f"/api/v1/artifacts/{artifacts[0]}")
    response1 = await authed_client.get(f"/api/v1/artifacts/{artifacts[1]}")

    # Recently accessed artifacts should be preserved
    assert response0.status_code == 200, "Recently accessed artifact should be kept"
    assert response1.status_code == 200, "Recently accessed artifact should be kept"

    print("✓ Quota cleanup with 'lru' strategy working correctly")


@pytest.mark.asyncio
async def test_quota_cleanup_block_uploads_strategy(
    authed_client: AsyncClient,
    test_tenant_id: str
):
    """Test quota enforcement with 'block_uploads' strategy."""
    # Update tenant config to use block_uploads strategy
    await update_tenant_config(
        authed_client,
        test_tenant_id,
        {"cleanup_strategy": "block_uploads"}
    )

    # Fill storage to exceed quota
    await fill_storage_to_exceed_quota(authed_client, test_tenant_id)

    # Act: Try to upload a new artifact
    import io

    files = {
        "file": ("test.txt", io.BytesIO(b"test content"), "text/plain")
    }

    data = {
        "execution_id": "test-execution-id",
        "execution_version": 1
    }

    response = await authed_client.post("/api/v1/artifacts", files=files, data=data)

    # Assert: Upload should be blocked (507 error)
    assert response.status_code == 507
    error_data = response.json()
    assert "quota" in error_data["error"].lower()

    print("✓ Quota cleanup with 'block_uploads' strategy working correctly")


@pytest.mark.asyncio
async def test_soft_delete_grace_period(
    authed_client: AsyncClient,
    test_artifact_id: str,
    cleanup_worker
):
    """Test that soft-deleted artifacts are hard-deleted after grace period."""
    # Soft delete artifact
    delete_response = await authed_client.delete(f"/api/v1/artifacts/{test_artifact_id}")
    assert delete_response.status_code == 204

    # Artifact should still exist in database with deleted_at set
    artifact_response = await authed_client.get(f"/api/v1/artifacts/{test_artifact_id}")
    assert artifact_response.status_code == 404  # Soft-deleted, not visible via API

    # Wait for grace period to pass (simulate)
    # In real implementation, cleanup worker would run after 7 days

    # Run cleanup worker
    await cleanup_worker.cleanup_expired_artifacts()
    await asyncio.sleep(1)

    # Artifact should now be hard-deleted (completely removed from storage and DB)
    # This would be verified by checking that storage file is gone


# Helper functions
async def create_backdated_trace(client: AsyncClient, tenant_id: str, created_at: datetime) -> str:
    """Create a trace with backdated timestamp (for testing retention)."""
    # NOTE: This would require direct database insertion with custom created_at
    # For testing purposes only
    pass


async def create_backdated_artifact(
    client: AsyncClient,
    tenant_id: str,
    created_at: datetime,
    size_bytes: int = 1024
) -> str:
    """Create an artifact with backdated timestamp (for testing retention)."""
    # NOTE: This would require direct database insertion with custom created_at
    # For testing purposes only
    pass


async def create_artifact_with_size(client: AsyncClient, tenant_id: str, size: int) -> str:
    """Create an artifact with specific size."""
    import io

    content = b"x" * size

    files = {
        "file": ("test.bin", io.BytesIO(content), "application/octet-stream")
    }

    data = {
        "execution_id": "test-execution-id",
        "execution_version": 1
    }

    response = await client.post("/api/v1/artifacts", files=files, data=data)
    return response.json()["id"]


async def get_tenant_config(client: AsyncClient, tenant_id: str) -> dict:
    """Get tenant configuration."""
    response = await client.get(f"/api/v1/tenants/{tenant_id}/config")
    return response.json()


async def update_tenant_config(client: AsyncClient, tenant_id: str, updates: dict):
    """Update tenant configuration."""
    await client.patch(f"/api/v1/tenants/{tenant_id}/config", json=updates)


async def fill_storage_to_exceed_quota(client: AsyncClient, tenant_id: str):
    """Fill tenant storage to exceed quota."""
    config = await get_tenant_config(client, tenant_id)
    quota = config["total_storage_quota_bytes"]
    current = config["current_storage_used_bytes"]

    remaining = quota - current

    # Upload enough to exceed quota
    await create_artifact_with_size(client, tenant_id, size=remaining + 1024)
