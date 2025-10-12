# Implementation Plan: Platform Infrastructure Enhancements

**Branch**: `003-we-need-to` | **Date**: 2025-10-12 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-we-need-to/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path
   → ✅ Loaded: 62 functional requirements across 5 features
2. Fill Technical Context (scan for NEEDS CLARIFICATION)
   → ✅ Project Type: Web application (frontend + backend)
   → ✅ Structure Decision: CrewAI UI Project
3. Fill the Constitution Check section
   → ✅ All 4 principles evaluated
4. Evaluate Constitution Check section
   → ✅ No violations, fully aligned
   → ✅ Progress: Initial Constitution Check PASS
5. Execute Phase 0 → research.md
   → ✅ Complete: 7 technical decisions documented
6. Execute Phase 1 → contracts, data-model.md, quickstart.md
   → ✅ Complete: data-model.md (11 entities + 20+ UUID migrations)
   → ✅ Complete: 4 OpenAPI contracts (30+ endpoints)
   → ✅ Complete: quickstart.md (5 test scenarios)
7. Re-evaluate Constitution Check section
   → ✅ Post-Design: No new violations
   → ✅ Progress: Post-Design Constitution Check PASS
8. Plan Phase 2 → Task generation approach described below
9. ✅ STOP - Ready for /tasks command
```

**IMPORTANT**: The /plan command STOPS at step 7. Phases 2-4 are executed by other commands:
- Phase 2: /tasks command creates tasks.md
- Phase 3-4: Implementation execution (manual or via tools)

## Summary

This plan implements five critical platform enhancements to transform the CrewAI UI platform into a production-ready, secure, scalable multi-tenant system:

1. **Authorization Service**: Fine-grained access control with custom hybrid RBAC+ABAC model (<50ms checks)
2. **UUID Migration**: Convert all 20+ entity IDs from integers to UUIDs using UUIDv7 (sortable)
3. **Async Task Execution**: Celery + Redis Streams message queue with distributed workers, rate limiting, DLQ
4. **Notification System**: Real-time WebSocket notifications (<1s delivery) with persistent storage, Redis Pub/Sub
5. **Tenant Management**: Super admin approval workflow for tenant creation with optional sample data installation

**Technical Approach** (from research.md):
- UUIDv7 for sortable, secure IDs (PostgreSQL-optimized)
- Custom authorization for <50ms performance (Redis caching, no external services)
- Celery + Redis Streams with pluggable backend abstraction
- FastAPI native WebSocket + Redis Pub/Sub for real-time notifications
- Prometheus metrics integration for observability

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: FastAPI (async), SQLAlchemy, Alembic, Celery, Redis 7, PostgreSQL 15, MongoDB 6.0, ClickHouse 23.8
**Storage**: PostgreSQL (primary), MongoDB (logs/chat), Redis (cache/queue), ClickHouse (analytics)
**Testing**: pytest, Playwright (frontend E2E)
**Target Platform**: Linux server (Docker containers)
**Project Type**: Web application - determines source structure
**Performance Goals**:
- Authorization: <50ms p95 latency
- Queue submission: <200ms response time
- Notification delivery: <1s latency
- Queue processing: >10 tasks/second
- WebSocket: >99% uptime

**Constraints**:
- Redis 6+ required (Redis Streams support) - ✅ Confirmed: Redis 7-alpine in docker-compose.yml
- Breaking API changes acceptable (early-stage product)
- Brief maintenance window for UUID migration acceptable
- Single atomic transaction for UUID migration (no partial states)

**Scale/Scope**:
- 62 functional requirements
- 11 new database entities
- UUID migration for 20+ existing entities
- 30+ API endpoints across 4 services
- 5 end-to-end test scenarios
- Support 100 concurrent executions/tenant
- 10+ concurrent chat sessions without degradation

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Principle I: Visual & Composable**
- [x] Does this feature support graphical UI editing without code changes?
  - ✅ Authorization policies will be configurable via admin UI (future enhancement)
  - ✅ Tenant management includes approval workflow dashboard
  - ✅ Sample data provides visual examples of crews/flows after tenant approval
  - ✅ UUID-based URLs support deep linking to visual editors

- [x] Are components drag-and-drop or schema-driven?
  - ✅ Not applicable to this infrastructure feature (backend services)
  - ✅ Enables UI features: Authorization controls crew/flow editing permissions

- [x] Is composition intuitive for non-technical users?
  - ✅ Tenant registration form is user-friendly (public, no technical knowledge)
  - ✅ Sample data demonstrates platform capabilities visually

**Principle II: Seamless & Transparent UX**
- [x] Are agent reasoning steps visible to users?
  - ✅ Real-time notifications show execution progress (<1s delivery)
  - ✅ Execution queue exposes system state (queue depth, processing rate)

- [x] Do tool invocations show structured inputs/outputs in real-time?
  - ✅ WebSocket notifications deliver execution events as they occur
  - ✅ Notification metadata includes structured data for tool calls

- [x] Is role distinction clear (Agent vs Crew vs User)?
  - ✅ Authorization audit logs track who performed what action
  - ✅ Tenant management distinguishes super admin vs tenant admin vs member

**Principle III: Modular & Extensible Architecture**
- [x] Can new tools be added in under 30 minutes?
  - ✅ Async execution workers support tool registration without core changes
  - ✅ Pluggable message queue backend (Redis → RabbitMQ/Kafka future)

- [x] Are frontend/backend decoupled with well-defined APIs?
  - ✅ 4 comprehensive OpenAPI contracts (authorization, execution, notifications, tenants)
  - ✅ REST endpoints + WebSocket protocol clearly specified

- [x] Are extension points documented with examples?
  - ✅ Pluggable backend abstraction documented in research.md
  - ✅ Sample data seeder provides extension template

**Principle IV: Spec-First Development**
- [x] Are schemas defined in `/specs` before implementation?
  - ✅ Phase 0: research.md completed (7 technical decisions)
  - ✅ Phase 1: data-model.md completed (11 entities + 20+ UUID migrations)

- [x] Are API contracts documented (OpenAPI/GraphQL)?
  - ✅ 4 OpenAPI 3.0.3 contracts completed before implementation
  - ✅ WebSocket protocol documented in notifications.openapi.yaml

- [x] Is documentation updated before code merge?
  - ✅ quickstart.md created with 5 test scenarios
  - ✅ All artifacts ready before implementation begins

**CONSTITUTIONAL COMPLIANCE**: ✅ FULLY ALIGNED - All checks pass with strong justification

## Project Structure

### Documentation (this feature)
```
specs/003-we-need-to/
├── plan.md                          # This file (/plan command output)
├── spec.md                          # Feature specification (62 requirements)
├── research.md                      # Phase 0 output (/plan command) - 7 decisions
├── data-model.md                    # Phase 1 output (/plan command) - 11 entities + UUID
├── quickstart.md                    # Phase 1 output (/plan command) - 5 scenarios
├── contracts/                       # Phase 1 output (/plan command)
│   ├── authorization.openapi.yaml   # 9 endpoints (authz checks, roles, policies)
│   ├── execution-queue.openapi.yaml # 8 endpoints (queue, metrics, DLQ)
│   ├── notifications.openapi.yaml   # 8 endpoints + WebSocket protocol
│   └── tenant-management.openapi.yaml # 5 endpoints (registration, approval)
└── tasks.md                         # Phase 2 output (/tasks command - NOT created by /plan)
```

### Source Code (repository root)

```
/backend
├── src/
│   ├── api/v1/                      # REST endpoints
│   │   ├── __init__.py
│   │   ├── agents.py
│   │   ├── crews.py
│   │   ├── flows.py
│   │   ├── authz.py                 # NEW: Authorization endpoints
│   │   ├── executions.py            # MODIFIED: Async queue integration
│   │   ├── notifications.py         # NEW: Notification endpoints
│   │   └── tenants.py               # NEW: Tenant management
│   ├── db/                          # Database connections
│   │   ├── __init__.py
│   │   ├── session.py               # PostgreSQL
│   │   ├── mongodb.py               # MongoDB
│   │   ├── redis.py                 # NEW: Redis connection pools
│   │   └── clickhouse.py            # ClickHouse
│   ├── models/                      # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── user.py                  # MODIFIED: Add is_super_admin, UUID
│   │   ├── tenant.py                # MODIFIED: UUID migration
│   │   ├── agent.py                 # MODIFIED: UUID migration
│   │   ├── crew.py                  # MODIFIED: UUID migration
│   │   ├── flow.py                  # MODIFIED: UUID migration
│   │   ├── execution.py             # MODIFIED: UUID migration
│   │   ├── permission.py            # NEW: Authorization
│   │   ├── role.py                  # NEW: Authorization
│   │   ├── policy.py                # NEW: Authorization
│   │   ├── authz_audit_log.py       # NEW: Authorization audit
│   │   ├── execution_queue.py       # NEW: Async execution
│   │   ├── dead_letter_task.py      # NEW: Failed task tracking
│   │   ├── notification.py          # NEW: Notifications
│   │   ├── notification_preference.py # NEW: Notification settings
│   │   └── tenant_registration.py   # NEW: Tenant approval workflow
│   ├── schemas/                     # Pydantic request/response schemas
│   │   ├── authz.py                 # NEW: Authorization schemas
│   │   ├── execution_queue.py       # NEW: Queue schemas
│   │   ├── notification.py          # NEW: Notification schemas
│   │   └── tenant_registration.py   # NEW: Tenant schemas
│   ├── services/                    # Business logic layer
│   │   ├── agent_service.py
│   │   ├── crew_service.py
│   │   ├── authz_service.py         # NEW: Authorization evaluation
│   │   ├── queue_service.py         # NEW: Execution queue management
│   │   ├── notification_service.py  # NEW: Notification delivery
│   │   ├── tenant_service.py        # NEW: Tenant management
│   │   ├── encryption_service.py    # Existing
│   │   └── versioning_service.py    # Existing
│   ├── workers/                     # NEW: Background task workers
│   │   ├── __init__.py
│   │   ├── celery_app.py            # Celery configuration
│   │   ├── tasks.py                 # Task definitions
│   │   └── message_queue/           # Pluggable backend
│   │       ├── base.py              # Abstract interface
│   │       └── redis_backend.py     # Redis Streams implementation
│   ├── websockets/                  # NEW: WebSocket endpoints
│   │   └── notifications.py         # WebSocket handler
│   └── main.py                      # MODIFIED: Add new routes
├── alembic/                         # Database migrations
│   └── versions/
│       ├── xxxx_migrate_to_uuid.py  # NEW: UUID migration
│       └── yyyy_add_authz_tables.py # NEW: Authorization tables
├── scripts/                         # Initialization scripts
│   ├── init-db.sh
│   ├── clickhouse-init.sql
│   └── seed_sample_data.py          # NEW: Sample data seeder
└── tests/
    ├── integration/
    │   ├── test_authz.py            # NEW: Authorization tests
    │   ├── test_queue.py            # NEW: Queue tests
    │   ├── test_notifications.py    # NEW: Notification tests
    │   └── test_tenant_mgmt.py      # NEW: Tenant tests
    └── unit/
        ├── test_authz_service.py    # NEW: Unit tests
        └── test_queue_service.py    # NEW: Unit tests

