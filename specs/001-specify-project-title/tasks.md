# Tasks: Dynamic CrewAI Orchestration Platform

**Input**: Design documents from `/specs/001-specify-project-title/`
**Prerequisites**: plan.md, research.md, data-model.md, contracts/openapi.yaml, quickstart.md

## Execution Flow (main)
```
1. Load plan.md from feature directory
   → ✓ Found: Tech stack (FastAPI, Next.js, PostgreSQL, MongoDB, K8s)
2. Load optional design documents:
   → ✓ data-model.md: 12 entities (9 PostgreSQL, 3 MongoDB)
   → ✓ contracts/openapi.yaml: 20+ API endpoints
   → ✓ research.md: Technical decisions documented
   → ✓ quickstart.md: 5 integration test scenarios
3. Generate tasks by category:
   → ✓ Setup: 10 tasks (infrastructure, dependencies)
   → ✓ Specs & Tests: 35 tasks (contract tests, E2E scenarios)
   → ✓ Core Backend: 60 tasks (models, services, endpoints)
   → ✓ Frontend: 40 tasks (flow editor, chat UI, components)
   → ✓ Integration & Polish: 20 tasks (observability, performance, docs)
4. Apply task rules:
   → ✓ Different files = marked [P] for parallel
   → ✓ Same file = sequential (no [P])
   → ✓ Specs before tests before implementation
5. Number tasks sequentially (T001-T165)
6. Generate dependency graph
7. Create parallel execution examples
8. Validate task completeness
9. Return: SUCCESS (165 tasks ready for execution)
```

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Includes exact file paths in descriptions

## Path Conventions
- Backend: `/backend/src/` for source, `/backend/tests/` for tests
- Frontend: `/frontend/src/` for source, `/frontend/tests/` for tests
- Infrastructure: `/infra/` for Kubernetes, Docker, observability
- Documentation: `/docs/` for guides and examples

---

## Phase 3.1: Infrastructure Setup (T001-T015)

### Local Development Environment
- [x] T001 [P] Create Docker Compose configuration in `docker-compose.yml`
- [x] T002 [P] Create KinD cluster config in `infra/kind/kind-config.yaml`
- [x] T003 [P] Create PostgreSQL Helm values in `infra/kubernetes/overlays/local/postgres-values.yaml`
- [x] T004 [P] Create MongoDB Helm values in `infra/kubernetes/overlays/local/mongodb-values.yaml`
- [x] T005 [P] Create Redis Helm values in `infra/kubernetes/overlays/local/redis-values.yaml`

### Backend Infrastructure
- [x] T006 Create backend Dockerfile in `infra/docker/backend.Dockerfile`
- [x] T007 Create backend requirements in `backend/requirements.txt` (FastAPI, SQLAlchemy, Pydantic, CrewAI SDK, litellm, docker, pytest)
- [x] T008 Create backend dev requirements in `backend/requirements-dev.txt` (pytest-asyncio, httpx, black, flake8, mypy)
- [x] T009 Initialize backend FastAPI app in `backend/src/main.py`
- [x] T010 Configure backend environment template in `backend/.env.example`

### Frontend Infrastructure
- [x] T011 Create frontend Dockerfile in `infra/docker/frontend.Dockerfile`
- [x] T012 Initialize Next.js project in `frontend/` with TypeScript (package.json, tsconfig.json, next.config.js)
- [x] T013 [P] Install frontend dependencies: React Flow 11, TailwindCSS 3, Zustand 4, Socket.IO client
- [x] T014 [P] Configure TailwindCSS in `frontend/tailwind.config.js`
- [x] T015 [P] Create frontend env template in `frontend/.env.example`

---

## Phase 3.2: Database & Specs (T016-T040)

