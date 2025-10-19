# Data Model: Isolated Worker Architecture

**Feature**: 004-proper-isolation-and
**Date**: 2025-10-17
**Status**: Design Complete

## Overview

This document defines the data model extensions and new entities required for isolated worker architecture with live execution streaming, priority queueing, artifact versioning, and worker pool management.

---

## Entity Definitions

### 1. ExecutionJob (Extends Existing `Execution` Model)

**Purpose**: Tracks execution requests with queue position, priority, retry state, and worker assignment.

**New Fields** (added to existing Execution model):

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `priority` | Integer | NOT NULL, DEFAULT 5, CHECK(0 ≤ priority ≤ 10) | Execution priority (0=highest, 10=lowest) |
| `queue_position` | Integer | NULLABLE | Current position in queue (null when not queued) |
| `estimated_start_time` | DateTime | NULLABLE | Calculated from queue depth * avg execution time |
| `retry_count` | Integer | NOT NULL, DEFAULT 0, CHECK(retry_count ≥ 0) | Number of retry attempts made |
| `max_retries` | Integer | NOT NULL, DEFAULT 3 | Maximum retries allowed (from tenant settings) |
| `timeout_seconds` | Integer | NOT NULL, DEFAULT 600, CHECK(60 ≤ timeout_seconds ≤ 3600) | Per-tenant timeout (10min default) |
| `parent_execution_id` | UUID | NULLABLE, FK(executions.id) | Parent execution for re-executions |
| `artifact_version` | Integer | NOT NULL, DEFAULT 1, CHECK(artifact_version ≥ 1) | Version number for re-executions |
| `cancellation_requested` | Boolean | NOT NULL, DEFAULT FALSE | User requested cancellation |
| `cancelled_at` | DateTime | NULLABLE | Timestamp when cancelled |
| `cancelled_by_user_id` | UUID | NULLABLE, FK(users.id) | User who cancelled execution |
| `worker_id` | UUID | NULLABLE, FK(worker_instances.id) | Assigned worker instance |

**Existing Fields** (used by this feature):
- `id` (UUID, PK)
- `tenant_id` (UUID, FK, indexed)
- `user_id` (UUID, FK)
- `status` (Enum: pending, queued, in_progress, completed, failed, cancelled)
- `execution_type` (Enum: crew, flow, task)
- `entity_id` (UUID) - ID of crew/flow/task being executed
- `input_parameters` (JSONB)
- `result_data` (JSONB)
- `created_at`, `updated_at` (DateTime)

**State Transitions**:
```
pending → queued → in_progress → [completed | failed | cancelled]
                  ↓ (crash)
                  queued (retry with backoff)
```

**Indexes**:
- `idx_executions_tenant_status` (tenant_id, status)
- `idx_executions_queue_position` (queue_position) WHERE status='queued'
- `idx_executions_worker` (worker_id) WHERE status='in_progress'
- `idx_executions_parent` (parent_execution_id)

**Validation Rules**:
1. `priority` must be 0-10 (enforced by CHECK constraint)
2. `timeout_seconds` must be 60-3600 (1min - 1hour)
3. `retry_count` must not exceed `max_retries`
4. `cancellation_requested = TRUE` implies `status IN ('in_progress', 'queued')`
5. `parent_execution_id` must reference completed/failed execution (for re-execution)
6. `artifact_version` increments for re-executions of same parent

---

### 2. ExecutionArtifact (New Model)

**Purpose**: Tracks output files, logs, and data exports produced by executions with versioning support.

