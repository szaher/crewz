# Tasks: Comprehensive Monitoring & Observability with Artifact Management

**Feature**: 005-implement-comprehensive-monitoring
**Branch**: `005-implement-comprehensive-monitoring`
**Input**: Design documents from `/specs/005-implement-comprehensive-monitoring/`
**Prerequisites**: plan.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

---

## Execution Summary

**Total Tasks**: 38
**Estimated Duration**: 3-4 weeks
**Parallel Tasks**: 18 tasks marked [P] for concurrent execution

**Tech Stack** (from plan.md):
- Backend: Python 3.11, FastAPI, SQLAlchemy, Celery, Langfuse SDK, boto3
- Frontend: TypeScript, React, Next.js, TailwindCSS
- Storage: PostgreSQL, Redis, S3/local filesystem
- Testing: pytest, Playwright

---

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- All paths relative to repository root

---

## Phase 3.1: Setup & Infrastructure

### T001: Create backend directory structure
**Status**: [X]
**Files**:
```
backend/src/models/trace.py (empty)
backend/src/models/artifact.py (empty)
backend/src/models/tenant_config.py (empty)
backend/src/services/langfuse_client.py (empty)
backend/src/services/artifact_storage.py (empty)
backend/src/services/preview_generator.py (empty)
backend/src/services/cleanup_worker.py (empty)
backend/src/integrations/langfuse/ (directory)
backend/src/api/v1/traces.py (empty)
backend/src/api/v1/artifacts.py (empty)
backend/src/api/v1/monitoring.py (empty)
backend/tests/contract/ (directory)
backend/tests/integration/ (directory)
```
**Description**: Create all backend directories and placeholder files for monitoring feature

---

### T002: Create frontend directory structure
**Status**: [X]
**Files**:
```
frontend/src/components/monitoring/ (directory)
frontend/src/components/artifacts/ (directory)
frontend/src/pages/monitoring/ (directory)
frontend/src/pages/artifacts/ (directory)
frontend/src/lib/api/traces.ts (empty)
frontend/src/lib/api/artifacts.ts (empty)
frontend/src/hooks/monitoring/ (directory)
frontend/tests/e2e/ (directory)
```
**Description**: Create all frontend directories and placeholder files for monitoring UI

---

### T003: [P] Install backend dependencies
**Status**: [X]
**Files**: `backend/requirements.txt`
**Description**: Add Langfuse SDK, boto3 (S3), Pillow (image preview), pygments (code highlighting), PyMuPDF (PDF preview) to requirements.txt and install

**Dependencies to add**:
```
langfuse>=2.0.0
boto3>=1.28.0
Pillow>=10.0.0
pygments>=2.16.0
PyMuPDF>=1.23.0
pandas>=2.0.0  # CSV preview
```

---

### T004: [P] Install frontend dependencies
**Status**: [X]
**Files**: `frontend/package.json`
**Description**: Add chart libraries (recharts), file preview components, and testing dependencies to package.json

**Dependencies to add**:
```json
{
  "recharts": "^2.10.0",
  "react-json-view": "^1.21.3",
  "date-fns": "^2.30.0"
}
```

---

### T005: [P] Configure S3/MinIO storage
**Status**: [X]
**Files**: `backend/src/config/storage.py`
**Description**: Create storage configuration with S3/local filesystem fallback, environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3_BUCKET_NAME, STORAGE_TYPE=s3|local)

---

### T006: [P] Configure Langfuse connection
**Status**: [X]
**Files**: `backend/src/config/langfuse.py`
**Description**: Create Langfuse configuration with API keys (LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST), async client initialization

---

## Phase 3.2: Database Schema & Migrations

### T007: [P] Create Trace model and migration
**Status**: [X]
**Files**:
- `backend/src/models/trace.py`
- `backend/migrations/versions/001_create_traces.py` (Alembic migration)
**Description**: Implement Trace model per data-model.md (id, tenant_id, execution_id, agent_id, tool_id, prompt, response, tokens, latency, cost, timestamps). Create Alembic migration with indexes.

**Key fields**:
- UUID primary key
- Foreign keys to tenant, execution, agent, tool
- JSONB metadata field
- Indexes: (tenant_id, created_at), (execution_id), (created_at)

---

### T008: [P] Create TraceMetrics model and migration
**Status**: [X]
**Files**:
- `backend/src/models/trace_metrics.py`
- `backend/migrations/versions/002_create_trace_metrics.py`
**Description**: Implement TraceMetrics model for pre-computed dashboard aggregations (period_type enum, totals, percentiles, error_rate, metrics_by_type JSONB)

---

### T009: [P] Create Artifact model and migration
**Status**: [X]
**Files**:
- `backend/src/models/artifact.py`
- `backend/migrations/versions/003_create_artifacts.py`
**Description**: Implement Artifact model with file metadata (id, tenant_id, execution_id, execution_version, file_name, size, mime_type, storage_path, artifact_type enum, soft delete). Create indexes for search.

