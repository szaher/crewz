# Tasks: Platform Infrastructure Enhancements

**Input**: Design documents from `/specs/003-we-need-to/`
**Prerequisites**: plan.md (✅), research.md (✅), data-model.md (✅), contracts/ (✅ 4 files), quickstart.md (✅)

## Execution Flow (main)
```
1. Load plan.md from feature directory
   → ✅ Found: Platform Infrastructure Enhancements
   → ✅ Tech stack: Python 3.11, FastAPI, SQLAlchemy, Celery, Redis 7, PostgreSQL 15
2. Load optional design documents:
   → ✅ data-model.md: 11 new entities + 20+ UUID migrations
   → ✅ contracts/: 4 OpenAPI files (30+ endpoints)
   → ✅ research.md: 7 technical decisions
   → ✅ quickstart.md: 5 test scenarios
3. Generate tasks by category:
   → ✅ Setup: Dependencies, utilities (UUIDv7), linting
   → ✅ Tests: 4 contract test files + 5 integration scenarios
   → ✅ Core: 11 models + services + 30+ endpoints
   → ✅ Integration: Redis, Celery, WebSocket, middleware
   → ✅ Polish: Unit tests, load tests, docs
4. Apply task rules:
   → ✅ Different files = mark [P] for parallel
   → ✅ Sequential stages (UUID migration first, then authorization, queue, notifications, tenants)
5. Number tasks sequentially (T001-T070)
6. Dependencies validated (UUID migration blocks all, models before services)
7. Parallel execution examples provided
8. Validation: ✅ All contracts tested, all entities modeled, tests before impl
9. Return: SUCCESS (70 tasks ready for execution, ~16-22 days)
```

---

## Task Overview

**Total Tasks**: 70
**Estimated Effort**: 16-22 days
**Parallelizable**: 35 tasks marked [P]

**Stage Breakdown**:
- Stage 1: UUID Migration (T001-T008) - 2-3 days - SEQUENTIAL (blocks all)
- Stage 2: Authorization Service (T009-T022) - 3-4 days
- Stage 3: Async Execution (T023-T040) - 4-5 days
- Stage 4: Notification System (T041-T055) - 3-4 days
- Stage 5: Tenant Management (T056-T063) - 2-3 days
- Stage 6: Integration & Testing (T064-T070) - 2-3 days

---

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

## Path Conventions
- **Backend**: `backend/src/`, `backend/tests/`, `backend/alembic/`
- **Frontend**: `frontend/src/`, `frontend/tests/`
- Web application structure (frontend + backend)

---

## Stage 1: UUID Migration (CRITICAL PATH - BLOCKS ALL OTHER STAGES)

**Goal**: Convert all 20+ entity IDs from integers to UUIDs using UUIDv7 in single atomic transaction

- [ ] **T001** Add uuid6 library to backend/requirements.txt
  - Add `uuid6==2024.1.12` dependency
  - Install dependencies: `pip install -r backend/requirements.txt`
  - **Files**: `backend/requirements.txt`
  - **Acceptance**: uuid6 library available for import

- [ ] **T002** Create UUID utility module in backend/src/utils/uuid.py
  - Implement `generate_uuid_v7()` function
  - Implement `uuid_to_string()` and `string_to_uuid()` helpers
  - Add docstrings and type hints
  - **Files**: `backend/src/utils/uuid.py`
  - **Acceptance**: Functions return valid UUIDv7 format

- [ ] **T003** Create Alembic migration script: UUID migration (all 20+ tables)
  - **File**: `backend/alembic/versions/xxxx_migrate_to_uuid.py`
  - **Steps** (from data-model.md):
    1. CREATE EXTENSION IF NOT EXISTS "uuid-ossp"
    2. Add uuid columns to all 20+ tables (users, tenants, agents, crews, tasks, flows, executions, prompts, etc.)
    3. Generate UUIDs for existing rows using uuid_generate_v4()
    4. Create temporary mapping tables (user_id_mapping, tenant_id_mapping, etc.)
    5. Add new UUID foreign key columns
    6. Populate UUID FKs using mapping tables
    7. Drop old integer columns and constraints
    8. Rename UUID columns (remove _uuid suffix)
    9. Recreate foreign key constraints
    10. Set NOT NULL constraints
    11. Create primary key constraints
  - **Acceptance**: Migration script validates syntax with `alembic check`

- [ ] **T004** Test UUID migration on empty dev database
  - Run: `alembic upgrade head`
  - Verify: All tables have UUID primary keys
  - Verify: All foreign keys reference UUID columns
  - Test rollback: `alembic downgrade -1` (should error with "not supported")
  - **Acceptance**: Migration completes without errors, all IDs are UUID

- [ ] **T005** Create sample data for testing UUID migration
  - Create script: `backend/scripts/create_test_data.py`
  - Insert 10 users, 5 tenants, 20 agents, 10 crews, 15 tasks, 10 flows, 50 executions
  - Ensure foreign key relationships (crew → agents, flow → tasks, execution → crew/flow)
  - **Files**: `backend/scripts/create_test_data.py`
  - **Acceptance**: Script runs successfully, data appears in database

