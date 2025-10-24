"""Add monitoring and observability models (Trace, TraceMetrics, Artifact, ArtifactMetadata, TenantConfig).

This migration adds comprehensive monitoring infrastructure:
- traces: LLM execution tracing with Langfuse integration
- trace_metrics: Pre-computed aggregated metrics for dashboard
- artifacts: Execution output files with S3/local storage
- artifact_metadata: Enrichment and searchable tags for artifacts
- tenant_configs: Per-tenant storage quotas and retention policies

Revision ID: 20251023_add_monitoring
Revises: add_flow_variables_config
Create Date: 2025-10-23 00:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251023_add_monitoring'
down_revision = 'add_flow_variables_config'
branch_labels = None
depends_on = None


def upgrade():
    # Create enum types for new models
    op.execute("CREATE TYPE periodtype AS ENUM ('hour', 'day', 'week', 'month')")
    op.execute("CREATE TYPE artifacttype AS ENUM ('document', 'image', 'data', 'code', 'other')")
    op.execute("CREATE TYPE cleanupstrategy AS ENUM ('oldest_first', 'largest_first', 'lru', 'block_uploads')")

    # Create traces table
    op.create_table(
        'traces',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('execution_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('tool_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('response', sa.Text(), nullable=False),
        sa.Column('model_name', sa.String(length=100), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('prompt_tokens', sa.Integer(), nullable=False),
        sa.Column('completion_tokens', sa.Integer(), nullable=False),
        sa.Column('total_tokens', sa.Integer(), nullable=False),
        sa.Column('latency_ms', sa.Integer(), nullable=False),
        sa.Column('cost_usd', postgresql.NUMERIC(10, 6), nullable=False, server_default='0'),
        sa.Column('langfuse_trace_id', sa.String(length=100), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('trace_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.CheckConstraint('total_tokens = prompt_tokens + completion_tokens', name='chk_trace_token_sum'),
        sa.CheckConstraint('latency_ms > 0', name='chk_trace_latency_positive'),
        sa.CheckConstraint('cost_usd >= 0', name='chk_trace_cost_non_negative'),
        sa.CheckConstraint('(agent_id IS NOT NULL AND tool_id IS NULL) OR (agent_id IS NULL AND tool_id IS NOT NULL)', name='chk_trace_entity_xor'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['execution_id'], ['executions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tool_id'], ['tools.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_trace_tenant_created', 'traces', ['tenant_id', 'created_at'])
    op.create_index('idx_trace_execution', 'traces', ['execution_id'])
    op.create_index('idx_trace_created', 'traces', ['created_at'])
    op.create_index('idx_trace_tenant_id', 'traces', ['tenant_id'])

    # Create trace_metrics table
    op.create_table(
        'trace_metrics',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('period_type', postgresql.ENUM('hour', 'day', 'week', 'month', name='periodtype', create_type=False), nullable=False),
        sa.Column('period_start', sa.DateTime(), nullable=False),
        sa.Column('period_end', sa.DateTime(), nullable=False),
        sa.Column('total_executions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_traces', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_tokens', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('total_cost_usd', postgresql.NUMERIC(12, 2), nullable=False, server_default='0'),
        sa.Column('avg_latency_ms', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('p50_latency_ms', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('p95_latency_ms', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('p99_latency_ms', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_rate', postgresql.NUMERIC(5, 2), nullable=False, server_default='0'),
        sa.Column('metrics_by_type', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.CheckConstraint('period_end > period_start', name='chk_metrics_period_valid'),
        sa.CheckConstraint('total_tokens >= 0', name='chk_metrics_tokens_non_negative'),
        sa.CheckConstraint('total_cost_usd >= 0', name='chk_metrics_cost_non_negative'),
        sa.CheckConstraint('error_rate >= 0 AND error_rate <= 100', name='chk_metrics_error_rate_range'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'period_type', 'period_start', name='uq_metrics_tenant_period_start')
    )
    op.create_index('idx_metrics_tenant_period', 'trace_metrics', ['tenant_id', 'period_type', 'period_start'])
    op.create_index('idx_trace_metrics_tenant_id', 'trace_metrics', ['tenant_id'])
    op.create_index('idx_trace_metrics_period_start', 'trace_metrics', ['period_start'])

    # Create file_artifacts table (renamed to avoid conflict with existing artifacts table)
    op.create_table(
        'file_artifacts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('execution_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('execution_version', sa.Integer(), nullable=False),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('file_extension', sa.String(length=10), nullable=False),
        sa.Column('file_size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=False),
        sa.Column('storage_path', sa.String(length=500), nullable=False),
        sa.Column('artifact_type', postgresql.ENUM('document', 'image', 'data', 'code', 'other', name='artifacttype', create_type=False), nullable=False),
        sa.Column('has_preview', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('preview_url', sa.String(length=500), nullable=True),
        sa.Column('last_accessed_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.CheckConstraint('file_size_bytes > 0', name='chk_artifact_size_positive'),
        sa.CheckConstraint('execution_version >= 1', name='chk_artifact_version_positive'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['execution_id'], ['executions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_file_artifact_tenant_created', 'file_artifacts', ['tenant_id', 'created_at'])
    op.create_index('idx_file_artifact_execution', 'file_artifacts', ['execution_id', 'execution_version'])
    op.create_index('idx_file_artifact_type', 'file_artifacts', ['tenant_id', 'artifact_type'])
    op.create_index('idx_file_artifact_deleted', 'file_artifacts', ['deleted_at'])
    op.create_index('idx_file_artifact_lru', 'file_artifacts', ['tenant_id', 'last_accessed_at'])
    op.create_index('idx_file_artifact_tenant_id', 'file_artifacts', ['tenant_id'])
    op.create_index('idx_file_artifact_execution_id', 'file_artifacts', ['execution_id'])

    # Create file_artifact_metadata table
    op.create_table(
        'file_artifact_metadata',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('artifact_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tags', postgresql.ARRAY(sa.String(length=50)), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('checksum_sha256', sa.String(length=64), nullable=False),
        sa.Column('compression_type', sa.String(length=20), nullable=True),
        sa.Column('related_artifacts', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['artifact_id'], ['file_artifacts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('artifact_id', name='uq_file_artifact_metadata_artifact_id')
    )
    op.create_index('idx_file_metadata_artifact', 'file_artifact_metadata', ['artifact_id'])
    # GIN indexes for full-text search on tags and description
    op.execute('CREATE INDEX idx_file_metadata_tags ON file_artifact_metadata USING GIN (tags)')
    op.execute('CREATE INDEX idx_file_metadata_description ON file_artifact_metadata USING GIN (to_tsvector(\'english\', COALESCE(description, \'\')))')

    # Create tenant_configs table
    op.create_table(
        'tenant_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('total_storage_quota_bytes', sa.BigInteger(), nullable=False),
        sa.Column('max_artifact_size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('current_storage_used_bytes', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('trace_retention_days', sa.Integer(), nullable=False),
        sa.Column('artifact_retention_days', sa.Integer(), nullable=False),
        sa.Column('cleanup_strategy', postgresql.ENUM('oldest_first', 'largest_first', 'lru', 'block_uploads', name='cleanupstrategy', create_type=False), nullable=False, server_default='lru'),
        sa.Column('quota_warning_threshold', postgresql.NUMERIC(3, 2), nullable=False, server_default='0.80'),
        sa.Column('quota_alert_threshold', postgresql.NUMERIC(3, 2), nullable=False, server_default='0.95'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.CheckConstraint('current_storage_used_bytes <= total_storage_quota_bytes', name='chk_tenant_config_quota_not_exceeded'),
        sa.CheckConstraint('max_artifact_size_bytes <= total_storage_quota_bytes', name='chk_tenant_config_max_size_valid'),
        sa.CheckConstraint('trace_retention_days >= 1', name='chk_tenant_config_trace_retention_positive'),
        sa.CheckConstraint('artifact_retention_days >= 1', name='chk_tenant_config_artifact_retention_positive'),
        sa.CheckConstraint('quota_warning_threshold > 0 AND quota_warning_threshold < quota_alert_threshold AND quota_alert_threshold <= 1.0', name='chk_tenant_config_quota_thresholds_valid'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', name='uq_tenant_config_tenant_id')
    )
    op.create_index('idx_tenant_config_tenant', 'tenant_configs', ['tenant_id'])


def downgrade():
    # Drop tables in reverse order
    op.drop_table('tenant_configs')
    op.drop_table('file_artifact_metadata')
    op.drop_table('file_artifacts')
    op.drop_table('trace_metrics')
    op.drop_table('traces')

    # Drop enum types
    op.execute('DROP TYPE IF EXISTS cleanupstrategy')
    op.execute('DROP TYPE IF EXISTS artifacttype')
    op.execute('DROP TYPE IF EXISTS periodtype')
