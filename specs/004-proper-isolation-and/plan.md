# Implementation Plan: Isolated Worker Architecture for Async Execution

**Branch**: `004-proper-isolation-and` | **Date**: 2025-10-17 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/004-proper-isolation-and/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path ✅
   → Found: /specs/004-proper-isolation-and/spec.md
2. Fill Technical Context ✅
   → Project Type: Web application (backend + frontend)
   → Set Structure Decision: CrewAI UI Project
3. Fill Constitution Check section ✅
4. Evaluate Constitution Check section ✅
   → Violations exist: Backend-only feature (no visual UI for workers)
   → Documented in Complexity Tracking
   → Update Progress Tracking: Initial Constitution Check
5. Execute Phase 0 → research.md
6. Execute Phase 1 → contracts, data-model.md, quickstart.md, CLAUDE.md
7. Re-evaluate Constitution Check section
8. Plan Phase 2 → Describe task generation approach (DO NOT create tasks.md)
9. STOP - Ready for /tasks command
```

**IMPORTANT**: The /plan command STOPS at step 9. Phases 2-4 are executed by other commands:
- Phase 2: /tasks command creates tasks.md
- Phase 3-4: Implementation execution (manual or via tools)

## Summary
This feature implements isolated worker architecture to offload crew/agent/task executions from the main API application to separate Docker containers. Workers are managed via Celery task queue with Redis, support live execution streaming via WebSocket, include priority-based job scheduling, auto-scaling via K8s HPA at 80% CPU/memory utilization, execution cancellation, re-execution with versioning, and artifact management. The system starts with 2 workers and scales to support 10,000 concurrent executions.

## Technical Context
**Language/Version**: Python 3.11 (backend), TypeScript/React (frontend)
**Primary Dependencies**:
  - Backend: Celery 5.3.4, Redis 4.6.0, FastAPI 0.104.1, python-socketio 5.10.0, docker-py 6.1.3
  - Frontend: React, WebSocket client, React Query for real-time updates
**Storage**: PostgreSQL (job metadata, execution results), MongoDB (execution logs), Redis (task queue, pub/sub), S3/local filesystem (artifacts)
**Testing**: pytest (backend), Playwright (frontend E2E), contract tests (OpenAPI validation)
**Target Platform**: Docker containers, Kubernetes with HPA (Horizontal Pod Autoscaler)
**Project Type**: Web application (CrewAI UI Project)
**Performance Goals**:
  - 10,000 concurrent executions at full scale
  - <500ms latency for live streaming worker→frontend
  - <1s queue position update propagation
  - Worker scaling within 2 minutes of threshold breach
**Constraints**:
  - 2 CPU + 4 GB RAM per worker container
  - 10 minute default execution timeout (tenant-configurable)
  - 30 day artifact retention
  - 5 second failure detection for live execution support
**Scale/Scope**:
  - Initial: 2 workers (docker-compose dev), scale to support 10k concurrent (K8s prod)
  - Multi-tenant isolation for executions and artifacts
  - UUIDv7 identifiers, existing authz patterns

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Principle I: Visual & Composable**
- [⚠️ PARTIAL] Does this feature support graphical UI editing without code changes?
  - Execution detail page shows live streams, artifacts, queue position (visual)
  - Worker management itself is infrastructure-level, not end-user facing
- [✅ YES] Are components drag-and-drop or schema-driven?
  - Execution parameters follow existing crew/flow schemas
- [✅ YES] Is composition intuitive for non-technical users?
  - Users trigger executions via existing flow UI; worker orchestration is transparent

**Principle II: Seamless & Transparent UX**
- [✅ YES] Are agent reasoning steps visible to users?
  - Live execution streaming shows real-time worker output
- [✅ YES] Do tool invocations show structured inputs/outputs in real-time?
  - Worker streams include tool calls and results
- [✅ YES] Is role distinction clear (Agent vs Crew vs User)?
  - Execution detail page clearly shows which crew/agents are running

**Principle III: Modular & Extensible Architecture**
- [✅ YES] Can new tools be added in under 30 minutes?
  - Workers inherit existing tool framework from main app
- [✅ YES] Are frontend/backend decoupled with well-defined APIs?
  - New WebSocket endpoints + REST APIs for execution management
  - OpenAPI contracts defined in Phase 1
- [✅ YES] Are extension points documented with examples?
  - Celery task registration, custom worker types, scaling policies

**Principle IV: Spec-First Development**
- [✅ YES] Are schemas defined in `/specs` before implementation?
  - This spec, research.md, data-model.md, contracts/ all precede code
- [✅ YES] Are API contracts documented (OpenAPI/GraphQL)?
  - Phase 1 generates OpenAPI schemas for new endpoints
- [✅ YES] Is documentation updated before code merge?
  - quickstart.md demonstrates execution flow before implementation

**Justification for Partial Compliance (Principle I)**:
Worker infrastructure is **backend architecture**, not end-user feature. Users interact with executions (which remain visual/composable), not workers directly. This aligns with "seamless & transparent" principle—users don't need to understand worker internals.

## Project Structure

### Documentation (this feature)
```
specs/004-proper-isolation-and/
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output (/plan command)
├── data-model.md        # Phase 1 output (/plan command)
├── quickstart.md        # Phase 1 output (/plan command)
├── contracts/           # Phase 1 output (/plan command)
│   ├── execution-queue-api.yaml
│   ├── execution-stream-ws.yaml
│   ├── worker-management-api.yaml
│   └── artifact-api.yaml
└── tasks.md             # Phase 2 output (/tasks command - NOT created by /plan)
```

### Source Code (repository root)
```
/backend
├── src/
│   ├── api/v1/
│   │   ├── executions.py          # Execution queue, status, cancellation endpoints
│   │   ├── artifacts.py           # Artifact download/versioning endpoints
│   │   └── workers.py             # Worker health/metrics endpoints (admin)
│   ├── models/
│   │   ├── execution_job.py       # ExecutionJob entity (queued/in-progress/completed/failed/cancelled)
│   │   ├── execution_artifact.py  # ExecutionArtifact entity (versioned outputs)
│   │   ├── worker_instance.py     # WorkerInstance entity (health tracking)
│   │   └── queue_position.py      # QueuePosition entity (estimated wait time)
│   ├── services/
│   │   ├── execution_service.py   # Execution lifecycle management
│   │   ├── worker_service.py      # Worker pool management
│   │   ├── queue_service.py       # Priority queue, position estimation
│   │   └── artifact_service.py    # Artifact capture, versioning, cleanup
│   ├── workers/
│   │   ├── celery_app.py          # Celery configuration, Redis broker
│   │   ├── execution_worker.py    # Main Celery task for crew/flow/task execution
│   │   ├── stream_handler.py      # WebSocket streaming during execution
│   │   └── retry_policy.py        # Exponential backoff retry logic
│   ├── websocket/
│   │   ├── execution_stream.py    # WebSocket endpoint for live execution output
│   │   └── queue_updates.py       # WebSocket endpoint for queue position updates
│   ├── db/
│   │   └── migrations/            # Alembic migrations for new models
│   └── config/
│       └── worker_config.py       # Worker resource limits, scaling thresholds
└── tests/
    ├── contract/
    │   ├── test_execution_queue_contract.py
    │   ├── test_execution_stream_contract.py
    │   └── test_artifact_contract.py
    ├── integration/
    │   ├── test_execution_lifecycle.py
    │   ├── test_worker_isolation.py
    │   ├── test_live_streaming.py
    │   └── test_queue_priority.py
    └── unit/
        ├── test_retry_policy.py
        ├── test_queue_service.py
        └── test_artifact_versioning.py