- [ ] **T006** Test UUID migration on database with sample data
  - Run sample data script
  - Take database backup: `pg_dump crewai_platform > backup.sql`
  - Run migration: `alembic upgrade head`
  - Verify: All 50 executions reference valid crew/flow UUIDs
  - Verify: All agents reference valid tenant UUIDs
  - Verify: Zero orphaned foreign keys
  - **Acceptance**: All relationships preserved, zero data loss

- [ ] **T007** [P] Update Pydantic schemas to use UUID type
  - Update all schema files in `backend/src/schemas/` to use `UUID` instead of `int` for IDs
  - Files: `agent.py`, `crew.py`, `flow.py`, `task.py`, `execution.py`, `prompt.py`, `llm_provider.py`, `user.py`, `tenant.py`
  - Import: `from uuid import UUID`
  - **Acceptance**: All schema classes validate UUID format

- [ ] **T008** [P] Update SQLAlchemy models to use UUID primary keys
  - Update all model files in `backend/src/models/` to use `postgresql.UUID(as_uuid=True)` for id columns
  - Files: `agent.py`, `crew.py`, `flow.py`, `task.py`, `execution.py`, `prompt.py`, `llm_provider.py`, `user.py`, `tenant.py`
  - Update foreign key types to UUID
  - **Acceptance**: Models reflect new UUID schema

---

## Stage 2: Authorization Service

**Goal**: Implement fine-grained RBAC+ABAC authorization with <50ms checks

**Contract**: `specs/003-we-need-to/contracts/authorization.openapi.yaml` (9 endpoints)

### Setup & Tests

- [ ] **T009** [P] Contract test: POST /api/v1/authz/check in backend/tests/contract/test_authz_check.py
  - Test valid permission check request
  - Test invalid resource type
  - Test missing required fields
  - Validate response schema (decision, latency_ms, reason)
  - **Acceptance**: Tests fail (endpoint not implemented), contract validated

- [ ] **T010** [P] Contract test: POST /api/v1/authz/bulk-check in backend/tests/contract/test_authz_bulk_check.py
  - Test batch check with 5 permissions
  - Test exceeding max limit (20)
  - Validate response schema (decisions array)
  - **Acceptance**: Tests fail, contract validated

- [ ] **T011** [P] Contract test: GET/POST /api/v1/authz/roles in backend/tests/contract/test_authz_roles.py
  - Test list roles for tenant
  - Test create custom role
  - Test validation errors (duplicate slug)
  - **Acceptance**: Tests fail, contract validated

- [ ] **T012** [P] Contract test: GET/POST/DELETE /api/v1/authz/policies in backend/tests/contract/test_authz_policies.py
  - Test list policies (tenant + user level)
  - Test create policy with pattern matching
  - Test delete policy
  - **Acceptance**: Tests fail, contract validated

### Data Models

- [ ] **T013** [P] Create Permission model in backend/src/models/permission.py
  - Fields: id (UUID), tenant_id, subject_type, subject_id, resource_type, resource_id, action, effect, conditions (JSONB)
  - Relationships: tenant, subject (polymorphic)
  - Indexes: subject, resource, tenant
  - **Acceptance**: Model imports successfully

- [ ] **T014** [P] Create Role model in backend/src/models/role.py
  - Fields: id (UUID), tenant_id, name, slug, description, is_system_role, is_default, priority
  - Relationships: tenant, users (many-to-many via user_roles)
  - Unique constraint: (tenant_id, slug)
  - **Acceptance**: Model imports successfully

- [ ] **T015** [P] Create Policy model in backend/src/models/policy.py
  - Fields: id (UUID), tenant_id, scope, scope_id, name, resource_pattern, action, effect, priority
  - Relationships: tenant, user (optional)
  - Indexes: tenant, scope
  - **Acceptance**: Model imports successfully

- [ ] **T016** [P] Create AuthorizationAuditLog model in backend/src/models/authz_audit_log.py
  - Fields: id (UUID), user_id, tenant_id, resource_type, resource_id, action, decision, reason, timestamp
  - Relationships: user, tenant
  - Partitioning: Monthly partitions (configure in migration)
  - **Acceptance**: Model imports successfully

- [ ] **T017** Create Alembic migration: Authorization tables
  - File: `backend/alembic/versions/yyyy_add_authz_tables.py`
  - Create: permissions, roles, policies, authorization_audit_logs, user_roles
  - Insert default system roles (super-admin, tenant-admin, member, viewer)
  - Create indexes per data-model.md
  - **Acceptance**: Migration runs successfully

### Core Service

