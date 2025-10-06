# Local Development Guide

## Overview

This guide walks you through setting up the Dynamic CrewAI Orchestration Platform on your local machine for development.

## Prerequisites

### Required Software

| Software | Minimum Version | Purpose |
|----------|----------------|---------|
| **Docker** | 24.0+ | Container runtime |
| **Docker Compose** | 2.20+ | Multi-container orchestration |
| **Python** | 3.11+ | Backend development |
| **Node.js** | 18.0+ | Frontend development |
| **Git** | 2.30+ | Version control |

### Optional Tools

- **PostgreSQL Client** (`psql`): Database queries
- **MongoDB Compass**: MongoDB GUI
- **Redis CLI**: Cache inspection
- **Postman/Insomnia**: API testing
- **VS Code**: Recommended editor with extensions

## Initial Setup

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/crewai-platform.git
cd crewai-platform
```

### 2. Environment Configuration

Create environment files for backend and frontend:

**Backend (.env):**
```bash
# Copy example environment file
cp backend/.env.example backend/.env

# Edit backend/.env
cat > backend/.env <<EOF
# Database
DATABASE_URL=postgresql://crewai:crewai_password@localhost:5432/crewai_dev
MONGODB_URL=mongodb://crewai:crewai_password@localhost:27017/crewai_dev
REDIS_URL=redis://localhost:6379/0

# Authentication
JWT_SECRET=your-super-secret-jwt-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Encryption
ENCRYPTION_KEY=your-32-byte-encryption-key-here-change-this

# Application
ENVIRONMENT=development
LOG_LEVEL=DEBUG
DEBUG=True

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:3001

# Celery
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Docker-in-Docker
DOCKER_HOST=tcp://localhost:2375

# OpenTelemetry
OTEL_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
OTEL_SERVICE_NAME=crewai-backend-dev

# LLM Providers (for testing)
OPENAI_API_KEY=sk-your-openai-key-here
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here
EOF
```

**Frontend (.env.local):**
```bash
# Copy example environment file
cp frontend/.env.example frontend/.env.local

# Edit frontend/.env.local
cat > frontend/.env.local <<EOF
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000

# Environment
NEXT_PUBLIC_ENVIRONMENT=development

# Features
NEXT_PUBLIC_ENABLE_ANALYTICS=false
NEXT_PUBLIC_ENABLE_ERROR_TRACKING=false
EOF
```

### 3. Start Infrastructure Services

Use Docker Compose to start PostgreSQL, MongoDB, Redis, and Docker-in-Docker:

```bash
# Start all infrastructure services
docker-compose up -d postgres mongodb redis docker-dind

# Verify services are running
docker-compose ps

# Expected output:
# NAME                COMMAND                  SERVICE    STATUS
# postgres            "docker-entrypoint.s…"   postgres   Up
# mongodb             "docker-entrypoint.s…"   mongodb    Up
# redis               "docker-entrypoint.s…"   redis      Up
# docker-dind         "dockerd-entrypoint.…"   docker     Up
```

**docker-compose.yml** (infrastructure services):
```yaml
version: '3.9'

