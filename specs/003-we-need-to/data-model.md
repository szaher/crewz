# Data Model: Platform Infrastructure Enhancements

**Feature**: Platform Infrastructure Enhancements
**Branch**: `003-we-need-to`
**Date**: 2025-10-12

## Overview

This document defines the complete data model for the Platform Infrastructure Enhancements feature, including:
- 11 new entities for authorization, execution queue, notifications, and tenant management
- UUID migration specifications for 20+ existing entities
- Indexes, constraints, and relationships
- Validation rules and business logic

---

## Part 1: New Entities

### 1. Permission (Authorization Domain)

Represents a fine-grained permission grant for a subject (user or role) on a resource.

**Table**: `permissions`

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PK, NOT NULL | Primary key (UUIDv7) |
| `tenant_id` | UUID | NOT NULL, FK → tenants.id | Tenant isolation |
| `subject_type` | ENUM('user', 'role') | NOT NULL | Type of subject |
| `subject_id` | UUID | NOT NULL | ID of user or role |
| `resource_type` | VARCHAR(50) | NOT NULL | Entity type (e.g., 'crew', 'flow') |
| `resource_id` | UUID | NULLABLE | Specific resource ID (NULL = all) |
| `action` | ENUM('read', 'write', 'execute', 'delete', '*') | NOT NULL | Allowed action |
| `effect` | ENUM('allow', 'deny') | NOT NULL, DEFAULT 'allow' | Permission effect |
| `conditions` | JSONB | NULLABLE | ABAC conditions (e.g., {"time_range": "9-17"}) |
| `created_by` | UUID | NOT NULL, FK → users.id | Creator |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Creation timestamp |
| `updated_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Last update |

**Indexes**:
```sql
CREATE INDEX idx_permissions_subject ON permissions(subject_type, subject_id);
CREATE INDEX idx_permissions_resource ON permissions(resource_type, resource_id);
CREATE INDEX idx_permissions_tenant ON permissions(tenant_id);
```

**Unique Constraints**:
```sql
-- Prevent duplicate permissions
ALTER TABLE permissions ADD CONSTRAINT unique_permission
    UNIQUE (subject_type, subject_id, resource_type, COALESCE(resource_id, '00000000-0000-0000-0000-000000000000'::uuid), action);
```

**Validation Rules**:
- `subject_id` must exist in `users.id` (if subject_type='user') or `roles.id` (if subject_type='role')
- `resource_id` must exist in the appropriate table (if not NULL)
- `action` must be valid for the resource_type (e.g., 'execute' only for crews/flows)

**Example**:
```json
{
  "id": "018e1234-5678-7abc-def0-123456789abc",
  "tenant_id": "018e0000-0000-7000-0000-000000000001",
  "subject_type": "user",
  "subject_id": "018e1111-1111-7111-1111-111111111111",
  "resource_type": "crew",
  "resource_id": "018e2222-2222-7222-2222-222222222222",
  "action": "execute",
  "effect": "allow",
  "conditions": null,
  "created_by": "018e1111-1111-7111-1111-111111111111",
  "created_at": "2025-10-12T10:00:00Z"
}
```

---

### 2. Role (Authorization Domain)

Named collection of permissions. Supports both default roles and custom tenant-specific roles.

**Table**: `roles`

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PK, NOT NULL | Primary key (UUIDv7) |
| `tenant_id` | UUID | NULLABLE, FK → tenants.id | NULL for system roles |
| `name` | VARCHAR(100) | NOT NULL | Role name |
| `slug` | VARCHAR(100) | NOT NULL | URL-safe identifier |
| `description` | TEXT | NULLABLE | Role description |
| `is_system_role` | BOOLEAN | NOT NULL, DEFAULT FALSE | Cannot be modified/deleted |
| `is_default` | BOOLEAN | NOT NULL, DEFAULT FALSE | Auto-assigned to new users |
| `priority` | INTEGER | NOT NULL, DEFAULT 0 | Role priority for conflict resolution |
| `created_by` | UUID | NULLABLE, FK → users.id | Creator (NULL for system) |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Creation timestamp |
| `updated_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Last update |

**Indexes**:
```sql
CREATE INDEX idx_roles_tenant ON roles(tenant_id);
CREATE INDEX idx_roles_slug ON roles(slug);
```

**Unique Constraints**:
```sql
-- System roles have globally unique slugs, tenant roles unique per tenant
ALTER TABLE roles ADD CONSTRAINT unique_role_slug
    UNIQUE (COALESCE(tenant_id, '00000000-0000-0000-0000-000000000000'::uuid), slug);
```

