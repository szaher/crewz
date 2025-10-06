# Multi-Tenancy Architecture Guide

## Overview

The Dynamic CrewAI Orchestration Platform implements a **schema-per-tenant** multi-tenancy model for PostgreSQL and a **collection-per-tenant** model for MongoDB. This approach provides strong data isolation while maintaining operational efficiency.

## Why Schema-per-Tenant?

### Comparison of Multi-Tenancy Approaches

| Approach | Isolation | Performance | Scalability | Complexity |
|----------|-----------|-------------|-------------|------------|
| **Shared Schema** | ⭐ Low | ⭐⭐⭐ High | ⭐⭐⭐ High | ⭐ Low |
| **Schema-per-Tenant** | ⭐⭐⭐ High | ⭐⭐ Medium | ⭐⭐ Medium | ⭐⭐ Medium |
| **Database-per-Tenant** | ⭐⭐⭐ Highest | ⭐ Low | ⭐ Low | ⭐⭐⭐ High |

### Our Choice: Schema-per-Tenant

**Advantages:**
- ✅ **Strong Isolation**: Each tenant has a dedicated schema, preventing SQL injection across tenants
- ✅ **Security**: Schema-level permissions prevent cross-tenant data access
- ✅ **Compliance**: Easier to meet regulatory requirements (GDPR, HIPAA)
- ✅ **Backup/Restore**: Can backup/restore individual tenants
- ✅ **Migration**: Schema migrations can be applied per-tenant
- ✅ **Cost-Effective**: Single database instance serves all tenants

**Trade-offs:**
- ⚠️ **Connection Management**: Requires setting `search_path` per request
- ⚠️ **Migrations**: Must migrate all tenant schemas
- ⚠️ **Resource Limits**: All tenants share database resources

## Database Architecture

### PostgreSQL Schema Design

```sql
-- ================================================
-- PUBLIC SCHEMA: Shared tenant metadata
-- ================================================

CREATE SCHEMA IF NOT EXISTS public;

-- Tenants table (shared across all tenants)
CREATE TABLE public.tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    db_schema VARCHAR(100) UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Users table (shared, with tenant_id foreign key)
CREATE TABLE public.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'member',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, email)
);

CREATE INDEX idx_users_tenant_id ON public.users(tenant_id);
CREATE INDEX idx_users_email ON public.users(email);


-- ================================================
-- TENANT TEMPLATE SCHEMA: Blueprint for new tenants
-- ================================================

CREATE SCHEMA IF NOT EXISTS tenant_template;

-- Agents table
CREATE TABLE tenant_template.agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(255) NOT NULL,
    goal TEXT NOT NULL,
    backstory TEXT,
    llm_provider_id UUID,
    allow_delegation BOOLEAN DEFAULT false,
    verbose BOOLEAN DEFAULT true,
    config JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_agents_tenant_id ON tenant_template.agents(tenant_id);
CREATE INDEX idx_agents_llm_provider ON tenant_template.agents(llm_provider_id);

-- LLM Providers table
CREATE TABLE tenant_template.llm_providers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    provider_type VARCHAR(50) NOT NULL,
    config JSONB NOT NULL,
    priority INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT true,
    encrypted_credentials BYTEA,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_llm_providers_tenant_id ON tenant_template.llm_providers(tenant_id);
CREATE INDEX idx_llm_providers_priority ON tenant_template.llm_providers(priority);

-- Crews table
CREATE TABLE tenant_template.crews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    process VARCHAR(50) DEFAULT 'sequential',
    verbose BOOLEAN DEFAULT true,
    config JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_crews_tenant_id ON tenant_template.crews(tenant_id);

-- Crew-Agent association table
CREATE TABLE tenant_template.crew_agents (
    crew_id UUID NOT NULL REFERENCES tenant_template.crews(id) ON DELETE CASCADE,
    agent_id UUID NOT NULL REFERENCES tenant_template.agents(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    PRIMARY KEY (crew_id, agent_id)
);

-- Flows table
CREATE TABLE tenant_template.flows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    definition JSONB NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_flows_tenant_id ON tenant_template.flows(tenant_id);
CREATE INDEX idx_flows_is_active ON tenant_template.flows(is_active);

-- Executions table
CREATE TABLE tenant_template.executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    flow_id UUID NOT NULL REFERENCES tenant_template.flows(id),
    user_id UUID NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    inputs JSONB,
    outputs JSONB,
    error TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_executions_tenant_id ON tenant_template.executions(tenant_id);
CREATE INDEX idx_executions_flow_id ON tenant_template.executions(flow_id);
CREATE INDEX idx_executions_status ON tenant_template.executions(status);
CREATE INDEX idx_executions_created_at ON tenant_template.executions(created_at DESC);

-- Tools table
CREATE TABLE tenant_template.tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    docker_image VARCHAR(255) NOT NULL,
    schema JSONB NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_tools_tenant_id ON tenant_template.tools(tenant_id);
CREATE INDEX idx_tools_is_active ON tenant_template.tools(is_active);
```

