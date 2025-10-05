# Quickstart: Dynamic CrewAI Orchestration Platform

**Date**: 2025-10-05
**Purpose**: Local development setup and integration testing guide

## Prerequisites

Ensure you have the following installed on your development machine:

### Required
- **Docker Desktop** 24+ or **Podman** 4+ (with Docker compatibility)
- **Node.js** 18+ and **npm** 9+
- **Python** 3.11+ and **pip** 23+
- **kubectl** 1.28+ (Kubernetes CLI)
- **kind** 0.20+ (Kubernetes in Docker)
- **Git** 2.40+

### Optional (Recommended)
- **Docker Compose** 2.20+ (for simplified local dev without Kubernetes)
- **Helm** 3.12+ (for Kubernetes deployment)
- **k9s** 0.27+ (Kubernetes cluster UI)

### Verify Installation
```bash
docker --version
node --version
python --version
kubectl version --client
kind --version
```

---

## Part 1: Quick Start (Docker Compose)

For rapid local development without Kubernetes complexity.

### 1.1 Clone Repository
```bash
git clone https://github.com/your-org/crewai-platform.git
cd crewai-platform
```

### 1.2 Environment Setup
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your settings (optional for local dev)
# Defaults are configured for local development
```

### 1.3 Start Services
```bash
# Start PostgreSQL, MongoDB, Redis, backend, frontend
docker-compose up -d

# Check all services are running
docker-compose ps
```

**Expected output**:
```
NAME                  STATUS       PORTS
crewai-backend        Up           0.0.0.0:8000->8000/tcp
crewai-frontend       Up           0.0.0.0:3000->3000/tcp
crewai-postgres       Up           0.0.0.0:5432->5432/tcp
crewai-mongodb        Up           0.0.0.0:27017->27017/tcp
crewai-redis          Up           0.0.0.0:6379->6379/tcp
```

### 1.4 Run Database Migrations
```bash
# Backend container should auto-run migrations on startup
# Verify migrations ran successfully
docker-compose logs backend | grep "Alembic"
```

### 1.5 Access Platform
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs (Swagger UI)
- **PostgreSQL**: localhost:5432 (user: `crewai`, password: `dev_password`)
- **MongoDB**: localhost:27017 (user: `crewai`, password: `dev_password`)

### 1.6 Create First Tenant
1. Open http://localhost:3000
2. Click "Register Organization"
3. Fill in:
   - Email: `admin@test.com`
   - Password: `TestPass123!`
   - Organization Name: `Test Org`
   - Slug: `test-org`
4. Click "Register" - you'll be auto-logged in

### 1.7 Verify Setup
```bash
# Test API health
curl http://localhost:8000/health

# Expected output: {"status": "healthy", "database": "connected"}

# Test frontend
curl http://localhost:3000

# Expected: HTML page loads
```

---

## Part 2: Full Setup (Kubernetes with KinD)

For production-like local environment with isolated container execution.

### 2.1 Create KinD Cluster
```bash
# Create cluster with sysbox support (for Docker-in-Docker)
kind create cluster --name crewai-local --config infra/kind/kind-config.yaml

# Verify cluster is running
kubectl cluster-info --context kind-crewai-local
```

### 2.2 Install Sysbox Runtime (Docker-in-Docker Support)
```bash
# Note: Sysbox requires Docker (not compatible with Podman)
# Install sysbox following: https://github.com/nestybox/sysbox#installation

# Restart Docker daemon after sysbox installation
sudo systemctl restart docker

# Recreate KinD cluster with sysbox
kind delete cluster --name crewai-local
kind create cluster --name crewai-local --config infra/kind/kind-config.yaml
```

### 2.3 Install Infrastructure Dependencies
```bash
# Add Bitnami Helm repository
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update

# Install PostgreSQL
helm install postgres bitnami/postgresql \
  -f infra/kubernetes/overlays/local/postgres-values.yaml \
  --namespace crewai-system --create-namespace

# Install MongoDB
helm install mongodb bitnami/mongodb \
  -f infra/kubernetes/overlays/local/mongodb-values.yaml \
  --namespace crewai-system

# Install Redis
helm install redis bitnami/redis \
  -f infra/kubernetes/overlays/local/redis-values.yaml \
  --namespace crewai-system

# Wait for databases to be ready
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=postgresql \
  -n crewai-system --timeout=300s
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=mongodb \
  -n crewai-system --timeout=300s
```

### 2.4 Build and Deploy Application
```bash
# Build Docker images
docker build -t crewai-backend:local -f infra/docker/backend.Dockerfile .
docker build -t crewai-frontend:local -f infra/docker/frontend.Dockerfile .

# Load images into KinD cluster
kind load docker-image crewai-backend:local --name crewai-local
kind load docker-image crewai-frontend:local --name crewai-local

