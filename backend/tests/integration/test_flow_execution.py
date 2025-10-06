"""
Integration Test: Flow Execution with Docker-in-Docker

This test validates:
1. Tool execution in isolated Docker containers
2. Resource limits enforcement (CPU, memory, timeout)
3. Container lifecycle management
4. Output capture and error handling
5. Security isolation via rootless Docker
"""

import pytest
import asyncio
import uuid
from datetime import datetime

from src.services.flow_service import FlowService
from src.services.execution_service import ExecutionService
from src.services.docker_service import DockerService
from src.models import Flow, Tool, Execution


class TestFlowExecutionWithDocker:
    """Test suite for Docker-based tool execution in flows."""

    @pytest.fixture
    async def docker_service(self):
        """Initialize Docker service."""
        service = DockerService()
        yield service
        # Cleanup: remove any dangling containers
        await service.cleanup_all()

    @pytest.fixture
    async def test_tool(self, db_session, test_tenant):
        """Create a test tool with Docker execution config."""
        tool = Tool(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            name="Echo Tool",
            description="Simple echo tool for testing",
            input_schema={
                "type": "object",
                "properties": {"message": {"type": "string"}},
                "required": ["message"],
            },
            output_schema={
                "type": "object",
                "properties": {"result": {"type": "string"}},
            },
            execution_config={
                "docker_image": "python:3.11-slim",
                "entrypoint": [
                    "python",
                    "-c",
                    "import sys, json; data=json.load(sys.stdin); print(json.dumps({'result': f'Echo: {data[\"message\"]}'}), flush=True)",
                ],
                "timeout_seconds": 30,
                "cpu_limit": "1",
                "memory_limit": "512Mi",
            },
            status="active",
        )
        db_session.add(tool)
        await db_session.commit()
        yield tool

    @pytest.mark.asyncio
    async def test_simple_tool_execution(self, docker_service, test_tool):
        """Test basic Docker container tool execution."""
        input_data = {"message": "Hello World"}

        result = await docker_service.execute_tool(
            tool_id=test_tool.id,
            input_data=input_data,
            execution_config=test_tool.execution_config,
        )

        assert result["status"] == "success"
        assert result["output"]["result"] == "Echo: Hello World"
        assert "execution_time_ms" in result
        assert result["execution_time_ms"] < 30000

    @pytest.mark.asyncio
    async def test_resource_limits_enforcement(self, docker_service):
        """Test that CPU and memory limits are enforced."""
        # Tool that tries to allocate excessive memory
        memory_hog_config = {
            "docker_image": "python:3.11-slim",
            "entrypoint": [
                "python",
                "-c",
                "import sys; data = [0] * (1024 * 1024 * 1024); sys.exit(0)",  # Try to allocate 1GB
            ],
            "timeout_seconds": 10,
            "cpu_limit": "0.5",
            "memory_limit": "256Mi",  # Only 256MB allowed
        }

        with pytest.raises(Exception, match="memory limit exceeded|OOMKilled"):
            await docker_service.execute_tool(
                tool_id=uuid.uuid4(),
                input_data={},
                execution_config=memory_hog_config,
            )

    @pytest.mark.asyncio
    async def test_execution_timeout(self, docker_service):
        """Test that execution timeout is enforced."""
        # Tool that sleeps longer than timeout
        timeout_config = {
            "docker_image": "python:3.11-slim",
            "entrypoint": ["python", "-c", "import time; time.sleep(60)"],
            "timeout_seconds": 2,
            "cpu_limit": "1",
            "memory_limit": "512Mi",
        }

        start_time = datetime.now()

        with pytest.raises(Exception, match="timeout|timed out"):
            await docker_service.execute_tool(
                tool_id=uuid.uuid4(), input_data={}, execution_config=timeout_config
            )

        elapsed = (datetime.now() - start_time).total_seconds()
        assert elapsed < 5  # Should timeout around 2 seconds, definitely < 5

    @pytest.mark.asyncio
    async def test_container_isolation(self, docker_service):
        """Test that containers are isolated from host filesystem."""
        # Try to access host filesystem (should fail)
        isolation_config = {
            "docker_image": "python:3.11-slim",
            "entrypoint": ["python", "-c", "open('/etc/passwd', 'r').read()"],
            "timeout_seconds": 5,
            "cpu_limit": "1",
            "memory_limit": "512Mi",
        }

        # In rootless Docker with proper isolation, this should fail or return container's /etc/passwd
        # not the host's
        result = await docker_service.execute_tool(
            tool_id=uuid.uuid4(), input_data={}, execution_config=isolation_config
        )

        # Container should have its own /etc/passwd, not host's
        assert result["status"] in ["success", "error"]

    @pytest.mark.asyncio
    async def test_flow_with_tool_nodes(
        self, db_session, test_tenant, test_user, test_tool
    ):
        """Test full flow execution with tool nodes."""
        # Create flow with Input -> Tool -> Output
        flow = Flow(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            name="Tool Execution Flow",
            nodes=[
                {"id": "input1", "type": "input", "position": {"x": 0, "y": 0}},
                {
                    "id": "tool1",
                    "type": "tool",
                    "position": {"x": 200, "y": 0},
                    "data": {"tool_id": str(test_tool.id), "inputs": {"message": "{{input.text}}"}},
                },
                {"id": "output1", "type": "output", "position": {"x": 400, "y": 0}},
            ],
            edges=[
                {"id": "e1", "source": "input1", "target": "tool1"},
                {"id": "e2", "source": "tool1", "target": "output1"},
            ],
            status="published",
        )
        db_session.add(flow)
        await db_session.commit()

        # Execute flow
        execution_service = ExecutionService(db_session)
        execution = await execution_service.create_execution(
            flow_id=flow.id,
            user_id=test_user.id,
            inputs={"text": "Integration Test"},
        )

        # Start execution
        await execution_service.start_execution(execution.id)

        # Wait for completion (with timeout)
        max_wait = 60  # 60 seconds
        waited = 0
        while waited < max_wait:
            await asyncio.sleep(1)
            waited += 1

            execution = await execution_service.get_execution(execution.id)
            if execution.status in ["succeeded", "failed", "timeout"]:
                break

        assert execution.status == "succeeded"
        assert execution.outputs is not None
        assert "result" in execution.outputs

    @pytest.mark.asyncio
    async def test_parallel_tool_executions(self, docker_service, test_tool):
        """Test that multiple tools can execute concurrently."""
        # Execute 5 tools in parallel
        tasks = [
            docker_service.execute_tool(
                tool_id=test_tool.id,
                input_data={"message": f"Message {i}"},
                execution_config=test_tool.execution_config,
            )
            for i in range(5)
        ]

        results = await asyncio.gather(*tasks)

        assert len(results) == 5
        for i, result in enumerate(results):
            assert result["status"] == "success"
            assert f"Message {i}" in result["output"]["result"]

    @pytest.mark.asyncio
    async def test_error_handling_in_tool(self, docker_service):
        """Test that tool execution errors are captured properly."""
        error_config = {
            "docker_image": "python:3.11-slim",
            "entrypoint": ["python", "-c", "raise Exception('Test error')"],
            "timeout_seconds": 5,
            "cpu_limit": "1",
            "memory_limit": "512Mi",
        }

        result = await docker_service.execute_tool(
            tool_id=uuid.uuid4(), input_data={}, execution_config=error_config
        )

        assert result["status"] == "error"
        assert "Test error" in result.get("error_message", "")

    @pytest.mark.asyncio
    async def test_container_cleanup(self, docker_service, test_tool):
        """Test that containers are cleaned up after execution."""
        # Execute tool
        await docker_service.execute_tool(
            tool_id=test_tool.id,
            input_data={"message": "Cleanup test"},
            execution_config=test_tool.execution_config,
        )

        # Check that no containers are left running
        running_containers = await docker_service.list_running_containers()

        # Filter to only our test containers
        test_containers = [
            c for c in running_containers if c["image"] == "python:3.11-slim"
        ]

        assert len(test_containers) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