### MongoDB Collection Design

```javascript
// ================================================
// EXECUTION LOGS COLLECTION
// ================================================

db.createCollection(`execution_logs_${tenantId}`, {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["execution_id", "level", "message", "timestamp"],
      properties: {
        execution_id: {
          bsonType: "string",
          description: "UUID of the execution"
        },
        node_id: {
          bsonType: "string",
          description: "Flow node that generated the log"
        },
        level: {
          enum: ["debug", "info", "warning", "error"],
          description: "Log level"
        },
        message: {
          bsonType: "string",
          description: "Log message"
        },
        metadata: {
          bsonType: "object",
          description: "Additional structured data"
        },
        timestamp: {
          bsonType: "date",
          description: "Log timestamp"
        }
      }
    }
  }
});

// Index for querying logs by execution
db[`execution_logs_${tenantId}`].createIndex(
  { execution_id: 1, timestamp: -1 }
);

// TTL index to auto-delete logs after 30 days
db[`execution_logs_${tenantId}`].createIndex(
  { timestamp: 1 },
  { expireAfterSeconds: 2592000 }  // 30 days
);


// ================================================
// CHAT MESSAGES COLLECTION
// ================================================

db.createCollection(`chat_messages_${tenantId}`, {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["conversation_id", "role", "content", "timestamp"],
      properties: {
        conversation_id: {
          bsonType: "string",
          description: "Conversation identifier"
        },
        role: {
          enum: ["user", "assistant", "system", "tool"],
          description: "Message sender role"
        },
        content: {
          bsonType: "string",
          description: "Message content"
        },
        tool_calls: {
          bsonType: "array",
          description: "Tool invocations in this message"
        },
        metadata: {
          bsonType: "object",
          description: "Additional metadata (tokens, cost, etc.)"
        },
        timestamp: {
          bsonType: "date"
        }
      }
    }
  }
});

db[`chat_messages_${tenantId}`].createIndex(
  { conversation_id: 1, timestamp: 1 }
);


// ================================================
// AUDIT LOGS COLLECTION
// ================================================

db.createCollection(`audit_logs_${tenantId}`, {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["user_id", "action", "resource_type", "timestamp"],
      properties: {
        user_id: {
          bsonType: "string",
          description: "User who performed the action"
        },
        action: {
          enum: ["create", "read", "update", "delete"],
          description: "Action performed"
        },
        resource_type: {
          bsonType: "string",
          description: "Type of resource (agent, flow, etc.)"
        },
        resource_id: {
          bsonType: "string",
          description: "ID of the affected resource"
        },
        changes: {
          bsonType: "object",
          description: "Before/after values"
        },
        ip_address: {
          bsonType: "string"
        },
        user_agent: {
          bsonType: "string"
        },
        timestamp: {
          bsonType: "date"
        }
      }
    }
  }
});

db[`audit_logs_${tenantId}`].createIndex(
  { user_id: 1, timestamp: -1 }
);

db[`audit_logs_${tenantId}`].createIndex(
  { resource_type: 1, resource_id: 1 }
);
```

## Tenant Lifecycle Management

### 1. Tenant Registration