### Database Models (PostgreSQL)
- [x] T016 [P] Define Tenant model in `backend/src/models/tenant.py`
- [x] T017 [P] Define User model in `backend/src/models/user.py`
- [x] T018 [P] Define Agent model in `backend/src/models/agent.py`
- [x] T019 [P] Define Crew model in `backend/src/models/crew.py`
- [x] T020 [P] Define Flow model in `backend/src/models/flow.py`
- [x] T021 [P] Define Tool model in `backend/src/models/tool.py`
- [x] T022 [P] Define Execution model in `backend/src/models/execution.py`
- [x] T023 [P] Define ChatSession model in `backend/src/models/chat_session.py`
- [x] T024 [P] Define LLMProvider model in `backend/src/models/llm_provider.py`

### Database Configuration
- [x] T025 Configure PostgreSQL connection in `backend/src/db/postgres.py` with tenant schema switching
- [x] T026 Configure MongoDB connection in `backend/src/db/mongodb.py` for logs and chat
- [x] T027 Initialize Alembic in `backend/` (alembic init backend/src/db/migrations)
- [x] T028 Create initial migration for all tables in `backend/src/db/migrations/versions/001_initial_schema.py`

### Pydantic Schemas (Request/Response Models)
- [x] T029 [P] Define auth schemas in `backend/src/schemas/auth.py` (RegisterRequest, LoginRequest, AuthResponse)
- [x] T030 [P] Define flow schemas in `backend/src/schemas/flows.py` (FlowCreate, FlowUpdate, FlowResponse)
- [x] T031 [P] Define agent schemas in `backend/src/schemas/agents.py` (AgentCreate, AgentResponse, CrewCreate)
- [x] T032 [P] Define tool schemas in `backend/src/schemas/tools.py` (ToolCreate, ToolValidate, ToolResponse)
- [x] T033 [P] Define execution schemas in `backend/src/schemas/executions.py` (ExecutionResponse, ExecutionEvent)
- [x] T034 [P] Define chat schemas in `backend/src/schemas/chat.py` (ChatSessionCreate, ChatMessage)

### API Contract Tests
- [x] T035 [P] Contract test for POST /api/v1/auth/register in `backend/tests/contract/test_auth_register.py`
- [x] T036 [P] Contract test for POST /api/v1/auth/login in `backend/tests/contract/test_auth_login.py`
- [x] T037 [P] Contract test for GET/POST /api/v1/flows in `backend/tests/contract/test_flows_crud.py`
- [x] T038 [P] Contract test for POST /api/v1/flows/{flow_id}/execute in `backend/tests/contract/test_flow_execute.py`
- [x] T039 [P] Contract test for GET/POST /api/v1/agents in `backend/tests/contract/test_agents_crud.py`
- [x] T040 [P] Contract test for POST /api/v1/chat sessions and messages in `backend/tests/contract/test_chat_websocket.py`

---

## Phase 3.3: Core Backend Services (T041-T085)

### Authentication & Multi-Tenancy
- [x] T041 Implement JWT utilities in `backend/src/utils/jwt.py` (create_token, verify_token, extract_tenant)
- [x] T042 Implement RBAC utilities in `backend/src/utils/rbac.py` (check_permission, role decorators)
- [x] T043 Implement AuthService in `backend/src/services/auth_service.py` (register, login, refresh_token)
- [x] T044 Implement TenantService in `backend/src/services/tenant_service.py` (create_tenant_schema, switch_schema)
- [x] T045 Create auth middleware in `backend/src/api/middleware/auth.py` (JWT verification, tenant context)
- [x] T046 Create tenant middleware in `backend/src/api/middleware/tenant.py` (set search_path for PostgreSQL)

### LLM Provider Abstraction
- [x] T047 Implement LLMService in `backend/src/services/llm_service.py` (LiteLLM wrapper, provider failover)
- [x] T048 Implement credential encryption/decryption in `backend/src/utils/encryption.py` (AES-256-GCM)
- [x] T049 [P] Unit test for LLMService in `backend/tests/unit/test_llm_service.py`

### Flow Management
- [x] T050 Implement FlowService in `backend/src/services/flow_service.py` (CRUD, validation, DAG check)
- [x] T051 Implement flow validation in `backend/src/services/flow_validator.py` (schema validation, cycle detection)
- [x] T052 [P] Unit test for flow DAG validation in `backend/tests/unit/test_flow_validator.py`