**Default System Roles**:
```sql
-- Inserted during migration
INSERT INTO roles (id, tenant_id, name, slug, description, is_system_role, priority) VALUES
    ('018e0000-0000-0000-0000-000000000001', NULL, 'Super Admin', 'super-admin', 'Platform super administrator', TRUE, 1000),
    ('018e0000-0000-0000-0000-000000000002', NULL, 'Tenant Admin', 'tenant-admin', 'Tenant administrator', TRUE, 900),
    ('018e0000-0000-0000-0000-000000000003', NULL, 'Member', 'member', 'Regular tenant member', TRUE, 500),
    ('018e0000-0000-0000-0000-000000000004', NULL, 'Viewer', 'viewer', 'Read-only viewer', TRUE, 100);
```

**Many-to-Many**: User ↔ Role
```sql
CREATE TABLE user_roles (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    assigned_by UUID NOT NULL REFERENCES users(id),
    assigned_at TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, role_id)
);
CREATE INDEX idx_user_roles_user ON user_roles(user_id);
CREATE INDEX idx_user_roles_role ON user_roles(role_id);
```

---

### 3. Policy (Authorization Domain)

Tenant-level or user-level authorization rules with pattern matching.

**Table**: `policies`

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PK, NOT NULL | Primary key (UUIDv7) |
| `tenant_id` | UUID | NOT NULL, FK → tenants.id | Tenant isolation |
| `scope` | ENUM('tenant', 'user') | NOT NULL | Policy scope |
| `scope_id` | UUID | NULLABLE | User ID (if scope='user'), NULL for tenant |
| `name` | VARCHAR(100) | NOT NULL | Policy name |
| `description` | TEXT | NULLABLE | Policy description |
| `resource_pattern` | VARCHAR(100) | NOT NULL | Resource pattern (e.g., 'crew:*', 'flow:prod-*') |
| `action_pattern` | VARCHAR(50) | NOT NULL | Action pattern (e.g., 'read', '*') |
| `effect` | ENUM('allow', 'deny') | NOT NULL | Policy effect |
| `conditions` | JSONB | NULLABLE | ABAC conditions |
| `priority` | INTEGER | NOT NULL, DEFAULT 0 | Evaluation priority (higher = first) |
| `is_active` | BOOLEAN | NOT NULL, DEFAULT TRUE | Enable/disable policy |
| `created_by` | UUID | NOT NULL, FK → users.id | Creator |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Creation timestamp |
| `updated_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Last update |

**Indexes**:
```sql
CREATE INDEX idx_policies_tenant ON policies(tenant_id);
CREATE INDEX idx_policies_scope ON policies(scope, scope_id);
CREATE INDEX idx_policies_active ON policies(is_active);
```

**Pattern Matching**:
- `*` wildcard matches any string
- `:` separates resource type from resource ID
- Examples:
  - `crew:*` → All crews
  - `crew:prod-*` → Crews with ID prefix "prod-"
  - `*:*` → All resources (use sparingly!)

**Example**:
```json
{
  "id": "018e3333-3333-7333-3333-333333333333",
  "tenant_id": "018e0000-0000-7000-0000-000000000001",
  "scope": "tenant",
  "scope_id": null,
  "name": "All Members Can View Prompts",
  "description": "Tenant-wide policy allowing all members to view prompts",
  "resource_pattern": "prompt:*",
  "action_pattern": "read",
  "effect": "allow",
  "conditions": null,
  "priority": 100,
  "is_active": true,
  "created_by": "018e1111-1111-7111-1111-111111111111",
  "created_at": "2025-10-12T10:00:00Z"
}
```

---

### 4. AuthorizationAuditLog (Authorization Domain)

Records all authorization checks for compliance and debugging.

**Table**: `authorization_audit_logs`

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PK, NOT NULL | Primary key (UUIDv7) |
| `tenant_id` | UUID | NOT NULL, FK → tenants.id | Tenant isolation |
| `user_id` | UUID | NOT NULL, FK → users.id | User making request |
| `resource_type` | VARCHAR(50) | NOT NULL | Entity type |
| `resource_id` | UUID | NULLABLE | Specific resource (if applicable) |
| `action` | VARCHAR(50) | NOT NULL | Action attempted |
| `decision` | ENUM('allow', 'deny') | NOT NULL | Authorization decision |
| `reason` | TEXT | NOT NULL | Decision reason (e.g., "role:admin", "policy:deny-all") |
| `latency_ms` | INTEGER | NOT NULL | Check latency in milliseconds |
| `ip_address` | INET | NULLABLE | Request IP address |
| `user_agent` | TEXT | NULLABLE | Request user agent |
| `timestamp` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Check timestamp |

**Indexes**:
```sql
CREATE INDEX idx_authz_audit_tenant ON authorization_audit_logs(tenant_id);
CREATE INDEX idx_authz_audit_user ON authorization_audit_logs(user_id);
CREATE INDEX idx_authz_audit_timestamp ON authorization_audit_logs(timestamp DESC);
CREATE INDEX idx_authz_audit_decision ON authorization_audit_logs(decision);
```

**Partitioning** (PostgreSQL 11+):
```sql
-- Partition by month for efficient archival
CREATE TABLE authorization_audit_logs (
    -- ... fields
) PARTITION BY RANGE (timestamp);

