# Live Execution Streaming - Test Guide

## ✅ What's Been Implemented

### 1. Queue UI with Real-time Updates
- **Location:** http://localhost:3001/queue
- Auto-refreshes every 5 seconds
- Shows queue metrics (depth, processing rate, avg duration, failure rate)
- Filterable by status (All, Queued, Running)
- Cancel button for queued/running executions
- Tenant-filtered (users only see their own executions)

### 2. Live Execution Streaming
- **Location:** http://localhost:3001/executions/[id]
- WebSocket connection to backend
- Real-time output streaming
- Live progress bar with percentage and current step
- Worker info display
- Auto-reconnection with exponential backoff
- Buffer replay for late connections

### 3. Enhanced Features
- Toast notifications for user actions
- Cancel executions from queue UI
- Progress tracking with visual feedback
- Connection status indicator
- Buffered output (last 100 lines)

---

## 🧪 Testing Steps

### Test 1: View Queue Dashboard

1. Navigate to http://localhost:3001/queue
2. **Expected:**
   - See queue metrics at the top
   - See list of queued/running executions
   - Each item shows: type, entity name, status, priority, queue position, created time, retries
   - Page auto-refreshes every 5 seconds

### Test 2: Execute a Crew (Trigger Streaming)

#### Option A: Via UI
1. Go to http://localhost:3001/crews
2. Click on any crew
3. Click "Execute" button
4. Fill in any required inputs
5. Submit

#### Option B: Via API
```bash
# Get your JWT token from localStorage in browser
TOKEN="your-jwt-token-here"

# Get a crew ID
curl http://localhost:8000/api/v1/crews \
  -H "Authorization: Bearer $TOKEN" | jq '.crews[0].id'

# Execute the crew
CREW_ID="your-crew-id-here"
curl -X POST http://localhost:8000/api/v1/crews/$CREW_ID/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "AI trends in 2025",
    "requirements": "Write a research report"
  }' | jq '.id'
```

**Expected Response:**
```json
{
  "id": "execution-uuid",
  "status": "queued",
  "queue_position": 1,
  "...": "..."
}
```

### Test 3: Monitor Live Execution

1. After executing a crew, note the execution ID
2. Navigate to http://localhost:3001/executions/[execution-id]
3. **Expected to see:**
   - Live Execution Stream component
   - Connection status: "connecting" → "connected"
   - Worker info displayed
   - Progress bar showing:
     - "Preparing task: ..." (0-30%)
     - "Executing crew" (30-90%)
     - "Processing results" (90-100%)
   - Live output lines appearing in real-time:
     ```
     >>> Execution started on worker: crewai-celery-worker
     Loaded crew: My Research Crew
     Found 3 tasks for crew
     Initializing execution dependencies...
     Building CrewAI crew instance...
     Starting execution with inputs: ['topic', 'requirements']
     >>> Execution completed: Crew execution completed: 3 tasks executed
     ```

### Test 4: Test Reconnection

1. While execution is running, stop the backend:
   ```bash
   docker-compose stop backend
   ```
2. **Expected:**
   - Connection status changes to "disconnected"
   - "Reconnecting..." message appears

3. Restart backend:
   ```bash
   docker-compose start backend
   ```
4. **Expected:**
   - WebSocket automatically reconnects
   - Buffered lines are replayed
   - "Replaying buffered output..." badge appears
   - Stream continues from where it left off

### Test 5: Cancel Execution from Queue

1. Go to http://localhost:3001/queue
2. Find a queued or running execution
3. Click "Cancel" button in the Actions column
4. Confirm the dialog
5. **Expected:**
   - Confirmation dialog appears
   - After confirming:
     - Success toast: "Execution cancelled successfully"
     - Item disappears from queue or status changes to "cancelled"
     - Queue list refreshes

### Test 6: View Queue Metrics

1. Go to http://localhost:3001/queue
2. **Expected metrics:**
   - **Queue Depth:** Total pending + running
   - **Processing Rate:** Tasks/second over last 5 minutes
   - **Avg Duration:** Average execution time
   - **Failure Rate:** Percentage (red if > 10%, green otherwise)

### Test 7: Test Tenant Isolation

1. Login as User A
2. Execute a crew
3. Note the execution ID
4. Logout and login as User B (different tenant)
5. Try to access http://localhost:3001/executions/[user-a-execution-id]
6. **Expected:**
   - Should not be able to see User A's execution
   - Or execution not found error

---

## 🔍 What to Look For

### In Queue UI (/queue)

✅ **Metrics Display:**
- Queue depth updates in real-time
- Processing rate calculated correctly
- Average duration in seconds
- Failure rate percentage with color coding

✅ **Queue List:**
- Shows executions in priority order
- Status badges color-coded:
  - Yellow: Queued
  - Blue: Running
  - Green: Completed
  - Red: Failed
- Priority labels: High (0-3), Normal (4-6), Low (7-10)
- Time ago display
- Retry counts
- Cancel button for active items

### In Execution Detail (/executions/[id])

✅ **Live Stream Component:**
- Connection indicator (green dot = connected)
- Worker hostname displayed
- Progress bar with percentage
- Current step text
- Terminal-style output (black background, monospace font)
- Auto-scroll to bottom
- Line count at bottom
- "Scroll to bottom" button