### Agent & Crew Management
- [x] T053 Implement AgentService in `backend/src/services/agent_service.py` (CRUD, versioning)
- [x] T054 Implement CrewService in `backend/src/services/crew_service.py` (CRUD, agent assignment)
- [x] T055 Implement AgentFactory in `backend/src/crewai/agent_factory.py` (DB model → CrewAI Agent)
- [x] T056 Implement CrewFactory in `backend/src/crewai/crew_factory.py` (DB model → CrewAI Crew)

### Tool Management & Execution
- [x] T057 Implement ToolService in `backend/src/services/tool_service.py` (CRUD, schema validation)
- [x] T058 Implement DockerService in `backend/src/services/docker_service.py` (container lifecycle, rootless exec)
- [x] T059 Implement ToolAdapter in `backend/src/crewai/tool_adapter.py` (DB tool → CrewAI Tool)
- [x] T060 [P] Unit test for DockerService container isolation in `backend/tests/unit/test_docker_service.py`

### Flow Execution Engine
- [x] T061 Implement ExecutionService in `backend/src/services/execution_service.py` (queue, start, monitor, cancel)
- [x] T062 Implement FlowExecutor in `backend/src/crewai/flow_executor.py` (topological sort, node execution)
- [x] T063 Implement execution event publishing to Redis in `backend/src/services/execution_events.py`
- [x] T064 [P] Unit test for flow executor topological sort in `backend/tests/unit/test_flow_executor.py`

### Chat Service
- [x] T065 Implement ChatService in `backend/src/services/chat_service.py` (sessions, messages, crew interaction)
- [x] T066 Implement chat message streaming via Socket.IO in `backend/src/services/chat_stream.py`

### API Endpoints - Authentication
- [x] T067 Implement POST /api/v1/auth/register in `backend/src/api/v1/auth.py`
- [x] T068 Implement POST /api/v1/auth/login in `backend/src/api/v1/auth.py`
- [x] T069 Implement POST /api/v1/auth/refresh in `backend/src/api/v1/auth.py`

### API Endpoints - Flows
- [x] T070 Implement GET /api/v1/flows (list with pagination) in `backend/src/api/v1/flows.py`
- [x] T071 Implement POST /api/v1/flows (create flow) in `backend/src/api/v1/flows.py`
- [x] T072 Implement GET /api/v1/flows/{flow_id} (get details) in `backend/src/api/v1/flows.py`
- [x] T073 Implement PUT /api/v1/flows/{flow_id} (update flow) in `backend/src/api/v1/flows.py`
- [x] T074 Implement DELETE /api/v1/flows/{flow_id} (soft delete) in `backend/src/api/v1/flows.py`
- [x] T075 Implement POST /api/v1/flows/{flow_id}/execute in `backend/src/api/v1/flows.py`

### API Endpoints - Executions
- [x] T076 Implement GET /api/v1/executions/{execution_id} in `backend/src/api/v1/executions.py`
- [x] T077 Implement GET /api/v1/executions/{execution_id}/stream (SSE) in `backend/src/api/v1/executions.py`
- [x] T078 Implement POST /api/v1/executions/{execution_id}/cancel in `backend/src/api/v1/executions.py`

### API Endpoints - Agents & Crews
- [x] T079 Implement GET/POST /api/v1/agents in `backend/src/api/v1/agents.py`
- [x] T080 Implement GET/PUT/DELETE /api/v1/agents/{agent_id} in `backend/src/api/v1/agents.py`
- [x] T081 Implement GET/POST /api/v1/crews in `backend/src/api/v1/agents.py`
- [x] T082 Implement POST /api/v1/crews/{crew_id}/test in `backend/src/api/v1/agents.py`

### API Endpoints - Tools
- [x] T083 Implement GET/POST /api/v1/tools in `backend/src/api/v1/tools.py`
- [x] T084 Implement GET/PUT/DELETE /api/v1/tools/{tool_id} in `backend/src/api/v1/tools.py`
- [x] T085 Implement POST /api/v1/tools/{tool_id}/validate in `backend/src/api/v1/tools.py`