---

### T010: [P] Create ArtifactMetadata model and migration
**Status**: [X]
**Files**:
- `backend/src/models/artifact_metadata.py`
- `backend/migrations/versions/004_create_artifact_metadata.py`
**Description**: Implement ArtifactMetadata model (tags array, description, category, checksum, related_artifacts). Create GIN indexes for full-text search.

---

### T011: [P] Create TenantConfig model and migration
**Status**: [X]
**Files**:
- `backend/src/models/tenant_config.py`
- `backend/migrations/versions/005_create_tenant_configs.py`
**Description**: Implement TenantConfig model (storage quotas, retention policies, cleanup_strategy enum). Add constraint checks (current_usage <= quota).

---

### T012: Run database migrations
**Status**: [X]
**Dependencies**: T007-T011 must complete first
**Command**: `alembic upgrade head`
**Description**: Apply all 5 migrations to create trace, artifact, and config tables with indexes

---

## Phase 3.3: Contract Tests (TDD)

### T013: [P] Contract test GET /api/v1/traces
**Status**: [X]
**Files**: `backend/tests/contract/test_traces_list.py`
**Description**: Test trace listing endpoint per contracts/traces-api.yaml. Assert request/response schema, pagination, filtering (execution_id, date range, provider, cost range). Test should FAIL initially.

---

### T014: [P] Contract test GET /api/v1/traces/{trace_id}
**Status**: [X]
**Files**: `backend/tests/contract/test_traces_get.py`
**Description**: Test single trace retrieval. Assert response matches Trace schema from OpenAPI contract. Test should FAIL initially.

---

### T015: [P] Contract test POST /api/v1/traces/export
**Status**: [X]
**Files**: `backend/tests/contract/test_traces_export.py`
**Description**: Test trace export to JSON/CSV. Assert pre-signed URL generation, expiration timestamp. Test should FAIL initially.

---

### T016: [P] Contract test GET /api/v1/monitoring/metrics
**Status**: [X]
**Files**: `backend/tests/contract/test_monitoring_metrics.py`
**Description**: Test dashboard metrics endpoint. Assert TraceMetrics schema, period filtering, entity_type breakdown. Test should FAIL initially.

---

### T017: [P] Contract test GET /api/v1/artifacts
**Status**: [X]
**Files**: `backend/tests/contract/test_artifacts_list.py`
**Description**: Test artifact search/list per contracts/artifacts-api.yaml. Assert filtering (execution_id, artifact_type, tags, date range, size), sorting, pagination. Test should FAIL initially.

---

### T018: [P] Contract test POST /api/v1/artifacts
**Status**: [X]
**Files**: `backend/tests/contract/test_artifacts_upload.py`
**Description**: Test artifact upload (multipart/form-data). Assert 201 response, metadata extraction, storage_path generation. Test quota enforcement (507 error). Test should FAIL initially.

---

### T019: [P] Contract test GET /api/v1/artifacts/{artifact_id}/preview
**Status**: [X]
**Files**: `backend/tests/contract/test_artifacts_preview.py`
**Description**: Test artifact preview generation. Assert preview_type enum (json/table/image/text/code), content structure per schema. Test should FAIL initially.

---

### T020: [P] Contract test POST /api/v1/artifacts/batch/download
**Status**: [X]
**Files**: `backend/tests/contract/test_artifacts_batch_download.py`
**Description**: Test batch ZIP download. Assert artifact_ids validation (max 100), download_url generation, metadata inclusion. Test should FAIL initially.

---

## Phase 3.4: Integration Test Scenarios (from quickstart.md)

### T021: [P] Integration test: Trace collection with <2% overhead
**Status**: [X]
**Files**: `backend/tests/integration/test_trace_collection.py`
**Description**: Implement quickstart Scenario 1. Execute crew with 2 agents (4 LLM calls), assert 4 traces captured, verify <2% latency overhead (FR-021). Test should FAIL initially.

---

### T022: [P] Integration test: Real-time trace streaming via SSE
**Status**: [X]
**Files**: `backend/tests/integration/test_trace_streaming.py`
**Description**: Implement quickstart Scenario 2. Connect SSE client to `/executions/{id}/traces/stream`, collect events for 10s, assert `connected` and `trace_completed` events received. Test should FAIL initially.

---

### T023: [P] Integration test: Dashboard metrics performance (<5s)
**Status**: [X]
**Files**: `backend/tests/integration/test_dashboard_metrics.py`
**Description**: Implement quickstart Scenario 3. Seed 100 executions over 7 days, request daily metrics, assert response time <5s (NFR-003), verify data correctness. Test should FAIL initially.

---

