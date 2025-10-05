"""Unit tests for DockerService - container isolation and security."""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi import HTTPException
import docker.errors

from src.services.docker_service import DockerService


@pytest.fixture
def mock_docker_client():
    """Create a mock Docker client."""
    client = Mock()
    client.containers = Mock()
    client.images = Mock()
    return client


@pytest.fixture
def docker_service(mock_docker_client):
    """Create a DockerService with mocked Docker client."""
    with patch('docker.from_env', return_value=mock_docker_client):
        service = DockerService()
    return service


@pytest.fixture
def mock_container():
    """Create a mock Docker container."""
    container = Mock()
    container.id = "test_container_id"
    container.status = "running"
    container.wait = Mock(return_value={"StatusCode": 0})
    container.logs = Mock(return_value=b"Tool output")
    container.attach_socket = Mock()
    container.kill = Mock()
    container.remove = Mock()
    return container


class TestDockerServiceInitialization:
    """Tests for DockerService initialization."""

    def test_initialization_success(self, mock_docker_client):
        """Test successful Docker client initialization."""
        with patch('docker.from_env', return_value=mock_docker_client):
            service = DockerService()
            assert service.client == mock_docker_client

    def test_initialization_failure(self):
        """Test initialization fails when Docker is not available."""
        with patch('docker.from_env', side_effect=Exception("Docker daemon not running")):
            with pytest.raises(RuntimeError) as exc_info:
                DockerService()

            assert "Failed to connect to Docker" in str(exc_info.value)


