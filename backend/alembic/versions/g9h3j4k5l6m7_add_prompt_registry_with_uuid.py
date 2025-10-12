"""add prompt registry with uuid

Revision ID: g9h3j4k5l6m7
Revises: f8a2b5c3d7e9
Create Date: 2025-10-11 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'g9h3j4k5l6m7'
down_revision = 'f8a2b5c3d7e9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add prompt registry tables with UUID support.

    This migration adds:
    - UUID extension for PostgreSQL
    - prompt_categories table for organizing prompts
    - prompt_templates table with model parameters and command support
    - prompt_versions table for version control
    - prompt_favorites table for user favorites
    - prompt_ratings table for 1-5 star ratings
    - prompt_feedback table for user feedback
    - prompt_executions table for tracking usage
    """

    # Enable UUID extension
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # Create prompt_categories table
    op.create_table(
        'prompt_categories',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('icon', sa.String(50), nullable=True),
        sa.Column('color', sa.String(20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create prompt_templates table
    op.create_table(
        'prompt_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('category_id', postgresql.UUID(as_uuid=True), nullable=True),

        # Core fields
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),

        # Model recommendations
        sa.Column('suggested_model', sa.String(100), nullable=True),
        sa.Column('suggested_provider_id', sa.Integer(), nullable=True),

        # Execution parameters
        sa.Column('default_temperature', sa.Numeric(3, 2), server_default='0.7', nullable=False),
        sa.Column('default_top_p', sa.Numeric(3, 2), server_default='1.0', nullable=False),
        sa.Column('default_top_k', sa.Integer(), nullable=True),
        sa.Column('default_max_tokens', sa.Integer(), nullable=True),
        sa.Column('default_frequency_penalty', sa.Numeric(3, 2), server_default='0.0', nullable=False),
        sa.Column('default_presence_penalty', sa.Numeric(3, 2), server_default='0.0', nullable=False),

        # Metadata
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('variables', postgresql.JSONB, nullable=True),
        sa.Column('is_public', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('is_command_enabled', sa.Boolean(), server_default='true', nullable=False),

        # Version control
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('parent_version_id', postgresql.UUID(as_uuid=True), nullable=True),

        # Usage and ranking
        sa.Column('usage_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('average_rating', sa.Numeric(3, 2), server_default='0.0', nullable=False),
        sa.Column('total_ratings', sa.Integer(), server_default='0', nullable=False),
        sa.Column('total_feedback', sa.Integer(), server_default='0', nullable=False),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['category_id'], ['prompt_categories.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['suggested_provider_id'], ['llm_providers.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['parent_version_id'], ['prompt_templates.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'slug', name='unique_prompt_slug_per_tenant'),
        sa.UniqueConstraint('tenant_id', 'name', 'version', name='unique_prompt_name_per_tenant')
    )

    # Create prompt_versions table
    op.create_table(
        'prompt_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('prompt_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('variables', postgresql.JSONB, nullable=True),
        sa.Column('model_params', postgresql.JSONB, nullable=True),
        sa.Column('change_summary', sa.Text(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

        sa.ForeignKeyConstraint(['prompt_id'], ['prompt_templates.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('prompt_id', 'version', name='unique_prompt_version')
    )

    # Create prompt_favorites table
    op.create_table(
        'prompt_favorites',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('prompt_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['prompt_id'], ['prompt_templates.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'prompt_id', name='unique_user_prompt_favorite')
    )

    # Create prompt_ratings table
    op.create_table(
        'prompt_ratings',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('prompt_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

        sa.ForeignKeyConstraint(['prompt_id'], ['prompt_templates.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'prompt_id', name='unique_user_prompt_rating'),
        sa.CheckConstraint('rating >= 1 AND rating <= 5', name='check_rating_range')
    )

    # Create prompt_feedback table
    op.create_table(
        'prompt_feedback',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('prompt_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('feedback_type', sa.String(50), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('is_resolved', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('resolved_by', sa.Integer(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

        sa.ForeignKeyConstraint(['prompt_id'], ['prompt_templates.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['resolved_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create prompt_executions table
    op.create_table(
        'prompt_executions',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('prompt_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),

        # Execution context
        sa.Column('context_type', sa.String(50), nullable=False),
        sa.Column('context_id', postgresql.UUID(as_uuid=True), nullable=True),

        # Execution details
        sa.Column('variables_used', postgresql.JSONB, nullable=True),
        sa.Column('model_used', sa.String(100), nullable=True),
        sa.Column('parameters_used', postgresql.JSONB, nullable=True),

        # Results
        sa.Column('rendered_content', sa.Text(), nullable=True),
        sa.Column('execution_time_ms', sa.Integer(), nullable=True),
        sa.Column('success', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),

        # User feedback
        sa.Column('user_satisfaction', sa.Integer(), nullable=True),

        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

        sa.ForeignKeyConstraint(['prompt_id'], ['prompt_templates.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('user_satisfaction >= 1 AND user_satisfaction <= 5', name='check_satisfaction_range')
    )

    # Create indexes for performance
    op.create_index('idx_prompts_tenant', 'prompt_templates', ['tenant_id'])
    op.create_index('idx_prompts_user', 'prompt_templates', ['user_id'])
    op.create_index('idx_prompts_category', 'prompt_templates', ['category_id'])
    op.create_index('idx_prompts_slug', 'prompt_templates', ['slug'])
    op.create_index('idx_prompts_tags', 'prompt_templates', ['tags'], postgresql_using='gin')
    op.create_index('idx_prompts_public', 'prompt_templates', ['is_public'], postgresql_where=sa.text('is_public = true'))
    op.create_index('idx_prompts_commands', 'prompt_templates', ['slug', 'is_command_enabled'], postgresql_where=sa.text('is_command_enabled = true'))
    op.create_index('idx_prompts_rating', 'prompt_templates', [sa.text('average_rating DESC')])
    op.create_index('idx_prompt_versions_prompt', 'prompt_versions', ['prompt_id'])
    op.create_index('idx_prompt_ratings_prompt', 'prompt_ratings', ['prompt_id'])
    op.create_index('idx_prompt_feedback_prompt', 'prompt_feedback', ['prompt_id'])
    op.create_index('idx_prompt_executions_prompt', 'prompt_executions', ['prompt_id'])
    op.create_index('idx_prompt_executions_user', 'prompt_executions', ['user_id'])
    op.create_index('idx_prompt_executions_context', 'prompt_executions', ['context_type', 'context_id'])


def downgrade() -> None:
    """Remove prompt registry tables and UUID extension."""
    # Drop indexes
    op.drop_index('idx_prompt_executions_context', table_name='prompt_executions')
    op.drop_index('idx_prompt_executions_user', table_name='prompt_executions')
    op.drop_index('idx_prompt_executions_prompt', table_name='prompt_executions')
    op.drop_index('idx_prompt_feedback_prompt', table_name='prompt_feedback')
    op.drop_index('idx_prompt_ratings_prompt', table_name='prompt_ratings')
    op.drop_index('idx_prompt_versions_prompt', table_name='prompt_versions')
    op.drop_index('idx_prompts_rating', table_name='prompt_templates')
    op.drop_index('idx_prompts_commands', table_name='prompt_templates')
    op.drop_index('idx_prompts_public', table_name='prompt_templates')
    op.drop_index('idx_prompts_tags', table_name='prompt_templates')
    op.drop_index('idx_prompts_slug', table_name='prompt_templates')
    op.drop_index('idx_prompts_category', table_name='prompt_templates')
    op.drop_index('idx_prompts_user', table_name='prompt_templates')
    op.drop_index('idx_prompts_tenant', table_name='prompt_templates')

    # Drop tables in reverse order
    op.drop_table('prompt_executions')
    op.drop_table('prompt_feedback')
    op.drop_table('prompt_ratings')
    op.drop_table('prompt_favorites')
    op.drop_table('prompt_versions')
    op.drop_table('prompt_templates')
    op.drop_table('prompt_categories')

    # Note: We don't drop the uuid-ossp extension as it might be used by other features