**Fields**:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PK | Artifact identifier (UUIDv7) |
| `tenant_id` | UUID | NOT NULL, FK(tenants.id), indexed | Tenant ownership |
| `execution_job_id` | UUID | NOT NULL, FK(executions.id) | Execution that produced artifact |
| `file_path` | String(500) | NOT NULL | S3 key or filesystem path |
| `file_name` | String(255) | NOT NULL | Original filename |
| `file_size` | BigInteger | NOT NULL, CHECK(file_size ≤ 104857600) | Size in bytes (≤100MB) |
| `mime_type` | String(100) | NOT NULL | MIME type (e.g., application/json) |
| `artifact_type` | Enum | NOT NULL | output_file, log_file, screenshot, data_export |
| `version_number` | Integer | NOT NULL, DEFAULT 1, CHECK(version_number ≥ 1) | Version (matches execution artifact_version) |
| `checksum_sha256` | String(64) | NULLABLE | SHA-256 hash for integrity verification |
| `created_at` | DateTime | NOT NULL, DEFAULT NOW() | Upload timestamp |
| `expires_at` | DateTime | NOT NULL | Deletion timestamp (created_at + 30 days) |

**Indexes**:
- `idx_artifacts_execution` (execution_job_id, version_number)
- `idx_artifacts_tenant_expiry` (tenant_id, expires_at)
- `idx_artifacts_expiry` (expires_at) - For cleanup jobs

**Validation Rules**:
1. `file_size` ≤ 100MB (104857600 bytes) per artifact
2. `artifact_type` must be in defined enum: ['output_file', 'log_file', 'screenshot', 'data_export']
3. `expires_at` = `created_at` + 30 days (enforced by application, configurable)
4. `file_path` format: `tenants/{tenant_id}/executions/{execution_id}/v{version}/{file_name}`

**S3 Bucket Structure**:
```
bucket-name/
└── tenants/
    └── {tenant_id}/
        └── executions/
            └── {execution_id}/
                ├── v1/
                │   ├── output.json
                │   └── execution.log
                └── v2/  (re-execution)
                    ├── output.json
                    └── execution.log
```

---

### 3. WorkerInstance (New Model)

**Purpose**: Tracks worker container health, resource usage, and current job assignment for monitoring and scaling.

**Fields**:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PK | Worker identifier (UUIDv7) |
| `worker_hostname` | String(255) | NOT NULL, UNIQUE | Container hostname (e.g., worker-7f3a9) |
| `status` | Enum | NOT NULL | idle, busy, crashed, stopping |
| `current_job_id` | UUID | NULLABLE, FK(executions.id) | Current execution (null when idle) |
| `cpu_usage_percent` | Float | NOT NULL, DEFAULT 0, CHECK(0 ≤ cpu_usage_percent ≤ 100) | Current CPU % |
| `memory_usage_mb` | Integer | NOT NULL, DEFAULT 0, CHECK(0 ≤ memory_usage_mb ≤ 4096) | Current memory usage (MB) |
| `last_heartbeat_at` | DateTime | NOT NULL | Last successful heartbeat |
| `started_at` | DateTime | NOT NULL | Worker container start time |
| `crashed_at` | DateTime | NULLABLE | Crash timestamp (null when healthy) |
| `worker_version` | String(50) | NOT NULL | Worker image version/tag |

**Indexes**:
- `idx_workers_status` (status)
- `idx_workers_heartbeat` (last_heartbeat_at) WHERE status IN ('idle', 'busy')
- `idx_workers_hostname` (worker_hostname)

**Validation Rules**:
1. `cpu_usage_percent` must be 0-100
2. `memory_usage_mb` must be 0-4096 (max 4GB resource limit)
3. **Heartbeat timeout**: If `NOW() - last_heartbeat_at` > 10 seconds → mark as crashed
4. `status='busy'` implies `current_job_id IS NOT NULL`
5. `status='idle'` implies `current_job_id IS NULL`

**State Transitions**:
```
started → idle → busy → idle → stopping → (terminated)
              ↓ (heartbeat timeout)
            crashed → (auto-restart) → started
```

**Metrics Calculation**:
- **Worker pool utilization**: `COUNT(status='busy') / COUNT(status IN ('busy','idle'))` * 100%
- **Average CPU**: `AVG(cpu_usage_percent)` WHERE status='busy'
- **Queue depth**: Calculated from Redis sorted sets (not stored here)

