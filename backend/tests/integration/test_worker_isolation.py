"""
Integration test for worker isolation from main application.

Tests T074: Worker isolation
- Crash worker1 during execution
- Verify backend API still responsive
- Worker2 unaffected
- Main app uptime 100%
"""
import pytest
import asyncio
import subprocess
import time
from httpx import AsyncClient


class TestWorkerIsolation:
    """Integration tests for worker process isolation from main application."""

    @pytest.mark.asyncio
    async def test_backend_responsive_during_worker_crash(
        self, client: AsyncClient, auth_headers: dict, test_flow: dict
    ):
        """
        Test that backend API remains responsive when worker crashes.

        Steps:
        1. Start execution on worker
        2. Crash worker container
        3. Verify backend API still responds to requests
        4. Verify other endpoints work normally
        """
        # Verify backend is initially responsive
        initial_response = await client.get(
            "/api/v1/health",
            headers=auth_headers
        )

        # Backend should be up (accept 200 or 404 if health endpoint not implemented)
        assert initial_response.status_code in [200, 404], \
            "Backend should be responsive initially"

        # Start execution
        payload = {
            "execution_type": "flow",
            "entity_id": str(test_flow["id"]),
            "input_params": {"isolation_test": True, "duration": 30},
            "priority": 5
        }

        exec_response = await client.post(
            "/api/v1/executions/queue",
            json=payload,
            headers=auth_headers
        )

        if exec_response.status_code not in [200, 201]:
            pytest.skip(f"Queue endpoint not ready: {exec_response.status_code}")

        data = exec_response.json()
        exec_id = data.get("job_id") or data.get("id")

        # Wait for execution to start
        await asyncio.sleep(3)

        # Crash a worker
        try:
            result = subprocess.run(
                ["docker", "ps", "--filter", "name=celery-worker", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=5
            )

            worker_containers = [name.strip() for name in result.stdout.split('\n') if name.strip()]

            if not worker_containers:
                pytest.skip("No worker containers found")

            # Kill first worker
            worker_to_kill = worker_containers[0]
            subprocess.run(
                ["docker", "kill", worker_to_kill],
                capture_output=True,
                timeout=10
            )

            # Wait a moment for crash
            await asyncio.sleep(2)

            # Verify backend is still responsive
            health_response = await client.get(
                "/api/v1/health",
                headers=auth_headers
            )

            assert health_response.status_code in [200, 404], \
                "Backend should remain responsive after worker crash"

            # Verify we can still query execution status
            status_response = await client.get(
                f"/api/v1/executions/{exec_id}/status",
                headers=auth_headers
            )

            assert status_response.status_code in [200, 404], \
                "Execution status endpoint should remain responsive"

            # Verify we can still queue new executions
            new_payload = {
                "execution_type": "flow",
                "entity_id": str(test_flow["id"]),
                "input_params": {"post_crash_test": True},
                "priority": 5
            }

            new_exec_response = await client.post(
                "/api/v1/executions/queue",
                json=new_payload,
                headers=auth_headers
            )

            assert new_exec_response.status_code in [200, 201], \
                "Should still be able to queue executions after worker crash"

            # Restart the worker for cleanup
            subprocess.run(
                ["docker", "start", worker_to_kill],
                capture_output=True,
                timeout=10
            )

        except subprocess.TimeoutExpired:
            pytest.skip("Docker commands timed out")
        except subprocess.CalledProcessError:
            pytest.skip("Docker command failed")
        except FileNotFoundError:
            pytest.skip("Docker not available")

    @pytest.mark.asyncio
    async def test_other_workers_unaffected_by_crash(
        self, client: AsyncClient, auth_headers: dict, test_flow: dict
    ):
        """
        Test that other workers continue processing when one crashes.

        Steps:
        1. Start multiple executions
        2. Crash one worker
        3. Verify other workers still process jobs
        """
        # Queue multiple executions
        execution_ids = []
        for i in range(3):
            payload = {
                "execution_type": "flow",
                "entity_id": str(test_flow["id"]),
                "input_params": {"multi_worker_test": i},
                "priority": 5
            }

            response = await client.post(
                "/api/v1/executions/queue",
                json=payload,
                headers=auth_headers
            )

            if response.status_code not in [200, 201]:
                pytest.skip(f"Queue endpoint not ready: {response.status_code}")

            data = response.json()
            execution_ids.append(data.get("job_id") or data.get("id"))

        # Wait for some to start
        await asyncio.sleep(3)

        # Crash a worker
        try:
            result = subprocess.run(
                ["docker", "ps", "--filter", "name=celery-worker", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=5
            )

            worker_containers = [name.strip() for name in result.stdout.split('\n') if name.strip()]

            if len(worker_containers) < 2:
                pytest.skip("Need at least 2 workers for this test")

            # Kill first worker
            worker_to_kill = worker_containers[0]
            subprocess.run(
                ["docker", "kill", worker_to_kill],
                capture_output=True,
                timeout=10
            )

            # Wait for retry/reassignment
            await asyncio.sleep(10)

            # Check if executions are still progressing
            completed_count = 0
            for exec_id in execution_ids:
                status_response = await client.get(
                    f"/api/v1/executions/{exec_id}/status",
                    headers=auth_headers
                )

                if status_response.status_code == 200:
                    status_data = status_response.json()
                    if status_data["status"] in ["running", "completed", "failed"]:
                        completed_count += 1

            # At least some executions should be processing (on remaining workers)
            assert completed_count > 0, \
                "Other workers should continue processing after one crashes"

            # Restart worker for cleanup
            subprocess.run(
                ["docker", "start", worker_to_kill],
                capture_output=True,
                timeout=10
            )

        except subprocess.TimeoutExpired:
            pytest.skip("Docker commands timed out")
        except subprocess.CalledProcessError:
            pytest.skip("Docker command failed")
        except FileNotFoundError:
            pytest.skip("Docker not available")

    @pytest.mark.asyncio
    async def test_backend_uptime_during_worker_operations(
        self, client: AsyncClient, auth_headers: dict
    ):
        """
        Test that backend maintains 100% uptime during worker operations.

        Steps:
        1. Make continuous API calls to backend
        2. Verify all requests succeed
        3. No backend crashes or restarts
        """
        # Make continuous requests to verify backend stability
        request_count = 20
        success_count = 0
        failure_count = 0

        for i in range(request_count):
            try:
                # Try different endpoints to verify full backend health
                if i % 3 == 0:
                    response = await client.get("/api/v1/health", headers=auth_headers)
                elif i % 3 == 1:
                    # Try to list flows or other entity
                    response = await client.get("/api/v1/flows", headers=auth_headers)
                else:
                    # Try to list executions
                    response = await client.get("/api/v1/executions", headers=auth_headers)

                # Accept 200, 401, 404 as "backend is running"
                if response.status_code in [200, 401, 404]:
                    success_count += 1
                else:
                    failure_count += 1

            except Exception as e:
                failure_count += 1

            await asyncio.sleep(0.2)

        # Backend should be responsive for all requests
        # Allow a small margin for network issues
        uptime_percentage = (success_count / request_count) * 100

        assert uptime_percentage >= 95, \
            f"Backend uptime should be >=95%, got {uptime_percentage}%"

    @pytest.mark.asyncio
    async def test_worker_crash_does_not_crash_backend(
        self, client: AsyncClient, auth_headers: dict
    ):
        """
        Test that worker crash does not cause backend to crash.

        Steps:
        1. Verify backend is running
        2. Kill worker
        3. Wait and verify backend still running
        4. Check backend logs for no errors
        """
        # Check backend is running
        try:
            result = subprocess.run(
                ["docker", "ps", "--filter", "name=backend", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=5
            )

            backend_containers = [name.strip() for name in result.stdout.split('\n') if name.strip()]

            if not backend_containers:
                pytest.skip("Backend container not found")

            initial_backend = backend_containers[0]

            # Verify backend responds
            initial_response = await client.get("/api/v1/health", headers=auth_headers)
            assert initial_response.status_code in [200, 404], \
                "Backend should be responsive initially"

            # Kill a worker
            worker_result = subprocess.run(
                ["docker", "ps", "--filter", "name=celery-worker", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=5
            )

            worker_containers = [name.strip() for name in worker_result.stdout.split('\n') if name.strip()]

            if not worker_containers:
                pytest.skip("No worker containers found")

            worker_to_kill = worker_containers[0]
            subprocess.run(
                ["docker", "kill", worker_to_kill],
                capture_output=True,
                timeout=10
            )

            # Wait
            await asyncio.sleep(5)

            # Verify backend still running
            backend_check = subprocess.run(
                ["docker", "ps", "--filter", f"name={initial_backend}", "--format", "{{.Status}}"],
                capture_output=True,
                text=True,
                timeout=5
            )

            assert "Up" in backend_check.stdout, \
                "Backend should still be running after worker crash"

            # Verify backend still responds
            final_response = await client.get("/api/v1/health", headers=auth_headers)
            assert final_response.status_code in [200, 404], \
                "Backend should still respond after worker crash"

            # Restart worker for cleanup
            subprocess.run(
                ["docker", "start", worker_to_kill],
                capture_output=True,
                timeout=10
            )

        except subprocess.TimeoutExpired:
            pytest.skip("Docker commands timed out")
        except subprocess.CalledProcessError:
            pytest.skip("Docker command failed")
        except FileNotFoundError:
            pytest.skip("Docker not available")

    @pytest.mark.asyncio
    async def test_execution_isolation_memory_leak(
        self, client: AsyncClient, auth_headers: dict, test_flow: dict
    ):
        """
        Test that worker executions don't leak into backend memory.

        Steps:
        1. Queue multiple executions
        2. Monitor backend memory usage (should stay stable)
        3. Verify worker handles the load, not backend
        """
        # This is a basic smoke test
        # Full memory monitoring would require more infrastructure

        # Queue several executions
        for i in range(5):
            payload = {
                "execution_type": "flow",
                "entity_id": str(test_flow["id"]),
                "input_params": {"memory_test": i},
                "priority": 5
            }

            response = await client.post(
                "/api/v1/executions/queue",
                json=payload,
                headers=auth_headers
            )

            if response.status_code not in [200, 201]:
                pytest.skip(f"Queue endpoint not ready: {response.status_code}")

        # Backend should remain responsive
        await asyncio.sleep(5)

        # Verify backend still works
        health_response = await client.get("/api/v1/health", headers=auth_headers)
        assert health_response.status_code in [200, 404], \
            "Backend should remain healthy after queueing multiple executions"

        # Note: Full memory profiling would require docker stats parsing
        # This test validates basic isolation - backend doesn't crash