CREATE TABLE authorization_audit_logs_2025_10 PARTITION OF authorization_audit_logs
    FOR VALUES FROM ('2025-10-01') TO ('2025-11-01');
-- Create new partitions monthly
```

**Retention Policy**:
- Keep 90 days by default (configurable per tenant)
- Archive to cold storage (e.g., S3) after retention period
- Delete archived logs after 1 year (compliance requirement)

---

### 5. ExecutionQueue (Execution Domain)

Tracks queued execution requests with metadata for Celery task management.

**Table**: `execution_queue`

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PK, NOT NULL | Primary key (UUIDv7) |
| `execution_id` | UUID | NOT NULL, FK → executions.id | Reference to execution |
| `tenant_id` | UUID | NOT NULL, FK → tenants.id | Tenant isolation |
| `user_id` | UUID | NOT NULL, FK → users.id | User who submitted |
| `execution_type` | ENUM('crew', 'flow', 'agent', 'task', 'tool') | NOT NULL | Type of execution |
| `priority` | ENUM('low', 'normal', 'high') | NOT NULL, DEFAULT 'normal' | Queue priority |
| `status` | ENUM('pending', 'running', 'completed', 'failed', 'timeout', 'cancelled') | NOT NULL, DEFAULT 'pending' | Execution status |
| `celery_task_id` | VARCHAR(255) | NULLABLE | Celery task ID (UUID format) |
| `retry_count` | INTEGER | NOT NULL, DEFAULT 0 | Number of retries attempted |
| `max_retries` | INTEGER | NOT NULL, DEFAULT 3 | Maximum retry attempts |
| `scheduled_at` | TIMESTAMP | NOT NULL | When task should run |
| `started_at` | TIMESTAMP | NULLABLE | When task started processing |
| `completed_at` | TIMESTAMP | NULLABLE | When task completed |
| `timeout_at` | TIMESTAMP | NULLABLE | When task times out |
| `payload` | JSONB | NOT NULL | Execution parameters |
| `result` | JSONB | NULLABLE | Execution result (if completed) |
| `error` | TEXT | NULLABLE | Error message (if failed) |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Queue entry creation |
| `updated_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Last update |

**Indexes**:
```sql
CREATE INDEX idx_exec_queue_tenant ON execution_queue(tenant_id);
CREATE INDEX idx_exec_queue_user ON execution_queue(user_id);
CREATE INDEX idx_exec_queue_status ON execution_queue(status);
CREATE INDEX idx_exec_queue_priority ON execution_queue(priority, scheduled_at);
CREATE INDEX idx_exec_queue_celery_task ON execution_queue(celery_task_id);
```

**Status Transitions**:
```
pending → running → completed
                 → failed (retry) → running → completed
                                          → failed (DLQ)
                 → timeout
                 → cancelled
```

**Example**:
```json
{
  "id": "018e4444-4444-7444-4444-444444444444",
  "execution_id": "018e5555-5555-7555-5555-555555555555",
  "tenant_id": "018e0000-0000-7000-0000-000000000001",
  "user_id": "018e1111-1111-7111-1111-111111111111",
  "execution_type": "crew",
  "priority": "normal",
  "status": "pending",
  "celery_task_id": "018e6666-6666-7666-6666-666666666666",
  "retry_count": 0,
  "max_retries": 3,
  "scheduled_at": "2025-10-12T10:05:00Z",
  "timeout_at": "2025-10-12T10:35:00Z",
  "payload": {
    "crew_id": "018e7777-7777-7777-7777-777777777777",
    "input_data": {"query": "Analyze Q3 sales"}
  },
  "created_at": "2025-10-12T10:04:50Z"
}
```

---

### 6. DeadLetterTask (Execution Domain)

Stores failed executions after retry exhaustion for admin review and requeuing.

**Table**: `dead_letter_tasks`

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PK, NOT NULL | Primary key (UUIDv7) |
| `original_queue_id` | UUID | NOT NULL, FK → execution_queue.id | Original queue entry |
| `tenant_id` | UUID | NOT NULL, FK → tenants.id | Tenant isolation |
| `user_id` | UUID | NOT NULL, FK → users.id | Original submitter |
| `execution_type` | ENUM | NOT NULL | Type of execution |
| `payload` | JSONB | NOT NULL | Original execution payload |
| `failure_reason` | TEXT | NOT NULL | Final failure reason |
| `retry_history` | JSONB | NOT NULL | Array of retry attempts with errors |
| `failure_timestamp` | TIMESTAMP | NOT NULL | When moved to DLQ |
| `is_requeued` | BOOLEAN | NOT NULL, DEFAULT FALSE | Whether task was requeued |
| `requeued_at` | TIMESTAMP | NULLABLE | When task was requeued |
| `requeued_by` | UUID | NULLABLE, FK → users.id | Admin who requeued |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | DLQ entry creation |

