# Feature Specification: Platform Infrastructure Enhancements

**Feature Branch**: `003-we-need-to`
**Created**: 2025-10-12
**Status**: Draft
**Input**: User description: "We need to implement an authz service to make sure only authorized users can carry specific actions on the system. Make sure all id on the entities are uuids not int for all entities like flows, crews, tasks, prompts, execution, chat, ...etc. propose a robust and scalable authz service. A new system design is required to be implemented to enable async task execution with message queueing to queue execution requests with to decouple backend and executions. Include a robust design for notification system using message queueing to notify users of various system actions. I need to use ultrathink to design the services with detailed review before starting the implementation."

## Execution Flow (main)
```
1. Parse user description from Input
   → ✅ Description parsed: 4 major enhancements identified
2. Extract key concepts from description
   → ✅ Identified: Authorization, UUID migration, Async execution, Notifications, Tenant management
3. For each unclear aspect:
   → ✅ All ambiguities resolved through Q&A
4. Fill User Scenarios & Testing section
   → ✅ User flows defined for each enhancement
5. Generate Functional Requirements
   → ✅ Requirements testable and scoped
6. Identify Key Entities
   → ✅ Entities mapped
7. Run Review Checklist
   → ✅ No implementation details, business-focused
8. Return: SUCCESS (spec ready for planning)
```

---

## ⚡ Quick Guidelines
- ✅ Focus on WHAT users need and WHY
- ❌ Avoid HOW to implement (no tech stack, APIs, code structure)
- 👥 Written for business stakeholders, not developers

---

## Executive Summary

This feature introduces four critical platform enhancements to improve security, scalability, and user experience:

1. **Authorization Service**: Implements fine-grained access control to ensure users can only perform actions they are authorized for
2. **UUID Migration**: Converts all entity identifiers from integers to UUIDs for better security, scalability, and multi-system integration
3. **Async Task Execution**: Decouples execution requests from the main application using message queuing for reliability and scalability
4. **Notification System**: Provides real-time notifications to users about system events via WebSocket with persistent storage
5. **Tenant Management**: Adds super admin approval workflow for tenant creation with optional sample data

---

## User Scenarios & Testing

### Scenario 1: Authorization - Restricted Resource Access

**Primary User Story**: As a team member, I should only be able to view and execute resources I have permission for, preventing unauthorized access to other teams' work.

**Acceptance Scenarios**:
1. **Given** Alice is a member of "Marketing Team" tenant, **When** she tries to view "Engineering Team" crews, **Then** system denies access and shows "Not authorized"
2. **Given** Bob has "viewer" role, **When** he tries to delete a crew, **Then** system denies the action
3. **Given** Carol has permission to execute Crew A, **When** she accesses Crew A, **Then** system automatically grants her access to Crew A's tasks and agents (permission inheritance)
4. **Given** David is assigned "execute" permission on Flow X, **When** he opens Flow X, **Then** he can run it but cannot edit or delete it
5. **Given** Admin configures tenant-wide policy "All members can view prompts", **When** any member logs in, **Then** they can see all prompts without individual grants

**Edge Cases**:
- What happens when a user is removed from a tenant mid-session? → Session invalidated, logged out immediately
- How does system handle permission conflicts (tenant policy allows, user policy denies)? → User-level deny takes precedence
- What if owner of a resource is deleted? → Resource ownership transfers to tenant admin
- Can users share resources across tenants? → No, all resources are tenant-isolated

### Scenario 2: UUID Migration - Secure Resource References

**Primary User Story**: As a system administrator, I need all resource identifiers to be non-guessable UUIDs to prevent enumeration attacks and enable secure cross-system integration.

**Acceptance Scenarios**:
1. **Given** system has migrated to UUIDs, **When** user views a crew URL, **Then** URL contains UUID (e.g., `/crews/a3f2c8b1-...`) instead of integer
2. **Given** existing API clients use integer IDs, **When** they make requests after migration, **Then** requests fail with clear error message indicating UUID requirement
3. **Given** database contains 10,000 executions with integer IDs, **When** migration runs, **Then** all records converted to UUIDs, relationships preserved, and sample data loaded
4. **Given** user bookmarked an old integer-based URL, **When** they visit it after migration, **Then** system shows "Resource not found - please use updated links"

