# Phase 0: Research & Technical Decisions

**Feature**: Comprehensive Monitoring & Observability with Artifact Management
**Date**: 2025-01-22

## Research Areas

### 1. Langfuse Integration for LLM Tracing

**Decision**: Use Langfuse SDK with async callback handler pattern

**Rationale**:
- Langfuse provides first-class support for LLM observability with minimal overhead
- Async callback handlers allow <2% latency overhead (FR-021 requirement)
- Native support for OpenAI, Anthropic, and custom LLM providers
- Built-in cost tracking and token counting
- Real-time streaming capabilities via SSE
- Production-ready with enterprise features (retention, RBAC)

**Alternatives Considered**:
- **LangSmith**: More tightly coupled to LangChain, less flexible for custom integrations
- **Weights & Biases**: Better for ML training, overkill for LLM tracing
- **Custom solution**: Would require significant development time and wouldn't meet <2% overhead requirement

**Implementation Approach**:
```python
# Async callback handler to minimize overhead
from langfuse import Langfuse
from langfuse.callback import CallbackHandler

# Trace collection with context propagation
class CrewAILangfuseHandler(CallbackHandler):
    async def on_llm_start(self, execution_id, agent_id, **kwargs):
        # Record trace with execution context
        pass

    async def on_llm_end(self, trace_id, response, tokens, cost):
        # Update trace with results
        pass
```

**Key Patterns**:
- Context propagation: Attach execution_id, tenant_id to all traces
- Graceful degradation: Catch Langfuse errors, never fail execution
- Batch flushing: Use Langfuse SDK's built-in batching for efficiency

---

### 2. Artifact Storage Architecture

**Decision**: Hybrid S3/local filesystem with PostgreSQL metadata layer

**Rationale**:
- **File storage**: S3 for production, local filesystem for development/testing
- **Metadata storage**: PostgreSQL for searchability, relationships, tenant isolation
- **Separation of concerns**: File bytes separate from searchable metadata
- **Scalability**: S3 handles large files, Postgres handles fast queries
- **Cost efficiency**: Hot/cold storage tiers for retention management

**Alternatives Considered**:
- **MongoDB GridFS**: Less efficient for large files, harder to manage retention
- **Direct S3 only**: Poor search performance, complex metadata queries
- **PostgreSQL BYTEA**: Not scalable for large files (>10MB), VACUUM issues

**Storage Structure**:
```
S3/filesystem:
  /{tenant_id}/
    /{execution_id}/
      /{version}/
        /{artifact_id}.{extension}

PostgreSQL:
  artifacts table:
    - id, tenant_id, execution_id, version, storage_path
    - metadata: name, size, mime_type, created_at
  artifact_metadata table:
    - artifact_id, tags[], description, type (document/image/data/code)
```

**Key Patterns**:
- Pre-signed URLs for direct S3 downloads (avoid proxying large files through API)
- Multipart uploads for files >5MB
- Async upload workers to prevent blocking executions

---

### 3. Artifact Preview Generation

**Decision**: Server-side preview generation with caching

**Rationale**:
- **Security**: Don't trust client-side rendering for untrusted files
- **Performance**: Cache generated previews in Redis (TTL 1 hour)
- **Consistency**: Same preview experience across all clients
- **Resource limits**: Prevent DoS via file size limits (<10MB for preview)

**Preview Strategies by File Type**:

| File Type | Strategy | Library |
|-----------|----------|---------|
| JSON | Parse + syntax highlight | `pygments` |
| CSV | Parse first 100 rows → HTML table | `pandas` |
| Images (PNG/JPG) | Thumbnail generation (max 800x600) | `Pillow` |
| PDF | First page thumbnail | `PyMuPDF` or `pdf2image` |
| Code (PY/JS/TS) | Syntax highlight | `pygments` |
| Text (TXT/MD/LOG) | Plain text with line numbers | Built-in |

**Alternatives Considered**:
- **Client-side preview**: Security risk with malicious files, inconsistent UX
- **External service (e.g., Google Docs Viewer)**: Data privacy concerns, latency
- **No preview**: Poor UX, forces downloads for inspection

**Implementation Pattern**:
```python
class PreviewGenerator:
    def generate_preview(self, file_path: str, mime_type: str) -> dict:
        # Check cache first
        cache_key = f"preview:{file_hash}"
        if cached := redis.get(cache_key):
            return cached

        # Generate preview based on type
        preview = self._generate_by_type(file_path, mime_type)

        # Cache with 1 hour TTL
        redis.setex(cache_key, 3600, preview)
        return preview
```

---

### 4. Dashboard Metrics Aggregation

**Decision**: Redis-cached materialized views with ClickHouse (optional)

**Rationale**:
- **Real-time metrics**: Redis cache for fast dashboard loads (<5 seconds, NFR-003)
- **Aggregation strategy**: Pre-compute metrics on trace ingestion
- **Time-series data**: ClickHouse for historical analytics (optional enhancement)
- **Multi-tenant**: Separate cache keys per tenant

