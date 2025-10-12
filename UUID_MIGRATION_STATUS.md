# UUID Migration Status

## Completed Tasks

### ✅ Phase 1: Database Backup (Completed)
- **Backup file**: `backup_before_uuid.sql` (132KB)
- **Database user**: `crewai`
- **Database**: `crewai_platform`
- **Current data**:
  - 19 executions
  - 18 prompt templates
  - 13 chat sessions
  - 9 flows, 9 prompt categories
  - 7 crews, 7 notifications
  - 5 tools, 4 agents, 4 crews
  - Total: 25 tables with data

### ✅ Phase 4: Frontend UUID Support (Completed)
**File updated**: `frontend/src/types/api.ts`

**All ID fields converted from `number` to `string` (UUID format)**:

#### Core Entities
- ✅ User (id, tenant_id)
- ✅ Tenant (id)
- ✅ Agent (id, llm_provider_id, tool_ids[])
- ✅ Crew (id, tenant_id, agent_ids[], task_ids[])
- ✅ Tool (id)
- ✅ Flow (id, tenant_id)
- ✅ Execution (id, tenant_id, flow_id, crew_id, agent_id, tool_id, task_id)
- ✅ ChatSession (id, tenant_id, agent_id, crew_id, session_id)

#### Nested References
- ✅ FlowNode.data (agent_id, crew_id, tool_id)
- ✅ ExecutionEvent (execution_id)
- ✅ ChatMessage (session_id)
- ✅ TypingEvent (session_id)

#### All Create/Update/Response interfaces updated
- ✅ AgentCreate, AgentUpdate, AgentResponse
- ✅ CrewCreate, CrewUpdate, CrewResponse
- ✅ ExecutionCreate, ExecutionResponse
- ✅ ChatSessionCreate, ChatSessionResponse
- ✅ All list response interfaces

## Pending Tasks

### ✅ Phase 2: Complete UUID Migration Template (Completed)
**Status**: Migration script complete for all 25 tables

**Migration coverage**:
- ✅ tenants (no FKs)
- ✅ users (FK: tenant_id)
- ✅ llm_providers (FK: tenant_id)
- ✅ agents (FK: tenant_id, llm_provider_id)
- ✅ tools (no FKs)
- ✅ flows (no FKs)
- ✅ tasks (FKs: agent_id, crew_id - both optional)
- ✅ crews (FK: manager_llm_provider_id - optional)
- ✅ executions (FKs: flow_id, crew_id, agent_id, tool_id, task_id, user_id - all optional except user_id)
- ✅ chat_folders (FKs: tenant_id, user_id)
- ✅ chat_sessions (FKs: user_id, llm_provider_id, folder_id - folder_id optional)
- ✅ notifications (FKs: tenant_id, user_id)
- ✅ feedback (FKs: tenant_id, user_id, execution_id, agent_id - last 2 optional)
- ✅ agent_versions (FK: agent_id)
- ✅ provider_versions (FK: provider_id)
- ✅ prompt_categories (FK: tenant_id - special handling, already UUID primary key)
- ✅ prompt_templates (FKs: tenant_id, user_id - special handling, already UUID primary key)
- ✅ prompt_executions (FKs: prompt_id, user_id, tenant_id - special handling, already UUID primary key)
- ✅ prompt_favorites (FK: user_id, prompt_id - special handling, already UUID primary key)
- ✅ prompt_ratings (FKs: prompt_id, user_id - special handling, already UUID primary key)
- ✅ prompt_feedback (FKs: prompt_id, user_id, resolved_by - special handling, already UUID primary key)
- ✅ prompt_versions (FKs: prompt_id, parent_version_id - special handling, already UUID primary key)
- ✅ agent_tools association table (FKs: agent_id, tool_id)
- ✅ crew_agents association table (FKs: crew_id, agent_id)

**Migration script**: `backend/alembic/versions/20251012_040852_migrate_to_uuid.py`
**Python syntax**: ✅ Validated