### T024: [P] Integration test: Artifact upload with preview (<3s)
**Status**: [X]
**Files**: `backend/tests/integration/test_artifact_upload_preview.py`
**Description**: Implement quickstart Scenario 4. Upload 5MB JSON artifact, assert preview generated within 3s (NFR-002), verify storage quota enforcement (507 error when exceeded). Test should FAIL initially.

---

### T025: [P] Integration test: Artifact search performance (<2s)
**Status**: [X]
**Files**: `backend/tests/integration/test_artifact_search.py`
**Description**: Implement quickstart Scenario 5. Seed 10,000 artifacts, search "Q4 report", assert results within 2s (NFR-004). Test batch ZIP generation for 50 artifacts. Test should FAIL initially.

---

### T026: [P] Integration test: Retention cleanup policies
**Status**: [X]
**Files**: `backend/tests/integration/test_retention_cleanup.py`
**Description**: Implement quickstart Scenario 6. Create traces at different ages, run cleanup worker, assert old traces deleted (7-day retention). Test quota cleanup strategies (oldest_first, largest_first, LRU). Test should FAIL initially.

---

## Phase 3.5: Core Implementation - Langfuse Integration

### T027: Implement Langfuse async callback handler
**Status**: [X]
**Dependencies**: T006 (Langfuse config)
**Files**: `backend/src/integrations/langfuse/callback_handler.py`
**Description**: Create CrewAILangfuseHandler extending Langfuse CallbackHandler. Implement `on_llm_start()`, `on_llm_end()`, `on_llm_error()` with async execution, context propagation (execution_id, tenant_id, agent_id), <2% overhead requirement.

**Key methods**:
```python
async def on_llm_start(execution_id, agent_id, prompt, **kwargs)
async def on_llm_end(trace_id, response, tokens, cost, latency)
async def on_llm_error(trace_id, error_message)
```

---

### T028: Integrate Langfuse handler with CrewAI execution
**Status**: [X]
**Dependencies**: T027
**Files**: `backend/src/services/execution_service.py` (existing file - modify)
**Description**: Inject CrewAILangfuseHandler into CrewAI LLM instances during execution. Ensure graceful degradation if Langfuse unavailable (NFR-001). Add async trace persistence to PostgreSQL.

---

### T029: Implement trace persistence service
**Status**: [X]
**Dependencies**: T007 (Trace model), T028 (Langfuse integration)
**Files**: `backend/src/services/trace_service.py`
**Description**: Create TraceService with `save_trace()`, `get_traces()`, `export_traces()`. Implement filtering, pagination, Redis caching for frequently accessed traces.

---

## Phase 3.6: Core Implementation - Artifact Storage

### T030: Implement artifact storage abstraction
**Status**: [ ]
**Dependencies**: T005 (storage config), T009 (Artifact model)
**Files**: `backend/src/services/artifact_storage.py`
**Description**: Create ArtifactStorageService with S3/local filesystem abstraction. Implement `upload_file()`, `download_file()`, `delete_file()`, `generate_presigned_url()`. Use hierarchical path: `{tenant_id}/{execution_id}/{version}/{artifact_id}.{ext}`

**Key methods**:
```python
async def upload_file(tenant_id, execution_id, version, file, mime_type) -> Artifact
async def download_file(artifact_id) -> str  # Returns pre-signed URL
async def delete_file(artifact_id) -> bool
```

---

### T031: Implement artifact preview generator
**Status**: [ ]
**Dependencies**: T009 (Artifact model), T030 (storage service)
**Files**: `backend/src/services/preview_generator.py`
**Description**: Create PreviewGenerator with handlers for JSON (pygments), CSV (pandas table), images (Pillow thumbnail), PDF (PyMuPDF thumbnail), code (pygments). Implement Redis caching (1 hour TTL), <3s generation for <10MB files (NFR-002).

**Preview handlers**:
```python
def generate_json_preview(file_path) -> dict
def generate_csv_preview(file_path, max_rows=100) -> dict
def generate_image_preview(file_path, max_size=(800, 600)) -> dict
def generate_pdf_preview(file_path) -> dict
def generate_code_preview(file_path, language) -> dict
```

---

### T032: Implement artifact metadata search service
**Status**: [ ]
**Dependencies**: T010 (ArtifactMetadata model)
**Files**: `backend/src/services/artifact_search.py`
**Description**: Create ArtifactSearchService with full-text search using PostgreSQL GIN indexes. Implement filtering (tags, description, file_name, date range, size, artifact_type), sorting, pagination. Ensure <2s response for 10k+ artifacts (NFR-004).

---

## Phase 3.7: Core Implementation - Metrics Aggregation

