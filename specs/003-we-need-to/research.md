# Research: Platform Infrastructure Enhancements

**Feature**: Platform Infrastructure Enhancements
**Branch**: `003-we-need-to`
**Date**: 2025-10-12

## Overview

This document captures research findings and technical decisions for five major platform enhancements:
1. Authorization Service (hybrid RBAC+ABAC)
2. UUID Migration (Integer → UUID for all entities)
3. Async Task Execution (Celery + Redis message queue)
4. Notification System (WebSocket + persistent storage)
5. Tenant Management (super admin approval workflow)

---

## 1. UUID Strategy

### Problem
Current system uses auto-incrementing integers as primary keys. Requirements:
- Non-guessable IDs (prevent enumeration attacks)
- Sortable by creation time (preserve ordering semantics)
- PostgreSQL-optimized (existing database)
- URL-safe representation

### Options Evaluated

#### Option A: UUIDv4 (Random)
- ✅ Non-guessable, cryptographically secure
- ✅ Standard library support
- ❌ Not sortable (random distribution)
- ❌ Poor database index performance (random inserts)
- ❌ No temporal information

#### Option B: UUIDv7 (Time-ordered)
- ✅ Sortable by timestamp (maintains ordering)
- ✅ Good database performance (sequential-ish inserts)
- ✅ Non-guessable (includes random component)
- ✅ PostgreSQL BTREE index friendly
- ⚠️ Requires external library (Python <=3.11, native in 3.12+)

#### Option C: ULID (Universally Unique Lexicographically Sortable Identifier)
- ✅ Sortable, time-ordered
- ✅ Base32 encoded (more compact than hex UUID)
- ✅ Case-insensitive
- ❌ Non-standard (requires third-party library)
- ❌ Less PostgreSQL ecosystem support
- ❌ Not native UUID type

### Decision: **UUIDv7**

**Rationale**:
- Best balance of sortability, security, and PostgreSQL compatibility
- Native UUID type support in PostgreSQL (efficient storage, indexing)
- Python 3.11: Use `uuid6` library (`uuid6.uuid7()`)
- Python 3.12+: Native support (`uuid.uuid7()`)
- Maintains creation-time ordering for debugging and querying
- Standard RFC 9562 specification

**Implementation Notes**:
- Add `uuid6` to requirements.txt for Python 3.11
- SQLAlchemy: Use `postgresql.UUID(as_uuid=True)` column type
- API responses: Serialize as string (RFC 4122 format)
- Frontend: Store as string, display as-is or shortened

---

## 2. Authorization Framework

### Problem
Implement hybrid RBAC+ABAC authorization with:
- Resource-level permissions (can access Crew X)
- Action-level permissions (can execute/edit/delete)
- Field-level permissions (hide sensitive fields)
- Tenant-level policies (apply to all users)
- User-level policies (override tenant policies)
- Permission inheritance (Crew access → Task access)

### Options Evaluated

#### Option A: Casbin (PERM/RBAC/ABAC engine)
- ✅ Supports hybrid RBAC+ABAC
- ✅ Policy-as-code (declarative)
- ✅ Python adapter available
- ✅ Tenant isolation via adapters
- ❌ Learning curve (policy DSL)
- ❌ Complex permission inheritance requires custom logic
- ❌ Performance concerns with large policy sets

#### Option B: Open Policy Agent (OPA)
- ✅ Powerful Rego policy language
- ✅ Supports complex ABAC scenarios
- ✅ Excellent for auditing
- ❌ Requires separate service (Go binary)
- ❌ Network latency for policy checks
- ❌ Overkill for current scale

#### Option C: Custom Hybrid Model
- ✅ Full control over logic
- ✅ Direct database access (fast queries)
- ✅ Tailored to exact requirements
- ✅ No external dependencies
- ⚠️ Must implement permission caching
- ⚠️ Requires careful design for scalability

### Decision: **Custom Hybrid RBAC+ABAC**

**Rationale**:
- Performance critical (<50ms requirement)
- Direct PostgreSQL queries faster than external policy engines
- Permission inheritance requires custom logic anyway
- Can leverage existing Redis for caching
- Simpler deployment (no additional services)

**Design**:
```
1. Permission Check Flow:
   - Check Redis cache first (TTL: 5 minutes)
   - If miss: Query PostgreSQL:
     a. Load user roles
     b. Load tenant policies
     c. Load user-specific policies
     d. Apply inheritance rules
     e. Evaluate deny/allow precedence
   - Cache result in Redis
   - Return decision + reason

2. Data Model:
   - Permission: subject (user/role), resource, action, effect (allow/deny)
   - Role: collection of permissions
   - Policy: tenant/user-level rules with pattern matching
   - AuthorizationAuditLog: all decisions logged

3. Evaluation Logic:
   - User-level DENY takes precedence (highest priority)
   - Then user-level ALLOW
   - Then tenant-level DENY
   - Then tenant-level ALLOW
   - Default: DENY (secure by default)
```