✅ **Progress Events:**
```
0-30%: Setup phase
  - Loaded crew
  - Found N tasks
  - Initializing dependencies
  - Building CrewAI instance

30-90%: Execution phase
  - Preparing each task
  - Executing crew
  - Agent/LLM interactions (from CrewAI)

90-100%: Completion phase
  - Processing results
  - Completed successfully
```

✅ **Error Handling:**
- Red text for stderr lines
- Error messages displayed
- Stack traces shown (if available)
- Connection errors with reconnection attempts

---

## 🐛 Troubleshooting

### WebSocket Not Connecting

**Check:**
1. Backend is running: `docker-compose ps backend`
2. Token is valid in localStorage
3. WebSocket URL is correct (check browser console)
4. No CORS issues (check browser console)

**Debug:**
```javascript
// In browser console
console.log('API URL:', process.env.NEXT_PUBLIC_API_URL);
console.log('Token:', localStorage.getItem('token'));
```

### No Output Appearing

**Check:**
1. Execution status is "running" (not queued or completed)
2. Worker is actually executing (check `docker-compose logs celery-worker`)
3. StreamHandler is initialized (check worker logs for "emit_started")
4. Redis pub/sub working (check `docker-compose logs redis`)

**Debug:**
```bash
# Check worker logs
docker-compose logs --tail=50 -f celery-worker

# Check for StreamHandler events
docker-compose logs celery-worker | grep "emit_"

# Check Redis pub/sub
docker exec crewai-redis redis-cli PUBSUB CHANNELS "execution_events:*"
```

### Queue Not Updating

**Check:**
1. Auto-refresh is working (watch browser console)
2. API endpoint returns data: `GET /api/v1/executions/queue/list`
3. User has executions in queue

**Debug:**
```bash
# Check queue API
curl http://localhost:8000/api/v1/executions/queue/list \
  -H "Authorization: Bearer $TOKEN"

# Check database
docker exec crewai-backend python test_execution_flow.py
```

### Cancel Not Working

**Check:**
1. Execution is in "queued" or "running" status
2. Cancel API endpoint: `POST /api/v1/executions/{id}/cancel`
3. User has permission to cancel

**Debug:**
```bash
# Try cancel via API
curl -X POST http://localhost:8000/api/v1/executions/{id}/cancel \
  -H "Authorization: Bearer $TOKEN"
```

---

## 📊 Expected Performance

### WebSocket Connection
- Connection time: < 100ms
- Reconnection delay: 1s, 2s, 4s, 8s, 16s (exponential backoff)
- Max reconnection attempts: 5
- Ping interval: 30s

### Queue Updates
- Auto-refresh interval: 5s
- API response time: < 200ms
- Metrics calculation: < 100ms

### Live Streaming
- Output latency: < 500ms (from worker to UI)
- Buffer size: 100 lines
- Buffer retention: 1 hour
- Progress update frequency: Per task/step

---

## ✨ Success Criteria

A successful test should show:

1. ✅ Queue dashboard loads and displays metrics
2. ✅ Can execute a crew from UI or API
3. ✅ Execution appears in queue immediately
4. ✅ WebSocket connects when viewing execution detail
5. ✅ Live output streams appear in real-time
6. ✅ Progress bar updates showing current step
7. ✅ Execution completes successfully with final message
8. ✅ Can cancel executions from queue UI
9. ✅ Toast notifications appear for actions
10. ✅ Auto-refresh works (queue updates every 5s)
11. ✅ Reconnection works after disconnection
12. ✅ Tenant isolation enforced (can't see other tenant's executions)

---

## 📞 Quick Test Commands

```bash
# 1. Check all services
docker-compose ps

# 2. View backend logs
docker-compose logs --tail=50 -f backend

# 3. View worker logs
docker-compose logs --tail=50 -f celery-worker

# 4. Test queue API
curl http://localhost:8000/api/v1/executions/queue/list \
  -H "Authorization: Bearer $TOKEN"

# 5. Test WebSocket connection (manual - use browser console)
# const ws = new WebSocket('ws://localhost:8000/ws/executions/{id}/stream?token={token}');
# ws.onmessage = (e) => console.log(JSON.parse(e.data));

# 6. Run test suite
docker exec crewai-backend python test_execution_flow.py

# 7. Check Redis pub/sub
docker exec crewai-redis redis-cli PUBSUB CHANNELS "execution_events:*"

# 8. Monitor Redis events
docker exec crewai-redis redis-cli SUBSCRIBE "execution_events:*"
```

---

## 🎯 Key Features Demonstrated

1. **Real-time Updates:** Queue metrics update every 5 seconds
2. **Live Streaming:** Execution output streams via WebSocket
3. **Progress Tracking:** Visual progress bar with step descriptions
4. **Tenant Isolation:** Users only see their own executions
5. **Error Handling:** Reconnection, error display, timeout handling
6. **User Actions:** Cancel, refresh, view details
7. **Notifications:** Toast messages for user feedback
8. **Responsive UI:** Works on desktop and mobile

---

**Test Date:** October 18, 2025
**Status:** ✅ Ready for Testing