services:
  postgres:
    image: postgres:15-alpine
    container_name: crewai-postgres-dev
    environment:
      POSTGRES_DB: crewai_dev
      POSTGRES_USER: crewai
      POSTGRES_PASSWORD: crewai_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U crewai"]
      interval: 10s
      timeout: 5s
      retries: 5

  mongodb:
    image: mongo:6
    container_name: crewai-mongodb-dev
    environment:
      MONGO_INITDB_ROOT_USERNAME: crewai
      MONGO_INITDB_ROOT_PASSWORD: crewai_password
      MONGO_INITDB_DATABASE: crewai_dev
    ports:
      - "27017:27017"
    volumes:
      - mongodb_data:/data/db
    healthcheck:
      test: ["CMD", "mongo", "--eval", "db.adminCommand('ping')"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: crewai-redis-dev
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  docker-dind:
    image: docker:24-dind
    container_name: crewai-docker-dind-dev
    privileged: true
    environment:
      DOCKER_TLS_CERTDIR: ""
    ports:
      - "2375:2375"
    volumes:
      - docker_data:/var/lib/docker

volumes:
  postgres_data:
  mongodb_data:
  redis_data:
  docker_data:
```

### 4. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run database migrations
alembic upgrade head

# Create initial tenant and admin user (optional)
python scripts/create_initial_tenant.py

# Start backend server
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Backend will be available at http://localhost:8000
# API docs at http://localhost:8000/docs
```

**Backend scripts/create_initial_tenant.py:**
```python
"""Create initial tenant for development."""

import asyncio
from src.db import AsyncSessionLocal
from src.services.tenant_service import TenantService

async def main():
    async with AsyncSessionLocal() as db:
        tenant_service = TenantService(db)

        tenant = await tenant_service.create_tenant(
            name="Development Tenant",
            slug="dev-tenant",
            admin_email="admin@dev.local",
            admin_password="admin123"
        )

        print(f"✅ Created tenant: {tenant.name}")
        print(f"   Slug: {tenant.slug}")
        print(f"   Admin email: admin@dev.local")
        print(f"   Admin password: admin123")

if __name__ == "__main__":
    asyncio.run(main())
```

### 5. Celery Worker Setup (Separate Terminal)

```bash
cd backend
source venv/bin/activate

# Start Celery worker
celery -A src.workers.celery_app worker --loglevel=info

# Optional: Start Flower for monitoring
celery -A src.workers.celery_app flower --port=5555
# Access Flower UI at http://localhost:5555
```

### 6. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev

# Frontend will be available at http://localhost:3000
```

## Development Workflow

### Running Tests

**Backend Tests:**
```bash
cd backend
source venv/bin/activate

# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/integration/test_flow_execution.py -v

# Run tests matching pattern
pytest -k "test_multi_tenancy" -v

# View coverage report
open htmlcov/index.html
```

**Frontend Tests:**
```bash
cd frontend

# Run unit tests
npm test

# Run E2E tests (requires backend running)
npm run test:e2e

# Run E2E tests in UI mode
npm run test:e2e:ui
```

### Code Quality Checks

**Backend:**
```bash
cd backend

# Linting
flake8 src/ tests/

# Type checking
mypy src/

# Format code
black src/ tests/

# Sort imports
isort src/ tests/
```

**Frontend:**
```bash
cd frontend

# Linting
npm run lint

# Type checking
npm run type-check

# Format code
npm run format
```

### Database Management

**PostgreSQL:**
```bash
# Connect to database
psql -h localhost -U crewai -d crewai_dev

# List all schemas
\dn

# Switch to tenant schema
SET search_path TO tenant_abc123, public;

# List tables in current schema
\dt

# Describe table
\d agents

# Exit
\q
```

**Create Migration:**
```bash
cd backend

# Auto-generate migration
alembic revision --autogenerate -m "add_new_field_to_agent"

# Review migration file in alembic/versions/

# Apply migration
alembic upgrade head

# Rollback one version
alembic downgrade -1
```

**MongoDB:**
```bash
# Connect to MongoDB
mongosh "mongodb://crewai:crewai_password@localhost:27017/crewai_dev?authSource=admin"

# List collections
show collections

# Query execution logs
db.execution_logs_<tenant_id>.find().limit(10).pretty()

# Count documents
db.execution_logs_<tenant_id>.countDocuments()

# Exit
exit
```

**Redis:**
```bash
# Connect to Redis
redis-cli

# List all keys
KEYS *

# Get value
GET key_name

# View cached data
HGETALL session:user_id

# Monitor commands in real-time
MONITOR

# Clear all data (caution!)
FLUSHALL

# Exit
exit
```

### API Testing

**Using cURL:**
```bash
# Register tenant
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Password123!",
    "tenant_name": "Test Tenant",
    "tenant_slug": "test-tenant"
  }'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=Password123!"

# Save token from response
export TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# Create agent
curl -X POST http://localhost:8000/api/v1/agents \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Research Agent",
    "role": "researcher",
    "goal": "Research and analyze information",
    "backstory": "Expert researcher with years of experience"
  }'
```

**Using Postman:**
1. Import OpenAPI spec from `http://localhost:8000/openapi.json`
2. Create environment with `base_url=http://localhost:8000`
3. Use collection runner for automated testing

### Debugging

**Backend Debugging (VS Code):**

Create `.vscode/launch.json`:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "src.main:app",
        "--reload",
        "--host", "0.0.0.0",
        "--port", "8000"
      ],
      "jinja": true,
      "justMyCode": false,
      "env": {
        "PYTHONPATH": "${workspaceFolder}/backend"
      }
    },
    {
      "name": "Python: Pytest",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": [
        "-v",
        "-s",
        "${file}"
      ],
      "console": "integratedTerminal",
      "justMyCode": false
    }
  ]
}
```

**Frontend Debugging (VS Code):**

Create `.vscode/launch.json`:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Next.js: debug client-side",
      "type": "chrome",
      "request": "launch",
      "url": "http://localhost:3000",
      "webRoot": "${workspaceFolder}/frontend"
    },
    {
      "name": "Next.js: debug server-side",
      "type": "node",
      "request": "launch",
      "runtimeExecutable": "npm",
      "runtimeArgs": ["run", "dev"],
      "cwd": "${workspaceFolder}/frontend",
      "console": "integratedTerminal"
    }
  ]
}
```

### Hot Reloading

**Backend:**
- FastAPI's `--reload` flag watches for file changes
- Automatic restart on code modifications
- Environment variable changes require manual restart