**Indexes**:
```sql
CREATE INDEX idx_dlq_tenant ON dead_letter_tasks(tenant_id);
CREATE INDEX idx_dlq_user ON dead_letter_tasks(user_id);
CREATE INDEX idx_dlq_requeued ON dead_letter_tasks(is_requeued);
CREATE INDEX idx_dlq_failure_timestamp ON dead_letter_tasks(failure_timestamp DESC);
```

**retry_history Format**:
```json
{
  "retry_history": [
    {
      "attempt": 1,
      "timestamp": "2025-10-12T10:05:30Z",
      "error": "ConnectionError: Failed to connect to LLM provider",
      "duration_ms": 5234
    },
    {
      "attempt": 2,
      "timestamp": "2025-10-12T10:05:34Z",
      "error": "ConnectionError: Failed to connect to LLM provider",
      "duration_ms": 4123
    },
    {
      "attempt": 3,
      "timestamp": "2025-10-12T10:05:42Z",
      "error": "ConnectionError: Failed to connect to LLM provider",
      "duration_ms": 5891
    }
  ]
}
```

---

### 7. ExecutionMetrics (Execution Domain)

Aggregated metrics for queue monitoring and capacity planning.

**Table**: `execution_metrics`

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PK, NOT NULL | Primary key (UUIDv7) |
| `tenant_id` | UUID | NULLABLE, FK → tenants.id | NULL for global metrics |
| `timestamp` | TIMESTAMP | NOT NULL | Metric timestamp (rounded to minute) |
| `queue_depth` | INTEGER | NOT NULL | Tasks in queue (pending + running) |
| `pending_count` | INTEGER | NOT NULL | Tasks pending |
| `running_count` | INTEGER | NOT NULL | Tasks running |
| `completed_count` | INTEGER | NOT NULL | Tasks completed in this minute |
| `failed_count` | INTEGER | NOT NULL | Tasks failed in this minute |
| `timeout_count` | INTEGER | NOT NULL | Tasks timed out in this minute |
| `processing_rate` | FLOAT | NOT NULL | Tasks/second |
| `avg_duration_ms` | INTEGER | NOT NULL | Average execution duration |
| `p95_duration_ms` | INTEGER | NOT NULL | 95th percentile duration |
| `p99_duration_ms` | INTEGER | NOT NULL | 99th percentile duration |
| `failure_rate` | FLOAT | NOT NULL | Percentage of failed tasks |

**Indexes**:
```sql
CREATE INDEX idx_exec_metrics_tenant ON execution_metrics(tenant_id);
CREATE INDEX idx_exec_metrics_timestamp ON execution_metrics(timestamp DESC);
```

**Time Series** (PostgreSQL with TimescaleDB extension):
```sql
-- Convert to hypertable for efficient time-series queries
SELECT create_hypertable('execution_metrics', 'timestamp', chunk_time_interval => INTERVAL '1 day');

-- Retention policy: Keep 30 days
SELECT add_retention_policy('execution_metrics', INTERVAL '30 days');
```

**Aggregation Job** (runs every minute):
```python
# backend/src/services/metrics_aggregator.py
@celery.task(bind=True)
def aggregate_execution_metrics(self):
    # Calculate metrics for last minute
    now = datetime.utcnow()
    minute_ago = now - timedelta(minutes=1)

    for tenant in tenants:
        metrics = calculate_metrics(tenant_id, minute_ago, now)
        ExecutionMetrics.create(tenant_id=tenant.id, timestamp=now, **metrics)
```

---

### 8. Notification (Notification Domain)

Persistent notification records delivered via WebSocket and stored for offline users.

**Table**: `notifications`

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PK, NOT NULL | Primary key (UUIDv7) |
| `tenant_id` | UUID | NOT NULL, FK → tenants.id | Tenant isolation |
| `user_id` | UUID | NOT NULL, FK → users.id | Recipient user |
| `category` | ENUM('execution_started', 'execution_completed', 'execution_failed', 'execution_timeout', 'invitation_received', 'team_mention', 'system_alert') | NOT NULL | Notification type |
| `priority` | ENUM('low', 'normal', 'high', 'critical') | NOT NULL, DEFAULT 'normal' | Notification priority |
| `title` | VARCHAR(255) | NOT NULL | Notification title |
| `message` | TEXT | NOT NULL | Notification message |
| `resource_type` | VARCHAR(50) | NULLABLE | Related resource type |
| `resource_id` | UUID | NULLABLE | Related resource ID |
| `resource_link` | VARCHAR(500) | NULLABLE | Deep link to resource (e.g., `/crews/{id}`) |
| `metadata` | JSONB | NULLABLE | Additional data (e.g., execution stats) |
| `read_status` | BOOLEAN | NOT NULL, DEFAULT FALSE | Whether notification has been read |
| `read_at` | TIMESTAMP | NULLABLE | When notification was read |
| `delivered_via_websocket` | BOOLEAN | NOT NULL, DEFAULT FALSE | Whether delivered via WebSocket |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Notification creation |

