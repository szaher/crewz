# Quickstart: Monitoring & Observability

**Feature**: 005-implement-comprehensive-monitoring
**Purpose**: Integration test scenarios demonstrating trace collection, artifact management, and monitoring dashboard

## Prerequisites

- Docker Compose environment running (backend, workers, PostgreSQL, Redis, S3/MinIO)
- Langfuse instance configured (local or cloud)
- Test tenant created with storage quota
- Sample crew/agent/flow definitions

## Test Scenario 1: End-to-End Trace Collection

**Goal**: Verify LLM traces are captured during crew execution and queryable via API

```python
# test_trace_collection.py
import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta

def test_crew_execution_with_trace_collection(client: TestClient, test_tenant, test_crew):
    """
    Given: A crew with 2 agents (Researcher, Writer), each making 2 LLM calls
    When: Crew is executed
    Then: 4 traces are captured with correct metadata and <2% overhead
    """
    # Arrange
    start_time = datetime.utcnow()
    crew_payload = {
        "crew_id": test_crew.id,
        "inputs": {"topic": "AI monitoring best practices"}
    }

    # Act: Execute crew (triggers Langfuse callbacks)
    response = client.post("/api/v1/executions", json=crew_payload)
    assert response.status_code == 201
    execution_id = response.json()["id"]

    # Wait for execution to complete
    execution = wait_for_completion(client, execution_id, timeout=60)
    end_time = datetime.utcnow()

    # Assert: Check trace collection
    traces_response = client.get(f"/api/v1/traces?execution_id={execution_id}")
    assert traces_response.status_code == 200
    traces = traces_response.json()["traces"]

    # Verify trace count (2 agents × 2 calls each = 4 traces)
    assert len(traces) == 4

    # Verify trace structure
    for trace in traces:
        assert trace["execution_id"] == execution_id
        assert trace["tenant_id"] == test_tenant.id
        assert trace["prompt"] is not None
        assert trace["response"] is not None
        assert trace["total_tokens"] > 0
        assert trace["latency_ms"] > 0
        assert trace["cost_usd"] >= 0
        assert trace["model_name"] in ["gpt-4", "gpt-3.5-turbo", "claude-3"]
        assert trace["provider"] in ["openai", "anthropic"]

    # Verify <2% latency overhead (FR-021)
    execution_time = (end_time - start_time).total_seconds()
    total_llm_time = sum(t["latency_ms"] for t in traces) / 1000
    overhead_percentage = ((execution_time - total_llm_time) / total_llm_time) * 100
    assert overhead_percentage < 2.0, f"Overhead {overhead_percentage}% exceeds 2% limit"

    print(f"✓ Trace collection successful: {len(traces)} traces, {overhead_percentage:.2f}% overhead")
```

**Expected Output**:
```
✓ Trace collection successful: 4 traces, 1.3% overhead
```

---

## Test Scenario 2: Real-Time Trace Streaming

**Goal**: Verify SSE stream delivers trace events in real-time

```python
# test_trace_streaming.py
import sseclient
import requests

def test_trace_streaming_sse(auth_token, test_execution_id):
    """
    Given: An active execution with ongoing LLM calls
    When: Client connects to trace stream endpoint
    Then: Trace events are received in real-time (<1s latency)
    """
    # Arrange
    url = f"http://localhost:8000/api/v1/executions/{test_execution_id}/traces/stream?token={auth_token}"
    events_received = []

    # Act: Connect to SSE stream
    response = requests.get(url, stream=True, headers={"Accept": "text/event-stream"})
    client = sseclient.SSEClient(response)

    # Collect events for 10 seconds
    start_time = datetime.utcnow()
    for event in client.events():
        event_data = json.loads(event.data)
        events_received.append(event_data)

        if (datetime.utcnow() - start_time).seconds > 10:
            break

    # Assert: Verify event structure
    assert len(events_received) > 0, "No events received from stream"

    connected_event = events_received[0]
    assert connected_event["type"] == "connected"

    trace_events = [e for e in events_received if e["type"] == "trace_completed"]
    assert len(trace_events) > 0, "No trace events received"

    for trace_event in trace_events:
        assert "data" in trace_event
        trace = trace_event["data"]
        assert trace["execution_id"] == test_execution_id
        assert trace["total_tokens"] > 0

    print(f"✓ SSE streaming successful: {len(trace_events)} traces streamed in real-time")
```

