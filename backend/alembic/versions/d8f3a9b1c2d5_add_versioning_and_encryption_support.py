"""add versioning and encryption support

Revision ID: d8f3a9b1c2d5
Revises: c7e4a55b3f7c
Create Date: 2025-10-05 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'd8f3a9b1c2d5'
down_revision = 'c7e4a55b3f7c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add version tracking tables for Agents and LLM Providers.

    This migration adds:
    - agent_versions table for tracking agent configuration history
    - provider_versions table for tracking provider configuration history
    - Support for diff storage and rollback functionality
    """

    # Create agent_versions table
    op.create_table(
        'agent_versions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('agent_id', sa.Integer(), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('action', sa.Enum('CREATE', 'UPDATE', 'ROLLBACK', name='versionaction'), nullable=False),
        sa.Column('changed_by_user_id', sa.Integer(), nullable=True),
        sa.Column('configuration', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('diff_from_previous', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('change_description', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['changed_by_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_versions_agent_id'), 'agent_versions', ['agent_id'], unique=False)

    # Create provider_versions table
    op.create_table(
        'provider_versions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('provider_id', sa.Integer(), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('action', sa.Enum('CREATE', 'UPDATE', 'ROLLBACK', name='versionaction'), nullable=False),
        sa.Column('changed_by_user_id', sa.Integer(), nullable=True),
        sa.Column('configuration', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('diff_from_previous', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('change_description', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['provider_id'], ['llm_providers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['changed_by_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_provider_versions_provider_id'), 'provider_versions', ['provider_id'], unique=False)


def downgrade() -> None:
    """Remove version tracking tables."""
    op.drop_index(op.f('ix_provider_versions_provider_id'), table_name='provider_versions')
    op.drop_table('provider_versions')

    op.drop_index(op.f('ix_agent_versions_agent_id'), table_name='agent_versions')
    op.drop_table('agent_versions')

    # Drop the enum type
    op.execute('DROP TYPE versionaction')