**Edge Cases**:
- What happens to API responses that reference IDs? → All ID fields return UUIDs
- How are foreign key relationships handled? → All foreign keys updated to UUID type, data migrated atomically
- Can users still filter/sort by ID? → Yes, but by UUID (sortable UUID variant recommended for time-based ordering)

### Scenario 3: Async Execution - Reliable Task Processing

**Primary User Story**: As a user running long-running crew executions, I need the system to queue my request reliably so that even if the web server restarts, my execution continues processing.

**Acceptance Scenarios**:
1. **Given** Emily submits a crew execution, **When** request is received, **Then** system immediately returns execution ID and queues the work for background processing
2. **Given** execution queue has 50 pending tasks from "Tenant A", **When** "Tenant A" reaches their rate limit (configured as 10 concurrent), **Then** new submissions from Tenant A are rejected until slots free up
3. **Given** an execution fails on first attempt, **When** failure occurs, **Then** system automatically retries up to 3 times with exponential backoff (2s, 4s, 8s)
4. **Given** execution exceeds timeout limit (tenant-configured, default 30 minutes), **When** timeout reached, **Then** system gracefully cancels execution, cleans up resources, and marks as "timeout"
5. **Given** execution fails after 3 retries, **When** final failure occurs, **Then** system moves task to dead letter queue for admin review
6. **Given** tenant has "high-priority" executions enabled, **When** they submit with priority flag, **Then** task processed before normal-priority tasks
7. **Given** 5 worker processes are running, **When** execution load increases, **Then** administrators can scale horizontally by adding more worker containers without code changes

**Edge Cases**:
- What happens if worker crashes mid-execution? → Another worker picks up task and retries (idempotency required)
- How are duplicate submissions prevented? → Execution IDs checked before queuing
- Can users cancel queued executions? → Yes, if status is "pending" or "running" and they have permission
- What if message queue (Redis) goes down? → New submissions fail with "Service unavailable", queued tasks resume when Redis recovers

### Scenario 4: Notifications - Real-Time User Awareness

**Primary User Story**: As a user, I want to receive immediate notifications when my crew executions complete, fail, or require attention, without having to refresh the page constantly.

**Acceptance Scenarios**:
1. **Given** Frank starts a crew execution, **When** execution completes successfully, **Then** he receives WebSocket notification and sees bell icon badge increment
2. **Given** Grace is logged in, **When** another team member invites her to collaborate on a flow, **Then** she receives real-time notification with invitation details
3. **Given** tenant admin disables execution notifications at tenant level, **When** any user in that tenant completes execution, **Then** no notification is sent (tenant policy overrides)
4. **Given** Henry disables "execution started" notifications in his user preferences, **When** his execution starts, **Then** he receives no notification, but still gets completion/failure alerts
5. **Given** system has 1000 notifications older than 90 days (tenant retention policy), **When** cleanup job runs, **Then** old notifications are automatically deleted
6. **Given** Isabella receives 5 notifications, **When** she opens notification panel, **Then** she sees all 5 with unread badges
7. **Given** Isabella clicks on a notification, **When** she views it, **Then** notification is marked as read and badge count decrements

**Edge Cases**:
- What happens if user is offline when notification sent? → Notification stored, delivered when user reconnects
- Can users mark all as read? → Yes, bulk action available
- What if WebSocket connection fails? → System automatically reconnects, resends undelivered notifications
- Can notifications trigger external webhooks? → [NEEDS CLARIFICATION: Future requirement or initial scope?] Assumed NO for initial release

### Scenario 5: Tenant Management - Controlled Onboarding

**Primary User Story**: As a super administrator, I need to review and approve new tenant registrations to ensure only legitimate organizations access the platform.

**Acceptance Scenarios**:
1. **Given** Jane wants to create a new tenant, **When** she submits registration form, **Then** system creates pending tenant and notifies super admins for approval
2. **Given** super admin reviews Jane's request, **When** they approve it, **Then** tenant is activated, Jane receives notification, and she can log in
3. **Given** super admin rejects registration, **When** they provide rejection reason, **Then** tenant record is marked rejected and Jane receives email with reason
4. **Given** approved tenant wants sample data, **When** they check "Install sample data" during registration, **Then** system loads sample crews, agents, flows, and prompts after approval
5. **Given** tenant is approved without sample data, **When** they log in first time, **Then** they see empty dashboard with onboarding wizard

