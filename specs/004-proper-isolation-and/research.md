# Research: Isolated Worker Architecture for Async Execution

**Feature**: 004-proper-isolation-and
**Date**: 2025-10-17
**Status**: Complete

## Research Questions

This document consolidates research findings for all technical decisions required to implement isolated worker architecture with live execution streaming, priority queuing, and auto-scaling.

---

## 1. Celery + Redis Architecture for Isolated Workers

### Decision
Use **Celery** workers running in separate Docker containers with **Redis** as both broker and result backend.

### Rationale
- **Mature ecosystem**: Celery 5.3.4 is production-ready with extensive documentation
- **Built-in features**: Retry policies, priority queues, task routing, result persistence
- **Isolation**: Workers run in separate processes/containers, crashes don't affect main app
- **Already installed**: Celery listed in requirements.txt line 22
- **Redis efficiency**: Single Redis instance serves as broker (queue) + backend (results) + pub/sub (streaming)

### Alternatives Considered
- **RabbitMQ as broker**: More complex setup, requires separate service, overkill for initial scale
- **Direct multiprocessing**: No true isolation, shared memory risks, no distributed execution
- **AWS SQS + Lambda**: Vendor lock-in, higher latency, cost at 10k concurrent scale

### Implementation Notes
- Workers connect to shared Redis instance
- Task serialization: JSON (default) for simple types, pickle for complex CrewAI objects
- Result expiry: 30 days (matches artifact retention requirement)
- Worker concurrency: 4 tasks/worker (2 CPU cores → 2 threads per CPU for I/O-bound LLM calls)

---

## 2. WebSocket Streaming for Live Execution Output

### Decision
Use **python-socketio** (backend) and native WebSocket client (frontend React) for bidirectional live streaming.

### Rationale
- **Already integrated**: python-socketio 5.10.0 in requirements.txt line 53
- **Room-based broadcasting**: Multiple users can watch same execution via Socket.IO rooms
- **Reconnection handling**: Built-in reconnection with exponential backoff
- **Bidirectional**: Workers can stream output, frontend can send cancel signals
- **Event-based**: Structured events (execution.started, execution.output, execution.completed)

### Alternatives Considered
- **Server-Sent Events (SSE)**: One-way only, can't handle cancellation signals, less feature-rich
- **HTTP polling**: 500ms latency requirement impossible, high server load
- **gRPC streams**: Requires protobuf, overkill for web clients, browser support limited

### Implementation Notes
- WebSocket endpoint: `/ws/executions/{job_id}/stream`
- Authentication: JWT token in query parameter `?token=...`
- Buffer size: Last 100 lines kept in Redis for late-joining clients
- Heartbeat: 25s ping to keep connections alive (AWS ALB 60s timeout)
- Rooms: `execution:{job_id}` for multi-user streaming

---

## 3. Priority Queue Implementation

### Decision
Use **Celery priority routing** with custom priority headers and **Redis sorted sets** for queue position tracking.

### Rationale
- **Native Celery support**: Priority routing via `task.apply_async(priority=X)`
- **Per-tenant priorities**: Custom header `x-tenant-priority` for priority calculation
- **Position tracking**: Redis sorted set `queue:{priority}` with score=queued_at timestamp
- **Estimated wait time**: Calculate from `(position * avg_execution_time)` using rolling average

### Alternatives Considered
- **Custom queue service**: Reinventing Celery's battle-tested routing, high complexity
- **Database-backed queue**: Polling overhead, can't match Redis sorted set performance
- **Single FIFO queue**: Doesn't meet priority-based requirement from clarifications

### Implementation Notes
- Priority levels: 0-10 (0=highest, 10=lowest), default=5
- Tenant-specific adjustments: Premium tenants get priority boost (-2)
- Queue depth metric: `ZCARD queue:{priority}` for monitoring
- Position calculation: `ZRANK queue:{priority} {job_id}` → O(log N)

---

## 4. Kubernetes Horizontal Pod Autoscaler (HPA) Configuration

### Decision
Use **K8s HPA** targeting **80% CPU + memory utilization** with custom metrics for queue depth.

### Rationale
- **Matches requirement**: 80% threshold specified in clarifications
- **Industry standard**: HPA widely adopted, well-documented, robust
- **Dual metrics**: CPU + memory prevents single-dimension bottlenecks
- **Custom metrics**: Extend with queue depth via Prometheus adapter for proactive scaling
- **Graceful scaling**: HPA respects pod disruption budgets, drains tasks before termination