**Implementation Libraries**:
- No external authz library
- Use SQLAlchemy for permission queries
- Use Redis for caching (via existing connection pool)
- Custom service: `AuthorizationService`

---

## 3. Celery + Message Queue Configuration

### Problem
Implement async task execution with:
- Pluggable backend (Redis, RabbitMQ, Kafka, SQS)
- Distributed workers
- Priority queues
- Rate limiting per tenant/user
- Retries with exponential backoff
- Dead letter queue
- Prometheus metrics

### Options Evaluated

#### Option A: Celery + Redis Broker
- ✅ Redis already in stack
- ✅ Simple setup, no new infrastructure
- ✅ Celery mature, well-documented
- ⚠️ Redis not ideal for large queues (in-memory)
- ⚠️ Limited durability guarantees

#### Option B: Celery + RabbitMQ Broker
- ✅ Durable, disk-based
- ✅ Better for high-volume queues
- ✅ Native priority queue support
- ❌ Adds new infrastructure dependency
- ❌ More complex deployment

#### Option C: Celery + Redis Streams
- ✅ Better than Redis list-based broker
- ✅ Persistent, log-structured
- ✅ Consumer groups for scaling
- ✅ Already using Redis
- ⚠️ Requires Redis 6+ (check current version)

### Decision: **Celery + Redis Streams** (primary), **pluggable abstraction layer**

**Rationale**:
- Redis 6+ already deployed (from docker-compose.yml)
- Redis Streams provide persistence + consumer groups
- Pluggable design allows future migration to RabbitMQ/Kafka
- Simplifies deployment (no new services for MVP)
- Performance sufficient for 100 concurrent executions/tenant

**Configuration**:
```python
# celery_config.py
broker_url = 'redis://redis:6379/0'
broker_transport_options = {
    'queue_order_strategy': 'priority',  # Priority support
}
result_backend = 'redis://redis:6379/1'  # Separate Redis DB for results

# Task settings
task_acks_late = True  # Acknowledge after completion
worker_prefetch_multiplier = 1  # One task per worker at a time
task_reject_on_worker_lost = True  # Requeue if worker crashes

# Retry configuration
task_autoretry_for = (Exception,)  # Auto-retry on any exception
task_retry_kwargs = {'max_retries': 3}
task_retry_backoff = 2  # Exponential backoff base
task_retry_backoff_max = 30  # Cap at 30 seconds
task_retry_jitter = True  # Add random jitter

# Timeouts
task_soft_time_limit = 1800  # 30 minutes soft limit
task_time_limit = 1900  # 31 minutes hard limit

# Rate limiting
task_annotations = {
    '*': {'rate_limit': '10/m'}  # Global default
}
```

**Pluggable Abstraction**:
```python
# backend/src/services/message_queue/base.py
class MessageQueueBackend(ABC):
    @abstractmethod
    def submit_task(self, task_name, args, kwargs, priority): pass

    @abstractmethod
    def get_task_status(self, task_id): pass

    @abstractmethod
    def cancel_task(self, task_id): pass

# Implementations:
# - RedisBackend (Celery + Redis Streams)
# - RabbitMQBackend (future)
# - KafkaBackend (future)
```

**Worker Deployment**:
- Separate container: `celery-worker`
- Environment-based scaling: `docker-compose scale celery-worker=5`
- Flower dashboard for monitoring (optional)

**Dead Letter Queue**:
```python
# Use Celery signals
from celery.signals import task_failure

@task_failure.connect
def handle_task_failure(sender, task_id, exception, args, kwargs, **kw):
    # Push to Redis list 'dlq:tasks'
    redis_client.lpush('dlq:tasks', json.dumps({
        'task_id': task_id,
        'task_name': sender.name,
        'exception': str(exception),
        'args': args,
        'kwargs': kwargs,
        'timestamp': datetime.utcnow().isoformat(),
    }))
```

---

## 4. WebSocket Notification Architecture

### Problem
Real-time notification delivery with:
- WebSocket connections for active users
- Persistent storage for offline users
- Connection management (reconnection, heartbeat)
- Notification preferences (user + tenant level)
- Retention policy (90 days default)

### Options Evaluated

#### Option A: FastAPI Native WebSocket
- ✅ Built into FastAPI, no dependencies
- ✅ Simple async/await API
- ✅ Integration with existing middleware
- ❌ Basic features only
- ❌ Must implement reconnection logic
- ❌ No room/channel abstraction

