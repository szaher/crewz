# System Architecture Overview

## Introduction

The Dynamic CrewAI Orchestration Platform is a sophisticated multi-tenant SaaS application that enables users to create, manage, and execute AI-powered workflows using the CrewAI framework. This document provides a comprehensive overview of the system's architecture, design decisions, and key components.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend Layer                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Next.js UI  │  │ React Flow   │  │  WebSocket   │          │
│  │   (React)    │  │  (Canvas)    │  │   Client     │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        API Gateway Layer                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              FastAPI Application (Python)                │   │
│  │  • REST API (v1)  • WebSocket  • Authentication          │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Business Logic Layer                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │  Agent   │  │   Crew   │  │   Flow   │  │   Tool   │       │
│  │ Service  │  │ Service  │  │ Service  │  │ Service  │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Data Persistence Layer                     │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐            │
│  │ PostgreSQL  │  │   MongoDB    │  │    Redis    │            │
│  │ (Relational)│  │ (Documents)  │  │   (Cache)   │            │
│  └─────────────┘  └──────────────┘  └─────────────┘            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Execution & Integration Layer                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Docker DinD │  │     Celery   │  │  LLM Provider│          │
│  │  (Tools)     │  │  (Workers)   │  │  Integration │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Observability & Monitoring                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Prometheus   │  │   Grafana    │  │ OpenTelemetry│          │
│  │  (Metrics)   │  │ (Dashboards) │  │   (Traces)   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Frontend Application

**Technology Stack:**
- **Framework**: Next.js 14 with App Router
- **UI Library**: React 18 with TypeScript
- **Flow Editor**: React Flow (xyflow) for visual workflow creation
- **State Management**: React Context + TanStack Query
- **Styling**: Tailwind CSS + shadcn/ui components
- **Real-time**: WebSocket for execution streaming

**Key Features:**
- Server-side rendering (SSR) for improved SEO and performance
- Client-side routing with React Router
- Visual workflow editor with drag-and-drop
- Real-time execution monitoring
- Multi-tenant workspace isolation

**Architecture Patterns:**
- Component-based architecture
- Custom hooks for business logic
- API client layer for backend communication
- Optimistic UI updates with server reconciliation

### 2. Backend API (FastAPI)

**Technology Stack:**
- **Framework**: FastAPI (Python 3.11+)
- **ORM**: SQLAlchemy 2.0 with async support
- **Validation**: Pydantic v2
- **Authentication**: JWT with bcrypt
- **WebSocket**: FastAPI WebSocket support
- **Background Tasks**: Celery with Redis broker

**API Design:**
- RESTful API following OpenAPI 3.0 specification
- Versioned endpoints (`/api/v1/...`)
- Consistent error handling with problem details (RFC 7807)
- Request/response validation with Pydantic schemas
- Rate limiting and throttling

**Key Endpoints:**
```
POST   /api/v1/auth/register         - Tenant registration
POST   /api/v1/auth/login            - User authentication
GET    /api/v1/agents                - List agents
POST   /api/v1/agents                - Create agent
GET    /api/v1/flows                 - List flows
POST   /api/v1/flows                 - Create flow
POST   /api/v1/flows/{id}/execute    - Execute flow
GET    /api/v1/executions/{id}       - Get execution status
WS     /api/v1/ws/executions/{id}    - Real-time execution streaming
```

### 3. Multi-Tenant Data Layer

**PostgreSQL - Relational Data:**
- **Isolation Strategy**: Schema-per-tenant
- **Tenant Metadata**: Stored in public schema
- **Application Data**: Stored in tenant-specific schemas

**Schema Design:**
```sql
-- Public schema (shared)
tenants (id, slug, name, db_schema, created_at)
users (id, tenant_id, email, password_hash, role)

-- Tenant schemas (isolated per tenant: tenant_<id>)
agents (id, name, role, goal, backstory, llm_provider_id)
crews (id, name, description, process, agent_ids)
flows (id, name, description, definition, is_active)
executions (id, flow_id, status, inputs, outputs, started_at)
llm_providers (id, name, provider_type, config, priority)
tools (id, name, docker_image, schema, is_active)
```

**MongoDB - Document Data:**
- **Collections**: Organized by tenant ID prefix
- **Use Cases**: Execution logs, chat messages, audit trails

**Collections:**
```javascript
execution_logs_{tenant_id}  // Detailed execution logs with timestamps
chat_messages_{tenant_id}   // Real-time chat conversations
audit_logs_{tenant_id}      // System audit trail
```

**Redis - Caching Layer:**
- **Use Cases**: Session management, rate limiting, caching, pub/sub
- **Data Structures**: Strings (cache), Hashes (sessions), Sets (active users)

### 4. Flow Execution Engine

