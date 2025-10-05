# Implementation Plan: Dynamic CrewAI Orchestration Platform

**Branch**: `001-specify-project-title` | **Date**: 2025-10-05 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-specify-project-title/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path
   → ✓ Spec found at /specs/001-specify-project-title/spec.md
2. Fill Technical Context (scan for NEEDS CLARIFICATION)
   → ✓ Project type: CrewAI UI Project (web application)
   → ✓ Tech stack determined from user requirements
3. Fill the Constitution Check section based on the constitution document
   → ✓ All four principles evaluated
4. Evaluate Constitution Check section below
   → ✓ All checks pass - platform aligns with constitution
   → Progress Tracking: Initial Constitution Check COMPLETE
5. Execute Phase 0 → research.md
   → ✓ Research completed for multi-tenant architecture, Docker-in-Docker, LLM integration
6. Execute Phase 1 → contracts, data-model.md, quickstart.md, CLAUDE.md
   → ✓ Data model with 11 core entities
   → ✓ API contracts for all major endpoints
   → ✓ Quickstart guide for local development
7. Re-evaluate Constitution Check section
   → ✓ Design maintains constitutional compliance
   → Progress Tracking: Post-Design Constitution Check COMPLETE
8. Plan Phase 2 → Describe task generation approach
   → ✓ Task breakdown strategy defined
