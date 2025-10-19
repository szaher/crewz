"""add_worker_architecture_fields_to_execution

Adds worker architecture support fields to executions table:
- priority (1-10, lower is higher priority)
- queue_position (ephemeral position in queue)
- retry_count (number of retry attempts)
- timeout_seconds (execution timeout, default 10 minutes)
- parent_execution_id (for re-executions with versioning)
- artifact_version (version number for artifacts)
- cancellation_requested (graceful cancellation flag)
- worker_id (worker instance that processed execution)

Also adds 'queued' status to ExecutionStatus enum.

All fields are NULLABLE for backward compatibility.

Revision ID: c5cfaf11e788
Revises: 20251015_000001
Create Date: 2025-10-17 09:38:48.089704

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c5cfaf11e788'
down_revision: Union[str, Sequence[str], None] = '20251015_000001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add worker architecture fields."""

    # Add 'queued' status to ExecutionStatus enum
    op.execute("ALTER TYPE executionstatus ADD VALUE IF NOT EXISTS 'queued'")

    # Add worker architecture fields to executions table (all nullable for safety)
    op.add_column('executions', sa.Column('priority', sa.Integer(), nullable=True, server_default='5'))
    op.add_column('executions', sa.Column('queue_position', sa.Integer(), nullable=True))
    op.add_column('executions', sa.Column('retry_count', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('executions', sa.Column('timeout_seconds', sa.Integer(), nullable=True, server_default='600'))
    op.add_column('executions', sa.Column('parent_execution_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('executions', sa.Column('artifact_version', sa.Integer(), nullable=True, server_default='1'))
    op.add_column('executions', sa.Column('cancellation_requested', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('executions', sa.Column('worker_id', sa.String(length=255), nullable=True))

    # Create indexes for query performance
    op.create_index(op.f('ix_executions_priority'), 'executions', ['priority'], unique=False)
    op.create_index(op.f('ix_executions_parent_execution_id'), 'executions', ['parent_execution_id'], unique=False)
    op.create_index(op.f('ix_executions_worker_id'), 'executions', ['worker_id'], unique=False)

    # Create foreign key for parent_execution_id (self-referencing for re-executions)
    op.create_foreign_key(
        'fk_executions_parent_execution',
        'executions', 'executions',
        ['parent_execution_id'], ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    """Downgrade schema - remove worker architecture fields."""

    # Drop foreign key
    op.drop_constraint('fk_executions_parent_execution', 'executions', type_='foreignkey')

    # Drop indexes
    op.drop_index(op.f('ix_executions_worker_id'), table_name='executions')
    op.drop_index(op.f('ix_executions_parent_execution_id'), table_name='executions')
    op.drop_index(op.f('ix_executions_priority'), table_name='executions')

    # Drop columns
    op.drop_column('executions', 'worker_id')
    op.drop_column('executions', 'cancellation_requested')
    op.drop_column('executions', 'artifact_version')
    op.drop_column('executions', 'parent_execution_id')
    op.drop_column('executions', 'timeout_seconds')
    op.drop_column('executions', 'retry_count')
    op.drop_column('executions', 'queue_position')
    op.drop_column('executions', 'priority')

    # Note: Cannot remove 'queued' enum value (PostgreSQL limitation)