**Indexes**:
```sql
CREATE INDEX idx_notifications_user ON notifications(user_id);
CREATE INDEX idx_notifications_tenant ON notifications(tenant_id);
CREATE INDEX idx_notifications_read_status ON notifications(user_id, read_status);
CREATE INDEX idx_notifications_created_at ON notifications(created_at DESC);
CREATE INDEX idx_notifications_category ON notifications(category);
```

**Retention Policy**:
- Default: 90 days (configurable per tenant)
- Cleanup job runs daily, deletes notifications older than retention period

**Example**:
```json
{
  "id": "018e8888-8888-7888-8888-888888888888",
  "tenant_id": "018e0000-0000-7000-0000-000000000001",
  "user_id": "018e1111-1111-7111-1111-111111111111",
  "category": "execution_completed",
  "priority": "normal",
  "title": "Crew Execution Completed",
  "message": "Your crew 'Marketing Team' has completed successfully",
  "resource_type": "execution",
  "resource_id": "018e5555-5555-7555-5555-555555555555",
  "resource_link": "/executions/018e5555-5555-7555-5555-555555555555",
  "metadata": {
    "crew_name": "Marketing Team",
    "duration_seconds": 45,
    "output_summary": "Generated 3 blog posts"
  },
  "read_status": false,
  "delivered_via_websocket": true,
  "created_at": "2025-10-12T10:10:00Z"
}
```

---

### 9. NotificationPreference (Notification Domain)

User and tenant-level notification preferences for category-based filtering.

**Table**: `notification_preferences`

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PK, NOT NULL | Primary key (UUIDv7) |
| `scope` | ENUM('tenant', 'user') | NOT NULL | Preference scope |
| `scope_id` | UUID | NOT NULL | Tenant ID or User ID |
| `category` | ENUM('execution_started', ...) | NOT NULL | Notification category |
| `enabled` | BOOLEAN | NOT NULL, DEFAULT TRUE | Whether category is enabled |
| `delivery_channels` | VARCHAR(50)[] | NOT NULL, DEFAULT ARRAY['websocket'] | Delivery channels (currently only websocket) |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Preference creation |
| `updated_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Last update |

**Indexes**:
```sql
CREATE INDEX idx_notif_pref_scope ON notification_preferences(scope, scope_id);
CREATE INDEX idx_notif_pref_category ON notification_preferences(category);
```

**Unique Constraints**:
```sql
ALTER TABLE notification_preferences ADD CONSTRAINT unique_preference
    UNIQUE (scope, scope_id, category);
```

**Evaluation Logic**:
```python
def should_send_notification(user_id, tenant_id, category):
    # 1. Check user preference (highest priority)
    user_pref = get_preference(scope='user', scope_id=user_id, category=category)
    if user_pref and not user_pref.enabled:
        return False  # User disabled, don't send

    # 2. Check tenant preference
    tenant_pref = get_preference(scope='tenant', scope_id=tenant_id, category=category)
    if tenant_pref and not tenant_pref.enabled:
        return False  # Tenant disabled, don't send

    # 3. Default: send notification
    return True
```

---

### 10. TenantRegistration (Tenant Domain)

Tracks tenant registration requests pending super admin approval.

**Table**: `tenant_registrations`

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PK, NOT NULL | Primary key (UUIDv7) |
| `company_name` | VARCHAR(255) | NOT NULL | Company/organization name |
| `admin_email` | VARCHAR(255) | NOT NULL, UNIQUE | Admin email address |
| `admin_name` | VARCHAR(255) | NOT NULL | Admin full name |
| `reason` | TEXT | NOT NULL | Reason for registration |
| `sample_data_requested` | BOOLEAN | NOT NULL, DEFAULT FALSE | Whether to load sample data |
| `status` | ENUM('pending', 'approved', 'rejected') | NOT NULL, DEFAULT 'pending' | Registration status |
| `rejection_reason` | TEXT | NULLABLE | Reason for rejection (required if rejected) |
| `approved_by` | UUID | NULLABLE, FK → users.id | Super admin who approved |
| `approved_at` | TIMESTAMP | NULLABLE | Approval timestamp |
| `tenant_id` | UUID | NULLABLE, FK → tenants.id | Created tenant (after approval) |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Registration submission |
| `updated_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Last status update |

**Indexes**:
```sql
CREATE INDEX idx_tenant_reg_status ON tenant_registrations(status);
CREATE INDEX idx_tenant_reg_email ON tenant_registrations(admin_email);
CREATE INDEX idx_tenant_reg_created_at ON tenant_registrations(created_at DESC);
```

**Validation Rules**:
- `admin_email` must be valid email format
- `rejection_reason` required if status='rejected'
- `approved_by` required if status='approved'
- `tenant_id` populated only after approval

