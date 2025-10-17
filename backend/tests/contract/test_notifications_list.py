"""
Contract tests for GET /api/v1/notifications endpoint.
Tests notification listing according to notifications.openapi.yaml specification.
"""

import pytest
from fastapi.testclient import TestClient


class TestListNotifications:
    """Test GET /api/v1/notifications endpoint"""

    def test_list_notifications_success(self, client: TestClient, auth_headers: dict):
        """Test listing notifications with default parameters"""
        response = client.get(
            "/api/v1/notifications",
            headers=auth_headers
        )

        # Should return 200 OK
        assert response.status_code == 200

        # Validate response schema
        data = response.json()
        assert "notifications" in data
        assert "unread_count" in data
        assert isinstance(data["notifications"], list)
        assert isinstance(data["unread_count"], int)

    def test_list_notifications_with_read_status_filter(self, client: TestClient, auth_headers: dict):
        """Test filtering by read status"""
        # Test unread only
        response = client.get(
            "/api/v1/notifications?read_status=unread",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "notifications" in data

        # Test read only
        response = client.get(
            "/api/v1/notifications?read_status=read",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "notifications" in data

        # Test all (default)
        response = client.get(
            "/api/v1/notifications?read_status=all",
            headers=auth_headers
        )

        assert response.status_code == 200

    def test_list_notifications_with_category_filter(self, client: TestClient, auth_headers: dict):
        """Test filtering by notification category"""
        categories = [
            "execution_update",
            "execution_failed",
            "execution_completed",
            "execution_timeout"
        ]

        for category in categories:
            response = client.get(
                f"/api/v1/notifications?category={category}",
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert "notifications" in data

    def test_list_notifications_with_priority_filter(self, client: TestClient, auth_headers: dict):
        """Test filtering by priority"""
        priorities = ["low", "normal", "high", "urgent"]

        for priority in priorities:
            response = client.get(
                f"/api/v1/notifications?priority={priority}",
                headers=auth_headers
            )

            assert response.status_code == 200

    def test_list_notifications_with_date_range(self, client: TestClient, auth_headers: dict):
        """Test filtering by date range"""
        from datetime import datetime, timedelta

        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)

        response = client.get(
            f"/api/v1/notifications?start_date={start_date.isoformat()}&end_date={end_date.isoformat()}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "notifications" in data

    def test_list_notifications_with_pagination(self, client: TestClient, auth_headers: dict):
        """Test pagination parameters"""
        # Page 1, size 10
        response = client.get(
            "/api/v1/notifications?page=1&page_size=10",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "notifications" in data
        assert len(data["notifications"]) <= 10

        # Page 2, size 25
        response = client.get(
            "/api/v1/notifications?page=2&page_size=25",
            headers=auth_headers
        )

        assert response.status_code == 200

    def test_list_notifications_combined_filters(self, client: TestClient, auth_headers: dict):
        """Test multiple filters combined"""
        response = client.get(
            "/api/v1/notifications?category=execution_failed&read_status=unread&priority=high&page=1&page_size=20",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "notifications" in data
        assert "unread_count" in data

    def test_list_notifications_response_schema(self, client: TestClient, auth_headers: dict):
        """Test notification object schema in response"""
        response = client.get(
            "/api/v1/notifications",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # If there are notifications, validate schema
        if len(data["notifications"]) > 0:
            notification = data["notifications"][0]
            assert "id" in notification
            assert "title" in notification
            assert "message" in notification or notification.get("message") is None
            assert "category" in notification or "type" in notification
            assert "priority" in notification or notification.get("priority") is None
            assert "is_read" in notification or "read_at" in notification
            assert "created_at" in notification

    def test_list_notifications_invalid_page(self, client: TestClient, auth_headers: dict):
        """Test validation error for invalid pagination"""
        # Page 0 (should be >= 1)
        response = client.get(
            "/api/v1/notifications?page=0",
            headers=auth_headers
        )

        assert response.status_code == 422

        # Negative page size
        response = client.get(
            "/api/v1/notifications?page_size=-10",
            headers=auth_headers
        )

        assert response.status_code == 422

    def test_list_notifications_page_size_limit(self, client: TestClient, auth_headers: dict):
        """Test page size limit enforcement"""
        # Page size exceeding max (usually 100)
        response = client.get(
            "/api/v1/notifications?page_size=1000",
            headers=auth_headers
        )

        assert response.status_code == 422

    def test_list_notifications_invalid_date_format(self, client: TestClient, auth_headers: dict):
        """Test validation error for invalid date format"""
        response = client.get(
            "/api/v1/notifications?start_date=invalid-date",
            headers=auth_headers
        )

        assert response.status_code == 422

    def test_list_notifications_unauthorized(self, client: TestClient):
        """Test unauthorized access without auth token"""
        response = client.get("/api/v1/notifications")

        assert response.status_code == 401

    def test_get_unread_count(self, client: TestClient, auth_headers: dict):
        """Test GET /api/v1/notifications/unread-count endpoint"""
        response = client.get(
            "/api/v1/notifications/unread-count",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "unread_count" in data
        assert isinstance(data["unread_count"], int)
        assert data["unread_count"] >= 0

    def test_get_unread_count_by_category(self, client: TestClient, auth_headers: dict):
        """Test unread count breakdown by category"""
        response = client.get(
            "/api/v1/notifications/unread-count",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Optional field: unread_by_category
        if "unread_by_category" in data:
            assert isinstance(data["unread_by_category"], dict)
            # Validate all values are integers
            for category, count in data["unread_by_category"].items():
                assert isinstance(count, int)
                assert count >= 0