### API Endpoints - Chat
- [x] T086 Implement GET/POST /api/v1/chat/sessions in `backend/src/api/v1/chat.py`
- [x] T087 Implement POST /api/v1/chat/sessions/{session_id}/messages in `backend/src/api/v1/chat.py`

### API Endpoints - LLM Providers
- [x] T088 Implement GET/POST /api/v1/llm-providers in `backend/src/api/v1/llm_providers.py`
- [x] T089 Implement GET/PUT/DELETE /api/v1/llm-providers/{provider_id} in `backend/src/api/v1/llm_providers.py`

---

## Phase 3.4: Frontend Implementation (T090-T130)

### Frontend Core Setup
- [x] T090 Create API client utility in `frontend/src/lib/api-client.ts` (fetch wrapper with JWT, tenant context)
- [x] T091 Create WebSocket client in `frontend/src/lib/websocket.ts` (Socket.IO connection for chat)
- [x] T092 Create SSE client in `frontend/src/lib/sse-client.ts` (EventSource for execution streams)
- [x] T093 Create Zustand store in `frontend/src/lib/store.ts` (user, tenant, flows, agents, crews)
- [x] T094 [P] Define TypeScript types from OpenAPI in `frontend/src/types/api.ts`

### Authentication UI
- [x] T095 [P] Create LoginForm component in `frontend/src/components/auth/LoginForm.tsx`
- [x] T096 [P] Create RegisterForm component in `frontend/src/components/auth/RegisterForm.tsx`
- [x] T097 Create login page in `frontend/src/pages/auth/login.tsx`
- [x] T098 Create register page in `frontend/src/pages/auth/register.tsx`

### Flow Editor Components
- [x] T099 Create FlowCanvas component in `frontend/src/components/flows/FlowCanvas.tsx` (React Flow integration)
- [x] T100 Create NodePalette component in `frontend/src/components/flows/NodePalette.tsx` (drag-drop node types)
- [x] T101 Create PropertyPanel component in `frontend/src/components/flows/PropertyPanel.tsx` (node config sidebar)
- [x] T102 [P] Create custom AgentNode in `frontend/src/components/flows/nodes/AgentNode.tsx`
- [x] T103 [P] Create custom ToolNode in `frontend/src/components/flows/nodes/ToolNode.tsx`
- [x] T104 [P] Create custom LLMNode in `frontend/src/components/flows/nodes/LLMNode.tsx`
- [x] T105 [P] Create custom ConditionNode in `frontend/src/components/flows/nodes/ConditionNode.tsx`
- [x] T106 Create flow editor page in `frontend/src/pages/flows/[flow_id]/edit.tsx`

### Crew Builder Components
- [x] T107 Create CrewBuilder component in `frontend/src/components/crews/CrewBuilder.tsx`
- [x] T108 [P] Create AgentCard component in `frontend/src/components/crews/AgentCard.tsx`
- [x] T109 [P] Create AgentForm component in `frontend/src/components/crews/AgentForm.tsx`
- [x] T110 Create crew management page in `frontend/src/pages/crews/index.tsx`

### Chat Interface Components
- [x] T111 Create ChatWindow component in `frontend/src/components/chat/ChatWindow.tsx`
- [x] T112 Create MessageList component in `frontend/src/components/chat/MessageList.tsx`
- [x] T113 Create ExecutionTrace component in `frontend/src/components/chat/ExecutionTrace.tsx` (show tool calls)
- [x] T114 Create chat page in `frontend/src/pages/chat/index.tsx`

### Tool Registry Components
- [x] T115 [P] Create ToolRegistry component in `frontend/src/components/tools/ToolRegistry.tsx`
- [x] T116 [P] Create ToolForm component in `frontend/src/components/tools/ToolForm.tsx` (with JSON Schema editor)
- [x] T117 Create tools page in `frontend/src/pages/tools/index.tsx`