**Example**:
```json
{
  "id": "018e9999-9999-7999-9999-999999999999",
  "company_name": "Acme Corporation",
  "admin_email": "admin@acme.com",
  "admin_name": "Jane Doe",
  "reason": "We want to use CrewAI for automating our marketing workflows",
  "sample_data_requested": true,
  "status": "pending",
  "rejection_reason": null,
  "approved_by": null,
  "approved_at": null,
  "tenant_id": null,
  "created_at": "2025-10-12T09:00:00Z"
}
```

---

### 11. User Extension: Super Admin

The `users` table will be extended with a super admin flag.

**Migration**: Add column to existing `users` table
```sql
ALTER TABLE users ADD COLUMN is_super_admin BOOLEAN NOT NULL DEFAULT FALSE;
CREATE INDEX idx_users_super_admin ON users(is_super_admin) WHERE is_super_admin = TRUE;
```

**Super Admin Privileges**:
- Access to all tenants (bypass tenant_id checks)
- Approve/reject tenant registrations
- View system-wide metrics
- Manage default roles
- Access authorization audit logs across all tenants

**Seed Super Admin**:
```sql
-- Create platform super admin during migration
INSERT INTO users (id, tenant_id, email, password_hash, full_name, role, is_active, is_super_admin)
VALUES (
    '018e0000-0000-0000-0001-000000000000',
    NULL,  -- No tenant affiliation
    'superadmin@platform.local',
    '<bcrypt-hash>',
    'Platform Super Administrator',
    'super_admin',
    TRUE,
    TRUE
);
```

---

## Part 2: UUID Migration for Existing Entities

All existing entities will have their `id` column migrated from `Integer` to `UUID` (UUIDv7).

### Entities to Migrate

| Table | Current ID Type | New ID Type | Relationships |
|-------|----------------|-------------|---------------|
| `users` | Integer | UUID | → tenant_id, many chat_sessions, executions |
| `tenants` | Integer | UUID | ← many users, agents, crews, flows |
| `agents` | Integer | UUID | → llm_provider_id, tenant_id, ↔ tools, crews |
| `crews` | Integer | UUID | → tenant_id, ↔ agents, tasks |
| `tasks` | Integer | UUID | → crew_id, agent_id, tenant_id |
| `flows` | Integer | UUID | → tenant_id, many nodes |
| `executions` | Integer | UUID | → flow_id, crew_id, agent_id, tool_id, task_id, user_id |
| `prompts` (prompt_templates) | Integer | UUID | → category_id, tenant_id |
| `prompt_categories` | Integer | UUID | → tenant_id |
| `prompt_executions` | Integer | UUID | → prompt_id, user_id |
| `prompt_ratings` | Integer | UUID | → prompt_id, user_id |
| `prompt_feedback` | Integer | UUID | → prompt_id, user_id |
| `prompt_favorites` | Integer | UUID | → prompt_id, user_id |
| `prompt_versions` | Integer | UUID | → prompt_id |
| `chat_sessions` | Integer | UUID | → user_id, folder_id |
| `chat_folders` | Integer | UUID | → user_id |
| `llm_providers` | Integer | UUID | → tenant_id |
| `provider_versions` | Integer | UUID | → provider_id |
| `agent_versions` | Integer | UUID | → agent_id |
| `tools` | Integer | UUID | → tenant_id, ↔ agents |
| `feedback` | Integer | UUID | → execution_id, user_id |
| `notifications` (existing) | Integer | UUID | → user_id |

### Migration Script Structure

```sql
-- alembic/versions/YYYYMMDD_uuid_migration.py
"""Migrate all entity IDs from Integer to UUID

Revision ID: uuid_migration_001
Revises: <previous_revision>
Create Date: 2025-10-12

"""

def upgrade():
    # Enable UUID extension
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # Step 1: Add UUID columns
    tables = ['users', 'tenants', 'agents', 'crews', ...] # All 20+ tables
    for table in tables:
        op.add_column(table, sa.Column('uuid', postgresql.UUID(as_uuid=True), nullable=True))

    # Step 2: Generate UUIDs (UUIDv7-like: time-ordered)
    # Use uuid_generate_v4() as placeholder (ideally uuid_v7() with extension)
    for table in tables:
        op.execute(f"UPDATE {table} SET uuid = uuid_generate_v4()")

    # Step 3: Create temporary mapping tables
    for table in tables:
        op.execute(f"""
            CREATE TEMP TABLE {table}_id_map AS
            SELECT id AS old_id, uuid AS new_uuid FROM {table}
        """)

    # Step 4: Add UUID foreign key columns
    op.add_column('agents', sa.Column('llm_provider_uuid', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('agents', sa.Column('tenant_uuid', postgresql.UUID(as_uuid=True), nullable=True))
    # ... for all 50+ foreign key columns

    # Step 5: Populate UUID foreign keys using mapping tables
    op.execute("""
        UPDATE agents a
        SET tenant_uuid = m.new_uuid
        FROM tenants_id_map m
        WHERE a.tenant_id = m.old_id
    """)
    # ... for all foreign keys

    # Step 6: Drop old integer columns and constraints
    op.drop_constraint('agents_llm_provider_id_fkey', 'agents')
    op.drop_column('agents', 'llm_provider_id')
    # ... for all foreign keys

    # Step 7: Rename UUID columns to remove '_uuid' suffix
    op.alter_column('users', 'uuid', new_column_name='id')
    op.alter_column('agents', 'llm_provider_uuid', new_column_name='llm_provider_id')
    # ... for all columns

    # Step 8: Set NOT NULL constraints
    for table in tables:
        op.alter_column(table, 'id', nullable=False)
    # ... for foreign keys

    # Step 9: Create primary key constraints
    for table in tables:
        op.create_primary_key(f'{table}_pkey', table, ['id'])

    # Step 10: Recreate foreign key constraints
    op.create_foreign_key('agents_llm_provider_id_fkey', 'agents', 'llm_providers', ['llm_provider_id'], ['id'])
    # ... for all 50+ foreign keys

    # Step 11: Recreate indexes
    op.create_index('idx_agents_tenant', 'agents', ['tenant_id'])
    # ... for all indexes

    # Step 12: Update sequences (if any auto-increment columns remain)
    # N/A - UUIDs don't use sequences

def downgrade():
    raise NotImplementedError("UUID migration downgrade not supported due to data loss risk")
```

