# Tasks: Isolated Worker Architecture for Async Execution (SAFE ROLLOUT)

**Feature**: 004-proper-isolation-and
**Input**: Design documents from `/specs/004-proper-isolation-and/`
**Prerequisites**: plan.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

## ⚠️ CRITICAL: Safety-First Approach

This feature requires **incremental rollout** with validation checkpoints to ensure zero-downtime deployment. Each phase includes smoke tests to verify system stability before proceeding.

### Existing System Analysis
- ✅ Execution model exists: `backend/src/models/execution.py`
- ✅ Execution API exists: `backend/src/api/v1/executions.py`
- ✅ Status enum: `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, `CANCELLED`
- ⚠️ Current execution: Synchronous in API process (no workers)

### Rollout Strategy
1. **Phase 1**: Add new fields to Execution model (nullable, no breaking changes)
2. **Phase 2**: Build worker infrastructure (disabled by default via feature flag)
3. **Phase 3**: Test workers in parallel with existing system
4. **Phase 4**: Switch to workers via feature flag
5. **Phase 5**: Remove old execution path after validation

---

## Path Conventions
- **Web app structure**: `backend/src/`, `backend/tests/`, `frontend/src/`, `frontend/tests/`
- **Infrastructure**: `infra/docker/`, `infra/k8s/`

---

## Phase 3.0: Pre-Flight Safety Checks

- [X] **T000** Create feature flag in `backend/src/config/settings.py` (add `ENABLE_WORKER_ARCHITECTURE: bool = False` - allows testing without affecting production)
- [X] **T001** Run existing execution tests to establish baseline in `backend/tests/` (execute: `pytest backend/tests/integration/ -k execution -v` - ALL must pass before proceeding)
- [X] **T002** Document current execution flow in `specs/004-proper-isolation-and/ROLLBACK.md` (capture FlowExecutor paths, dependencies, how to revert if needed)

---

## Phase 3.1: Setup & Dependencies

- [X] **T003** Add Celery worker dependencies to `backend/requirements.txt` (celery[redis]==5.3.4, gevent==23.9.1, kombu==5.3.4)
- [X] **T004** Create Celery configuration in `backend/src/workers/celery_app.py` (Redis broker, result backend, task discovery, disabled by default checking ENABLE_WORKER_ARCHITECTURE flag)
- [X] **T005** Create worker resource config in `backend/src/config/worker_config.py` (2 CPU, 4GB RAM limits, timeout defaults, retry settings, load from env vars)
- [X] **T006** **CHECKPOINT**: Verify backend still starts with new dependencies (`docker-compose up backend` - ensure no import errors, API responds on :8000)

---

## Phase 3.2: Data Models & Migrations (Safe Extensions)

- [X] **T007** [P] Create Alembic migration to extend Execution model in `backend/src/db/migrations/xxx_add_worker_fields.py` (Add nullable fields: priority DEFAULT 5, queue_position, estimated_start_time, retry_count DEFAULT 0, max_retries DEFAULT 3, timeout_seconds DEFAULT 600, parent_execution_id, artifact_version DEFAULT 1, cancellation_requested DEFAULT FALSE, cancelled_at, cancelled_by_user_id, worker_id - ALL NULLABLE to avoid breaking existing rows)
- [X] **T008** [P] Add new status enum values in migration (ALTER TYPE executionstatus ADD VALUE IF NOT EXISTS 'queued' - keep existing PENDING/RUNNING/COMPLETED/FAILED/CANCELLED)
- [X] **T009** [P] Create ExecutionArtifact model in `backend/src/models/execution_artifact.py` (file_path, file_name, file_size, mime_type, artifact_type enum, version_number, expires_at, tenant_id FK)
- [X] **T010** [P] Create WorkerInstance model in `backend/src/models/worker_instance.py` (worker_hostname UNIQUE, status enum, current_job_id FK, cpu_usage_percent, memory_usage_mb, last_heartbeat_at, crashed_at)
- [X] **T011** [P] Create Alembic migration for ExecutionArtifact table in `backend/src/db/migrations/xxx_create_execution_artifacts.py` (with indexes on execution_id+version, tenant_id+expires_at)
- [X] **T012** [P] Create Alembic migration for WorkerInstance table in `backend/src/db/migrations/xxx_create_worker_instances.py` (with indexes on status, last_heartbeat_at, worker_hostname UNIQUE)
- [X] **T013** Update model imports in `backend/src/models/__init__.py` (add ExecutionArtifact, WorkerInstance to __all__ list)
- [X] **T014** Run migrations: `cd backend && alembic upgrade head` (apply all schema changes)
- [X] **T015** **CHECKPOINT**: Create test execution using existing API (`POST /api/v1/flows/{id}/execute` - verify migration didn't break existing execution creation, check executions table has new NULL columns)

---

## Phase 3.3: Contract Tests (Write Tests First)

- [X] **T016** [P] Contract test for POST /api/v1/executions/queue in `backend/tests/contract/test_execution_queue_contract.py` (validate request/response schemas match OpenAPI spec in contracts/execution-queue-api.yaml)
- [X] **T017** [P] Contract test for GET /api/v1/executions/{id}/status in `backend/tests/contract/test_execution_status_contract.py` (verify queue_position, worker_id, retry_count fields)
- [X] **T018** [P] Contract test for POST /api/v1/executions/{id}/cancel in `backend/tests/contract/test_execution_cancel_contract.py` (validate cancellation_requested flag)
- [X] **T019** [P] Contract test for POST /api/v1/executions/{id}/re-execute in `backend/tests/contract/test_execution_reexecute_contract.py` (check version_number increment)
- [X] **T020** [P] Contract test for WebSocket /ws/executions/{id}/stream in `backend/tests/contract/test_execution_stream_contract.py` (validate event schemas: execution.started, execution.output, execution.progress, execution.completed, execution.error)
- [X] **T021** [P] Contract test for GET /api/v1/executions/{id}/artifacts in `backend/tests/contract/test_artifacts_list_contract.py` (verify artifact metadata fields)
- [X] **T022** [P] Contract test for GET /api/v1/artifacts/{id}/download in `backend/tests/contract/test_artifact_download_contract.py` (check presigned URL generation)

---

## Phase 3.4: Core Services (Build Workers Infrastructure)

- [X] **T023** [P] Implement retry policy with exponential backoff + jitter in `backend/src/workers/retry_policy.py` (calculate_backoff function: `2^n * random(0.5-1.5)`, max_retries from config, unit tests inline)
- [X] **T024** [P] Implement queue service in `backend/src/services/queue_service.py` (add_to_queue, get_position, estimate_wait_time using Redis sorted sets, priority routing 0-10, check ENABLE_WORKER_ARCHITECTURE flag)
- [X] **T025** [P] Implement worker service in `backend/src/services/worker_service.py` (register_worker, update_heartbeat, mark_as_crashed if heartbeat > 10s old, assign_job, release_job, get_pool_metrics)
- [X] **T026** [P] Implement artifact service in `backend/src/services/artifact_service.py` (upload_to_s3, create_artifact_record with versioning, generate_presigned_url, cleanup_expired_artifacts Celery beat task)
- [X] **T027** Create execution service wrapper in `backend/src/services/execution_service_worker.py` (NEW file - wraps existing execution_service, adds queue_execution, cancel_execution, reexecute_with_version, handle_worker_crash_retry - delegates to old service when flag disabled)
- [X] **T028** **CHECKPOINT**: Unit test all services in isolation (`pytest backend/tests/unit/test_*_service.py -v` - ensure queue, worker, artifact services work independently)

---

## Phase 3.5: Celery Worker Tasks (Disabled by Default)

- [X] **T029** Implement main execution worker task in `backend/src/workers/execution_worker.py` (execute_crew_task Celery task with soft_time_limit, timeout via SIGTERM, artifact capture, only runs if ENABLE_WORKER_ARCHITECTURE=True)
- [X] **T030** Implement WebSocket stream handler in `backend/src/workers/stream_handler.py` (capture stdout/stderr, emit execution.output events to Socket.IO room `execution:{job_id}`, buffer last 100 lines in Redis)
- [X] **T031** Implement worker health check periodic task in `backend/src/workers/health_check.py` (Celery beat task every 30s, marks workers crashed if heartbeat > 10s, requeues jobs with retry policy)
- [X] **T032** **CHECKPOINT**: Start Celery worker locally with flag disabled (`ENABLE_WORKER_ARCHITECTURE=False celery -A backend.src.workers.celery_app worker -l info` - worker should start but not process tasks, verify no errors)

---

## Phase 3.6: API Endpoints (New Routes, Don't Touch Existing)

- [X] **T033** Implement POST /api/v1/executions/queue in `backend/src/api/v1/executions.py` (NEW endpoint, add to router, validates tenant/priority/timeout, uses queue_service if flag enabled else falls back to old flow)
- [X] **T034** Update GET /api/v1/executions/{id}/status in `backend/src/api/v1/executions.py` (EXTEND existing endpoint, add queue_position, worker_id, retry_count to response when fields populated)
- [X] **T035** Implement POST /api/v1/executions/{id}/cancel in `backend/src/api/v1/executions.py` (NEW endpoint, sets cancellation_requested=True, sends Celery revoke if worker execution, else updates status directly)
- [X] **T036** Implement POST /api/v1/executions/{id}/re-execute in `backend/src/api/v1/executions.py` (NEW endpoint, clones execution with parent_execution_id, increments artifact_version)
- [X] **T037** Create artifacts endpoints in `backend/src/api/v1/artifacts.py` (NEW file, GET /artifacts for list, GET /artifacts/{id}/download for presigned URL, tenant ownership validation)
- [X] **T038** Update API router in `backend/src/api/v1/__init__.py` (add artifacts.router to api_router)
- [X] **T039** **CHECKPOINT**: Test new endpoints with flag disabled (`pytest backend/tests/integration/test_execution_endpoints.py` - /queue should fall back to old flow, existing /executions/{id} still works)

---

## Phase 3.7: WebSocket Implementation

- [X] **T040** Implement WebSocket endpoint /ws/executions/{id}/stream in `backend/src/websocket/execution_stream.py` (JWT auth from query param, join Socket.IO room, replay last 100 lines from Redis buffer, handle disconnect/reconnect)
- [X] **T041** Implement queue position updates WebSocket in `backend/src/websocket/queue_updates.py` (emit queue.position.updated events when Redis sorted set changes, broadcast to watching users)
- [X] **T042** Update WebSocket routing in `backend/src/main.py` (register new Socket.IO namespaces for execution streams)
- [X] **T043** **CHECKPOINT**: Test WebSocket connection (`wscat -c "ws://localhost:8000/ws/executions/test-id/stream?token=..."` - should connect even with flag disabled, no crash)

---

## Phase 3.8: Frontend Components (Feature-Flagged)

- [X] **T044** [P] Create LiveExecutionStream component in `frontend/src/components/executions/LiveExecutionStream.tsx` (WebSocket connection, display output lines with colors, auto-scroll, reconnection, shows "Live streaming not enabled" if flag false)
- [X] **T045** [P] Create QueuePosition component in `frontend/src/components/executions/QueuePosition.tsx` (displays position, estimated wait time, progress bar, hidden if queue_position null)
- [X] **T046** [P] Create ArtifactList component in `frontend/src/components/executions/ArtifactList.tsx` (table with file_name, size, download button, version dropdown, hidden if no artifacts)
- [X] **T047** [P] Create ExecutionActions component in `frontend/src/components/executions/ExecutionActions.tsx` (Cancel button with modal, Re-execute button, conditionally shown based on status)
- [X] **T048** Update ExecutionDetailPage in `frontend/src/app/executions/[id]/page.tsx` (EXTEND existing page, add LiveExecutionStream, QueuePosition, ArtifactList, ExecutionActions as optional sections)
- [X] **T049** **CHECKPOINT**: Frontend still works with backend flag disabled (`npm run dev` - execution detail page shows existing data, new components gracefully hidden)

---

## Phase 3.9: Frontend Hooks & Services

- [X] **T050** [P] Create useExecutionStream hook in `frontend/src/hooks/useExecutionStream.ts` (WebSocket connection manager, event parsing, reconnection with backoff, cleanup on unmount)
- [X] **T051** [P] Create useQueuePosition hook in `frontend/src/hooks/useQueuePosition.ts` (polls GET /status for queue_position, returns position + wait time, only if queue_position not null)
- [X] **T052** [P] Create useExecutionActions hook in `frontend/src/hooks/useExecutionActions.ts` (cancel mutation, re-execute mutation, invalidates React Query cache on success)
- [X] **T053** Update executionApi service in `frontend/src/services/executionApi.ts` (ADD new endpoints: POST /queue, POST /cancel, POST /re-execute, GET /artifacts - keep existing endpoints)
- [X] **T054** Implement websocketClient service in `frontend/src/services/websocketClient.ts` (Socket.IO client singleton, JWT injection, room helpers, connection pooling)

---

## Phase 3.10: Infrastructure (Workers Containers)

- [X] **T055** Create worker Dockerfile in `infra/docker/worker.Dockerfile` (FROM backend image, install gevent, set resource limits, ENTRYPOINT celery worker --concurrency=4 --pool=gevent)
- [X] **T056** Create docker-compose.worker.yml in `infra/docker/docker-compose.worker.yml` (worker1, worker2 services, Redis dependency, resource limits 2 CPU + 4GB RAM, volume mount backend code, depends_on backend)
- [X] **T057** Update main docker-compose.yml (add celery-beat service for health checks, ensure Redis service exists with persistence)
- [X] **T058** Create K8s worker deployment in `infra/k8s/worker-deployment.yaml` (replicas: 2, resources: requests=limits=2CPU+4Gi, env ENABLE_WORKER_ARCHITECTURE, readiness probe on worker heartbeat)
- [X] **T059** Create K8s HPA in `infra/k8s/worker-hpa.yaml` (min 2, max 500, targetCPU 80%, targetMemory 80%, behavior: scaleUp aggressive, scaleDown conservative)
- [X] **T060** **CHECKPOINT**: Start workers locally (`docker-compose -f infra/docker/docker-compose.worker.yml up` - workers start, register with Celery, no crashes, ready to accept tasks)

---

## Phase 3.11: Enable Workers & Test (Feature Flag ON)

- [X] **T061** Set ENABLE_WORKER_ARCHITECTURE=True in `.env` for local testing
- [X] **T062** Create smoke test execution via new queue endpoint (`curl -X POST http://localhost:8000/api/v1/executions/queue -d '{"execution_type":"crew","entity_id":"...","input_params":{}}'` - verify job queued, worker picks up, execution completes)
- [X] **T063** Monitor worker logs for errors (`docker-compose logs -f worker1 worker2` - check for task execution, no exceptions, proper cleanup)
- [X] **T064** Test live streaming (`wscat -c "ws://localhost:8000/ws/executions/{id}/stream?token=..."` - verify events received in real-time)
- [X] **T065** Test queue visualization (queue 3 jobs, verify position updates as workers drain queue)
- [X] **T066** **CHECKPOINT**: Workers fully functional, all smoke tests pass, ready for integration tests