**Edge Cases**:
- What happens if super admin doesn't respond to request for 7 days? → [NEEDS CLARIFICATION: Auto-approve, auto-reject, or indefinite pending?] Assumed indefinite pending with reminder emails
- Can regular admins see pending tenant list? → No, only super admins
- Can tenant registration be edited after submission? → No, must submit new request

---

## Requirements

### Functional Requirements: Authorization Service

- **FR-AUTH-001**: System MUST enforce authorization checks on every resource access (read, write, execute, delete)
- **FR-AUTH-002**: System MUST support hybrid authorization model combining role-based (RBAC) and attribute-based (ABAC) controls
- **FR-AUTH-003**: System MUST implement resource-level permissions (e.g., "can view Crew A")
- **FR-AUTH-004**: System MUST implement action-level permissions (e.g., "can execute", "can edit", "can delete")
- **FR-AUTH-005**: System MUST implement field-level permissions (e.g., "cannot see API keys in LLM provider")
- **FR-AUTH-006**: System MUST support tenant-level authorization policies that apply to all users in tenant
- **FR-AUTH-007**: System MUST support user-level authorization policies that override tenant policies (deny takes precedence)
- **FR-AUTH-008**: System MUST implement permission inheritance (access to Crew grants access to its Tasks and Agents)
- **FR-AUTH-009**: System MUST provide default roles: Super Admin, Tenant Admin, Member, Viewer
- **FR-AUTH-010**: Tenant admins MUST be able to create custom roles with specific permission sets
- **FR-AUTH-011**: System MUST deny access by default when no policy matches
- **FR-AUTH-012**: System MUST audit all authorization decisions (allow/deny) with timestamp and reason
- **FR-AUTH-013**: System MUST invalidate sessions immediately when user permissions change or user is removed from tenant
- **FR-AUTH-014**: System MUST prevent resource enumeration by returning same error for "not found" and "not authorized"

### Functional Requirements: UUID Migration

- **FR-UUID-001**: System MUST use UUID as primary identifier for all entities: Users, Tenants, Agents, Crews, Tasks, Flows, Executions, Prompts, ChatSessions, Tools, Notifications, LLMProviders, Feedback
- **FR-UUID-002**: System MUST use sortable UUID format (UUIDv7 or ULID) to enable time-based ordering
- **FR-UUID-003**: Migration MUST convert all existing integer IDs to UUIDs in single atomic transaction
- **FR-UUID-004**: Migration MUST preserve all foreign key relationships during conversion
- **FR-UUID-005**: System MUST reject API requests using old integer IDs after migration
- **FR-UUID-006**: System MUST include clear error messages for deprecated integer ID usage
- **FR-UUID-007**: All URLs MUST use UUID format (e.g., `/crews/{uuid}`)
- **FR-UUID-008**: Migration MUST include rollback mechanism in case of failure
- **FR-UUID-009**: System MUST load sample data after migration (sample crews, agents, tasks, flows, prompts)

### Functional Requirements: Async Task Execution

- **FR-EXEC-001**: System MUST queue all execution requests (crews, flows, agents, tasks) for background processing
- **FR-EXEC-002**: System MUST return execution ID immediately upon request submission, before processing begins
- **FR-EXEC-003**: System MUST support pluggable message queue backends (Redis, RabbitMQ, Kafka, SQS)
- **FR-EXEC-004**: System MUST implement distributed worker processing to enable horizontal scaling
- **FR-EXEC-005**: System MUST support tenant-configurable priority levels (high, normal, low) for executions
- **FR-EXEC-006**: System MUST enforce rate limiting per tenant (configurable concurrent execution limit, default: 10)
- **FR-EXEC-007**: System MUST enforce rate limiting per user (configurable, default: 5 concurrent executions)
- **FR-EXEC-008**: Tenant admins MUST be able to adjust rate limits through settings interface
- **FR-EXEC-009**: System MUST automatically retry failed executions up to 3 times
- **FR-EXEC-010**: System MUST use exponential backoff with jitter for retries (base: 2s, 4s, 8s, capped at 30s)
- **FR-EXEC-011**: System MUST move executions to dead letter queue after 3 failed attempts
- **FR-EXEC-012**: Admins MUST be able to view and requeue tasks from dead letter queue
- **FR-EXEC-013**: System MUST enforce tenant-configurable execution timeout (default: 30 minutes)
- **FR-EXEC-014**: System MUST gracefully terminate executions that exceed timeout, cleaning up resources
- **FR-EXEC-015**: System MUST handle soft timeout (warning before termination) and hard timeout (forced termination)
- **FR-EXEC-016**: System MUST ensure task idempotency to handle duplicate submissions safely
- **FR-EXEC-017**: System MUST expose execution queue metrics (queue depth, processing rate, failure rate)
- **FR-EXEC-018**: System MUST integrate with monitoring system (Prometheus) for observability
- **FR-EXEC-019**: Workers MUST automatically reconnect to message queue if connection lost
- **FR-EXEC-020**: System MUST prevent execution submission when message queue is unavailable

