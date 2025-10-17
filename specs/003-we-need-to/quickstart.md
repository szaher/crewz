# Quickstart: Platform Infrastructure Enhancements

**Feature**: Platform Infrastructure Enhancements
**Branch**: `003-we-need-to`
**Purpose**: End-to-end testing guide for all 5 major features

---

## Prerequisites

```bash
# 1. Environment running
docker-compose ps  # Verify all services running (postgres, redis, backend, frontend)

# 2. Apply migrations
docker-compose exec backend alembic upgrade head

# 3. Get JWT token
export JWT_TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@test.com","password":"password"}' | jq -r '.access_token')
```

---

## Scenario 1: UUID Migration

**Goal**: Verify all entities migrated to UUID successfully

### Step 1: Check UUID format in database
```bash
docker-compose exec postgres psql -U crewai -d crewai_platform -c \
  "SELECT id, email FROM users LIMIT 3;"

# Expected: UUIDs like 018e1234-5678-7abc-def0-123456789abc (36 chars)
```

### Step 2: Test API with UUID
```bash
# Get user by UUID
USER_ID="<uuid-from-step-1>"
curl http://localhost:8000/api/v1/users/$USER_ID \
  -H "Authorization: Bearer $JWT_TOKEN"

# Expected: 200 OK with user details
```

### Step 3: Verify foreign key relationships
```bash
docker-compose exec postgres psql -U crewai -d crewai_platform -c \
  "SELECT a.id as agent_id, a.name, t.id as tenant_id, t.name as tenant_name
   FROM agents a JOIN tenants t ON a.tenant_id = t.id LIMIT 3;"

# Expected: UUIDs for both agent_id and tenant_id, relationships intact
```

### Step 4: Test integer ID rejection
```bash
# Try old integer ID (should fail)
curl http://localhost:8000/api/v1/users/123 \
  -H "Authorization: Bearer $JWT_TOKEN"

# Expected: 400 Bad Request "Invalid UUID format"
```

✅ **Success Criteria**: All IDs are UUIDs, relationships work, integer IDs rejected

---

## Scenario 2: Authorization Service

**Goal**: Test permission checks, roles, and policies

### Step 1: Create custom role
```bash
curl -X POST http://localhost:8000/api/v1/authz/roles \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Data Scientist",
    "slug": "data-scientist",
    "description": "Can execute crews, cannot delete",
    "priority": 600
  }'

# Expected: 201 Created with role details
# Save role_id from response
ROLE_ID="<role-id-from-response>"
```

### Step 2: Add permission to role
```bash
curl -X POST http://localhost:8000/api/v1/authz/roles/$ROLE_ID/permissions \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "resource_type": "crew",
    "resource_id": null,
    "action": "execute",
    "effect": "allow"
  }'

# Expected: 201 Created
```

### Step 3: Check permission
```bash
CREW_ID="<existing-crew-uuid>"
curl -X POST http://localhost:8000/api/v1/authz/check \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "resource_type": "crew",
    "resource_id": "'$CREW_ID'",
    "action": "execute"
  }'

# Expected: {"decision": "allow", "reason": "role:data-scientist", "latency_ms": <50}
```

### Step 4: Create tenant-level policy
```bash
curl -X POST http://localhost:8000/api/v1/authz/policies \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "scope": "tenant",
    "name": "All members can view prompts",
    "resource_pattern": "prompt:*",
    "action_pattern": "read",
    "effect": "allow",
    "priority": 100
  }'

# Expected: 201 Created
```

### Step 5: Query audit logs
```bash
curl "http://localhost:8000/api/v1/authz/audit?decision=allow&page=1" \
  -H "Authorization: Bearer $JWT_TOKEN"

# Expected: List of authorization checks with decisions and reasons
```

✅ **Success Criteria**: Roles/permissions work, policies apply, audit logs captured, checks <50ms

---

## Scenario 3: Async Task Execution

**Goal**: Submit execution, monitor queue, test retries and DLQ

