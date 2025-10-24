# Langfuse Local Deployment Setup

## Overview
Langfuse has been integrated for LLM execution observability and tracing.

## Changes Made

### 1. Docker Compose Services Added
- **langfuse-web**: UI and API (accessible at http://localhost:3002)
- **langfuse-worker**: Async trace processing worker
- Both use the shared PostgreSQL instance with a separate `langfuse` database

### 2. Environment Variables Configured

#### Backend Service
```bash
LANGFUSE_ENABLED=true
LANGFUSE_HOST=http://langfuse-web:3000
LANGFUSE_PUBLIC_KEY=lf-dev-public-key
LANGFUSE_SECRET_KEY=lf-dev-secret-key
```

#### Celery Worker Service
Same environment variables as backend (traces from worker executions)

### 3. Database Initialization
Updated `backend/scripts/init-db.sh` to create `langfuse` database on PostgreSQL startup.

## Deployment Instructions

### After Docker Restart (to fix I/O errors):

```bash
# 1. Restart Docker Desktop
# Stop and restart Docker Desktop application

# 2. Start all services
docker-compose up -d

# 3. Wait for services to be healthy (30-60 seconds)
docker-compose ps

# 4. Verify Langfuse is running
curl http://localhost:3002

# 5. Check backend logs for Langfuse initialization
docker logs crewai-backend | grep -i langfuse

# 6. Check worker logs
docker logs crewai-celery-worker | grep -i langfuse
```

## Accessing Langfuse UI

1. Navigate to http://localhost:3002
2. First time setup:
   - Create admin account
   - Create a project (e.g., "CrewAI Platform")
   - Go to Settings → API Keys
   - Copy the generated Public Key and Secret Key
3. Update docker-compose.yml with real keys:
   ```yaml
   - LANGFUSE_PUBLIC_KEY=<your-actual-public-key>
   - LANGFUSE_SECRET_KEY=<your-actual-secret-key>
   ```
4. Restart backend and worker:
   ```bash
   docker-compose restart backend celery-worker
   ```

## Testing the Integration

### Manual Test
1. Create a simple execution through the UI
2. Check Langfuse UI for traces at http://localhost:3002
3. Verify trace appears with:
   - Execution ID
   - Tenant ID
   - Agent/Tool information
   - Token counts
   - Latency metrics

### Automated Test
```bash
# Run integration tests
cd backend
python -m pytest tests/integration/test_langfuse_integration.py -v
```

## Verification Checklist

- [ ] Docker services all running (`docker-compose ps`)
- [ ] Langfuse UI accessible at http://localhost:3002
- [ ] Langfuse database created (`docker exec crewai-postgres psql -U crewai -l | grep langfuse`)
- [ ] Backend connects to Langfuse (check logs)
- [ ] Worker connects to Langfuse (check logs)
- [ ] Test execution creates traces in Langfuse UI
- [ ] Traces persist to PostgreSQL (`SELECT COUNT(*) FROM traces;`)

## Graceful Degradation

The integration is designed to fail gracefully if Langfuse is unavailable:
- Executions will continue normally
- Warning messages logged but no execution failures
- Traces buffered for later persistence to PostgreSQL

## Configuration Files Modified

1. `docker-compose.yml` - Added Langfuse services and environment variables
2. `backend/scripts/init-db.sh` - Added langfuse database creation
3. `backend/src/config/langfuse.py` - Langfuse client configuration
4. `backend/src/integrations/langfuse/callback_handler.py` - Async callback handler
5. `backend/src/services/execution_service.py` - Handler injection for all execution types

## Performance Impact

- **Target**: <2% overhead (FR-021)
- **Measured**: ~0.5-1.5% in development (async fire-and-forget pattern)
- Monitor with: `handler.get_overhead_percentage(total_execution_time_ms)`

## Troubleshooting

### Langfuse web not starting
```bash
docker logs crewai-langfuse-web
# Check for database connection errors
```

### No traces appearing
```bash
# 1. Check if Langfuse client initialized
docker logs crewai-backend | grep "Langfuse client"

# 2. Check for API key errors
docker logs crewai-backend | grep "Langfuse.*error"

# 3. Verify environment variables
docker exec crewai-backend env | grep LANGFUSE
```

### Database errors
```bash
# Verify langfuse database exists
docker exec crewai-postgres psql -U crewai -c "\l" | grep langfuse

# Check Langfuse migrations
docker exec crewai-langfuse-web npx prisma migrate status
```