---

## Phase 3.12: Integration Tests (Full System Validation)

- [X] **T067** [P] Integration test: Queue execution and worker assignment in `backend/tests/integration/test_execution_lifecycle.py` (queue 3 jobs, verify workers process, check final status, validate queue position updates)
- [X] **T068** [P] Integration test: Live execution streaming in `backend/tests/integration/test_live_streaming.py` (start execution, connect WebSocket, verify all event types received, test mid-execution reconnect)
- [X] **T069** [P] Integration test: Worker crash and retry in `backend/tests/integration/test_worker_crash_retry.py` (start execution, kill worker container, verify job retried with backoff on worker2, check retry_count incremented)
- [X] **T070** [P] Integration test: Execution cancellation in `backend/tests/integration/test_execution_cancellation.py` (start long job, POST /cancel, verify SIGTERM sent to Celery, status=cancelled, partial artifacts saved)
- [X] **T071** [P] Integration test: Re-execution with versioning in `backend/tests/integration/test_reexecution_versioning.py` (complete execution, POST /re-execute, verify parent_execution_id set, artifact_version=2, new execution queued)
- [X] **T072** [P] Integration test: Artifact download in `backend/tests/integration/test_artifact_download.py` (execution with artifacts, GET /artifacts list, GET /download presigned URL, verify S3 access works)
- [X] **T073** [P] Integration test: Priority queue ordering in `backend/tests/integration/test_queue_priority.py` (queue 5 jobs with priorities 0,5,10, verify execution order: 0 first, then 5, then 10)
- [X] **T074** [P] Integration test: Worker isolation in `backend/tests/integration/test_worker_isolation.py` (crash worker1 during execution, verify backend API still responsive, worker2 unaffected, main app uptime 100%)
- [X] **T075** **CHECKPOINT**: ALL integration tests pass (`pytest backend/tests/integration/test_*.py -v` - zero failures, workers stable)

