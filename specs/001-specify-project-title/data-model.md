# Data Model: Dynamic CrewAI Orchestration Platform

**Date**: 2025-10-05
**Phase**: 1 - Design & Contracts
**Storage**: PostgreSQL 15 (relational entities) + MongoDB 6 (logs, chat, audit)

## Overview

The platform uses a hybrid storage model:
- **PostgreSQL**: Core entities (tenants, users, flows, agents, crews, tools, executions)
- **MongoDB**: High-write-throughput data (execution logs, chat messages, audit logs)

All PostgreSQL tables reside in tenant-specific schemas (`tenant_{slug}`) except for the `public.tenants` table which is global.

---

## PostgreSQL Entities

### 1. Tenant (Global Schema: `public`)

**Purpose**: Represents an organization with isolated workspace

**Table**: `public.tenants`

**Fields**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY | Unique tenant identifier |
| `name` | VARCHAR(255) | NOT NULL | Organization display name |
| `slug` | VARCHAR(100) | UNIQUE, NOT NULL | URL-safe identifier |
| `db_schema` | VARCHAR(100) | UNIQUE, NOT NULL | PostgreSQL schema name |
| `created_at` | TIMESTAMP | NOT NULL | Tenant registration timestamp |
| `status` | ENUM | NOT NULL | active, suspended, deleted |
| `settings` | JSONB | NOT NULL, DEFAULT '{}' | Tenant-wide configuration |
| `quotas` | JSONB | NOT NULL | Resource limits (see ResourceQuota) |
| `billing_info` | JSONB | NULL | Payment and subscription details |

**Relationships**:
- Has many: Users, Flows, Agents, Crews, Tools, LLMProviders (via tenant_id foreign key in tenant schemas)

**Indexes**:
- `idx_tenants_slug` on `slug` (unique lookup)
- `idx_tenants_status` on `status` (filter active tenants)

**Validation**:
- `slug` must match `^[a-z0-9-]+$` (lowercase alphanumeric + hyphens)
- `db_schema` must be `tenant_{slug}`
- `quotas` must include: `max_flows`, `max_executions_per_day`, `max_storage_gb`, `max_llm_tokens_per_day`

**State Transitions**:
```
active ──suspend──> suspended ──reactivate──> active
   │                                            │
   └──────────────────delete───────────────────┘
                       ↓
                   deleted (soft delete)
```

---

### 2. User (Tenant Schema: `tenant_{slug}.users`)

**Purpose**: Represents an individual account within a tenant

**Fields**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY | Unique user identifier |
| `tenant_id` | UUID | NOT NULL | Foreign key to public.tenants |
| `email` | VARCHAR(255) | NOT NULL | User email (unique per tenant) |
| `password_hash` | VARCHAR(255) | NOT NULL | Bcrypt hashed password |
| `role` | ENUM | NOT NULL | admin, editor, viewer, executor |
| `created_at` | TIMESTAMP | NOT NULL | Account creation timestamp |
| `last_login` | TIMESTAMP | NULL | Last successful login |
| `preferences` | JSONB | NOT NULL, DEFAULT '{}' | UI preferences, notifications |
| `status` | ENUM | NOT NULL | active, invited, disabled |

**Relationships**:
- Belongs to: Tenant (via tenant_id)
- Has many: Flows (as creator), ChatSessions, Executions (as initiator)

**Indexes**:
- `idx_users_tenant_email` on `(tenant_id, email)` (unique constraint)
- `idx_users_role` on `role` (RBAC filtering)

**Validation**:
- `email` must be valid email format (RFC 5322)
- `password_hash` must be bcrypt with cost factor ≥ 12
- `role` must be one of: admin, editor, viewer, executor

**RBAC Permissions**:
- **admin**: Full tenant control, user management, billing
- **editor**: Create/edit/delete flows, agents, crews, tools
- **viewer**: Read-only access to all resources
- **executor**: Execute flows, view execution logs (no edit)

---

### 3. Agent (Tenant Schema: `tenant_{slug}.agents`)

**Purpose**: AI agent configuration with assigned LLM