- [ ] **T018** Implement AuthorizationService in backend/src/services/authz_service.py
  - Method: `check_permission(user_id, tenant_id, resource_type, resource_id, action) → bool`
  - Evaluation order: User deny > User allow > Tenant deny > Tenant allow > Default deny
  - Redis caching (5-minute TTL): `authz:{user_id}:{resource_type}:{resource_id}:{action}`
  - Permission inheritance: Access to Crew grants access to its Tasks/Agents
  - Audit logging: Log every decision to authorization_audit_logs
  - **Files**: `backend/src/services/authz_service.py`
  - **Dependencies**: T013-T017 (models and migration)
  - **Acceptance**: Service methods callable

- [ ] **T019** Implement Redis caching layer for AuthorizationService
  - Add Redis connection: `backend/src/db/redis.py`
  - Cache hit: Return decision immediately (<10ms)
  - Cache miss: Query PostgreSQL, cache result (TTL: 5 minutes)
  - Cache invalidation: `invalidate_cache(user_id, resource_pattern)`
  - **Files**: `backend/src/db/redis.py`, `backend/src/services/authz_service.py`
  - **Dependencies**: T018
  - **Acceptance**: Cache hit returns <10ms

### API Endpoints

- [ ] **T020** Implement POST /api/v1/authz/check endpoint in backend/src/api/v1/authz.py
  - Handler: `check_permission(request: PermissionCheckRequest)`
  - Call: `authz_service.check_permission()`
  - Response: `{decision: "allow"|"deny", latency_ms: int, reason: str}`
  - Target latency: <50ms p95
  - **Files**: `backend/src/api/v1/authz.py`, `backend/src/schemas/authz.py`
  - **Dependencies**: T018-T019
  - **Acceptance**: Contract test T009 passes

- [ ] **T021** Implement remaining authorization endpoints in backend/src/api/v1/authz.py
  - POST /authz/bulk-check (batch permission checks, max 20)
  - GET /authz/roles (list roles for tenant)
  - POST /authz/roles (create custom role)
  - GET /authz/policies (list policies)
  - POST /authz/policies (create policy)
  - DELETE /authz/policies/{id} (delete policy)
  - GET /authz/audit (query audit logs with filters)
  - POST /authz/cache/invalidate (clear Redis cache)
  - **Files**: `backend/src/api/v1/authz.py`
  - **Dependencies**: T020
  - **Acceptance**: Contract tests T010-T012 pass

- [ ] **T022** Create FastAPI middleware for authorization checks in backend/src/middleware/authz.py
  - Intercept all API requests
  - Extract: user_id (from JWT), resource_type, resource_id (from URL), action (from HTTP method)
  - Call: `authz_service.check_permission()`
  - If denied: Return 403 Forbidden
  - Exclude: Public endpoints (/tenants/register, /auth/login)
  - **Files**: `backend/src/middleware/authz.py`, `backend/src/main.py`
  - **Dependencies**: T018-T021
  - **Acceptance**: Unauthorized requests return 403

---

## Stage 3: Async Task Execution

**Goal**: Implement message queue-based execution system with Celery + Redis Streams

**Contract**: `specs/003-we-need-to/contracts/execution-queue.openapi.yaml` (8 endpoints)

### Setup & Tests

- [ ] **T023** [P] Add Celery dependencies to backend/requirements.txt
  - Add: `celery[redis]==5.3.4`, `redis[streams]==5.0.1`, `prometheus-client==0.19.0`
  - Install: `pip install -r backend/requirements.txt`
  - **Files**: `backend/requirements.txt`
  - **Acceptance**: Celery importable

- [ ] **T024** [P] Contract test: POST /api/v1/executions/submit in backend/tests/contract/test_queue_submit.py
  - Test valid execution submission (crew, flow, agent, task)
  - Test rate limit error (429)
  - Validate response schema (execution_id, queue_id, status, estimated_start_time)
  - **Acceptance**: Tests fail, contract validated

- [ ] **T025** [P] Contract test: GET/DELETE /api/v1/executions/{id} in backend/tests/contract/test_queue_status.py
  - Test get execution status
  - Test cancel execution (pending → cancelled)
  - Test cannot cancel completed execution
  - **Acceptance**: Tests fail, contract validated

- [ ] **T026** [P] Contract test: GET /api/v1/executions/queue/metrics in backend/tests/contract/test_queue_metrics.py
  - Test queue metrics (queue_depth, processing_rate, failure_rate)
  - Test timeframe parameter (1m, 5m, 15m, 1h, 24h)
  - **Acceptance**: Tests fail, contract validated

- [ ] **T027** [P] Contract test: GET/POST /api/v1/executions/dlq in backend/tests/contract/test_dlq.py
  - Test list dead letter tasks
  - Test requeue failed task
  - **Acceptance**: Tests fail, contract validated

### Data Models

