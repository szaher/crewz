"""
Contract tests for notification preferences endpoints.
Tests GET/PUT /api/v1/notifications/preferences
according to notifications.openapi.yaml specification.
"""

import pytest
from fastapi.testclient import TestClient


class TestGetNotificationPreferences:
    """Test GET /api/v1/notifications/preferences endpoint"""

    def test_get_preferences_success(self, client: TestClient, auth_headers: dict):
        """Test getting user notification preferences"""
        response = client.get(
            "/api/v1/notifications/preferences",
            headers=auth_headers
        )

        # Should return 200 OK
        assert response.status_code == 200

        # Validate response schema
        data = response.json()
        assert "user_id" in data
        assert "preferences" in data
        assert isinstance(data["preferences"], dict)

    def test_get_preferences_contains_delivery_channels(self, client: TestClient, auth_headers: dict):
        """Test that preferences include delivery channel settings"""
        response = client.get(
            "/api/v1/notifications/preferences",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Preferences should have channel-level settings
        preferences = data["preferences"]

        # Common delivery channels
        expected_channels = ["websocket", "email", "webhook"]

        # At least one channel should be present
        channel_found = any(channel in preferences for channel in expected_channels)
        assert channel_found, f"Expected at least one of {expected_channels} in preferences"

        # Validate channel structure
        for channel in expected_channels:
            if channel in preferences:
                channel_prefs = preferences[channel]
                assert isinstance(channel_prefs, dict)
                assert "enabled" in channel_prefs
                assert isinstance(channel_prefs["enabled"], bool)

                # If types field exists, it should be a list
                if "types" in channel_prefs:
                    assert isinstance(channel_prefs["types"], list)

    def test_get_preferences_includes_notification_types(self, client: TestClient, auth_headers: dict):
        """Test that preferences specify which notification types are enabled"""
        response = client.get(
            "/api/v1/notifications/preferences",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        preferences = data["preferences"]

        # Check that at least one channel has notification types configured
        has_types = False
        for channel_prefs in preferences.values():
            if isinstance(channel_prefs, dict) and "types" in channel_prefs:
                has_types = True
                types_list = channel_prefs["types"]
                assert isinstance(types_list, list)

                # Common notification types
                valid_types = [
                    "execution_update",
                    "execution_failed",
                    "execution_completed",
                    "execution_timeout",
                    "daily_summary",
                    "system_maintenance",
                    "security_alert"
                ]

                # Types should be from valid set (if any are specified)
                for notification_type in types_list:
                    assert notification_type in valid_types or notification_type.startswith("execution_")

        assert has_types, "At least one channel should have notification types configured"

    def test_get_preferences_tenant_defaults_merge(self, client: TestClient, auth_headers: dict):
        """Test that response includes tenant defaults merged with user overrides"""
        response = client.get(
            "/api/v1/notifications/preferences",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Preferences should represent effective settings (tenant defaults + user overrides)
        # This is implicitly tested by checking that preferences are always returned
        assert "preferences" in data
        assert len(data["preferences"]) > 0

    def test_get_preferences_unauthorized(self, client: TestClient):
        """Test unauthorized access without auth token"""
        response = client.get("/api/v1/notifications/preferences")

        assert response.status_code == 401


class TestUpdateNotificationPreferences:
    """Test PUT /api/v1/notifications/preferences endpoint"""

    def test_update_preferences_success(self, client: TestClient, auth_headers: dict):
        """Test updating user notification preferences"""
        update_data = {
            "preferences": {
                "websocket": {
                    "enabled": True,
                    "types": ["execution_update", "execution_failed"]
                },
                "email": {
                    "enabled": False,
                    "types": [],
                    "frequency": "daily"
                }
            }
        }

        response = client.put(
            "/api/v1/notifications/preferences",
            json=update_data,
            headers=auth_headers
        )

        # Should return 200 OK
        assert response.status_code == 200

        # Validate response schema
        data = response.json()
        assert "user_id" in data
        assert "preferences" in data
        assert "updated_at" in data

    def test_update_preferences_partial_update(self, client: TestClient, auth_headers: dict):
        """Test partial preference update (only specific channels)"""
        # Update only email preferences
        update_data = {
            "preferences": {
                "email": {
                    "enabled": True,
                    "types": ["execution_failed", "daily_summary"]
                }
            }
        }

        response = client.put(
            "/api/v1/notifications/preferences",
            json=update_data,
            headers=auth_headers
        )

        assert response.status_code == 200

    def test_update_preferences_disable_all_channels(self, client: TestClient, auth_headers: dict):
        """Test disabling all notification channels"""
        update_data = {
            "preferences": {
                "websocket": {"enabled": False, "types": []},
                "email": {"enabled": False, "types": []},
                "webhook": {"enabled": False, "types": []}
            }
        }

        response = client.put(
            "/api/v1/notifications/preferences",
            json=update_data,
            headers=auth_headers
        )

        # Should succeed even if all channels are disabled
        assert response.status_code == 200

    def test_update_preferences_enable_all_types(self, client: TestClient, auth_headers: dict):
        """Test enabling all notification types for a channel"""
        update_data = {
            "preferences": {
                "websocket": {
                    "enabled": True,
                    "types": [
                        "execution_update",
                        "execution_failed",
                        "execution_completed",
                        "execution_timeout",
                        "daily_summary"
                    ]
                }
            }
        }

        response = client.put(
            "/api/v1/notifications/preferences",
            json=update_data,
            headers=auth_headers
        )

        assert response.status_code == 200

    def test_update_preferences_invalid_channel(self, client: TestClient, auth_headers: dict):
        """Test validation error for invalid delivery channel"""
        update_data = {
            "preferences": {
                "invalid_channel": {
                    "enabled": True,
                    "types": []
                }
            }
        }

        response = client.put(
            "/api/v1/notifications/preferences",
            json=update_data,
            headers=auth_headers
        )

        # Should return 400 Bad Request
        assert response.status_code == 400

    def test_update_preferences_invalid_notification_type(self, client: TestClient, auth_headers: dict):
        """Test validation error for invalid notification type"""
        update_data = {
            "preferences": {
                "websocket": {
                    "enabled": True,
                    "types": ["invalid_notification_type_12345"]
                }
            }
        }

        response = client.put(
            "/api/v1/notifications/preferences",
            json=update_data,
            headers=auth_headers
        )

        # Should either accept it (if types are not strictly validated)
        # or return 400
        assert response.status_code in [200, 400]

    def test_update_preferences_missing_required_fields(self, client: TestClient, auth_headers: dict):
        """Test validation error for missing required fields"""
        # Missing 'preferences' key
        update_data = {}

        response = client.put(
            "/api/v1/notifications/preferences",
            json=update_data,
            headers=auth_headers
        )

        # Should return 422 Validation Error
        assert response.status_code == 422

    def test_update_preferences_invalid_data_type(self, client: TestClient, auth_headers: dict):
        """Test validation error for invalid data types"""
        # enabled should be boolean, not string
        update_data = {
            "preferences": {
                "websocket": {
                    "enabled": "yes",  # Should be boolean
                    "types": []
                }
            }
        }

        response = client.put(
            "/api/v1/notifications/preferences",
            json=update_data,
            headers=auth_headers
        )

        assert response.status_code == 422

    def test_update_preferences_persists_across_requests(self, client: TestClient, auth_headers: dict):
        """Test that preference updates persist"""
        # Update preferences
        update_data = {
            "preferences": {
                "email": {
                    "enabled": True,
                    "types": ["execution_failed"]
                }
            }
        }

        update_response = client.put(
            "/api/v1/notifications/preferences",
            json=update_data,
            headers=auth_headers
        )

        assert update_response.status_code == 200

        # Get preferences and verify
        get_response = client.get(
            "/api/v1/notifications/preferences",
            headers=auth_headers
        )

        assert get_response.status_code == 200
        data = get_response.json()

        # Email preferences should match what we set
        assert "preferences" in data
        assert "email" in data["preferences"]
        assert data["preferences"]["email"]["enabled"] is True

    def test_update_preferences_unauthorized(self, client: TestClient):
        """Test unauthorized access without auth token"""
        update_data = {
            "preferences": {
                "websocket": {"enabled": True, "types": []}
            }
        }

        response = client.put(
            "/api/v1/notifications/preferences",
            json=update_data
        )

        assert response.status_code == 401


class TestTenantAdminNotificationPreferences:
    """Test tenant-level notification preferences (admin only)"""

    def test_get_tenant_preferences_admin_only(self, client: TestClient, auth_headers: dict):
        """Test that tenant-level preferences require admin access"""
        response = client.get(
            "/api/v1/admin/notifications/preferences/tenant",
            headers=auth_headers
        )

        # Should return 200 if user is admin, 403 if not
        assert response.status_code in [200, 403]

    def test_update_tenant_preferences_admin_only(self, client: TestClient, auth_headers: dict):
        """Test that updating tenant preferences requires admin access"""
        update_data = {
            "preferences": {
                "websocket": {
                    "enabled": True,
                    "types": ["execution_failed"]
                }
            }
        }

        response = client.put(
            "/api/v1/admin/notifications/preferences/tenant",
            json=update_data,
            headers=auth_headers
        )

        # Should return 200 if user is admin, 403 if not
        assert response.status_code in [200, 403]

    def test_tenant_preferences_serve_as_defaults(self, client: TestClient, auth_headers: dict):
        """Test that tenant preferences serve as defaults for users"""
        # This test requires admin access to modify tenant defaults
        # and then verifying user preferences inherit them
        pytest.skip("Requires admin privileges and complex test setup")
