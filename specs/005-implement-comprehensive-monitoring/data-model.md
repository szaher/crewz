# Data Model: Monitoring & Observability

**Feature**: 005-implement-comprehensive-monitoring
**Date**: 2025-01-22

## Entity Definitions

### 1. Trace

**Purpose**: Represents a single LLM interaction captured during execution

**Fields**:
```python
class Trace:
    id: UUID (PK)
    tenant_id: UUID (FK → Tenant, indexed)
    execution_id: UUID (FK → Execution, indexed)
    agent_id: UUID (FK → Agent, nullable) # Which agent made the call
    tool_id: UUID (FK → Tool, nullable)   # Which tool made the call

    # Trace content
    prompt: Text                   # Input to LLM
    response: Text                 # Output from LLM
    model_name: String(100)        # e.g., "gpt-4", "claude-3"
    provider: String(50)           # e.g., "openai", "anthropic"

    # Metrics
    prompt_tokens: Integer
    completion_tokens: Integer
    total_tokens: Integer
    latency_ms: Integer           # Time from request to response
    cost_usd: Decimal(10, 6)      # Estimated cost

    # Metadata
    created_at: DateTime (indexed)
    langfuse_trace_id: String(100) # Reference to Langfuse external system
    error_message: Text (nullable)  # If trace failed
    metadata: JSONB                # Additional context

    # Indexes
    INDEX idx_trace_tenant_created (tenant_id, created_at DESC)
    INDEX idx_trace_execution (execution_id)
    INDEX idx_trace_created (created_at)  # For retention cleanup
```

**Relationships**:
- Belongs to Execution (many Traces → one Execution)
- Belongs to Tenant (for multi-tenancy isolation)
- References Agent or Tool (which entity made the LLM call)

**Validation Rules**:
- `total_tokens` = `prompt_tokens` + `completion_tokens`
- `latency_ms` > 0
- `cost_usd` >= 0
- Either `agent_id` OR `tool_id` must be set (not both, not neither)

**State Transitions**: N/A (immutable once created)

---

### 2. TraceMetrics

**Purpose**: Aggregated statistics for monitoring dashboard (pre-computed)

**Fields**:
```python
class TraceMetrics:
    id: UUID (PK)
    tenant_id: UUID (FK → Tenant, indexed)

    # Time period
    period_type: Enum('hour', 'day', 'week', 'month')
    period_start: DateTime (indexed)
    period_end: DateTime

    # Aggregations
    total_executions: Integer      # Number of executions in period
    total_traces: Integer          # Number of LLM calls
    total_tokens: BigInteger       # Sum of all tokens
    total_cost_usd: Decimal(12, 2) # Sum of all costs

    # Performance metrics
    avg_latency_ms: Integer
    p50_latency_ms: Integer
    p95_latency_ms: Integer
    p99_latency_ms: Integer

    # Error tracking
    error_count: Integer
    error_rate: Decimal(5, 2)     # Percentage

    # Breakdown by entity type
    metrics_by_type: JSONB        # {crew: {...}, agent: {...}, tool: {...}, flow: {...}}

    # Metadata
    created_at: DateTime
    updated_at: DateTime

    # Indexes
    INDEX idx_metrics_tenant_period (tenant_id, period_type, period_start DESC)
    UNIQUE idx_metrics_unique (tenant_id, period_type, period_start)
```

**Relationships**:
- Belongs to Tenant

**Validation Rules**:
- `period_end` > `period_start`
- `error_rate` = (`error_count` / `total_traces`) * 100
- `total_tokens` >= 0, `total_cost_usd` >= 0

**State Transitions**:
- Created on first trace in period
- Updated incrementally as new traces arrive
- Deleted after retention period + 30 days

---

### 3. Artifact

**Purpose**: Represents a file produced by an execution