- [ ] **T028** [P] Create ExecutionQueue model in backend/src/models/execution_queue.py
  - Fields: id (UUID), execution_id, tenant_id, user_id, execution_type, entity_id, status, priority, retry_count, max_retries, celery_task_id, payload (JSONB), scheduled_at, started_at, completed_at, duration_ms, result, error
  - Relationships: tenant, user
  - Indexes: (tenant_id, status), (status, priority), celery_task_id
  - State transitions: pending → running → completed/failed/timeout/cancelled
  - **Acceptance**: Model imports successfully

- [ ] **T029** [P] Create DeadLetterTask model in backend/src/models/dead_letter_task.py
  - Fields: id (UUID), original_queue_id, execution_type, payload, failure_reason, retry_history (JSONB), failure_timestamp, is_requeued
  - Relationships: execution_queue (original_queue_id FK)
  - **Acceptance**: Model imports successfully

- [ ] **T030** [P] Create ExecutionMetrics model in backend/src/models/execution_metrics.py
  - Fields: timestamp, tenant_id, queue_depth, pending_count, running_count, completed_last_minute, failed_last_minute, processing_rate, avg_duration_ms, p95_duration_ms, p99_duration_ms, failure_rate
  - Use TimescaleDB hypertable (if available) or regular table with time-based partitioning
  - **Acceptance**: Model imports successfully

- [ ] **T031** Create Alembic migration: Execution queue tables
  - File: `backend/alembic/versions/zzzz_add_execution_queue_tables.py`
  - Create: execution_queue, dead_letter_tasks, execution_metrics
  - Create indexes per data-model.md
  - **Acceptance**: Migration runs successfully

### Message Queue Infrastructure

- [ ] **T032** Create pluggable message queue backend abstraction in backend/src/workers/message_queue/base.py
  - Abstract class: `MessageQueueBackend`
  - Methods: `submit_task(task_name, args, kwargs, priority)`, `get_task_status(task_id)`, `cancel_task(task_id)`
  - **Files**: `backend/src/workers/message_queue/base.py`
  - **Acceptance**: Interface defined

- [ ] **T033** Implement Redis Streams backend in backend/src/workers/message_queue/redis_backend.py
  - Extends: `MessageQueueBackend`
  - Celery broker URL: `redis://redis:6379/0`
  - Celery result backend: `redis://redis:6379/1`
  - **Files**: `backend/src/workers/message_queue/redis_backend.py`
  - **Dependencies**: T032
  - **Acceptance**: Backend implements all abstract methods

- [ ] **T034** Configure Celery app in backend/src/workers/celery_app.py
  - Broker: Redis Streams (from research.md)
  - Config: task_acks_late=True, worker_prefetch_multiplier=1, task_reject_on_worker_lost=True
  - Retry: 3 attempts, exponential backoff (2s, 4s, 8s), max 30s, jitter enabled
  - Timeout: soft_time_limit=1800 (30 min), time_limit=1900 (31 min)
  - **Files**: `backend/src/workers/celery_app.py`
  - **Dependencies**: T033
  - **Acceptance**: Celery app starts with `celery -A backend.src.workers.celery_app worker`

- [ ] **T035** Implement Celery tasks in backend/src/workers/tasks.py
  - Task: `execute_crew(execution_id, crew_id, payload)`
  - Task: `execute_flow(execution_id, flow_id, payload)`
  - Task: `execute_agent(execution_id, agent_id, payload)`
  - Task: `execute_task(execution_id, task_id, payload)`
  - Each task:
    - Update execution_queue status: pending → running
    - Call CrewAI SDK
    - Save result to execution_queue
    - Update status: running → completed/failed/timeout
    - Publish notification via Redis pub/sub
  - **Files**: `backend/src/workers/tasks.py`
  - **Dependencies**: T034
  - **Acceptance**: Tasks callable via Celery

- [ ] **T036** Implement Dead Letter Queue handler in backend/src/workers/dlq_handler.py
  - Use Celery signal: `@task_failure.connect`
  - On final failure (after 3 retries):
    - Insert into dead_letter_tasks table
    - Include retry_history (all 3 attempts with timestamps, errors, duration)
  - **Files**: `backend/src/workers/dlq_handler.py`
  - **Dependencies**: T035
  - **Acceptance**: Failed tasks appear in dead_letter_tasks

- [ ] **T037** Implement rate limiting middleware in backend/src/middleware/rate_limit.py
  - Per-tenant limit: 10 concurrent executions (default, configurable)
  - Per-user limit: 5 concurrent executions (default, configurable)
  - Check: Count `execution_queue` where status IN ('pending', 'running')
  - If exceeded: Return 429 with retry_after header
  - **Files**: `backend/src/middleware/rate_limit.py`
  - **Dependencies**: T028-T031
  - **Acceptance**: Rate limits enforced

### API Endpoints

- [ ] **T038** Implement POST /api/v1/executions/submit endpoint in backend/src/api/v1/executions.py
  - Handler: `submit_execution(request: ExecutionSubmitRequest)`
  - Create execution_queue record (status='pending')
  - Submit to Celery queue (high/normal/low priority)
  - Return execution_id immediately (<200ms target)
  - **Files**: `backend/src/api/v1/executions.py`, `backend/src/schemas/execution_queue.py`
  - **Dependencies**: T028-T037
  - **Acceptance**: Contract test T024 passes

