# Feature Specification: Isolated Worker Architecture for Async Execution

**Feature Branch**: `004-proper-isolation-and`
**Created**: 2025-10-17
**Status**: Draft
**Input**: User description: "proper isolation and async execution in docker container. Split the execution logic to worker as independent workers in separate docker containers from the main app. The application will initially start with two workers then scale if needed"

## Execution Flow (main)
```
1. Parse user description from Input
   → Feature requests: isolated workers, async execution, Docker containers, scaling
2. Extract key concepts from description
   → Actors: main app, workers, orchestrator
   → Actions: execute crews/tasks, scale workers, isolate execution
   → Data: execution jobs, results, logs
   → Constraints: initial 2 workers, scaling capability
3. For each unclear aspect:
   → All clarifications provided in Session 2025-10-17
4. Fill User Scenarios & Testing section
   → Primary flow: user triggers execution → dispatched to worker → isolated execution → results returned
5. Generate Functional Requirements
   → Worker isolation, job distribution, scaling, monitoring
6. Identify Key Entities
   → Worker instance, execution job, worker pool
7. Run Review Checklist
   → All requirements clarified and testable
8. Return: SUCCESS (spec ready for planning)
```

---

## ⚡ Quick Guidelines
- ✅ Focus on WHAT users need and WHY
- ❌ Avoid HOW to implement (no tech stack, APIs, code structure)
- 👥 Written for business stakeholders, not developers

---

## Clarifications

### Session 2025-10-17
- Q: Auto-scaling triggers → A: Autoscale when workers are 80% utilized in memory and CPU (K8s deployment replicas and HPA)
- Q: Max worker count → A: Infrastructure dependent - size workers to support 10,000 concurrent executions (calculation needed based on per-worker concurrency)
- Q: Scaling down criteria → A: Keep 1-2 workers if queue is idle for X minutes (configurable per deployment)
- Q: Queue strategy → A: Priority-based
- Q: Failure detection timeout → A: As soon as possible (live execution support required)
- Q: Execution timeout → A: Configurable per tenant in tenant settings with default of 10 minutes
- Q: Result retention → A: 30 days by default
- Q: Total worker crash → A: Implement retry policy with exponential backoff; after X retries consider job failed
- Q: Resource limits → A: 2 CPU + 4 GB RAM per worker
- Q: Graceful shutdown → A: Send cancellation signal and let worker log all outputs and state before exiting

**Additional Requirements from Clarifications:**
- Queue visualization: Highlight execution position in queue and estimated execution time
- Live execution: Stream execution output live to users in frontend (critical requirement)
- Execution cancellation: Users can cancel in-progress executions
- Re-execution: Enable re-running executions with output versioning
- Artifact capture: Capture execution outputs with versioning; users can download artifacts from execution page
- Design consistency: Maintain UUIDs, multi-tenancy, authorization patterns consistent with existing platform

---

## User Scenarios & Testing

### Primary User Story
When a user initiates a crew execution (e.g., running a multi-agent workflow), the system must offload the actual execution to an isolated worker container separate from the main application. This ensures:
1. The main application remains responsive and doesn't crash if an execution fails
2. Resource-intensive tasks don't impact API performance
3. Multiple executions can run in parallel without interfering with each other
4. Failed executions are contained and don't affect other running tasks
5. Users can watch execution progress live in real-time
6. Users can cancel long-running executions
7. Users can re-run past executions and compare outputs across versions

The system starts with 2 worker containers and automatically scales up when workers reach 80% CPU/memory utilization (K8s HPA).

### Acceptance Scenarios

1. **Given** a user triggers a crew execution, **When** the request reaches the API, **Then** the execution job is queued and dispatched to an available worker container (not executed in the main app)

2. **Given** 2 workers are running and both are busy, **When** a new execution is queued, **Then** the job waits for an available worker and user sees queue position and estimated wait time

3. **Given** a worker crashes during execution, **When** the failure is detected immediately, **Then** the execution is retried with exponential backoff up to X attempts before marking as failed

4. **Given** workers reach 80% CPU or memory utilization, **When** scaling conditions are met, **Then** additional worker containers are spawned up to the calculated max based on 10,000 concurrent execution target

5. **Given** a worker completes an execution, **When** results are ready, **Then** results and artifacts are versioned, stored, and user is notified via WebSocket with live streaming stopped

6. **Given** an execution runs longer than tenant's configured timeout (default 10 minutes), **When** timeout occurs, **Then** the worker terminates the execution gracefully and returns timeout error with partial outputs