**Fields**:
```python
class Artifact:
    id: UUID (PK)
    tenant_id: UUID (FK → Tenant, indexed)
    execution_id: UUID (FK → Execution, indexed)
    execution_version: Integer    # For re-executions

    # File information
    file_name: String(255)
    file_extension: String(10)
    file_size_bytes: BigInteger
    mime_type: String(100)
    storage_path: String(500)     # S3 key or filesystem path

    # Artifact classification
    artifact_type: Enum('document', 'image', 'data', 'code', 'other')

    # Preview support
    has_preview: Boolean
    preview_url: String(500) (nullable)  # Pre-signed URL or cache key

    # Metadata
    created_at: DateTime (indexed)
    last_accessed_at: DateTime (nullable, indexed)  # For LRU cleanup
    deleted_at: DateTime (nullable, indexed)        # Soft delete

    # Indexes
    INDEX idx_artifact_tenant_created (tenant_id, created_at DESC)
    INDEX idx_artifact_execution (execution_id, execution_version)
    INDEX idx_artifact_type (tenant_id, artifact_type)
    INDEX idx_artifact_deleted (deleted_at)  # For cleanup workers
    INDEX idx_artifact_lru (tenant_id, last_accessed_at)  # LRU cleanup
```

**Relationships**:
- Belongs to Execution
- Belongs to Tenant
- Has one ArtifactMetadata (optional enrichment)

**Validation Rules**:
- `file_size_bytes` > 0
- `file_size_bytes` <= tenant's `max_artifact_size_bytes`
- `file_extension` matches `mime_type` (e.g., ".json" → "application/json")
- `execution_version` >= 1

**State Transitions**:
```
Created → Active → Soft Deleted → Hard Deleted
          ↓
          Accessed (update last_accessed_at)
```

---

### 4. ArtifactMetadata

**Purpose**: Enriches artifacts with user-provided searchable information

**Fields**:
```python
class ArtifactMetadata:
    id: UUID (PK)
    artifact_id: UUID (FK → Artifact, unique)

    # User-provided metadata
    tags: ARRAY[String]           # User-defined tags for categorization
    description: Text (nullable)  # User-provided description
    category: String(100) (nullable)  # Custom category

    # System metadata
    checksum_sha256: String(64)   # File integrity verification
    compression_type: String(20) (nullable)  # If file is compressed

    # Relationships
    related_artifacts: ARRAY[UUID]  # Links to related artifacts

    # Metadata
    created_at: DateTime
    updated_at: DateTime

    # Indexes
    INDEX idx_metadata_tags (tags) USING GIN  # Full-text search on tags
    INDEX idx_metadata_description (description) USING GIN  # Full-text search
```

**Relationships**:
- Belongs to Artifact (one-to-one)

**Validation Rules**:
- `checksum_sha256` matches actual file checksum
- `tags` array max length 20 tags
- Each tag max length 50 characters

**State Transitions**: Updated independently of Artifact

---

### 5. TenantConfig

**Purpose**: Per-tenant configuration for storage quotas and retention policies

**Fields**:
```python
class TenantConfig:
    id: UUID (PK)
    tenant_id: UUID (FK → Tenant, unique)

    # Storage quotas (configurable per tenant)
    total_storage_quota_bytes: BigInteger
    max_artifact_size_bytes: BigInteger
    current_storage_used_bytes: BigInteger  # Updated on upload/delete

    # Retention policies (tier-based defaults, tenant overrides)
    trace_retention_days: Integer         # Free: 7, Pro: 30, Enterprise: 90
    artifact_retention_days: Integer      # Free: 30, Pro: 90, Enterprise: 180

    # Cleanup policy (configurable per tenant)
    cleanup_strategy: Enum('oldest_first', 'largest_first', 'lru', 'block_uploads')

    # Quota alerts
    quota_warning_threshold: Decimal(3, 2)  # Default 0.80 (80%)
    quota_alert_threshold: Decimal(3, 2)    # Default 0.95 (95%)

    # Metadata
    created_at: DateTime
    updated_at: DateTime
```

**Relationships**:
- Belongs to Tenant (one-to-one)