9. STOP - Ready for /tasks command
```

## Summary

Build a full-stack, multi-tenant platform for visual CrewAI workflow orchestration. Users create and manage AI "crews" (agent teams) and "flows" (visual workflows) through a drag-and-drop interface. The platform supports:

- **Visual flow building**: React-based drag-and-drop editor for composing agents, tools, and LLM nodes
- **Secure multi-tenancy**: Per-tenant database schemas with JWT authentication and RBAC
- **Isolated execution**: Rootless Docker containers for user-defined tool execution
- **LLM abstraction**: Backend-centralized access to multiple LLM providers (OpenAI, Anthropic, local models)
- **Real-time monitoring**: Live execution tracking, chat interface, and comprehensive logging
- **Kubernetes deployment**: Production-ready with KinD for local development

**Technical Approach**: FastAPI backend with PostgreSQL/MongoDB, Next.js frontend with React Flow, Docker-in-Docker execution runtime, Kubernetes orchestration, OpenTelemetry observability.

## Technical Context

**Language/Version**:
- Backend: Python 3.11+ (FastAPI)
- Frontend: TypeScript 5.0+ (Next.js 14, React 18)
- Infrastructure: Bash/YAML (Kubernetes manifests)

**Primary Dependencies**:
- Backend: FastAPI 0.104+, SQLAlchemy 2.0, Pydantic 2.0, CrewAI SDK, Docker SDK for Python
- Frontend: Next.js 14, React Flow 11, TailwindCSS 3, Zustand 4, Socket.IO client
- Database: PostgreSQL 15+, MongoDB 6.0+
- Infrastructure: Docker 24+, Kubernetes 1.28+, KinD 0.20+
- Observability: OpenTelemetry, Prometheus, Grafana

**Storage**:
- Primary: PostgreSQL 15 (tenant schemas, users, flows, executions)
- Secondary: MongoDB 6 (execution logs, chat history, audit logs)
- Object: S3-compatible storage for flow exports and artifacts

**Testing**:
- Backend: pytest 7.4+, pytest-asyncio, httpx (async client testing)
- Frontend: Playwright 1.40+, Jest 29, React Testing Library
- Integration: Docker Compose test environments
- Load: Locust for API performance testing

**Target Platform**:
- Development: Linux/macOS with Docker Desktop or Podman, KinD cluster
- Production: Kubernetes 1.28+ (any CNCF-certified distribution)
- Container Runtime: Docker 24+ with rootless mode support

**Project Type**: CrewAI UI Project (full-stack web application)

**Performance Goals**:
- API response time: p95 < 200ms for CRUD operations
- Flow execution latency: p95 < 5s for simple flows (3-5 nodes)
- LLM streaming: First token < 2s, sustained 20+ tokens/sec
- Concurrent executions: 100+ flows per tenant simultaneously
- UI responsiveness: 60 FPS canvas rendering with 100+ nodes

**Constraints**:
- Multi-tenant isolation: Zero data leakage between tenants (enforced at DB schema level)
- Container security: All user code runs in rootless containers with resource limits
- LLM centralization: Frontend must never directly access LLM API keys
- Execution timeout: Configurable per flow, default 1 hour maximum
- Storage quotas: Per-tenant limits enforced (default: 100 flows, 10GB storage, 1000 executions/day)

**Scale/Scope**:
- Tenants: 1000+ organizations on shared infrastructure
- Users: 10,000+ concurrent users across all tenants
- Flows: 100,000+ flow definitions stored
- Executions: 1M+ flow executions per month
- Codebase: ~50K LOC backend, ~30K LOC frontend, ~10K LOC infrastructure

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Principle I: Visual & Composable**
- [x] Does this feature support graphical UI editing without code changes?
  - Yes: React Flow-based drag-and-drop editor for all flow components
- [x] Are components drag-and-drop or schema-driven?
  - Yes: Node-based editor with schema-driven properties panels
- [x] Is composition intuitive for non-technical users?
  - Yes: Visual connections, real-time validation, template library

**Principle II: Seamless & Transparent UX**
- [x] Are agent reasoning steps visible to users?
  - Yes: Real-time execution timeline shows agent decision points
- [x] Do tool invocations show structured inputs/outputs in real-time?
  - Yes: Live logs panel displays tool I/O with syntax highlighting
- [x] Is role distinction clear (Agent vs Crew vs User)?
  - Yes: Color-coded nodes, distinct UI sections, role badges

**Principle III: Modular & Extensible Architecture**
- [x] Can new tools be added in under 30 minutes?
  - Yes: Tool registration API with OpenAPI schema upload
- [x] Are frontend/backend decoupled with well-defined APIs?
  - Yes: OpenAPI 3.0 spec, GraphQL for real-time, versioned endpoints
- [x] Are extension points documented with examples?
  - Yes: Plugin architecture docs, example tools in `/docs/tools`

**Principle IV: Spec-First Development**
- [x] Are schemas defined in `/specs` before implementation?
  - Yes: This plan generates OpenAPI schemas in Phase 1
- [x] Are API contracts documented (OpenAPI/GraphQL)?
  - Yes: Full OpenAPI 3.0 spec generated from contracts
- [x] Is documentation updated before code merge?
  - Yes: Docs are deliverables in each phase

*All constitutional checks pass. No complexity justification needed.*

## Project Structure

### Documentation (this feature)
```
specs/001-specify-project-title/
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output (/plan command)
├── data-model.md        # Phase 1 output (/plan command)
├── quickstart.md        # Phase 1 output (/plan command)
├── contracts/           # Phase 1 output (/plan command)
│   ├── openapi.yaml     # Complete OpenAPI 3.0 specification
│   ├── auth.yaml        # Auth endpoints contract
│   ├── tenants.yaml     # Tenant management contract
│   ├── flows.yaml       # Flow CRUD contract
│   ├── agents.yaml      # Agent/crew management contract
│   ├── tools.yaml       # Tool registration contract
│   ├── executions.yaml  # Flow execution contract
│   └── chat.yaml        # Chat interface contract
└── tasks.md             # Phase 2 output (/tasks command - NOT created by /plan)
```

### Source Code (repository root)
```
/frontend
├── src/
│   ├── components/
│   │   ├── flows/              # Flow editor components
│   │   │   ├── FlowCanvas.tsx
│   │   │   ├── NodePalette.tsx
│   │   │   ├── PropertyPanel.tsx
│   │   │   └── nodes/          # Custom node types
│   │   ├── crews/              # Crew manager components
│   │   │   ├── CrewBuilder.tsx
│   │   │   ├── AgentCard.tsx
│   │   │   └── CrewTemplates.tsx
│   │   ├── chat/               # Chat interface components
│   │   │   ├── ChatWindow.tsx
│   │   │   ├── MessageList.tsx
│   │   │   └── ExecutionTrace.tsx
│   │   ├── tools/              # Tool integration UI
│   │   │   ├── ToolRegistry.tsx
│   │   │   ├── ToolForm.tsx
│   │   │   └── ToolInvocation.tsx
│   │   ├── auth/               # Authentication UI
│   │   └── shared/             # Shared components
│   ├── pages/
│   │   ├── api/                # Next.js API routes (BFF pattern)
│   │   ├── flows/
│   │   ├── crews/
│   │   ├── chat/
│   │   └── dashboard/
│   ├── lib/
│   │   ├── api-client.ts       # Backend API client
│   │   ├── websocket.ts        # Real-time connection
│   │   └── store.ts            # Zustand state management
│   └── types/                  # TypeScript definitions
└── tests/
    ├── e2e/                    # Playwright tests
    └── unit/                   # Jest tests

