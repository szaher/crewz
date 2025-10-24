"""Contract test for POST /api/v1/traces/export endpoint."""

import pytest
from httpx import AsyncClient
from fastapi import status
from datetime import datetime, timedelta


@pytest.mark.asyncio
async def test_export_traces_json_format(authed_client: AsyncClient):
    """Test successful trace export in JSON format."""
    payload = {
        "format": "json",
        "filters": {}
    }

    response = await authed_client.post("/api/v1/traces/export", json=payload)

    # Assert status code
    assert response.status_code == status.HTTP_200_OK

    # Assert response schema per traces-api.yaml
    data = response.json()
    assert "download_url" in data
    assert "expires_at" in data

    # Validate download_url is a valid URL
    assert data["download_url"].startswith("http")

    # Validate expires_at is a valid timestamp
    expires_at = datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00"))
    assert expires_at > datetime.utcnow()


@pytest.mark.asyncio
async def test_export_traces_csv_format(authed_client: AsyncClient):
    """Test successful trace export in CSV format."""
    payload = {
        "format": "csv",
        "filters": {}
    }

    response = await authed_client.post("/api/v1/traces/export", json=payload)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert "download_url" in data
    assert "expires_at" in data


@pytest.mark.asyncio
async def test_export_traces_with_filters(authed_client: AsyncClient, test_execution_id: str):
    """Test trace export with filtering."""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=7)

    payload = {
        "format": "json",
        "filters": {
            "execution_id": test_execution_id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "provider": "openai",
            "min_cost": 0.001,
            "max_cost": 1.0
        }
    }

    response = await authed_client.post("/api/v1/traces/export", json=payload)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert "download_url" in data
    assert "expires_at" in data


@pytest.mark.asyncio
async def test_export_traces_error_filter(authed_client: AsyncClient):
    """Test export with error filtering."""
    payload = {
        "format": "json",
        "filters": {
            "has_error": True
        }
    }

    response = await authed_client.post("/api/v1/traces/export", json=payload)

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_export_traces_invalid_format(authed_client: AsyncClient):
    """Test 400 response for invalid export format."""
    payload = {
        "format": "xml",  # Not supported
        "filters": {}
    }

    response = await authed_client.post("/api/v1/traces/export", json=payload)

    assert response.status_code == status.HTTP_400_BAD_REQUEST

    error = response.json()
    assert "error" in error


@pytest.mark.asyncio
async def test_export_traces_missing_format(authed_client: AsyncClient):
    """Test 400 response when format is missing."""
    payload = {
        "filters": {}
    }

    response = await authed_client.post("/api/v1/traces/export", json=payload)

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_export_traces_invalid_date_range(authed_client: AsyncClient):
    """Test 400 response when end_date is before start_date."""
    end_date = datetime.utcnow()
    start_date = end_date + timedelta(days=7)  # Start after end

    payload = {
        "format": "json",
        "filters": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }
    }

    response = await authed_client.post("/api/v1/traces/export", json=payload)

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_export_traces_presigned_url_expiration(authed_client: AsyncClient):
    """Test that pre-signed URL has reasonable expiration time."""
    payload = {
        "format": "json",
        "filters": {}
    }

    response = await authed_client.post("/api/v1/traces/export", json=payload)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    expires_at = datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00"))
    now = datetime.utcnow()

    # URL should expire within 1 hour (default per storage.py config)
    time_diff = (expires_at - now).total_seconds()
    assert 0 < time_diff <= 3600  # 1 hour in seconds


@pytest.mark.asyncio
async def test_export_traces_unauthorized(client: AsyncClient):
    """Test that endpoint requires authentication."""
    payload = {
        "format": "json",
        "filters": {}
    }

    response = await client.post("/api/v1/traces/export", json=payload)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
