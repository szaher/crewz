# Rollback Guide: Worker Architecture Migration

**Feature**: 004-proper-isolation-and
**Last Updated**: 2025-10-17

---

## Overview

This document describes the **current (pre-migration) execution architecture** and provides rollback instructions if the worker architecture migration needs to be reverted.

---

## Current Execution Architecture (Legacy)

### Flow Description

**Synchronous execution in the main API process**:

1. **API Request**: Client calls execution endpoint (e.g., POST to flow/crew/agent/tool endpoint)
2. **Execution Record**: `ExecutionService.create_execution_async()` creates `Execution` record with `status=PENDING`
3. **Background Task**: `asyncio.create_task(self._execute_async(execution.id))` fires immediately in the same process
4. **Execution**: Task runs in FastAPI event loop via `asyncio.to_thread()`:
   - Flow: `FlowExecutor.execute_flow()` → backend/src/crewai/flow_executor.py
   - Crew: `CrewFactory.from_db_model()` + `crewai_crew.kickoff()`
   - Agent: `AgentFactory.from_db_model()` + `crew.kickoff()`
   - Tool: `DockerService.execute_tool()` or custom Python `exec()`
5. **Status Update**: Updates `Execution.status` to `COMPLETED` or `FAILED`
6. **Event Publishing**: Publishes events to Redis channel `executions:{id}` for SSE streaming
7. **Notifications**: Creates notifications via `NotificationService`

### Key Files

| File | Purpose | Lines |
|------|---------|-------|
| `backend/src/api/v1/executions.py` | Execution API endpoints | 1-635 |
| `backend/src/services/execution_service.py` | Execution lifecycle management | 1-836 |
| `backend/src/models/execution.py` | Execution model (PostgreSQL) | 1-67 |
| `backend/src/crewai/flow_executor.py` | Flow execution logic | - |
| `backend/src/crewai/crew_factory.py` | Crew creation from DB models | - |
| `backend/src/crewai/agent_factory.py` | Agent creation from DB models | - |

### Current Execution Model Schema

```python
class Execution(BaseModel):
    __tablename__ = "executions"

    # Core fields
    execution_type = Column(Enum(ExecutionType))  # flow, crew, agent, tool, task
    status = Column(Enum(ExecutionStatus))        # pending, running, completed, failed, cancelled

    # References (nullable - only one populated based on type)
    flow_id = Column(UUID, nullable=True)
    crew_id = Column(UUID, nullable=True)
    agent_id = Column(UUID, nullable=True)
    tool_id = Column(UUID, nullable=True)
    task_id = Column(UUID, nullable=True)
    user_id = Column(UUID, nullable=False)

    # Execution data
    input_data = Column(JSON, default=dict)
    output_data = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)

    # Performance metrics
    execution_time_ms = Column(Integer, nullable=True)

    # MongoDB reference for detailed logs
    mongo_log_id = Column(String(24), nullable=True)
```

**Status Values** (ExecutionStatus enum):
- `PENDING`: Execution created, not started
- `RUNNING`: Execution in progress
- `COMPLETED`: Execution finished successfully
- `FAILED`: Execution encountered error
- `CANCELLED`: Execution cancelled by user

### Current API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/executions` | GET | List all executions (paginated) |
| `/api/v1/executions/{id}` | GET | Get execution details |
| `/api/v1/executions/{id}/stream` | GET | SSE stream of execution events |
| `/api/v1/executions/{id}/cancel` | POST | Cancel running execution |
| `/api/v1/executions/submit` | POST | Submit execution (queue endpoints T038-T040) |
| `/api/v1/executions/queue/metrics` | GET | Queue metrics (T039) |
| `/api/v1/executions/dlq` | GET | Dead letter queue tasks (T040) |
| `/api/v1/executions/dlq/{id}/requeue` | POST | Requeue failed task (T040) |

### Current Characteristics