**Architecture:**
```
┌──────────────────────────────────────────────────────┐
│              Flow Execution Orchestrator             │
│                                                      │
│  1. Parse Flow Definition (DAG validation)          │
│  2. Resolve Dependencies (topological sort)         │
│  3. Initialize Agents (load configs)                │
│  4. Execute Nodes (sequential/parallel)             │
│  5. Stream Results (WebSocket)                      │
│  6. Handle Errors (retry/failover)                  │
└──────────────────────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────┐
│                 CrewAI Integration                   │
│                                                      │
│  • Convert flow nodes to CrewAI Tasks               │
│  • Assign agents to tasks                           │
│  • Execute with CrewAI Crew.kickoff()               │
│  • Capture intermediate results                     │
└──────────────────────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────┐
│              LLM Provider Failover                   │
│                                                      │
│  • Primary provider execution                       │
│  • Error detection (rate limit, timeout, etc.)      │
│  • Automatic failover to next priority provider     │
│  • Cost tracking and optimization                   │
└──────────────────────────────────────────────────────┘
```

**Execution Flow:**
1. **Flow Validation**: Validate DAG structure, check for cycles
2. **Node Resolution**: Determine execution order via topological sort
3. **Agent Initialization**: Load agent configurations and LLM providers
4. **Task Execution**: Execute nodes sequentially or in parallel
5. **Output Propagation**: Pass outputs from parent nodes to children
6. **Result Streaming**: Send real-time updates via WebSocket
7. **Completion**: Store final results and update execution status

### 5. Tool Execution System

**Docker-in-Docker Architecture:**
```
┌────────────────────────────────────────────────────┐
│           Sysbox Runtime Container                 │
│  ┌──────────────────────────────────────────────┐  │
│  │         Docker Daemon (Rootless)             │  │
│  │  ┌────────────────────────────────────────┐  │  │
│  │  │      User Tool Container               │  │  │
│  │  │  • Custom Python/Node.js code          │  │  │
│  │  │  • Environment isolation               │  │  │
│  │  │  • Resource limits (CPU/Memory)        │  │  │
│  │  │  • Network restrictions                │  │  │
│  │  └────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────┘
```

**Security Features:**
- Sysbox runtime for unprivileged containers
- Resource limits (CPU, memory, disk I/O)
- Network isolation (no internet access by default)
- Timeout enforcement
- Automatic cleanup after execution

**Tool Lifecycle:**
1. **Registration**: User uploads Dockerfile + JSON schema
2. **Build**: System builds Docker image with validation
3. **Storage**: Image stored in container registry
4. **Execution**: Container spawned with inputs
5. **Output Capture**: Results captured from stdout/files
6. **Cleanup**: Container destroyed after completion

### 6. Authentication & Authorization

**JWT-Based Authentication:**
```
┌─────────────────────────────────────────────────┐
│         User Login Request                      │
│  (email + password)                             │
└─────────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│      Password Verification (bcrypt)             │
│  • Hash comparison                              │
│  • Timing-safe check                            │
└─────────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│        JWT Token Generation                     │
│  Header: {"alg": "HS256", "typ": "JWT"}         │
│  Payload: {                                     │
│    "user_id": "...",                            │
│    "tenant_id": "...",                          │
│    "role": "admin",                             │
│    "exp": timestamp                             │
│  }                                              │
│  Signature: HMAC-SHA256(header.payload, secret) │
└─────────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│         Client Storage (HttpOnly Cookie)        │
│  • Secure flag (HTTPS only)                     │
│  • SameSite=Strict (CSRF protection)            │
│  • 24-hour expiration                           │
└─────────────────────────────────────────────────┘
```

**Role-Based Access Control (RBAC):**
- **Tenant Admin**: Full access to tenant resources
- **Member**: Read/write access to shared resources
- **Viewer**: Read-only access

**Permission Model:**
```python
permissions = {
    "admin": ["*"],  # All permissions
    "member": [
        "agents:read", "agents:write",
        "flows:read", "flows:write", "flows:execute",
        "executions:read"
    ],
    "viewer": [
        "agents:read", "flows:read", "executions:read"
    ]
}
```

### 7. Background Task Processing

**Celery Architecture:**
```
┌────────────────────────────────────────────────┐
│            FastAPI Application                 │
│  • Creates tasks via celery_app.send_task()    │
└────────────────────────────────────────────────┘
                  │
                  ▼
┌────────────────────────────────────────────────┐
│           Redis (Message Broker)               │
│  • Task queue storage                          │
│  • Result backend                              │
└────────────────────────────────────────────────┘
                  │
                  ▼
┌────────────────────────────────────────────────┐
│          Celery Worker Processes               │
│  • Concurrency: 4 workers                      │
│  • Task execution (flow processing)            │
│  • Retry logic (exponential backoff)           │
└────────────────────────────────────────────────┘
```

