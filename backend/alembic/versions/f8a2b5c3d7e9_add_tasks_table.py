"""add tasks table

Revision ID: f8a2b5c3d7e9
Revises: cd12ef34aa56
Create Date: 2025-10-09 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'f8a2b5c3d7e9'
down_revision = 'cd12ef34aa56'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add tasks table for CrewAI task management.

    This migration adds:
    - tasks table for storing task configurations
    - Support for agent assignment and crew association
    - Task ordering and execution configuration
    """

    # Create tasks table
    op.create_table(
        'tasks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('expected_output', sa.Text(), nullable=False),
        sa.Column('agent_id', sa.Integer(), nullable=True),
        sa.Column('crew_id', sa.Integer(), nullable=True),
        sa.Column('order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('async_execution', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('output_format', sa.Enum('TEXT', 'JSON', 'PYDANTIC', name='taskoutputformat'), nullable=False, server_default='TEXT'),
        sa.Column('output_file', sa.String(500), nullable=True),
        sa.Column('context', sa.Text(), nullable=True),
        sa.Column('tools_config', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['crew_id'], ['crews.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index(op.f('ix_tasks_agent_id'), 'tasks', ['agent_id'], unique=False)
    op.create_index(op.f('ix_tasks_crew_id'), 'tasks', ['crew_id'], unique=False)


def downgrade() -> None:
    """Remove tasks table."""
    op.drop_index(op.f('ix_tasks_crew_id'), table_name='tasks')
    op.drop_index(op.f('ix_tasks_agent_id'), table_name='tasks')
    op.drop_table('tasks')
    op.execute('DROP TYPE taskoutputformat')
