"""
Integration Test: Multi-Tenant Schema Isolation

This test validates that:
1. Each tenant gets its own PostgreSQL schema
2. Data is completely isolated between tenants
3. Queries automatically scope to correct tenant schema
4. Cross-tenant data access is prevented
5. Schema switching via middleware works correctly
"""

import pytest
import uuid
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker

from src.db import get_db
from src.models import Tenant, User, Flow, Agent
from src.services.tenant_service import TenantService
from src.api.middleware.tenant import set_tenant_context


class TestMultiTenancyIsolation:
    """Test suite for multi-tenant schema isolation."""

    @pytest.fixture
    async def test_tenants(self, db_session):
        """Create two test tenants for isolation testing."""
        tenant_service = TenantService(db_session)

        # Create Tenant A
        tenant_a = await tenant_service.create_tenant(
            name="Test Tenant A",
            slug=f"test-a-{uuid.uuid4().hex[:8]}",
            settings={},
            quotas={
                "max_flows": 100,
                "max_executions_per_day": 1000,
                "max_storage_gb": 10,
                "max_llm_tokens_per_day": 100000,
            },
        )

        # Create Tenant B
        tenant_b = await tenant_service.create_tenant(
            name="Test Tenant B",
            slug=f"test-b-{uuid.uuid4().hex[:8]}",
            settings={},
            quotas={
                "max_flows": 100,
                "max_executions_per_day": 1000,
                "max_storage_gb": 10,
                "max_llm_tokens_per_day": 100000,
            },
        )

        yield tenant_a, tenant_b

        # Cleanup: Drop tenant schemas
        await tenant_service.delete_tenant(tenant_a.id)
        await tenant_service.delete_tenant(tenant_b.id)

    @pytest.mark.asyncio
    async def test_schema_creation(self, db_session, test_tenants):
        """Test that tenant schemas are created correctly."""
        tenant_a, tenant_b = test_tenants

        # Verify schemas exist
        inspector = inspect(db_session.bind)
        schemas = inspector.get_schema_names()

        assert tenant_a.db_schema in schemas
        assert tenant_b.db_schema in schemas

        # Verify schema naming convention
        assert tenant_a.db_schema.startswith("tenant_")
        assert tenant_b.db_schema.startswith("tenant_")

    @pytest.mark.asyncio
    async def test_data_isolation_users(self, db_session, test_tenants):
        """Test that user data is isolated between tenants."""
        tenant_a, tenant_b = test_tenants

        # Set context to Tenant A
        set_tenant_context(tenant_a.id, tenant_a.db_schema)

        # Create user in Tenant A
        user_a = User(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            email="user_a@test.com",
            password_hash="hashed_password",
            role="admin",
            status="active",
        )
        db_session.add(user_a)
        await db_session.commit()

        # Query users in Tenant A
        result_a = await db_session.execute(text("SELECT * FROM users"))
        users_a = result_a.fetchall()
        assert len(users_a) == 1
        assert users_a[0].email == "user_a@test.com"

        # Switch context to Tenant B
        set_tenant_context(tenant_b.id, tenant_b.db_schema)

        # Create user in Tenant B
        user_b = User(
            id=uuid.uuid4(),
            tenant_id=tenant_b.id,
            email="user_b@test.com",
            password_hash="hashed_password",
            role="editor",
            status="active",
        )
        db_session.add(user_b)
        await db_session.commit()

        # Query users in Tenant B
        result_b = await db_session.execute(text("SELECT * FROM users"))
        users_b = result_b.fetchall()
        assert len(users_b) == 1
        assert users_b[0].email == "user_b@test.com"

        # Verify isolation: User A should not be visible in Tenant B
        user_a_in_b = await db_session.execute(
            text("SELECT * FROM users WHERE email = 'user_a@test.com'")
        )
        assert user_a_in_b.fetchone() is None

        # Switch back to Tenant A
        set_tenant_context(tenant_a.id, tenant_a.db_schema)

        # Verify User B is not visible in Tenant A
        user_b_in_a = await db_session.execute(
            text("SELECT * FROM users WHERE email = 'user_b@test.com'")
        )
        assert user_b_in_a.fetchone() is None

    @pytest.mark.asyncio
    async def test_data_isolation_flows(self, db_session, test_tenants):
        """Test that flow data is isolated between tenants."""
        tenant_a, tenant_b = test_tenants

        # Create user in Tenant A
        set_tenant_context(tenant_a.id, tenant_a.db_schema)
        user_a = User(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            email="creator_a@test.com",
            password_hash="hashed",
            role="admin",
            status="active",
        )
        db_session.add(user_a)
        await db_session.commit()

        # Create flow in Tenant A
        flow_a = Flow(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            user_id=user_a.id,
            name="Flow A",
            nodes=[{"id": "node1", "type": "input"}],
            edges=[],
            status="published",
        )
        db_session.add(flow_a)
        await db_session.commit()

        # Query flows in Tenant A
        result_a = await db_session.execute(text("SELECT * FROM flows"))
        flows_a = result_a.fetchall()
        assert len(flows_a) == 1
        assert flows_a[0].name == "Flow A"

        # Switch to Tenant B
        set_tenant_context(tenant_b.id, tenant_b.db_schema)

        # Create user in Tenant B
        user_b = User(
            id=uuid.uuid4(),
            tenant_id=tenant_b.id,
            email="creator_b@test.com",
            password_hash="hashed",
            role="admin",
            status="active",
        )
        db_session.add(user_b)
        await db_session.commit()

        # Create flow in Tenant B
        flow_b = Flow(
            id=uuid.uuid4(),
            tenant_id=tenant_b.id,
            user_id=user_b.id,
            name="Flow B",
            nodes=[{"id": "node1", "type": "input"}],
            edges=[],
            status="published",
        )
        db_session.add(flow_b)
        await db_session.commit()

        # Query flows in Tenant B
        result_b = await db_session.execute(text("SELECT * FROM flows"))
        flows_b = result_b.fetchall()
        assert len(flows_b) == 1
        assert flows_b[0].name == "Flow B"

        # Verify Flow A is not accessible in Tenant B
        flow_a_in_b = await db_session.execute(
            text("SELECT * FROM flows WHERE name = 'Flow A'")
        )
        assert flow_a_in_b.fetchone() is None

    @pytest.mark.asyncio
    async def test_schema_switching_via_middleware(self, client, test_tenants):
        """Test that tenant context switching via middleware works correctly."""
        tenant_a, tenant_b = test_tenants

        # Create admin users for both tenants
        # (In real implementation, this would be done via registration endpoint)

        # Login as Tenant A user
        response_a = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin_a@test.com", "password": "password"},
        )
        assert response_a.status_code == 200
        token_a = response_a.json()["access_token"]

        # Create flow in Tenant A
        response_create_a = await client.post(
            "/api/v1/flows",
            json={
                "name": "Tenant A Flow",
                "description": "Flow for tenant A",
                "nodes": [{"id": "n1", "type": "input"}],
                "edges": [],
            },
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert response_create_a.status_code == 201
        flow_a_id = response_create_a.json()["id"]

        # Login as Tenant B user
        response_b = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin_b@test.com", "password": "password"},
        )
        assert response_b.status_code == 200
        token_b = response_b.json()["access_token"]

        # Try to access Tenant A's flow with Tenant B's token
        response_forbidden = await client.get(
            f"/api/v1/flows/{flow_a_id}",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        # Should return 404 (not found) since flow doesn't exist in Tenant B's schema
        assert response_forbidden.status_code == 404

        # Verify Tenant B can't see Tenant A's flows in list
        response_list_b = await client.get(
            "/api/v1/flows", headers={"Authorization": f"Bearer {token_b}"}
        )
        assert response_list_b.status_code == 200
        flows_b = response_list_b.json()["flows"]
        assert len(flows_b) == 0  # Should see no flows

        # Verify Tenant A can still access their own flow
        response_get_a = await client.get(
            f"/api/v1/flows/{flow_a_id}",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert response_get_a.status_code == 200
        assert response_get_a.json()["name"] == "Tenant A Flow"

    @pytest.mark.asyncio
    async def test_tenant_quotas_enforcement(self, db_session, test_tenants):
        """Test that tenant quotas are enforced per schema."""
        tenant_a, tenant_b = test_tenants

        # Set low quota for Tenant A
        tenant_a.quotas = {"max_flows": 2}
        await db_session.commit()

        set_tenant_context(tenant_a.id, tenant_a.db_schema)

        # Create user
        user = User(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            email="quota_test@test.com",
            password_hash="hashed",
            role="admin",
            status="active",
        )
        db_session.add(user)
        await db_session.commit()

        # Create 2 flows (within quota)
        for i in range(2):
            flow = Flow(
                id=uuid.uuid4(),
                tenant_id=tenant_a.id,
                user_id=user.id,
                name=f"Flow {i}",
                nodes=[],
                edges=[],
                status="published",
            )
            db_session.add(flow)
        await db_session.commit()

        # Try to create 3rd flow (should fail quota check)
        from src.services.flow_service import FlowService

        flow_service = FlowService(db_session)

        with pytest.raises(Exception, match="quota exceeded"):
            await flow_service.create_flow(
                tenant_id=tenant_a.id,
                user_id=user.id,
                name="Flow 3",
                nodes=[],
                edges=[],
            )

    @pytest.mark.asyncio
    async def test_concurrent_multi_tenant_requests(
        self, db_session, test_tenants, asyncio
    ):
        """Test that concurrent requests to different tenants don't interfere."""
        tenant_a, tenant_b = test_tenants

        async def create_user_in_tenant(tenant, email):
            """Helper to create user in specific tenant."""
            set_tenant_context(tenant.id, tenant.db_schema)
            user = User(
                id=uuid.uuid4(),
                tenant_id=tenant.id,
                email=email,
                password_hash="hashed",
                role="admin",
                status="active",
            )
            db_session.add(user)
            await db_session.commit()
            return user

        # Create users concurrently in both tenants
        results = await asyncio.gather(
            create_user_in_tenant(tenant_a, "concurrent_a@test.com"),
            create_user_in_tenant(tenant_b, "concurrent_b@test.com"),
        )

        assert len(results) == 2

        # Verify each user exists only in their own tenant
        set_tenant_context(tenant_a.id, tenant_a.db_schema)
        result_a = await db_session.execute(
            text("SELECT email FROM users WHERE email = 'concurrent_a@test.com'")
        )
        assert result_a.fetchone() is not None

        result_b_in_a = await db_session.execute(
            text("SELECT email FROM users WHERE email = 'concurrent_b@test.com'")
        )
        assert result_b_in_a.fetchone() is None

        set_tenant_context(tenant_b.id, tenant_b.db_schema)
        result_b = await db_session.execute(
            text("SELECT email FROM users WHERE email = 'concurrent_b@test.com'")
        )
        assert result_b.fetchone() is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