/frontend
├── src/
│   ├── components/
│   │   ├── executions/
│   │   │   ├── ExecutionDetailPage.tsx     # Live stream, artifacts, cancel button
│   │   │   ├── LiveExecutionStream.tsx     # WebSocket-based output display
│   │   │   ├── QueuePosition.tsx           # Position + estimated time
│   │   │   ├── ArtifactList.tsx            # Download links, version history
│   │   │   └── ExecutionActions.tsx        # Cancel, re-execute buttons
│   │   └── workers/
│   │       └── WorkerStatusIndicator.tsx   # Worker pool health (admin view)
│   ├── hooks/
│   │   ├── useExecutionStream.ts           # WebSocket connection for live output
│   │   ├── useQueuePosition.ts             # Polling/WebSocket for queue updates
│   │   └── useExecutionActions.ts          # Cancel, re-execute mutations
│   └── services/
│       ├── executionApi.ts                 # REST API client for executions
│       └── websocketClient.ts              # WebSocket connection manager
└── tests/
    └── e2e/
        ├── execution-lifecycle.spec.ts
        ├── live-streaming.spec.ts
        └── queue-visualization.spec.ts

/infra/docker/
├── worker.Dockerfile                      # Worker container image
└── docker-compose.worker.yml              # Local 2-worker setup