**Task Types:**
- **Flow Execution**: Long-running workflow execution
- **Tool Builds**: Docker image building
- **Cleanup**: Old execution cleanup
- **Notifications**: Email/webhook delivery

### 8. Observability Stack

**OpenTelemetry Integration:**
- **Traces**: Distributed tracing across services
- **Metrics**: Application and business metrics
- **Logs**: Structured logging with correlation IDs

**Metrics Collection:**
```python
# Custom application metrics
http_requests_total          # Total HTTP requests by endpoint/status
flow_executions_total        # Total flow executions by status
llm_api_calls_total          # LLM API calls by provider
llm_tokens_total             # Token usage by provider
docker_containers_active     # Active tool containers
cache_hits_total             # Redis cache hits/misses
```

**Prometheus Queries:**
```promql
# Request rate by endpoint
rate(http_requests_total[5m])

# Error rate
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])

# Average response time
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# LLM cost per hour
sum(rate(llm_tokens_total[1h])) * 0.00001  # Assuming $0.01/1K tokens
```

## Deployment Architecture

### Kubernetes Deployment

```
┌───────────────────────────────────────────────────────────────┐
│                      Kubernetes Cluster                       │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │               crewai-prod Namespace                     │  │
│  │                                                         │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │  │
│  │  │   Backend    │  │  Frontend    │  │   Workers    │ │  │
│  │  │ Deployment   │  │ Deployment   │  │ Deployment   │ │  │
│  │  │ (3 replicas) │  │ (3 replicas) │  │ (5 replicas) │ │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘ │  │
│  │                                                         │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │  │
│  │  │  PostgreSQL  │  │   MongoDB    │  │    Redis     │ │  │
│  │  │ StatefulSet  │  │ StatefulSet  │  │ StatefulSet  │ │  │
│  │  │  (1 master)  │  │ (1 replica)  │  │ (1 master)   │ │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘ │  │
│  │                                                         │  │
│  │  ┌──────────────┐                                      │  │
│  │  │ Docker DinD  │                                      │  │
│  │  │ Deployment   │  (Sysbox runtime)                    │  │
│  │  │ (10 replicas)│                                      │  │
│  │  └──────────────┘                                      │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │            Ingress (NGINX + cert-manager)               │  │
│  │  • TLS termination (Let's Encrypt)                      │  │
│  │  • Rate limiting                                        │  │
│  │  • WAF rules                                            │  │
│  └─────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────┘
```

**High Availability Features:**
- **HorizontalPodAutoscaler**: Auto-scaling based on CPU/memory
- **PodDisruptionBudget**: Minimum replicas during updates
- **NetworkPolicies**: Pod-level network isolation
- **ResourceQuotas**: Prevent resource exhaustion

## Data Flow Examples

### Example 1: User Creates and Executes a Flow

```
1. User creates flow in React Flow editor
   └─→ POST /api/v1/flows
       └─→ FastAPI validates definition
           └─→ PostgreSQL: INSERT INTO tenant_X.flows

2. User clicks "Execute"
   └─→ POST /api/v1/flows/{id}/execute
       └─→ FastAPI creates execution record
           └─→ PostgreSQL: INSERT INTO tenant_X.executions (status=pending)
           └─→ Celery: celery_app.send_task("execute_flow", args=[execution_id])
           └─→ Returns execution_id to client

3. Client opens WebSocket connection
   └─→ WS /api/v1/ws/executions/{execution_id}
       └─→ Redis: SUBSCRIBE execution:{execution_id}

4. Celery worker picks up task
   └─→ Load flow definition from PostgreSQL
   └─→ Initialize CrewAI agents with LLM providers
   └─→ For each node in topological order:
       ├─→ Execute agent task
       ├─→ Capture output
       ├─→ Redis: PUBLISH execution:{execution_id} {"node_id": "...", "status": "completed"}
       └─→ MongoDB: INSERT execution_logs_{tenant_id}
   └─→ Update PostgreSQL: UPDATE executions SET status=completed, outputs={...}

5. Client receives real-time updates via WebSocket
   └─→ Updates UI with node status and outputs
```

### Example 2: LLM Provider Failover

```
1. Agent attempts to call primary LLM provider (OpenAI)
   └─→ LLMProviderService.call(provider_id=primary, prompt="...")
       └─→ HTTP request to OpenAI API
       └─→ Response: 429 Rate Limit Exceeded

2. Failover logic triggered
   └─→ LLMProviderService.get_next_provider(current=primary)
       └─→ Query PostgreSQL: SELECT * FROM llm_providers WHERE priority > 1 ORDER BY priority
       └─→ Returns secondary provider (Anthropic)

3. Retry with secondary provider
   └─→ LLMProviderService.call(provider_id=secondary, prompt="...")
       └─→ HTTP request to Anthropic API
       └─→ Response: 200 OK {content: "..."}

4. Track costs and update metrics
   └─→ Prometheus: llm_api_calls_total{provider="anthropic", status="success"}
   └─→ Prometheus: llm_tokens_total{provider="anthropic"} += tokens_used
```