### T033: Implement metrics aggregation worker
**Status**: [ ]
**Dependencies**: T008 (TraceMetrics model), T029 (trace service)
**Files**: `backend/src/services/metrics_aggregator.py`
**Description**: Create MetricsAggregator Celery task that incrementally updates TraceMetrics on trace ingestion. Compute totals (tokens, cost, executions), percentiles (P50, P95, P99), error_rate. Cache results in Redis with TTL = retention_days + 7.

**Key methods**:
```python
@celery.task
async def aggregate_trace_metrics(trace_id: UUID)
async def compute_percentiles(tenant_id, period_type, period_start) -> dict
async def get_cached_metrics(tenant_id, period_type, start, end) -> list[TraceMetrics]
```

---

### T034: Implement cleanup worker with retention policies
**Status**: [ ]
**Dependencies**: T011 (TenantConfig model), T009 (Artifact model), T007 (Trace model)
**Files**: `backend/src/services/cleanup_worker.py`
**Description**: Create Celery periodic tasks (run every 6 hours). Implement `cleanup_expired_traces()` (delete traces older than tenant.trace_retention_days), `cleanup_expired_artifacts()` (delete artifacts older than tenant.artifact_retention_days), `enforce_storage_quota()` (cleanup based on tenant.cleanup_strategy: oldest_first, largest_first, LRU, block_uploads).

**Tasks**:
```python
@celery_beat.task(run_every=timedelta(hours=6))
def cleanup_expired_traces()

@celery_beat.task(run_every=timedelta(hours=6))
def cleanup_expired_artifacts()

@celery_beat.task(run_every=timedelta(hours=1))
def enforce_storage_quota()
```

---

## Phase 3.8: API Endpoints Implementation

### T035: Implement GET /api/v1/traces endpoint
**Status**: [ ]
**Dependencies**: T029 (trace service), T013 (contract test)
**Files**: `backend/src/api/v1/traces.py`
**Description**: Implement trace listing with filtering (execution_id, tenant_id, date range, provider, model, cost, has_error), pagination (limit/offset). Make T013 contract test PASS.

---

### T036: Implement GET /api/v1/traces/{trace_id} endpoint
**Status**: [ ]
**Dependencies**: T029 (trace service), T014 (contract test)
**Files**: `backend/src/api/v1/traces.py`
**Description**: Implement single trace retrieval. Make T014 contract test PASS.

---

### T037: Implement POST /api/v1/traces/export endpoint
**Status**: [ ]
**Dependencies**: T029 (trace service), T015 (contract test)
**Files**: `backend/src/api/v1/traces.py`
**Description**: Implement trace export to JSON/CSV. Generate file, upload to S3, return pre-signed URL with 1-hour expiration. Make T015 contract test PASS.

---

### T038: Implement GET /api/v1/executions/{id}/traces/stream SSE endpoint
**Status**: [ ]
**Dependencies**: T029 (trace service), T022 (integration test)
**Files**: `backend/src/api/v1/traces.py`
**Description**: Implement Server-Sent Events stream for real-time trace delivery. Subscribe to Redis pub/sub channel `traces:{execution_id}`, stream events (connected, trace_started, trace_completed, trace_failed). Make T022 integration test PASS.

---

### T039: Implement GET /api/v1/monitoring/metrics endpoint
**Status**: [ ]
**Dependencies**: T033 (metrics aggregator), T016 (contract test)
**Files**: `backend/src/api/v1/monitoring.py`
**Description**: Implement dashboard metrics endpoint. Query TraceMetrics with period filtering (hour/day/week/month), entity_type breakdown. Ensure <5s response (NFR-003). Make T016 contract test PASS.

---

### T040: Implement POST /api/v1/artifacts endpoint (upload)
**Status**: [ ]
**Dependencies**: T030 (storage service), T011 (TenantConfig), T018 (contract test)
**Files**: `backend/src/api/v1/artifacts.py`
**Description**: Implement artifact upload (multipart/form-data). Validate file size against tenant.max_artifact_size_bytes, check storage quota, upload to S3, create Artifact + ArtifactMetadata records. Return 507 if quota exceeded. Make T018 contract test PASS.

---

### T041: Implement GET /api/v1/artifacts endpoint (search/list)
**Status**: [ ]
**Dependencies**: T032 (search service), T017 (contract test)
**Files**: `backend/src/api/v1/artifacts.py`
**Description**: Implement artifact search with full-text search (file_name, tags, description), filtering (execution_id, artifact_type, date range, size), sorting, pagination. Ensure <2s response for 10k+ artifacts (NFR-004). Make T017 contract test PASS.

---

### T042: Implement GET /api/v1/artifacts/{id}/download endpoint
**Status**: [ ]
**Dependencies**: T030 (storage service)
**Files**: `backend/src/api/v1/artifacts.py`
**Description**: Implement artifact download. Generate S3 pre-signed URL (1 hour expiration), update last_accessed_at for LRU tracking. Return download_url, expires_at, file metadata.

