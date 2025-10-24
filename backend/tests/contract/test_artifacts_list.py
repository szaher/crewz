"""Contract test for GET /api/v1/artifacts endpoint."""

import pytest
from httpx import AsyncClient
from fastapi import status
from datetime import datetime, timedelta


@pytest.mark.asyncio
async def test_list_artifacts_success(authed_client: AsyncClient):
    """Test successful artifact listing with pagination."""
    response = await authed_client.get(
        "/api/v1/artifacts",
        params={"limit": 50, "offset": 0}
    )

    # Assert status code
    assert response.status_code == status.HTTP_200_OK

    # Assert response schema per artifacts-api.yaml
    data = response.json()
    assert "artifacts" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    assert isinstance(data["artifacts"], list)
    assert isinstance(data["total"], int)
    assert data["limit"] == 50
    assert data["offset"] == 0


@pytest.mark.asyncio
async def test_list_artifacts_with_execution_filter(authed_client: AsyncClient, test_execution_id: str):
    """Test filtering artifacts by execution_id."""
    response = await authed_client.get(
        "/api/v1/artifacts",
        params={"execution_id": test_execution_id}
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # All artifacts should have matching execution_id
    for artifact in data["artifacts"]:
        assert artifact["execution_id"] == test_execution_id


@pytest.mark.asyncio
async def test_list_artifacts_with_execution_version(authed_client: AsyncClient, test_execution_id: str):
    """Test filtering by execution_id and execution_version."""
    response = await authed_client.get(
        "/api/v1/artifacts",
        params={"execution_id": test_execution_id, "execution_version": 1}
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    for artifact in data["artifacts"]:
        assert artifact["execution_id"] == test_execution_id
        assert artifact["execution_version"] == 1


@pytest.mark.asyncio
async def test_list_artifacts_with_type_filter(authed_client: AsyncClient):
    """Test filtering artifacts by artifact_type."""
    for artifact_type in ["document", "image", "data", "code", "other"]:
        response = await authed_client.get(
            "/api/v1/artifacts",
            params={"artifact_type": artifact_type}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # All artifacts should have matching type
        for artifact in data["artifacts"]:
            assert artifact["artifact_type"] == artifact_type


@pytest.mark.asyncio
async def test_list_artifacts_with_search_query(authed_client: AsyncClient):
    """Test full-text search in file names, tags, and descriptions."""
    response = await authed_client.get(
        "/api/v1/artifacts",
        params={"search_query": "report"}
    )

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_list_artifacts_with_tags_filter(authed_client: AsyncClient):
    """Test filtering by tags (OR logic)."""
    response = await authed_client.get(
        "/api/v1/artifacts",
        params={"tags": ["production", "important"]}
    )

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_list_artifacts_with_date_range(authed_client: AsyncClient):
    """Test filtering by date range."""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=7)

    response = await authed_client.get(
        "/api/v1/artifacts",
        params={
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Verify artifacts are within date range
    for artifact in data["artifacts"]:
        artifact_time = datetime.fromisoformat(artifact["created_at"].replace("Z", "+00:00"))
        assert start_date <= artifact_time <= end_date


@pytest.mark.asyncio
async def test_list_artifacts_with_size_range(authed_client: AsyncClient):
    """Test filtering by file size range."""
    response = await authed_client.get(
        "/api/v1/artifacts",
        params={"min_size": 1024, "max_size": 1048576}  # 1KB to 1MB
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # All artifacts should be within size range
    for artifact in data["artifacts"]:
        assert 1024 <= artifact["file_size_bytes"] <= 1048576


@pytest.mark.asyncio
async def test_list_artifacts_sorting(authed_client: AsyncClient):
    """Test sorting by different fields."""
    for sort_by in ["created_at", "file_size", "file_name"]:
        for sort_order in ["asc", "desc"]:
            response = await authed_client.get(
                "/api/v1/artifacts",
                params={"sort_by": sort_by, "sort_order": sort_order}
            )

            assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_list_artifacts_pagination_limits(authed_client: AsyncClient):
    """Test pagination limits enforcement."""
    # Test exceeding max limit
    response = await authed_client.get(
        "/api/v1/artifacts",
        params={"limit": 1000}  # Exceeds max of 500
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_list_artifacts_response_schema(authed_client: AsyncClient):
    """Test that artifact response matches schema from artifacts-api.yaml."""
    response = await authed_client.get("/api/v1/artifacts", params={"limit": 1})

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    if len(data["artifacts"]) > 0:
        artifact = data["artifacts"][0]

        # Required fields per OpenAPI spec
        assert "id" in artifact
        assert "tenant_id" in artifact
        assert "execution_id" in artifact
        assert "execution_version" in artifact
        assert "file_name" in artifact
        assert "file_extension" in artifact
        assert "file_size_bytes" in artifact
        assert "mime_type" in artifact
        assert "storage_path" in artifact
        assert "artifact_type" in artifact
        assert "has_preview" in artifact
        assert "created_at" in artifact

        # Optional fields
        assert "preview_url" in artifact
        assert "last_accessed_at" in artifact
        assert "deleted_at" in artifact

        # Value constraints
        assert artifact["file_size_bytes"] > 0
        assert artifact["execution_version"] >= 1
        assert artifact["artifact_type"] in ["document", "image", "data", "code", "other"]
        assert isinstance(artifact["has_preview"], bool)


@pytest.mark.asyncio
async def test_list_artifacts_exclude_soft_deleted(authed_client: AsyncClient):
    """Test that soft-deleted artifacts are excluded by default."""
    response = await authed_client.get("/api/v1/artifacts")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # No artifact should have deleted_at set
    for artifact in data["artifacts"]:
        assert artifact["deleted_at"] is None


@pytest.mark.asyncio
async def test_list_artifacts_unauthorized(client: AsyncClient):
    """Test that endpoint requires authentication."""
    response = await client.get("/api/v1/artifacts")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