---

### 4. QueuePosition (Ephemeral, Redis-Backed)

**Purpose**: Provides real-time queue position and estimated wait time for queued executions.

**Storage**: Redis sorted set `queue:{priority}` with score = `queued_at` timestamp (Unix epoch millis)

**Fields** (in-memory representation only, not PostgreSQL):

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | UUID | Execution job ID |
| `position` | Integer | Position in queue (1-indexed) |
| `estimated_wait_seconds` | Integer | Estimated time until execution starts |
| `priority` | Integer | Priority level (0-10) |
| `queued_at` | DateTime | Timestamp when added to queue |

**Redis Operations**:

| Operation | Redis Command | Description |
|-----------|---------------|-------------|
| Add to queue | `ZADD queue:{priority} {timestamp} {job_id}` | Insert with queued_at as score |
| Get position | `ZRANK queue:{priority} {job_id}` | Returns 0-indexed rank → add 1 for position |
| Get queue depth | `ZCARD queue:{priority}` | Count of items in queue |
| Remove from queue | `ZREM queue:{priority} {job_id}` | When worker picks up job |
| Pop next job | `ZPOPMIN queue:{priority}` | Earliest queued job (lowest score) |

**Position Calculation**:
```python
position = redis.zrank(f"queue:{priority}", job_id) + 1  # 0-indexed → 1-indexed
```

**Estimated Wait Time Calculation**:
```python
avg_execution_time = get_rolling_average()  # From last 100 executions
estimated_wait_seconds = position * avg_execution_time
```

**Priority Routing**:
- Higher priority queues (0, 1, 2) checked first by workers
- Within same priority, FIFO (sorted by queued_at timestamp)
- Tenant-specific priority boost: Premium tenants get priority - 2

---

## Relationships

```
Execution (ExecutionJob)
├── 1:N → ExecutionArtifact (execution_job_id FK)
├── N:1 → WorkerInstance (worker_id FK)
├── 1:N → Execution (parent_execution_id self-FK)
├── N:1 → Tenant (tenant_id FK)
└── N:1 → User (user_id FK, cancelled_by_user_id FK)

ExecutionArtifact
├── N:1 → Execution (execution_job_id FK)
└── N:1 → Tenant (tenant_id FK)

WorkerInstance
└── 1:1 → Execution (current_job_id FK) [nullable]

QueuePosition (Redis)
└── Ephemeral mapping to Execution by job_id
```

---

## Migration Strategy

### Phase 1: Extend Execution Model
```sql
-- Alembic migration: add new fields to executions table
ALTER TABLE executions
  ADD COLUMN priority INTEGER NOT NULL DEFAULT 5,
  ADD COLUMN queue_position INTEGER,
  ADD COLUMN estimated_start_time TIMESTAMP,
  ADD COLUMN retry_count INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN max_retries INTEGER NOT NULL DEFAULT 3,
  ADD COLUMN timeout_seconds INTEGER NOT NULL DEFAULT 600,
  ADD COLUMN parent_execution_id UUID REFERENCES executions(id),
  ADD COLUMN artifact_version INTEGER NOT NULL DEFAULT 1,
  ADD COLUMN cancellation_requested BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN cancelled_at TIMESTAMP,
  ADD COLUMN cancelled_by_user_id UUID REFERENCES users(id),
  ADD COLUMN worker_id UUID,
  ADD CONSTRAINT chk_priority CHECK (priority BETWEEN 0 AND 10),
  ADD CONSTRAINT chk_timeout CHECK (timeout_seconds BETWEEN 60 AND 3600),
  ADD CONSTRAINT chk_retry CHECK (retry_count >= 0),
  ADD CONSTRAINT chk_artifact_version CHECK (artifact_version >= 1);

-- Add new status value 'cancelled' to existing enum
ALTER TYPE executionstatus ADD VALUE 'cancelled';
```