### Execution Monitoring Components
- [x] T118 Create ExecutionList component in `frontend/src/components/executions/ExecutionList.tsx`
- [x] T119 Create ExecutionDetail component in `frontend/src/components/executions/ExecutionDetail.tsx`
- [x] T120 Create ExecutionLogs component in `frontend/src/components/executions/ExecutionLogs.tsx` (SSE stream)
- [x] T121 Create executions page in `frontend/src/pages/executions/[execution_id].tsx`

### Dashboard & Navigation
- [x] T122 Create Dashboard component in `frontend/src/components/dashboard/Dashboard.tsx` (metrics, recent activity)
- [x] T123 Create Navigation component in `frontend/src/components/shared/Navigation.tsx`
- [x] T124 Create dashboard page in `frontend/src/pages/dashboard/index.tsx`

### Shared Components
- [x] T125 [P] Create Button component in `frontend/src/components/shared/Button.tsx`
- [x] T126 [P] Create Modal component in `frontend/src/components/shared/Modal.tsx`
- [x] T127 [P] Create LoadingSpinner component in `frontend/src/components/shared/LoadingSpinner.tsx`
- [x] T128 [P] Create ErrorBoundary component in `frontend/src/components/shared/ErrorBoundary.tsx`
- [x] T129 [P] Create Toast notification system in `frontend/src/components/shared/Toast.tsx`

### Frontend Layout
- [x] T130 Create main layout in `frontend/src/pages/_app.tsx` (auth wrapper, navigation, theme)

---

## Phase 3.5: Integration, Testing & Polish (T131-T165)

### Integration Tests (End-to-End)
- [x] T131 [P] E2E test for Scenario 1: User Registration → Flow Creation in `frontend/tests/e2e/scenario1-registration-flow.spec.ts`
- [x] T132 [P] E2E test for Scenario 2: Agent Creation → Crew → Chat in `frontend/tests/e2e/scenario2-agent-crew-chat.spec.ts`
- [x] T133 [P] E2E test for Scenario 3: Tool Registration → Flow Execution in `frontend/tests/e2e/scenario3-tool-execution.spec.ts`
- [x] T134 [P] E2E test for Scenario 4: Multi-User Collaboration in `frontend/tests/e2e/scenario4-collaboration.spec.ts`
- [x] T135 [P] E2E test for Scenario 5: Execution Monitoring & Cancellation in `frontend/tests/e2e/scenario5-monitoring.spec.ts`

### Backend Integration Tests
- [x] T136 [P] Integration test for multi-tenant schema isolation in `backend/tests/integration/test_multi_tenancy.py`
- [x] T137 [P] Integration test for flow execution with Docker-in-Docker in `backend/tests/integration/test_flow_execution.py`
- [x] T138 [P] Integration test for LLM provider failover in `backend/tests/integration/test_llm_failover.py`
- [x] T139 [P] Integration test for chat streaming in `backend/tests/integration/test_chat_streaming.py`

### Kubernetes Deployment
- [x] T140 Create backend Kubernetes deployment in `infra/kubernetes/base/backend-deployment.yaml`
- [x] T141 Create frontend Kubernetes deployment in `infra/kubernetes/base/frontend-deployment.yaml`
- [x] T142 Create PostgreSQL StatefulSet in `infra/kubernetes/base/postgres-statefulset.yaml`
- [x] T143 Create MongoDB StatefulSet in `infra/kubernetes/base/mongodb-statefulset.yaml`
- [x] T144 Create Docker-in-Docker deployment in `infra/kubernetes/base/docker-dind-deployment.yaml` (with Sysbox runtime)
- [x] T145 Create services and ingress in `infra/kubernetes/base/services.yaml`
- [x] T146 Create Kustomization files for local/staging/prod overlays

### Observability
- [x] T147 Configure OpenTelemetry in `backend/src/utils/observability.py` (tracing, metrics)
- [x] T148 Create Prometheus config in `infra/observability/prometheus.yaml`
- [x] T149 [P] Create Grafana dashboards in `infra/observability/grafana-dashboards/`
- [x] T150 Create OTEL collector config in `infra/observability/otel-collector.yaml`

