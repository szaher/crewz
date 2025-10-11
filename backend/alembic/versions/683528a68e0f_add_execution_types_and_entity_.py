"""add_execution_types_and_entity_references

Revision ID: 683528a68e0f
Revises: 1a372377f75e
Create Date: 2025-10-10 11:34:14.998912

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '683528a68e0f'
down_revision: Union[str, Sequence[str], None] = '1a372377f75e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # First, update the enum type to include new values
    op.execute("ALTER TYPE executiontype ADD VALUE IF NOT EXISTS 'agent'")
    op.execute("ALTER TYPE executiontype ADD VALUE IF NOT EXISTS 'tool'")
    op.execute("ALTER TYPE executiontype ADD VALUE IF NOT EXISTS 'task'")

    # Add new entity reference columns
    op.add_column('executions', sa.Column('agent_id', sa.Integer(), nullable=True))
    op.add_column('executions', sa.Column('tool_id', sa.Integer(), nullable=True))
    op.add_column('executions', sa.Column('task_id', sa.Integer(), nullable=True))

    # Add execution time tracking
    op.add_column('executions', sa.Column('execution_time_ms', sa.Integer(), nullable=True))

    # Create foreign key constraints
    op.create_foreign_key(
        'fk_executions_agent_id',
        'executions', 'agents',
        ['agent_id'], ['id']
    )
    op.create_foreign_key(
        'fk_executions_tool_id',
        'executions', 'tools',
        ['tool_id'], ['id']
    )
    op.create_foreign_key(
        'fk_executions_task_id',
        'executions', 'tasks',
        ['task_id'], ['id']
    )

    # Create indexes for performance
    op.create_index('ix_executions_agent_id', 'executions', ['agent_id'])
    op.create_index('ix_executions_tool_id', 'executions', ['tool_id'])
    op.create_index('ix_executions_task_id', 'executions', ['task_id'])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index('ix_executions_task_id', 'executions')
    op.drop_index('ix_executions_tool_id', 'executions')
    op.drop_index('ix_executions_agent_id', 'executions')

    # Drop foreign keys
    op.drop_constraint('fk_executions_task_id', 'executions', type_='foreignkey')
    op.drop_constraint('fk_executions_tool_id', 'executions', type_='foreignkey')
    op.drop_constraint('fk_executions_agent_id', 'executions', type_='foreignkey')

    # Drop columns
    op.drop_column('executions', 'execution_time_ms')
    op.drop_column('executions', 'task_id')
    op.drop_column('executions', 'tool_id')
    op.drop_column('executions', 'agent_id')