**Fields**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY | Unique agent identifier |
| `tenant_id` | UUID | NOT NULL | Foreign key to public.tenants |
| `name` | VARCHAR(255) | NOT NULL | Agent display name |
| `description` | TEXT | NULL | Agent purpose and capabilities |
| `system_prompt` | TEXT | NOT NULL | Agent instructions and personality |
| `llm_provider_id` | UUID | NOT NULL | Foreign key to llm_providers |
| `config` | JSONB | NOT NULL, DEFAULT '{}' | CrewAI agent config (temperature, max_tokens, etc.) |
| `version` | INTEGER | NOT NULL, DEFAULT 1 | Agent version number |
| `status` | ENUM | NOT NULL | draft, active, archived |
| `created_at` | TIMESTAMP | NOT NULL | Agent creation timestamp |
| `updated_at` | TIMESTAMP | NOT NULL | Last modification timestamp |

**Relationships**:
- Belongs to: Tenant, LLMProvider
- Belongs to many: Crews (via crew_agents join table)
- Has many: AgentVersions (version history)

**Indexes**:
- `idx_agents_tenant` on `tenant_id`
- `idx_agents_status` on `status`
- `idx_agents_llm_provider` on `llm_provider_id`

**Validation**:
- `name` must be non-empty
- `system_prompt` must be non-empty
- `config` must be valid JSON matching CrewAI agent schema
- `version` increments on each update

---

### 4. Crew (Tenant Schema: `tenant_{slug}.crews`)

**Purpose**: Group of agents that collaborate on tasks

**Fields**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY | Unique crew identifier |
| `tenant_id` | UUID | NOT NULL | Foreign key to public.tenants |
| `name` | VARCHAR(255) | NOT NULL | Crew display name |
| `description` | TEXT | NULL | Crew purpose and use case |
| `collaboration_pattern` | ENUM | NOT NULL | sequential, hierarchical |
| `config` | JSONB | NOT NULL, DEFAULT '{}' | CrewAI crew config (max_rpm, memory, etc.) |
| `status` | ENUM | NOT NULL | draft, active, archived |
| `created_at` | TIMESTAMP | NOT NULL | Crew creation timestamp |
| `updated_at` | TIMESTAMP | NOT NULL | Last modification timestamp |

**Relationships**:
- Belongs to: Tenant
- Has many: Agents (via crew_agents join table)
- Has many: ChatSessions (crews used in chat)

**Indexes**:
- `idx_crews_tenant` on `tenant_id`
- `idx_crews_status` on `status`

**Join Table** (`crew_agents`):
| Field | Type | Constraints |
|-------|------|-------------|
| `crew_id` | UUID | NOT NULL, FK to crews |
| `agent_id` | UUID | NOT NULL, FK to agents |
| `position` | INTEGER | NOT NULL |

**Validation**:
- Must have at least one agent
- `collaboration_pattern` must be one of: sequential (agents run in order), hierarchical (manager assigns tasks)
- `position` in `crew_agents` determines execution order for sequential crews

---

### 5. Flow (Tenant Schema: `tenant_{slug}.flows`)

**Purpose**: Visual workflow composed of nodes (agents, tools, LLMs) and edges

**Fields**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY | Unique flow identifier |
| `tenant_id` | UUID | NOT NULL | Foreign key to public.tenants |
| `user_id` | UUID | NOT NULL | Foreign key to users (creator) |
| `name` | VARCHAR(255) | NOT NULL | Flow display name |
| `description` | TEXT | NULL | Flow purpose and functionality |
| `nodes` | JSONB | NOT NULL | Array of flow nodes (see schema below) |
| `edges` | JSONB | NOT NULL | Array of flow edges (see schema below) |
| `input_schema` | JSONB | NULL | JSON Schema for flow inputs |
| `output_schema` | JSONB | NULL | JSON Schema for flow outputs |
| `version` | INTEGER | NOT NULL, DEFAULT 1 | Flow version number |
| `status` | ENUM | NOT NULL | draft, published, archived |
| `created_at` | TIMESTAMP | NOT NULL | Flow creation timestamp |
| `updated_at` | TIMESTAMP | NOT NULL | Last modification timestamp |

**Node Schema** (JSONB):
```json
{
  "id": "node_uuid",
  "type": "agent | tool | llm | condition | input | output",
  "position": {"x": 100, "y": 200},
  "data": {
    // Type-specific data
    // For agent: {"agent_id": "uuid"}
    // For tool: {"tool_id": "uuid", "inputs": {...}}
    // For llm: {"llm_provider_id": "uuid", "prompt": "..."}
    // For condition: {"expression": "output.status == 'success'"}
  }
}
```