### ✅ Phase 3: Test Migration on Fresh Database (Completed)
**Completed steps**:
1. ✅ Created test database
2. ✅ Ran Alembic migration: `docker-compose exec backend alembic upgrade head`
3. ✅ Verified UUID columns created for all 25 tables
4. ✅ Tested foreign key constraints - all working correctly
5. ✅ Inserted test data via registration and API calls
6. ✅ Validated queries work with UUID format
7. ✅ Fixed JWT token serialization to handle UUIDs
8. ✅ Fixed startup seed script to use UUID tenant/user IDs

### ⏳ Phase 5: End-to-End Verification
**Testing checklist**:
- [ ] Backend API returns UUIDs
- [ ] Frontend TypeScript compiles without errors
- [ ] CRUD operations work with UUID strings
- [ ] URL routing with UUID params works
- [ ] WebSocket events use UUID format
- [ ] ID comparisons work correctly (string vs string)
- [ ] Search/filter by ID works
- [ ] Local storage keys handle UUIDs

## Backend Changes Already Applied

### ✅ Models Updated (24+ files)
All SQLAlchemy models now use `postgresql.UUID(as_uuid=True)`:
- base.py (BaseModel with UUID primary key)
- All entity models: tenant, user, agent, llm_provider, crew, task, flow, execution, tool
- Support models: chat_session, chat_folder, notification, feedback
- Version models: agent_version, provider_version
- Prompt models: All 7 prompt-related models
- Association tables: agent_tools, crew_agents

### ✅ Schemas Updated (15 files)
All Pydantic schemas use `UUID` type:
- agents.py, flows.py, crew.py, task.py, executions.py, tools.py
- feedback.py, chat.py, notifications.py, prompt.py
- All request/response schemas

### ✅ UUID Utilities
- `backend/src/utils/uuid.py` with UUIDv7 generation
- uuid6 library added to requirements.txt

## Migration Safety Notes

⚠️ **CRITICAL WARNINGS**:
1. Migration is **ONE-WAY** and **DESTRUCTIVE**
2. All existing integer IDs will be replaced with UUIDs
3. **Breaks API compatibility** - frontend must be updated first
4. Cannot be automatically rolled back
5. Backup is essential: `backup_before_uuid.sql`

## Restore Command (if needed)
```bash
docker-compose exec -T postgres psql -U crewai -d crewai_platform < backup_before_uuid.sql
```

## Next Steps

1. **Complete Phase 2**: Finish migration template for all tables
2. **Test Phase 3**: Run migration on test database
3. **Deploy together**: Backend + Frontend must be deployed simultaneously
4. **Monitor**: Check logs for UUID format issues

## Runtime Issues Fixed

### Issue 1: JWT Token UUID Serialization
**Problem**: UUID objects not JSON serializable in JWT tokens
**File**: `backend/src/utils/jwt.py`
**Fix**:
- Updated function signatures to accept `Union[int, UUID]`
- Convert UUIDs to strings for JWT encoding
- Parse strings back to UUID objects when extracting from tokens
**Status**: ✅ Fixed

### Issue 2: Startup Seed Script Integer IDs
**Problem**: Seed script using integer `tenant_id=1` instead of UUID
**Files**:
- `backend/src/main.py` (startup event)
- `backend/src/services/prompt_seed.py` (seed function)
**Fix**:
- Updated function signatures to accept UUID parameters
- Query actual tenant and user UUIDs from database
- Pass UUIDs to seed function instead of hardcoded integers
**Status**: ✅ Fixed
**Verification**: 18 prompt templates and 8 categories successfully seeded with UUID IDs

## Timeline
- Phase 1: ✅ Completed (database backup)
- Phase 2: ✅ Completed (migration script for all 25 tables)
- Phase 4: ✅ Completed (frontend types updated)
- Phase 3: ✅ Completed (migration testing + runtime fixes)
- Phase 5: ⏳ Pending (end-to-end verification)

**Total time invested**: ~120 minutes
**Remaining time**: ~10 minutes for final verification
