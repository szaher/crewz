# Research: Dynamic CrewAI Orchestration Platform

**Date**: 2025-10-05
**Phase**: 0 - Outline & Research
**Status**: Complete

## Research Areas

### 1. Multi-Tenant Database Schema Isolation (PostgreSQL)

**Decision**: Schema-per-tenant with connection pooling

**Rationale**:
- **Schema-per-tenant** provides strong isolation while remaining manageable at scale (1000+ tenants)
- PostgreSQL `SET search_path` allows dynamic schema switching without separate connections
- Connection pooling (via PgBouncer) amortizes connection overhead across tenants
- Backup/restore granularity at schema level simplifies tenant data management
- Migration complexity is reasonable (run once per schema, parallelizable)

**Alternatives Considered**:
- **Table-per-tenant**: Weak isolation, schema becomes unwieldy with 1000+ tenants (thousands of tables)
- **Database-per-tenant**: Strong isolation but impractical resource overhead (1000 databases), migration complexity
- **Row-level security**: Good for smaller scale, but query performance degrades with complex filters, harder to reason about

**Implementation Approach**:
- Middleware intercepts requests, extracts tenant from JWT, sets `search_path` before query execution
- Tenant schema created on registration: `CREATE SCHEMA tenant_{slug}`
- Alembic migrations run per schema using dynamic target (loop over all tenants)
- Connection pool sized to handle peak concurrent tenants (e.g., 100 connections)

**References**:
- PostgreSQL Multi-Tenant Patterns: https://www.citusdata.com/blog/2016/10/03/designing-your-saas-database-for-scale/
- Schema-based Multi-Tenancy Best Practices: https://www.postgresql.org/docs/15/ddl-schemas.html

---

### 2. Docker-in-Docker Security & Rootless Execution

**Decision**: Rootless Docker with sysbox runtime in Kubernetes

**Rationale**:
- **Rootless Docker** eliminates root daemon exposure, critical for untrusted user code
- **Sysbox** container runtime enables Docker-in-Docker without privileged mode
- Kubernetes supports sysbox via RuntimeClass
- Resource limits enforced at pod level (CPU, memory, network bandwidth)
- Seccomp and AppArmor policies provide defense-in-depth

**Alternatives Considered**:
- **Privileged DinD**: Unacceptable security risk (root access to host)
- **Kata Containers**: Strong isolation via VMs, but higher overhead and complexity
- **gVisor**: Good sandboxing, but Docker-in-Docker support is experimental
- **Firecracker microVMs**: Excellent isolation, but requires AWS Firecracker integration, higher operational complexity

**Implementation Approach**:
- Deploy sysbox-enabled node pool in Kubernetes cluster
- Tool execution pods use `runtimeClassName: sysbox-runc`
- Each tool execution gets dedicated ephemeral pod with Docker daemon
- Pod security policy enforces: no privileged escalation, read-only root filesystem, seccomp profile
- Resource limits: 2 CPU cores, 4GB RAM, 10GB storage, 1Mbps network egress per tool execution
- Execution timeout enforced via pod activeDeadlineSeconds (default 3600s)

**References**:
- Sysbox Runtime: https://github.com/nestybox/sysbox
- Rootless Docker Security: https://docs.docker.com/engine/security/rootless/
- Kubernetes RuntimeClass: https://kubernetes.io/docs/concepts/containers/runtime-class/

---

### 3. LLM Provider Abstraction Layer

**Decision**: Unified LiteLLM library with backend-managed credentials

**Rationale**:
- **LiteLLM** provides unified interface for 100+ LLM providers (OpenAI, Anthropic, Ollama, vLLM, etc.)
- Consistent streaming API across providers
- Built-in retry logic and fallback strategies
- Frontend never sees API keys (enforced by RBAC)
- LLM provider configs stored encrypted in database (AES-256)