# Deploy application
kubectl apply -k infra/kubernetes/overlays/local

# Wait for deployments
kubectl wait --for=condition=available deployment/backend \
  -n crewai-app --timeout=300s
kubectl wait --for=condition=available deployment/frontend \
  -n crewai-app --timeout=300s
```

### 2.5 Run Database Migrations
```bash
# Port-forward to backend
kubectl port-forward -n crewai-app deployment/backend 8000:8000 &

# Run migrations
kubectl exec -n crewai-app deployment/backend -- \
  python -m alembic upgrade head

# Kill port-forward
kill %1
```

### 2.6 Access Platform (via Port Forwarding)
```bash
# Frontend
kubectl port-forward -n crewai-app deployment/frontend 3000:3000 &

# Backend
kubectl port-forward -n crewai-app deployment/backend 8000:8000 &

# Open http://localhost:3000
```

**Alternative**: Configure Ingress (see `docs/guides/kubernetes-ingress.md`)

---

## Part 3: Integration Test Scenarios

These scenarios validate the platform end-to-end.

### Scenario 1: User Registration → Flow Creation

**Steps**:
1. Navigate to http://localhost:3000
2. Register new tenant (org: `TestCo`, slug: `testco`)
3. Log in as admin
4. Navigate to "Flows" → "Create Flow"
5. Drag "Input" node onto canvas
6. Drag "LLM" node onto canvas
7. Drag "Output" node onto canvas
8. Connect: Input → LLM → Output
9. Configure LLM node:
   - Select LLM Provider (create one if needed)
   - Set prompt: "Summarize: {{input.text}}"
10. Save flow as "Text Summarizer"
11. Execute flow with input: `{"text": "Long text here..."}`
12. Verify execution completes successfully
13. View execution logs

**Expected Result**: Flow executes, LLM generates summary, output displayed in UI

---

### Scenario 2: Agent Creation → Crew → Chat

**Steps**:
1. Navigate to "Agents" → "Create Agent"
2. Configure agent:
   - Name: "Research Assistant"
   - System Prompt: "You are a helpful research assistant..."
   - LLM Provider: Select configured provider
3. Save agent
4. Navigate to "Crews" → "Create Crew"
5. Add "Research Assistant" agent to crew
6. Set collaboration pattern: Sequential
7. Save crew as "Research Team"
8. Navigate to "Chat"
9. Start new session with "Research Team"
10. Send message: "What are the benefits of multi-tenant architecture?"
11. Verify crew responds with reasoning steps visible
12. Send follow-up: "Can you elaborate on data isolation?"
13. Verify context is maintained

**Expected Result**: Chat interface shows agent reasoning, tool invocations (if any), and maintains conversation context

---

### Scenario 3: Custom Tool Registration → Flow Execution

**Steps**:
1. Navigate to "Tools" → "Register Tool"
2. Configure tool:
   - Name: "HTTP Request"
   - Description: "Make HTTP GET request"
   - Input Schema:
     ```json
     {
       "type": "object",
       "properties": {
         "url": {"type": "string", "format": "uri"}
       },
       "required": ["url"]
     }
     ```
   - Output Schema:
     ```json
     {
       "type": "object",
       "properties": {
         "status_code": {"type": "integer"},
         "body": {"type": "string"}
       }
     }
     ```
   - Execution Config:
     ```json
     {
       "docker_image": "python:3.11-slim",
       "entrypoint": ["python", "-c", "import requests; ..."],
       "timeout_seconds": 60
     }
     ```
3. Save tool
4. Validate tool (should pass schema validation)
5. Create flow with tool node
6. Execute flow with URL input
7. Verify tool executes in isolated container
8. Check execution logs show Docker container lifecycle

**Expected Result**: Tool executes safely in isolated container, returns structured output

---

### Scenario 4: Multi-User Collaboration

**Prerequisites**: Tenant created from Scenario 1

**Steps**:
1. As admin, navigate to "Users" → "Invite User"
2. Invite user: `editor@testco.com` with role "Editor"
3. Editor receives invite (check logs for invite token)
4. Editor accepts invite, sets password
5. Editor logs in
6. Editor creates new flow
7. Editor shares flow with admin (View permission)
8. Admin views shared flow (read-only)
9. Admin tries to edit flow (should be blocked)
10. Editor updates flow permissions (grant Edit to admin)
11. Admin edits flow successfully

**Expected Result**: RBAC permissions enforced, flow sharing works correctly

---

### Scenario 5: Execution Monitoring & Cancellation

**Steps**:
1. Create flow with long-running LLM node (large prompt)
2. Execute flow
3. Navigate to "Executions"
4. View real-time execution progress (SSE stream)
5. Observe node-by-node status updates
6. While execution is running, click "Cancel"
7. Verify execution status changes to "cancelled"
8. Check execution logs for cancellation timestamp

**Expected Result**: Real-time updates stream correctly, cancellation stops execution immediately

---

## Part 4: Development Workflow

### Backend Development

```bash
# Install dependencies
cd backend
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run backend locally (outside Docker)
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Run tests
pytest tests/