### Phase 2: Create ExecutionArtifact Table
```sql
CREATE TYPE artifacttype AS ENUM ('output_file', 'log_file', 'screenshot', 'data_export');

CREATE TABLE execution_artifacts (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  execution_job_id UUID NOT NULL REFERENCES executions(id),
  file_path VARCHAR(500) NOT NULL,
  file_name VARCHAR(255) NOT NULL,
  file_size BIGINT NOT NULL CHECK (file_size <= 104857600),
  mime_type VARCHAR(100) NOT NULL,
  artifact_type artifacttype NOT NULL,
  version_number INTEGER NOT NULL DEFAULT 1 CHECK (version_number >= 1),
  checksum_sha256 VARCHAR(64),
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMP NOT NULL
);

CREATE INDEX idx_artifacts_execution ON execution_artifacts(execution_job_id, version_number);
CREATE INDEX idx_artifacts_tenant_expiry ON execution_artifacts(tenant_id, expires_at);
CREATE INDEX idx_artifacts_expiry ON execution_artifacts(expires_at);
```

### Phase 3: Create WorkerInstance Table
```sql
CREATE TYPE workerstatus AS ENUM ('idle', 'busy', 'crashed', 'stopping');

CREATE TABLE worker_instances (
  id UUID PRIMARY KEY,
  worker_hostname VARCHAR(255) NOT NULL UNIQUE,
  status workerstatus NOT NULL,
  current_job_id UUID REFERENCES executions(id),
  cpu_usage_percent FLOAT NOT NULL DEFAULT 0 CHECK (cpu_usage_percent BETWEEN 0 AND 100),
  memory_usage_mb INTEGER NOT NULL DEFAULT 0 CHECK (memory_usage_mb BETWEEN 0 AND 4096),
  last_heartbeat_at TIMESTAMP NOT NULL,
  started_at TIMESTAMP NOT NULL,
  crashed_at TIMESTAMP,
  worker_version VARCHAR(50) NOT NULL
);

CREATE INDEX idx_workers_status ON worker_instances(status);
CREATE INDEX idx_workers_heartbeat ON worker_instances(last_heartbeat_at) WHERE status IN ('idle', 'busy');
CREATE INDEX idx_workers_hostname ON worker_instances(worker_hostname);
```

### Phase 4: Add Foreign Key (After WorkerInstance Created)
```sql
ALTER TABLE executions
  ADD CONSTRAINT fk_executions_worker FOREIGN KEY (worker_id) REFERENCES worker_instances(id);

CREATE INDEX idx_executions_worker ON executions(worker_id) WHERE status='in_progress';
CREATE INDEX idx_executions_queue_position ON executions(queue_position) WHERE status='queued';
CREATE INDEX idx_executions_parent ON executions(parent_execution_id);
```

---

## Cleanup Jobs

### Artifact Cleanup (Daily Celery Task)
```python
# Delete artifacts where expires_at < NOW()
expired_artifacts = db.query(ExecutionArtifact).filter(
    ExecutionArtifact.expires_at < datetime.utcnow()
).all()

for artifact in expired_artifacts:
    # Delete from S3
    s3_client.delete_object(Bucket=BUCKET, Key=artifact.file_path)
    # Delete DB row
    db.delete(artifact)
```

### Worker Health Check (Every 30 Seconds)
```python
# Mark workers as crashed if heartbeat > 10s old
crashed_workers = db.query(WorkerInstance).filter(
    WorkerInstance.status.in_(['idle', 'busy']),
    WorkerInstance.last_heartbeat_at < datetime.utcnow() - timedelta(seconds=10)
).all()

for worker in crashed_workers:
    worker.status = 'crashed'
    worker.crashed_at = datetime.utcnow()
    # Requeue current job if exists
    if worker.current_job_id:
        requeue_execution(worker.current_job_id)
```

---

**Next Phase**: Generate API contracts in `contracts/` directory
