"""
Locust load test for CrewAI Platform API endpoints.

This test simulates realistic user behavior across all major API endpoints
to measure performance, identify bottlenecks, and validate system behavior
under load.

Run with:
    locust -f backend/tests/performance/locustfile.py --host=http://localhost:8000

For headless mode with 100 users ramping up over 10 seconds:
    locust -f backend/tests/performance/locustfile.py --host=http://localhost:8000 \
           --users 100 --spawn-rate 10 --run-time 5m --headless
"""

import json
import random
import uuid
from typing import Dict, Any

from locust import HttpUser, task, between, events
from locust.exception import RescheduleTask


class CrewAIPlatformUser(HttpUser):
    """
    Simulates a typical platform user performing various operations.

    User behavior pattern:
    - Login and maintain session
    - Create/manage LLM providers (10% of requests)
    - Create/manage agents (15% of requests)
    - Create/manage crews (15% of requests)
    - Create/manage flows (20% of requests)
    - Execute flows (25% of requests)
    - Monitor executions (15% of requests)
    """

    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks

    def on_start(self):
        """Called when a simulated user starts. Handles authentication."""
        self.tenant_slug = f"tenant_{uuid.uuid4().hex[:8]}"
        self.token = None
        self.llm_providers = []
        self.agents = []
        self.crews = []
        self.flows = []
        self.executions = []

        # Register and login
        self._register()
        self._login()

    def _register(self):
        """Register a new tenant."""
        response = self.client.post(
            "/api/v1/auth/register",
            json={
                "email": f"{self.tenant_slug}@loadtest.com",
                "password": "LoadTest123!",
                "tenant_name": f"Load Test {self.tenant_slug}",
                "tenant_slug": self.tenant_slug
            },
            name="/api/v1/auth/register"
        )

        if response.status_code != 201:
            raise RescheduleTask()

    def _login(self):
        """Login and obtain JWT token."""
        response = self.client.post(
            "/api/v1/auth/login",
            data={
                "username": f"{self.tenant_slug}@loadtest.com",
                "password": "LoadTest123!"
            },
            name="/api/v1/auth/login"
        )

        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access_token")
        else:
            raise RescheduleTask()

    @property
    def headers(self) -> Dict[str, str]:
        """Return authorization headers."""
        return {"Authorization": f"Bearer {self.token}"}

    @task(10)
    def create_llm_provider(self):
        """Create a new LLM provider configuration."""
        provider_types = ["openai", "anthropic", "azure", "cohere"]
        provider_type = random.choice(provider_types)

        response = self.client.post(
            "/api/v1/llm-providers",
            headers=self.headers,
            json={
                "name": f"{provider_type}_provider_{uuid.uuid4().hex[:6]}",
                "provider_type": provider_type,
                "config": {
                    "api_key": f"sk-test-{uuid.uuid4().hex}",
                    "model": "gpt-4" if provider_type == "openai" else "claude-3-opus",
                    "temperature": 0.7,
                    "max_tokens": 2000
                },
                "priority": random.randint(1, 10),
                "is_active": True
            },
            name="/api/v1/llm-providers [POST]"
        )

        if response.status_code == 201:
            self.llm_providers.append(response.json()["id"])

    @task(5)
    def list_llm_providers(self):
        """List all LLM provider configurations."""
        self.client.get(
            "/api/v1/llm-providers",
            headers=self.headers,
            name="/api/v1/llm-providers [GET]"
        )

    @task(15)
    def create_agent(self):
        """Create a new AI agent."""
        if not self.llm_providers:
            return

        roles = ["researcher", "writer", "analyst", "reviewer", "coder"]
        role = random.choice(roles)

        response = self.client.post(
            "/api/v1/agents",
            headers=self.headers,
            json={
                "name": f"{role}_agent_{uuid.uuid4().hex[:6]}",
                "role": role,
                "goal": f"Act as a {role} and help with tasks",
                "backstory": f"You are an expert {role} with years of experience",
                "llm_provider_id": random.choice(self.llm_providers),
                "allow_delegation": random.choice([True, False]),
                "verbose": True,
                "config": {
                    "max_iterations": 10,
                    "memory": True
                }
            },
            name="/api/v1/agents [POST]"
        )

        if response.status_code == 201:
            self.agents.append(response.json()["id"])

    @task(5)
    def list_agents(self):
        """List all agents."""
        self.client.get(
            "/api/v1/agents",
            headers=self.headers,
            name="/api/v1/agents [GET]"
        )

    @task(3)
    def get_agent_detail(self):
        """Get agent details."""
        if not self.agents:
            return

        agent_id = random.choice(self.agents)
        self.client.get(
            f"/api/v1/agents/{agent_id}",
            headers=self.headers,
            name="/api/v1/agents/{id} [GET]"
        )

    @task(15)
    def create_crew(self):
        """Create a new crew with multiple agents."""
        if len(self.agents) < 2:
            return

        selected_agents = random.sample(self.agents, min(3, len(self.agents)))

        response = self.client.post(
            "/api/v1/crews",
            headers=self.headers,
            json={
                "name": f"crew_{uuid.uuid4().hex[:6]}",
                "description": "A crew for load testing",
                "agent_ids": selected_agents,
                "process": random.choice(["sequential", "hierarchical"]),
                "verbose": True,
                "config": {
                    "max_rpm": 10,
                    "share_crew": False
                }
            },
            name="/api/v1/crews [POST]"
        )

        if response.status_code == 201:
            self.crews.append(response.json()["id"])

    @task(5)
    def list_crews(self):
        """List all crews."""
        self.client.get(
            "/api/v1/crews",
            headers=self.headers,
            name="/api/v1/crews [GET]"
        )

    @task(20)
    def create_flow(self):
        """Create a new workflow."""
        if not self.agents:
            return

        flow_data = {
            "name": f"flow_{uuid.uuid4().hex[:6]}",
            "description": "Load test workflow",
            "definition": {
                "nodes": [
                    {
                        "id": "node_1",
                        "type": "agent",
                        "agent_id": random.choice(self.agents),
                        "task": "Analyze the input data",
                        "expected_output": "Analysis report"
                    },
                    {
                        "id": "node_2",
                        "type": "agent",
                        "agent_id": random.choice(self.agents),
                        "task": "Generate recommendations based on analysis",
                        "expected_output": "List of recommendations"
                    }
                ],
                "edges": [
                    {
                        "source": "node_1",
                        "target": "node_2"
                    }
                ]
            },
            "is_active": True
        }

        response = self.client.post(
            "/api/v1/flows",
            headers=self.headers,
            json=flow_data,
            name="/api/v1/flows [POST]"
        )

        if response.status_code == 201:
            self.flows.append(response.json()["id"])

    @task(10)
    def list_flows(self):
        """List all flows."""
        self.client.get(
            "/api/v1/flows",
            headers=self.headers,
            name="/api/v1/flows [GET]"
        )

    @task(25)
    def execute_flow(self):
        """Execute a workflow."""
        if not self.flows:
            return

        flow_id = random.choice(self.flows)

        response = self.client.post(
            f"/api/v1/flows/{flow_id}/execute",
            headers=self.headers,
            json={
                "inputs": {
                    "data": f"Sample data for execution {uuid.uuid4().hex[:8]}"
                },
                "config": {
                    "timeout": 300,
                    "max_retries": 3
                }
            },
            name="/api/v1/flows/{id}/execute [POST]"
        )

        if response.status_code == 201:
            self.executions.append(response.json()["execution_id"])

    @task(15)
    def get_execution_status(self):
        """Check execution status."""
        if not self.executions:
            return

        execution_id = random.choice(self.executions)

        self.client.get(
            f"/api/v1/executions/{execution_id}",
            headers=self.headers,
            name="/api/v1/executions/{id} [GET]"
        )

    @task(10)
    def list_executions(self):
        """List all executions."""
        self.client.get(
            "/api/v1/executions",
            headers=self.headers,
            params={
                "limit": 50,
                "offset": 0
            },
            name="/api/v1/executions [GET]"
        )

    @task(5)
    def get_execution_logs(self):
        """Get execution logs."""
        if not self.executions:
            return

        execution_id = random.choice(self.executions)

        self.client.get(
            f"/api/v1/executions/{execution_id}/logs",
            headers=self.headers,
            name="/api/v1/executions/{id}/logs [GET]"
        )

    @task(3)
    def health_check(self):
        """Check API health endpoint."""
        self.client.get(
            "/health",
            name="/health [GET]"
        )


