"""Add notification tables (Notification, NotificationPreference).

This migration adds the notification system tables:
- notifications: User notifications with read status
- notification_preferences: Tenant and user-level notification preferences

Revision ID: 20251014_000001
Revises: 20251013_000001
Create Date: 2025-10-14 00:00:01

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251014_000001'
down_revision = '20251013_000001'  # Execution queue migration
branch_labels = None
depends_on = None


def upgrade():
    # Create enum type for preference scope
    op.execute("DO $$ BEGIN CREATE TYPE preferencescope AS ENUM ('tenant', 'user'); EXCEPTION WHEN duplicate_object THEN null; END $$;")

    # Create notifications table
    op.create_table(
        'notifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False, server_default='info',
                 comment='Notification type (info, success, warning, error)'),
        sa.Column('title', sa.String(length=255), nullable=False,
                 comment='Notification title'),
        sa.Column('message', sa.Text(), nullable=True,
                 comment='Notification message body'),
        sa.Column('data', postgresql.JSONB(astext_type=sa.Text()), nullable=True,
                 comment='Additional notification data (metadata, links, etc.)'),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default='false',
                 comment='Whether user has read this notification'),
        sa.Column('read_at', sa.DateTime(), nullable=True,
                 comment='When notification was marked as read'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for notifications
    op.create_index('idx_notifications_tenant_id', 'notifications', ['tenant_id'])
    op.create_index('idx_notifications_user_id', 'notifications', ['user_id'])
    op.create_index('idx_notifications_user_is_read', 'notifications', ['user_id', 'is_read'])
    op.create_index('idx_notifications_user_created_at', 'notifications', ['user_id', 'created_at'])
    op.create_index('idx_notifications_type', 'notifications', ['type'])
    op.create_index('idx_notifications_created_at', 'notifications', ['created_at'])

    # Create notification_preferences table
    op.create_table(
        'notification_preferences',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('scope', sa.Enum('tenant', 'user', name='preferencescope'), nullable=False,
                 comment='Scope of preference (tenant-level default or user-level override)'),
        sa.Column('scope_id', postgresql.UUID(as_uuid=True), nullable=False,
                 comment='ID of tenant or user this preference applies to'),
        sa.Column('category', sa.String(length=100), nullable=False,
                 comment='Notification category (execution_update, execution_failed, etc.)'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true',
                 comment='Whether this notification category is enabled'),
        sa.Column('delivery_channels', postgresql.ARRAY(sa.String()), nullable=False, server_default='{}',
                 comment='Array of delivery channels (websocket, email, webhook)'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('scope', 'scope_id', 'category', name='uq_notification_preference_scope_category')
    )

    # Create indexes for notification_preferences
    op.create_index('idx_notification_preferences_scope', 'notification_preferences', ['scope'])
    op.create_index('idx_notification_preferences_scope_id', 'notification_preferences', ['scope_id'])
    op.create_index('idx_notification_preferences_category', 'notification_preferences', ['category'])
    op.create_index('idx_notification_preferences_scope_scope_id', 'notification_preferences', ['scope', 'scope_id'])

    # Insert default tenant-level notification preferences for common categories
    # These will be created for each tenant when they're created, but we add common categories here
    # Note: In a real migration, you'd iterate over existing tenants and create these preferences
    # For now, this serves as a template for the application to use when creating new tenants

    # The application should create these preferences when a new tenant is created:
    # Default categories: execution_update, execution_failed, execution_completed, execution_timeout,
    #                    daily_summary, system_maintenance, security_alert


def downgrade():
    # Drop tables
    op.drop_table('notification_preferences')
    op.drop_table('notifications')

    # Drop enum types
    op.execute('DROP TYPE IF EXISTS preferencescope')