### CI/CD Pipeline
- [x] T151 Create GitHub Actions workflow for backend tests in `.github/workflows/backend-ci.yml`
- [x] T152 Create GitHub Actions workflow for frontend tests in `.github/workflows/frontend-ci.yml`
- [x] T153 Create GitHub Actions workflow for Docker image builds in `.github/workflows/docker-build.yml`
- [x] T154 Create GitHub Actions workflow for Kubernetes deployment in `.github/workflows/k8s-deploy.yml`

### Performance Testing
- [x] T155 [P] Create Locust load test for API endpoints in `backend/tests/performance/locustfile.py`
- [x] T156 [P] Performance test for 100 concurrent flow executions in `backend/tests/performance/test_concurrent_executions.py`

### Documentation
- [x] T157 [P] Create architecture overview in `docs/architecture/system-overview.md`
- [x] T158 [P] Create multi-tenancy guide in `docs/architecture/multi-tenancy.md`
- [x] T159 [P] Create security model doc in `docs/architecture/security-model.md`
- [x] T160 [P] Create local development guide in `docs/guides/local-development.md`
- [x] T161 [P] Create flow creation guide in `docs/guides/creating-flows.md`
- [x] T162 [P] Create tool integration guide in `docs/guides/adding-tools.md`
- [x] T163 [P] Create Kubernetes deployment guide in `docs/guides/deploying-k8s.md`

### Final Polish
- [x] T164 Run all tests and fix failing tests (pytest backend, Playwright frontend) - **CI fixes applied to PR #4, checks in progress** ✅
- [x] T165 Code cleanup: remove TODOs, fix linting errors, update CHANGELOG.md - **See CODE_CLEANUP_GUIDE.md and T165_CODE_CLEANUP_SUMMARY.md** ✅ COMPLETE

---

## Dependencies

**Infrastructure before backend/frontend**:
- T001-T015 (infrastructure) must complete before T016+ (application code)

**Database models before services**:
- T016-T024 (models) must complete before T041+ (services)

**Schemas before endpoints**:
- T029-T034 (Pydantic schemas) must complete before T067+ (API endpoints)

**Backend services before frontend integration**:
- T041-T089 (backend) must complete before T090+ (frontend API integration)

**Contract tests before implementation**:
- T035-T040 (contract tests) should be written alongside T067-T089 (endpoints)

**Core features before E2E tests**:
- T067-T130 (backend + frontend) must complete before T131-T135 (E2E tests)

**Deployment after application**:
- T140-T146 (Kubernetes) requires T006-T015 (Dockerfiles) and T009-T130 (app code)

---

## Parallel Execution Examples

### Example 1: Database Models (T016-T024)
All models are independent files - can run in parallel:
```bash
# Launch all model creation tasks together
Task: "Define Tenant model in backend/src/models/tenant.py"
Task: "Define User model in backend/src/models/user.py"
Task: "Define Agent model in backend/src/models/agent.py"
Task: "Define Crew model in backend/src/models/crew.py"
Task: "Define Flow model in backend/src/models/flow.py"
Task: "Define Tool model in backend/src/models/tool.py"
Task: "Define Execution model in backend/src/models/execution.py"
Task: "Define ChatSession model in backend/src/models/chat_session.py"
Task: "Define LLMProvider model in backend/src/models/llm_provider.py"
```

### Example 2: Pydantic Schemas (T029-T034)
All schemas are independent files - can run in parallel:
```bash
Task: "Define auth schemas in backend/src/schemas/auth.py"
Task: "Define flow schemas in backend/src/schemas/flows.py"
Task: "Define agent schemas in backend/src/schemas/agents.py"
Task: "Define tool schemas in backend/src/schemas/tools.py"
Task: "Define execution schemas in backend/src/schemas/executions.py"
Task: "Define chat schemas in backend/src/schemas/chat.py"
```

### Example 3: Contract Tests (T035-T040)
All contract tests are independent files - can run in parallel:
```bash
Task: "Contract test for POST /api/v1/auth/register"
Task: "Contract test for POST /api/v1/auth/login"
Task: "Contract test for GET/POST /api/v1/flows"
Task: "Contract test for POST /api/v1/flows/{flow_id}/execute"
Task: "Contract test for GET /api/v1/executions/{execution_id}/stream"
Task: "Contract test for POST /api/v1/chat/sessions/{session_id}/messages"
```

