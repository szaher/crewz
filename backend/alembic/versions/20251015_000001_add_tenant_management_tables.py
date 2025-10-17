"""Add tenant management tables (TenantRegistration) and super admin support.

This migration adds the tenant management system tables:
- tenant_registrations: Tenant registration requests pending super admin approval
- Adds is_super_admin column to users table

Revision ID: 20251015_000001
Revises: 20251014_000001
Create Date: 2025-10-15 00:00:01

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251015_000001'
down_revision = '20251014_000001'  # Notification tables migration
branch_labels = None
depends_on = None


def upgrade():
    # Create enum types for tenant registrations
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE registrationstatus AS ENUM ('pending', 'approved', 'rejected');
        EXCEPTION WHEN duplicate_object THEN null; END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE companysize AS ENUM ('1-10', '11-50', '51-200', '201-1000', '1000+');
        EXCEPTION WHEN duplicate_object THEN null; END $$;
    """)

    # Add is_super_admin column to users table
    op.add_column('users',
        sa.Column('is_super_admin', sa.Boolean(), nullable=False, server_default='false',
                 comment='Platform super administrator flag')
    )

    # Create index on is_super_admin for fast super admin lookups
    op.create_index('idx_users_is_super_admin', 'users', ['is_super_admin'],
                   postgresql_where=sa.text('is_super_admin = true'))

    # Create tenant_registrations table
    op.create_table(
        'tenant_registrations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),

        # Company information
        sa.Column('company_name', sa.String(length=255), nullable=False,
                 comment='Name of the company/organization'),
        sa.Column('admin_email', sa.String(length=255), nullable=False,
                 comment='Email address for the tenant administrator'),
        sa.Column('admin_name', sa.String(length=255), nullable=False,
                 comment='Full name of the tenant administrator'),
        sa.Column('reason', sa.Text(), nullable=False,
                 comment='Reason for registration (min 20 chars)'),

        # Optional fields
        sa.Column('sample_data_requested', sa.Boolean(), nullable=False, server_default='false',
                 comment='Whether tenant requested sample data to be loaded'),
        sa.Column('company_size', sa.Enum('1-10', '11-50', '51-200', '201-1000', '1000+', name='companysize'),
                 nullable=True, comment='Size of the company'),
        sa.Column('use_case', sa.Text(), nullable=True,
                 comment='Primary use case for the platform'),

        # Status tracking
        sa.Column('status', sa.Enum('pending', 'approved', 'rejected', name='registrationstatus'),
                 nullable=False, server_default='pending',
                 comment='Current status of the registration'),
        sa.Column('rejection_reason', sa.Text(), nullable=True,
                 comment='Reason for rejection (if status is rejected)'),

        # Approval tracking
        sa.Column('approved_by', postgresql.UUID(as_uuid=True), nullable=True,
                 comment='Super admin user ID who approved/rejected the registration'),
        sa.Column('approved_at', sa.DateTime(), nullable=True,
                 comment='When the registration was approved'),

        # Tenant reference (populated after approval)
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True,
                 comment='Reference to created tenant (populated after approval)'),

        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),

        # Foreign keys
        sa.ForeignKeyConstraint(['approved_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),

        # Constraints
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('admin_email', name='uq_tenant_registration_email')
    )

    # Create indexes for tenant_registrations
    op.create_index('idx_tenant_registrations_status', 'tenant_registrations', ['status'])
    op.create_index('idx_tenant_registrations_admin_email', 'tenant_registrations', ['admin_email'])
    op.create_index('idx_tenant_registrations_company_name', 'tenant_registrations', ['company_name'])
    op.create_index('idx_tenant_registrations_created_at', 'tenant_registrations', ['created_at'])
    op.create_index('idx_tenant_registrations_approved_by', 'tenant_registrations', ['approved_by'])
    op.create_index('idx_tenant_registrations_tenant_id', 'tenant_registrations', ['tenant_id'])


def downgrade():
    # Drop tenant_registrations table
    op.drop_table('tenant_registrations')

    # Drop is_super_admin column from users
    op.drop_index('idx_users_is_super_admin', table_name='users')
    op.drop_column('users', 'is_super_admin')

    # Drop enum types
    op.execute('DROP TYPE IF EXISTS registrationstatus;')
    op.execute('DROP TYPE IF EXISTS companysize;')