**Expected Output**:
```
✓ SSE streaming successful: 3 traces streamed in real-time
```

---

## Test Scenario 3: Dashboard Metrics Aggregation

**Goal**: Verify metrics are pre-computed and queryable within 5 seconds

```python
# test_dashboard_metrics.py
def test_dashboard_metrics_performance(client: TestClient, test_tenant):
    """
    Given: 100 completed executions with traces from the past 7 days
    When: Dashboard requests daily metrics
    Then: Metrics returned within 5 seconds (NFR-003)
    """
    # Arrange: Create test data
    seed_test_executions(test_tenant, count=100, days_back=7)

    # Act: Request dashboard metrics
    start_time = datetime.utcnow()
    response = client.get(
        "/api/v1/monitoring/metrics",
        params={
            "period_type": "day",
            "start_date": (datetime.utcnow() - timedelta(days=7)).isoformat(),
            "end_date": datetime.utcnow().isoformat(),
        }
    )
    request_time = (datetime.utcnow() - start_time).total_seconds()

    # Assert: Performance requirement
    assert request_time < 5.0, f"Metrics request took {request_time}s (>5s limit)"

    # Assert: Data correctness
    assert response.status_code == 200
    data = response.json()
    assert "metrics" in data
    assert "summary" in data

    metrics = data["metrics"]
    assert len(metrics) == 7  # 7 days of daily metrics

    for daily_metric in metrics:
        assert daily_metric["period_type"] == "day"
        assert daily_metric["total_executions"] > 0
        assert daily_metric["total_traces"] > 0
        assert daily_metric["total_tokens"] > 0
        assert daily_metric["total_cost_usd"] >= 0
        assert 0 <= daily_metric["error_rate"] <= 100

    summary = data["summary"]
    assert summary["total_cost_usd"] > 0
    assert summary["total_tokens"] > 0
    assert summary["trend"] in ["increasing", "decreasing", "stable"]

    print(f"✓ Dashboard metrics: {len(metrics)} periods in {request_time:.2f}s")
```

**Expected Output**:
```
✓ Dashboard metrics: 7 periods in 2.3s
```

---

## Test Scenario 4: Artifact Upload and Storage Quota

**Goal**: Verify artifact upload, preview generation, and quota enforcement

