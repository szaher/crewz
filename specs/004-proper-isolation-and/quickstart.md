# Quickstart: Isolated Worker Architecture

**Feature**: 004-proper-isolation-and
**Purpose**: Validate worker isolation, live streaming, priority queue, and artifact management

---

## Prerequisites

- Docker Compose installed
- Backend API running
- Redis running (for Celery broker)
- PostgreSQL with migrations applied
- S3/MinIO configured for artifacts

---

## Step 1: Start Workers

```bash
# Start 2 Celery workers in separate containers
docker-compose -f infra/docker/docker-compose.worker.yml up -d

# Verify workers registered
docker-compose -f infra/docker/docker-compose.worker.yml logs worker1 worker2 | grep "ready"
# Expected output:
# worker1    | [2025-10-17 10:00:00] celery@worker1 ready.
# worker2    | [2025-10-17 10:00:00] celery@worker2 ready.
```

---

## Step 2: Queue an Execution

```bash
# Trigger crew execution via API
curl -X POST http://localhost:8000/api/v1/executions/queue \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "execution_type": "crew",
    "entity_id": "550e8400-e29b-41d4-a716-446655440000",
    "input_params": {"query": "Analyze market trends"},
    "priority": 5
  }'

# Expected response:
# {
#   "job_id": "650e8400-e29b-41d4-a716-446655440001",
#   "queue_position": 1,
#   "estimated_start_time": "2025-10-17T10:00:05Z"
# }
```

---

## Step 3: Watch Live Execution Stream

```bash
# Connect to WebSocket (using wscat or frontend client)
wscat -c "ws://localhost:8000/ws/executions/650e8400-e29b-41d4-a716-446655440001/stream?token=$JWT_TOKEN"

# Expected events:
# > {"event": "execution.started", "job_id": "650e...", "worker_id": "worker1", "started_at": "..."}
# > {"event": "execution.output", "line": "Starting crew execution...", "stream_type": "stdout"}
# > {"event": "execution.progress", "percent": 25, "current_step": "Agent 1", "total_steps": 4}
# > {"event": "execution.output", "line": "Agent 1 completed task", "stream_type": "stdout"}
# > {"event": "execution.completed", "status": "completed", "artifacts": [...]}
```

---

## Step 4: Validate Queue Position

```bash
# Queue 3 more executions while worker1 busy
for i in {1..3}; do
  curl -X POST http://localhost:8000/api/v1/executions/queue \
    -H "Authorization: Bearer $JWT_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
      "execution_type": "crew",
      "entity_id": "550e8400-e29b-41d4-a716-446655440000",
      "input_params": {"query": "Query '$i'"},
      "priority": 5
    }'
done

# Check queue position for last job
curl -X GET http://localhost:8000/api/v1/executions/{last_job_id}/status \
  -H "Authorization: Bearer $JWT_TOKEN"

# Expected:
# {
#   "status": "queued",
#   "queue_position": 3,  # 2 workers busy, 1 in queue ahead
#   "estimated_start_time": "..."
# }
```

---

## Step 5: Test Execution Cancellation

```bash
# Start long-running execution
JOB_ID=$(curl -X POST http://localhost:8000/api/v1/executions/queue \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "execution_type": "crew",
    "entity_id": "550e8400-e29b-41d4-a716-446655440000",
    "input_params": {"query": "Long task"},
    "timeout_seconds": 600
  }' | jq -r '.job_id')

# Wait for execution to start (status = in_progress)
sleep 5

# Cancel execution
curl -X POST http://localhost:8000/api/v1/executions/$JOB_ID/cancel \
  -H "Authorization: Bearer $JWT_TOKEN"

# Expected response:
# {
#   "cancelled": true,
#   "final_state_logged": true
# }

# Verify status changed to cancelled
curl -X GET http://localhost:8000/api/v1/executions/$JOB_ID/status \
  -H "Authorization: Bearer $JWT_TOKEN" | jq '.status'
# Expected: "cancelled"
```

---

## Step 6: Verify Artifacts and Versioning