- [ ] **T039** Implement execution queue management endpoints in backend/src/api/v1/executions.py
  - GET /executions/{id} (get status)
  - DELETE /executions/{id} (cancel execution)
  - GET /executions/queue/metrics (queue performance)
  - **Files**: `backend/src/api/v1/executions.py`
  - **Dependencies**: T038
  - **Acceptance**: Contract tests T025-T026 pass

- [ ] **T040** Implement DLQ management endpoints in backend/src/api/v1/executions.py
  - GET /executions/dlq (list dead letter tasks, admin only)
  - POST /executions/dlq/{id}/requeue (retry failed task, admin only)
  - GET /admin/settings/rate-limits (get rate limits)
  - PUT /admin/settings/rate-limits (update rate limits, tenant admin only)
  - **Files**: `backend/src/api/v1/executions.py`
  - **Dependencies**: T039
  - **Acceptance**: Contract test T027 passes

---

## Stage 4: Notification System

**Goal**: Implement real-time WebSocket notifications with <1s delivery

**Contract**: `specs/003-we-need-to/contracts/notifications.openapi.yaml` (8 endpoints + WebSocket)

### Setup & Tests

- [ ] **T041** [P] Contract test: GET /api/v1/notifications in backend/tests/contract/test_notifications_list.py
  - Test list notifications with filters (category, read_status, priority, date range)
  - Test pagination
  - Validate response schema (notifications array, total, unread_count)
  - **Acceptance**: Tests fail, contract validated

- [ ] **T042** [P] Contract test: PUT /api/v1/notifications/{id}/read in backend/tests/contract/test_notifications_read.py
  - Test mark notification as read
  - Test read_at timestamp updated
  - **Acceptance**: Tests fail, contract validated

- [ ] **T043** [P] Contract test: GET/PUT /api/v1/notifications/preferences in backend/tests/contract/test_notification_preferences.py
  - Test get user preferences
  - Test update preferences (enable/disable categories)
  - Test tenant-level defaults
  - **Acceptance**: Tests fail, contract validated

### Data Models

- [ ] **T044** [P] Create Notification model in backend/src/models/notification.py
  - Fields: id (UUID), user_id, tenant_id, category, priority, title, message, resource_type, resource_id, resource_link, metadata (JSONB), read_status, read_at, delivered_via_websocket, created_at
  - Relationships: user, tenant
  - Indexes: (user_id, read_status), (user_id, created_at)
  - **Acceptance**: Model imports successfully

- [ ] **T045** [P] Create NotificationPreference model in backend/src/models/notification_preference.py
  - Fields: id (UUID), scope (tenant/user), scope_id, category, enabled, delivery_channels (array), created_at, updated_at
  - Relationships: tenant or user (polymorphic)
  - Unique constraint: (scope, scope_id, category)
  - **Acceptance**: Model imports successfully

- [ ] **T046** Create Alembic migration: Notification tables
  - File: `backend/alembic/versions/aaaa_add_notification_tables.py`
  - Create: notifications, notification_preferences
  - Create indexes per data-model.md
  - Insert default tenant preferences (all categories enabled)
  - **Acceptance**: Migration runs successfully

### WebSocket Implementation

- [ ] **T047** Create WebSocket endpoint in backend/src/websockets/notifications.py
  - Endpoint: `ws://localhost:8000/ws/notifications?token=<JWT>`
  - Authenticate: Decode JWT token from query parameter
  - Subscribe: Redis channel `notifications:user:{user_id}`
  - Send: Pending unread notifications from PostgreSQL on connect
  - Heartbeat: Respond to client heartbeat every 30s
  - Disconnect: Unsubscribe from Redis channel
  - **Files**: `backend/src/websockets/notifications.py`
  - **Dependencies**: T044-T046
  - **Acceptance**: WebSocket connection successful with valid JWT

- [ ] **T048** Implement Redis pub/sub for WebSocket broadcasting
  - On notification creation: Publish to Redis channel `notifications:user:{user_id}`
  - Message format: `{type: "notification", data: {...}, timestamp: "..."}`
  - All backend instances subscribe to their active user channels
  - **Files**: `backend/src/websockets/notifications.py`, `backend/src/services/notification_service.py`
  - **Dependencies**: T047
  - **Acceptance**: Notification published to Redis appears in WebSocket

- [ ] **T049** Implement NotificationService in backend/src/services/notification_service.py
  - Method: `create_notification(user_id, category, title, message, resource_type, resource_id, metadata)`
  - Check: User/tenant notification preferences (enabled/disabled)
  - If online: Publish to Redis pub/sub (WebSocket delivery)
  - Always: Save to notifications table (persistent storage)
  - Mark: delivered_via_websocket=True if online, False if offline
  - **Files**: `backend/src/services/notification_service.py`
  - **Dependencies**: T044-T048
  - **Acceptance**: Notifications created and delivered