/infra/k8s/
├── worker-deployment.yaml                 # K8s deployment for workers
├── worker-hpa.yaml                        # Horizontal Pod Autoscaler (80% CPU/mem)
└── redis-deployment.yaml                  # Redis for Celery broker/backend
```

**Structure Decision**: CrewAI UI Project (Option 3) - Web application with frontend + backend. This feature adds worker isolation infrastructure to the existing CrewAI platform, introducing new backend services (Celery workers), WebSocket streaming, and frontend components for execution monitoring. Workers run in separate Docker containers managed via docker-compose (dev) and K8s deployments (prod).

## Phase 0: Outline & Research

### Unknowns from Technical Context
All technical decisions are clarified in spec.md Session 2025-10-17. No NEEDS CLARIFICATION markers remain.

### Research Tasks
1. **Celery + Redis architecture for isolated workers**
   - Decision: Celery workers run in separate containers, Redis as broker + result backend
   - Rationale: Mature task queue, built-in retry/backoff, supports priority queues
   - Alternatives considered: RabbitMQ (more complex), direct multiprocessing (no isolation)

2. **WebSocket streaming for live execution output**
   - Decision: python-socketio on backend, React WebSocket client on frontend
   - Rationale: Already in use (requirements.txt line 53), bidirectional streaming, room-based broadcasting
   - Alternatives considered: SSE (one-way only), polling (high latency)

3. **Priority queue implementation**
   - Decision: Celery priority routing with Redis sorted sets for queue position tracking
   - Rationale: Native Celery support, tenant-specific priorities via custom headers
   - Alternatives considered: Custom queue service (reinventing wheel)

4. **K8s Horizontal Pod Autoscaler (HPA) configuration**
   - Decision: HPA targeting 80% CPU + memory utilization, custom metrics for queue depth
   - Rationale: Matches clarification requirement, industry standard for autoscaling
   - Alternatives considered: Manual scaling (doesn't meet requirements), KEDA (overkill for MVP)

5. **Artifact storage and versioning**
   - Decision: S3/MinIO for artifact blobs, PostgreSQL for metadata + version tracking
   - Rationale: Existing storage patterns, supports 30-day retention + cleanup jobs
   - Alternatives considered: MongoDB GridFS (no versioning support), local filesystem (not scalable)

6. **Execution timeout enforcement**
   - Decision: Celery task soft_time_limit + SIGTERM handler for graceful shutdown
   - Rationale: Per-tenant timeout configurable via task kwargs, allows state logging
   - Alternatives considered: Hard kill (loses partial outputs), worker-level timeout (not per-execution)

7. **Worker resource isolation**
   - Decision: Docker resource limits (2 CPU, 4GB RAM) + K8s resource requests/limits
   - Rationale: Prevents resource exhaustion, triggers OOM kill + restart, metrics for HPA
   - Alternatives considered: cgroups directly (more complex), no limits (risky)

8. **Failure detection and retry policy**
   - Decision: Celery task result tracking + exponential backoff with jitter (2^n * random(0.5-1.5))
   - Rationale: <5s detection via heartbeat checks, jitter prevents thundering herd
   - Alternatives considered: Fixed retry intervals (causes stampedes), no retry (bad UX)

**Output**: research.md with consolidated findings (to be generated)

## Phase 1: Design & Contracts

### Data Model Entities (data-model.md)

**ExecutionJob** (extends existing Execution model)
- **New Fields**:
  - `priority` (Integer, 0-10, default 5) - Tenant-specific priority
  - `queue_position` (Integer, nullable) - Current position in queue
  - `estimated_start_time` (DateTime, nullable) - Calculated from queue depth
  - `retry_count` (Integer, default 0) - Number of retry attempts
  - `timeout_seconds` (Integer, default 600) - Per-tenant timeout
  - `parent_execution_id` (UUID, nullable) - For re-executions
  - `artifact_version` (Integer, default 1) - Incremented on re-execution
  - `cancellation_requested` (Boolean, default False)
  - `cancelled_at` (DateTime, nullable)
  - `worker_id` (UUID, FK to WorkerInstance, nullable)
- **State Transitions**: pending → queued → in_progress → [completed | failed | cancelled]
- **Validation**:
  - `priority` in range 0-10
  - `timeout_seconds` >= 60, <= 3600
  - `retry_count` <= max_retries (tenant setting)

**ExecutionArtifact** (new model)
- **Fields**:
  - `id` (UUID, PK)
  - `tenant_id` (UUID, FK, indexed)
  - `execution_job_id` (UUID, FK to ExecutionJob)
  - `file_path` (String 500) - S3 key or filesystem path
  - `file_name` (String 255)
  - `file_size` (BigInteger) - Bytes
  - `mime_type` (String 100)
  - `artifact_type` (Enum: output_file, log_file, screenshot, data_export)
  - `version_number` (Integer, default 1)
  - `created_at` (DateTime)
  - `expires_at` (DateTime) - created_at + 30 days
- **Indexes**: `(execution_job_id, version_number)`, `(tenant_id, expires_at)`
- **Validation**:
  - `file_size` <= 100MB per artifact
  - `artifact_type` in defined enum

**WorkerInstance** (new model)
- **Fields**:
  - `id` (UUID, PK)
  - `worker_hostname` (String 255, unique)
  - `status` (Enum: idle, busy, crashed, stopping)
  - `current_job_id` (UUID, FK to ExecutionJob, nullable)
  - `cpu_usage_percent` (Float, 0-100)
  - `memory_usage_mb` (Integer)
  - `last_heartbeat_at` (DateTime)
  - `started_at` (DateTime)
  - `crashed_at` (DateTime, nullable)
- **Indexes**: `(status)`, `(last_heartbeat_at)`
- **Validation**:
  - `cpu_usage_percent` in range 0-100
  - Heartbeat timeout: 10 seconds (mark as crashed)

**QueuePosition** (ephemeral, Redis-backed)
- **Fields** (in-memory only):
  - `job_id` (UUID)
  - `position` (Integer)
  - `estimated_wait_seconds` (Integer)
  - `priority` (Integer)
  - `queued_at` (DateTime)
- **Storage**: Redis sorted set `queue:{priority}` with score=queued_at timestamp
- **Calculation**: Position = rank in sorted set, wait time = avg_execution_time * position

### API Contracts (contracts/)

**1. Execution Queue API** (`execution-queue-api.yaml`)
```yaml
POST /api/v1/executions/queue
  - Request: { execution_type, entity_id, input_params, priority? }
  - Response: { job_id, queue_position, estimated_start_time }
  - Auth: Tenant + User context

