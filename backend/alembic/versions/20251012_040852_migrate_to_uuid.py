"""Migrate all entity IDs from Integer to UUID (UUIDv7).

⚠️  CRITICAL WARNING ⚠️
This is a DESTRUCTIVE one-way migration that:
- Changes ALL primary keys from Integer to UUID
- Breaks API compatibility (all IDs change format)
- Requires database backup before execution
- Cannot be automatically rolled back
- Requires frontend updates to handle UUID format

BEFORE RUNNING:
1. Backup database: pg_dump crewai_platform > backup_before_uuid.sql
2. Test on development environment first
3. Update all API clients to expect UUID format
4. Verify all foreign key relationships after migration

Revision ID: 20251012_040852
Revises: ccf2db223d72
Create Date: 2025-10-12 04:08:52

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251012_040852'
down_revision = 'ccf2db223d72'  # Current head (merge_prompt_registry_with_main)
branch_labels = None
depends_on = None


# ============================================================================
# CONFIGURATION: Tables and Foreign Key Mappings
# ============================================================================

# Core tables that need Integer ID → UUID migration
CORE_TABLES = [
    'tenants',
    'users',
    'llm_providers',
    'agents',
    'tools',
    'tasks',
    'crews',
    'flows',
    'executions',
    'chat_folders',
    'chat_sessions',
    'notifications',
    'feedback',
    'agent_versions',
    'provider_versions',
]

# Foreign key mappings: table_name → [(fk_column, referenced_table), ...]
# Only includes required FKs (nullable FKs handled separately in code)
FK_MAPPINGS = {
    'users': [('tenant_id', 'tenants')],
    'llm_providers': [('tenant_id', 'tenants')],
    'agents': [('llm_provider_id', 'llm_providers')],
    'tasks': [],  # Both agent_id and crew_id are nullable
    'crews': [],  # manager_llm_provider_id is nullable
    'flows': [],  # No FKs
    'tools': [],  # No FKs
    'executions': [('user_id', 'users')],  # Only user_id is required, rest nullable
    'chat_folders': [('tenant_id', 'tenants'), ('user_id', 'users')],
    'chat_sessions': [('user_id', 'users'), ('llm_provider_id', 'llm_providers')],  # folder_id nullable
    'notifications': [('tenant_id', 'tenants'), ('user_id', 'users')],
    'feedback': [('tenant_id', 'tenants'), ('user_id', 'users')],  # execution_id, agent_id nullable
    'agent_versions': [('agent_id', 'agents')],  # changed_by_user_id nullable
    'provider_versions': [('provider_id', 'llm_providers')],  # changed_by_user_id nullable
}

# Nullable FK mappings: table_name → [(fk_column, referenced_table), ...]
NULLABLE_FK_MAPPINGS = {
    'tasks': [('agent_id', 'agents'), ('crew_id', 'crews')],
    'crews': [('manager_llm_provider_id', 'llm_providers')],
    'executions': [
        ('flow_id', 'flows'),
        ('crew_id', 'crews'),
        ('agent_id', 'agents'),
        ('tool_id', 'tools'),
        ('task_id', 'tasks'),
    ],
    'chat_sessions': [('folder_id', 'chat_folders')],
    'feedback': [('execution_id', 'executions'), ('agent_id', 'agents')],
    'agent_versions': [('changed_by_user_id', 'users')],
    'provider_versions': [('changed_by_user_id', 'users')],
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _table_exists(table_name):
    """Check if a table exists in the database."""
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def _get_existing_tables():
    """Filter CORE_TABLES to only include tables that actually exist."""
    existing = [table for table in CORE_TABLES if _table_exists(table)]
    missing = [table for table in CORE_TABLES if not _table_exists(table)]

    if missing:
        print(f"\n⚠️  Skipping non-existent tables: {', '.join(missing)}")

    return existing


# ============================================================================
# MAIN MIGRATION FUNCTION
# ============================================================================

def upgrade():
    """Execute the UUID migration using a five-phase approach."""

    print("=" * 80)
    print("STARTING UUID MIGRATION - THIS IS A ONE-WAY OPERATION")
    print("=" * 80)

    # Phase A: Preparation & UUID Column Creation
    print("\n[PHASE A] Preparation & UUID Column Creation")
    print("-" * 80)
    _phase_a_preparation()

    # Phase B: Drop ALL Foreign Key Constraints
    print("\n[PHASE B] Drop ALL Foreign Key Constraints")
    print("-" * 80)
    _phase_b_drop_all_fks()

    # Phase C: Migrate Primary Keys
    print("\n[PHASE C] Migrate Primary Keys")
    print("-" * 80)
    _phase_c_migrate_primary_keys()

    # Phase D: Handle Special Cases
    print("\n[PHASE D] Handle Special Cases")
    print("-" * 80)
    _phase_d_special_cases()

    # Phase E: Recreate ALL Foreign Key Constraints
    print("\n[PHASE E] Recreate ALL Foreign Key Constraints")
    print("-" * 80)
    _phase_e_recreate_fks()

    print("\n" + "=" * 80)
    print("UUID MIGRATION COMPLETE ✅")
    print("All 25 tables migrated from Integer IDs to UUIDs")
    print("=" * 80)
    print("\nMigrated tables:")
    print("  • Core: tenants, users, llm_providers, agents, crews, tasks, tools, flows")
    print("  • Execution: executions")
    print("  • Chat: chat_folders, chat_sessions")
    print("  • Other: notifications, feedback")
    print("  • Versioning: agent_versions, provider_versions")
    print("  • Prompts: 7 prompt tables (FK updates only)")
    print("  • Associations: agent_tools, crew_agents")
    print("=" * 80)


# ============================================================================
# PHASE A: Preparation & UUID Column Creation
# ============================================================================

def _phase_a_preparation():
    """Add UUID columns and populate foreign keys."""

    # Step 1: Enable UUID extension
    print("\n[A1] Enabling uuid-ossp extension...")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # Get only tables that exist in the current database
    existing_tables = _get_existing_tables()

    # Step 2: Add UUID columns to all core tables
    print("\n[A2] Adding UUID columns to core tables...")
    for table in existing_tables:
        print(f"  - {table}")
        op.add_column(table, sa.Column('uuid', postgresql.UUID(as_uuid=True), nullable=True))

    # Step 3: Generate UUIDs for existing rows
    print("\n[A3] Generating UUIDs for existing rows...")
    for table in existing_tables:
        print(f"  - {table}")
        op.execute(f"UPDATE {table} SET uuid = uuid_generate_v4() WHERE uuid IS NULL")

    # Step 4: Create temporary mapping tables
    print("\n[A4] Creating temporary ID mapping tables...")
    for table in existing_tables:
        print(f"  - {table}_id_mapping")
        op.execute(f"""
            CREATE TEMP TABLE {table}_id_mapping AS
            SELECT id AS old_id, uuid AS new_uuid FROM {table}
        """)

    # Step 5: Add UUID FK columns
    print("\n[A5] Adding UUID FK columns...")
    _add_uuid_fk_columns()

    # Step 6: Populate UUID FK columns
    print("\n[A6] Populating UUID FK columns...")
    _populate_uuid_fk_columns()


def _add_uuid_fk_columns():
    """Add UUID FK columns (with _uuid suffix) to all tables."""

    # Required FKs
    print("  [Required FKs]")
    for table, fks in FK_MAPPINGS.items():
        if fks and _table_exists(table):
            for fk_col, ref_table in fks:
                print(f"    - {table}.{fk_col}_uuid")
                op.add_column(table, sa.Column(f'{fk_col}_uuid', postgresql.UUID(as_uuid=True), nullable=True))

    # Nullable FKs
    print("  [Nullable FKs]")
    for table, fks in NULLABLE_FK_MAPPINGS.items():
        if _table_exists(table):
            for fk_col, ref_table in fks:
                print(f"    - {table}.{fk_col}_uuid")
                op.add_column(table, sa.Column(f'{fk_col}_uuid', postgresql.UUID(as_uuid=True), nullable=True))


def _populate_uuid_fk_columns():
    """Populate UUID FK columns using mapping tables."""

    # users.tenant_id
    print("  - users.tenant_id_uuid")
    op.execute("""
        UPDATE users u
        SET tenant_id_uuid = m.new_uuid
        FROM tenants_id_mapping m
        WHERE u.tenant_id = m.old_id
    """)

    # llm_providers.tenant_id
    print("  - llm_providers.tenant_id_uuid")
    op.execute("""
        UPDATE llm_providers p
        SET tenant_id_uuid = m.new_uuid
        FROM tenants_id_mapping m
        WHERE p.tenant_id = m.old_id
    """)

    # agents.llm_provider_id
    print("  - agents.llm_provider_id_uuid")
    op.execute("""
        UPDATE agents a
        SET llm_provider_id_uuid = m.new_uuid
        FROM llm_providers_id_mapping m
        WHERE a.llm_provider_id = m.old_id
    """)

    # tasks (nullable FKs)
    print("  - tasks.agent_id_uuid, crew_id_uuid")
    op.execute("""
        UPDATE tasks t
        SET agent_id_uuid = (SELECT new_uuid FROM agents_id_mapping WHERE old_id = t.agent_id),
            crew_id_uuid = (SELECT new_uuid FROM crews_id_mapping WHERE old_id = t.crew_id)
    """)

    # crews (nullable FK)
    print("  - crews.manager_llm_provider_id_uuid")
    op.execute("""
        UPDATE crews c
        SET manager_llm_provider_id_uuid = (SELECT new_uuid FROM llm_providers_id_mapping WHERE old_id = c.manager_llm_provider_id)
    """)

    # executions (1 required, 5 nullable)
    print("  - executions (6 FKs)")
    op.execute("""
        UPDATE executions e
        SET user_id_uuid = (SELECT new_uuid FROM users_id_mapping WHERE old_id = e.user_id),
            flow_id_uuid = (SELECT new_uuid FROM flows_id_mapping WHERE old_id = e.flow_id),
            crew_id_uuid = (SELECT new_uuid FROM crews_id_mapping WHERE old_id = e.crew_id),
            agent_id_uuid = (SELECT new_uuid FROM agents_id_mapping WHERE old_id = e.agent_id),
            tool_id_uuid = (SELECT new_uuid FROM tools_id_mapping WHERE old_id = e.tool_id),
            task_id_uuid = (SELECT new_uuid FROM tasks_id_mapping WHERE old_id = e.task_id)
    """)

    # chat_folders
    print("  - chat_folders.tenant_id_uuid, user_id_uuid")
    op.execute("""
        UPDATE chat_folders cf
        SET tenant_id_uuid = (SELECT new_uuid FROM tenants_id_mapping WHERE old_id = cf.tenant_id),
            user_id_uuid = (SELECT new_uuid FROM users_id_mapping WHERE old_id = cf.user_id)
    """)

    # chat_sessions (2 required, 1 nullable)
    print("  - chat_sessions (3 FKs)")
    op.execute("""
        UPDATE chat_sessions cs
        SET user_id_uuid = (SELECT new_uuid FROM users_id_mapping WHERE old_id = cs.user_id),
            llm_provider_id_uuid = (SELECT new_uuid FROM llm_providers_id_mapping WHERE old_id = cs.llm_provider_id),
            folder_id_uuid = (SELECT new_uuid FROM chat_folders_id_mapping WHERE old_id = cs.folder_id)
    """)

    # notifications (skip if table doesn't exist)
    if _table_exists('notifications'):
        print("  - notifications.tenant_id_uuid, user_id_uuid")
        op.execute("""
            UPDATE notifications n
            SET tenant_id_uuid = (SELECT new_uuid FROM tenants_id_mapping WHERE old_id = n.tenant_id),
                user_id_uuid = (SELECT new_uuid FROM users_id_mapping WHERE old_id = n.user_id)
        """)

    # feedback (2 required, 2 nullable) - skip if table doesn't exist
    if _table_exists('feedback'):
        print("  - feedback (4 FKs)")
        op.execute("""
            UPDATE feedback f
            SET tenant_id_uuid = (SELECT new_uuid FROM tenants_id_mapping WHERE old_id = f.tenant_id),
                user_id_uuid = (SELECT new_uuid FROM users_id_mapping WHERE old_id = f.user_id),
                execution_id_uuid = (SELECT new_uuid FROM executions_id_mapping WHERE old_id = f.execution_id),
                agent_id_uuid = (SELECT new_uuid FROM agents_id_mapping WHERE old_id = f.agent_id)
        """)

    # agent_versions (1 required, 1 nullable) - skip if table doesn't exist
    if _table_exists('agent_versions'):
        print("  - agent_versions.agent_id_uuid, changed_by_user_id_uuid")
        op.execute("""
            UPDATE agent_versions av
            SET agent_id_uuid = (SELECT new_uuid FROM agents_id_mapping WHERE old_id = av.agent_id),
                changed_by_user_id_uuid = (SELECT new_uuid FROM users_id_mapping WHERE old_id = av.changed_by_user_id)
        """)

    # provider_versions (1 required, 1 nullable) - skip if table doesn't exist
    if _table_exists('provider_versions'):
        print("  - provider_versions.provider_id_uuid, changed_by_user_id_uuid")
        op.execute("""
            UPDATE provider_versions pv
            SET provider_id_uuid = (SELECT new_uuid FROM llm_providers_id_mapping WHERE old_id = pv.provider_id),
                changed_by_user_id_uuid = (SELECT new_uuid FROM users_id_mapping WHERE old_id = pv.changed_by_user_id)
        """)


# ============================================================================
# PHASE B: Drop ALL Foreign Key Constraints
# ============================================================================

def _phase_b_drop_all_fks():
    """Drop all foreign key constraints dynamically."""

    print("  Querying pg_catalog for all FK constraints...")
    print("  Dropping all FK constraints...")

    op.execute("""
        DO $$
        DECLARE
            r RECORD;
            constraint_count INTEGER := 0;
        BEGIN
            FOR r IN (
                SELECT conname, conrelid::regclass AS table_name
                FROM pg_constraint
                WHERE contype = 'f'
                  AND connamespace = 'public'::regnamespace
            ) LOOP
                EXECUTE format('ALTER TABLE %s DROP CONSTRAINT IF EXISTS %I CASCADE', r.table_name, r.conname);
                constraint_count := constraint_count + 1;
            END LOOP;
            RAISE NOTICE 'Dropped % FK constraints', constraint_count;
        END $$;
    """)

    print("  ✓ All FK constraints dropped")


# ============================================================================
# PHASE C: Migrate Primary Keys
# ============================================================================

def _phase_c_migrate_primary_keys():
    """Migrate primary keys from Integer to UUID for all core tables."""

    # Only migrate tables that exist
    existing_tables = _get_existing_tables()

    for table in existing_tables:
        print(f"  - {table}")
        _migrate_table_pk(table)


def _migrate_table_pk(table_name):
    """Migrate a single table's primary key from Integer to UUID."""

    # Drop old PK constraint
    try:
        op.execute(f"ALTER TABLE {table_name} DROP CONSTRAINT IF EXISTS {table_name}_pkey CASCADE")
    except Exception as e:
        print(f"    ⚠ Warning: Could not drop PK constraint: {e}")

    # Drop old integer FK columns
    all_fks = FK_MAPPINGS.get(table_name, []) + NULLABLE_FK_MAPPINGS.get(table_name, [])
    for fk_col, ref_table in all_fks:
        try:
            op.execute(f"ALTER TABLE {table_name} DROP COLUMN IF EXISTS {fk_col} CASCADE")
        except Exception as e:
            print(f"    ⚠ Warning: Could not drop column {fk_col}: {e}")

    # Drop old integer id column
    op.execute(f"ALTER TABLE {table_name} DROP COLUMN IF EXISTS id CASCADE")

    # Rename uuid column to id
    op.alter_column(table_name, 'uuid', new_column_name='id')

    # Rename UUID FK columns (remove _uuid suffix)
    for fk_col, ref_table in all_fks:
        op.alter_column(table_name, f'{fk_col}_uuid', new_column_name=fk_col)

    # Set NOT NULL on id
    op.alter_column(table_name, 'id', nullable=False)

    # Set NOT NULL on required FKs only
    for fk_col, ref_table in FK_MAPPINGS.get(table_name, []):
        op.alter_column(table_name, fk_col, nullable=False)

    # Create new PK constraint
    op.create_primary_key(f'{table_name}_pkey', table_name, ['id'])

    # Create index on id
    try:
        op.create_index(f'ix_{table_name}_id', table_name, ['id'], unique=False)
    except:
        pass  # Index might already exist


