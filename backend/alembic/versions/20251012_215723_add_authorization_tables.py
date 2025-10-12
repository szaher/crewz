"""Add authorization tables (Permission, Role, Policy, AuthorizationAuditLog).

This migration adds the authorization system tables:
- permissions: Fine-grained permission grants for users/roles on resources
- roles: Named collections of permissions (system and tenant-specific)
- user_roles: Many-to-many association table for User <-> Role
- policies: Tenant-level or user-level authorization rules with pattern matching
- authorization_audit_logs: Records all authorization checks for compliance

Revision ID: 20251012_215723
Revises: 20251012_040852
Create Date: 2025-10-12 21:57:23

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from uuid import UUID

# revision identifiers, used by Alembic.
revision = '20251012_215723'
down_revision = '20251012_040852'  # UUID migration
branch_labels = None
depends_on = None


def upgrade():
    # Create enum types (CREATE IF NOT EXISTS to handle existing types)
    op.execute("DO $$ BEGIN CREATE TYPE subjecttype AS ENUM ('user', 'role'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
    op.execute("DO $$ BEGIN CREATE TYPE action AS ENUM ('read', 'write', 'execute', 'delete', '*'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
    op.execute("DO $$ BEGIN CREATE TYPE effect AS ENUM ('allow', 'deny'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
    op.execute("DO $$ BEGIN CREATE TYPE policyscope AS ENUM ('tenant', 'user'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
    op.execute("DO $$ BEGIN CREATE TYPE auditdecision AS ENUM ('allow', 'deny'); EXCEPTION WHEN duplicate_object THEN null; END $$;")

    # Create roles table
    op.create_table(
        'roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_system_role', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_roles_tenant', 'roles', ['tenant_id'])
    op.create_index('idx_roles_slug', 'roles', ['slug'])

    # Unique constraint: system roles have globally unique slugs, tenant roles unique per tenant
    op.execute("""
        ALTER TABLE roles ADD CONSTRAINT unique_role_slug
        UNIQUE (COALESCE(tenant_id, '00000000-0000-0000-0000-000000000000'::uuid), slug)
    """)

    # Create user_roles association table
    op.create_table(
        'user_roles',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assigned_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('assigned_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['assigned_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'role_id')
    )
    op.create_index('idx_user_roles_user', 'user_roles', ['user_id'])
    op.create_index('idx_user_roles_role', 'user_roles', ['role_id'])

    # Create permissions table
    op.create_table(
        'permissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('subject_type', sa.Enum('user', 'role', name='subjecttype'), nullable=False),
        sa.Column('subject_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=False),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.Enum('read', 'write', 'execute', 'delete', '*', name='action'), nullable=False),
        sa.Column('effect', sa.Enum('allow', 'deny', name='effect'), nullable=False, server_default='allow'),
        sa.Column('conditions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_permissions_subject', 'permissions', ['subject_type', 'subject_id'])
    op.create_index('idx_permissions_resource', 'permissions', ['resource_type', 'resource_id'])
    op.create_index('idx_permissions_tenant', 'permissions', ['tenant_id'])

    # Unique constraint: prevent duplicate permissions
    op.execute("""
        ALTER TABLE permissions ADD CONSTRAINT unique_permission
        UNIQUE (subject_type, subject_id, resource_type,
                COALESCE(resource_id, '00000000-0000-0000-0000-000000000000'::uuid), action)
    """)

    # Create policies table
    op.create_table(
        'policies',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('scope', sa.Enum('tenant', 'user', name='policyscope'), nullable=False),
        sa.Column('scope_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('resource_pattern', sa.String(length=100), nullable=False),
        sa.Column('action_pattern', sa.String(length=50), nullable=False),
        sa.Column('effect', sa.Enum('allow', 'deny', name='effect'), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('conditions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_policies_tenant', 'policies', ['tenant_id'])
    op.create_index('idx_policies_scope', 'policies', ['scope', 'scope_id'])
    op.create_index('idx_policies_active', 'policies', ['is_active'])

    # Create authorization_audit_logs table
    op.create_table(
        'authorization_audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=False),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('decision', sa.Enum('allow', 'deny', name='auditdecision'), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('latency_ms', sa.Integer(), nullable=False),
        sa.Column('ip_address', postgresql.INET(), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_authz_audit_tenant', 'authorization_audit_logs', ['tenant_id'])
    op.create_index('idx_authz_audit_user', 'authorization_audit_logs', ['user_id'])
    op.create_index('idx_authz_audit_timestamp', 'authorization_audit_logs', ['timestamp'],
                    postgresql_using='btree', postgresql_ops={'timestamp': 'DESC'})
    op.create_index('idx_authz_audit_decision', 'authorization_audit_logs', ['decision'])

    # Insert default system roles
    op.execute("""
        INSERT INTO roles (id, tenant_id, name, slug, description, is_system_role, is_default, priority)
        VALUES
            ('018e0000-0000-0000-0000-000000000001'::uuid, NULL, 'Super Admin', 'super-admin',
             'Platform super administrator with access to all tenants', TRUE, FALSE, 1000),
            ('018e0000-0000-0000-0000-000000000002'::uuid, NULL, 'Tenant Admin', 'tenant-admin',
             'Tenant administrator with full control within their tenant', TRUE, FALSE, 900),
            ('018e0000-0000-0000-0000-000000000003'::uuid, NULL, 'Member', 'member',
             'Regular tenant member with standard permissions', TRUE, TRUE, 500),
            ('018e0000-0000-0000-0000-000000000004'::uuid, NULL, 'Viewer', 'viewer',
             'Read-only viewer with limited access', TRUE, FALSE, 100)
    """)


def downgrade():
    # Drop tables in reverse order
    op.drop_table('authorization_audit_logs')
    op.drop_table('policies')
    op.drop_table('permissions')
    op.drop_table('user_roles')
    op.drop_table('roles')

    # Drop enum types
    op.execute('DROP TYPE IF EXISTS auditdecision')
    op.execute('DROP TYPE IF EXISTS policyscope')
    op.execute('DROP TYPE IF EXISTS effect')
    op.execute('DROP TYPE IF EXISTS action')
    op.execute('DROP TYPE IF EXISTS subjecttype')