- [ ] **T050** Add retention policy cleanup job in backend/src/services/notification_service.py
  - Method: `cleanup_old_notifications(retention_days=90)`
  - Delete: notifications WHERE created_at < NOW() - INTERVAL '{retention_days} days'
  - Schedule: Run daily via cron or Celery beat
  - **Files**: `backend/src/services/notification_service.py`
  - **Dependencies**: T049
  - **Acceptance**: Old notifications deleted

### API Endpoints

- [ ] **T051** Implement GET /api/v1/notifications endpoint in backend/src/api/v1/notifications.py
  - Handler: `list_notifications(category, read_status, priority, start_date, end_date, page, page_size)`
  - Query: Filter by parameters, sort by created_at DESC
  - Response: notifications array, total count, unread_count
  - **Files**: `backend/src/api/v1/notifications.py`, `backend/src/schemas/notification.py`
  - **Dependencies**: T049-T050
  - **Acceptance**: Contract test T041 passes

- [ ] **T052** Implement notification read endpoints in backend/src/api/v1/notifications.py
  - PUT /notifications/{id}/read (mark single as read)
  - POST /notifications/mark-all-read (bulk mark read, optional category filter)
  - GET /notifications/unread-count (badge count for UI)
  - **Files**: `backend/src/api/v1/notifications.py`
  - **Dependencies**: T051
  - **Acceptance**: Contract test T042 passes

- [ ] **T053** Implement notification preferences endpoints in backend/src/api/v1/notifications.py
  - GET /notifications/preferences (get user + tenant preferences + effective settings)
  - PUT /notifications/preferences (update user-level preferences)
  - GET /admin/notifications/preferences/tenant (tenant defaults, admin only)
  - PUT /admin/notifications/preferences/tenant (update tenant defaults, admin only)
  - **Files**: `backend/src/api/v1/notifications.py`
  - **Dependencies**: T052
  - **Acceptance**: Contract test T043 passes

### Frontend Implementation

- [ ] **T054** [P] Create WebSocket client in frontend/src/lib/websocket/notifications.ts
  - Connect: `ws://localhost:8000/ws/notifications?token=${getJWT()}`
  - Reconnection: Exponential backoff (1s, 2s, 4s, ..., max 30s), max 10 attempts
  - Heartbeat: Send heartbeat every 30s
  - On message: Dispatch notification to Redux store
  - On reconnect: Fetch missed notifications via API
  - **Files**: `frontend/src/lib/websocket/notifications.ts`
  - **Acceptance**: WebSocket connects and receives notifications

- [ ] **T055** [P] Create notification bell component in frontend/src/components/notifications/NotificationBell.tsx
  - Display: Bell icon with unread count badge
  - Dropdown: List of recent notifications (10 latest)
  - Actions: Mark as read, mark all as read, view all (link to notifications page)
  - Real-time updates: Listen to WebSocket messages
  - **Files**: `frontend/src/components/notifications/NotificationBell.tsx`
  - **Acceptance**: Component renders, badge updates on new notification

---

## Stage 5: Tenant Management

**Goal**: Implement super admin approval workflow for tenant creation

**Contract**: `specs/003-we-need-to/contracts/tenant-management.openapi.yaml` (5 endpoints)

### Setup & Tests

- [ ] **T056** [P] Contract test: POST /api/v1/tenants/register in backend/tests/contract/test_tenant_register.py
  - Test valid tenant registration (public, no auth)
  - Test validation errors (missing fields, invalid email)
  - Validate response schema (registration_id, status='pending')
  - **Acceptance**: Tests fail, contract validated

- [ ] **T057** [P] Contract test: GET /api/v1/admin/tenants/pending in backend/tests/contract/test_tenant_approval.py
  - Test list pending registrations (super admin only)
  - Test 403 for non-super-admin
  - **Acceptance**: Tests fail, contract validated

### Data Models

- [ ] **T058** [P] Create TenantRegistration model in backend/src/models/tenant_registration.py
  - Fields: id (UUID), company_name, admin_email, admin_name, reason, sample_data_requested, company_size, use_case, status, rejection_reason, approved_by, approved_at, tenant_id, created_at, updated_at
  - Relationships: approved_by (user), tenant (after approval)
  - State transitions: pending → approved/rejected
  - **Acceptance**: Model imports successfully

- [ ] **T059** [P] Update User model to add is_super_admin field in backend/src/models/user.py
  - Add field: is_super_admin (BOOLEAN, DEFAULT FALSE)
  - Create first super admin via migration or seed script
  - **Files**: `backend/src/models/user.py`
  - **Acceptance**: Field added, migration created