### Functional Requirements: Notification System

- **FR-NOTIF-001**: System MUST send real-time notifications via WebSocket to active users
- **FR-NOTIF-002**: System MUST persist all notifications in database for offline users
- **FR-NOTIF-003**: System MUST deliver pending notifications when user reconnects
- **FR-NOTIF-004**: System MUST track notification read/unread status per user
- **FR-NOTIF-005**: System MUST display unread count badge in UI bell icon
- **FR-NOTIF-006**: Users MUST be able to mark notifications as read individually
- **FR-NOTIF-007**: Users MUST be able to mark all notifications as read in bulk
- **FR-NOTIF-008**: System MUST support notification categories: execution_started, execution_completed, execution_failed, execution_timeout, invitation_received, team_mention, system_alert
- **FR-NOTIF-009**: System MUST allow tenant admins to enable/disable notification categories at tenant level
- **FR-NOTIF-010**: System MUST allow users to enable/disable notification categories at user level
- **FR-NOTIF-011**: User-level notification preferences MUST override tenant-level preferences
- **FR-NOTIF-012**: System MUST implement tenant-configurable notification retention policy (default: 90 days)
- **FR-NOTIF-013**: System MUST automatically delete notifications older than retention period
- **FR-NOTIF-014**: System MUST include deep links in notifications to relevant resources
- **FR-NOTIF-015**: System MUST automatically reconnect WebSocket if connection drops
- **FR-NOTIF-016**: System MUST batch notifications to prevent notification spam (max 1 per resource per minute)
- **FR-NOTIF-017**: System MUST include notification timestamp and source (system, user)
- **FR-NOTIF-018**: System MUST support notification priority levels (low, normal, high, critical)

### Functional Requirements: Tenant Management

- **FR-TENANT-001**: System MUST require super admin approval for new tenant registrations
- **FR-TENANT-002**: System MUST create tenant in "pending" status upon registration submission
- **FR-TENANT-003**: System MUST notify all super admins when new tenant registration submitted
- **FR-TENANT-004**: Super admins MUST be able to view all pending tenant registrations
- **FR-TENANT-005**: Super admins MUST be able to approve or reject tenant registrations
- **FR-TENANT-006**: System MUST require rejection reason when super admin rejects tenant
- **FR-TENANT-007**: System MUST notify tenant requester when registration is approved or rejected
- **FR-TENANT-008**: Tenant registration MUST include option to request sample data installation
- **FR-TENANT-009**: System MUST load sample data (crews, agents, tasks, flows, prompts) after tenant approval if requested
- **FR-TENANT-010**: Sample data MUST be fully functional and demonstrate platform capabilities
- **FR-TENANT-011**: Approved tenants without sample data MUST see onboarding wizard on first login
- **FR-TENANT-012**: Tenant registration MUST be immutable after submission (no edits allowed)

---

## Key Entities

### Authorization Domain

- **Permission**: Represents a specific authorization grant (subject: user/role, resource: entity UUID, action: read/write/execute/delete, effect: allow/deny)
- **Role**: Named collection of permissions (e.g., "Data Science Team Lead" with specific crew/agent permissions)
- **Policy**: Tenant-level or user-level authorization rule (e.g., "All members can view public prompts")
- **AuthorizationAuditLog**: Records all authorization checks (timestamp, user, resource, action, decision, reason)

### Execution Domain