class AdminUser(HttpUser):
    """
    Simulates an admin user performing system-level operations.

    Admin operations:
    - View system metrics
    - Monitor all tenants
    - Check platform health
    """

    wait_time = between(5, 10)  # Admins check less frequently
    weight = 1  # Only 1 admin for every 10 regular users

    def on_start(self):
        """Admin login."""
        self.token = None
        self._admin_login()

    def _admin_login(self):
        """Login with admin credentials."""
        # In production, you'd use actual admin credentials
        response = self.client.post(
            "/api/v1/auth/login",
            data={
                "username": "admin@crewai.com",
                "password": "admin_password"
            },
            name="/api/v1/auth/login [ADMIN]"
        )

        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access_token")

    @property
    def headers(self) -> Dict[str, str]:
        """Return authorization headers."""
        if not self.token:
            return {}
        return {"Authorization": f"Bearer {self.token}"}

    @task(10)
    def get_system_metrics(self):
        """Get system-wide metrics."""
        self.client.get(
            "/api/v1/admin/metrics",
            headers=self.headers,
            name="/api/v1/admin/metrics [GET]"
        )

    @task(5)
    def list_all_tenants(self):
        """List all tenants in the system."""
        self.client.get(
            "/api/v1/admin/tenants",
            headers=self.headers,
            name="/api/v1/admin/tenants [GET]"
        )

    @task(15)
    def check_health(self):
        """Check platform health."""
        self.client.get(
            "/health",
            name="/health [GET]"
        )


# Event handlers for custom metrics

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when the test starts."""
    print("Starting CrewAI Platform load test...")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when the test stops."""
    print("Load test completed.")
    print(f"Total requests: {environment.stats.total.num_requests}")
    print(f"Total failures: {environment.stats.total.num_failures}")
    print(f"Average response time: {environment.stats.total.avg_response_time:.2f}ms")
    print(f"RPS: {environment.stats.total.total_rps:.2f}")