---

## Phase 3.13: Frontend E2E Tests

- [X] **T076** [P] E2E test: Execution lifecycle in `frontend/tests/e2e/execution-lifecycle.spec.ts` (Playwright: queue via UI, watch live stream output, verify completion notification, download artifact)
- [X] **T077** [P] E2E test: Live streaming reliability in `frontend/tests/e2e/live-streaming.spec.ts` (start execution, verify output appears <500ms latency, disconnect/reconnect, verify buffer replay works)
- [X] **T078** [P] E2E test: Queue visualization in `frontend/tests/e2e/queue-visualization.spec.ts` (queue 3 jobs, verify position countdown, estimated time accuracy within 10%)
- [X] **T079** **CHECKPOINT**: All E2E tests pass (`npm run test:e2e` - Playwright suite green)

---

## Phase 3.14: Unit Tests & Polish

- [X] **T080** [P] Unit test: Retry policy math in `backend/tests/unit/test_retry_policy.py` (verify backoff = 2^n * jitter, jitter in [0.5,1.5], max_retries enforcement)
- [X] **T081** [P] Unit test: Queue position calculation in `backend/tests/unit/test_queue_service.py` (Redis sorted set ops, estimated_wait = position * avg_time, priority routing correctness)
- [X] **T082** [P] Unit test: Artifact versioning logic in `backend/tests/unit/test_artifact_versioning.py` (version increment on re-execute, expires_at = created_at + 30d, parent linking)
- [X] **T083** [P] Unit test: Worker health check in `backend/tests/unit/test_worker_service.py` (heartbeat timeout detection, job reassignment, metrics calculation accuracy)
- [X] **T084** [P] Add docstrings to Celery tasks in `backend/src/workers/*.py` (task signatures, params, return values, example usage)
- [X] **T085** [P] Add API docs in `backend/src/api/v1/executions.py` and `artifacts.py` (FastAPI autodoc annotations, example request/response)
- [X] **T086** [P] Component documentation in `frontend/src/components/executions/*.tsx` (JSDoc for props, usage examples)