- [ ] **T060** Create Alembic migration: Tenant management tables
  - File: `backend/alembic/versions/bbbb_add_tenant_management.py`
  - Create: tenant_registrations table
  - Add: is_super_admin column to users table
  - Create indexes per data-model.md
  - **Acceptance**: Migration runs successfully

### Sample Data Seeder

- [ ] **T061** Create sample data seeder script in backend/scripts/seed_sample_data.py
  - Create: 3 sample crews (Content Marketing, Data Analysis, Customer Support)
  - Create: 5 sample flows (Blog Post Creation, Data Pipeline, Customer Inquiry, Code Review, Marketing Campaign)
  - Create: 10 sample prompts (with variables)
  - Create: 5 sample tools (Web Search, SQL Query, File Upload, API Call, Calculator)
  - Create: 10 sample executions (mix of successful, failed, timeout)
  - All entities: Scoped to provided tenant_id
  - **Files**: `backend/scripts/seed_sample_data.py`
  - **Acceptance**: Script runs successfully, sample data appears in database

### API Endpoints & Service

- [ ] **T062** Implement tenant registration endpoints in backend/src/api/v1/tenants.py
  - POST /tenants/register (public, no auth) - Create pending registration
  - GET /tenants/register/status?email=<email> (public, rate-limited) - Check status
  - **Files**: `backend/src/api/v1/tenants.py`, `backend/src/schemas/tenant_registration.py`
  - **Dependencies**: T058-T061
  - **Acceptance**: Contract test T056 passes

- [ ] **T063** Implement super admin approval endpoints in backend/src/api/v1/tenants.py
  - GET /admin/tenants/pending (super admin only) - List pending registrations
  - POST /admin/tenants/{id}/approve (super admin only) - Approve registration
    - Create tenant
    - Create admin user with temporary password
    - Optionally load sample data (if sample_data_requested=True)
    - Send email to admin with credentials
  - POST /admin/tenants/{id}/reject (super admin only) - Reject with reason
  - **Files**: `backend/src/api/v1/tenants.py`
  - **Dependencies**: T062
  - **Acceptance**: Contract test T057 passes, sample data loaded on approval

---

## Stage 6: Integration & Testing

**Goal**: End-to-end validation, load testing, and documentation

- [ ] **T064** [P] Run Quickstart Scenario 1: UUID Migration Verification
  - Steps: `specs/003-we-need-to/quickstart.md` - Scenario 1
  - Verify: All IDs are UUIDs (36 chars)
  - Verify: API requests with UUIDs return data
  - Verify: Foreign key relationships preserved
  - **Acceptance**: All scenario 1 tests pass

- [ ] **T065** [P] Run Quickstart Scenario 2: Authorization Service Testing
  - Steps: `specs/003-we-need-to/quickstart.md` - Scenario 2
  - Test: Role creation, permission checks, policy evaluation order, audit logs
  - Verify: <50ms latency for authorization checks
  - **Acceptance**: All scenario 2 tests pass

- [ ] **T066** [P] Run Quickstart Scenario 3: Async Execution Testing
  - Steps: `specs/003-we-need-to/quickstart.md` - Scenario 3
  - Test: Queue submission, status tracking, rate limiting, retry, timeout, DLQ
  - Verify: <200ms submission response time
  - **Acceptance**: All scenario 3 tests pass

- [ ] **T067** [P] Run Quickstart Scenario 4: Notification System Testing
  - Steps: `specs/003-we-need-to/quickstart.md` - Scenario 4
  - Test: WebSocket connection, real-time delivery, offline persistence, preferences, reconnection
  - Verify: <1s notification delivery latency
  - **Acceptance**: All scenario 4 tests pass

- [ ] **T068** [P] Run Quickstart Scenario 5: Tenant Management Testing
  - Steps: `specs/003-we-need-to/quickstart.md` - Scenario 5
  - Test: Public registration, super admin approval, sample data installation, rejection workflow
  - Verify: Sample data (3 crews, 5 flows, 10 prompts) loaded correctly
  - **Acceptance**: All scenario 5 tests pass

- [ ] **T069** Performance & Load Testing
  - Authorization: `artillery quick --count 100 --num 50 http://localhost:8000/api/v1/authz/check` (target: p95 <50ms)
  - Queue submission: `wrk -t4 -c100 -d30s http://localhost:8000/api/v1/executions/submit` (target: <200ms)
  - WebSocket: Custom load test script (100 concurrent connections, measure delivery latency)
  - Verify: All performance targets met
  - Optimize: If targets not met, tune Redis, PostgreSQL, add indexes
  - **Acceptance**: All performance targets met

- [ ] **T070** Update documentation
  - Update API documentation: Regenerate Swagger/ReDoc from OpenAPI contracts
  - Create architecture diagrams: Authorization flow, execution queue flow, notification flow
  - Update deployment guide: Redis Sentinel/Cluster setup for production
  - Create monitoring dashboards: Grafana dashboards for Prometheus metrics
  - **Files**: `docs/api.md`, `docs/architecture/authorization.md`, `docs/deployment.md`, `docs/monitoring.md`
  - **Acceptance**: Documentation complete, diagrams exported