/backend
├── src/
│   ├── api/                    # REST/GraphQL endpoints
│   │   ├── v1/
│   │   │   ├── auth.py
│   │   │   ├── tenants.py
│   │   │   ├── flows.py
│   │   │   ├── agents.py
│   │   │   ├── tools.py
│   │   │   ├── executions.py
│   │   │   └── chat.py
│   │   └── middleware/         # CORS, auth, tenant context
│   ├── models/                 # SQLAlchemy ORM models
│   │   ├── tenant.py
│   │   ├── user.py
│   │   ├── agent.py
│   │   ├── crew.py
│   │   ├── flow.py
│   │   ├── tool.py
│   │   ├── execution.py
│   │   ├── chat_session.py
│   │   ├── llm_provider.py
│   │   └── audit_log.py
│   ├── services/               # Business logic
│   │   ├── auth_service.py
│   │   ├── tenant_service.py
│   │   ├── flow_service.py
│   │   ├── execution_service.py
│   │   ├── llm_service.py      # LLM routing and abstraction
│   │   ├── tool_service.py     # Tool execution orchestration
│   │   └── docker_service.py   # Docker-in-Docker management
│   ├── crewai/                 # CrewAI SDK integration
│   │   ├── agent_factory.py
│   │   ├── crew_factory.py
│   │   ├── flow_executor.py
│   │   └── tool_adapter.py
│   ├── db/
│   │   ├── postgres.py         # PostgreSQL connection
│   │   ├── mongodb.py          # MongoDB connection
│   │   └── migrations/         # Alembic migrations
│   ├── schemas/                # Pydantic request/response models
│   └── utils/
│       ├── jwt.py
│       ├── rbac.py
│       └── observability.py
└── tests/
    ├── contract/               # Contract tests for each endpoint
    ├── integration/            # Integration tests
    └── unit/                   # Unit tests

/infra
├── kubernetes/
│   ├── base/                   # Base Kubernetes manifests
│   │   ├── backend-deployment.yaml
│   │   ├── frontend-deployment.yaml
│   │   ├── postgres-statefulset.yaml
│   │   ├── mongodb-statefulset.yaml
│   │   ├── docker-dind-deployment.yaml
│   │   └── services.yaml
│   ├── overlays/
│   │   ├── local/              # KinD configuration
│   │   ├── staging/
│   │   └── production/
│   └── helm/                   # Helm chart
│       ├── Chart.yaml
│       ├── values.yaml
│       └── templates/
├── docker/
│   ├── backend.Dockerfile
│   ├── frontend.Dockerfile
│   └── tool-executor.Dockerfile
├── kind/
│   └── kind-config.yaml
└── observability/
    ├── prometheus.yaml
    ├── grafana-dashboards/
    └── otel-collector.yaml

