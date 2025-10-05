"""Pytest fixtures for contract and integration tests."""

import pytest
import asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.main import app
from src.db.postgres import Base, get_db
from src.models import Tenant, User, Agent, Flow, Tool, Execution, ChatSession, LLMProvider


# Test database URL
TEST_DATABASE_URL = "postgresql://crewai:dev_password@localhost:5432/crewai_platform_test"

# Create test engine
test_engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def db_session():
    """Create a fresh database session for each test."""
    # Create all tables
    Base.metadata.create_all(bind=test_engine)

    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        # Drop all tables after test
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create test client without authentication."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture(scope="function")
async def test_user(db_session) -> dict:
    """Create a test user."""
    # Create tenant
    tenant = Tenant(
        name="Test Tenant",
        schema_name="test_tenant",
        api_key="test_api_key_123",
    )
    db_session.add(tenant)
    db_session.commit()

    # Create user
    user = User(
        tenant_id=tenant.id,
        email="test@example.com",
        password_hash="hashed_password",  # In real tests, use proper hashing
        full_name="Test User",
        role="admin",
    )
    db_session.add(user)
    db_session.commit()

    return {
        "id": user.id,
        "email": user.email,
        "password": "password123",  # Plain password for testing
        "tenant_id": tenant.id,
        "tenant_schema": tenant.schema_name,
        "role": user.role,
    }


@pytest.fixture(scope="function")
async def authed_client(client: AsyncClient, test_user: dict) -> AsyncClient:
    """Create authenticated test client."""
    # Login to get token
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": test_user["email"], "password": test_user["password"]},
    )
    token = response.json()["access_token"]

    # Set authorization header
    client.headers["Authorization"] = f"Bearer {token}"
    return client


@pytest.fixture(scope="function")
async def test_llm_provider(db_session) -> dict:
    """Create a test LLM provider."""
    provider = LLMProvider(
        name="Test OpenAI",
        provider_type="openai",
        model_name="gpt-4",
        api_key="test_key",
        is_active=True,
        is_default=True,
    )
    db_session.add(provider)
    db_session.commit()

    return {"id": provider.id, "name": provider.name, "model_name": provider.model_name}


@pytest.fixture(scope="function")
async def test_agent(db_session, test_llm_provider: dict) -> dict:
    """Create a test agent."""
    agent = Agent(
        name="Test Agent",
        role="Researcher",
        goal="Research topics",
        backstory="An experienced researcher",
        llm_provider_id=test_llm_provider["id"],
        temperature=0.7,
    )
    db_session.add(agent)
    db_session.commit()

    return {"id": agent.id, "name": agent.name, "role": agent.role}


@pytest.fixture(scope="function")
async def test_flow(db_session) -> dict:
    """Create a test flow."""
    flow = Flow(
        name="Test Flow",
        description="A test flow",
        status="draft",
        nodes=[
            {"id": "node1", "type": "input", "position": {"x": 0, "y": 0}, "data": {}}
        ],
        edges=[],
        version=1,
    )
    db_session.add(flow)
    db_session.commit()

    return {
        "id": flow.id,
        "name": flow.name,
        "status": flow.status,
        "nodes": flow.nodes,
    }


@pytest.fixture(scope="function")
async def test_execution(db_session, test_flow: dict, test_user: dict) -> dict:
    """Create a test execution."""
    execution = Execution(
        execution_type="flow",
        status="pending",
        flow_id=test_flow["id"],
        user_id=test_user["id"],
        input_data={"test": "data"},
    )
    db_session.add(execution)
    db_session.commit()

    return {
        "id": execution.id,
        "flow_id": execution.flow_id,
        "status": execution.status,
    }


@pytest.fixture(scope="function")
async def test_chat_session(db_session, test_user: dict, test_llm_provider: dict) -> dict:
    """Create a test chat session."""
    session = ChatSession(
        user_id=test_user["id"],
        title="Test Chat",
        llm_provider_id=test_llm_provider["id"],
        is_active=True,
    )
    db_session.add(session)
    db_session.commit()

    return {
        "id": session.id,
        "user_id": session.user_id,
        "title": session.title,
    }