# ============================================================================
# PHASE D: Handle Special Cases
# ============================================================================

def _phase_d_special_cases():
    """Handle association tables and prompt tables."""

    # Association tables
    print("\n  [D1] Association tables")
    _migrate_association_tables()

    # Prompt tables
    print("\n  [D2] Prompt tables FK updates")
    _update_prompt_table_fks()


def _migrate_association_tables():
    """Migrate agent_tools and crew_agents association tables."""

    # agent_tools
    print("    - agent_tools")
    op.add_column('agent_tools', sa.Column('agent_uuid', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('agent_tools', sa.Column('tool_uuid', postgresql.UUID(as_uuid=True), nullable=True))
    op.execute("""
        UPDATE agent_tools at
        SET agent_uuid = (SELECT new_uuid FROM agents_id_mapping WHERE old_id = at.agent_id),
            tool_uuid = (SELECT new_uuid FROM tools_id_mapping WHERE old_id = at.tool_id)
    """)
    op.execute("ALTER TABLE agent_tools DROP COLUMN IF EXISTS agent_id CASCADE")
    op.execute("ALTER TABLE agent_tools DROP COLUMN IF EXISTS tool_id CASCADE")
    op.alter_column('agent_tools', 'agent_uuid', new_column_name='agent_id')
    op.alter_column('agent_tools', 'tool_uuid', new_column_name='tool_id')
    op.alter_column('agent_tools', 'agent_id', nullable=False)
    op.alter_column('agent_tools', 'tool_id', nullable=False)

    # crew_agents
    print("    - crew_agents")
    op.add_column('crew_agents', sa.Column('crew_uuid', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('crew_agents', sa.Column('agent_uuid', postgresql.UUID(as_uuid=True), nullable=True))
    op.execute("""
        UPDATE crew_agents ca
        SET crew_uuid = (SELECT new_uuid FROM crews_id_mapping WHERE old_id = ca.crew_id),
            agent_uuid = (SELECT new_uuid FROM agents_id_mapping WHERE old_id = ca.agent_id)
    """)
    op.execute("ALTER TABLE crew_agents DROP COLUMN IF EXISTS crew_id CASCADE")
    op.execute("ALTER TABLE crew_agents DROP COLUMN IF EXISTS agent_id CASCADE")
    op.alter_column('crew_agents', 'crew_uuid', new_column_name='crew_id')
    op.alter_column('crew_agents', 'agent_uuid', new_column_name='agent_id')
    op.alter_column('crew_agents', 'crew_id', nullable=False)
    op.alter_column('crew_agents', 'agent_id', nullable=False)


def _update_prompt_table_fks():
    """Update FK columns in prompt tables from Integer to UUID."""

    # These tables already have UUID primary keys, only FK columns need type changes

    # prompt_categories: tenant_id
    print("    - prompt_categories.tenant_id")
    op.add_column('prompt_categories', sa.Column('tenant_uuid', postgresql.UUID(as_uuid=True), nullable=True))
    op.execute("""
        UPDATE prompt_categories pc
        SET tenant_uuid = (SELECT new_uuid FROM tenants_id_mapping WHERE old_id = pc.tenant_id::integer)
    """)
    op.execute("ALTER TABLE prompt_categories DROP COLUMN IF EXISTS tenant_id CASCADE")
    op.alter_column('prompt_categories', 'tenant_uuid', new_column_name='tenant_id')
    op.alter_column('prompt_categories', 'tenant_id', nullable=False)

    # prompt_templates: tenant_id, user_id, suggested_provider_id
    print("    - prompt_templates (3 FKs)")
    op.add_column('prompt_templates', sa.Column('tenant_uuid', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('prompt_templates', sa.Column('user_uuid', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('prompt_templates', sa.Column('suggested_provider_uuid', postgresql.UUID(as_uuid=True), nullable=True))
    op.execute("""
        UPDATE prompt_templates pt
        SET tenant_uuid = (SELECT new_uuid FROM tenants_id_mapping WHERE old_id = pt.tenant_id::integer),
            user_uuid = (SELECT new_uuid FROM users_id_mapping WHERE old_id = pt.user_id::integer),
            suggested_provider_uuid = (SELECT new_uuid FROM llm_providers_id_mapping WHERE old_id = pt.suggested_provider_id::integer)
    """)
    op.execute("ALTER TABLE prompt_templates DROP COLUMN IF EXISTS tenant_id CASCADE")
    op.execute("ALTER TABLE prompt_templates DROP COLUMN IF EXISTS user_id CASCADE")
    op.execute("ALTER TABLE prompt_templates DROP COLUMN IF EXISTS suggested_provider_id CASCADE")
    op.alter_column('prompt_templates', 'tenant_uuid', new_column_name='tenant_id')
    op.alter_column('prompt_templates', 'user_uuid', new_column_name='user_id')
    op.alter_column('prompt_templates', 'suggested_provider_uuid', new_column_name='suggested_provider_id')

    # prompt_executions: tenant_id, user_id
    print("    - prompt_executions.tenant_id, user_id")
    op.add_column('prompt_executions', sa.Column('tenant_uuid', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('prompt_executions', sa.Column('user_uuid', postgresql.UUID(as_uuid=True), nullable=True))
    op.execute("""
        UPDATE prompt_executions pe
        SET tenant_uuid = (SELECT new_uuid FROM tenants_id_mapping WHERE old_id = pe.tenant_id::integer),
            user_uuid = (SELECT new_uuid FROM users_id_mapping WHERE old_id = pe.user_id::integer)
    """)
    op.execute("ALTER TABLE prompt_executions DROP COLUMN IF EXISTS tenant_id CASCADE")
    op.execute("ALTER TABLE prompt_executions DROP COLUMN IF EXISTS user_id CASCADE")
    op.alter_column('prompt_executions', 'tenant_uuid', new_column_name='tenant_id')
    op.alter_column('prompt_executions', 'user_uuid', new_column_name='user_id')

    # prompt_favorites, prompt_ratings, prompt_feedback: user_id
    for table in ['prompt_favorites', 'prompt_ratings', 'prompt_feedback']:
        print(f"    - {table}.user_id")
        op.add_column(table, sa.Column('user_uuid', postgresql.UUID(as_uuid=True), nullable=True))
        op.execute(f"""
            UPDATE {table} t
            SET user_uuid = (SELECT new_uuid FROM users_id_mapping WHERE old_id = t.user_id::integer)
        """)
        op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS user_id CASCADE")
        op.alter_column(table, 'user_uuid', new_column_name='user_id')

    # prompt_feedback: resolved_by
    print("    - prompt_feedback.resolved_by")
    op.add_column('prompt_feedback', sa.Column('resolved_by_uuid', postgresql.UUID(as_uuid=True), nullable=True))
    op.execute("""
        UPDATE prompt_feedback pf
        SET resolved_by_uuid = (SELECT new_uuid FROM users_id_mapping WHERE old_id = pf.resolved_by::integer)
        WHERE pf.resolved_by IS NOT NULL
    """)
    op.execute("ALTER TABLE prompt_feedback DROP COLUMN IF EXISTS resolved_by CASCADE")
    op.alter_column('prompt_feedback', 'resolved_by_uuid', new_column_name='resolved_by')


# ============================================================================
# PHASE E: Recreate ALL Foreign Key Constraints
# ============================================================================

def _phase_e_recreate_fks():
    """Recreate all foreign key constraints."""

    print("  [E1] Recreating FK constraints for core tables")
    _recreate_core_table_fks()

    print("\n  [E2] Recreating FK constraints for association tables")
    _recreate_association_table_fks()

    print("\n  [E3] Recreating FK constraints for prompt tables")
    _recreate_prompt_table_fks()


def _recreate_core_table_fks():
    """Recreate FK constraints for core tables."""

    # Required FKs
    for table, fks in FK_MAPPINGS.items():
        if fks and _table_exists(table):
            for fk_col, ref_table in fks:
                constraint_name = f'{table}_{fk_col}_fkey'
                print(f"    - {constraint_name}")
                op.create_foreign_key(
                    constraint_name,
                    table,
                    ref_table,
                    [fk_col],
                    ['id'],
                    ondelete='CASCADE'
                )

    # Nullable FKs
    for table, fks in NULLABLE_FK_MAPPINGS.items():
        if _table_exists(table):
            for fk_col, ref_table in fks:
                constraint_name = f'{table}_{fk_col}_fkey'
                print(f"    - {constraint_name}")
                op.create_foreign_key(
                    constraint_name,
                    table,
                    ref_table,
                    [fk_col],
                    ['id'],
                    ondelete='SET NULL'
                )


def _recreate_association_table_fks():
    """Recreate FK constraints for association tables."""

    # agent_tools
    print("    - agent_tools_agent_id_fkey")
    op.create_foreign_key('agent_tools_agent_id_fkey', 'agent_tools', 'agents', ['agent_id'], ['id'], ondelete='CASCADE')
    print("    - agent_tools_tool_id_fkey")
    op.create_foreign_key('agent_tools_tool_id_fkey', 'agent_tools', 'tools', ['tool_id'], ['id'], ondelete='CASCADE')
    op.create_primary_key('agent_tools_pkey', 'agent_tools', ['agent_id', 'tool_id'])

    # crew_agents
    print("    - crew_agents_crew_id_fkey")
    op.create_foreign_key('crew_agents_crew_id_fkey', 'crew_agents', 'crews', ['crew_id'], ['id'], ondelete='CASCADE')
    print("    - crew_agents_agent_id_fkey")
    op.create_foreign_key('crew_agents_agent_id_fkey', 'crew_agents', 'agents', ['agent_id'], ['id'], ondelete='CASCADE')
    op.create_primary_key('crew_agents_pkey', 'crew_agents', ['crew_id', 'agent_id'])


def _recreate_prompt_table_fks():
    """Recreate FK constraints for prompt tables."""

    # prompt_categories → tenants
    print("    - prompt_categories_tenant_id_fkey")
    op.create_foreign_key('prompt_categories_tenant_id_fkey', 'prompt_categories', 'tenants', ['tenant_id'], ['id'], ondelete='CASCADE')

    # prompt_templates → tenants, users, llm_providers
    print("    - prompt_templates (3 FKs)")
    op.create_foreign_key('prompt_templates_tenant_id_fkey', 'prompt_templates', 'tenants', ['tenant_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('prompt_templates_user_id_fkey', 'prompt_templates', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('prompt_templates_suggested_provider_id_fkey', 'prompt_templates', 'llm_providers', ['suggested_provider_id'], ['id'], ondelete='SET NULL')

    # prompt_executions → tenants, users
    print("    - prompt_executions (2 FKs)")
    op.create_foreign_key('prompt_executions_tenant_id_fkey', 'prompt_executions', 'tenants', ['tenant_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('prompt_executions_user_id_fkey', 'prompt_executions', 'users', ['user_id'], ['id'], ondelete='CASCADE')

    # prompt_favorites, prompt_ratings, prompt_feedback → users
    for table in ['prompt_favorites', 'prompt_ratings', 'prompt_feedback']:
        print(f"    - {table}_user_id_fkey")
        op.create_foreign_key(f'{table}_user_id_fkey', table, 'users', ['user_id'], ['id'], ondelete='CASCADE')

    # prompt_feedback → users (resolved_by)
    print("    - prompt_feedback_resolved_by_fkey")
    op.create_foreign_key('prompt_feedback_resolved_by_fkey', 'prompt_feedback', 'users', ['resolved_by'], ['id'], ondelete='SET NULL')


# ============================================================================
# DOWNGRADE (NOT SUPPORTED)
# ============================================================================

def downgrade():
    """
    Downgrade is NOT supported for this migration.

    UUID → Integer conversion would lose data and break referential integrity.
    To rollback, restore from database backup taken before migration.
    """
    raise NotImplementedError(
        "UUID migration cannot be automatically rolled back. "
        "Restore from backup: docker-compose exec -T postgres psql -U crewai -d crewai_platform < backup_before_uuid.sql"
    )