```python
# test_artifact_upload.py
def test_artifact_upload_with_preview(client: TestClient, test_execution):
    """
    Given: An execution and a 5MB JSON artifact
    When: Artifact is uploaded
    Then: File stored, metadata indexed, preview generated within 3s
    """
    # Arrange
    artifact_data = generate_test_json(size_mb=5)
    files = {"file": ("results.json", artifact_data, "application/json")}
    form_data = {
        "execution_id": test_execution.id,
        "artifact_type": "data",
        "tags": ["test", "results"],
        "description": "Test execution results"
    }

    # Act: Upload artifact
    start_time = datetime.utcnow()
    response = client.post("/api/v1/artifacts", files=files, data=form_data)
    upload_time = (datetime.utcnow() - start_time).total_seconds()

    # Assert: Upload success
    assert response.status_code == 201
    artifact = response.json()
    assert artifact["file_name"] == "results.json"
    assert artifact["file_size_bytes"] == len(artifact_data)
    assert artifact["artifact_type"] == "data"
    assert artifact["mime_type"] == "application/json"
    assert artifact["has_preview"] is True

    # Act: Request preview
    preview_start = datetime.utcnow()
    preview_response = client.get(f"/api/v1/artifacts/{artifact['id']}/preview")
    preview_time = (datetime.utcnow() - preview_start).total_seconds()

    # Assert: Preview performance (NFR-002)
    assert preview_time < 3.0, f"Preview took {preview_time}s (>3s limit)"
    assert preview_response.status_code == 200

    preview = preview_response.json()
    assert preview["preview_type"] == "json"
    assert "formatted_json" in preview["content"]

    print(f"✓ Artifact upload: {upload_time:.2f}s, preview: {preview_time:.2f}s")


def test_storage_quota_enforcement(client: TestClient, test_tenant):
    """
    Given: Tenant with 100MB storage quota, 95MB used
    When: User uploads 10MB artifact
    Then: Upload rejected with 507 error
    """
    # Arrange: Set tenant quota
    update_tenant_quota(test_tenant.id, total_quota_bytes=100_000_000, current_usage=95_000_000)

    # Act: Upload artifact exceeding quota
    large_file = generate_test_file(size_mb=10)
    files = {"file": ("large.bin", large_file, "application/octet-stream")}
    form_data = {"execution_id": test_execution.id}

    response = client.post("/api/v1/artifacts", files=files, data=form_data)

    # Assert: Quota enforcement
    assert response.status_code == 507  # Insufficient Storage
    error = response.json()
    assert "quota exceeded" in error["error"].lower()
    assert error["current_usage_bytes"] == 95_000_000
    assert error["quota_bytes"] == 100_000_000

    print(f"✓ Quota enforcement: Upload blocked at 95% usage")
```

**Expected Output**:
```
✓ Artifact upload: 1.2s, preview: 0.8s
✓ Quota enforcement: Upload blocked at 95% usage
```

---

## Test Scenario 5: Artifact Search and Batch Operations

**Goal**: Verify full-text search and batch download performance

```python
# test_artifact_search.py
def test_artifact_search_performance(client: TestClient, test_tenant):
    """
    Given: 10,000 artifacts with tags and descriptions
    When: User searches for "Q4 report"
    Then: Results returned within 2 seconds (NFR-004)
    """
    # Arrange: Seed test data
    seed_artifacts(test_tenant, count=10_000, include_tags=True, include_descriptions=True)

    # Act: Search artifacts
    start_time = datetime.utcnow()
    response = client.get(
        "/api/v1/artifacts",
        params={"search_query": "Q4 report", "limit": 100}
    )
    search_time = (datetime.utcnow() - start_time).total_seconds()

    # Assert: Performance requirement
    assert search_time < 2.0, f"Search took {search_time}s (>2s limit)"

    # Assert: Results correctness
    assert response.status_code == 200
    data = response.json()
    assert len(data["artifacts"]) > 0
    assert data["total"] > 0

    for artifact in data["artifacts"]:
        assert "Q4" in artifact["file_name"] or "Q4" in artifact["metadata"]["description"]

    print(f"✓ Artifact search: {data['total']} results in {search_time:.2f}s")


def test_batch_download_zip(client: TestClient, test_execution):
    """
    Given: Execution with 50 artifacts (500MB total)
    When: User requests batch download
    Then: ZIP file generated within 10 seconds
    """
    # Arrange: Create test artifacts
    artifact_ids = create_test_artifacts(test_execution, count=50, avg_size_mb=10)

    # Act: Request batch download
    start_time = datetime.utcnow()
    response = client.post("/api/v1/artifacts/batch/download", json={"artifact_ids": artifact_ids})
    zip_time = (datetime.utcnow() - start_time).total_seconds()

    # Assert: ZIP generation performance
    assert zip_time < 10.0, f"ZIP generation took {zip_time}s (>10s for 500MB)"
    assert response.status_code == 200

    data = response.json()
    assert "download_url" in data
    assert data["artifact_count"] == 50
    assert data["total_size_bytes"] > 500_000_000

    print(f"✓ Batch ZIP: {data['artifact_count']} files ({data['total_size_bytes'] // 1_000_000}MB) in {zip_time:.2f}s")
```