### Migration Testing Checklist

- [ ] Backup production database
- [ ] Run migration on staging with production data snapshot
- [ ] Verify all IDs converted (no NULL UUIDs)
- [ ] Verify all foreign key relationships preserved
- [ ] Run full API test suite
- [ ] Benchmark query performance (should be similar)
- [ ] Test rollback procedure (restore from backup)
- [ ] Document migration timeline (estimated 10-30 minutes for 100k records)

---

## Part 3: Validation Rules Summary

### Cross-Entity Validation

| Rule | Description | Enforcement |
|------|-------------|-------------|
| **Tenant Isolation** | All resources must belong to same tenant | Application + DB CHECK constraint |
| **Authorization** | Users can only access resources they have permission for | Middleware (AuthorizationService) |
| **Rate Limiting** | Tenants/users cannot exceed configured execution limits | Pre-queue check (ExecutionService) |
| **Foreign Key Integrity** | All FKs must reference existing UUIDs | PostgreSQL FOREIGN KEY constraint |
| **UUID Format** | All UUIDs must be valid UUIDv7 format | PostgreSQL UUID type validation |
| **Enum Values** | Enums must be from allowed set | PostgreSQL ENUM type |
| **Notification Categories** | Categories must match NotificationPreference categories | Application validation |

---

## Part 4: Sample Data

See `backend/src/scripts/seed_sample_data.py` for full implementation. Summary:

- **3 Sample Crews**: Marketing, Data Analysis, Customer Support
- **5 Sample Flows**: Blog Post, Data Pipeline, Customer Inquiry, Code Review, Marketing Campaign
- **10 Sample Prompts**: Various task-specific prompts with variables
- **5 Sample Tools**: Web Search, SQL Query, File Upload, API Call, Calculator
- **10 Sample Executions**: Historical execution records with mixed success/failure

---

## Part 5: Performance Considerations

### Indexing Strategy

**Priority 1 (Critical Path)**:
- Authorization checks: `(subject_type, subject_id)`, `(resource_type, resource_id)`
- Queue operations: `(status)`, `(priority, scheduled_at)`, `(celery_task_id)`
- Notifications: `(user_id, read_status)`, `(created_at DESC)`

**Priority 2 (Analytics)**:
- Audit logs: `(tenant_id)`, `(timestamp DESC)`, `(decision)`
- Execution metrics: `(tenant_id)`, `(timestamp DESC)`

**Priority 3 (Admin)**:
- Tenant registrations: `(status)`, `(created_at DESC)`
- Dead letter tasks: `(tenant_id)`, `(is_requeued)`

### Query Optimization

**Authorization Checks** (<50ms requirement):
```sql
-- Cached result for 5 minutes, cache key: authz:{user_id}:{resource_type}:{resource_id}:{action}

-- If cache miss, run:
WITH user_permissions AS (
    SELECT effect FROM permissions
    WHERE subject_type = 'user' AND subject_id = $1
      AND resource_type = $2 AND (resource_id = $3 OR resource_id IS NULL)
      AND action IN ($4, '*')
),
role_permissions AS (
    SELECT p.effect FROM permissions p
    JOIN user_roles ur ON p.subject_id = ur.role_id
    WHERE p.subject_type = 'role' AND ur.user_id = $1
      AND p.resource_type = $2 AND (p.resource_id = $3 OR p.resource_id IS NULL)
      AND p.action IN ($4, '*')
),
policies AS (
    SELECT effect, priority FROM policies
    WHERE tenant_id = $5
      AND ((scope = 'user' AND scope_id = $1) OR (scope = 'tenant' AND scope_id IS NULL))
      AND $2 ~ resource_pattern AND $4 ~ action_pattern
      AND is_active = TRUE
    ORDER BY priority DESC
)
SELECT effect FROM (
    SELECT effect, 1000 AS priority FROM user_permissions
    UNION ALL
    SELECT effect, 900 AS priority FROM role_permissions
    UNION ALL
    SELECT effect, priority FROM policies
) combined
ORDER BY priority DESC, CASE WHEN effect = 'deny' THEN 0 ELSE 1 END
LIMIT 1;
```