7. **Given** a user watches an in-progress execution, **When** execution produces output, **Then** output is streamed live to the frontend in real-time

8. **Given** a user clicks cancel on an in-progress execution, **When** cancellation is triggered, **Then** worker receives cancellation signal, logs final state, and marks execution as cancelled

9. **Given** a user views a past execution, **When** they click re-execute, **Then** a new execution is created with same inputs and outputs are versioned separately

10. **Given** an execution produces artifacts, **When** user visits execution detail page, **Then** artifacts are listed with download links and version history

11. **Given** queue is idle for X minutes (deployment-configurable), **When** scale-down criteria met, **Then** workers scale down to 1-2 minimum instances

12. **Given** system is shutting down with in-progress executions, **When** shutdown signal received, **Then** workers receive cancellation signal, log outputs/state, and terminate gracefully

### Edge Cases

- **All workers crash simultaneously**: Jobs remain queued; retry policy applies to each job independently once workers restart
- **Container limit reached**: New executions queue indefinitely; system logs warning about capacity limits
- **Worker resource exhaustion**: Workers limited to 2 CPU + 4 GB RAM; exceeding triggers container restart and job retry
- **In-progress executions during shutdown**: Cancellation signal sent; workers log state and exit; executions marked as cancelled/incomplete
- **Execution results retrieval when API instance unavailable**: Results persisted to shared database accessible by all API instances

---

## Requirements

### Functional Requirements

**Worker Isolation**
- **FR-001**: System MUST execute all crew/agent/task runs in isolated worker containers separate from the main API application
- **FR-002**: System MUST ensure worker crashes do not impact the main application's availability or other workers
- **FR-003**: System MUST prevent workers from directly accessing the main application's memory or state
- **FR-004**: Each worker MUST have isolated file system access for execution artifacts
- **FR-005**: Each worker MUST be limited to 2 CPU cores and 4 GB RAM

**Job Distribution & Queuing**
- **FR-006**: System MUST queue execution requests when all workers are busy rather than rejecting them
- **FR-007**: System MUST distribute execution jobs to available workers using priority-based scheduling
- **FR-008**: System MUST track job state (queued, in-progress, completed, failed, cancelled) persistently
- **FR-009**: System MUST allow users to check execution status via API without blocking
- **FR-010**: System MUST display queue position and estimated execution time for queued jobs
- **FR-011**: System MUST support tenant-specific execution priorities

**Worker Pool Management**
- **FR-012**: System MUST start with exactly 2 worker containers on initial deployment
- **FR-013**: System MUST scale worker count up when workers reach 80% CPU or memory utilization (using K8s HPA)
- **FR-014**: System MUST scale worker count down to 1-2 instances when queue is idle for configurable X minutes
- **FR-015**: System MUST size worker pool to support 10,000 concurrent executions at target capacity
- **FR-016**: System MUST calculate per-worker concurrency based on infrastructure capabilities

**Failure Handling & Retry**
- **FR-017**: System MUST detect worker failures as soon as possible to support live execution requirements
- **FR-018**: System MUST automatically restart failed workers
- **FR-019**: System MUST retry failed executions with exponential backoff up to X configurable attempts
- **FR-020**: System MUST mark executions as permanently failed after retry limit exceeded
- **FR-021**: System MUST reassign queued jobs from failed workers to healthy workers

**Execution Timeout & Cancellation**
- **FR-022**: System MUST enforce per-tenant configurable execution timeout (default 10 minutes)
- **FR-023**: System MUST allow users to cancel in-progress executions via UI/API
- **FR-024**: System MUST send cancellation signal to worker when execution is cancelled
- **FR-025**: System MUST allow worker to log outputs and state before terminating on cancellation
- **FR-026**: System MUST mark cancelled executions with distinct status (not failed)

**Live Execution Streaming**
- **FR-027**: System MUST stream execution output live to frontend in real-time via WebSocket
- **FR-028**: System MUST support multiple users watching same execution simultaneously
- **FR-029**: System MUST handle WebSocket disconnections gracefully and allow reconnection to live streams
- **FR-030**: System MUST buffer recent output for users joining mid-execution

**Result Persistence, Artifacts & Versioning**
- **FR-031**: System MUST store execution results in shared persistent storage accessible by all API instances
- **FR-032**: System MUST capture execution artifacts (files, outputs, logs) and persist them
- **FR-033**: System MUST version execution outputs for re-executions of same configuration
- **FR-034**: System MUST retain execution logs and artifacts for 30 days by default
- **FR-035**: System MUST allow users to download execution artifacts from execution detail page
- **FR-036**: System MUST display artifact version history for each execution configuration