**Alternatives Considered**:
- **Custom abstraction**: Significant development overhead, hard to keep pace with new providers
- **LangChain LLMs**: Heavier dependency, more opinionated, less focused on provider abstraction
- **Direct SDKs**: No unified interface, frontend would need provider-specific logic

**Implementation Approach**:
- `LLMService` wraps LiteLLM with tenant context
- LLM provider configs fetched per-request based on agent assignment
- Streaming handled via FastAPI's StreamingResponse + SSE
- Failover: if primary provider fails, retry with secondary provider (if configured)
- Usage tracking: log all requests to MongoDB (tenant, user, model, tokens, cost)
- Rate limiting: enforce per-tenant token limits via Redis counter (sliding window)

**Example**:
```python
from litellm import completion

response = completion(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello"}],
    api_key=provider.api_credentials['api_key'],
    stream=True
)
```

**References**:
- LiteLLM Documentation: https://docs.litellm.ai/docs/
- FastAPI Streaming: https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse

---

### 4. Real-Time Execution Monitoring

**Decision**: Server-Sent Events (SSE) for execution updates, WebSocket for chat

**Rationale**:
- **SSE** is simpler than WebSocket for unidirectional server→client streaming
- Built-in reconnection logic in browsers
- Works over HTTP/2, reuses connections efficiently
- WebSocket reserved for bidirectional chat interactions
- Redis Pub/Sub for backend-to-backend execution event distribution

**Alternatives Considered**:
- **WebSocket only**: Adds complexity for simple progress updates, requires more connection management
- **Polling**: Inefficient, high latency, poor user experience
- **GraphQL subscriptions**: Adds GraphQL dependency, overkill for this use case

**Implementation Approach**:
- Execution service publishes events to Redis: `PUBLISH executions:{execution_id} {event_json}`
- SSE endpoint subscribes to Redis channel, streams events to connected clients
- Event schema: `{type: "node_started" | "node_completed" | "node_failed", node_id, timestamp, data}`
- Client reconnects automatically on disconnect (browser native SSE behavior)
- Chat uses Socket.IO (WebSocket + fallback) for bidirectional crew interaction

**Example**:
```python
@router.get("/executions/{execution_id}/stream")
async def stream_execution(execution_id: str):
    async def event_generator():
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(f"executions:{execution_id}")
        async for message in pubsub.listen():
            if message['type'] == 'message':
                yield f"data: {message['data']}\\n\\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

**References**:
- Server-Sent Events Spec: https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events
- Redis Pub/Sub: https://redis.io/docs/manual/pubsub/

---

### 5. CrewAI SDK Integration Patterns

**Decision**: Dynamic agent factory with database-driven configuration

**Rationale**:
- CrewAI agents defined via Python classes, but our agents are user-configured JSON
- Factory pattern instantiates CrewAI agents from database models at runtime
- Custom tool adapter bridges database tool definitions to CrewAI tool interface
- Flow executor orchestrates CrewAI crew execution based on visual flow graph

**Alternatives Considered**:
- **Static Python agents**: Not feasible—users define agents via UI, not code
- **CrewAI YAML configs**: Still requires file system, doesn't fit multi-tenant database model

**Implementation Approach**:

1. **Agent Factory**:
```python
from crewai import Agent

class AgentFactory:
    @staticmethod
    def from_db_model(agent_model: Agent, llm_service: LLMService) -> CrewAIAgent:
        llm = llm_service.get_llm(agent_model.llm_provider_id)
        return CrewAIAgent(
            role=agent_model.name,
            goal=agent_model.description,
            backstory=agent_model.system_prompt,
            llm=llm,
            tools=[ToolAdapter.from_db_model(t) for t in agent_model.tools],
            **agent_model.config
        )
```

2. **Crew Factory**:
```python
from crewai import Crew