/specs                          # OpenAPI/GraphQL schemas, flow/crew schemas
/docs                           # Architecture, guides, flow examples
├── architecture/
│   ├── system-overview.md
│   ├── multi-tenancy.md
│   ├── execution-model.md
│   └── security-model.md
├── guides/
│   ├── local-development.md
│   ├── creating-flows.md
│   ├── adding-tools.md
│   └── deploying-k8s.md
└── flows/                      # Example flow configurations
```

**Structure Decision**: Selected **Option 3: CrewAI UI Project** structure. This is a full-stack web application with distinct frontend and backend services, plus infrastructure-as-code. The multi-tenant, containerized architecture requires clear separation between user-facing UI (`/frontend`), API/execution layer (`/backend`), and deployment configurations (`/infra`). Additional `/specs` and `/docs` directories support the spec-first development principle.

## Phase 0: Outline & Research

**Research Areas Identified**:

1. **Multi-Tenant Database Schema Isolation (PostgreSQL)**
   - Decision needed: Schema-per-tenant vs table-per-tenant vs database-per-tenant
   - Performance implications of schema switching
   - Connection pooling strategies for multi-tenancy

2. **Docker-in-Docker Security & Rootless Execution**
   - Rootless Docker configuration in Kubernetes
   - Resource limits enforcement (CPU, memory, network)
   - Seccomp profiles and AppArmor policies for container sandboxing

3. **LLM Provider Abstraction Layer**
   - Unified interface for OpenAI, Anthropic, local models (Ollama, vLLM)
   - Streaming response handling across providers
   - Retry logic and failover strategies

4. **Real-Time Execution Monitoring**
   - WebSocket vs Server-Sent Events for execution updates
   - Scaling real-time connections in Kubernetes
   - Message queue integration (Redis Streams vs RabbitMQ)

5. **CrewAI SDK Integration Patterns**
   - Dynamic agent instantiation from database configurations
   - Custom tool registration with CrewAI
   - Flow execution state management

6. **Kubernetes StatefulSet for Databases**
   - PostgreSQL operator vs manual StatefulSet
   - MongoDB replica set configuration
   - Persistent volume provisioning in KinD

**Research Output** → `research.md`

## Phase 1: Design & Contracts
*Prerequisites: research.md complete*

### 1. Data Model (`data-model.md`)

**Core Entities** (from spec.md):

**Tenant**
- Fields: `id`, `name`, `slug`, `db_schema`, `created_at`, `settings`, `quotas`, `billing_info`
- Relationships: has_many Users, has_many Flows, has_many Agents, has_many LLMProviders
- Validation: Unique slug, schema name must be valid PostgreSQL identifier
- State: active, suspended, deleted

**User**
- Fields: `id`, `tenant_id`, `email`, `password_hash`, `role`, `created_at`, `last_login`, `preferences`
- Relationships: belongs_to Tenant, has_many Flows (created), has_many ChatSessions
- Validation: Unique email per tenant, valid email format, role enum (admin, editor, viewer, executor)
- State: active, invited, disabled

**Agent**
- Fields: `id`, `tenant_id`, `name`, `description`, `system_prompt`, `llm_provider_id`, `config`, `version`
- Relationships: belongs_to Tenant, belongs_to LLMProvider, belongs_to_many Crews
- Validation: Non-empty name, valid JSON config
- State: draft, active, archived

**Crew**
- Fields: `id`, `tenant_id`, `name`, `description`, `agent_ids`, `collaboration_pattern`, `config`
- Relationships: belongs_to Tenant, has_many Agents (through join table)
- Validation: At least one agent, valid collaboration pattern enum
- State: draft, active, archived

**Flow**
- Fields: `id`, `tenant_id`, `user_id`, `name`, `description`, `nodes`, `edges`, `input_schema`, `output_schema`, `version`
- Relationships: belongs_to Tenant, belongs_to User, has_many Executions
- Validation: Valid JSON for nodes/edges, DAG validation (no cycles unless intentional loops)
- State: draft, published, archived

**Tool**
- Fields: `id`, `tenant_id`, `name`, `description`, `input_schema`, `output_schema`, `execution_config`, `credentials`
- Relationships: belongs_to Tenant
- Validation: Valid JSON schema for inputs/outputs, credential encryption
- State: active, disabled

**Execution**
- Fields: `id`, `flow_id`, `user_id`, `status`, `start_time`, `end_time`, `inputs`, `outputs`, `logs_ref`
- Relationships: belongs_to Flow, belongs_to User, has_many ExecutionNodes
- Validation: Valid status enum (queued, running, succeeded, failed, cancelled, timeout)
- State: queued → running → terminal (succeeded/failed/cancelled/timeout)

**ExecutionNode** (MongoDB)
- Fields: `execution_id`, `node_id`, `status`, `start_time`, `end_time`, `inputs`, `outputs`, `logs`, `metadata`
- Stored in MongoDB for high write throughput

**ChatSession**
- Fields: `id`, `tenant_id`, `user_id`, `crew_id`, `attached_flow_id`, `created_at`, `messages_ref`
- Relationships: belongs_to User, belongs_to Crew (optional), references Flow (optional)
- Messages stored in MongoDB

**LLMProvider**
- Fields: `id`, `tenant_id`, `name`, `provider_type`, `api_credentials`, `config`, `is_active`
- Relationships: belongs_to Tenant, has_many Agents
- Validation: Encrypted credentials, valid provider_type enum (openai, anthropic, ollama, vllm)

**AuditLog** (MongoDB)
- Fields: `timestamp`, `tenant_id`, `user_id`, `action`, `resource_type`, `resource_id`, `metadata`, `ip_address`
- Indexed by tenant_id, timestamp, action

**ResourceQuota**
- Fields: `tenant_id`, `max_flows`, `max_executions_per_day`, `max_storage_gb`, `max_llm_tokens_per_day`
- Relationships: belongs_to Tenant (embedded in Tenant model)

### 2. API Contracts (`contracts/`)

**Authentication Endpoints** (`auth.yaml`)
```yaml
/api/v1/auth/register:
  POST:
    summary: Register new tenant
    request: { email, password, tenant_name, tenant_slug }
    response: { tenant_id, user_id, access_token, refresh_token }