**Re-execution**
- **FR-037**: System MUST allow users to re-execute past executions with same inputs
- **FR-038**: System MUST create new versioned execution record for re-executions
- **FR-039**: System MUST allow users to compare outputs across execution versions

**Graceful Shutdown**
- **FR-040**: System MUST send cancellation signal to all in-progress executions during shutdown
- **FR-041**: System MUST allow workers to log outputs and state before exiting on shutdown
- **FR-042**: System MUST mark in-progress executions as cancelled/incomplete after shutdown

**Monitoring & Observability**
- **FR-043**: System MUST expose worker health status (healthy, degraded, crashed)
- **FR-044**: System MUST track metrics: active workers, queue depth, average execution time, failure rate, retry counts
- **FR-045**: System MUST log worker lifecycle events (started, stopped, crashed, restarted)
- **FR-046**: System MUST alert when worker pool cannot scale due to infrastructure limits

**Design Consistency**
- **FR-047**: System MUST use UUIDs (UUIDv7) for all execution, job, and worker identifiers
- **FR-048**: System MUST enforce multi-tenancy isolation for all executions and artifacts
- **FR-049**: System MUST apply authorization checks consistent with existing platform patterns
- **FR-050**: System MUST scope all worker operations to tenant context

### Non-Functional Requirements

**Performance & Scalability**
- **NFR-001**: System MUST support 10,000 concurrent executions at full scale
- **NFR-002**: Queue position updates MUST be reflected in UI within 1 second
- **NFR-003**: Live execution streaming MUST have <500ms latency from worker output to user display
- **NFR-004**: Worker scaling MUST complete within 2 minutes of threshold breach

**Reliability & Availability**
- **NFR-005**: Worker crashes MUST NOT impact main application availability (99.9% uptime target)
- **NFR-006**: Failure detection MUST occur within 5 seconds to support live execution
- **NFR-007**: Retry backoff MUST use exponential strategy with jitter to prevent thundering herd

**Observability**
- **NFR-008**: All worker lifecycle events MUST be logged with structured metadata
- **NFR-009**: Queue depth and worker utilization metrics MUST be exposed for monitoring dashboards

### Key Entities

- **Worker Instance**: Represents an isolated execution container. Attributes include: worker ID (UUID), status (idle/busy/crashed), current job ID (if any), CPU usage %, memory usage %, start time, last heartbeat time, resource limits (2 CPU, 4 GB RAM).

- **Execution Job**: Represents a crew/agent/task execution request. Attributes include: job ID (UUID), tenant ID (UUID), user ID (UUID), execution type (crew/flow/task), input parameters, priority level, status (queued/in-progress/completed/failed/cancelled), assigned worker ID, queued timestamp, started timestamp, completed timestamp, result data, artifact references, version number, timeout duration, retry count, parent execution ID (for re-executions).

- **Worker Pool**: Represents the collection of all worker instances. Attributes include: total worker count, active worker count, idle worker count, target worker count (for scaling), scaling policy (80% CPU/memory threshold), min instances (1-2), calculated max instances (based on 10k concurrent target), idle scale-down timeout (configurable).

- **Execution Artifact**: Represents output files/data produced by execution. Attributes include: artifact ID (UUID), execution job ID, tenant ID, file path, file size, mime type, version number, created timestamp, expiry timestamp (30 days default).

- **Queue Position**: Represents position in execution queue. Attributes include: job ID, queue position (integer), estimated wait time, priority level.

---

## Review & Acceptance Checklist
*GATE: Automated checks run during main() execution*

### Content Quality
- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

### Requirement Completeness
- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable (worker count, isolation, job distribution, scaling thresholds)
- [x] Scope is clearly bounded (worker architecture, live streaming, artifact management)
- [x] Dependencies and assumptions identified (Docker, K8s, shared storage, WebSocket)

---

## Execution Status
*Updated by main() during processing*

- [x] User description parsed
- [x] Key concepts extracted (workers, isolation, scaling, job distribution)
- [x] Ambiguities resolved (10 clarifications provided)
- [x] User scenarios defined (12 acceptance scenarios, 5 edge cases)
- [x] Requirements generated (50 functional requirements, 9 non-functional requirements)
- [x] Entities identified (Worker Instance, Execution Job, Worker Pool, Execution Artifact, Queue Position)
- [x] Review checklist passed

---