---

### T043: Implement GET /api/v1/artifacts/{id}/preview endpoint
**Status**: [ ]
**Dependencies**: T031 (preview generator), T019 (contract test)
**Files**: `backend/src/api/v1/artifacts.py`
**Description**: Implement artifact preview. Check Redis cache first, generate preview if not cached (<3s for <10MB files), return preview_type + content. Handle unsupported types gracefully (415 error). Make T019 contract test PASS.

---

### T044: Implement PATCH /api/v1/artifacts/{id} endpoint (update metadata)
**Status**: [ ]
**Dependencies**: T010 (ArtifactMetadata model)
**Files**: `backend/src/api/v1/artifacts.py`
**Description**: Implement metadata updates (tags, description, category). Validate tags array (max 20, each max 50 chars).

---

### T045: Implement DELETE /api/v1/artifacts/{id} endpoint (soft delete)
**Status**: [ ]
**Dependencies**: T009 (Artifact model)
**Files**: `backend/src/api/v1/artifacts.py`
**Description**: Implement artifact soft delete. Set deleted_at timestamp, schedule hard delete after 7-day grace period via cleanup worker.

---

### T046: Implement POST /api/v1/artifacts/batch/download endpoint
**Status**: [ ]
**Dependencies**: T030 (storage service), T020 (contract test)
**Files**: `backend/src/api/v1/artifacts.py`
**Description**: Implement batch ZIP generation. Validate artifact_ids (max 100), create ZIP with original filenames + metadata.json, upload to S3, return pre-signed URL. Handle up to 1GB total size (NFR-006). Make T020 contract test PASS.

---

### T047: Implement POST /api/v1/artifacts/batch/update endpoint
**Status**: [ ]
**Dependencies**: T010 (ArtifactMetadata model)
**Files**: `backend/src/api/v1/artifacts.py`
**Description**: Implement batch metadata update (add_tags, remove_tags, category). Return updated_count and failed_ids.

---

### T048: Implement POST /api/v1/artifacts/batch/delete endpoint
**Status**: [ ]
**Dependencies**: T009 (Artifact model)
**Files**: `backend/src/api/v1/artifacts.py`
**Description**: Implement batch soft delete. Return deleted_count and failed_ids.

---

### T049: Implement GET /api/v1/tenants/{id}/storage/quota endpoint
**Status**: [ ]
**Dependencies**: T011 (TenantConfig model)
**Files**: `backend/src/api/v1/tenants.py`
**Description**: Implement storage quota status. Return current_usage, total_quota, usage_percentage, is_over_warning, is_over_alert flags.

---

## Phase 3.9: Frontend Implementation

### T050: [P] Implement trace API client
**Status**: [ ]
**Files**: `frontend/src/lib/api/traces.ts`
**Description**: Create TypeScript API client for trace endpoints. Implement `listTraces()`, `getTrace()`, `exportTraces()`, `streamTraces()` with SSE client.

---

### T051: [P] Implement artifact API client
**Status**: [ ]
**Files**: `frontend/src/lib/api/artifacts.ts`
**Description**: Create TypeScript API client for artifact endpoints. Implement `listArtifacts()`, `uploadArtifact()`, `getArtifactPreview()`, `downloadArtifact()`, `batchDownload()`, batch update/delete.

---

### T052: [P] Implement monitoring hooks
**Status**: [ ]
**Files**:
- `frontend/src/hooks/monitoring/useTraces.ts`
- `frontend/src/hooks/monitoring/useMetrics.ts`
- `frontend/src/hooks/monitoring/useTraceStream.ts`
**Description**: Create React hooks for trace data (with filtering, pagination), metrics data (with caching), SSE trace streaming.

---

### T053: [P] Implement artifact hooks
**Status**: [ ]
**Files**:
- `frontend/src/hooks/artifacts/useArtifacts.ts`
- `frontend/src/hooks/artifacts/useArtifactSearch.ts`
- `frontend/src/hooks/artifacts/useArtifactUpload.ts`
**Description**: Create React hooks for artifact listing, search, upload with progress tracking, batch operations.

---

### T054: Implement dashboard metrics charts component
**Status**: [ ]
**Dependencies**: T052 (metrics hook)
**Files**: `frontend/src/components/monitoring/MetricsCharts.tsx`
**Description**: Create dashboard with Recharts. Show token usage over time, cost breakdown (pie chart), latency percentiles (line chart), error rate (bar chart). Implement period selector (hour/day/week/month), entity type filter.

---

### T055: Implement trace viewer component
**Status**: [ ]
**Dependencies**: T052 (traces hook)
**Files**: `frontend/src/components/monitoring/TraceViewer.tsx`
**Description**: Create trace list with filtering UI (execution, date range, provider, cost), sorting, pagination. Expandable row showing prompt/response, tokens, latency, cost. Link to Langfuse external trace ID.

