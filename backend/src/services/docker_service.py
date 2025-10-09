"""Docker service for secure tool execution in rootless containers."""

import docker
import asyncio
from typing import Optional, Dict, Any
from fastapi import HTTPException, status


class DockerService:
    """
    Service for executing tools in isolated Docker containers.

    Uses rootless Docker with Sysbox runtime for security.
    """

    def __init__(self):
        # Connect to Docker daemon (optional - gracefully handle if not available)
        try:
            self.client = docker.from_env()
            self.available = True
        except Exception as e:
            # Docker not available - this is OK for basic operations
            # Tools that require Docker will fail gracefully
            self.client = None
            self.available = False
            import logging
            logging.warning(f"Docker service not available: {str(e)}")

    async def execute_tool(
        self,
        tool_id: int,
        input_data: str,
        docker_image: str,
        docker_command: Optional[str] = None,
        timeout: int = 300,  # 5 minutes default
    ) -> str:
        """
        Execute a tool in an isolated Docker container.

        Args:
            tool_id: Tool ID for logging
            input_data: Input data to pass to the tool
            docker_image: Docker image to use
            docker_command: Command to run (optional)
            timeout: Execution timeout in seconds

        Returns:
            Tool output as string

        Raises:
            HTTPException: If execution fails
        """
        if not self.available:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Docker service is not available. Cannot execute Docker-based tools.",
            )

        container = None

        try:
            # Run container with resource limits
            container = self.client.containers.run(
                image=docker_image,
                command=docker_command,
                stdin_open=True,
                detach=True,
                remove=False,  # We'll remove manually after getting logs
                mem_limit="512m",
                cpu_quota=50000,  # 50% of one CPU
                network_mode="none",  # No network access for security
                security_opt=["no-new-privileges"],
                read_only=True,  # Read-only root filesystem
            )

            # Send input data via stdin
            container_socket = container.attach_socket(
                params={"stdin": 1, "stream": 1}
            )
            container_socket._sock.sendall(input_data.encode() + b"\n")

            # Wait for container with timeout
            result = container.wait(timeout=timeout)

            # Get output
            output = container.logs().decode("utf-8")

            # Check exit code
            if result["StatusCode"] != 0:
                raise Exception(f"Tool execution failed with code {result['StatusCode']}: {output}")

            return output

        except docker.errors.ContainerError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Container error: {str(e)}",
            )

        except docker.errors.ImageNotFound:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Docker image not found: {docker_image}",
            )

        except asyncio.TimeoutError:
            if container:
                container.kill()
            raise HTTPException(
                status_code=status.HTTP_408_REQUEST_TIMEOUT,
                detail=f"Tool execution timed out after {timeout} seconds",
            )

        finally:
            # Cleanup container
            if container:
                try:
                    container.remove(force=True)
                except Exception:
                    pass  # Best effort cleanup

    async def pull_image(self, image: str) -> None:
        """
        Pull a Docker image if not already present.

        Args:
            image: Docker image name
        """
        if not self.available:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Docker service is not available. Cannot pull images.",
            )

        try:
            self.client.images.pull(image)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to pull image: {str(e)}",
            )

    def list_images(self) -> list:
        """List all available Docker images."""
        if not self.available:
            return []
        return [img.tags for img in self.client.images.list()]

    def cleanup_old_containers(self, hours: int = 24) -> int:
        """
        Cleanup old stopped containers.

        Args:
            hours: Remove containers older than this many hours

        Returns:
            Number of containers removed
        """
        if not self.available:
            return 0

        import datetime

        cutoff = datetime.datetime.now() - datetime.timedelta(hours=hours)
        removed = 0

        for container in self.client.containers.list(all=True):
            if container.status == "exited":
                created = datetime.datetime.fromisoformat(
                    container.attrs["Created"].split(".")[0]
                )
                if created < cutoff:
                    container.remove()
                    removed += 1

        return removed
