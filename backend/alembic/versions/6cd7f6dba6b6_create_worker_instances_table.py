"""create_worker_instances_table

Revision ID: 6cd7f6dba6b6
Revises: 56109a7ea805
Create Date: 2025-10-17 09:52:25.963087

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6cd7f6dba6b6'
down_revision: Union[str, Sequence[str], None] = '56109a7ea805'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - create worker_instances table."""

    # Create WorkerStatus enum
    worker_status_enum = sa.Enum(
        'starting', 'idle', 'busy', 'crashed', 'stopped',
        name='workerstatus',
        create_type=True
    )
    worker_status_enum.create(op.get_bind(), checkfirst=True)

    # Create worker_instances table
    op.create_table(
        'worker_instances',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),

        # Worker identification
        sa.Column('worker_hostname', sa.String(255), nullable=False, unique=True),

        # Worker status
        sa.Column('status', worker_status_enum, nullable=False, server_default='starting'),

        # Current job assignment
        sa.Column('current_job_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),

        # Resource usage metrics
        sa.Column('cpu_usage_percent', sa.Float(), nullable=True),
        sa.Column('memory_usage_mb', sa.Integer(), nullable=True),

        # Health tracking
        sa.Column('last_heartbeat_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('crashed_at', sa.DateTime(timezone=True), nullable=True),

        # Foreign key constraints
        sa.ForeignKeyConstraint(['current_job_id'], ['executions.id'], ondelete='SET NULL'),

        # Unique constraint
        sa.UniqueConstraint('worker_hostname', name='uq_worker_hostname'),
    )

    # Create indexes for efficient querying
    op.create_index('ix_worker_instances_worker_hostname', 'worker_instances', ['worker_hostname'])
    op.create_index('ix_worker_instances_status', 'worker_instances', ['status'])
    op.create_index('ix_worker_instances_current_job_id', 'worker_instances', ['current_job_id'])
    op.create_index('ix_worker_instances_last_heartbeat_at', 'worker_instances', ['last_heartbeat_at'])

    # Composite index for health check queries
    op.create_index(
        'ix_worker_instances_status_heartbeat',
        'worker_instances',
        ['status', 'last_heartbeat_at']
    )


def downgrade() -> None:
    """Downgrade schema - drop worker_instances table."""

    # Drop indexes
    op.drop_index('ix_worker_instances_status_heartbeat', table_name='worker_instances')
    op.drop_index('ix_worker_instances_last_heartbeat_at', table_name='worker_instances')
    op.drop_index('ix_worker_instances_current_job_id', table_name='worker_instances')
    op.drop_index('ix_worker_instances_status', table_name='worker_instances')
    op.drop_index('ix_worker_instances_worker_hostname', table_name='worker_instances')

    # Drop table
    op.drop_table('worker_instances')

    # Drop enum
    sa.Enum(name='workerstatus').drop(op.get_bind(), checkfirst=True)