---

## Dependencies Graph

```
Stage 1 (UUID Migration) BLOCKS ALL OTHER STAGES
├── T001-T008 (sequential)
    ↓
Stage 2 (Authorization)
├── T009-T012 [P] (contract tests)
├── T013-T017 [P] (models + migration)
├── T018 (service) → depends on T013-T017
├── T019 (caching) → depends on T018
├── T020 (endpoint) → depends on T018-T019
├── T021 (endpoints) → depends on T020
└── T022 (middleware) → depends on T018-T021

Stage 3 (Async Execution)
├── T023 [P] (dependencies)
├── T024-T027 [P] (contract tests)
├── T028-T031 [P] (models + migration)
├── T032-T033 (backend abstraction)
├── T034 (Celery config) → depends on T033
├── T035 (Celery tasks) → depends on T034
├── T036 (DLQ handler) → depends on T035
├── T037 (rate limiting) → depends on T028-T031
├── T038 (submit endpoint) → depends on T028-T037
├── T039 (queue endpoints) → depends on T038
└── T040 (DLQ endpoints) → depends on T039

Stage 4 (Notifications)
├── T041-T043 [P] (contract tests)
├── T044-T046 [P] (models + migration)
├── T047 (WebSocket endpoint) → depends on T044-T046
├── T048 (Redis pub/sub) → depends on T047
├── T049 (service) → depends on T044-T048
├── T050 (retention) → depends on T049
├── T051 (list endpoint) → depends on T049-T050
├── T052 (read endpoints) → depends on T051
├── T053 (preferences) → depends on T052
├── T054 [P] (frontend WebSocket client)
└── T055 [P] (frontend notification bell)

Stage 5 (Tenant Management)
├── T056-T057 [P] (contract tests)
├── T058-T060 [P] (models + migration)
├── T061 [P] (sample data seeder)
├── T062 (registration endpoints) → depends on T058-T061
└── T063 (approval endpoints) → depends on T062

Stage 6 (Integration & Testing)
├── T064-T068 [P] (quickstart scenarios) → depends on all stages
├── T069 (load testing) → depends on T064-T068
└── T070 [P] (documentation)
```

---

## Parallel Execution Examples

**After T001-T008 (UUID Migration Complete):**
```bash
# Launch all Stage 2 contract tests in parallel (T009-T012):
Task: "Contract test POST /api/v1/authz/check in backend/tests/contract/test_authz_check.py"
Task: "Contract test POST /api/v1/authz/bulk-check in backend/tests/contract/test_authz_bulk_check.py"
Task: "Contract test GET/POST /api/v1/authz/roles in backend/tests/contract/test_authz_roles.py"
Task: "Contract test GET/POST/DELETE /api/v1/authz/policies in backend/tests/contract/test_authz_policies.py"
```

**After T001-T008, launch all Stage 2 models in parallel (T013-T016):**
```bash
Task: "Create Permission model in backend/src/models/permission.py"
Task: "Create Role model in backend/src/models/role.py"
Task: "Create Policy model in backend/src/models/policy.py"
Task: "Create AuthorizationAuditLog model in backend/src/models/authz_audit_log.py"
```

**After all stages complete, launch all quickstart scenarios in parallel (T064-T068):**
```bash
Task: "Run Quickstart Scenario 1: UUID Migration Verification"
Task: "Run Quickstart Scenario 2: Authorization Service Testing"
Task: "Run Quickstart Scenario 3: Async Execution Testing"
Task: "Run Quickstart Scenario 4: Notification System Testing"
Task: "Run Quickstart Scenario 5: Tenant Management Testing"
```

---

## Validation Checklist

*GATE: Verified before task generation*

- [x] All contracts have corresponding tests (T009-T012, T024-T027, T041-T043, T056-T057)
- [x] All entities have model tasks (T013-T016, T028-T030, T044-T045, T058-T059)
- [x] All tests come before implementation (contract tests first)
- [x] Parallel tasks truly independent (different files marked [P])
- [x] Each task specifies exact file path
- [x] No task modifies same file as another [P] task

---

## Notes

- **[P] tasks**: Different files, no dependencies, can run concurrently
- **UUID Migration (Stage 1)**: MUST complete before all other stages (blocks everything)
- **Commit frequency**: Commit after each task for traceability
- **Performance targets**: Authorization <50ms, Queue <200ms, Notifications <1s
- **Spec-first**: All contracts written before implementation (Principle IV)
- **Test-driven**: Contract tests fail initially, pass after implementation

**Total Effort**: 16-22 days (sequential), 10-14 days (with 3-4 parallel workers)

---

**Generated**: 2025-10-12
**Based on**: plan.md, research.md, data-model.md, 4 contract files, quickstart.md
**Status**: Ready for execution via `/implement` or manual task completion