**Frontend:**
- Next.js dev server auto-reloads on changes
- Fast Refresh preserves component state
- CSS changes apply instantly

## Common Development Tasks

### Adding a New API Endpoint

1. **Define Pydantic schema:**
```python
# backend/src/schemas/my_resource.py

from pydantic import BaseModel, Field

class MyResourceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None

class MyResourceResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    created_at: datetime

    class Config:
        from_attributes = True
```

2. **Create SQLAlchemy model:**
```python
# backend/src/models/my_resource.py

from sqlalchemy import Column, String, Text
from sqlalchemy.dialects.postgresql import UUID
from src.models import Base

class MyResource(Base):
    __tablename__ = "my_resources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
```

3. **Create service:**
```python
# backend/src/services/my_resource_service.py

from sqlalchemy.ext.asyncio import AsyncSession
from src.models import MyResource

class MyResourceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, tenant_id: UUID, data: MyResourceCreate) -> MyResource:
        resource = MyResource(
            tenant_id=tenant_id,
            **data.dict()
        )
        self.db.add(resource)
        await self.db.commit()
        await self.db.refresh(resource)
        return resource
```

4. **Create router:**
```python
# backend/src/api/v1/my_resources.py

from fastapi import APIRouter, Depends
from src.schemas.my_resource import MyResourceCreate, MyResourceResponse
from src.services.my_resource_service import MyResourceService

router = APIRouter(prefix="/my-resources", tags=["my-resources"])

@router.post("", response_model=MyResourceResponse)
async def create_my_resource(
    data: MyResourceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = MyResourceService(db)
    resource = await service.create(current_user.tenant_id, data)
    return resource
```

5. **Register router:**
```python
# backend/src/api/v1/__init__.py

from src.api.v1 import my_resources

app.include_router(my_resources.router, prefix="/api/v1")
```

6. **Create migration:**
```bash
alembic revision --autogenerate -m "add_my_resource_table"
alembic upgrade head
```

### Adding a New Frontend Page

1. **Create page component:**
```typescript
// frontend/app/my-feature/page.tsx

'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';

export default function MyFeaturePage() {
  const [data, setData] = useState(null);

  return (
    <div className="container mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">My Feature</h1>
      {/* Your component content */}
    </div>
  );
}
```

2. **Create API client:**
```typescript
// frontend/lib/api/my-feature.ts

import { apiClient } from './client';

export interface MyResource {
  id: string;
  name: string;
  description?: string;
}

export const myResourceApi = {
  async list(): Promise<MyResource[]> {
    const response = await apiClient.get('/my-resources');
    return response.data;
  },

  async create(data: { name: string; description?: string }): Promise<MyResource> {
    const response = await apiClient.post('/my-resources', data);
    return response.data;
  }
};
```

3. **Add navigation link:**
```typescript
// frontend/components/layout/sidebar.tsx

const navItems = [
  { href: '/dashboard', label: 'Dashboard', icon: Home },
  { href: '/my-feature', label: 'My Feature', icon: Star },
  // ...
];
```

## Troubleshooting

### Backend won't start

**Error:** `psycopg2.OperationalError: could not connect to server`

**Solution:**
```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# Restart PostgreSQL
docker-compose restart postgres

# Check logs
docker-compose logs postgres
```

**Error:** `alembic.util.exc.CommandError: Can't locate revision identified by 'abc123'`

**Solution:**
```bash
# Reset alembic version
alembic stamp head

# Or downgrade to base and re-migrate
alembic downgrade base
alembic upgrade head
```

### Frontend won't start

**Error:** `Error: Cannot find module 'next'`

**Solution:**
```bash
# Delete node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

**Error:** `CORS policy: No 'Access-Control-Allow-Origin' header`

**Solution:**
```python
# Check backend CORS configuration
# Ensure frontend URL is in CORS_ORIGINS
CORS_ORIGINS=http://localhost:3000
```

### Tests failing

**Error:** `pytest: No such file or directory`

**Solution:**
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dev dependencies
pip install -r requirements-dev.txt
```

## VS Code Extensions

Recommended extensions for optimal development experience:

**Python:**
- Python (Microsoft)
- Pylance
- Python Test Explorer
- autoDocstring

**JavaScript/TypeScript:**
- ESLint
- Prettier
- TypeScript + JavaScript
- Tailwind CSS IntelliSense

**General:**
- GitLens
- Docker
- Thunder Client (API testing)
- Error Lens

## Next Steps

Now that you have the development environment set up:

1. [Create Your First Flow](./creating-flows.md)
2. [Add Custom Tools](./adding-tools.md)
3. [Deploy to Kubernetes](./deploying-k8s.md)
4. Review [System Architecture](../architecture/system-overview.md)
5. Understand [Multi-Tenancy](../architecture/multi-tenancy.md)