### Alternatives Considered
- **Manual scaling**: Doesn't meet auto-scaling requirement, operator overhead
- **KEDA (Kubernetes Event-Driven Autoscaling)**: Overkill for MVP, adds complexity
- **Custom controller**: Reinventing HPA, maintenance burden

### Implementation Notes
- Min replicas: 2 (initial requirement), max replicas: 50 (calculated for 10k concurrent)
- Scale-up policy: Aggressive (1 pod/10s when > 80%)
- Scale-down policy: Conservative (1 pod/5min when < 50% for 5min)
- Metrics server: K8s metrics-server for CPU/memory, Prometheus for queue depth
- Target queue depth: <20 jobs/worker (triggers proactive scaling)

---

## 5. Artifact Storage and Versioning

### Decision
Use **S3/MinIO** for artifact blobs and **PostgreSQL** for metadata + version tracking.

### Rationale
- **Separation of concerns**: Blob storage (S3) separate from metadata (PostgreSQL)
- **Existing patterns**: Platform already uses S3 for file storage
- **Versioning**: PostgreSQL tracks version_number, parent_execution_id for re-executions
- **Retention**: S3 lifecycle policy + PostgreSQL expires_at for 30-day cleanup
- **Multi-tenancy**: S3 prefix `tenants/{tenant_id}/executions/{job_id}/` for isolation

### Alternatives Considered
- **MongoDB GridFS**: No native versioning, query performance for version history poor
- **Local filesystem**: Not scalable to K8s multi-node, no replication
- **PostgreSQL BYTEA**: 100MB artifacts exceed practical BYTEA limits, backup bloat

### Implementation Notes
- S3 bucket structure: `{bucket}/tenants/{tenant_id}/executions/{execution_id}/v{version}/{filename}`
- Metadata fields: artifact_id, execution_job_id, file_path (S3 key), version_number, expires_at
- Cleanup job: Celery periodic task (daily) deletes S3 objects + DB rows where expires_at < now()
- Presigned URLs: 1-hour expiry for download links (POST /artifacts/{id}/download)

---

## 6. Execution Timeout Enforcement

### Decision
Use **Celery soft_time_limit** with custom **SIGTERM handler** for graceful shutdown.

### Rationale
- **Per-execution timeout**: Celery task kwargs `soft_time_limit=600` (default 10min)
- **Graceful shutdown**: SIGTERM allows worker to log partial outputs, save artifacts
- **Tenant-configurable**: Timeout from tenant settings, passed as task parameter
- **Partial results**: State logged before termination (better UX than hard kill)

### Alternatives Considered
- **Hard time_limit**: SIGKILL doesn't allow state logging, loses partial outputs
- **Worker-level timeout**: Can't differentiate per-execution, all tasks same timeout
- **External watchdog**: Adds complexity, Celery built-in sufficient

### Implementation Notes
- Soft limit: `task.apply_async(soft_time_limit=timeout_seconds)`
- Signal handler: Catches `SoftTimeLimitExceeded`, logs output buffer, saves to artifacts
- Hard limit: `soft_time_limit + 60s` grace period before SIGKILL
- Timeout error: Execution marked as "failed" with error_type="timeout"

---

## 7. Worker Resource Isolation

### Decision
Use **Docker resource limits** (2 CPU, 4GB RAM) and **K8s resource requests/limits**.

### Rationale
- **Prevents exhaustion**: Memory limit triggers OOM kill, CPU limit prevents starvation
- **Predictable scaling**: Fixed resources per worker → calculable max workers for 10k concurrent
- **HPA metrics**: Resource requests/limits enable accurate CPU% / memory% metrics
- **Isolation guarantee**: cgroups enforce limits at kernel level

### Alternatives Considered
- **cgroups directly**: More complex, Docker/K8s abstract this, no benefit
- **No limits**: Workers could consume entire node resources, cascade failures
- **Smaller limits** (1 CPU, 2GB): LLM API calls I/O-bound, but CrewAI orchestration needs headroom

### Implementation Notes
- Docker: `deploy.resources.limits: {cpus: '2', memory: '4096M'}`
- K8s: `resources: {requests: {cpu: 2, memory: 4Gi}, limits: {cpu: 2, memory: 4Gi}}`
- Worker concurrency: 4 tasks/worker (based on 2 CPU, I/O-bound LLM calls)
- Max workers calculation: 10,000 concurrent / 4 tasks/worker = 2,500 workers (theoretical max)

---

## 8. Failure Detection and Retry Policy

### Decision
Use **Celery task result tracking** with **exponential backoff + jitter** (`2^n * random(0.5-1.5)`).