**Validation Rules**:
- `current_storage_used_bytes` <= `total_storage_quota_bytes` (enforced on upload)
- `max_artifact_size_bytes` <= `total_storage_quota_bytes`
- `trace_retention_days` >= 1
- `artifact_retention_days` >= 1
- `0 < quota_warning_threshold < quota_alert_threshold <= 1.0`

**State Transitions**:
- `current_storage_used_bytes` incremented on artifact upload
- `current_storage_used_bytes` decremented on artifact delete

---

## Entity Relationships Diagram

```
┌─────────┐
│ Tenant  │
└────┬────┘
     │
     ├──────────────┬──────────────┬──────────────┐
     │              │              │              │
     ▼              ▼              ▼              ▼
┌─────────┐   ┌──────────┐  ┌──────────┐  ┌──────────────┐
│  Trace  │   │ Artifact │  │TraceMetr…│  │TenantConfig  │
└────┬────┘   └────┬─────┘  └──────────┘  └──────────────┘
     │             │
     │             ├──────────────┐
     │             │              │
     ▼             ▼              ▼
┌───────────┐  ┌──────────┐  ┌──────────────────┐
│ Execution │  │Execution │  │ArtifactMetadata  │
└───────────┘  └──────────┘  └──────────────────┘
```

---

## Database Migrations

### Migration 001: Create Trace Tables
```sql
CREATE TABLE traces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    execution_id UUID NOT NULL REFERENCES executions(id),
    agent_id UUID REFERENCES agents(id),
    tool_id UUID REFERENCES tools(id),

    prompt TEXT NOT NULL,
    response TEXT NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    provider VARCHAR(50) NOT NULL,

    prompt_tokens INTEGER NOT NULL,
    completion_tokens INTEGER NOT NULL,
    total_tokens INTEGER NOT NULL,
    latency_ms INTEGER NOT NULL,
    cost_usd DECIMAL(10, 6) NOT NULL DEFAULT 0,

    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    langfuse_trace_id VARCHAR(100),
    error_message TEXT,
    metadata JSONB,

    CONSTRAINT chk_trace_tokens CHECK (total_tokens = prompt_tokens + completion_tokens),
    CONSTRAINT chk_trace_entity CHECK (
        (agent_id IS NOT NULL AND tool_id IS NULL) OR
        (agent_id IS NULL AND tool_id IS NOT NULL)
    )
);

CREATE INDEX idx_trace_tenant_created ON traces(tenant_id, created_at DESC);
CREATE INDEX idx_trace_execution ON traces(execution_id);
CREATE INDEX idx_trace_created ON traces(created_at);
```

### Migration 002: Create TraceMetrics Tables
```sql
CREATE TYPE period_type AS ENUM ('hour', 'day', 'week', 'month');

CREATE TABLE trace_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),

    period_type period_type NOT NULL,
    period_start TIMESTAMP NOT NULL,
    period_end TIMESTAMP NOT NULL,

    total_executions INTEGER NOT NULL DEFAULT 0,
    total_traces INTEGER NOT NULL DEFAULT 0,
    total_tokens BIGINT NOT NULL DEFAULT 0,
    total_cost_usd DECIMAL(12, 2) NOT NULL DEFAULT 0,

    avg_latency_ms INTEGER NOT NULL DEFAULT 0,
    p50_latency_ms INTEGER NOT NULL DEFAULT 0,
    p95_latency_ms INTEGER NOT NULL DEFAULT 0,
    p99_latency_ms INTEGER NOT NULL DEFAULT 0,

    error_count INTEGER NOT NULL DEFAULT 0,
    error_rate DECIMAL(5, 2) NOT NULL DEFAULT 0,
    metrics_by_type JSONB,

    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_metrics_period CHECK (period_end > period_start)
);

CREATE INDEX idx_metrics_tenant_period ON trace_metrics(tenant_id, period_type, period_start DESC);
CREATE UNIQUE INDEX idx_metrics_unique ON trace_metrics(tenant_id, period_type, period_start);
```

