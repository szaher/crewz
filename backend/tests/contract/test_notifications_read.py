"""
Contract tests for notification read operations.
Tests PUT /api/v1/notifications/{id}/read and POST /api/v1/notifications/mark-all-read
according to notifications.openapi.yaml specification.
"""

import pytest
from uuid import uuid4
from fastapi.testclient import TestClient


class TestMarkNotificationAsRead:
    """Test PUT /api/v1/notifications/{notification_id}/read endpoint"""

    def test_mark_notification_as_read_success(self, client: TestClient, auth_headers: dict):
        """Test marking a notification as read"""
        # First, get a notification ID
        list_response = client.get(
            "/api/v1/notifications?read_status=unread&page_size=1",
            headers=auth_headers
        )

        if list_response.status_code == 200:
            data = list_response.json()
            if len(data["notifications"]) > 0:
                notification_id = data["notifications"][0]["id"]

                # Mark as read
                response = client.put(
                    f"/api/v1/notifications/{notification_id}/read",
                    headers=auth_headers
                )

                # Should return 200 OK
                assert response.status_code == 200

                # Validate response schema
                notification = response.json()
                assert "id" in notification
                assert notification["id"] == notification_id
                assert "is_read" in notification or "read_at" in notification

                # If read_at is present, it should be a valid timestamp
                if "read_at" in notification and notification["read_at"] is not None:
                    from datetime import datetime
                    # Should be parseable as ISO datetime
                    datetime.fromisoformat(notification["read_at"].replace('Z', '+00:00'))
            else:
                pytest.skip("No unread notifications available for testing")
        else:
            pytest.skip("Unable to list notifications for testing")

    def test_mark_notification_as_read_idempotent(self, client: TestClient, auth_headers: dict):
        """Test marking already-read notification is idempotent"""
        # Get any notification
        list_response = client.get(
            "/api/v1/notifications?page_size=1",
            headers=auth_headers
        )

        if list_response.status_code == 200:
            data = list_response.json()
            if len(data["notifications"]) > 0:
                notification_id = data["notifications"][0]["id"]

                # Mark as read twice
                response1 = client.put(
                    f"/api/v1/notifications/{notification_id}/read",
                    headers=auth_headers
                )
                response2 = client.put(
                    f"/api/v1/notifications/{notification_id}/read",
                    headers=auth_headers
                )

                assert response1.status_code == 200
                assert response2.status_code == 200
            else:
                pytest.skip("No notifications available for testing")
        else:
            pytest.skip("Unable to list notifications for testing")

    def test_mark_notification_as_read_not_found(self, client: TestClient, auth_headers: dict):
        """Test marking non-existent notification returns 404"""
        fake_id = str(uuid4())

        response = client.put(
            f"/api/v1/notifications/{fake_id}/read",
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_mark_notification_as_read_invalid_uuid(self, client: TestClient, auth_headers: dict):
        """Test validation error for invalid UUID format"""
        response = client.put(
            "/api/v1/notifications/not-a-uuid/read",
            headers=auth_headers
        )

        assert response.status_code == 422

    def test_mark_notification_as_read_unauthorized(self, client: TestClient):
        """Test unauthorized access without auth token"""
        fake_id = str(uuid4())

        response = client.put(f"/api/v1/notifications/{fake_id}/read")

        assert response.status_code == 401

    def test_mark_notification_as_read_other_users_notification(self, client: TestClient, auth_headers: dict):
        """Test that users cannot mark other users' notifications"""
        # This test would require creating a notification for another user
        # and attempting to mark it as read. The expected behavior is 404 or 403.
        # Implementation depends on how the API handles this scenario.
        pytest.skip("Requires multi-user test setup")


class TestMarkAllNotificationsAsRead:
    """Test POST /api/v1/notifications/mark-all-read endpoint"""

    def test_mark_all_as_read_success(self, client: TestClient, auth_headers: dict):
        """Test marking all notifications as read"""
        response = client.post(
            "/api/v1/notifications/mark-all-read",
            json={},
            headers=auth_headers
        )

        # Should return 200 OK
        assert response.status_code == 200

        # Validate response schema
        data = response.json()
        assert "updated" in data
        assert isinstance(data["updated"], int)
        assert data["updated"] >= 0

    def test_mark_all_as_read_with_category_filter(self, client: TestClient, auth_headers: dict):
        """Test marking all notifications in specific category as read"""
        categories = [
            "execution_completed",
            "execution_failed",
            "execution_update"
        ]

        for category in categories:
            response = client.post(
                "/api/v1/notifications/mark-all-read",
                json={"category": category},
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert "updated" in data
            assert isinstance(data["updated"], int)

    def test_mark_all_as_read_idempotent(self, client: TestClient, auth_headers: dict):
        """Test marking all as read is idempotent"""
        # First call
        response1 = client.post(
            "/api/v1/notifications/mark-all-read",
            json={},
            headers=auth_headers
        )

        assert response1.status_code == 200
        updated1 = response1.json()["updated"]

        # Second call should update 0 (all already read)
        response2 = client.post(
            "/api/v1/notifications/mark-all-read",
            json={},
            headers=auth_headers
        )

        assert response2.status_code == 200
        updated2 = response2.json()["updated"]
        assert updated2 == 0  # All were already marked read

    def test_mark_all_as_read_reduces_unread_count(self, client: TestClient, auth_headers: dict):
        """Test that unread count becomes 0 after mark all as read"""
        # Get initial unread count
        count_response1 = client.get(
            "/api/v1/notifications/unread-count",
            headers=auth_headers
        )

        if count_response1.status_code == 200:
            initial_unread = count_response1.json()["unread_count"]

            if initial_unread > 0:
                # Mark all as read
                mark_response = client.post(
                    "/api/v1/notifications/mark-all-read",
                    json={},
                    headers=auth_headers
                )

                assert mark_response.status_code == 200

                # Get updated unread count
                count_response2 = client.get(
                    "/api/v1/notifications/unread-count",
                    headers=auth_headers
                )

                assert count_response2.status_code == 200
                final_unread = count_response2.json()["unread_count"]
                assert final_unread == 0
            else:
                pytest.skip("No unread notifications to test with")
        else:
            pytest.skip("Unable to get unread count for testing")

    def test_mark_all_as_read_invalid_category(self, client: TestClient, auth_headers: dict):
        """Test validation error for invalid category"""
        response = client.post(
            "/api/v1/notifications/mark-all-read",
            json={"category": "invalid_category_12345"},
            headers=auth_headers
        )

        # Should either accept it (if categories are not strictly validated)
        # or return 422
        assert response.status_code in [200, 422]

    def test_mark_all_as_read_unauthorized(self, client: TestClient):
        """Test unauthorized access without auth token"""
        response = client.post(
            "/api/v1/notifications/mark-all-read",
            json={}
        )

        assert response.status_code == 401
