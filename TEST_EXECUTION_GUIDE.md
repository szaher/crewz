# Test Execution Guide (T164)

This guide provides instructions for running all tests and fixing any failures.

## Prerequisites

### 1. Environment Setup

Ensure you have completed local development setup per `docs/guides/local-development.md`:

```bash
# Verify required software
docker --version          # 24.0+
docker-compose --version  # 2.20+
python3 --version         # 3.11+
node --version            # 18.0+
```

### 2. Start Infrastructure Services

```bash
# Start PostgreSQL, MongoDB, Redis, Docker-in-Docker
docker-compose up -d

# Verify all services are running
docker-compose ps

# Expected output:
# NAME                STATUS
# postgres            Up
# mongodb             Up
# redis               Up
# docker-dind         Up
```

### 3. Backend Setup

```bash
cd backend

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run database migrations
alembic upgrade head

# Create test tenant (optional, for manual testing)
python scripts/create_initial_tenant.py
```

### 4. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Install Playwright browsers for E2E tests
npx playwright install --with-deps chromium
```

## Running Tests

### Backend Tests

#### 1. Contract Tests

Test API contracts against OpenAPI specification:

```bash
cd backend
source venv/bin/activate

pytest tests/contract/ -v --tb=short

# Expected output:
# tests/contract/test_auth_register.py::test_register_endpoint PASSED
# tests/contract/test_auth_login.py::test_login_endpoint PASSED
# tests/contract/test_flows_crud.py::test_flow_endpoints PASSED
# tests/contract/test_flow_execute.py::test_flow_execution PASSED
# tests/contract/test_agents_crud.py::test_agent_endpoints PASSED
# tests/contract/test_chat_websocket.py::test_chat_functionality PASSED
```

#### 2. Unit Tests

Test individual components in isolation:

```bash
cd backend
source venv/bin/activate

pytest tests/unit/ -v --cov=src --cov-report=html --cov-report=term

# Expected output:
# tests/unit/test_llm_service.py::test_llm_failover PASSED
# tests/unit/test_flow_validator.py::test_dag_validation PASSED
# tests/unit/test_docker_service.py::test_container_isolation PASSED
# tests/unit/test_flow_executor.py::test_topological_sort PASSED
# ...
# Coverage: 85%+ target

# View coverage report
open htmlcov/index.html
```

#### 3. Integration Tests

Test component interactions with real databases:

```bash
cd backend
source venv/bin/activate

# Set test environment variables
export DATABASE_URL="postgresql://crewai:crewai_password@localhost:5432/crewai_test"
export MONGODB_URL="mongodb://crewai:crewai_password@localhost:27017/crewai_test"
export REDIS_URL="redis://localhost:6379/0"

pytest tests/integration/ -v --tb=short

# Expected tests:
# test_multi_tenancy.py::test_schema_isolation PASSED
# test_multi_tenancy.py::test_data_isolation_users PASSED
# test_multi_tenancy.py::test_cross_tenant_queries_blocked PASSED
# test_flow_execution.py::test_docker_tool_execution PASSED
# test_flow_execution.py::test_flow_timeout_enforcement PASSED
# test_llm_failover.py::test_provider_failover PASSED
# test_llm_failover.py::test_cost_tracking PASSED
# test_chat_streaming.py::test_websocket_streaming PASSED
# test_chat_streaming.py::test_message_persistence PASSED
```

#### 4. All Backend Tests

Run complete backend test suite:

```bash
cd backend
source venv/bin/activate

pytest tests/ -v --cov=src --cov-report=html --cov-report=term --tb=short

# Coverage targets:
# - Overall: 80%+
# - Models: 90%+
# - Services: 85%+
# - API endpoints: 75%+
```

### Frontend Tests

#### 1. Unit Tests

Test React components in isolation:

```bash
cd frontend

npm test -- --coverage --watchAll=false