class CrewFactory:
    @staticmethod
    def from_db_model(crew_model: Crew, agent_factory: AgentFactory) -> CrewAICrew:
        agents = [agent_factory.from_db_model(a) for a in crew_model.agents]
        return CrewAICrew(
            agents=agents,
            process=crew_model.collaboration_pattern,  # "sequential" or "hierarchical"
            **crew_model.config
        )
```

3. **Tool Adapter**:
```python
from crewai.tools import Tool

class ToolAdapter:
    @staticmethod
    def from_db_model(tool_model: Tool) -> CrewAITool:
        return Tool(
            name=tool_model.name,
            description=tool_model.description,
            func=lambda input: DockerService.execute_tool(tool_model.id, input)
        )
```

4. **Flow Executor**:
- Parses flow graph (nodes, edges)
- Topological sort for execution order
- Executes each node (agent, tool, LLM call) based on node type
- Passes outputs to downstream nodes as inputs
- Handles conditional branches based on node outputs

**References**:
- CrewAI Documentation: https://docs.crewai.com/
- CrewAI Agent API: https://docs.crewai.com/core-concepts/Agents/

---

### 6. Kubernetes StatefulSet for Databases

**Decision**: Bitnami Helm charts for PostgreSQL and MongoDB

**Rationale**:
- **Bitnami charts** are production-ready, well-maintained, widely adopted
- Handles StatefulSet, PVC provisioning, init scripts, backups
- Customizable via values.yaml for local (KinD) vs production
- Avoids operator overhead for MVP (operators add complexity)
- Easy to migrate to managed services (RDS, Atlas) later

**Alternatives Considered**:
- **PostgreSQL Operator (Zalando, Crunchy)**: Production-grade, but overkill for MVP, steeper learning curve
- **Manual StatefulSet**: Requires deep Kubernetes expertise, error-prone, lacks backup automation
- **Managed services (RDS, Atlas)**: Ideal for production, but doesn't work for local KinD development

**Implementation Approach**:

1. **PostgreSQL** (via Bitnami):
```yaml
# infra/kubernetes/overlays/local/postgres-values.yaml
global:
  postgresql:
    auth:
      postgresPassword: "dev_password"
      database: "crewai_platform"

primary:
  persistence:
    size: 10Gi

resources:
  limits:
    cpu: 2
    memory: 4Gi
  requests:
    cpu: 1
    memory: 2Gi
```

2. **MongoDB** (via Bitnami):
```yaml
# infra/kubernetes/overlays/local/mongodb-values.yaml
auth:
  enabled: true
  rootPassword: "dev_password"

persistence:
  size: 20Gi

resources:
  limits:
    cpu: 2
    memory: 4Gi
```

3. **KinD** local storage:
- Use local-path-provisioner (comes with KinD)
- PVCs automatically provisioned on host filesystem

4. **Production**:
- Use cloud provider storage classes (AWS EBS, GCP PD, Azure Disk)
- Enable backups via Bitnami chart configurations
- OR migrate to managed RDS/Atlas for reduced operational burden

**References**:
- Bitnami PostgreSQL Chart: https://github.com/bitnami/charts/tree/main/bitnami/postgresql
- Bitnami MongoDB Chart: https://github.com/bitnami/charts/tree/main/bitnami/mongodb
- KinD Local Storage: https://kind.sigs.k8s.io/docs/user/local-registry/

---

## Summary

All research areas have been investigated and decisions made. The technical foundation is ready for Phase 1 design and contract generation.

**Key Technologies Selected**:
- Multi-tenancy: PostgreSQL schema-per-tenant with connection pooling
- Container security: Rootless Docker with Sysbox runtime
- LLM abstraction: LiteLLM with backend-managed credentials
- Real-time: SSE for execution updates, WebSocket for chat, Redis Pub/Sub
- CrewAI integration: Dynamic factories for agents/crews/tools
- Kubernetes databases: Bitnami Helm charts for PostgreSQL and MongoDB

**No unresolved NEEDS CLARIFICATION items remain.** Ready to proceed to Phase 1.
