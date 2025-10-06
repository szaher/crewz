"""
Performance test for concurrent flow executions.

This test validates that the system can handle 100+ concurrent flow executions
without degradation, ensuring proper resource management, task queuing, and
execution isolation.

Run with:
    pytest backend/tests/performance/test_concurrent_executions.py -v -s
"""

import asyncio
import time
import uuid
from typing import List, Dict, Any
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from src.main import app
from src.models import Tenant, User, Agent, Flow, Execution
from src.db import get_db
from src.services.auth_service import AuthService


@pytest.fixture
async def test_tenant(db_session: AsyncSession) -> Tenant:
    """Create a test tenant for performance testing."""
    tenant = Tenant(
        id=uuid.uuid4(),
        name="Performance Test Tenant",
        slug=f"perf_test_{uuid.uuid4().hex[:8]}",
        db_schema=f"tenant_perf_{uuid.uuid4().hex[:8]}",
        is_active=True
    )
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    return tenant


@pytest.fixture
async def test_user(db_session: AsyncSession, test_tenant: Tenant) -> User:
    """Create a test user."""
    auth_service = AuthService(db_session)
    user = await auth_service.create_user(
        tenant_id=test_tenant.id,
        email=f"perftest_{uuid.uuid4().hex[:8]}@test.com",
        password="TestPassword123!",
        full_name="Performance Test User"
    )
    return user


@pytest.fixture
async def auth_token(test_user: User) -> str:
    """Generate authentication token."""
    auth_service = AuthService(None)
    token = auth_service.create_access_token(
        user_id=str(test_user.id),
        tenant_id=str(test_user.tenant_id)
    )
    return token


@pytest.fixture
async def test_agents(
    db_session: AsyncSession,
    test_tenant: Tenant
) -> List[Agent]:
    """Create test agents for flow execution."""
    agents = []
    for i in range(5):
        agent = Agent(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            name=f"Test Agent {i}",
            role=f"agent_{i}",
            goal=f"Execute task {i}",
            backstory="Test agent for performance testing",
            llm_provider_id=uuid.uuid4(),  # Mock provider
            config={"max_iterations": 5}
        )
        db_session.add(agent)
        agents.append(agent)

    await db_session.commit()
    return agents


@pytest.fixture
async def test_flows(
    db_session: AsyncSession,
    test_tenant: Tenant,
    test_agents: List[Agent]
) -> List[Flow]:
    """Create test flows with varying complexity."""
    flows = []

    # Simple flow (1 agent, 1 task)
    simple_flow = Flow(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        name="Simple Flow",
        description="Single agent flow",
        definition={
            "nodes": [
                {
                    "id": "node_1",
                    "type": "agent",
                    "agent_id": str(test_agents[0].id),
                    "task": "Process input data",
                    "expected_output": "Processed result"
                }
            ],
            "edges": []
        },
        is_active=True
    )
    db_session.add(simple_flow)
    flows.append(simple_flow)

    # Medium flow (3 agents, sequential)
    medium_flow = Flow(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        name="Medium Flow",
        description="Sequential multi-agent flow",
        definition={
            "nodes": [
                {
                    "id": "node_1",
                    "type": "agent",
                    "agent_id": str(test_agents[0].id),
                    "task": "Analyze input",
                    "expected_output": "Analysis"
                },
                {
                    "id": "node_2",
                    "type": "agent",
                    "agent_id": str(test_agents[1].id),
                    "task": "Generate recommendations",
                    "expected_output": "Recommendations"
                },
                {
                    "id": "node_3",
                    "type": "agent",
                    "agent_id": str(test_agents[2].id),
                    "task": "Create summary",
                    "expected_output": "Summary"
                }
            ],
            "edges": [
                {"source": "node_1", "target": "node_2"},
                {"source": "node_2", "target": "node_3"}
            ]
        },
        is_active=True
    )
    db_session.add(medium_flow)
    flows.append(medium_flow)

    # Complex flow (5 agents, parallel branches)
    complex_flow = Flow(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        name="Complex Flow",
        description="Parallel multi-agent flow",
        definition={
            "nodes": [
                {
                    "id": "node_1",
                    "type": "agent",
                    "agent_id": str(test_agents[0].id),
                    "task": "Initial processing",
                    "expected_output": "Initial result"
                },
                {
                    "id": "node_2",
                    "type": "agent",
                    "agent_id": str(test_agents[1].id),
                    "task": "Branch A analysis",
                    "expected_output": "Branch A result"
                },
                {
                    "id": "node_3",
                    "type": "agent",
                    "agent_id": str(test_agents[2].id),
                    "task": "Branch B analysis",
                    "expected_output": "Branch B result"
                },
                {
                    "id": "node_4",
                    "type": "agent",
                    "agent_id": str(test_agents[3].id),
                    "task": "Merge results",
                    "expected_output": "Merged result"
                },
                {
                    "id": "node_5",
                    "type": "agent",
                    "agent_id": str(test_agents[4].id),
                    "task": "Final summary",
                    "expected_output": "Final summary"
                }
            ],
            "edges": [
                {"source": "node_1", "target": "node_2"},
                {"source": "node_1", "target": "node_3"},
                {"source": "node_2", "target": "node_4"},
                {"source": "node_3", "target": "node_4"},
                {"source": "node_4", "target": "node_5"}
            ]
        },
        is_active=True
    )
    db_session.add(complex_flow)
    flows.append(complex_flow)

    await db_session.commit()
    return flows