class TestExecuteTool:
    """Tests for execute_tool method."""

    @pytest.mark.asyncio
    async def test_execute_tool_success(self, docker_service, mock_container):
        """Test successful tool execution in container."""
        # Arrange
        mock_socket = Mock()
        mock_socket._sock = Mock()
        mock_socket._sock.sendall = Mock()
        mock_container.attach_socket.return_value = mock_socket

        docker_service.client.containers.run = Mock(return_value=mock_container)

        # Act
        result = await docker_service.execute_tool(
            tool_id=1,
            input_data="test input",
            docker_image="python:3.11-slim",
            docker_command="python -c 'print(input())'",
            timeout=60
        )

        # Assert
        assert result == "Tool output"

        # Verify container was run with security constraints
        docker_service.client.containers.run.assert_called_once()
        call_kwargs = docker_service.client.containers.run.call_args[1]
        assert call_kwargs["image"] == "python:3.11-slim"
        assert call_kwargs["mem_limit"] == "512m"
        assert call_kwargs["network_mode"] == "none"
        assert call_kwargs["read_only"] is True
        assert "no-new-privileges" in call_kwargs["security_opt"]

        # Verify input was sent
        mock_socket._sock.sendall.assert_called_once()

        # Verify container cleanup
        mock_container.remove.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_tool_with_resource_limits(self, docker_service, mock_container):
        """Test tool execution applies resource limits."""
        # Arrange
        mock_socket = Mock()
        mock_socket._sock = Mock()
        mock_container.attach_socket.return_value = mock_socket
        docker_service.client.containers.run = Mock(return_value=mock_container)

        # Act
        await docker_service.execute_tool(
            tool_id=1,
            input_data="test",
            docker_image="python:3.11-slim",
        )

        # Assert
        call_kwargs = docker_service.client.containers.run.call_args[1]
        assert call_kwargs["mem_limit"] == "512m"
        assert call_kwargs["cpu_quota"] == 50000  # 50% of one CPU

    @pytest.mark.asyncio
    async def test_execute_tool_network_isolation(self, docker_service, mock_container):
        """Test tool execution enforces network isolation."""
        # Arrange
        mock_socket = Mock()
        mock_socket._sock = Mock()
        mock_container.attach_socket.return_value = mock_socket
        docker_service.client.containers.run = Mock(return_value=mock_container)

        # Act
        await docker_service.execute_tool(
            tool_id=1,
            input_data="test",
            docker_image="python:3.11-slim",
        )

        # Assert - verify network is disabled for security
        call_kwargs = docker_service.client.containers.run.call_args[1]
        assert call_kwargs["network_mode"] == "none"

    @pytest.mark.asyncio
    async def test_execute_tool_read_only_filesystem(self, docker_service, mock_container):
        """Test tool execution enforces read-only filesystem."""
        # Arrange
        mock_socket = Mock()
        mock_socket._sock = Mock()
        mock_container.attach_socket.return_value = mock_socket
        docker_service.client.containers.run = Mock(return_value=mock_container)

        # Act
        await docker_service.execute_tool(
            tool_id=1,
            input_data="test",
            docker_image="python:3.11-slim",
        )

        # Assert - verify filesystem is read-only
        call_kwargs = docker_service.client.containers.run.call_args[1]
        assert call_kwargs["read_only"] is True

    @pytest.mark.asyncio
    async def test_execute_tool_security_options(self, docker_service, mock_container):
        """Test tool execution applies security options."""
        # Arrange
        mock_socket = Mock()
        mock_socket._sock = Mock()
        mock_container.attach_socket.return_value = mock_socket
        docker_service.client.containers.run = Mock(return_value=mock_container)

        # Act
        await docker_service.execute_tool(
            tool_id=1,
            input_data="test",
            docker_image="python:3.11-slim",
        )

        # Assert - verify no-new-privileges security option
        call_kwargs = docker_service.client.containers.run.call_args[1]
        assert "no-new-privileges" in call_kwargs["security_opt"]

    @pytest.mark.asyncio
    async def test_execute_tool_non_zero_exit_code(self, docker_service, mock_container):
        """Test tool execution handles non-zero exit codes."""
        # Arrange
        mock_socket = Mock()
        mock_socket._sock = Mock()
        mock_container.attach_socket.return_value = mock_socket
        mock_container.wait.return_value = {"StatusCode": 1}
        mock_container.logs.return_value = b"Error occurred"
        docker_service.client.containers.run = Mock(return_value=mock_container)

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await docker_service.execute_tool(
                tool_id=1,
                input_data="test",
                docker_image="python:3.11-slim",
            )

        assert "failed with code 1" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_tool_image_not_found(self, docker_service):
        """Test tool execution handles missing Docker image."""
        # Arrange
        docker_service.client.containers.run = Mock(
            side_effect=docker.errors.ImageNotFound("Image not found")
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await docker_service.execute_tool(
                tool_id=1,
                input_data="test",
                docker_image="nonexistent:latest",
            )

        assert exc_info.value.status_code == 404
        assert "not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_execute_tool_container_error(self, docker_service):
        """Test tool execution handles container errors."""
        # Arrange
        docker_service.client.containers.run = Mock(
            side_effect=docker.errors.ContainerError(
                container="test",
                exit_status=1,
                command="test",
                image="test",
                stderr="Error message"
            )
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await docker_service.execute_tool(
                tool_id=1,
                input_data="test",
                docker_image="python:3.11-slim",
            )

        assert exc_info.value.status_code == 500
        assert "Container error" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_execute_tool_cleanup_on_error(self, docker_service, mock_container):
        """Test container cleanup occurs even on error."""
        # Arrange
        mock_socket = Mock()
        mock_socket._sock = Mock()
        mock_container.attach_socket.return_value = mock_socket
        mock_container.wait.side_effect = Exception("Unexpected error")
        docker_service.client.containers.run = Mock(return_value=mock_container)

        # Act & Assert
        with pytest.raises(Exception):
            await docker_service.execute_tool(
                tool_id=1,
                input_data="test",
                docker_image="python:3.11-slim",
            )

        # Verify cleanup was attempted
        mock_container.remove.assert_called_once_with(force=True)


class TestPullImage:
    """Tests for pull_image method."""

    @pytest.mark.asyncio
    async def test_pull_image_success(self, docker_service):
        """Test successful image pull."""
        # Arrange
        docker_service.client.images.pull = Mock()

        # Act
        await docker_service.pull_image("python:3.11-slim")

        # Assert
        docker_service.client.images.pull.assert_called_once_with("python:3.11-slim")

    @pytest.mark.asyncio
    async def test_pull_image_failure(self, docker_service):
        """Test image pull failure."""
        # Arrange
        docker_service.client.images.pull = Mock(
            side_effect=Exception("Network error")
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await docker_service.pull_image("python:3.11-slim")

        assert exc_info.value.status_code == 500
        assert "Failed to pull image" in str(exc_info.value.detail)


class TestListImages:
    """Tests for list_images method."""

    def test_list_images(self, docker_service):
        """Test listing Docker images."""
        # Arrange
        mock_image1 = Mock()
        mock_image1.tags = ["python:3.11-slim"]
        mock_image2 = Mock()
        mock_image2.tags = ["node:18-alpine"]

        docker_service.client.images.list = Mock(return_value=[mock_image1, mock_image2])

        # Act
        result = docker_service.list_images()

        # Assert
        assert result == [["python:3.11-slim"], ["node:18-alpine"]]


class TestCleanupOldContainers:
    """Tests for cleanup_old_containers method."""

    def test_cleanup_old_containers(self, docker_service):
        """Test cleanup of old exited containers."""
        # Arrange
        import datetime

        old_date = (datetime.datetime.now() - datetime.timedelta(hours=48)).isoformat()
        recent_date = (datetime.datetime.now() - datetime.timedelta(hours=1)).isoformat()

        old_container = Mock()
        old_container.status = "exited"
        old_container.attrs = {"Created": old_date}
        old_container.remove = Mock()

        recent_container = Mock()
        recent_container.status = "exited"
        recent_container.attrs = {"Created": recent_date}
        recent_container.remove = Mock()

        running_container = Mock()
        running_container.status = "running"

        docker_service.client.containers.list = Mock(
            return_value=[old_container, recent_container, running_container]
        )

        # Act
        removed = docker_service.cleanup_old_containers(hours=24)

        # Assert
        assert removed == 1  # Only old_container should be removed
        old_container.remove.assert_called_once()
        recent_container.remove.assert_not_called()

    def test_cleanup_no_old_containers(self, docker_service):
        """Test cleanup when no old containers exist."""
        # Arrange
        docker_service.client.containers.list = Mock(return_value=[])

        # Act
        removed = docker_service.cleanup_old_containers(hours=24)

        # Assert
        assert removed == 0