### Step 1: Submit crew execution
```bash
curl -X POST http://localhost:8000/api/v1/executions/submit \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "execution_type": "crew",
    "entity_id": "'$CREW_ID'",
    "payload": {"input": "Analyze Q3 sales data"},
    "priority": "normal"
  }'

# Expected: 202 Accepted with execution_id (returned in <200ms)
# Save execution_id
EXEC_ID="<execution-id-from-response>"
```

### Step 2: Monitor execution status
```bash
curl http://localhost:8000/api/v1/executions/$EXEC_ID \
  -H "Authorization: Bearer $JWT_TOKEN"

# Expected: status changes: pending → running → completed
# Poll every 2 seconds to see status progression
```

### Step 3: Check queue metrics
```bash
curl "http://localhost:8000/api/v1/executions/queue/metrics?timeframe=5m" \
  -H "Authorization: Bearer $JWT_TOKEN"

# Expected: queue_depth, processing_rate, avg_duration_ms, failure_rate
```

### Step 4: Test rate limiting
```bash
# Submit 11 concurrent executions (exceeds default limit of 10)
for i in {1..11}; do
  curl -X POST http://localhost:8000/api/v1/executions/submit \
    -H "Authorization: Bearer $JWT_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"execution_type":"crew","entity_id":"'$CREW_ID'","payload":{}}' &
done
wait

# Expected: First 10 succeed (202), 11th returns 429 Rate Limit Exceeded
```

### Step 5: View dead letter queue (simulate failure)
```bash
# After a task fails 3 times (manually trigger or wait for natural failure)
curl http://localhost:8000/api/v1/executions/dlq \
  -H "Authorization: Bearer $JWT_TOKEN"

# Expected: List of failed tasks with retry_history showing 3 attempts
```

### Step 6: Requeue from DLQ
```bash
DLQ_TASK_ID="<task-id-from-dlq>"
curl -X POST http://localhost:8000/api/v1/executions/dlq/$DLQ_TASK_ID/requeue \
  -H "Authorization: Bearer $JWT_TOKEN"

# Expected: 200 OK with new execution_id
```

✅ **Success Criteria**: Submissions <200ms, retries work, DLQ captures failures, metrics available

---

## Scenario 4: Notification System

**Goal**: Test WebSocket delivery, read/unread tracking, preferences

### Step 1: Connect WebSocket (in browser console or wscat)
```javascript
// Browser console or wscat cli
const ws = new WebSocket(`ws://localhost:8000/ws/notifications?token=${JWT_TOKEN}`);

ws.onmessage = (event) => {
  console.log('Notification:', JSON.parse(event.data));
};

// Expected: Connection established, any pending notifications delivered immediately
```

### Step 2: Trigger notification (execute crew from Scenario 3)
```bash
# Submit execution (will trigger execution_started notification)
curl -X POST http://localhost:8000/api/v1/executions/submit \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"execution_type":"crew","entity_id":"'$CREW_ID'","payload":{}}'

# Expected: WebSocket receives notification within 1 second
# {
#   "type": "notification",
#   "data": {
#     "category": "execution_started",
#     "title": "Crew Execution Started",
#     "message": "Your crew 'Marketing Team' has started",
#     ...
#   }
# }
```

### Step 3: Check unread count
```bash
curl http://localhost:8000/api/v1/notifications/unread-count \
  -H "Authorization: Bearer $JWT_TOKEN"

# Expected: {"unread_count": 2, "unread_by_category": {"execution_started": 1, "execution_completed": 1}}
```

### Step 4: Mark as read
```bash
NOTIF_ID="<notification-id>"
curl -X PUT http://localhost:8000/api/v1/notifications/$NOTIF_ID/read \
  -H "Authorization: Bearer $JWT_TOKEN"

# Expected: 200 OK, unread_count decrements
```

### Step 5: Update preferences
```bash
curl -X PUT http://localhost:8000/api/v1/notifications/preferences \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "preferences": [
      {
        "category": "execution_started",
        "enabled": false
      },
      {
        "category": "execution_completed",
        "enabled": true
      }
    ]
  }'

# Expected: 200 OK, execution_started notifications now disabled
```

### Step 6: Test offline delivery
```bash
# 1. Disconnect WebSocket
ws.close();

# 2. Trigger notification (execute crew)
curl -X POST http://localhost:8000/api/v1/executions/submit ... # (same as step 2)