---

### T056: Implement live trace stream component
**Status**: [ ]
**Dependencies**: T052 (trace stream hook)
**Files**: `frontend/src/components/monitoring/LiveTraceStream.tsx`
**Description**: Create real-time trace display during execution. Show trace events as they arrive via SSE, highlight LLM calls, display running totals (tokens, cost).

---

### T057: Implement artifact browser component
**Status**: [ ]
**Dependencies**: T053 (artifacts hook)
**Files**: `frontend/src/components/artifacts/ArtifactBrowser.tsx`
**Description**: Create artifact list with grid/list view toggle. Show thumbnail for images, file type icons, metadata (size, type, tags), actions (preview, download, delete). Implement filtering UI (execution, type, tags, date range, size).

---

### T058: Implement artifact preview modal
**Status**: [ ]
**Dependencies**: T053 (artifacts hook)
**Files**: `frontend/src/components/artifacts/ArtifactPreviewModal.tsx`
**Description**: Create modal for inline preview. Render JSON (syntax highlighted), CSV (table with sort), images (full size), PDF (iframe), code (syntax highlighted), text (scrollable). Show "Preview not available" for unsupported types.

---

### T059: Implement artifact upload component
**Status**: [ ]
**Dependencies**: T053 (upload hook)
**Files**: `frontend/src/components/artifacts/ArtifactUpload.tsx`
**Description**: Create drag-and-drop upload component with progress bar. Show file size validation, quota warning, tag/description inputs. Display upload errors (413 file too large, 507 quota exceeded).

---

### T060: Implement artifact batch actions component
**Status**: [ ]
**Dependencies**: T053 (artifacts hook)
**Files**: `frontend/src/components/artifacts/BatchActions.tsx`
**Description**: Create multi-select UI with batch actions (download ZIP, add tags, delete). Show progress during batch operations, display failed items with error messages.

---

### T061: Implement monitoring dashboard page
**Status**: [ ]
**Dependencies**: T054, T055, T056
**Files**: `frontend/src/pages/monitoring/index.tsx`
**Description**: Create dashboard page combining metrics charts, trace viewer, live stream. Add period selector, export button, refresh button.

---

### T062: Implement artifact search page
**Status**: [ ]
**Dependencies**: T057, T058, T059, T060
**Files**: `frontend/src/pages/artifacts/index.tsx`
**Description**: Create artifact search page with full-text search input, filters sidebar, artifact browser, preview modal, batch actions toolbar.

---

### T063: Enhance execution detail page with traces tab
**Status**: [ ]
**Dependencies**: T055, T056
**Files**: `frontend/src/app/executions/[id]/page.tsx` (existing file - modify)
**Description**: Add "Traces" tab to existing execution detail page. Show trace viewer for execution, live stream during active execution.

---

### T064: Enhance execution detail page with artifacts tab
**Status**: [ ]
**Dependencies**: T057, T058
**Files**: `frontend/src/app/executions/[id]/page.tsx` (existing file - modify)
**Description**: Add "Artifacts" tab to existing execution detail page. Show artifacts for execution (all versions), preview modal, download actions.

---

## Phase 3.10: End-to-End Tests

### T065: [P] E2E test: View dashboard metrics
**Status**: [ ]
**Dependencies**: T061 (dashboard page)
**Files**: `frontend/tests/e2e/test_monitoring_dashboard.spec.ts`
**Description**: Playwright test for dashboard page. Verify charts render, period selector works, data refreshes, export button generates file.

---

### T066: [P] E2E test: Search and preview artifacts
**Status**: [ ]
**Dependencies**: T062 (artifact search page)
**Files**: `frontend/tests/e2e/test_artifact_search.spec.ts`
**Description**: Playwright test for artifact search. Type search query, apply filters, verify results update, click preview, verify modal opens with correct content.

---

### T067: [P] E2E test: Upload artifact with quota warning
**Status**: [ ]
**Dependencies**: T059 (upload component)
**Files**: `frontend/tests/e2e/test_artifact_upload.spec.ts`
**Description**: Playwright test for artifact upload. Drag file to upload zone, add tags/description, submit, verify success message. Test quota warning at 80% usage.

---

### T068: [P] E2E test: Batch download artifacts as ZIP
**Status**: [ ]
**Dependencies**: T060 (batch actions)
**Files**: `frontend/tests/e2e/test_artifact_batch.spec.ts`
**Description**: Playwright test for batch operations. Select 5 artifacts, click "Download Selected", verify ZIP file downloads with correct contents.

---

## Phase 3.11: Polish & Documentation

### T069: [P] Add unit tests for preview generator
**Status**: [ ]
**Dependencies**: T031 (preview generator)
**Files**: `backend/tests/unit/test_preview_generator.py`
**Description**: Unit tests for each preview handler (JSON, CSV, image, PDF, code). Test caching behavior, error handling for corrupted files, file size limits.

