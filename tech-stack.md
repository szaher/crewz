# Dynamic CrewAI Orchestration Platform - Tech Stack Summary

## 🏗️ Architecture Overview

The system is a **multi-tenant, cloud-native platform** for orchestrating AI agent workflows with a visual flow editor. It follows a **microservices architecture** with separate frontend, backend, and infrastructure layers.

---

## 🎨 Frontend Stack

### **Next.js 14** (App Router)
- **Purpose**: React framework for the web application
- **Usage**: Server-side rendering, file-based routing, API routes
- **Location**: `/frontend`

### **React 18** + **TypeScript**
- **Purpose**: UI component library with type safety
- **Usage**: Building interactive components, state management
- **Why**: Type-safe development, better DX, component reusability

### **React Flow 11**
- **Purpose**: Visual flow editor library
- **Usage**: Drag-and-drop workflow builder, node-based UI
- **Features**: Custom nodes (Agent, Tool, LLM, Condition), edge connections, canvas controls
- **Location**: `/frontend/src/components/flows/`

### **TailwindCSS 3**
- **Purpose**: Utility-first CSS framework
- **Usage**: Styling components, responsive design
- **Why**: Rapid UI development, consistent design system

### **Zustand 4**
- **Purpose**: Lightweight state management
- **Usage**: Global state for flows, agents, crews, tools, user auth
- **Features**: Persistence to localStorage, no boilerplate
- **Location**: `/frontend/src/lib/store.ts`

### **Socket.IO Client**
- **Purpose**: WebSocket client for real-time communication
- **Usage**: Chat streaming, execution event updates
- **Features**: Automatic reconnection, fallback to polling

### **EventSource (SSE)**
- **Purpose**: Server-Sent Events for streaming
- **Usage**: Real-time flow execution logs, monitoring
- **Location**: `/frontend/src/lib/sse-client.ts`

---

## ⚙️ Backend Stack

### **FastAPI** (Python 3.11+)
- **Purpose**: Modern async web framework
- **Usage**: REST API endpoints, WebSocket support
- **Why**: Async/await, automatic OpenAPI docs, Pydantic validation
- **Location**: `/backend/src/main.py`, `/backend/src/api/v1/`

### **Pydantic V2**
- **Purpose**: Data validation and serialization
- **Usage**: Request/response schemas, configuration management
- **Features**: Type hints, automatic validation, JSON schema generation
- **Location**: `/backend/src/schemas/`

### **SQLAlchemy 2.0**
- **Purpose**: SQL ORM for relational data
- **Usage**: Database models, relationships, queries
- **Features**: Async support, schema-per-tenant (multi-tenancy)
- **Location**: `/backend/src/models/`

### **Alembic**
- **Purpose**: Database migration tool
- **Usage**: Version control for database schema changes
- **Location**: `/backend/alembic/versions/`

### **CrewAI SDK**
- **Purpose**: AI agent orchestration framework
- **Usage**: Creating agents, crews, tasks
- **How**: Factory pattern converts DB models → CrewAI objects
- **Location**: `/backend/src/crewai/`

### **LiteLLM**
- **Purpose**: Universal LLM API abstraction
- **Usage**: Multi-provider support (OpenAI, Anthropic, Ollama, vLLM)
- **Features**: Provider failover, streaming, cost tracking
- **Why**: Single interface for multiple LLM providers
- **Location**: `/backend/src/services/llm_service.py`

### **Docker SDK for Python**
- **Purpose**: Docker container management
- **Usage**: Secure tool execution in isolated containers
- **Features**: Resource limits, network isolation, read-only filesystem
- **Security**: Rootless containers, Sysbox runtime
- **Location**: `/backend/src/services/docker_service.py`

---

## 🗄️ Data Layer

### **PostgreSQL 15**
- **Purpose**: Primary relational database
- **Usage**: Structured data (users, tenants, flows, agents, crews, tools, executions)
- **Multi-tenancy**: Schema-per-tenant approach (dynamic `search_path`)
- **Tables**: 9 main entities (Tenant, User, Agent, Crew, Flow, Tool, Execution, ChatSession, LLMProvider)

### **MongoDB 6.0**
- **Purpose**: Document store for unstructured data
- **Usage**:
  - Execution logs (high-volume, time-series)
  - Chat message history
  - Agent reasoning traces
- **Why**: Schema flexibility, horizontal scaling

### **Redis 7**
- **Purpose**: In-memory cache and message broker
- **Usage**:
  - Session storage
  - Real-time event streaming (execution events)
  - Task queue (Celery backend)
  - Rate limiting

---

## 🔐 Security & Auth

### **JWT (JSON Web Tokens)**
- **Purpose**: Stateless authentication
- **Usage**: User authentication, tenant context
- **Implementation**: Custom middleware extracts user + tenant from token
- **Location**: `/backend/src/utils/jwt.py`, `/backend/src/api/middleware/auth.py`

### **RBAC (Role-Based Access Control)**
- **Purpose**: Permission management
- **Roles**: admin, member, viewer
- **Usage**: Endpoint-level access control
- **Location**: `/backend/src/utils/rbac.py`

### **AES-256-GCM Encryption**
- **Purpose**: API key encryption at rest
- **Usage**: Encrypting LLM provider credentials
- **Location**: `/backend/src/utils/encryption.py`

### **Rootless Docker + Sysbox**
- **Purpose**: Container security
- **Usage**: Tool execution in unprivileged containers
- **Features**: No root access, network isolation, resource limits

---

## 🚀 Infrastructure & DevOps

### **Docker Compose**
- **Purpose**: Local development environment
- **Services**: Frontend, Backend, PostgreSQL, MongoDB, Redis
- **Location**: `/docker-compose.yml`