## Security Considerations

### Data Isolation
- **PostgreSQL**: Schema-per-tenant prevents SQL injection across tenants
- **MongoDB**: Collection naming with tenant ID prefix
- **Redis**: Key namespacing with tenant ID

### API Security
- **Authentication**: JWT with short expiration (24h)
- **Authorization**: RBAC with permission checks on every endpoint
- **Rate Limiting**: 100 requests/minute per user, 1000 requests/minute per tenant
- **Input Validation**: Pydantic schemas with strict type checking
- **SQL Injection**: Parameterized queries via SQLAlchemy ORM
- **XSS Protection**: Content-Security-Policy headers

### Container Security
- **Sysbox Runtime**: Unprivileged containers (no `privileged: true`)
- **Resource Limits**: CPU/memory quotas prevent DoS
- **Network Policies**: Deny all ingress/egress by default
- **Image Scanning**: Trivy scans for CVEs before deployment

### Secrets Management
- **Kubernetes Secrets**: Encrypted at rest (etcd encryption)
- **Environment Variables**: Injected at runtime, never in code
- **LLM API Keys**: Encrypted in database with AES-256
- **Certificate Management**: cert-manager with Let's Encrypt

## Performance Optimizations

### Caching Strategy
- **Redis**:
  - LLM responses (cache key = hash(prompt + model))
  - User sessions (TTL = 24h)
  - Flow definitions (invalidate on update)

### Database Optimization
- **PostgreSQL**:
  - Indexes on foreign keys and frequently queried columns
  - Connection pooling (SQLAlchemy pool_size=20)
  - Query optimization with EXPLAIN ANALYZE

- **MongoDB**:
  - Compound indexes on (tenant_id, created_at)
  - TTL indexes for auto-expiring logs (30 days)

### API Performance
- **Async I/O**: FastAPI with async/await for non-blocking operations
- **Response Compression**: gzip compression for responses > 1KB
- **Pagination**: Cursor-based pagination for large result sets
- **Eager Loading**: SQLAlchemy joinedload() to avoid N+1 queries

## Scalability

### Horizontal Scaling
- **Stateless API**: All backend instances are identical and stateless
- **Load Balancing**: Kubernetes Service with round-robin
- **Worker Scaling**: Celery workers scale independently via HPA
- **Database Sharding**: PostgreSQL sharding by tenant_id (future)

### Vertical Scaling
- **Resource Requests**: Conservative requests, generous limits
- **Database Resources**: Dedicated PostgreSQL instances for large tenants
- **Cache Tiering**: Redis Cluster for distributed caching (future)

## Disaster Recovery

### Backup Strategy
- **PostgreSQL**:
  - Daily full backups via pg_dump
  - WAL archiving for point-in-time recovery
  - Retention: 30 days

- **MongoDB**:
  - Daily mongodump backups
  - Retention: 30 days

- **Redis**:
  - RDB snapshots every 6 hours
  - AOF persistence enabled

### High Availability
- **Database Replication**:
  - PostgreSQL: Streaming replication (1 master, 1 standby)
  - MongoDB: Replica sets (1 primary, 2 secondaries)
  - Redis: Sentinel for automatic failover

- **Application**:
  - Minimum 2 replicas per service
  - Rolling updates with zero downtime
  - Health checks and automatic restarts

## Future Enhancements

### Planned Features
1. **GraphQL API**: Complement REST with GraphQL for flexible querying
2. **Multi-Region Deployment**: Deploy to multiple regions for low latency
3. **Advanced Analytics**: Data warehouse integration for business intelligence
4. **Marketplace**: Public marketplace for sharing flows and tools
5. **Collaboration**: Real-time collaborative editing of flows
6. **Mobile Apps**: Native iOS/Android applications

### Technical Debt
1. **Database Sharding**: Implement tenant-based sharding for PostgreSQL
2. **Event Sourcing**: Consider CQRS pattern for execution history
3. **Service Mesh**: Istio for advanced traffic management
4. **gRPC**: Internal service communication via gRPC for performance

## Conclusion

The Dynamic CrewAI Orchestration Platform is built with modern cloud-native principles, emphasizing security, scalability, and maintainability. The architecture supports rapid feature development while maintaining high availability and performance under load.

For detailed implementation guides, see:
- [Multi-Tenancy Guide](./multi-tenancy.md)
- [Security Model](./security-model.md)
- [Local Development Guide](../guides/local-development.md)