/api/v1/auth/login:
  POST:
    summary: User login
    request: { email, password }
    response: { access_token, refresh_token, user, tenant }

/api/v1/auth/refresh:
  POST:
    summary: Refresh access token
    request: { refresh_token }
    response: { access_token }

/api/v1/auth/logout:
  POST:
    summary: Invalidate tokens
```

**Flow Management** (`flows.yaml`)
```yaml
/api/v1/flows:
  GET:
    summary: List flows for current tenant
    query: { page, limit, status, created_by }
    response: { flows[], total, page_info }
  POST:
    summary: Create new flow
    request: { name, description, nodes, edges, input_schema, output_schema }
    response: { flow }

/api/v1/flows/{flow_id}:
  GET:
    summary: Get flow details
    response: { flow, versions[] }
  PUT:
    summary: Update flow
    request: { name?, description?, nodes?, edges? }
    response: { flow }
  DELETE:
    summary: Delete flow (soft delete)

/api/v1/flows/{flow_id}/execute:
  POST:
    summary: Execute flow
    request: { inputs, config? }
    response: { execution_id, status }

/api/v1/flows/{flow_id}/versions:
  GET:
    summary: List flow versions
```

**Execution Monitoring** (`executions.yaml`)
```yaml
/api/v1/executions/{execution_id}:
  GET:
    summary: Get execution status and logs
    response: { execution, nodes[], logs }

/api/v1/executions/{execution_id}/stream:
  GET:
    summary: SSE stream for real-time execution updates
    response: text/event-stream

/api/v1/executions/{execution_id}/cancel:
  POST:
    summary: Cancel running execution
```

**Agent/Crew Management** (`agents.yaml`)
```yaml
/api/v1/agents:
  GET, POST:
    summary: List/create agents