GET /api/v1/executions/{job_id}/status
  - Response: { status, queue_position?, worker_id?, started_at?, progress_percent? }

POST /api/v1/executions/{job_id}/cancel
  - Response: { cancelled: true, final_state_logged: boolean }

POST /api/v1/executions/{job_id}/re-execute
  - Response: { new_job_id, version_number }
```

**2. Execution Stream WebSocket** (`execution-stream-ws.yaml`)
```yaml
WS /ws/executions/{job_id}/stream
  - Events (server→client):
    - execution.started: { job_id, worker_id, started_at }
    - execution.output: { line, timestamp, stream_type: stdout|stderr }
    - execution.progress: { percent, current_step, total_steps }
    - execution.completed: { status, result_summary, artifacts[] }
    - execution.error: { error_type, message, traceback? }
  - Auth: JWT token in query param, tenant validation
  - Reconnection: Buffer last 100 lines, replay on reconnect
```

**3. Worker Management API** (`worker-management-api.yaml`) - Admin only
```yaml
GET /api/v1/admin/workers
  - Response: [{ worker_id, status, cpu%, memory_mb, current_job_id? }]

GET /api/v1/admin/workers/metrics
  - Response: { total_workers, active_workers, queue_depth, avg_execution_time }
```

**4. Artifact API** (`artifact-api.yaml`)
```yaml
GET /api/v1/executions/{job_id}/artifacts
  - Response: [{ artifact_id, file_name, file_size, mime_type, version, download_url }]

