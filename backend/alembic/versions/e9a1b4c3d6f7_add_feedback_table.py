"""add feedback table

Revision ID: e9a1b4c3d6f7
Revises: d8f3a9b1c2d5
Create Date: 2025-10-06 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'e9a1b4c3d6f7'
down_revision = 'd8f3a9b1c2d5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add feedback table for Phase 3.2.

    Enables users to rate and comment on executions, agents, and chat interactions.
    """

    # Create feedback table
    op.create_table(
        'feedback',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

        # Tenant and user
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),

        # Feedback type and target
        sa.Column('feedback_type', sa.String(20), nullable=False),
        sa.Column('execution_id', sa.Integer(), nullable=True),
        sa.Column('agent_id', sa.Integer(), nullable=True),
        sa.Column('chat_session_id', sa.String(255), nullable=True),

        # Rating and feedback
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),

        # Sentiment analysis
        sa.Column('sentiment', sa.String(20), nullable=True),
        sa.Column('sentiment_score', sa.Float(), nullable=True),

        # Tags and extra data
        sa.Column('tags', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('extra_data', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='{}'),

        # Foreign keys
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['execution_id'], ['executions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='SET NULL'),

        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for performance
    op.create_index('ix_feedback_tenant_id', 'feedback', ['tenant_id'])
    op.create_index('ix_feedback_user_id', 'feedback', ['user_id'])
    op.create_index('ix_feedback_type', 'feedback', ['feedback_type'])
    op.create_index('ix_feedback_execution_id', 'feedback', ['execution_id'])
    op.create_index('ix_feedback_agent_id', 'feedback', ['agent_id'])
    op.create_index('ix_feedback_chat_session_id', 'feedback', ['chat_session_id'])
    op.create_index('ix_feedback_rating', 'feedback', ['rating'])
    op.create_index('ix_feedback_sentiment', 'feedback', ['sentiment'])
    op.create_index('ix_feedback_created_at', 'feedback', ['created_at'])

    # Composite index for common queries
    op.create_index('ix_feedback_tenant_type_created', 'feedback', ['tenant_id', 'feedback_type', 'created_at'])


def downgrade() -> None:
    """Remove feedback table and enum types."""

    # Drop indexes
    op.drop_index('ix_feedback_tenant_type_created', table_name='feedback')
    op.drop_index('ix_feedback_created_at', table_name='feedback')
    op.drop_index('ix_feedback_sentiment', table_name='feedback')
    op.drop_index('ix_feedback_rating', table_name='feedback')
    op.drop_index('ix_feedback_chat_session_id', table_name='feedback')
    op.drop_index('ix_feedback_agent_id', table_name='feedback')
    op.drop_index('ix_feedback_execution_id', table_name='feedback')
    op.drop_index('ix_feedback_type', table_name='feedback')
    op.drop_index('ix_feedback_user_id', table_name='feedback')
    op.drop_index('ix_feedback_tenant_id', table_name='feedback')

    # Drop table
    op.drop_table('feedback')