#### Option B: Socket.IO (python-socketio)
- ✅ Rich feature set (rooms, namespaces)
- ✅ Automatic reconnection
- ✅ Fallback to long-polling
- ❌ Requires Socket.IO client library (frontend)
- ❌ Heavier protocol overhead
- ❌ Another dependency

#### Option C: FastAPI WebSocket + Redis Pub/Sub
- ✅ FastAPI native WebSocket
- ✅ Redis pub/sub for broadcasting
- ✅ Scales horizontally (multiple backend instances)
- ✅ Already using Redis
- ⚠️ Must implement reconnection (client-side)

### Decision: **FastAPI WebSocket + Redis Pub/Sub**

**Rationale**:
- Leverages existing FastAPI + Redis stack
- No additional frontend dependencies (native WebSocket API)
- Redis pub/sub enables multi-server broadcasting
- Clean separation: WebSocket for transport, Redis for routing

**Architecture**:
```
[User Browser] <--WebSocket--> [FastAPI Backend] <--Pub/Sub--> [Redis] <--Pub/Sub--> [Celery Workers]
                                      |
                                      v
                                [PostgreSQL: notifications table]
```

**Flow**:
1. User connects: `ws://localhost:8000/ws/notifications?token=<jwt>`
2. Backend authenticates, subscribes to Redis channel: `notifications:user:{user_id}`
3. Event occurs (e.g., execution completes):
   - Worker publishes to Redis: `notifications:user:{user_id}`
   - Backend receives via pub/sub, forwards to WebSocket
   - Also saves to PostgreSQL for offline delivery
4. User disconnects: Unsubscribe from Redis channel
5. User reconnects: Fetch unread notifications from PostgreSQL, then resume WebSocket

**Connection Management**:
```python
# backend/src/api/websockets/notifications.py
@router.websocket("/ws/notifications")
async def notifications_websocket(websocket: WebSocket, token: str):
    # Authenticate
    user = await authenticate_ws_token(token)
    await websocket.accept()

    # Subscribe to Redis channel
    channel = f"notifications:user:{user.id}"
    pubsub = redis_client.pubsub()
    pubsub.subscribe(channel)

    try:
        # Heartbeat + message loop
        while True:
            # Check for Redis messages (non-blocking)
            message = pubsub.get_message(timeout=0.1)
            if message and message['type'] == 'message':
                await websocket.send_json(json.loads(message['data']))

            # Heartbeat every 30 seconds
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        pubsub.unsubscribe(channel)
```

**Frontend Reconnection**:
```typescript
// frontend/src/lib/websocket/notifications.ts
class NotificationWebSocket {
    private ws: WebSocket | null = null;
    private reconnectAttempts = 0;
    private maxReconnectAttempts = 10;

    connect() {
        this.ws = new WebSocket(`ws://localhost:8000/ws/notifications?token=${getJWT()}`);

        this.ws.onclose = () => {
            if (this.reconnectAttempts < this.maxReconnectAttempts) {
                setTimeout(() => {
                    this.reconnectAttempts++;
                    this.connect();
                }, Math.min(1000 * 2 ** this.reconnectAttempts, 30000)); // Exponential backoff, max 30s
            }
        };

        this.ws.onmessage = (event) => {
            const notification = JSON.parse(event.data);
            this.handleNotification(notification);
        };
    }
}
```

---

## 5. Prometheus Integration

### Problem
Monitor system health with metrics:
- Queue depth, processing rate, failure rate
- Authorization check latency
- WebSocket connection count
- Notification delivery success rate

### Options Evaluated

#### Option A: prometheus-fastapi-instrumentator
- ✅ FastAPI-specific, automatic instrumentation
- ✅ HTTP request metrics out-of-box
- ✅ Easy integration
- ⚠️ Limited custom metric support

#### Option B: prometheus-client (official)
- ✅ Official Prometheus client
- ✅ Full control over metrics
- ✅ Custom collectors
- ⚠️ Manual instrumentation

### Decision: **prometheus-client** + **prometheus-fastapi-instrumentator**

**Rationale**:
- Use instrumentator for automatic HTTP metrics
- Use prometheus-client for custom business metrics
- Best of both worlds

**Custom Metrics**:
```python
from prometheus_client import Counter, Histogram, Gauge

# Authorization metrics
authz_checks_total = Counter(
    'authz_checks_total',
    'Total authorization checks',
    ['decision']  # allow/deny
)

authz_check_latency = Histogram(
    'authz_check_latency_seconds',
    'Authorization check latency',
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5)
)