# Expected output:
# PASS src/components/auth/LoginForm.test.tsx
# PASS src/components/flows/FlowCanvas.test.tsx
# PASS src/components/chat/ChatWindow.test.tsx
# ...
# Coverage: 80%+ target
```

#### 2. Type Checking

Verify TypeScript types:

```bash
cd frontend

npm run type-check

# Expected: No type errors
```

#### 3. Linting

Check code quality:

```bash
cd frontend

npm run lint

# Expected: No linting errors
```

#### 4. Build Verification

Ensure production build succeeds:

```bash
cd frontend

npm run build

# Expected: Build completes without errors
# Check bundle size: .next/ directory
du -sh .next/
```

#### 5. E2E Tests (Playwright)

**Important**: Backend server must be running!

Terminal 1 - Start backend:
```bash
cd backend
source venv/bin/activate
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Terminal 2 - Start frontend:
```bash
cd frontend
npm run dev
```

Terminal 3 - Run E2E tests:
```bash
cd frontend

# Run all E2E scenarios
npm run test:e2e

# Expected tests:
# scenario1-registration-flow.spec.ts PASSED (User registration → Flow creation)
# scenario2-agent-crew-chat.spec.ts PASSED (Agent → Crew → Chat)
# scenario3-tool-execution.spec.ts PASSED (Tool registration → Execution)
# scenario4-collaboration.spec.ts PASSED (Multi-user RBAC)
# scenario5-monitoring.spec.ts PASSED (Execution monitoring)

# Run specific scenario
npm run test:e2e -- scenario1-registration-flow.spec.ts

# Run in headed mode (see browser)
npm run test:e2e:ui
```

### Performance Tests (Optional)

#### 1. Locust Load Test

**Prerequisites**: Backend running, create test tenant first

```bash
cd backend
source venv/bin/activate

# Start Locust
locust -f tests/performance/locustfile.py --host=http://localhost:8000

# Open browser: http://localhost:8089
# Configure:
#   - Number of users: 100
#   - Spawn rate: 10 users/sec
#   - Host: http://localhost:8000
# Click "Start swarming"

# Monitor:
# - Request rate (RPS)
# - Response times (P50, P95, P99)
# - Error rate (target: <1%)
```

#### 2. Concurrent Execution Test

```bash
cd backend
source venv/bin/activate

pytest tests/performance/test_concurrent_executions.py -v -s

# Tests:
# test_concurrent_simple_flows - 100 parallel simple flows
# test_concurrent_mixed_complexity - Mixed flow complexity
# test_sustained_load - 5 minutes sustained load
# test_resource_cleanup - Verify cleanup

# Performance targets:
# - P95 response time < 1s
# - Error rate < 1%
# - All executions complete successfully
```

## Troubleshooting

### Common Issues

#### 1. Database Connection Errors

**Error**: `psycopg2.OperationalError: could not connect to server`

**Solution**:
```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# Restart if needed
docker-compose restart postgres

# Check logs
docker-compose logs postgres
```

#### 2. Import Errors

**Error**: `ModuleNotFoundError: No module named 'xxx'`

**Solution**:
```bash
# Backend: Reinstall dependencies
cd backend
source venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

# Frontend: Reinstall dependencies
cd frontend
rm -rf node_modules package-lock.json
npm install
```

#### 3. Migration Errors

**Error**: `alembic.util.exc.CommandError`

**Solution**:
```bash
cd backend
source venv/bin/activate

# Check current version
alembic current

# Reset if needed
alembic downgrade base
alembic upgrade head
```

#### 4. E2E Tests Timeout

**Error**: `Timeout 30000ms exceeded`

**Solution**:
- Ensure backend is running on port 8000
- Ensure frontend is running on port 3000
- Check API connectivity: `curl http://localhost:8000/health`
- Increase timeout in playwright.config.ts if needed

#### 5. Port Already in Use

**Error**: `Error: listen EADDRINUSE: address already in use`

