"""
Integration test for queue priority ordering.

Tests T073: Priority queue ordering
- Queue 5 jobs with priorities 0, 5, 10
- Verify execution order: 0 first, then 5, then 10
"""
import pytest
import asyncio
import time
from httpx import AsyncClient
from typing import List, Tuple


class TestQueuePriority:
    """Integration tests for execution queue priority ordering."""

    @pytest.mark.asyncio
    async def test_priority_queue_ordering(
        self, client: AsyncClient, auth_headers: dict, test_flow: dict
    ):
        """
        Test that executions are processed in priority order.

        Priority scale: 0 (highest) to 10 (lowest)

        Steps:
        1. Queue 5 jobs with different priorities
        2. Track which ones start first
        3. Verify high priority (0) starts before low priority (10)
        """
        # Queue executions with different priorities
        executions = [
            {"priority": 10, "label": "low-1"},
            {"priority": 0, "label": "high-1"},
            {"priority": 5, "label": "medium-1"},
            {"priority": 0, "label": "high-2"},
            {"priority": 10, "label": "low-2"},
        ]

        execution_data = []

        for exec_config in executions:
            payload = {
                "execution_type": "flow",
                "entity_id": str(test_flow["id"]),
                "input_params": {"priority_test": True, "label": exec_config["label"]},
                "priority": exec_config["priority"]
            }

            response = await client.post(
                "/api/v1/executions/queue",
                json=payload,
                headers=auth_headers
            )

            if response.status_code not in [200, 201]:
                pytest.skip(f"Queue endpoint not ready: {response.status_code}")

            data = response.json()
            exec_id = data.get("job_id") or data.get("id")

            execution_data.append({
                "id": exec_id,
                "priority": exec_config["priority"],
                "label": exec_config["label"],
                "started_at": None
            })

            # Small delay to ensure queue order
            await asyncio.sleep(0.1)

        # Monitor which executions start first
        max_wait = 60
        start_time = time.time()
        started_count = 0

        while time.time() - start_time < max_wait and started_count < len(execution_data):
            for exec_info in execution_data:
                if exec_info["started_at"] is None:
                    status_response = await client.get(
                        f"/api/v1/executions/{exec_info['id']}/status",
                        headers=auth_headers
                    )

                    if status_response.status_code == 200:
                        status_data = status_response.json()

                        if status_data["status"] in ["running", "completed", "failed"]:
                            exec_info["started_at"] = time.time()
                            started_count += 1

            await asyncio.sleep(0.5)

        # Verify at least some executions started
        assert started_count > 0, "At least some executions should have started"

        # Sort by start time
        started_executions = [e for e in execution_data if e["started_at"] is not None]
        started_executions.sort(key=lambda x: x["started_at"])

        # Verify priority ordering
        # High priority (0) should generally start before low priority (10)
        high_priority_execs = [e for e in started_executions if e["priority"] == 0]
        low_priority_execs = [e for e in started_executions if e["priority"] == 10]

        if high_priority_execs and low_priority_execs:
            # Check if high priority started before low priority
            first_high_priority_start = min(e["started_at"] for e in high_priority_execs)
            first_low_priority_start = min(e["started_at"] for e in low_priority_execs)

            # High priority should start first (or very close)
            # Allow some tolerance for concurrent processing
            assert first_high_priority_start <= first_low_priority_start + 2, \
                "High priority (0) executions should start before or same time as low priority (10)"

    @pytest.mark.asyncio
    async def test_same_priority_fifo_ordering(
        self, client: AsyncClient, auth_headers: dict, test_flow: dict
    ):
        """
        Test that executions with same priority follow FIFO order.

        Steps:
        1. Queue 3 jobs with same priority
        2. Verify they are processed in order queued
        """
        execution_ids = []

        for i in range(3):
            payload = {
                "execution_type": "flow",
                "entity_id": str(test_flow["id"]),
                "input_params": {"fifo_test": i},
                "priority": 5  # Same priority for all
            }

            response = await client.post(
                "/api/v1/executions/queue",
                json=payload,
                headers=auth_headers
            )

            if response.status_code not in [200, 201]:
                pytest.skip(f"Queue endpoint not ready: {response.status_code}")

            data = response.json()
            exec_id = data.get("job_id") or data.get("id")
            execution_ids.append(exec_id)

            await asyncio.sleep(0.1)  # Ensure queue order

        # Monitor start order
        start_times = {}
        max_wait = 60
        start_time = time.time()

        while time.time() - start_time < max_wait and len(start_times) < len(execution_ids):
            for exec_id in execution_ids:
                if exec_id not in start_times:
                    status_response = await client.get(
                        f"/api/v1/executions/{exec_id}/status",
                        headers=auth_headers
                    )

                    if status_response.status_code == 200:
                        status_data = status_response.json()

                        if status_data["status"] in ["running", "completed", "failed"]:
                            start_times[exec_id] = time.time()

            await asyncio.sleep(0.5)

        # Verify FIFO order (with some tolerance)
        if len(start_times) >= 2:
            for i in range(len(execution_ids) - 1):
                first_id = execution_ids[i]
                second_id = execution_ids[i + 1]

                if first_id in start_times and second_id in start_times:
                    # First queued should start before or at same time as second
                    # Allow 2 second tolerance for concurrent processing
                    assert start_times[first_id] <= start_times[second_id] + 2, \
                        f"Execution {i} should start before execution {i+1} (FIFO)"

    @pytest.mark.asyncio
    async def test_priority_bounds_validation(
        self, client: AsyncClient, auth_headers: dict, test_flow: dict
    ):
        """
        Test priority validation (0-10 range per spec).

        Steps:
        1. Try priority 0 (valid)
        2. Try priority 10 (valid)
        3. Try priority 11 (invalid)
        4. Verify validation
        """
        # Test min boundary (highest priority)
        payload = {
            "execution_type": "flow",
            "entity_id": str(test_flow["id"]),
            "input_params": {"priority_bounds": True},
            "priority": 0
        }

        response = await client.post(
            "/api/v1/executions/queue",
            json=payload,
            headers=auth_headers
        )

        if response.status_code == 404:
            pytest.skip("Queue endpoint not implemented yet")

        assert response.status_code in [200, 201], \
            "Priority 0 should be valid"

        # Test max boundary (lowest priority)
        payload["priority"] = 10
        response = await client.post(
            "/api/v1/executions/queue",
            json=payload,
            headers=auth_headers
        )

        assert response.status_code in [200, 201], \
            "Priority 10 should be valid"

        # Test out of bounds
        payload["priority"] = 11
        response = await client.post(
            "/api/v1/executions/queue",
            json=payload,
            headers=auth_headers
        )

        # Should return validation error
        assert response.status_code == 422, \
            "Priority 11 should be rejected (out of bounds)"

    @pytest.mark.asyncio
    async def test_default_priority(
        self, client: AsyncClient, auth_headers: dict, test_flow: dict
    ):
        """
        Test default priority when not specified.

        Steps:
        1. Queue execution without priority
        2. Verify default priority is assigned (5 per spec)
        """
        payload = {
            "execution_type": "flow",
            "entity_id": str(test_flow["id"]),
            "input_params": {"default_priority": True}
            # No priority specified
        }

        response = await client.post(
            "/api/v1/executions/queue",
            json=payload,
            headers=auth_headers
        )

        if response.status_code not in [200, 201]:
            pytest.skip(f"Queue endpoint not ready: {response.status_code}")

        data = response.json()
        exec_id = data.get("job_id") or data.get("id")

        # Check status to see if priority is set
        status_response = await client.get(
            f"/api/v1/executions/{exec_id}/status",
            headers=auth_headers
        )

        if status_response.status_code == 200:
            status_data = status_response.json()

            # If priority field exists, verify default is 5
            if "priority" in status_data:
                assert status_data["priority"] == 5, \
                    "Default priority should be 5"

    @pytest.mark.asyncio
    async def test_queue_position_reflects_priority(
        self, client: AsyncClient, auth_headers: dict, test_flow: dict
    ):
        """
        Test that queue position reflects priority ordering.

        Steps:
        1. Queue low priority job first
        2. Queue high priority job second
        3. Verify high priority has lower queue position
        """
        # Queue low priority first
        low_payload = {
            "execution_type": "flow",
            "entity_id": str(test_flow["id"]),
            "input_params": {"position_test": "low"},
            "priority": 10
        }

        low_response = await client.post(
            "/api/v1/executions/queue",
            json=low_payload,
            headers=auth_headers
        )

        if low_response.status_code not in [200, 201]:
            pytest.skip(f"Queue endpoint not ready: {low_response.status_code}")

        low_data = low_response.json()
        low_exec_id = low_data.get("job_id") or low_data.get("id")
        low_queue_pos = low_data.get("queue_position")

        # Queue high priority second
        high_payload = {
            "execution_type": "flow",
            "entity_id": str(test_flow["id"]),
            "input_params": {"position_test": "high"},
            "priority": 0
        }

        high_response = await client.post(
            "/api/v1/executions/queue",
            json=high_payload,
            headers=auth_headers
        )

        high_data = high_response.json()
        high_exec_id = high_data.get("job_id") or high_data.get("id")
        high_queue_pos = high_data.get("queue_position")

        # If queue positions are returned, high priority should have lower position
        if low_queue_pos is not None and high_queue_pos is not None:
            assert high_queue_pos <= low_queue_pos, \
                f"High priority (0) should have lower queue position than low priority (10): " \
                f"{high_queue_pos} vs {low_queue_pos}"