```python
# backend/src/services/tenant_service.py

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

class TenantService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_tenant(
        self,
        name: str,
        slug: str,
        admin_email: str,
        admin_password: str
    ) -> Tenant:
        """
        Create a new tenant with isolated schema.

        Steps:
        1. Create tenant record in public.tenants
        2. Create dedicated schema for tenant
        3. Clone tenant_template schema structure
        4. Create admin user in public.users
        5. Initialize MongoDB collections
        """
        # Step 1: Create tenant record
        tenant_id = uuid.uuid4()
        db_schema = f"tenant_{tenant_id.hex[:8]}"

        tenant = Tenant(
            id=tenant_id,
            name=name,
            slug=slug,
            db_schema=db_schema,
            is_active=True
        )
        self.db.add(tenant)
        await self.db.flush()

        # Step 2: Create schema
        await self.db.execute(
            text(f"CREATE SCHEMA IF NOT EXISTS {db_schema}")
        )

        # Step 3: Clone tenant_template structure
        await self._clone_template_schema(db_schema)

        # Step 4: Create admin user
        from src.services.auth_service import AuthService
        auth_service = AuthService(self.db)
        admin_user = await auth_service.create_user(
            tenant_id=tenant_id,
            email=admin_email,
            password=admin_password,
            role="admin"
        )

        # Step 5: Initialize MongoDB collections
        await self._initialize_mongodb_collections(str(tenant_id))

        await self.db.commit()
        return tenant

    async def _clone_template_schema(self, target_schema: str):
        """Clone all tables from tenant_template to target schema."""
        tables = [
            "agents", "llm_providers", "crews", "crew_agents",
            "flows", "executions", "tools"
        ]

        for table in tables:
            # Create table structure
            await self.db.execute(text(f"""
                CREATE TABLE {target_schema}.{table}
                (LIKE tenant_template.{table} INCLUDING ALL)
            """))

            # Copy indexes
            await self.db.execute(text(f"""
                SELECT indexdef
                FROM pg_indexes
                WHERE schemaname = 'tenant_template'
                AND tablename = '{table}'
            """))
            # (Execute index creation for target schema)

    async def _initialize_mongodb_collections(self, tenant_id: str):
        """Create MongoDB collections for tenant."""
        from src.db.mongodb import get_mongodb_client

        client = get_mongodb_client()
        db = client.get_database()

        # Create collections with validation
        collections = [
            f"execution_logs_{tenant_id}",
            f"chat_messages_{tenant_id}",
            f"audit_logs_{tenant_id}"
        ]

        for collection_name in collections:
            await db.create_collection(
                collection_name,
                validator=self._get_collection_validator(collection_name)
            )
```

### 2. Request Context Switching

```python
# backend/src/middleware/tenant_middleware.py

from fastapi import Request, HTTPException
from sqlalchemy import text
from src.db import get_db

class TenantContextMiddleware:
    """
    Middleware to set PostgreSQL search_path based on tenant context.

    This ensures all queries automatically use the correct tenant schema.
    """

    async def __call__(self, request: Request, call_next):
        # Extract tenant from JWT token
        tenant_id = request.state.tenant_id  # Set by auth middleware

        if not tenant_id:
            raise HTTPException(status_code=401, detail="Tenant not identified")

        # Get tenant schema from database
        async with get_db() as db:
            result = await db.execute(
                text("SELECT db_schema FROM public.tenants WHERE id = :tenant_id"),
                {"tenant_id": tenant_id}
            )
            row = result.fetchone()

            if not row:
                raise HTTPException(status_code=404, detail="Tenant not found")

            db_schema = row[0]

            # Set search_path for this connection
            await db.execute(
                text(f"SET search_path TO {db_schema}, public")
            )

            # Store schema in request state for logging
            request.state.db_schema = db_schema

        response = await call_next(request)
        return response
```

### 3. SQLAlchemy Integration

```python
# backend/src/db/__init__.py

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager

DATABASE_URL = "postgresql+asyncpg://user:pass@localhost/crewai"

engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    echo=False
)

AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


@asynccontextmanager
async def get_tenant_db(tenant_schema: str):
    """
    Get a database session with tenant schema set.

    Usage:
        async with get_tenant_db("tenant_abc123") as db:
            agents = await db.execute(select(Agent))
    """
    async with AsyncSessionLocal() as session:
        # Set search_path for this session
        await session.execute(
            text(f"SET search_path TO {tenant_schema}, public")
        )

        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Global tenant context (set by middleware)
from contextvars import ContextVar

current_tenant_schema: ContextVar[str] = ContextVar("current_tenant_schema", default="public")

async def get_db():
    """
    Get database session with current tenant context.

    The tenant schema is set by TenantContextMiddleware.
    """
    schema = current_tenant_schema.get()
    async with get_tenant_db(schema) as db:
        yield db
```

## Data Isolation Verification

### SQL Injection Prevention

```python
# Example: Attempting to access another tenant's data

# ❌ INCORRECT: Vulnerable to SQL injection
async def get_agents_vulnerable(tenant_id: str, db: AsyncSession):
    # Attacker could pass: tenant_id = "'; DROP TABLE agents; --"
    query = f"SELECT * FROM agents WHERE tenant_id = '{tenant_id}'"
    result = await db.execute(text(query))
    return result.fetchall()

# ✅ CORRECT: Using ORM with search_path isolation
async def get_agents_secure(db: AsyncSession):
    # search_path is set to tenant schema by middleware
    # Query automatically uses correct schema
    result = await db.execute(select(Agent))
    return result.scalars().all()

# Even if attacker tries to inject SQL, they can't escape the schema:
# - SET search_path is executed with admin privileges
# - User queries run in isolated schema context
# - Cross-schema queries require explicit schema.table syntax
# - Permissions prevent cross-schema access
```