**Queue Depth** (for metrics):
```sql
-- Efficient COUNT with partial index
SELECT COUNT(*) FROM execution_queue
WHERE status IN ('pending', 'running') AND tenant_id = $1;

-- Index: CREATE INDEX idx_exec_queue_active ON execution_queue(tenant_id, status) WHERE status IN ('pending', 'running');
```

---

## Part 6: Schema Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Authorization Domain                            │
├─────────────┬─────────────┬──────────────┬─────────────────────────────┤
│ permissions │    roles    │   policies   │ authorization_audit_logs    │
│             │             │              │                             │
│ • id (PK)   │ • id (PK)   │ • id (PK)    │ • id (PK)                   │
│ • tenant_id │ • tenant_id │ • tenant_id  │ • tenant_id                 │
│ • subject_* │ • name      │ • scope      │ • user_id                   │
│ • resource_*│ • slug      │ • scope_id   │ • resource_*                │
│ • action    │ • is_system │ • resource_* │ • action                    │
│ • effect    │             │ • action_*   │ • decision                  │
│ • conditions│ user_roles  │ • effect     │ • reason                    │
│             │ (M2M)       │ • priority   │ • latency_ms                │
└─────────────┴─────────────┴──────────────┴─────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                           Execution Domain                               │
├──────────────────┬─────────────────────┬───────────────────────────────┤
│ execution_queue  │ dead_letter_tasks   │  execution_metrics            │
│                  │                     │                               │
│ • id (PK)        │ • id (PK)           │ • id (PK)                     │
│ • execution_id   │ • original_queue_id │ • tenant_id                   │
│ • tenant_id      │ • tenant_id         │ • timestamp                   │
│ • user_id        │ • user_id           │ • queue_depth                 │
│ • execution_type │ • payload           │ • pending_count               │
│ • priority       │ • failure_reason    │ • running_count               │
│ • status         │ • retry_history     │ • completed_count             │
│ • celery_task_id │ • is_requeued       │ • processing_rate             │
│ • retry_count    │ • requeued_by       │ • avg_duration_ms             │
│ • payload        │                     │ • failure_rate                │
└──────────────────┴─────────────────────┴───────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                         Notification Domain                              │
├────────────────────────────┬────────────────────────────────────────────┤
│      notifications         │     notification_preferences               │
│                            │                                            │
│ • id (PK)                  │ • id (PK)                                  │
│ • tenant_id                │ • scope (tenant/user)                      │
│ • user_id                  │ • scope_id                                 │
│ • category                 │ • category                                 │
│ • priority                 │ • enabled                                  │
│ • title                    │ • delivery_channels                        │
│ • message                  │                                            │
│ • resource_link            │                                            │
│ • read_status              │                                            │
│ • delivered_via_websocket  │                                            │
└────────────────────────────┴────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                           Tenant Domain                                  │
├────────────────────────────┬────────────────────────────────────────────┤
│   tenant_registrations     │          users (extended)                  │
│                            │                                            │
│ • id (PK)                  │ • id (PK) [UUID]                           │
│ • company_name             │ • tenant_id                                │
│ • admin_email              │ • is_super_admin [NEW]                     │
│ • admin_name               │ • email                                    │
│ • reason                   │ • role                                     │
│ • sample_data_requested    │ • ...                                      │
│ • status                   │                                            │
│ • rejection_reason         │                                            │
│ • approved_by              │                                            │
│ • tenant_id (after approval)│                                           │
└────────────────────────────┴────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                    Existing Entities (UUID Migration)                    │
├─────────────┬─────────────┬─────────────┬──────────────────────────────┤
│ • users     │ • agents    │ • flows     │ • prompts                    │
│ • tenants   │ • crews     │ • executions│ • chat_sessions              │
│ • tasks     │ • tools     │ • llm_*     │ • feedback                   │
│             │             │             │                              │
│             ALL MIGRATED TO UUID PRIMARY KEYS                          │
└─────────────┴─────────────┴─────────────┴──────────────────────────────┘
```

---

## Summary

This data model introduces **11 new entities** and **migrates 20+ existing entities** to UUID, providing:
- Fine-grained authorization with hybrid RBAC+ABAC
- Robust async execution queue with retry and DLQ
- Real-time notification system with persistence
- Tenant management with admin approval
- Comprehensive audit logging and metrics
- Security through non-guessable UUIDs

The model is designed for performance (<50ms authz, <200ms queue), scalability (horizontal workers), and observability (audit logs, metrics, Prometheus).

---