**Expected Output**:
```
✓ Artifact search: 47 results in 1.1s
✓ Batch ZIP: 50 files (523MB) in 7.8s
```

---

## Test Scenario 6: Retention and Cleanup

**Goal**: Verify cleanup workers honor retention policies

```python
# test_retention_cleanup.py
def test_trace_retention_cleanup(client: TestClient, test_tenant):
    """
    Given: Tenant with 7-day trace retention (Free tier)
    When: Cleanup worker runs
    Then: Traces older than 7 days are deleted
    """
    # Arrange: Create traces at different ages
    recent_trace = create_trace(test_tenant, days_ago=3)
    old_trace = create_trace(test_tenant, days_ago=10)

    # Act: Run cleanup worker
    from workers.cleanup_worker import cleanup_expired_traces
    cleanup_expired_traces()

    # Assert: Old traces deleted, recent traces retained
    recent_check = client.get(f"/api/v1/traces/{recent_trace.id}")
    assert recent_check.status_code == 200

    old_check = client.get(f"/api/v1/traces/{old_trace.id}")
    assert old_check.status_code == 404

    print(f"✓ Trace retention: Old traces cleaned up, recent retained")


def test_artifact_quota_cleanup_strategy(client: TestClient, test_tenant):
    """
    Given: Tenant with 'oldest_first' cleanup strategy, quota exceeded
    When: Cleanup worker runs
    Then: Oldest artifacts deleted until under quota
    """
    # Arrange: Set quota and create artifacts
    config = update_tenant_config(
        test_tenant.id,
        total_quota_bytes=100_000_000,
        cleanup_strategy="oldest_first"
    )

    old_artifact = create_artifact(test_tenant, size_mb=40, days_ago=30)
    mid_artifact = create_artifact(test_tenant, size_mb=40, days_ago=15)
    new_artifact = create_artifact(test_tenant, size_mb=40, days_ago=1)  # Total 120MB > 100MB quota

    # Act: Run cleanup worker
    from workers.cleanup_worker import enforce_storage_quota
    enforce_storage_quota(test_tenant.id)

    # Assert: Oldest artifact deleted
    old_check = client.get(f"/api/v1/artifacts/{old_artifact.id}")
    assert old_check.status_code == 404

    mid_check = client.get(f"/api/v1/artifacts/{mid_artifact.id}")
    assert mid_check.status_code == 200

    new_check = client.get(f"/api/v1/artifacts/{new_artifact.id}")
    assert new_check.status_code == 200

    # Verify quota now under limit
    quota = client.get(f"/api/v1/tenants/{test_tenant.id}/storage/quota").json()
    assert quota["current_usage_bytes"] <= quota["total_quota_bytes"]

    print(f"✓ Quota cleanup: Oldest artifacts deleted, usage now {quota['usage_percentage']:.1f}%")
```

**Expected Output**:
```
✓ Trace retention: Old traces cleaned up, recent retained
✓ Quota cleanup: Oldest artifacts deleted, usage now 79.2%
```

---

## Running All Tests

```bash
# Run all quickstart tests
pytest specs/005-implement-comprehensive-monitoring/quickstart.md --verbose

# Run with coverage
pytest specs/005-implement-comprehensive-monitoring/quickstart.md --cov=src --cov-report=html

# Run specific scenario
pytest specs/005-implement-comprehensive-monitoring/quickstart.md::test_crew_execution_with_trace_collection
```

---

## Success Criteria

All tests pass with:
- [x] Trace collection with <2% overhead (FR-021)
- [x] Dashboard metrics load <5s (NFR-003)
- [x] Artifact search <2s across 10k+ artifacts (NFR-004)
- [x] Artifact preview <3s for files <10MB (NFR-002)
- [x] Storage quota enforcement working
- [x] Retention cleanup policies working
- [x] Batch operations within timeout limits

---

**Next Steps**: Execute /tasks command to generate ordered task breakdown