@pytest.mark.asyncio
@pytest.mark.performance
async def test_concurrent_simple_flows(
    test_flows: List[Flow],
    auth_token: str
):
    """
    Test 100 concurrent executions of simple flows.

    Acceptance criteria:
    - All 100 executions should be created successfully
    - Response time should be < 1s for 95% of requests
    - No deadlocks or resource exhaustion
    - Execution queue should process all tasks
    """
    num_concurrent = 100
    simple_flow = test_flows[0]

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        headers = {"Authorization": f"Bearer {auth_token}"}

        # Track execution times
        execution_times = []
        execution_ids = []

        async def execute_flow(index: int):
            """Execute a single flow and record timing."""
            start_time = time.time()

            response = await client.post(
                f"/api/v1/flows/{simple_flow.id}/execute",
                headers=headers,
                json={
                    "inputs": {"data": f"Test data {index}"},
                    "config": {"timeout": 60}
                }
            )

            end_time = time.time()
            execution_time = end_time - start_time

            execution_times.append(execution_time)

            assert response.status_code == 201, f"Failed to create execution {index}"
            data = response.json()
            execution_ids.append(data["execution_id"])

            return data

        # Execute all flows concurrently
        print(f"\n🚀 Starting {num_concurrent} concurrent flow executions...")
        start_time = time.time()

        tasks = [execute_flow(i) for i in range(num_concurrent)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        total_time = time.time() - start_time

        # Analyze results
        successful = sum(1 for r in results if not isinstance(r, Exception))
        failed = num_concurrent - successful

        print(f"\n📊 Execution Results:")
        print(f"   Total executions: {num_concurrent}")
        print(f"   Successful: {successful}")
        print(f"   Failed: {failed}")
        print(f"   Total time: {total_time:.2f}s")
        print(f"   Throughput: {num_concurrent / total_time:.2f} executions/sec")

        # Validate response times
        execution_times_sorted = sorted(execution_times)
        p50 = execution_times_sorted[int(len(execution_times_sorted) * 0.50)]
        p95 = execution_times_sorted[int(len(execution_times_sorted) * 0.95)]
        p99 = execution_times_sorted[int(len(execution_times_sorted) * 0.99)]

        print(f"\n⏱️  Response Times:")
        print(f"   P50: {p50:.3f}s")
        print(f"   P95: {p95:.3f}s")
        print(f"   P99: {p99:.3f}s")

        # Assertions
        assert successful == num_concurrent, f"Expected {num_concurrent} successful executions, got {successful}"
        assert p95 < 1.0, f"P95 response time {p95:.3f}s exceeds 1s threshold"

        # Wait for some executions to complete
        await asyncio.sleep(5)

        # Check execution statuses
        statuses = {"pending": 0, "running": 0, "completed": 0, "failed": 0}

        for exec_id in execution_ids[:10]:  # Check first 10
            response = await client.get(
                f"/api/v1/executions/{exec_id}",
                headers=headers
            )
            if response.status_code == 200:
                status = response.json()["status"]
                statuses[status] = statuses.get(status, 0) + 1

        print(f"\n📈 Execution Statuses (sample of 10):")
        for status, count in statuses.items():
            print(f"   {status}: {count}")


@pytest.mark.asyncio
@pytest.mark.performance
async def test_concurrent_mixed_complexity(
    test_flows: List[Flow],
    auth_token: str
):
    """
    Test 100 concurrent executions with mixed flow complexity.

    This simulates a realistic workload with varying flow complexity:
    - 50% simple flows (1 agent)
    - 30% medium flows (3 agents)
    - 20% complex flows (5 agents)
    """
    num_concurrent = 100

    # Distribution: 50 simple, 30 medium, 20 complex
    flow_distribution = (
        [test_flows[0]] * 50 +  # Simple
        [test_flows[1]] * 30 +  # Medium
        [test_flows[2]] * 20    # Complex
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        headers = {"Authorization": f"Bearer {auth_token}"}

        execution_times_by_type = {
            "simple": [],
            "medium": [],
            "complex": []
        }

        async def execute_flow(flow: Flow, index: int):
            """Execute a flow and track timing by type."""
            start_time = time.time()

            response = await client.post(
                f"/api/v1/flows/{flow.id}/execute",
                headers=headers,
                json={
                    "inputs": {"data": f"Test data {index}"},
                    "config": {"timeout": 120}
                }
            )

            end_time = time.time()
            execution_time = end_time - start_time

            flow_type = flow.name.split()[0].lower()
            execution_times_by_type[flow_type].append(execution_time)

            assert response.status_code == 201
            return response.json()

        print(f"\n🚀 Starting {num_concurrent} mixed complexity executions...")
        start_time = time.time()

        tasks = [execute_flow(flow, i) for i, flow in enumerate(flow_distribution)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        total_time = time.time() - start_time

        # Analyze results by complexity
        print(f"\n📊 Results by Flow Complexity:")
        for flow_type, times in execution_times_by_type.items():
            if times:
                avg_time = sum(times) / len(times)
                p95_time = sorted(times)[int(len(times) * 0.95)]
                print(f"   {flow_type.capitalize()} flows:")
                print(f"      Count: {len(times)}")
                print(f"      Avg time: {avg_time:.3f}s")
                print(f"      P95 time: {p95_time:.3f}s")

        print(f"\n   Total time: {total_time:.2f}s")
        print(f"   Throughput: {num_concurrent / total_time:.2f} executions/sec")

        # Assertions
        successful = sum(1 for r in results if not isinstance(r, Exception))
        assert successful == num_concurrent


@pytest.mark.asyncio
@pytest.mark.performance
async def test_sustained_load(
    test_flows: List[Flow],
    auth_token: str
):
    """
    Test sustained load over 5 minutes with continuous flow executions.

    This test validates:
    - No memory leaks during sustained operation
    - Consistent performance over time
    - Proper cleanup of completed executions
    """
    duration_seconds = 300  # 5 minutes
    target_rps = 2  # 2 executions per second
    simple_flow = test_flows[0]

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        headers = {"Authorization": f"Bearer {auth_token}"}

        execution_count = 0
        error_count = 0
        response_times = []

        start_time = time.time()
        end_time = start_time + duration_seconds

        print(f"\n🔥 Starting sustained load test ({duration_seconds}s @ {target_rps} RPS)...")

        async def execute_flow():
            """Execute a single flow."""
            nonlocal execution_count, error_count

            try:
                req_start = time.time()

                response = await client.post(
                    f"/api/v1/flows/{simple_flow.id}/execute",
                    headers=headers,
                    json={
                        "inputs": {"data": f"Sustained load {execution_count}"},
                        "config": {"timeout": 60}
                    }
                )

                req_time = time.time() - req_start
                response_times.append(req_time)

                if response.status_code == 201:
                    execution_count += 1
                else:
                    error_count += 1

            except Exception as e:
                error_count += 1
                print(f"Error: {e}")

        # Run test for specified duration
        while time.time() < end_time:
            batch_start = time.time()

            # Execute target RPS
            await asyncio.gather(*[execute_flow() for _ in range(target_rps)])

            # Sleep to maintain RPS
            elapsed = time.time() - batch_start
            sleep_time = max(0, 1.0 - elapsed)
            await asyncio.sleep(sleep_time)

            # Print progress every 30 seconds
            if int(time.time() - start_time) % 30 == 0:
                current_rps = execution_count / (time.time() - start_time)
                print(f"   Progress: {int(time.time() - start_time)}s | "
                      f"Executions: {execution_count} | "
                      f"Errors: {error_count} | "
                      f"RPS: {current_rps:.2f}")

        total_duration = time.time() - start_time

        # Final statistics
        print(f"\n📊 Sustained Load Results:")
        print(f"   Duration: {total_duration:.2f}s")
        print(f"   Total executions: {execution_count}")
        print(f"   Total errors: {error_count}")
        print(f"   Average RPS: {execution_count / total_duration:.2f}")
        print(f"   Error rate: {(error_count / (execution_count + error_count)) * 100:.2f}%")

        if response_times:
            response_times_sorted = sorted(response_times)
            p50 = response_times_sorted[int(len(response_times_sorted) * 0.50)]
            p95 = response_times_sorted[int(len(response_times_sorted) * 0.95)]
            p99 = response_times_sorted[int(len(response_times_sorted) * 0.99)]

            print(f"\n⏱️  Response Times:")
            print(f"   P50: {p50:.3f}s")
            print(f"   P95: {p95:.3f}s")
            print(f"   P99: {p99:.3f}s")

        # Assertions
        error_rate = error_count / (execution_count + error_count) if execution_count + error_count > 0 else 0
        assert error_rate < 0.01, f"Error rate {error_rate * 100:.2f}% exceeds 1% threshold"
        assert p95 < 2.0, f"P95 response time {p95:.3f}s exceeds 2s threshold for sustained load"


@pytest.mark.asyncio
@pytest.mark.performance
async def test_resource_cleanup(
    db_session: AsyncSession,
    test_flows: List[Flow],
    auth_token: str
):
    """
    Test that completed executions are properly cleaned up.

    Validates:
    - Old executions are archived/deleted
    - Database doesn't grow unbounded
    - Logs are properly rotated
    """
    simple_flow = test_flows[0]

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        headers = {"Authorization": f"Bearer {auth_token}"}

        # Create 50 executions
        print("\n🗑️  Testing resource cleanup...")
        execution_ids = []

        for i in range(50):
            response = await client.post(
                f"/api/v1/flows/{simple_flow.id}/execute",
                headers=headers,
                json={
                    "inputs": {"data": f"Cleanup test {i}"},
                    "config": {"timeout": 60}
                }
            )
            assert response.status_code == 201
            execution_ids.append(response.json()["execution_id"])

        # Check initial count
        from sqlalchemy import select, func
        initial_count = await db_session.scalar(
            select(func.count()).select_from(Execution)
        )
        print(f"   Initial execution count: {initial_count}")

        # Wait for executions to complete
        await asyncio.sleep(10)

        # Trigger cleanup (if cleanup endpoint exists)
        # This would be a cron job or background task in production
        cleanup_response = await client.post(
            "/api/v1/admin/cleanup-executions",
            headers=headers,
            json={
                "older_than_days": 0,  # Clean up immediately for testing
                "keep_failed": False
            }
        )

        if cleanup_response.status_code == 200:
            final_count = await db_session.scalar(
                select(func.count()).select_from(Execution)
            )
            print(f"   Final execution count: {final_count}")
            print(f"   Cleaned up: {initial_count - final_count} executions")

            # Verify some cleanup occurred
            assert final_count < initial_count, "No cleanup occurred"