/api/v1/agents/{agent_id}:
  GET, PUT, DELETE

/api/v1/crews:
  GET, POST:
    summary: List/create crews

/api/v1/crews/{crew_id}:
  GET, PUT, DELETE

/api/v1/crews/{crew_id}/test:
  POST:
    summary: Test crew with sample input
```

**Tool Integration** (`tools.yaml`)
```yaml
/api/v1/tools:
  GET, POST:
    summary: List/register tools

/api/v1/tools/{tool_id}:
  GET, PUT, DELETE

/api/v1/tools/{tool_id}/validate:
  POST:
    summary: Validate tool schema and credentials
```

**Chat Interface** (`chat.yaml`)
```yaml
/api/v1/chat/sessions:
  GET, POST:
    summary: List/create chat sessions

/api/v1/chat/sessions/{session_id}/messages:
  POST:
    summary: Send message to crew
    request: { content, attached_flow_id? }
    response: { message_id }

/api/v1/chat/sessions/{session_id}/stream:
  GET:
    summary: WebSocket connection for chat
```

**Complete OpenAPI 3.0 spec** generated as `contracts/openapi.yaml`

### 3. Contract Tests

Generated in `/backend/tests/contract/`:
- `test_auth_contract.py`
- `test_flows_contract.py`
- `test_executions_contract.py`
- `test_agents_contract.py`
- `test_tools_contract.py`
- `test_chat_contract.py`

Each test file validates request/response schemas against OpenAPI spec.

### 4. Integration Test Scenarios (`quickstart.md`)

**Quickstart: Local Development Setup**

1. Prerequisites: Docker Desktop, Node.js 18+, Python 3.11+, kubectl, kind
2. Clone repository
3. Start KinD cluster: `kind create cluster --config infra/kind/kind-config.yaml`
4. Deploy infrastructure: `kubectl apply -k infra/kubernetes/overlays/local`
5. Run database migrations: `cd backend && alembic upgrade head`
6. Start backend: `cd backend && uvicorn src.main:app --reload`
7. Start frontend: `cd frontend && npm run dev`
8. Open http://localhost:3000

**Integration Test Flows**:
- User registration → tenant creation → first flow
- Flow creation → agent selection → tool addition → execution
- Chat session → crew interaction → flow attachment → response streaming
- Multi-user collaboration → flow sharing → permission enforcement

### 5. Agent File Update

Run: `.specify/scripts/bash/update-agent-context.sh claude`

**Output**: `CLAUDE.md` in repository root with:
- Active technologies: FastAPI, Next.js, PostgreSQL, MongoDB, Docker, Kubernetes
- Project structure: CrewAI UI Project layout
- Common commands: docker-compose up, kubectl apply, npm run dev, pytest
- Recent changes: Phase 1 design complete, contracts generated

## Phase 2: Task Planning Approach
*This section describes what the /tasks command will do - DO NOT execute during /plan*

**Task Generation Strategy**:

1. **Load task template** from `.specify/templates/tasks-template.md`

2. **Generate tasks from contracts**:
   - For each API endpoint in `contracts/*.yaml`:
     - Create contract test task (e.g., T004: Contract test POST /api/v1/flows)
     - Create endpoint implementation task (e.g., T020: Implement POST /api/v1/flows)

3. **Generate tasks from data model**:
   - For each entity in `data-model.md`:
     - Create model definition task (e.g., T015: Define Flow model with SQLAlchemy)
     - Create migration task (e.g., T016: Create Alembic migration for flows table)

4. **Generate tasks from user stories** (spec.md):
   - Acceptance scenario 1 → T050: Integration test for user registration flow
   - Acceptance scenario 2 → T051: Integration test for drag-and-drop flow editor
   - ... (one task per scenario)

5. **Generate infrastructure tasks**:
   - Docker image builds, Kubernetes manifests, Helm chart, CI/CD pipeline

**Ordering Strategy**:

- **Phase 3.1: Infrastructure Setup** (T001-T010)
  - KinD cluster, PostgreSQL/MongoDB StatefulSets, Docker-in-Docker deployment
  - All infrastructure tasks can run in parallel [P]

- **Phase 3.2: Specs & Database** (T011-T025)
  - Database models, migrations, contract tests
  - Models can be created in parallel [P], migrations are sequential

- **Phase 3.3: Core Backend Implementation** (T026-T080)
  - Services layer: auth, tenant, flow, execution, LLM, tool, docker services
  - API endpoints for each contract
  - Tests alongside implementation (relaxed TDD per new constitution)

- **Phase 3.4: Frontend Implementation** (T081-T120)
  - Flow editor, crew builder, chat interface, tool registry, auth UI
  - Playwright E2E tests for each user scenario

- **Phase 3.5: Integration & Polish** (T121-T140)
  - End-to-end integration tests
  - Performance testing with Locust
  - Observability setup (OpenTelemetry, Prometheus, Grafana)
  - Documentation completion

**Estimated Output**: 140+ numbered, ordered tasks in tasks.md

**Parallel Execution Opportunities**:
- All infrastructure provisioning tasks
- All model definition tasks
- Independent service implementations (auth, tenant, flow services can be developed concurrently)
- Independent frontend components (flow editor, chat UI, crew builder)
- Contract test generation

**Dependencies**:
- Infrastructure must complete before backend can deploy
- Database models must exist before services
- Services must exist before API endpoints
- API endpoints must work before frontend integration
- Core features must work before E2E tests

## Phase 3+: Future Implementation
*These phases are beyond the scope of the /plan command*

**Phase 3**: Task execution (/tasks command creates tasks.md with 140+ tasks)

**Phase 4**: Implementation (execute tasks.md following constitutional principles)
- Milestone 1 (Weeks 1-2): Infrastructure + auth foundation
- Milestone 2 (Weeks 3-5): Core backend (flows, agents, tools, executions)
- Milestone 3 (Weeks 6-8): Frontend (flow editor, crew builder)
- Milestone 4 (Weeks 9-10): Chat interface + LLM integration
- Milestone 5 (Weeks 11-12): Docker-in-Docker execution runtime
- Milestone 6 (Weeks 13-14): Integration testing + observability
- Milestone 7 (Weeks 15-16): Performance tuning + deployment automation

**Phase 5**: Validation (run tests, execute quickstart.md, performance validation)
- All contract tests passing
- All integration tests passing
- All E2E tests passing (10 user scenarios from spec)
- Load test: 100 concurrent flow executions
- Security audit: penetration testing, dependency scanning
- Documentation review: all guides executable

## Complexity Tracking
*No constitutional violations - all checks passed.*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | N/A | N/A |

## Progress Tracking

**Phase Status**:
- [x] Phase 0: Research complete (/plan command)
- [x] Phase 1: Design complete (/plan command)
- [x] Phase 2: Task planning complete (/plan command - describe approach only)
- [ ] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS
- [x] Post-Design Constitution Check: PASS
- [x] All NEEDS CLARIFICATION resolved (using suggested defaults from spec)
- [x] Complexity deviations documented (none)

**Timeline Estimate**:
- Phase 0 (Research): 1 week ✓
- Phase 1 (Design & Contracts): 1 week ✓
- Phase 2 (Task Planning): Complete ✓
- Phase 3 (Task Generation): /tasks command (1 hour)
- Phase 4 (Implementation): 16 weeks (4 months)
  - Milestone 1: 2 weeks
  - Milestone 2: 3 weeks
  - Milestone 3: 3 weeks
  - Milestone 4: 2 weeks
  - Milestone 5: 2 weeks
  - Milestone 6: 2 weeks
  - Milestone 7: 2 weeks
- Phase 5 (Validation): 2 weeks

**Total Project Duration**: 20 weeks (~5 months)

---
*Based on Constitution v2.0.0 - See `.specify/memory/constitution.md`*