```bash
# Wait for execution to complete
sleep 30

# List artifacts
curl -X GET http://localhost:8000/api/v1/executions/650e8400-e29b-41d4-a716-446655440001/artifacts \
  -H "Authorization: Bearer $JWT_TOKEN"

# Expected:
# [
#   {
#     "artifact_id": "750e8400-...",
#     "file_name": "output.json",
#     "file_size": 1024,
#     "mime_type": "application/json",
#     "artifact_type": "output_file",
#     "version": 1,
#     "download_url": "https://s3.amazonaws.com/..."
#   },
#   {
#     "artifact_id": "850e8400-...",
#     "file_name": "execution.log",
#     "file_size": 2048,
#     "artifact_type": "log_file",
#     "version": 1,
#     "download_url": "..."
#   }
# ]

# Re-execute to test versioning
curl -X POST http://localhost:8000/api/v1/executions/650e8400-e29b-41d4-a716-446655440001/re-execute \
  -H "Authorization: Bearer $JWT_TOKEN"

# Expected:
# {
#   "new_job_id": "950e8400-...",
#   "version_number": 2
# }

# Verify new artifacts have version=2
curl -X GET http://localhost:8000/api/v1/executions/950e8400-.../artifacts \
  -H "Authorization: Bearer $JWT_TOKEN" | jq '.[0].version'
# Expected: 2
```

---

## Step 7: Test Worker Crash and Retry

```bash
# Start execution on worker1
JOB_ID=$(curl -X POST http://localhost:8000/api/v1/executions/queue \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "execution_type": "crew",
    "entity_id": "550e8400-e29b-41d4-a716-446655440000",
    "input_params": {"query": "Crash test"}
  }' | jq -r '.job_id')

# Wait for worker to pick up job
sleep 5

# Simulate worker crash (kill container)
docker-compose -f infra/docker/docker-compose.worker.yml kill worker1

# Check execution status
curl -X GET http://localhost:8000/api/v1/executions/$JOB_ID/status \
  -H "Authorization: Bearer $JWT_TOKEN"

# Expected (after retry):
# {
#   "status": "in_progress",  # Retried and assigned to worker2
#   "worker_id": "worker2-id",
#   "retry_count": 1
# }

# Restart worker1
docker-compose -f infra/docker/docker-compose.worker.yml up -d worker1
```

---

## Step 8: Validate Worker Metrics (Admin)

```bash
# Get worker pool status
curl -X GET http://localhost:8000/api/v1/admin/workers \
  -H "Authorization: Bearer $ADMIN_JWT_TOKEN"

# Expected:
# [
#   {
#     "worker_id": "worker1-id",
#     "status": "idle",
#     "cpu_percent": 15.2,
#     "memory_mb": 512,
#     "current_job_id": null
#   },
#   {
#     "worker_id": "worker2-id",
#     "status": "busy",
#     "cpu_percent": 65.8,
#     "memory_mb": 1024,
#     "current_job_id": "950e8400-..."
#   }
# ]

# Get metrics
curl -X GET http://localhost:8000/api/v1/admin/workers/metrics \
  -H "Authorization: Bearer $ADMIN_JWT_TOKEN"

# Expected:
# {
#   "total_workers": 2,
#   "active_workers": 1,
#   "queue_depth": 0,
#   "avg_execution_time": 45.3
# }
```

---

## Success Criteria

✅ Workers start and register with Celery
✅ Execution queued and assigned to worker
✅ Live WebSocket streaming shows real-time output
✅ Queue position accurately reflects wait time
✅ Cancellation stops execution and logs partial state
✅ Artifacts versioned correctly on re-execution
✅ Worker crash triggers retry with exponential backoff
✅ Worker metrics exposed for monitoring

---

## Cleanup

```bash
# Stop workers
docker-compose -f infra/docker/docker-compose.worker.yml down

# Clean up Redis queue
docker exec -it crewai-redis redis-cli FLUSHDB
```

---

**Next**: Run `/tasks` command to generate implementation tasks