---

## Phase 3.15: Production Readiness

- [X] **T087** Run quickstart.md validation (`specs/004-proper-isolation-and/quickstart.md` - execute all 8 steps manually, verify success criteria met, document deviations)
- [X] **T088** Performance test: 100 concurrent executions in `backend/tests/performance/test_concurrent_load.py` (queue 100 jobs, measure completion time, verify <5min with 2 workers, check memory leaks via `docker stats`)
- [X] **T089** Security audit: Tenant isolation (`backend/tests/security/test_tenant_isolation.py` - verify no cross-tenant execution access, S3 presigned URLs scoped, JWT validation on WebSocket)
- [X] **T090** Create monitoring dashboard config in `infra/monitoring/grafana-dashboard.json` (panels for: queue depth, worker CPU/memory, execution throughput, error rate, P95 latency)
- [X] **T091** Document rollback procedure in `specs/004-proper-isolation-and/ROLLBACK.md` (steps to disable workers: set flag=False, restart backend, verify old execution flow works, how to drain queue)
- [X] **T092** **FINAL CHECKPOINT**: Production readiness review (all tests pass, performance acceptable, monitoring in place, rollback tested, team trained)

---

## Dependencies & Critical Path

### Setup & Safety (T000-T006)
- T000-T002: Sequential (feature flag → baseline tests → rollback docs)
- T003-T005: Parallel [P] (dependencies, Celery config, worker config)
- T006: Checkpoint blocks all subsequent work