### Migration 003: Create Artifact Tables
```sql
CREATE TYPE artifact_type AS ENUM ('document', 'image', 'data', 'code', 'other');

CREATE TABLE artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    execution_id UUID NOT NULL REFERENCES executions(id),
    execution_version INTEGER NOT NULL DEFAULT 1,

    file_name VARCHAR(255) NOT NULL,
    file_extension VARCHAR(10) NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    storage_path VARCHAR(500) NOT NULL,

    artifact_type artifact_type NOT NULL DEFAULT 'other',

    has_preview BOOLEAN NOT NULL DEFAULT FALSE,
    preview_url VARCHAR(500),

    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_accessed_at TIMESTAMP,
    deleted_at TIMESTAMP,

    CONSTRAINT chk_artifact_size CHECK (file_size_bytes > 0)
);

CREATE INDEX idx_artifact_tenant_created ON artifacts(tenant_id, created_at DESC);
CREATE INDEX idx_artifact_execution ON artifacts(execution_id, execution_version);
CREATE INDEX idx_artifact_type ON artifacts(tenant_id, artifact_type);
CREATE INDEX idx_artifact_deleted ON artifacts(deleted_at) WHERE deleted_at IS NOT NULL;
CREATE INDEX idx_artifact_lru ON artifacts(tenant_id, last_accessed_at);

CREATE TABLE artifact_metadata (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    artifact_id UUID NOT NULL UNIQUE REFERENCES artifacts(id) ON DELETE CASCADE,

    tags TEXT[],
    description TEXT,
    category VARCHAR(100),

    checksum_sha256 VARCHAR(64) NOT NULL,
    compression_type VARCHAR(20),
    related_artifacts UUID[],

    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_metadata_tags ON artifact_metadata USING GIN(tags);
CREATE INDEX idx_metadata_description ON artifact_metadata USING GIN(to_tsvector('english', description));
```

### Migration 004: Create TenantConfig Table
```sql
CREATE TYPE cleanup_strategy AS ENUM ('oldest_first', 'largest_first', 'lru', 'block_uploads');

CREATE TABLE tenant_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL UNIQUE REFERENCES tenants(id),

    total_storage_quota_bytes BIGINT NOT NULL,
    max_artifact_size_bytes BIGINT NOT NULL,
    current_storage_used_bytes BIGINT NOT NULL DEFAULT 0,

    trace_retention_days INTEGER NOT NULL DEFAULT 7,
    artifact_retention_days INTEGER NOT NULL DEFAULT 30,

    cleanup_strategy cleanup_strategy NOT NULL DEFAULT 'oldest_first',

    quota_warning_threshold DECIMAL(3, 2) NOT NULL DEFAULT 0.80,
    quota_alert_threshold DECIMAL(3, 2) NOT NULL DEFAULT 0.95,

    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_config_quota CHECK (current_storage_used_bytes <= total_storage_quota_bytes),
    CONSTRAINT chk_config_retention CHECK (trace_retention_days >= 1 AND artifact_retention_days >= 1),
    CONSTRAINT chk_config_thresholds CHECK (quota_warning_threshold < quota_alert_threshold AND quota_alert_threshold <= 1.0)
);
```

---

## Storage Calculations

**Trace Storage**:
- Average trace: ~5KB (prompt + response text)
- 1000 executions/day × 10 traces/execution = 10,000 traces/day
- Daily storage: 10,000 × 5KB = 50MB/day
- 30-day retention: 50MB × 30 = 1.5GB

**Artifact Storage**:
- Highly variable (1KB to max tenant limit)
- Assume average 500KB per artifact
- 1000 executions/day × 2 artifacts/execution = 2,000 artifacts/day
- Daily storage: 2,000 × 500KB = 1GB/day
- 90-day retention: 1GB × 90 = 90GB

**Total per 1000 tenants**: ~91.5GB × 1000 = 91.5TB (with 90-day artifact retention)

---

## Next Phase

Data model complete. Next: Generate API contracts for trace/artifact endpoints.