# Queue metrics
queue_depth = Gauge('queue_depth', 'Current queue depth', ['tenant_id'])
queue_processing_rate = Counter('queue_processed_total', 'Total tasks processed')
queue_failures = Counter('queue_failures_total', 'Total task failures')

# Notification metrics
notification_delivery_success = Counter(
    'notification_delivery_success_total',
    'Successful notification deliveries',
    ['channel']  # websocket/database
)

websocket_connections = Gauge('websocket_connections_active', 'Active WebSocket connections')
```

**Endpoint**:
- Expose metrics at `/metrics`
- Scrape interval: 15 seconds (Prometheus default)

---

## 6. Database Migration Strategy

### Problem
Convert all entity primary keys from Integer → UUID atomically with:
- Zero data loss
- Preserve all foreign key relationships
- Rollback capability
- Sample data loading

### Migration Approach

**Tool**: Alembic (already in use)

**Strategy**: Single migration with transaction

```python
# alembic/versions/xxxx_migrate_to_uuid.py
def upgrade():
    # 1. Create UUID extension if not exists
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # 2. Add new UUID columns to all tables
    op.add_column('users', sa.Column('uuid', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('tenants', sa.Column('uuid', postgresql.UUID(as_uuid=True), nullable=True))
    # ... repeat for all 20+ tables

    # 3. Generate UUIDs for existing rows (UUIDv7-ish: timestamp-based)
    op.execute("""
        UPDATE users SET uuid = uuid_generate_v4();
        UPDATE tenants SET uuid = uuid_generate_v4();
        -- ... repeat for all tables
    """)

    # 4. Create mapping tables for foreign key updates
    op.execute("""
        CREATE TEMP TABLE user_id_mapping AS
        SELECT id AS old_id, uuid AS new_uuid FROM users;
        -- ... repeat for all tables
    """)

    # 5. Add new UUID foreign key columns
    op.add_column('agents', sa.Column('tenant_uuid', postgresql.UUID(as_uuid=True), nullable=True))
    # ... repeat for all foreign keys

    # 6. Populate UUID foreign keys using mapping tables
    op.execute("""
        UPDATE agents a
        SET tenant_uuid = m.new_uuid
        FROM user_id_mapping m
        WHERE a.tenant_id = m.old_id;
        -- ... repeat for all foreign keys
    """)

    # 7. Drop old integer columns and constraints
    op.drop_constraint('agents_tenant_id_fkey', 'agents')
    op.drop_column('agents', 'tenant_id')
    # ... repeat for all foreign keys

    # 8. Rename UUID columns to remove '_uuid' suffix
    op.alter_column('users', 'uuid', new_column_name='id')
    op.alter_column('agents', 'tenant_uuid', new_column_name='tenant_id')
    # ... repeat for all columns

    # 9. Recreate foreign key constraints
    op.create_foreign_key('agents_tenant_id_fkey', 'agents', 'tenants', ['tenant_id'], ['id'])
    # ... repeat for all foreign keys

    # 10. Set columns NOT NULL
    op.alter_column('users', 'id', nullable=False)
    # ... repeat for all tables

    # 11. Create primary key constraints
    op.create_primary_key('users_pkey', 'users', ['id'])
    # ... repeat for all tables

def downgrade():
    # Rollback not supported (data loss risk)
    raise NotImplementedError("UUID migration cannot be automatically rolled back")
```

**Testing**:
1. Run migration on test database with sample data
2. Verify all IDs converted, relationships preserved
3. Run API tests to ensure UUID handling works
4. Benchmark query performance (should be similar or better)

**Deployment**:
1. Take database backup
2. Put system in maintenance mode (brief downtime acceptable per requirements)
3. Run migration
4. Restart backend services
5. Verify system health
6. If issues: Restore from backup

---

## 7. Sample Data Strategy

### Problem
Provide functional sample data for approved tenants showcasing:
- Crews with agents and tasks
- Flows with multiple steps
- Prompts with variables
- Tool integrations
- Realistic execution history

### Approach

**Sample Data Seeder**: `backend/src/scripts/seed_sample_data.py`

**Contents**:
1. **3 Sample Crews**:
   - "Content Marketing Team": Writer, SEO Specialist, Editor agents
   - "Data Analysis Team": Data Scientist, Analyst, Visualizer agents
   - "Customer Support Team": Triager, Resolver, Escalator agents

2. **5 Sample Flows**:
   - "Blog Post Creation": Research → Draft → Edit → Publish
   - "Data Pipeline": Extract → Transform → Analyze → Report
   - "Customer Inquiry": Receive → Classify → Respond → Follow-up
   - "Code Review": Submit → Analyze → Suggest → Approve
   - "Marketing Campaign": Plan → Create → Schedule → Monitor

3. **10 Sample Prompts**:
   - "Write Blog Post" (variables: topic, tone, length)
   - "Analyze Dataset" (variables: data_source, metrics)
   - "Respond to Customer" (variables: inquiry, sentiment)
   - "Review Code" (variables: language, pr_url)
   - "Create Social Media Post" (variables: platform, topic)
   - etc.

4. **5 Sample Tools**:
   - Web Search Tool
   - SQL Query Tool
   - File Upload Tool
   - API Call Tool
   - Calculator Tool

5. **10 Sample Executions** (historical):
   - Mix of successful, failed, and timeout executions
   - Demonstrate various crew configurations
   - Provide realistic execution times

**Implementation**:
```python
def seed_sample_data(tenant_id: UUID, db: Session):
    # Create sample LLM provider
    provider = LLMProvider(
        tenant_id=tenant_id,
        name="Sample GPT-4 Provider",
        provider_type=LLMProviderType.OPENAI,
        model_name="gpt-4",
        api_key="<insert-your-key>",
        is_active=True,
    )
    db.add(provider)

    # Create sample tools
    tools = create_sample_tools(tenant_id, db)

    # Create sample agents
    agents = create_sample_agents(tenant_id, provider.id, tools, db)

    # Create sample crews
    crews = create_sample_crews(tenant_id, agents, db)

    # Create sample flows
    flows = create_sample_flows(tenant_id, crews, db)

    # Create sample prompts
    prompts = create_sample_prompts(tenant_id, db)

    # Create sample executions
    create_sample_executions(tenant_id, crews, flows, db)

    db.commit()
```

---

## 8. Redis Connection Pooling

### Current State
From `docker-compose.yml`: Redis 7-alpine already running on port 6379.

### Configuration
```python
# backend/src/db/redis.py
import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool

# Connection pool for general use
redis_pool = ConnectionPool(
    host='redis',
    port=6379,
    db=0,
    max_connections=50,
    decode_responses=True,
)

# Connection pool for pub/sub (separate to avoid blocking)
redis_pubsub_pool = ConnectionPool(
    host='redis',
    port=6379,
    db=0,
    max_connections=20,
    decode_responses=True,
)

async def get_redis() -> redis.Redis:
    return redis.Redis(connection_pool=redis_pool)

async def get_redis_pubsub() -> redis.Redis:
    return redis.Redis(connection_pool=redis_pubsub_pool)
```

---

## Summary of Decisions

| Area | Decision | Key Rationale |
|------|----------|---------------|
| **UUID Strategy** | UUIDv7 | Sortable, PostgreSQL-optimized, secure |
| **Authorization** | Custom Hybrid RBAC+ABAC | Performance, control, no external services |
| **Message Queue** | Celery + Redis Streams | Leverage existing Redis, pluggable design |
| **WebSocket** | FastAPI native + Redis Pub/Sub | Simple, scalable, no extra dependencies |
| **Monitoring** | Prometheus (client + instrumentator) | Comprehensive metrics, standard tooling |
| **Migration** | Alembic single transaction | Atomic, rollback-capable (via backup) |
| **Sample Data** | Seeder script with 3 crews, 5 flows, 10 prompts | Showcase all features realistically |

---

## Risks and Mitigations

### Risk 1: UUID Migration Failure
**Mitigation**: Full database backup before migration, thorough testing on staging environment, ability to restore from backup within 1 hour.

### Risk 2: Redis Single Point of Failure
**Mitigation**: Redis Sentinel or Redis Cluster for production (documented, not implemented in MVP), graceful degradation (queue submissions fail fast, notifications stored in DB).

### Risk 3: Authorization Performance
**Mitigation**: Aggressive caching (5-minute TTL), database query optimization (indexes on permission lookups), load testing to validate <50ms requirement.

### Risk 4: WebSocket Scalability
**Mitigation**: Redis pub/sub enables horizontal scaling (multiple backend instances), connection limits per backend instance, documented scaling playbook.

### Risk 5: Celery Worker Overload
**Mitigation**: Rate limiting per tenant (enforced before queuing), worker autoscaling based on queue depth, timeout enforcement (soft + hard limits).

---

## Next Steps

1. **Phase 1**: Create data models and API contracts based on these decisions
2. **Proof of Concept**: Build small prototypes for UUID migration, authorization checks, and WebSocket connections
3. **Load Testing**: Validate performance assumptions (authz <50ms, queue <200ms, notifications <1s)
4. **Documentation**: Update architecture diagrams and deployment guides

---