# 3. Reconnect WebSocket
const ws2 = new WebSocket(`ws://localhost:8000/ws/notifications?token=${JWT_TOKEN}`);

# Expected: Missed notification delivered immediately on reconnect
```

✅ **Success Criteria**: Notifications <1s, WebSocket reconnects, preferences work, offline delivery works

---

## Scenario 5: Tenant Management

**Goal**: Test tenant registration, super admin approval, sample data

### Step 1: Submit tenant registration (public, no auth)
```bash
curl -X POST http://localhost:8000/api/v1/tenants/register \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Test Corp",
    "admin_email": "admin@testcorp.com",
    "admin_name": "John Doe",
    "reason": "We want to automate our workflows with AI agents for marketing and data analysis tasks.",
    "sample_data_requested": true
  }'

# Expected: 201 Created with registration_id, status="pending"
# Save registration_id
REG_ID="<registration-id>"
```

### Step 2: Check registration status (public)
```bash
curl "http://localhost:8000/api/v1/tenants/register/status?email=admin@testcorp.com"

# Expected: {"status": "pending", "submitted_at": "2025-10-12T...", "message": "Registration pending approval"}
```

### Step 3: Login as super admin
```bash
export SUPER_ADMIN_TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"superadmin@platform.local","password":"<super-admin-password>"}' | jq -r '.access_token')
```

### Step 4: List pending registrations (super admin only)
```bash
curl http://localhost:8000/api/v1/admin/tenants/pending \
  -H "Authorization: Bearer $SUPER_ADMIN_TOKEN"

# Expected: List including registration from Step 1
```

### Step 5: Approve registration
```bash
curl -X POST http://localhost:8000/api/v1/admin/tenants/$REG_ID/approve \
  -H "Authorization: Bearer $SUPER_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"notes": "Approved for pilot program"}'

# Expected: 200 OK with:
# - tenant: {id, name, status="active"}
# - admin_user: {id, email, temporary_password}
# - sample_data_loaded: true
#
# Save tenant_id and temporary_password
TENANT_ID="<tenant-id>"
TEMP_PASSWORD="<temporary-password>"
```

### Step 6: Verify sample data loaded
```bash
# Login as new tenant admin
TENANT_ADMIN_TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@testcorp.com","password":"'$TEMP_PASSWORD'"}' | jq -r '.access_token')

# List crews (should have 3 sample crews)
curl http://localhost:8000/api/v1/crews \
  -H "Authorization: Bearer $TENANT_ADMIN_TOKEN"

# Expected: 3 crews (Marketing Team, Data Analysis Team, Customer Support Team)

# List flows (should have 5 sample flows)
curl http://localhost:8000/api/v1/flows \
  -H "Authorization: Bearer $TENANT_ADMIN_TOKEN"

# Expected: 5 flows (Blog Post, Data Pipeline, etc.)
```

### Step 7: Test rejection (optional)
```bash
# Submit another registration
curl -X POST http://localhost:8000/api/v1/tenants/register \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Spam Corp",
    "admin_email": "spam@spam.com",
    "admin_name": "Spammer",
    "reason": "I want to spam people with AI agents",
    "sample_data_requested": false
  }'

REG_ID_2="<registration-id-2>"

# Reject as super admin
curl -X POST http://localhost:8000/api/v1/admin/tenants/$REG_ID_2/reject \
  -H "Authorization: Bearer $SUPER_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Use case does not align with platform values. Suspected spam activity."}'

# Expected: 200 OK, status="rejected"
```

✅ **Success Criteria**: Registration flow works, super admin can approve/reject, sample data loads correctly

---

## Integration Test: All Features Together

**Goal**: Test features working together end-to-end

```bash
# 1. Tenant registers
curl -X POST http://localhost:8000/api/v1/tenants/register \
  -H "Content-Type: application/json" \
  -d '{"company_name":"Integration Test Co","admin_email":"test@integration.com","admin_name":"Tester","reason":"Full integration testing of platform features including authorization, execution queue, and notifications","sample_data_requested":true}'

# 2. Super admin approves
curl -X POST http://localhost:8000/api/v1/admin/tenants/<reg-id>/approve \
  -H "Authorization: Bearer $SUPER_ADMIN_TOKEN"