### Data Layer (T007-T015)
- T007-T012: Parallel [P] (independent migrations)
- T013-T014: Sequential (import updates → run migrations)
- T015: Checkpoint - system must still work

### Contract Tests (T016-T022)
- All parallel [P] after T015 checkpoint

### Services (T023-T028)
- T023-T026: Parallel [P] (independent service files)
- T027: Sequential (wraps others)
- T028: Checkpoint - unit tests must pass

### Workers (T029-T032)
- T029-T031: Sequential (execution_worker → stream → health)
- T032: Checkpoint - workers start cleanly

### API & WebSocket (T033-T043)
- T033-T038: Parallel [P] (different endpoints)
- T039: Checkpoint - endpoints work with flag off
- T040-T042: Sequential (WebSocket setup)
- T043: Checkpoint - WebSocket connects

### Frontend (T044-T054)
- T044-T047: Parallel [P] (independent components)
- T048-T049: Sequential (page integration → checkpoint)
- T050-T054: Parallel [P] (hooks and services)

### Infrastructure (T055-T060)
- T055-T059: Sequential (Dockerfile → compose → K8s)
- T060: Checkpoint - workers deployable

### Enable & Test (T061-T066)
- T061-T065: Sequential (enable flag → smoke tests)
- T066: Checkpoint - workers fully functional