---

### T070: [P] Add unit tests for metrics aggregator
**Status**: [ ]
**Dependencies**: T033 (metrics aggregator)
**Files**: `backend/tests/unit/test_metrics_aggregator.py`
**Description**: Unit tests for metrics computation (totals, percentiles, error_rate). Test incremental updates, Redis caching behavior.

---

### T071: [P] Add unit tests for cleanup worker
**Status**: [ ]
**Dependencies**: T034 (cleanup worker)
**Files**: `backend/tests/unit/test_cleanup_worker.py`
**Description**: Unit tests for retention cleanup (trace/artifact expiration), quota enforcement strategies (oldest_first, largest_first, LRU, block_uploads).

---

### T072: Performance test: Dashboard metrics <5s
**Status**: [ ]
**Dependencies**: T039 (metrics endpoint), T023 (integration test)
**Files**: `backend/tests/performance/test_metrics_performance.py`
**Description**: Load test with 10,000 traces over 30 days. Verify metrics endpoint responds within 5s (NFR-003) under load.

---

### T073: Performance test: Artifact search <2s
**Status**: [ ]
**Dependencies**: T041 (search endpoint), T025 (integration test)
**Files**: `backend/tests/performance/test_search_performance.py`
**Description**: Load test with 50,000 artifacts. Verify full-text search responds within 2s (NFR-004) with complex queries.

---

### T074: Performance test: Trace collection <2% overhead
**Status**: [ ]
**Dependencies**: T028 (Langfuse integration), T021 (integration test)
**Files**: `backend/tests/performance/test_trace_overhead.py`
**Description**: Benchmark crew execution with/without tracing enabled. Verify overhead <2% (FR-021) across different execution patterns (short/long, few/many LLM calls).

---

### T075: [P] Update API documentation
**Status**: [ ]
**Files**: `docs/api/monitoring.md`, `docs/api/artifacts.md`
**Description**: Create API documentation from OpenAPI contracts. Include authentication, rate limits, error codes, usage examples with curl/Python/TypeScript.

---

### T076: [P] Create architecture diagram
**Status**: [ ]
**Files**: `docs/architecture/monitoring-system.md`
**Description**: Document monitoring architecture with diagrams: Langfuse integration flow, artifact storage hierarchy, metrics aggregation pipeline, cleanup worker schedule.

---

### T077: [P] Create user guide for monitoring dashboard
**Status**: [ ]
**Files**: `docs/guides/monitoring-dashboard.md`
**Description**: User guide for monitoring dashboard. Explain metrics (token usage, cost, latency percentiles), filtering traces, exporting data, interpreting error rates.

---

### T078: [P] Create user guide for artifact management
**Status**: [ ]
**Files**: `docs/guides/artifact-management.md`
**Description**: User guide for artifacts. Explain search syntax, preview capabilities, batch operations, storage quotas, retention policies, cleanup strategies.

---

## Dependencies Graph

```
Setup (T001-T006) → Models (T007-T011) → Migration (T012)
    ↓
Contract Tests (T013-T020) [ALL PARALLEL]
    ↓
Integration Tests (T021-T026) [ALL PARALLEL]
    ↓
Core Services:
  T027 → T028 → T029 (Langfuse → Trace Service)
  T030 → T031 (Storage → Preview)
  T032 (Search Service)
  T033 (Metrics Aggregator)
  T034 (Cleanup Worker)
    ↓
API Endpoints (T035-T049):
  T029 → T035, T036, T037, T038 (Traces endpoints)
  T033 → T039 (Metrics endpoint)
  T030, T031, T032 → T040-T049 (Artifacts endpoints)
    ↓
Frontend:
  T050, T051 → T052, T053 (API Clients → Hooks) [PARALLEL]
  T052, T053 → T054-T064 (Components & Pages)
    ↓
E2E Tests (T065-T068) [ALL PARALLEL]
    ↓
Polish:
  Unit Tests (T069-T071) [PARALLEL]
  Performance Tests (T072-T074)
  Documentation (T075-T078) [PARALLEL]
```

---

## Parallel Execution Examples

### Example 1: Models (after T006 setup complete)
Run T007-T011 in parallel (all create different model files):
```bash
Task: "Create Trace model in backend/src/models/trace.py and migration 001"
Task: "Create TraceMetrics model in backend/src/models/trace_metrics.py and migration 002"
Task: "Create Artifact model in backend/src/models/artifact.py and migration 003"
Task: "Create ArtifactMetadata model in backend/src/models/artifact_metadata.py and migration 004"
Task: "Create TenantConfig model in backend/src/models/tenant_config.py and migration 005"
```