# 3. Tenant admin logs in
TENANT_TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@integration.com","password":"<temp-password>"}' | jq -r '.access_token')

# 4. Connect WebSocket for notifications
# (In browser: new WebSocket(...))

# 5. Execute sample crew (triggers authz check + queue + notification)
curl -X POST http://localhost:8000/api/v1/executions/submit \
  -H "Authorization: Bearer $TENANT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"execution_type":"crew","entity_id":"<sample-crew-id>","payload":{"input":"Test integration"}}'

# Expected flow:
# - Authorization check: allow (role:tenant-admin)
# - Execution queued: 202 Accepted <200ms
# - Notification sent via WebSocket: "execution_started" <1s
# - Worker processes execution
# - Notification sent via WebSocket: "execution_completed" <1s
# - Audit log captured
# - Queue metrics updated

# 6. Verify all components
curl http://localhost:8000/api/v1/authz/audit | jq '.logs[0]'  # Authz decision logged
curl http://localhost:8000/api/v1/executions/<exec-id> | jq '.status'  # Execution completed
curl http://localhost:8000/api/v1/notifications/unread-count | jq '.unread_count'  # Notifications received
```

✅ **Success Criteria**: All features work together seamlessly with correct timing and state

---

## Performance Validation

### Authorization Check Latency (<50ms p95)
```bash
# Run 100 permission checks, measure p95 latency
for i in {1..100}; do
  curl -s -w "%{time_total}\n" -o /dev/null -X POST http://localhost:8000/api/v1/authz/check \
    -H "Authorization: Bearer $JWT_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"resource_type":"crew","action":"read"}'
done | sort -n | tail -5

# Expected: p95 < 0.050 seconds (50ms)
```

### Queue Submission Latency (<200ms)
```bash
# Run 100 submissions, measure p95 latency
for i in {1..100}; do
  curl -s -w "%{time_total}\n" -o /dev/null -X POST http://localhost:8000/api/v1/executions/submit \
    -H "Authorization: Bearer $JWT_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"execution_type":"crew","entity_id":"'$CREW_ID'","payload":{}}'
done | sort -n | tail -5

# Expected: p95 < 0.200 seconds (200ms)
```

### Notification Delivery Latency (<1s)
```javascript
// Browser console - measure WebSocket latency
const startTime = Date.now();
fetch('/api/v1/executions/submit', {
  method: 'POST',
  headers: {'Authorization': 'Bearer ' + JWT_TOKEN, 'Content-Type': 'application/json'},
  body: JSON.stringify({execution_type:'crew',entity_id:CREW_ID,payload:{}})
});

ws.onmessage = (event) => {
  const latency = Date.now() - startTime;
  console.log(`Notification latency: ${latency}ms`);
  // Expected: < 1000ms
};
```

---

## Cleanup

```bash
# Reset database (development only!)
docker-compose down -v
docker-compose up -d
docker-compose exec backend alembic upgrade head

# Or just delete test data
docker-compose exec postgres psql -U crewai -d crewai_platform -c \
  "DELETE FROM tenant_registrations WHERE company_name LIKE 'Test%';"
```

---

## Troubleshooting

### Authorization checks slow (>50ms)
- Check Redis connection: `docker-compose exec redis redis-cli ping`
- Check cache hit rate: Redis keys should include `authz:*`
- Review database indexes: `\d permissions` in psql

### Executions not processing
- Check Celery workers: `docker-compose logs celery-worker`
- Check Redis queue: `docker-compose exec redis redis-cli LLEN celery`
- Check dead letter queue: `curl .../executions/dlq`

### Notifications not delivering
- Check WebSocket connection: Browser dev tools → Network → WS
- Check Redis pub/sub: `docker-compose exec redis redis-cli PUBSUB CHANNELS`
- Check notification preferences: `curl .../notifications/preferences`

### Sample data not loading
- Check seeder logs: `docker-compose logs backend | grep seed`
- Verify tenant_id: `SELECT * FROM tenants WHERE ...`
- Check foreign keys: Sample data requires LLM provider configured

---

**End of Quickstart Guide**