# Run specific test
pytest tests/unit/test_flow_service.py

# Generate coverage report
pytest --cov=src --cov-report=html
open htmlcov/index.html
```

### Frontend Development

```bash
# Install dependencies
cd frontend
npm install

# Run frontend dev server
npm run dev

# Open http://localhost:3000

# Run tests
npm test

# Run E2E tests (requires backend running)
npm run test:e2e

# Build for production
npm run build
```

### Database Management

```bash
# Create new migration
cd backend
alembic revision --autogenerate -m "Add new column to flows"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history
```

### Kubernetes Development

```bash
# View logs
kubectl logs -f deployment/backend -n crewai-app

# Shell into pod
kubectl exec -it deployment/backend -n crewai-app -- /bin/bash

# Restart deployment
kubectl rollout restart deployment/backend -n crewai-app

# Delete and recreate cluster
kind delete cluster --name crewai-local
kind create cluster --name crewai-local --config infra/kind/kind-config.yaml
```

---

## Part 5: Troubleshooting

### Issue: Backend fails to connect to PostgreSQL

**Solution**:
```bash
# Check PostgreSQL is running
docker-compose ps postgres  # Docker Compose
kubectl get pods -n crewai-system  # Kubernetes

# Test connection
psql -h localhost -U crewai -d crewai_platform  # Docker Compose
kubectl exec -it postgres-postgresql-0 -n crewai-system -- psql -U crewai  # K8s

# Check backend logs
docker-compose logs backend  # Docker Compose
kubectl logs deployment/backend -n crewai-app  # K8s
```

### Issue: Flow execution stuck in "queued" status

**Solution**:
```bash
# Check execution service is running
docker-compose logs backend | grep "ExecutionService"

# Check Docker-in-Docker pods are available
kubectl get pods -l app=docker-dind -n crewai-system

# Manually trigger execution (dev only)
curl -X POST http://localhost:8000/api/v1/debug/trigger-execution/{execution_id}
```

### Issue: Frontend shows "CORS error"

**Solution**:
```bash
# Verify backend CORS settings
curl -I http://localhost:8000/api/v1/health

# Should include header: Access-Control-Allow-Origin: http://localhost:3000

# Check .env file has correct FRONTEND_URL
cat .env | grep FRONTEND_URL
```

### Issue: LLM requests failing

**Solution**:
1. Verify LLM provider credentials in UI
2. Check backend logs for API errors
3. Test provider connection:
   ```bash
   curl http://localhost:8000/api/v1/llm-providers/{provider_id}/test
   ```

---

## Part 6: Next Steps

After completing the quickstart:

1. **Read Documentation**:
   - Architecture Overview: `docs/architecture/system-overview.md`
   - Multi-Tenancy Guide: `docs/architecture/multi-tenancy.md`
   - Security Model: `docs/architecture/security-model.md`

2. **Explore Features**:
   - Create complex multi-agent flows
   - Register custom tools with Docker execution
   - Configure multiple LLM providers (OpenAI, Anthropic, Ollama)
   - Set up crew collaboration patterns

3. **Deploy to Production**:
   - See `docs/guides/deploying-k8s.md` for production Kubernetes setup
   - Configure managed PostgreSQL (RDS, Cloud SQL)
   - Set up SSL/TLS with Ingress
   - Enable monitoring with Prometheus/Grafana

4. **Contribute**:
   - See `CONTRIBUTING.md` for development guidelines
   - Review constitution: `.specify/memory/constitution.md`
   - Submit issues or pull requests

---

## Summary

You now have a fully functional CrewAI Orchestration Platform running locally!

**What you can do**:
- ✅ Create and manage AI agents and crews
- ✅ Build visual workflows with drag-and-drop
- ✅ Execute flows with real-time monitoring
- ✅ Chat with crews via conversational interface
- ✅ Register custom tools with isolated execution
- ✅ Manage multiple LLM providers
- ✅ Collaborate with team members (multi-user)

**Integration Test Status**:
- Scenario 1 (Flow Creation): Ready to test
- Scenario 2 (Agent & Chat): Ready to test
- Scenario 3 (Custom Tools): Ready to test
- Scenario 4 (Multi-User): Ready to test
- Scenario 5 (Monitoring): Ready to test

For questions or issues, refer to:
- Documentation: `/docs`
- API Spec: `/specs/001-specify-project-title/contracts/openapi.yaml`
- GitHub Issues: (your repository issues page)