**Edge Schema** (JSONB):
```json
{
  "id": "edge_uuid",
  "source": "source_node_id",
  "target": "target_node_id",
  "sourceHandle": "output_port",
  "targetHandle": "input_port"
}
```

**Relationships**:
- Belongs to: Tenant, User (creator)
- Has many: Executions
- Has many: FlowVersions (version history)

**Indexes**:
- `idx_flows_tenant` on `tenant_id`
- `idx_flows_user` on `user_id`
- `idx_flows_status` on `status`

**Validation**:
- `nodes` must be non-empty JSON array
- `edges` must be JSON array (can be empty for single-node flows)
- DAG validation: no cycles unless node type allows loops
- All edge sources/targets must reference valid node IDs
- `input_schema` and `output_schema` must be valid JSON Schema (draft-07)

---

### 6. Tool (Tenant Schema: `tenant_{slug}.tools`)

**Purpose**: External capability invoked by agents (APIs, databases, plugins)

**Fields**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY | Unique tool identifier |
| `tenant_id` | UUID | NOT NULL | Foreign key to public.tenants |
| `name` | VARCHAR(255) | NOT NULL | Tool display name |
| `description` | TEXT | NOT NULL | Tool purpose and usage |
| `input_schema` | JSONB | NOT NULL | JSON Schema for tool inputs |
| `output_schema` | JSONB | NOT NULL | JSON Schema for tool outputs |
| `execution_config` | JSONB | NOT NULL | Docker image, entrypoint, env vars |
| `credentials` | TEXT | NULL | Encrypted credentials (AES-256) |
| `status` | ENUM | NOT NULL | active, disabled |
| `created_at` | TIMESTAMP | NOT NULL | Tool creation timestamp |
| `updated_at` | TIMESTAMP | NOT NULL | Last modification timestamp |

**Execution Config Schema** (JSONB):
```json
{
  "docker_image": "python:3.11-slim",
  "entrypoint": ["/app/tool.py"],
  "env": {
    "API_KEY": "{{credentials.api_key}}"
  },
  "timeout_seconds": 300,
  "cpu_limit": "2",
  "memory_limit": "4Gi"
}
```

**Relationships**:
- Belongs to: Tenant
- Referenced by: Flow nodes (via `data.tool_id`)

**Indexes**:
- `idx_tools_tenant` on `tenant_id`
- `idx_tools_status` on `status`

**Validation**:
- `input_schema` and `output_schema` must be valid JSON Schema
- `credentials` encrypted with tenant-specific key (AES-256-GCM)
- `execution_config.docker_image` must be valid Docker image reference
- `execution_config.timeout_seconds` must be ≤ 3600 (1 hour)

---

### 7. Execution (Tenant Schema: `tenant_{slug}.executions`)

**Purpose**: Single run of a flow with inputs, outputs, and status

**Fields**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY | Unique execution identifier |
| `flow_id` | UUID | NOT NULL | Foreign key to flows |
| `user_id` | UUID | NOT NULL | Foreign key to users (initiator) |
| `status` | ENUM | NOT NULL | queued, running, succeeded, failed, cancelled, timeout |
| `start_time` | TIMESTAMP | NULL | Execution start timestamp |
| `end_time` | TIMESTAMP | NULL | Execution end timestamp |
| `inputs` | JSONB | NULL | Flow input parameters |
| `outputs` | JSONB | NULL | Flow output results |
| `logs_ref` | VARCHAR(255) | NULL | MongoDB collection reference |
| `error_message` | TEXT | NULL | Error details if failed |
| `created_at` | TIMESTAMP | NOT NULL | Execution queued timestamp |

**Relationships**:
- Belongs to: Flow, User
- Referenced by: ExecutionNode documents in MongoDB (via execution_id)

**Indexes**:
- `idx_executions_flow` on `flow_id`
- `idx_executions_user` on `user_id`
- `idx_executions_status` on `status`
- `idx_executions_created` on `created_at` (time-range queries)

**State Transitions**:
```
queued ──start──> running ──┬──success──> succeeded
                             ├──error────> failed
                             ├──cancel───> cancelled
                             └──timeout──> timeout
```

**Validation**:
- `inputs` must match `flow.input_schema` if defined
- `outputs` must match `flow.output_schema` if defined
- `logs_ref` format: `executions_{tenant_slug}` (MongoDB collection)
- Duration (`end_time - start_time`) must not exceed flow timeout (default 3600s)