### Testing Data Isolation

```python
# backend/tests/integration/test_multi_tenancy.py

@pytest.mark.asyncio
async def test_cross_tenant_isolation(db_session: AsyncSession):
    """Verify that tenants cannot access each other's data."""

    # Create two tenants
    tenant_service = TenantService(db_session)

    tenant_a = await tenant_service.create_tenant(
        name="Tenant A",
        slug="tenant-a",
        admin_email="admin@tenanta.com",
        admin_password="password123"
    )

    tenant_b = await tenant_service.create_tenant(
        name="Tenant B",
        slug="tenant-b",
        admin_email="admin@tenantb.com",
        admin_password="password123"
    )

    # Create an agent in Tenant A's schema
    await db_session.execute(
        text(f"SET search_path TO {tenant_a.db_schema}, public")
    )

    agent_a = Agent(
        id=uuid.uuid4(),
        tenant_id=tenant_a.id,
        name="Agent A",
        role="researcher",
        goal="Research for Tenant A",
        backstory="I work for Tenant A"
    )
    db_session.add(agent_a)
    await db_session.commit()

    # Switch to Tenant B's schema
    await db_session.execute(
        text(f"SET search_path TO {tenant_b.db_schema}, public")
    )

    # Try to query agents (should only see Tenant B's agents)
    result = await db_session.execute(select(Agent))
    agents_in_b = result.scalars().all()

    # Verify isolation
    assert len(agents_in_b) == 0, "Tenant B should not see Tenant A's agents"

    # Explicitly try to query Tenant A's schema (should fail)
    with pytest.raises(Exception):
        await db_session.execute(
            text(f"SELECT * FROM {tenant_a.db_schema}.agents")
        )
```

## Schema Migration Strategy

### Alembic Configuration for Multi-Tenancy

```python
# backend/alembic/env.py

from alembic import context
from sqlalchemy import engine_from_config, pool, text
from src.models import Base

def run_migrations_online():
    """Run migrations in 'online' mode."""

    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # Get all tenant schemas
        result = connection.execute(
            text("SELECT db_schema FROM public.tenants WHERE is_active = true")
        )
        tenant_schemas = [row[0] for row in result.fetchall()]

        # Migrate tenant_template first
        schemas_to_migrate = ["tenant_template"] + tenant_schemas

        for schema in schemas_to_migrate:
            print(f"Migrating schema: {schema}")

            # Set search_path to target schema
            connection.execute(text(f"SET search_path TO {schema}, public"))

            # Run migrations
            context.configure(
                connection=connection,
                target_metadata=Base.metadata,
                version_table_schema=schema  # Store alembic_version in each schema
            )

            with context.begin_transaction():
                context.run_migrations()
```

### Creating a Migration

```bash
# Create a new migration
alembic revision -m "add_agent_version_field"

# Apply migrations to all tenant schemas
alembic upgrade head

# Rollback one version for all tenants
alembic downgrade -1
```

## Performance Considerations

### Connection Pooling

```python
# Optimal pool settings for schema-per-tenant

engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,           # Base pool size
    max_overflow=10,        # Additional connections under load
    pool_timeout=30,        # Wait time for available connection
    pool_recycle=3600,      # Recycle connections after 1 hour
    pool_pre_ping=True      # Verify connection health before use
)
```

**Calculation:**
- **Concurrent Requests**: 100
- **Average Request Duration**: 200ms
- **Requests per Second**: 100 / 0.2 = 500 RPS
- **Required Pool Size**: 100 / (1 / 0.2) = 20 connections

### Query Performance

```python
# ✅ GOOD: Single query with JOIN
async def get_flow_with_executions(flow_id: UUID, db: AsyncSession):
    result = await db.execute(
        select(Flow)
        .options(joinedload(Flow.executions))
        .where(Flow.id == flow_id)
    )
    return result.scalar_one()

# ❌ BAD: N+1 query problem
async def get_flow_with_executions_bad(flow_id: UUID, db: AsyncSession):
    flow = await db.get(Flow, flow_id)
    # This triggers a separate query for each execution
    executions = [await db.get(Execution, e.id) for e in flow.execution_ids]
    return flow
```