GET /api/v1/artifacts/{artifact_id}/download
  - Response: Pre-signed S3 URL or file stream
  - Auth: Tenant ownership check
```

### Contract Tests (tests/contract/)

**test_execution_queue_contract.py**
```python
def test_queue_execution_contract():
    """POST /api/v1/executions/queue matches OpenAPI schema"""
    # Should fail: endpoint not implemented yet

def test_execution_status_contract():
    """GET /api/v1/executions/{id}/status matches schema"""

def test_cancel_execution_contract():
    """POST /api/v1/executions/{id}/cancel matches schema"""
```

**test_execution_stream_contract.py**
```python
def test_websocket_connection_contract():
    """WS /ws/executions/{id}/stream accepts JWT auth"""

def test_stream_event_schemas():
    """All WebSocket events match defined schemas"""
```

### Integration Test Scenarios (from user stories)

**Scenario 1: User triggers execution, sees queue position**
```gherkin
Given: 2 workers busy with long-running tasks
When: User triggers new crew execution
Then:
  - Execution queued with position 3
  - Estimated wait time displayed
  - WebSocket connects to /ws/executions/{id}/stream
```

**Scenario 2: Worker crashes, execution retried**
```gherkin
Given: Worker executing task for 2 minutes
When: Worker container killed (simulate crash)
Then:
  - Worker marked as crashed within 5 seconds
  - Execution retried with exponential backoff (2^1 = 2s delay)
  - New worker assigned
  - Frontend shows "Retrying (attempt 1/3)"
```

**Scenario 3: User cancels execution**
```gherkin
Given: Execution in-progress for 5 minutes
When: User clicks "Cancel" button
Then:
  - POST /api/v1/executions/{id}/cancel succeeds
  - Worker receives SIGTERM signal
  - Worker logs partial outputs to artifacts
  - Execution marked as "cancelled" (not "failed")
  - WebSocket sends execution.completed event with status=cancelled
```

**Scenario 4: User re-executes with versioning**
```gherkin
Given: Completed execution with artifacts version 1
When: User clicks "Re-execute" button
Then:
  - New ExecutionJob created with parent_execution_id set
  - Artifacts saved with version_number=2
  - Execution detail page shows version comparison dropdown