---

### 8. ChatSession (Tenant Schema: `tenant_{slug}.chat_sessions`)

**Purpose**: Conversational interaction between user and crew

**Fields**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY | Unique session identifier |
| `tenant_id` | UUID | NOT NULL | Foreign key to public.tenants |
| `user_id` | UUID | NOT NULL | Foreign key to users |
| `crew_id` | UUID | NULL | Foreign key to crews (optional) |
| `attached_flow_id` | UUID | NULL | Foreign key to flows (optional) |
| `created_at` | TIMESTAMP | NOT NULL | Session start timestamp |
| `messages_ref` | VARCHAR(255) | NOT NULL | MongoDB collection reference |

**Relationships**:
- Belongs to: Tenant, User
- References: Crew (optional), Flow (optional)
- Messages stored in MongoDB (via messages_ref)

**Indexes**:
- `idx_chat_sessions_user` on `user_id`
- `idx_chat_sessions_crew` on `crew_id`

**Validation**:
- `messages_ref` format: `chat_messages_{tenant_slug}` (MongoDB collection)
- If `attached_flow_id` is set, crew can execute that flow during conversation

---

### 9. LLMProvider (Tenant Schema: `tenant_{slug}.llm_providers`)

**Purpose**: Configured AI model provider (OpenAI, Anthropic, Ollama, etc.)

**Fields**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY | Unique provider identifier |
| `tenant_id` | UUID | NOT NULL | Foreign key to public.tenants |
| `name` | VARCHAR(255) | NOT NULL | Provider display name |
| `provider_type` | ENUM | NOT NULL | openai, anthropic, ollama, vllm, custom |
| `api_credentials` | TEXT | NOT NULL | Encrypted credentials (AES-256) |
| `config` | JSONB | NOT NULL, DEFAULT '{}' | Provider-specific config (base_url, model, etc.) |
| `is_active` | BOOLEAN | NOT NULL, DEFAULT true | Enable/disable provider |
| `created_at` | TIMESTAMP | NOT NULL | Provider creation timestamp |
| `updated_at` | TIMESTAMP | NOT NULL | Last modification timestamp |

**Config Schema** (JSONB):
```json
{
  "base_url": "https://api.openai.com/v1",  // For custom providers
  "model": "gpt-4",
  "temperature": 0.7,
  "max_tokens": 2000,
  "top_p": 1.0
}
```

**Relationships**:
- Belongs to: Tenant
- Has many: Agents (agents using this provider)

**Indexes**:
- `idx_llm_providers_tenant` on `tenant_id`
- `idx_llm_providers_active` on `is_active`

**Validation**:
- `api_credentials` encrypted with tenant-specific key (AES-256-GCM)
- `provider_type` determines expected credential fields:
  - `openai`: `{"api_key": "sk-..."}`
  - `anthropic`: `{"api_key": "sk-ant-..."}`
  - `ollama`: `{"base_url": "http://ollama:11434"}`
  - `vllm`: `{"base_url": "http://vllm:8000", "api_key": "..."}`

---

## MongoDB Collections

### 10. ExecutionNode (Collection: `executions_{tenant_slug}`)

**Purpose**: Per-node execution logs for flow runs (high write throughput)

**Document Schema**:
```json
{
  "_id": ObjectId("..."),
  "execution_id": "uuid",
  "node_id": "uuid",
  "status": "queued | running | succeeded | failed",
  "start_time": ISODate("2025-10-05T12:00:00Z"),
  "end_time": ISODate("2025-10-05T12:01:30Z"),
  "inputs": {"key": "value"},
  "outputs": {"result": "data"},
  "logs": ["Log line 1", "Log line 2"],
  "metadata": {
    "duration_ms": 90000,
    "llm_tokens": 1234,
    "tool_invocations": 2
  }
}
```

**Indexes**:
- `execution_id` (query all nodes for an execution)
- `status` (filter by status)
- `start_time` (time-range queries)

---

### 11. ChatMessage (Collection: `chat_messages_{tenant_slug}`)

**Purpose**: Chat session messages