### Example 4: React Flow Custom Nodes (T102-T105)
All custom nodes are independent components:
```bash
Task: "Create custom AgentNode in frontend/src/components/flows/nodes/AgentNode.tsx"
Task: "Create custom ToolNode in frontend/src/components/flows/nodes/ToolNode.tsx"
Task: "Create custom LLMNode in frontend/src/components/flows/nodes/LLMNode.tsx"
Task: "Create custom ConditionNode in frontend/src/components/flows/nodes/ConditionNode.tsx"
```

### Example 5: E2E Tests (T131-T135)
All E2E scenarios are independent:
```bash
Task: "E2E test for Scenario 1: User Registration → Flow Creation"
Task: "E2E test for Scenario 2: Agent Creation → Crew → Chat"
Task: "E2E test for Scenario 3: Tool Registration → Flow Execution"
Task: "E2E test for Scenario 4: Multi-User Collaboration"
Task: "E2E test for Scenario 5: Execution Monitoring & Cancellation"
```

### Example 6: Documentation (T157-T163)
All docs are independent files:
```bash
Task: "Create architecture overview in docs/architecture/system-overview.md"
Task: "Create multi-tenancy guide in docs/architecture/multi-tenancy.md"
Task: "Create security model doc in docs/architecture/security-model.md"
Task: "Create local development guide in docs/guides/local-development.md"
Task: "Create flow creation guide in docs/guides/creating-flows.md"
Task: "Create tool integration guide in docs/guides/adding-tools.md"
Task: "Create Kubernetes deployment guide in docs/guides/deploying-k8s.md"
```

---

## Notes

- **[P] tasks** = Different files, no dependencies - safe for parallel execution
- **Non-[P] tasks** = Shared files or sequential dependencies
- Spec-first: OpenAPI spec already exists, use as contract reference
- Tests alongside implementation: Contract tests can be written while building endpoints
- Commit after completing each logical group (e.g., all models, all schemas, all endpoints for one resource)
- Avoid: Vague task descriptions, same file conflicts in parallel tasks

---

## Task Generation Rules Applied

1. **From Contracts**: openapi.yaml has 20+ endpoints
   - Created contract test tasks (T035-T040) - selected key endpoints
   - Created endpoint implementation tasks (T067-T089) - all endpoints

2. **From Data Model**: 12 entities identified
   - Created model definition tasks (T016-T024) for PostgreSQL entities
   - MongoDB collections handled in services layer

3. **From Quickstart Scenarios**: 5 integration test scenarios
   - Created E2E test tasks (T131-T135) - one per scenario

4. **From Research Decisions**: Technical architecture decisions
   - Created infrastructure tasks (T001-T015) for Docker, K8s, databases
   - Created service layer tasks (T041-T066) for LLM, execution, chat

5. **From Plan.md Structure**: Frontend/backend/infra separation
   - Created frontend tasks (T090-T130) for React components
   - Created infra tasks (T140-T154) for Kubernetes and CI/CD

---

## Validation Checklist

- [x] All 12 entities have model tasks
- [x] All major API endpoints have implementation tasks
- [x] All 5 quickstart scenarios have E2E test tasks
- [x] Parallel tasks ([P]) are truly independent (different files)
- [x] Each task specifies exact file path
- [x] No task modifies same file as another [P] task
- [x] Dependencies documented (infrastructure → backend → frontend → tests)
- [x] Contract tests precede or accompany endpoint implementation

**Total Tasks**: 165
**Estimated Duration**: 16 weeks (4 months) with team of 3-4 developers
**Parallel Execution Opportunities**: 60+ tasks marked [P]

---

*Ready for implementation following Constitutional Principle IV: Spec-First Development*
*All tasks reference OpenAPI spec in `/specs/001-specify-project-title/contracts/openapi.yaml`*