**Execution Model**:
- ✅ Single-process execution (no isolation)
- ✅ Immediate execution via `asyncio.create_task()`
- ✅ No queue management or priority ordering
- ✅ No retry policy
- ✅ No worker pool or autoscaling
- ✅ No artifact versioning
- ✅ Basic SSE streaming via Redis pub/sub
- ✅ Cancellation via status update (best-effort)

**Limitations**:
- ❌ No fault isolation (crashed execution can affect API server)
- ❌ No horizontal scaling (limited to single server concurrency)
- ❌ No queue position tracking
- ❌ No priority-based scheduling
- ❌ No execution timeout enforcement
- ❌ No automatic retry on failure
- ❌ No artifact capture or versioning
- ❌ No worker metrics or monitoring

---

## Baseline Test State

**Test File**: `backend/tests/integration/test_flow_execution.py`

**Status** (as of 2025-10-17):
- ❌ **FAILING** (pre-existing issues, unrelated to worker architecture)

**Error Summary**:
```
E       fixture 'test_tenant' not found
>       available fixtures: ... db_session, docker_service, ... test_user, ...
```

**Test Results**:
- 8 tests collected
- Multiple ERRORs due to missing `test_tenant` fixture
- Some FAILEDs on other issues (resource limits, timeouts)

**Action**:
- Baseline failures documented
- Will use alternative testing strategies (manual smoke tests, higher-level integration tests)
- Worker architecture tests will be independent

---

## Rollback Procedure

### Quick Rollback (Zero Code Changes)

If worker architecture is deployed but causing issues, **disable it immediately** via feature flag:

**Step 1**: Set environment variable in deployment:
```bash
# In docker-compose.yml, Kubernetes ConfigMap, or .env
ENABLE_WORKER_ARCHITECTURE=false
```

**Step 2**: Restart backend service:
```bash
docker-compose restart backend
# OR
kubectl rollout restart deployment/crewai-backend
```

**Result**: Executions revert to legacy synchronous mode in API process.

---

### Full Rollback (Remove Worker Code)

If rolling back permanently after migration:

**Step 1**: Revert code changes
```bash
git revert <migration-commit-range>
# OR
git reset --hard <pre-migration-commit>
```

**Step 2**: Rollback database migrations
```bash
# Inside backend container
docker-compose exec backend alembic downgrade -1  # Undo last migration
docker-compose exec backend alembic downgrade <revision>  # Undo to specific revision
```

**Step 3**: Remove worker containers
```bash
docker-compose -f infra/docker/docker-compose.worker.yml down
```

**Step 4**: Clean up Redis queue
```bash
docker exec -it crewai-redis redis-cli FLUSHDB
```

**Step 5**: Remove added dependencies
```bash
# Edit backend/requirements.txt - remove:
# - celery[redis]>=5.3.4
# - python-socketio>=5.11.0
# - boto3>=1.34.0  (if S3 artifacts added)

# Rebuild backend
docker-compose build backend
docker-compose up -d backend
```

---

## Validation After Rollback

**Smoke Test**:
1. Start backend: `docker-compose up -d backend`
2. Create flow execution via API
3. Check execution completes and status updates
4. Verify SSE stream works at `/executions/{id}/stream`
5. Test cancellation endpoint

**Expected Behavior**:
- ✅ Executions run synchronously in API process
- ✅ No Celery workers required
- ✅ SSE streaming via Redis pub/sub
- ✅ Notifications created
- ✅ Status: PENDING → RUNNING → COMPLETED/FAILED

---

## Migration Safety Checkpoints

The migration plan includes **12 validation checkpoints** to ensure safe rollout:

| Checkpoint | Task | Validation |
|------------|------|------------|
| T006 | Backend starts after config changes | `docker-compose up backend` succeeds |
| T015 | Create test execution after migrations | Execution record created successfully |
| T023 | Verify contract tests pass | All OpenAPI/AsyncAPI specs validated |
| T037 | Smoke test Celery worker startup | Workers register with Redis |
| T044 | Verify API still works in legacy mode | `ENABLE_WORKER_ARCHITECTURE=false` works |
| T055 | Test queue submission end-to-end | Queue → Worker → Completion flow |
| T061 | Enable workers and smoke test | First execution with workers |
| T067 | Integration test suite passes | All E2E scenarios pass |
| T074 | Load test queue under stress | 100 concurrent executions handled |
| T081 | Verify cancellation and timeout | Cancellation signal propagates to worker |
| T087 | Production monitoring configured | Metrics, logs, alerts set up |
| T092 | Final go/no-go decision | All acceptance criteria met |

**Abort Trigger**: If any checkpoint fails and cannot be fixed within 2 hours, **abort and rollback** immediately.

---

## Configuration Reference

### Current Settings (Pre-Migration)

**File**: `backend/src/config/settings.py`

```python
class Settings:
    # ===== Worker Architecture Feature Flag =====
    ENABLE_WORKER_ARCHITECTURE: bool = os.getenv("ENABLE_WORKER_ARCHITECTURE", "false").lower() == "true"

    # ===== Database Configuration =====
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    MONGODB_URL: str = os.getenv("MONGODB_URL", "")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")

    # ===== ClickHouse Configuration =====
    CLICKHOUSE_HOST: str = os.getenv("CLICKHOUSE_HOST", "clickhouse")
    CLICKHOUSE_PORT: int = int(os.getenv("CLICKHOUSE_PORT", "9000"))

    # ===== Security =====
    JWT_SECRET: str = os.getenv("JWT_SECRET", "dev_secret_change_in_production")
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "")

    # ... other settings ...
```

**Import Pattern**:
```python
from src.config import settings, is_worker_architecture_enabled

# Check feature flag
if is_worker_architecture_enabled():
    # Queue to Celery worker
    task.apply_async(args=[...])
else:
    # Execute synchronously in current process
    await execute_directly(...)
```

---

## Contacts and Support

**Migration Owner**: Claude (AI Assistant)
**Feature Spec**: `specs/004-proper-isolation-and/spec.md`
**Implementation Plan**: `specs/004-proper-isolation-and/plan.md`
**Task Tracker**: `specs/004-proper-isolation-and/tasks.md`

**Rollback Decision Authority**: Product Owner / Engineering Lead

---

## Appendix: Execution Flow Diagram (Current)

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ POST /api/v1/flows/{id}/execute
       ▼
┌─────────────────────────────────────────────────┐
│          FastAPI Server (Single Process)        │
│                                                  │
│  ┌────────────────────────────────────────┐    │
│  │  ExecutionService.create_execution()   │    │
│  │  - Create Execution (status=PENDING)   │    │
│  │  - Fire asyncio.create_task()          │    │
│  └─────────────────┬──────────────────────┘    │
│                    │                             │
│  ┌─────────────────▼──────────────────────┐    │
│  │  _execute_async()                      │    │
│  │  - Update status=RUNNING               │    │
│  │  - FlowExecutor.execute_flow()         │    │
│  │  - CrewFactory + kickoff()             │    │
│  │  - Update status=COMPLETED/FAILED      │    │
│  └─────────────────┬──────────────────────┘    │
│                    │                             │
└────────────────────┼─────────────────────────────┘
                     │
                     ▼ Publish events
            ┌─────────────────┐
            │  Redis Pub/Sub  │
            │  executions:{id}│
            └────────┬─────────┘
                     │
                     ▼ Subscribe
            ┌─────────────────┐
            │  SSE Client     │
            │  /stream        │
            └─────────────────┘
```

**Characteristics**:
- Single process (no isolation)
- Immediate execution (no queue)
- No retry or timeout enforcement
- No worker pool or autoscaling

---

**End of Rollback Guide**