**Document Schema**:
```json
{
  "_id": ObjectId("..."),
  "session_id": "uuid",
  "role": "user | assistant | system",
  "content": "Message text",
  "timestamp": ISODate("2025-10-05T12:00:00Z"),
  "metadata": {
    "agent_id": "uuid",  // If assistant message from specific agent
    "tool_invocations": [
      {"tool_id": "uuid", "inputs": {...}, "outputs": {...}}
    ]
  }
}
```

**Indexes**:
- `session_id` (query messages for a session)
- `timestamp` (chronological order)

---

### 12. AuditLog (Collection: `audit_logs_{tenant_slug}`)

**Purpose**: Security and compliance event logging

**Document Schema**:
```json
{
  "_id": ObjectId("..."),
  "timestamp": ISODate("2025-10-05T12:00:00Z"),
  "tenant_id": "uuid",
  "user_id": "uuid",
  "action": "login | create_flow | execute_flow | delete_user | etc.",
  "resource_type": "flow | agent | crew | tool | user",
  "resource_id": "uuid",
  "metadata": {
    "ip_address": "192.168.1.1",
    "user_agent": "Mozilla/5.0...",
    "changes": {"field": "old_value -> new_value"}
  },
  "result": "success | failure",
  "error_message": "Error details if failure"
}
```

**Indexes**:
- `tenant_id` (tenant-specific audit trail)
- `timestamp` (time-range queries)
- `action` (filter by event type)
- `user_id` (user activity tracking)

---

## Entity Relationship Diagram (ERD)

```
public.tenants (1) ──< (N) tenant_{slug}.users
                  │
                  ├──< (N) tenant_{slug}.flows
                  ├──< (N) tenant_{slug}.agents
                  ├──< (N) tenant_{slug}.crews
                  ├──< (N) tenant_{slug}.tools
                  ├──< (N) tenant_{slug}.llm_providers
                  └──< (N) tenant_{slug}.chat_sessions

tenant_{slug}.users (1) ──< (N) flows (creator)
                       ├──< (N) executions (initiator)
                       └──< (N) chat_sessions

tenant_{slug}.agents (N) ──< (M) ──> (N) crews (via crew_agents)
                        └──> (1) llm_providers

tenant_{slug}.flows (1) ──< (N) executions

tenant_{slug}.crews (1) ──< (N) chat_sessions

tenant_{slug}.executions (1) ──> (N) MongoDB execution_nodes (via execution_id)

tenant_{slug}.chat_sessions (1) ──> (N) MongoDB chat_messages (via session_id)
```

---

## Data Retention Policies

| Entity | Retention Period | Archive Strategy |
|--------|------------------|------------------|
| Tenants | Indefinite | Soft delete (`status = deleted`) |
| Users | Tenant lifetime | Anonymize on user deletion |
| Flows | Tenant lifetime | Soft delete (`status = archived`) |
| Agents/Crews | Tenant lifetime | Soft delete (`status = archived`) |
| Tools | Tenant lifetime | Hard delete (no historical value) |
| Executions | 90 days (default) | Move to cold storage (S3) after 90 days |
| ExecutionNode logs | 90 days | Delete after 90 days (or archive to S3) |
| ChatMessages | 1 year | Archive to S3 after 1 year |
| AuditLogs | 7 years (compliance) | Archive to S3 after 1 year, delete after 7 years |

**Configuration**: Retention periods configurable per tenant via `settings.retention_policies`

---

## Migration Strategy

1. **Initial Setup**:
   - Create `public.tenants` table
   - Create template schema `tenant_template` with all tables
   - Create MongoDB databases per tenant: `crewai_{tenant_slug}`

2. **New Tenant Registration**:
   ```sql
   CREATE SCHEMA tenant_{slug};
   -- Copy all tables from tenant_template
   ```

3. **Schema Versioning**:
   - Use Alembic for PostgreSQL migrations
   - Migrations run per schema (loop over all active tenant schemas)
   - Track migration version in `public.schema_versions` table

4. **Rollback Strategy**:
   - Each migration includes `upgrade()` and `downgrade()`
   - Migrations tested in staging tenant schemas before production rollout

---

## Summary

- **11 PostgreSQL entities** across global and tenant schemas
- **3 MongoDB collections** for high-throughput logging
- **Multi-tenant isolation** via PostgreSQL schemas
- **Hybrid storage** optimizes for both relational integrity and performance
- **Comprehensive validation** ensures data quality and security
- **Clear retention policies** for compliance and cost management

Ready for API contract generation (Phase 1.2).