### Rationale
- **<5s detection**: Celery worker heartbeat every 2s, broker timeout at 5s → crash detected
- **Exponential backoff**: Prevents retry storms (2s, 4s, 8s, 16s, 32s delays)
- **Jitter**: Random factor 0.5-1.5 prevents thundering herd when batch fails
- **Configurable retries**: Max retries per tenant (default 3), then mark as permanently failed

### Alternatives Considered
- **Fixed retry intervals**: Causes synchronized retries, stampedes broker/workers
- **No retry**: Bad UX, transient failures (network blips) cause user-visible errors
- **Linear backoff**: Insufficient delay reduction, still risk of stampede

### Implementation Notes
- Celery retry config: `autoretry_for=(Exception,)`, `retry_backoff=True`, `retry_jitter=True`
- Max retries: `max_retries=3` (tenant setting, default)
- Backoff formula: `delay = (2 ** retry_count) * random.uniform(0.5, 1.5)`
- Retry tracking: `retry_count` field in ExecutionJob model, incremented per attempt
- Permanent failure: After max_retries, status="failed", error_type="max_retries_exceeded"

---

## 9. Worker Concurrency Calculation for 10,000 Concurrent Executions

### Decision
**4 tasks per worker**, requiring **2,500 workers at theoretical max**, **~250 workers for realistic load**.

### Rationale
- **I/O-bound workload**: LLM API calls (OpenAI, Anthropic) are network I/O, not CPU-bound
- **Concurrency per worker**: 2 CPU cores × 2 greenlets/core (gevent) = 4 concurrent tasks
- **Realistic load**: 10k concurrent unlikely simultaneously, assume 10% peak → 1,000 concurrent → 250 workers
- **HPA scaling**: Start with 2 workers, scale to 250 workers at 80% utilization

### Alternatives Considered
- **1 task/worker** (process pool): Requires 10,000 workers, infeasible resource cost
- **Higher concurrency** (16+ tasks/worker): Context switching overhead, diminishing returns

### Implementation Notes
- Worker concurrency: `celery worker --concurrency=4 --pool=gevent`
- Min replicas: 2, max replicas: 500 (headroom above 250 realistic peak)
- HPA scale trigger: 80% CPU or memory, or queue depth > 20 tasks/worker
- Expected steady-state: 20-50 workers for typical load (200-400 concurrent executions)

---

## 10. Multi-Tenancy and Authorization Patterns

### Decision
Maintain **existing platform patterns**: UUIDv7 identifiers, tenant_id scoping, JWT-based authz.

### Rationale
- **Consistency**: Aligns with existing models (Execution, Agent, Crew all have tenant_id)
- **Isolation**: All queries filtered by `tenant_id`, worker tasks validate tenant context
- **Authorization**: JWT contains tenant_id, validated at API layer before queueing
- **Audit trail**: tenant_id in all execution logs, artifacts, worker metrics

### Implementation Notes
- ExecutionJob.tenant_id: FK to tenants table, indexed, NOT NULL
- Worker task signature: `execute_crew.apply_async(args=[job_id], headers={'x-tenant-id': str(tenant_id)})`
- Artifact isolation: S3 prefix includes tenant_id, download endpoint checks ownership
- WebSocket auth: JWT decoded to extract tenant_id, only allow streaming own tenant's executions

---

## Summary of Decisions

| Component | Technology | Rationale |
|-----------|------------|-----------|
| **Task Queue** | Celery 5.3.4 + Redis | Mature, built-in retry/priority, isolation |
| **Live Streaming** | python-socketio + WebSocket | Already integrated, bidirectional, room-based |
| **Priority Queue** | Celery priority + Redis sorted sets | Native support, O(log N) position tracking |
| **Auto-scaling** | K8s HPA (80% CPU/mem) | Industry standard, custom metrics extensible |
| **Artifacts** | S3/MinIO (blobs) + PostgreSQL (metadata) | Scalable, versioning, existing patterns |
| **Timeout** | Celery soft_time_limit + SIGTERM | Graceful shutdown, partial outputs preserved |
| **Resource Limits** | Docker/K8s limits (2 CPU, 4GB RAM) | Isolation, predictable scaling, HPA metrics |
| **Retry Policy** | Exponential backoff + jitter | <5s detection, prevents stampedes |
| **Concurrency** | 4 tasks/worker (gevent pool) | I/O-bound workload, 250 workers @ peak |
| **Multi-tenancy** | UUIDv7, tenant_id scoping, JWT authz | Existing platform patterns, consistent |

---

**Next Phase**: Generate data-model.md, contracts/, quickstart.md (Phase 1)