**Solution**:
```bash
# Find process using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>

# Or use different port
uvicorn src.main:app --port 8001
```

## Fixing Failing Tests

### Step-by-Step Process

1. **Run tests to identify failures**:
   ```bash
   pytest tests/ -v --tb=short
   ```

2. **Analyze failure output**:
   - Read the traceback
   - Identify the failing assertion
   - Check error message

3. **Common failure patterns**:

   **Assertion failures**:
   - Check expected vs actual values
   - Verify test data setup
   - Review business logic

   **Timeout failures**:
   - Increase timeout if operation is slow
   - Check if external service is available
   - Review async/await usage

   **Database errors**:
   - Verify migrations are up to date
   - Check test database isolation
   - Review transaction handling

   **Import errors**:
   - Check for circular imports
   - Verify module structure
   - Review __init__.py files

4. **Fix the code**:
   - Make minimal changes to fix issue
   - Don't break other tests
   - Follow existing patterns

5. **Re-run tests**:
   ```bash
   # Run just the fixed test
   pytest tests/path/to/test_file.py::test_function -v

   # Run full suite to ensure no regression
   pytest tests/ -v
   ```

6. **Update test if needed**:
   - If requirements changed, update test
   - Add comments explaining edge cases
   - Consider adding more test cases

## Test Coverage Requirements

### Backend
- **Overall**: 80%+ (pytest --cov)
- **Models**: 90%+ (critical for data integrity)
- **Services**: 85%+ (core business logic)
- **API endpoints**: 75%+ (integration coverage)

### Frontend
- **Overall**: 80%+ (Jest coverage)
- **Components**: 75%+ (UI logic)
- **Utilities**: 90%+ (pure functions)
- **Pages**: 70%+ (integration tests)

## Continuous Integration

Tests are automatically run on:
- Every push to feature branches
- Every pull request to main
- Before deployment to staging/production

See `.github/workflows/` for CI configuration.

## Reporting Test Results

After completing test execution:

1. **Generate coverage report**:
   ```bash
   # Backend
   cd backend
   pytest tests/ --cov=src --cov-report=html
   # Report: backend/htmlcov/index.html

   # Frontend
   cd frontend
   npm test -- --coverage --watchAll=false
   # Report: frontend/coverage/lcov-report/index.html
   ```

2. **Document any failures**:
   - Create GitHub issues for bugs
   - Note known issues in documentation
   - Tag issues with severity

3. **Update CHANGELOG.md**:
   - List any bugs fixed
   - Note test coverage achieved
   - Document known limitations

## Next Steps

After successful test execution:

1. ✅ Mark T164 as complete in tasks.md
2. → Proceed to T165 (Code cleanup)
3. → Prepare for staging deployment
4. → Conduct user acceptance testing

## Quick Reference

```bash
# Backend - All tests with coverage
cd backend && source venv/bin/activate && pytest tests/ --cov=src --cov-report=html -v

# Frontend - All tests
cd frontend && npm test -- --coverage --watchAll=false && npm run type-check

# E2E - All scenarios (requires servers running)
cd frontend && npm run test:e2e

# Performance - Load test
cd backend && source venv/bin/activate && locust -f tests/performance/locustfile.py --headless --users 100 --spawn-rate 10 --run-time 5m --host http://localhost:8000

# Performance - Concurrent executions
cd backend && source venv/bin/activate && pytest tests/performance/test_concurrent_executions.py -v -s
```

---

**Test Completion Checklist**:
- [ ] All backend unit tests pass (80%+ coverage)
- [ ] All backend integration tests pass
- [ ] All frontend unit tests pass (80%+ coverage)
- [ ] All E2E scenarios pass
- [ ] No linting errors
- [ ] No type errors
- [ ] Build succeeds
- [ ] Performance tests meet targets (optional)
- [ ] Coverage reports generated
- [ ] Test results documented