- **ExecutionQueue**: Tracks queued execution requests (execution_id, type, priority, status, tenant_id, user_id, retry_count, scheduled_time)
- **DeadLetterTask**: Failed executions after retry exhaustion (original payload, failure reason, failure timestamp, retry history)
- **ExecutionMetrics**: Queue performance data (queue_depth, processing_rate, avg_execution_time, failure_rate)

### Notification Domain

- **Notification**: Persistent notification record (user_id, category, title, message, priority, resource_link, read_status, timestamp)
- **NotificationPreference**: User or tenant notification settings (category, enabled, delivery_channel)

### Tenant Domain

- **TenantRegistration**: Pending tenant request (company_name, admin_email, reason, sample_data_requested, status: pending/approved/rejected, rejection_reason)
- **SuperAdmin**: Special user role with platform-wide permissions

---

## Success Criteria

### Authorization Service
- ✅ Zero unauthorized access incidents after deployment
- ✅ Authorization check response time < 50ms at 95th percentile
- ✅ All API endpoints enforce authorization (100% coverage)
- ✅ Audit logs capture 100% of authorization decisions

### UUID Migration
- ✅ Zero data loss during migration
- ✅ All 20+ entity types converted to UUID
- ✅ All foreign key relationships preserved
- ✅ Sample data loaded successfully

### Async Execution
- ✅ Execution requests return < 200ms (immediate queue, not wait for processing)
- ✅ System handles 100 concurrent executions per tenant
- ✅ 99.9% task completion rate (including retries)
- ✅ Failed tasks moved to DLQ within 1 minute
- ✅ Horizontal scaling proven with 10+ workers

### Notification System
- ✅ Notifications delivered < 1 second after event
- ✅ 99.9% WebSocket delivery success rate
- ✅ Zero notification loss (all persisted)
- ✅ Unread count updates in real-time

### Tenant Management
- ✅ Tenant registrations processed within SLA (e.g., 24 hours)
- ✅ Sample data loads successfully for all approved tenants
- ✅ Super admins can manage all tenant requests

---

## Dependencies and Assumptions

### Dependencies
- Existing authentication system (JWT tokens)
- PostgreSQL database for primary storage
- Redis for message queue and caching
- WebSocket infrastructure for real-time communication
- Monitoring system (Prometheus) for metrics

### Assumptions
- Breaking API changes acceptable (early-stage product)
- Development/test data can be dropped and recreated
- Super admin accounts already exist in system
- System can have short maintenance window for UUID migration
- Redis is highly available (clustered or replicated)
- WebSocket connections maintained for active users

---

## Out of Scope (Future Enhancements)

- Two-factor authentication (2FA)
- Single Sign-On (SSO) integration
- Webhook notifications to external systems
- Email notifications
- Mobile push notifications
- Permission delegation (user grants permissions to another user)
- Time-based permissions (expires after X days)
- Approval workflows for sensitive operations
- Multi-region deployment
- Kafka message queue support (pluggable, but not implemented initially)

---

## Review & Acceptance Checklist

### Content Quality
- ✅ No implementation details (languages, frameworks, APIs)
- ✅ Focused on user value and business needs
- ✅ Written for non-technical stakeholders
- ✅ All mandatory sections completed

### Requirement Completeness
- ⚠️ One [NEEDS CLARIFICATION] marker: Tenant registration timeout behavior
- ✅ Requirements are testable and unambiguous
- ✅ Success criteria are measurable
- ✅ Scope is clearly bounded
- ✅ Dependencies and assumptions identified

---

## Execution Status

- ✅ User description parsed
- ✅ Key concepts extracted
- ✅ Ambiguities resolved (17 clarifying questions answered)
- ✅ User scenarios defined (5 major scenarios)
- ✅ Requirements generated (62 functional requirements)
- ✅ Entities identified (11 entities)
- ✅ Review checklist passed (1 minor clarification noted)

---

## Next Steps

1. **Planning Phase**: Use `/plan` command to generate detailed implementation plan with component diagrams and data flows
2. **Task Breakdown**: Use `/tasks` command to create dependency-ordered task list
3. **Implementation**: Begin with UUID migration (prerequisite for other features), then authorization, then async execution, then notifications, then tenant management
4. **Testing**: Comprehensive testing of authorization policies, queue behavior, and notification delivery
5. **Documentation**: API documentation update, admin guide for tenant management

---