**Metric Computation**:
```python
# On trace ingestion (async worker)
async def update_metrics(trace: Trace):
    tenant_id = trace.tenant_id
    period = "daily"  # or weekly, monthly

    # Increment counters in Redis
    redis.hincrby(f"metrics:{tenant_id}:{period}", "total_tokens", trace.tokens)
    redis.hincrby(f"metrics:{tenant_id}:{period}", "total_cost", trace.cost)
    redis.lpush(f"latencies:{tenant_id}:{period}", trace.latency)

    # TTL = retention period + 7 days buffer
    redis.expire(f"metrics:{tenant_id}:{period}", retention_days * 86400 + 604800)
```

**Alternatives Considered**:
- **On-demand aggregation**: Too slow for large datasets, violates NFR-003
- **PostgreSQL materialized views**: Refresh overhead, less flexible than Redis
- **ClickHouse only**: Overkill for MVP, adds operational complexity

**Key Patterns**:
- Incremental updates (no full recalculation)
- Percentile calculation via HyperLogLog or reservoir sampling
- Cache invalidation on retention policy changes

---

### 5. Retention & Cleanup Workers

**Decision**: Celery periodic tasks with configurable strategies

**Rationale**:
- **Existing infrastructure**: Already using Celery for async workers
- **Flexibility**: Per-tenant cleanup policies (oldest/largest/LRU/block)
- **Safety**: Soft delete with grace period before hard delete
- **Observability**: Track cleanup jobs in execution logs

**Cleanup Strategies**:

| Strategy | When Used | Implementation |
|----------|-----------|----------------|
| Oldest First (FIFO) | Default for most tenants | `ORDER BY created_at ASC LIMIT batch_size` |
| Largest First | When nearing quota quickly | `ORDER BY size DESC LIMIT batch_size` |
| Least Accessed (LRU) | For active tenants | Track `last_accessed_at`, delete oldest access |
| Block Uploads | Critical overages | Return 403, require manual cleanup |

**Worker Schedule**:
```python
# Celery beat schedule
@app.task
def cleanup_expired_artifacts():
    # Run every 6 hours
    for tenant in Tenant.all():
        retention_days = tenant.artifact_retention_days
        cutoff = now() - timedelta(days=retention_days)

        # Soft delete first
        artifacts = Artifact.filter(tenant=tenant, created_at__lt=cutoff)
        artifacts.update(deleted_at=now())

        # Hard delete after 7 day grace period
        hard_cutoff = now() - timedelta(days=7)
        Artifact.filter(deleted_at__lt=hard_cutoff).delete()
```

**Alternatives Considered**:
- **Database triggers**: Less flexible, harder to customize per tenant
- **S3 lifecycle policies**: Can't implement custom strategies (LRU, selective)
- **Manual cleanup only**: Poor UX, violates FR-018

---

### 6. Real-Time Trace Streaming

**Decision**: Server-Sent Events (SSE) for trace streaming

**Rationale**:
- **Existing pattern**: Already using SSE for execution streaming
- **Simplicity**: Unidirectional (server → client), no WebSocket complexity
- **Compatibility**: Works through HTTP proxies, no special firewall rules
- **Efficiency**: HTTP/2 multiplexing for multiple streams

**Streaming Architecture**:
```
1. Execution starts → Langfuse callback handler activated
2. Trace data collected → Published to Redis pub/sub
3. SSE endpoint subscribed to Redis channel
4. Client receives trace events in real-time
5. Execution ends → Stream closes
```

**Alternatives Considered**:
- **WebSocket**: Bidirectional overhead not needed, more complex
- **Polling**: Inefficient, higher latency, server load
- **Langfuse UI**: External dependency, not integrated with CrewAI UI

---

### 7. Multi-Provider LLM Support

**Decision**: Provider-agnostic trace collection via CrewAI SDK hooks

**Rationale**:
- **Integration point**: Hook into CrewAI's LLM abstraction layer
- **Consistency**: Same trace format regardless of provider
- **Extensibility**: New providers automatically supported via CrewAI

**Provider Coverage**:
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude)
- Cohere
- Local models (via CrewAI's local LLM support)
- Custom LLM endpoints

**Key Pattern**:
```python
# CrewAI integration hook
from crewai import Agent, LLM

class TracedLLM(LLM):
    def __init__(self, *args, langfuse_handler=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.langfuse_handler = langfuse_handler

    async def generate(self, prompt, **kwargs):
        trace_id = self.langfuse_handler.start_trace(prompt)
        response = await super().generate(prompt, **kwargs)
        self.langfuse_handler.end_trace(trace_id, response)
        return response
```

---

## Research Summary

All technical unknowns resolved:

| Area | Technology | Rationale |
|------|------------|-----------|
| LLM Tracing | Langfuse SDK + async handlers | <2% overhead, multi-provider support |
| Artifact Storage | S3/local + PostgreSQL metadata | Scalable, searchable, cost-efficient |
| Preview Generation | Server-side with Redis cache | Secure, fast (<3s), consistent |
| Metrics Aggregation | Redis + optional ClickHouse | Fast dashboard (<5s), real-time |
| Cleanup Workers | Celery periodic tasks | Flexible policies, existing infra |
| Trace Streaming | Server-Sent Events (SSE) | Simple, efficient, existing pattern |
| Multi-Provider Support | CrewAI SDK integration | Consistent tracing across providers |

**Next Phase**: Design data models and API contracts based on research decisions.