/frontend
├── src/
│   ├── components/
│   │   ├── flows/                   # Flow editor components
│   │   ├── crews/                   # Crew manager components
│   │   ├── chat/                    # Chat interface components
│   │   ├── notifications/           # NEW: Notification bell component
│   │   └── admin/                   # NEW: Tenant approval dashboard
│   ├── pages/
│   │   ├── register.tsx             # NEW: Tenant registration form
│   │   └── admin/                   # NEW: Admin pages
│   ├── lib/
│   │   └── websocket/
│   │       └── notifications.ts     # NEW: WebSocket client
│   └── services/
│       └── api.ts                   # MODIFIED: Add new API clients
└── tests/
    └── e2e/
        ├── authz.spec.ts            # NEW: Authorization E2E tests
        └── notifications.spec.ts    # NEW: Notification E2E tests

/specs                               # Feature specifications
/docs                                # Architecture diagrams
```

**Structure Decision**: Web application (CrewAI UI Project). This is a full-stack web application with React/Next.js frontend and FastAPI backend, following the CrewAI UI project structure. The feature adds new backend services (authorization, queue, notifications, tenant management) and minimal frontend components (notification bell, tenant registration/approval UI).

## Phase 0: Outline & Research

**Document**: [research.md](./research.md)

**Status**: ✅ Complete

**Unknowns Resolved**:
1. ✅ UUID Strategy → UUIDv7 (sortable, PostgreSQL-optimized)
2. ✅ Authorization Framework → Custom Hybrid RBAC+ABAC
3. ✅ Message Queue Technology → Celery + Redis Streams (pluggable)
4. ✅ WebSocket Architecture → FastAPI native + Redis Pub/Sub
5. ✅ Monitoring Solution → Prometheus (client + instrumentator)
6. ✅ Migration Strategy → Alembic single atomic transaction
7. ✅ Sample Data Approach → Seeder script (3 crews, 5 flows, 10 prompts)

**Key Research Findings**:

**Decision 1: UUIDv7**
- **Rationale**: Sortable by timestamp (maintains ordering), PostgreSQL BTREE index friendly, non-guessable (security)
- **Alternatives**: UUIDv4 (not sortable), ULID (non-standard, less PostgreSQL support)
- **Implementation**: Python: `uuid6.uuid7()`, SQLAlchemy: `postgresql.UUID(as_uuid=True)`

**Decision 2: Custom Authorization**
- **Rationale**: Performance critical (<50ms requirement), direct PostgreSQL queries faster than external policy engines, permission inheritance requires custom logic
- **Alternatives**: Casbin (learning curve, complex inheritance), OPA (network latency, overkill)
- **Implementation**: PostgreSQL permissions table + Redis caching (5-min TTL)

**Decision 3: Celery + Redis Streams**
- **Rationale**: Redis 7 already deployed, Redis Streams provide persistence + consumer groups, pluggable design allows future migration
- **Alternatives**: RabbitMQ (adds infrastructure), Kafka (overkill for MVP)
- **Implementation**: Celery broker + Redis Streams + pluggable abstraction layer

**Decision 4: FastAPI WebSocket + Redis Pub/Sub**
- **Rationale**: Leverages existing stack, no frontend dependencies (native WebSocket API), Redis pub/sub enables multi-server broadcasting
- **Alternatives**: Socket.IO (heavier, extra dependency), FastAPI alone (no multi-server support)
- **Implementation**: WebSocket endpoint + Redis pub/sub subscription per user

**Decision 5: Prometheus Metrics**
- **Rationale**: Standard monitoring tooling, custom business metrics (authz latency, queue depth, notification success)
- **Implementation**: prometheus-client (custom metrics) + prometheus-fastapi-instrumentator (HTTP metrics)

**Decision 6: Atomic Migration**
- **Rationale**: Zero data loss, single transaction ensures all-or-nothing, temporary mapping tables for FK updates
- **Implementation**: Alembic migration with 11 steps (add UUID columns → generate UUIDs → update FKs → rename columns → drop old columns)

**Decision 7: Sample Data Seeder**
- **Rationale**: Showcase all features realistically, provide functional examples for new tenants
- **Implementation**: Python script: `seed_sample_data.py` (3 crews, 5 flows, 10 prompts, 5 tools, 10 executions)

**Output**: research.md with all technical decisions documented

## Phase 1: Design & Contracts

**Status**: ✅ Complete

**Prerequisites**: ✅ research.md complete

**Outputs**:

### 1. Data Model (data-model.md)

**New Entities Extracted** (11 tables):

1. **Permission** (Authorization)
   - Fields: id (UUID), tenant_id, subject_type (user/role), subject_id, resource_type, resource_id, action (read/write/execute/delete), effect (allow/deny), conditions (JSONB)
   - Relationships: tenant, subject (polymorphic: user or role)
   - Validation: Composite unique constraint (tenant + subject + resource + action)

2. **Role** (Authorization)
   - Fields: id (UUID), tenant_id, name, description, created_by
   - Relationships: tenant, permissions (1:many), users (many:many)
   - Validation: Unique (tenant_id, name)

3. **Policy** (Authorization)
   - Fields: id (UUID), scope (tenant/user), scope_id, category, pattern (e.g., "crew:*"), effect, priority
   - Relationships: tenant or user
   - Validation: Pattern matching rules

4. **AuthorizationAuditLog** (Authorization)
   - Fields: id (UUID), user_id, tenant_id, resource_type, resource_id, action, decision (allow/deny), reason, timestamp
   - Relationships: user, tenant
   - State: Append-only, partitioned by month

5. **ExecutionQueue** (Async Execution)
   - Fields: id (UUID), execution_id, tenant_id, user_id, execution_type, entity_id, status, priority, retry_count, celery_task_id, payload (JSONB), scheduled_at, started_at, completed_at
   - Relationships: tenant, user
   - State Transitions: pending → running → completed/failed/timeout/cancelled

6. **DeadLetterTask** (Async Execution)
   - Fields: id (UUID), original_queue_id, failure_reason, retry_history (JSONB), failure_timestamp
   - Relationships: execution_queue
   - State: Immutable after creation

7. **ExecutionMetrics** (Async Execution - TimescaleDB)
   - Fields: timestamp, queue_depth, processing_rate, avg_duration_ms, failure_rate
   - Relationships: None (time-series data)

8. **Notification** (Notifications)
   - Fields: id (UUID), user_id, tenant_id, category, priority, title, message, resource_type, resource_id, resource_link, metadata (JSONB), read_status, read_at, delivered_via_websocket
   - Relationships: user, tenant
   - State: created → read

9. **NotificationPreference** (Notifications)
   - Fields: id (UUID), scope (tenant/user), scope_id, category, enabled, delivery_channels (array)
   - Relationships: tenant or user
   - Validation: Unique (scope + scope_id + category)

10. **TenantRegistration** (Tenant Management)
    - Fields: id (UUID), company_name, admin_email, admin_name, reason, sample_data_requested, status, rejection_reason, approved_by, approved_at, tenant_id
    - Relationships: approved_by (user), tenant (after approval)
    - State Transitions: pending → approved/rejected

11. **User Extension**
    - New field: is_super_admin (boolean, default false)

**UUID Migration** (20+ tables):
- users, tenants, agents, crews, tasks, flows, executions, prompts, chat_sessions, tools, llm_providers, feedback, agent_versions, provider_versions, flow_steps, crew_tasks, task_dependencies, execution_logs, chat_messages, tool_calls

**Migration Strategy**:
```sql
-- 11-step process (detailed in data-model.md):
1. Add UUID columns to all tables
2. Generate UUIDs for existing rows
3. Create temporary mapping tables
4. Add new UUID foreign key columns
5. Populate UUID FKs using mapping tables
6. Drop old integer columns and constraints
7. Rename UUID columns (remove _uuid suffix)
8. Recreate foreign key constraints
9. Set NOT NULL constraints
10. Create primary key constraints
11. Create indexes
```

### 2. API Contracts (contracts/)

**Generated Contracts** (4 OpenAPI 3.0.3 files):

**authorization.openapi.yaml** (9 endpoints):
- `POST /authz/check` - Single permission check (<50ms target)
- `POST /authz/bulk-check` - Batch checks (max 20)
- `GET /authz/roles` - List roles for tenant
- `POST /authz/roles` - Create custom role
- `GET /authz/policies` - List policies (tenant + user)
- `POST /authz/policies` - Create policy
- `DELETE /authz/policies/{id}` - Delete policy
- `GET /authz/audit` - Query audit logs
- `POST /authz/cache/invalidate` - Clear Redis cache

**execution-queue.openapi.yaml** (8 endpoints):
- `POST /executions/submit` - Queue execution (<200ms target)
- `GET /executions/{id}` - Get execution status
- `DELETE /executions/{id}` - Cancel execution
- `GET /executions/queue/metrics` - Queue performance metrics
- `GET /executions/dlq` - List dead letter tasks
- `POST /executions/dlq/{id}/requeue` - Retry failed task
- `GET /admin/settings/rate-limits` - Get rate limits
- `PUT /admin/settings/rate-limits` - Update rate limits

**notifications.openapi.yaml** (8 endpoints + WebSocket):
- `GET /notifications` - List notifications with filters
- `GET /notifications/unread-count` - Badge count for UI
- `PUT /notifications/{id}/read` - Mark as read
- `POST /notifications/mark-all-read` - Bulk mark read
- `GET /notifications/preferences` - Get user preferences
- `PUT /notifications/preferences` - Update preferences
- `GET /admin/notifications/preferences/tenant` - Tenant defaults
- `PUT /admin/notifications/preferences/tenant` - Update tenant defaults
- `WS /ws/notifications?token=<jwt>` - Real-time WebSocket stream

**tenant-management.openapi.yaml** (5 endpoints):
- `POST /tenants/register` - Public registration (no auth required)
- `GET /tenants/register/status?email=<email>` - Check registration status
- `GET /admin/tenants/pending` - List pending registrations (super admin only)
- `POST /admin/tenants/{id}/approve` - Approve tenant (creates tenant, admin user, sample data)
- `POST /admin/tenants/{id}/reject` - Reject with reason

### 3. Test Scenarios (quickstart.md)

**5 End-to-End Scenarios**:

**Scenario 1: UUID Migration Verification**
- Database queries to verify UUID format
- API tests to ensure UUID handling
- Foreign key relationship validation
- Sample data loading verification

**Scenario 2: Authorization Service Testing**
- Role creation and assignment
- Permission checks (allow/deny scenarios)
- Policy evaluation order (user deny > user allow > tenant deny > tenant allow)
- Audit log verification
- Cache invalidation testing

**Scenario 3: Async Execution Testing**
- Queue submission and immediate response
- Status tracking (pending → running → completed)
- Rate limiting enforcement (10 concurrent/tenant, 5/user)
- Retry behavior (3 attempts with exponential backoff)
- Timeout enforcement (30 min default)
- Dead letter queue management

**Scenario 4: Notification System Testing**
- WebSocket connection and authentication
- Real-time notification delivery (<1s)
- Offline notification persistence
- Preference management (user + tenant level)
- Reconnection handling (exponential backoff)
- Unread count accuracy

**Scenario 5: Tenant Management Testing**
- Public tenant registration submission
- Super admin approval workflow
- Sample data installation (3 crews, 5 flows, 10 prompts)
- Admin user creation with temporary password
- Rejection workflow with reason

### 4. Agent Context Update

**IMPORTANT**: Agent context file (CLAUDE.md) will be updated via:
```bash
.specify/scripts/bash/update-agent-context.sh claude
```

This script will:
- Add new technologies: UUIDv7, Celery, Redis Streams, WebSocket, Prometheus
- Update recent changes: Platform Infrastructure Enhancements
- Preserve manual additions between markers
- Keep under 150 lines for token efficiency

**Output**: data-model.md (11 entities + UUID), 4 OpenAPI contracts (30+ endpoints), quickstart.md (5 scenarios), CLAUDE.md updated

## Phase 2: Task Planning Approach
*This section describes what the /tasks command will do - DO NOT execute during /plan*

**Task Generation Strategy**:

The `/tasks` command will load `.specify/templates/tasks-template.md` and generate a dependency-ordered task list based on Phase 0-1 artifacts:

**Source Documents**:
- research.md (technical decisions)
- data-model.md (11 entities + UUID migration)
- 4 OpenAPI contracts (30+ endpoints)
- quickstart.md (5 test scenarios)

**Task Generation Rules**:

1. **UUID Migration Tasks** (Stage 1):
   - Create Alembic migration script
   - Add UUID generation utilities
   - Execute migration on dev database
   - Verify data integrity (all FKs preserved)
   - Update API schemas to use UUID

2. **Authorization Tasks** (Stage 2):
   - Create models (Permission, Role, Policy, AuthorizationAuditLog)
   - Implement AuthorizationService (evaluation logic, caching, audit)
   - Create API endpoints (9 endpoints from authorization.openapi.yaml)
   - Add FastAPI middleware for auth checks
   - Write unit tests (evaluation logic)
   - Write integration tests (API endpoints)

3. **Async Execution Tasks** (Stage 3):
   - Configure Celery + Redis Streams
   - Create pluggable backend abstraction
   - Create models (ExecutionQueue, DeadLetterTask, ExecutionMetrics)
   - Implement Celery worker (retry, timeout, DLQ)
   - Create API endpoints (8 endpoints from execution-queue.openapi.yaml)
   - Add rate limiting middleware
   - Write integration tests (queue, DLQ)
   - Write load tests (scaling)

4. **Notification Tasks** (Stage 4):
   - Create models (Notification, NotificationPreference)
   - Implement WebSocket endpoint + Redis pub/sub
   - Implement NotificationService (delivery, preferences)
   - Create API endpoints (8 endpoints from notifications.openapi.yaml)
   - Add retention policy cleanup job
   - Create frontend WebSocket client
   - Create notification bell component
   - Write integration tests (delivery, reconnection)

5. **Tenant Management Tasks** (Stage 5):
   - Create models (TenantRegistration, User.is_super_admin)
   - Create sample data seeder script
   - Create API endpoints (5 endpoints from tenant-management.openapi.yaml)
   - Add super admin middleware
   - Create frontend registration form
   - Create admin approval dashboard
   - Write integration tests (approval workflow)

6. **Integration Tasks** (Stage 6):
   - Run all 5 quickstart scenarios
   - Fix integration issues
   - Run load tests (authz, queue, notifications)
   - Optimize based on results
   - Update API documentation
   - Create architecture diagrams
   - Update deployment guide

**Ordering Strategy**:
- **Sequential Stages**: UUID migration MUST complete before all other stages
- **Parallel Within Stages**: Tasks marked [P] can run concurrently (independent files)
- **TDD Order**: Tests written before implementation where applicable
- **Dependency Order**: Models → Services → API Endpoints → Tests

**Task Granularity**:
- Each task = 1-2 hours of work
- Clear acceptance criteria per task
- File paths and function signatures specified

**Estimated Output**:
- 50-70 numbered, ordered tasks in tasks.md
- Organized into 6 stages
- Total estimated effort: 16-22 days

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation
*These phases are beyond the scope of the /plan command*

**Phase 3**: Task execution (/tasks command creates tasks.md)
**Phase 4**: Implementation (execute tasks.md following constitutional principles)
**Phase 5**: Validation (run tests, execute quickstart.md, performance validation)

## Complexity Tracking
*Fill ONLY if Constitution Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | All principles aligned |

**CONSTITUTIONAL COMPLIANCE**: ✅ FULLY ALIGNED - No complexity deviations


## Progress Tracking
*This checklist is updated during execution flow*

**Phase Status**:
- [x] Phase 0: Research complete (/plan command)
- [x] Phase 1: Design complete (/plan command)
- [x] Phase 2: Task planning complete (/plan command - describe approach only)
- [ ] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS (all 4 principles aligned)
- [x] Post-Design Constitution Check: PASS (no new violations)
- [x] All NEEDS CLARIFICATION resolved (7/7 decisions documented)
- [x] Complexity deviations documented (0 deviations)

**Artifact Status**:
- [x] research.md created (7 technical decisions)
- [x] data-model.md created (11 entities + 20+ UUID migrations)
- [x] contracts/authorization.openapi.yaml created (9 endpoints)
- [x] contracts/execution-queue.openapi.yaml created (8 endpoints)
- [x] contracts/notifications.openapi.yaml created (8 endpoints + WebSocket)
- [x] contracts/tenant-management.openapi.yaml created (5 endpoints)
- [x] quickstart.md created (5 test scenarios)
- [x] plan.md created (this document)
- [ ] CLAUDE.md updated (pending: run update-agent-context.sh)
- [ ] tasks.md (pending: /tasks command)

---
*Based on Constitution v2.0.0 - See `.specify/memory/constitution.md`*
