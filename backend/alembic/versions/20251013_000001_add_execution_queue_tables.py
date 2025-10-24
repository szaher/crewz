"""Add execution queue tables (ExecutionQueue, DeadLetterTask, ExecutionMetrics).

This migration adds the async execution queue system tables:
- execution_queue: Async task execution queue with Celery integration
- dead_letter_tasks: Failed tasks after retry exhaustion
- execution_metrics: Time-series metrics for queue monitoring

Revision ID: 20251013_000001
Revises: 20251012_215723
Create Date: 2025-10-13 00:00:01

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251013_000001'
down_revision = '20251012_215723'  # Authorization migration
branch_labels = None
depends_on = None


def upgrade():
    # Create enum types for execution queue (with duplicate check)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'executionstatus') THEN
                CREATE TYPE executionstatus AS ENUM ('pending', 'running', 'completed', 'failed', 'timeout', 'cancelled');
            END IF;
        END $$;
    """)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'executionpriority') THEN
                CREATE TYPE executionpriority AS ENUM ('low', 'normal', 'high');
            END IF;
        END $$;
    """)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'executiontype') THEN
                CREATE TYPE executiontype AS ENUM ('crew', 'flow', 'agent', 'task', 'tool');
            END IF;
        END $$;
    """)

    # Create execution_queue table
    op.create_table(
        'execution_queue',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('execution_id', postgresql.UUID(as_uuid=True), nullable=False, unique=True,
                 comment='Public execution ID returned to client'),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('execution_type', postgresql.ENUM('crew', 'flow', 'agent', 'task', 'tool', name='executiontype', create_type=False), nullable=False,
                 comment='Type of entity being executed'),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=False,
                 comment='ID of the crew/flow/agent/task/tool to execute'),
        sa.Column('status', postgresql.ENUM('pending', 'running', 'completed', 'failed', 'timeout', 'cancelled', name='executionstatus', create_type=False),
                 nullable=False, server_default='pending'),
        sa.Column('priority', postgresql.ENUM('low', 'normal', 'high', name='executionpriority', create_type=False),
                 nullable=False, server_default='normal'),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0',
                 comment='Current retry attempt (0 = first attempt)'),
        sa.Column('max_retries', sa.Integer(), nullable=False, server_default='3',
                 comment='Maximum retry attempts before moving to DLQ'),
        sa.Column('celery_task_id', sa.String(length=255), nullable=True,
                 comment='Celery task ID for tracking and cancellation'),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}',
                 comment='Execution parameters (inputs, config, etc.)'),
        sa.Column('result', postgresql.JSONB(astext_type=sa.Text()), nullable=True,
                 comment='Execution result (output, artifacts, etc.)'),
        sa.Column('error', sa.Text(), nullable=True,
                 comment='Error message if execution failed'),
        sa.Column('scheduled_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()'),
                 comment='When execution was submitted to queue'),
        sa.Column('started_at', sa.DateTime(), nullable=True,
                 comment='When execution actually started processing'),
        sa.Column('completed_at', sa.DateTime(), nullable=True,
                 comment='When execution finished (success or failure)'),
        sa.Column('duration_ms', sa.Integer(), nullable=True,
                 comment='Execution duration in milliseconds'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for execution_queue
    op.create_index('idx_execution_queue_execution_id', 'execution_queue', ['execution_id'])
    op.create_index('idx_execution_queue_tenant_id', 'execution_queue', ['tenant_id'])
    op.create_index('idx_execution_queue_user_id', 'execution_queue', ['user_id'])
    op.create_index('idx_execution_queue_status', 'execution_queue', ['status'])
    op.create_index('idx_execution_queue_priority', 'execution_queue', ['priority'])
    op.create_index('idx_execution_queue_celery_task_id', 'execution_queue', ['celery_task_id'])
    op.create_index('idx_execution_queue_tenant_status', 'execution_queue', ['tenant_id', 'status'])
    op.create_index('idx_execution_queue_status_priority', 'execution_queue', ['status', 'priority'])
    op.create_index('idx_execution_queue_user_status', 'execution_queue', ['user_id', 'status'])
    op.create_index('idx_execution_queue_scheduled_at', 'execution_queue', ['scheduled_at'])

    # Create dead_letter_tasks table
    op.create_table(
        'dead_letter_tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('original_queue_id', postgresql.UUID(as_uuid=True), nullable=False,
                 comment='ID of the original execution_queue record'),
        sa.Column('execution_type', sa.String(length=50), nullable=False,
                 comment='Type of execution (crew, flow, agent, task, tool)'),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False,
                 comment='Original execution payload'),
        sa.Column('failure_reason', sa.Text(), nullable=False,
                 comment='Final error message that caused DLQ entry'),
        sa.Column('retry_history', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]',
                 comment='Array of retry attempts with timestamps, errors, durations'),
        sa.Column('failure_timestamp', sa.DateTime(), nullable=False, server_default=sa.text('NOW()'),
                 comment='When task was moved to DLQ'),
        sa.Column('is_requeued', sa.Boolean(), nullable=False, server_default='false',
                 comment='Whether task has been manually requeued'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['original_queue_id'], ['execution_queue.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for dead_letter_tasks
    op.create_index('idx_dead_letter_tasks_original_queue_id', 'dead_letter_tasks', ['original_queue_id'])
    op.create_index('idx_dead_letter_tasks_is_requeued', 'dead_letter_tasks', ['is_requeued'])

    # Create execution_metrics table
    op.create_table(
        'execution_metrics',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.text('NOW()'),
                 comment='Metric collection timestamp'),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True,
                 comment='Tenant ID (null for global metrics)'),
        sa.Column('queue_depth', sa.Integer(), nullable=False, server_default='0',
                 comment='Total pending + running executions'),
        sa.Column('pending_count', sa.Integer(), nullable=False, server_default='0',
                 comment='Executions in pending state'),
        sa.Column('running_count', sa.Integer(), nullable=False, server_default='0',
                 comment='Executions in running state'),
        sa.Column('completed_last_minute', sa.Integer(), nullable=False, server_default='0',
                 comment='Executions completed in last minute'),
        sa.Column('failed_last_minute', sa.Integer(), nullable=False, server_default='0',
                 comment='Executions failed in last minute'),
        sa.Column('processing_rate', sa.Float(), nullable=False, server_default='0.0',
                 comment='Tasks per second'),
        sa.Column('avg_duration_ms', sa.Integer(), nullable=False, server_default='0',
                 comment='Average execution duration (milliseconds)'),
        sa.Column('p95_duration_ms', sa.Integer(), nullable=False, server_default='0',
                 comment='95th percentile duration (milliseconds)'),
        sa.Column('p99_duration_ms', sa.Integer(), nullable=False, server_default='0',
                 comment='99th percentile duration (milliseconds)'),
        sa.Column('failure_rate', sa.Float(), nullable=False, server_default='0.0',
                 comment='Failure rate (0.0-1.0)'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for execution_metrics
    op.create_index('idx_execution_metrics_timestamp', 'execution_metrics', ['timestamp'])
    op.create_index('idx_execution_metrics_tenant_id', 'execution_metrics', ['tenant_id'])
    op.create_index('idx_execution_metrics_tenant_timestamp', 'execution_metrics', ['tenant_id', 'timestamp'])


def downgrade():
    # Drop tables
    op.drop_table('execution_metrics')
    op.drop_table('dead_letter_tasks')
    op.drop_table('execution_queue')

    # Drop enum types
    op.execute('DROP TYPE IF EXISTS executiontype;')
    op.execute('DROP TYPE IF EXISTS executionpriority;')
    op.execute('DROP TYPE IF EXISTS executionstatus;')