### Index Strategy

```sql
-- Create indexes on frequently queried columns

-- For WHERE tenant_id = ?
CREATE INDEX idx_agents_tenant_id ON agents(tenant_id);

-- For WHERE tenant_id = ? AND is_active = true
CREATE INDEX idx_flows_tenant_active ON flows(tenant_id, is_active);

-- For ORDER BY created_at DESC LIMIT 10
CREATE INDEX idx_executions_created_desc ON executions(created_at DESC);

-- For JOIN operations
CREATE INDEX idx_crew_agents_crew_id ON crew_agents(crew_id);
CREATE INDEX idx_crew_agents_agent_id ON crew_agents(agent_id);
```

## Monitoring and Observability

### Tenant-Level Metrics

```python
# backend/src/utils/observability.py

from prometheus_client import Counter, Histogram, Gauge

# Track requests per tenant
requests_per_tenant = Counter(
    "http_requests_per_tenant_total",
    "Total HTTP requests by tenant",
    ["tenant_id", "endpoint", "status"]
)

# Track execution time per tenant
execution_duration_per_tenant = Histogram(
    "flow_execution_duration_seconds",
    "Flow execution duration by tenant",
    ["tenant_id", "flow_id"]
)

# Track active users per tenant
active_users_per_tenant = Gauge(
    "active_users_per_tenant",
    "Number of active users per tenant",
    ["tenant_id"]
)
```

### Grafana Dashboard Queries

```promql
# Top 10 tenants by request volume
topk(10, sum by (tenant_id) (rate(http_requests_per_tenant_total[5m])))

# Tenant with highest error rate
topk(5,
  sum by (tenant_id) (rate(http_requests_per_tenant_total{status=~"5.."}[5m]))
  /
  sum by (tenant_id) (rate(http_requests_per_tenant_total[5m]))
)

# Average execution time per tenant
avg by (tenant_id) (flow_execution_duration_seconds)
```

## Security Best Practices

### 1. Always Use Parameterized Queries

```python
# ❌ NEVER do this
query = f"SELECT * FROM agents WHERE name = '{user_input}'"

# ✅ ALWAYS do this
query = select(Agent).where(Agent.name == user_input)
```

### 2. Validate Tenant Context

```python
# Verify tenant owns the resource before allowing access
async def get_agent(agent_id: UUID, tenant_id: UUID, db: AsyncSession):
    agent = await db.get(Agent, agent_id)

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    if agent.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    return agent
```

### 3. Schema Naming Convention

```python
# Use UUID-based schema names to prevent enumeration
db_schema = f"tenant_{uuid.uuid4().hex[:8]}"  # tenant_a3f2c1b9

# ❌ DON'T use predictable names
db_schema = f"tenant_{tenant_id}"  # Easy to guess
```

## Troubleshooting

### Issue: Queries returning empty results

**Cause**: `search_path` not set correctly

**Solution**:
```python
# Check current search_path
result = await db.execute(text("SHOW search_path"))
print(result.scalar())  # Should show: tenant_xxx, public

# Manually set search_path
await db.execute(text(f"SET search_path TO {correct_schema}, public"))
```

### Issue: Migrations failing for some tenants

**Cause**: Inconsistent schema state

**Solution**:
```bash
# Check alembic version for each tenant schema
psql -d crewai -c "SELECT schemaname, version_num FROM alembic_version"

# Manually stamp schema to specific version
alembic stamp <revision>
```

### Issue: Connection pool exhaustion

**Cause**: Too many concurrent tenants

**Solution**:
```python
# Increase pool size
engine = create_async_engine(
    DATABASE_URL,
    pool_size=50,  # Increased from 20
    max_overflow=20  # Increased from 10
)

# Or implement connection queueing
from asyncio import Semaphore

db_semaphore = Semaphore(100)  # Max 100 concurrent DB operations

async def get_db_with_limit():
    async with db_semaphore:
        async with get_db() as db:
            yield db
```

## Conclusion

The schema-per-tenant architecture provides strong data isolation while maintaining operational efficiency. Key takeaways:

1. **Isolation**: Each tenant has a dedicated PostgreSQL schema
2. **Security**: SQL injection cannot cross tenant boundaries
3. **Performance**: Connection pooling shared across all tenants
4. **Scalability**: Single database serves hundreds of tenants
5. **Compliance**: Easy to backup/restore individual tenant data

For implementation details, see:
- [Security Model](./security-model.md)
- [Local Development Guide](../guides/local-development.md)