### **Kubernetes (K8s)**
- **Purpose**: Production orchestration
- **Components**:
  - Deployments for backend/frontend
  - StatefulSets for databases
  - Services and Ingress for routing
  - Kustomize for environment overlays (local/staging/prod)
- **Location**: `/infra/kubernetes/`

### **KinD (Kubernetes in Docker)**
- **Purpose**: Local K8s cluster for testing
- **Location**: `/infra/kind/kind-config.yaml`

### **Helm**
- **Purpose**: Package manager for K8s
- **Charts**: PostgreSQL, MongoDB, Redis
- **Location**: `/infra/kubernetes/overlays/local/`

---

## 📊 Observability

### **OpenTelemetry (OTEL)**
- **Purpose**: Distributed tracing and metrics
- **Usage**: Request tracing across services
- **Location**: `/backend/src/utils/observability.py`

### **Prometheus**
- **Purpose**: Metrics collection and alerting
- **Metrics**: API latency, execution duration, error rates
- **Location**: `/infra/observability/prometheus.yaml`

### **Grafana**
- **Purpose**: Metrics visualization
- **Dashboards**: System health, execution metrics, resource usage
- **Location**: `/infra/observability/grafana-dashboards/`

---

## 🧪 Testing Stack

### **pytest** + **pytest-asyncio**
- **Purpose**: Backend unit and integration tests
- **Usage**: Testing services, validators, executors
- **Location**: `/backend/tests/unit/`, `/backend/tests/integration/`

### **Playwright**
- **Purpose**: Frontend E2E testing
- **Usage**: Testing user workflows (registration → flow creation → execution)
- **Location**: `/frontend/tests/e2e/`

### **Locust**
- **Purpose**: Performance/load testing
- **Usage**: Testing concurrent flow executions, API throughput
- **Location**: `/backend/tests/performance/`

---

## 🔄 CI/CD

### **GitHub Actions**
- **Purpose**: Automated testing and deployment
- **Workflows**:
  - Backend tests (pytest)
  - Frontend tests (Playwright)
  - Docker image builds
  - K8s deployment
- **Location**: `.github/workflows/`

---

## 🌊 Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      USER BROWSER                            │
│  Next.js 14 + React 18 + TailwindCSS + React Flow          │
└──────────────┬──────────────────────────────┬───────────────┘
               │                               │
         REST API                        WebSocket/SSE
               │                               │
┌──────────────┴───────────────────────────────┴───────────────┐
│                    FastAPI Backend                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   Auth       │  │   Flows      │  │  Executions  │       │
│  │ Middleware   │  │   Service    │  │   Service    │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  CrewAI      │  │   Docker     │  │     LLM      │       │
│  │  Factory     │  │   Service    │  │   Service    │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└──────────┬─────────────┬─────────────────┬──────────────────┘
           │             │                 │
    ┌──────┴──────┐  ┌──┴────┐     ┌──────┴──────┐
    │ PostgreSQL  │  │ Redis │     │  MongoDB    │
    │ (Tenants,   │  │(Cache)│     │   (Logs,    │
    │  Flows,     │  └───────┘     │    Chat)    │
    │  Agents)    │                └─────────────┘
    └─────────────┘
           │
    ┌──────┴──────┐
    │   CrewAI    │──→ LiteLLM ──→ OpenAI/Anthropic/Ollama
    │   Agents    │
    └─────────────┘
           │
    ┌──────┴──────┐
    │   Docker    │──→ Isolated tool containers
    │ Containers  │
    └─────────────┘
```

---

## 🎯 Key Design Patterns

### **1. Multi-Tenancy**
- **Pattern**: Schema-per-tenant in PostgreSQL
- **Implementation**: Middleware sets `search_path` per request
- **Isolation**: Each tenant has isolated database schema

### **2. Factory Pattern**
- **Usage**: Converting DB models → CrewAI objects
- **Classes**: `AgentFactory`, `CrewFactory`, `ToolAdapter`
- **Why**: Decouples storage from execution logic

### **3. Repository Pattern**
- **Usage**: Service layer abstracts data access
- **Classes**: `FlowService`, `AgentService`, `ToolService`
- **Why**: Testability, separation of concerns

### **4. Event-Driven Architecture**
- **Usage**: Execution events published to Redis
- **Subscribers**: Frontend (SSE), logging, metrics
- **Why**: Real-time updates, decoupled components

### **5. DAG Execution**
- **Usage**: Topological sort for flow node execution
- **Implementation**: `FlowValidator`, `FlowExecutor`
- **Why**: Correct dependency resolution, parallel execution

---

## 📦 Deployment Model

### **Development**
```
Docker Compose → All services in containers → localhost:3001 (frontend) + localhost:8000 (backend)
```

### **Production**
```
Kubernetes Cluster
├── Frontend (3 replicas)
├── Backend (5 replicas)
├── PostgreSQL (StatefulSet)
├── MongoDB (StatefulSet)
├── Redis (StatefulSet)
└── Docker-in-Docker (Sysbox for secure tool execution)
```

---

## 🔑 Key Differentiators

1. **Visual Flow Editor**: React Flow for no-code agent orchestration
2. **Multi-LLM Support**: LiteLLM for provider flexibility
3. **Secure Tool Execution**: Rootless Docker containers
4. **Multi-Tenancy**: Full data isolation per customer
5. **Real-time Updates**: WebSocket + SSE for live execution monitoring
6. **Hybrid Storage**: PostgreSQL (structured) + MongoDB (unstructured)

This tech stack provides a **scalable, secure, and developer-friendly** platform for building and executing AI agent workflows! 🚀