### Integration Tests (T067-T075)
- T067-T074: Parallel [P] (independent test scenarios)
- T075: Checkpoint - ALL must pass

### E2E & Polish (T076-T092)
- T076-T078: Parallel [P] (Playwright tests)
- T079: Checkpoint
- T080-T086: Parallel [P] (unit tests + docs)
- T087-T092: Sequential (validation → perf → security → monitoring → rollback → final review)

---

## Parallel Execution Examples

### Safe Parallel: Services (after T015 checkpoint)
```bash
# T023-T026 together (4 independent files):
Task: "Implement retry policy in backend/src/workers/retry_policy.py"
Task: "Implement queue service in backend/src/services/queue_service.py"
Task: "Implement worker service in backend/src/services/worker_service.py"
Task: "Implement artifact service in backend/src/services/artifact_service.py"
```

### Safe Parallel: Integration Tests (after T066 checkpoint)
```bash
# T067-T074 together (8 independent test files):
Task: "Test execution lifecycle in backend/tests/integration/test_execution_lifecycle.py"
Task: "Test live streaming in backend/tests/integration/test_live_streaming.py"
Task: "Test worker crash in backend/tests/integration/test_worker_crash_retry.py"
# ... (all 8 tests)
```

---

## Validation Checklist

- [x] All contracts have tests (T016-T022)
- [x] All entities have models (T007-T012)
- [x] Tests before implementation (contract tests before endpoints)
- [x] All [P] tasks use different files (verified)
- [x] Each task has exact file paths (included)
- [x] Checkpoints after risky changes (6 checkpoints: T006, T015, T028, T032, T039, T043, T049, T060, T066, T075, T079, T092)
- [x] Feature flag for safe rollout (T000)
- [x] Rollback documentation (T002, T091)
- [x] Smoke tests before migration (T001)
- [x] Smoke tests after migration (T015)

---

## Summary

- **Total Tasks**: 92 (up from 68)
- **Safety Tasks Added**: 24 (checkpoints, feature flags, rollback, smoke tests)
- **Checkpoints**: 12 validation gates
- **Parallel Tasks**: 48 marked [P]
- **Critical Path**: ~30 hours sequential, ~12 hours with 4 parallel agents
- **Rollback Time**: <5 minutes (disable flag, restart backend)

### Key Safety Features
✅ Feature flag (ENABLE_WORKER_ARCHITECTURE) for gradual rollout
✅ 12 validation checkpoints to catch issues early
✅ Safe migrations (all new fields nullable/defaulted)
✅ Smoke tests after every risky change
✅ Documented rollback procedure
✅ No backward compatibility burden (clean migration)
✅ System stability validated at each phase

**Next**: Execute tasks sequentially through checkpoints, validating system health before proceeding to next phase.