```

### Quickstart (quickstart.md)

**quickstart.md** will contain:
1. **Setup**: Start 2 workers with `docker-compose -f docker-compose.worker.yml up`
2. **Trigger Execution**: POST /api/v1/executions/queue with sample crew
3. **Watch Live Stream**: Connect to WebSocket, see output in real-time
4. **Validate Queue**: Check queue position updates as workers drain queue
5. **Test Cancellation**: Cancel mid-execution, verify graceful shutdown
6. **Verify Artifacts**: Download execution artifacts, check versioning

### Agent Context Update

**Execute**: `.specify/scripts/bash/update-agent-context.sh claude`

Expected output: `CLAUDE.md` updated with:
- New technologies: Celery, Redis (task queue), python-socketio (streaming), K8s HPA
- Recent changes: "Added isolated worker architecture with live execution streaming"
- Key patterns: Priority queue, exponential backoff, WebSocket streaming

**Output**: data-model.md, contracts/*.yaml, failing tests, quickstart.md, CLAUDE.md

## Phase 2: Task Planning Approach
*This section describes what the /tasks command will do - DO NOT execute during /plan*

**Task Generation Strategy**:
1. Load `.specify/templates/tasks-template.md` as base
2. Generate tasks from Phase 1 artifacts:
   - **Data Model Tasks** (data-model.md):
     - T001: Create ExecutionJob model extensions (alembic migration)
     - T002: Create ExecutionArtifact model
     - T003: Create WorkerInstance model
     - T004: Create QueuePosition Redis schema
   - **Contract Test Tasks** (contracts/):
     - T005: Implement contract tests for execution queue API [P]
     - T006: Implement contract tests for WebSocket stream [P]
     - T007: Implement contract tests for artifact API [P]
   - **Service Tasks**:
     - T008: Implement queue_service.py (priority queue, position estimation)
     - T009: Implement worker_service.py (pool management, health checks)
     - T010: Implement artifact_service.py (versioning, S3 upload, cleanup)
     - T011: Implement retry_policy.py (exponential backoff with jitter)
   - **Worker Tasks**:
     - T012: Configure Celery app with Redis broker
     - T013: Implement execution_worker.py (main task, timeout handling)
     - T014: Implement stream_handler.py (WebSocket output streaming)
   - **API Endpoint Tasks**:
     - T015: Implement POST /api/v1/executions/queue
     - T016: Implement GET /api/v1/executions/{id}/status
     - T017: Implement POST /api/v1/executions/{id}/cancel
     - T018: Implement POST /api/v1/executions/{id}/re-execute
     - T019: Implement WS /ws/executions/{id}/stream
     - T020: Implement GET /api/v1/executions/{id}/artifacts
   - **Frontend Tasks**:
     - T021: Create LiveExecutionStream component
     - T022: Create QueuePosition component
     - T023: Create ArtifactList component with download
     - T024: Create ExecutionActions (cancel, re-execute)
     - T025: Implement useExecutionStream hook
   - **Infrastructure Tasks**:
     - T026: Create worker.Dockerfile
     - T027: Create docker-compose.worker.yml (2 workers)
     - T028: Create K8s worker-deployment.yaml
     - T029: Create K8s worker-hpa.yaml (80% CPU/mem)
   - **Integration Test Tasks** (quickstart scenarios):
     - T030: Test execution queueing and worker assignment
     - T031: Test live execution streaming
     - T032: Test worker crash and retry
     - T033: Test execution cancellation
     - T034: Test re-execution and versioning
     - T035: Test artifact download
     - T036: Test queue visualization

**Ordering Strategy**:
1. **Phase 1: Data Layer** (T001-T004) - Sequential, migrations depend on prior models
2. **Phase 2: Contract Tests** (T005-T007) - Parallel [P], independent files
3. **Phase 3: Core Services** (T008-T011) - Parallel [P] after data layer
4. **Phase 4: Worker Implementation** (T012-T014) - Sequential, Celery app → tasks → streaming
5. **Phase 5: API Endpoints** (T015-T020) - Parallel [P] after services
6. **Phase 6: Frontend** (T021-T025) - Parallel [P] after API endpoints
7. **Phase 7: Infrastructure** (T026-T029) - Sequential, Docker → K8s
8. **Phase 8: Integration Tests** (T030-T036) - Parallel [P] after all implementations

**Estimated Output**: 36 numbered, dependency-ordered tasks in tasks.md

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation
*These phases are beyond the scope of the /plan command*

**Phase 3**: Task execution (/tasks command creates tasks.md)
**Phase 4**: Implementation (execute tasks.md following constitutional principles)
**Phase 5**: Validation (run tests, execute quickstart.md, K8s HPA validation, load test 10k concurrent executions)

## Complexity Tracking
*Fill ONLY if Constitution Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Principle I (Partial): Workers not visually editable | Workers are backend infrastructure for execution isolation, not end-user feature | Making workers "visual" would expose unnecessary complexity to non-technical users. Users interact with executions (which remain visual), not worker internals. This maintains "seamless & transparent" UX. |

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
- [x] Initial Constitution Check: PASS (with documented justification)
- [x] Post-Design Constitution Check: PASS (backend infrastructure aligns with transparent UX)
- [x] All NEEDS CLARIFICATION resolved (clarifications in spec.md Session 2025-10-17)
- [x] Complexity deviations documented (Principle I partial compliance justified)

---
*Based on Constitution v2.0.0 - See `.specify/memory/constitution.md`*