### Example 2: Contract Tests (after T012 migration complete)
Run T013-T020 in parallel (all create different test files):
```bash
Task: "Contract test GET /api/v1/traces in backend/tests/contract/test_traces_list.py"
Task: "Contract test GET /api/v1/traces/{id} in backend/tests/contract/test_traces_get.py"
Task: "Contract test POST /api/v1/traces/export in backend/tests/contract/test_traces_export.py"
Task: "Contract test GET /api/v1/monitoring/metrics in backend/tests/contract/test_monitoring_metrics.py"
Task: "Contract test GET /api/v1/artifacts in backend/tests/contract/test_artifacts_list.py"
Task: "Contract test POST /api/v1/artifacts in backend/tests/contract/test_artifacts_upload.py"
Task: "Contract test GET /api/v1/artifacts/{id}/preview in backend/tests/contract/test_artifacts_preview.py"
Task: "Contract test POST /api/v1/artifacts/batch/download in backend/tests/contract/test_artifacts_batch_download.py"
```

### Example 3: Integration Tests (after T020 contract tests complete)
Run T021-T026 in parallel (all create different test files):
```bash
Task: "Integration test trace collection with <2% overhead in backend/tests/integration/test_trace_collection.py"
Task: "Integration test SSE trace streaming in backend/tests/integration/test_trace_streaming.py"
Task: "Integration test dashboard metrics <5s in backend/tests/integration/test_dashboard_metrics.py"
Task: "Integration test artifact upload + preview <3s in backend/tests/integration/test_artifact_upload_preview.py"
Task: "Integration test artifact search <2s in backend/tests/integration/test_artifact_search.py"
Task: "Integration test retention cleanup in backend/tests/integration/test_retention_cleanup.py"
```

### Example 4: Frontend API Clients (after backend APIs deployed)
Run T050-T053 in parallel (all create different files):
```bash
Task: "Implement trace API client in frontend/src/lib/api/traces.ts"
Task: "Implement artifact API client in frontend/src/lib/api/artifacts.ts"
Task: "Implement monitoring hooks (useTraces, useMetrics, useTraceStream) in frontend/src/hooks/monitoring/"
Task: "Implement artifact hooks (useArtifacts, useArtifactSearch, useArtifactUpload) in frontend/src/hooks/artifacts/"
```

### Example 5: Documentation (after all implementation complete)
Run T075-T078 in parallel (all create different doc files):
```bash
Task: "Update API documentation in docs/api/monitoring.md and docs/api/artifacts.md"
Task: "Create architecture diagram in docs/architecture/monitoring-system.md"
Task: "Create monitoring dashboard user guide in docs/guides/monitoring-dashboard.md"
Task: "Create artifact management user guide in docs/guides/artifact-management.md"
```

---

## Validation Checklist

Before marking Phase 3 complete, verify:

- [x] All 2 contracts have corresponding test tasks (T013-T020: 8 contract tests)
- [x] All 5 entities have model tasks (T007-T011)
- [x] All contract tests come before endpoint implementation
- [x] All integration tests (T021-T026) written before core implementation
- [x] Parallel tasks ([P] marked) truly independent (different files)
- [x] Each task specifies exact file path
- [x] No [P] task modifies same file as another [P] task
- [x] Dependencies correctly ordered (Setup → Tests → Core → Integration → Polish)

---

## Notes

- **TDD Approach**: All contract tests (T013-T020) and integration tests (T021-T026) MUST be written before implementation and should FAIL initially
- **Performance Requirements**: Tasks T021, T023, T024, T025 validate NFR compliance (<2% trace overhead, <5s metrics, <3s preview, <2s search)
- **Graceful Degradation**: T028 must implement NFR-001 (trace collection must not cause execution failures)
- **Parallel Execution**: 18 tasks marked [P] can run concurrently (45% parallelizable)
- **Estimated Duration**: 3-4 weeks with 2-3 developers (assuming parallel execution)
- **Commit Strategy**: Commit after each task completion with message format: `[T0XX] Task description`

---

## Next Steps

1. **Verify Prerequisites**: Ensure Docker containers running (PostgreSQL, Redis, S3/MinIO, Celery workers)
2. **Start with Setup**: Execute T001-T006 sequentially
3. **Run Models in Parallel**: Execute T007-T011 concurrently
4. **Apply Migrations**: Execute T012 to create database schema
5. **Write Tests First**: Execute contract tests (T013-T020) and integration tests (T021-T026) in parallel
6. **Implement Core**: Execute T027-T034 services sequentially (respecting dependencies)
7. **Implement Endpoints**: Execute T035-T049 to make tests pass
8. **Build Frontend**: Execute T050-T064 progressively
9. **E2E Validation**: Execute T065-T068 to verify full stack
10. **Polish**: Execute T069-T078 for production readiness

**Ready to begin implementation!** Use `/implement` command or execute tasks manually with clear commit messages.
