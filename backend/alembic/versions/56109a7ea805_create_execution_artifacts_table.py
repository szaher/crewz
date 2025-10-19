"""create_execution_artifacts_table

Creates ExecutionArtifact table for storing execution output files.
Includes indexes for efficient querying by execution, version, and expiration.

Revision ID: 56109a7ea805
Revises: c5cfaf11e788
Create Date: 2025-10-17 09:51:34.376744

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '56109a7ea805'
down_revision: Union[str, Sequence[str], None] = 'c5cfaf11e788'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - create execution_artifacts table."""

    # Create ArtifactType enum
    artifact_type_enum = sa.Enum(
        'output_file', 'log_file', 'result_json', 'error_log', 'metrics_file', 'custom',
        name='artifacttype',
        create_type=True
    )
    artifact_type_enum.create(op.get_bind(), checkfirst=True)

    # Create execution_artifacts table
    op.create_table(
        'execution_artifacts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),

        # Foreign keys
        sa.Column('execution_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),

        # File information
        sa.Column('file_path', sa.String(1024), nullable=False),
        sa.Column('file_name', sa.String(255), nullable=False),
        sa.Column('file_size', sa.BigInteger(), nullable=False),
        sa.Column('mime_type', sa.String(127), nullable=True),

        # Artifact metadata
        sa.Column('artifact_type', artifact_type_enum, nullable=False, server_default='output_file'),
        sa.Column('version_number', sa.Integer(), nullable=False, server_default='1'),

        # Expiration
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),

        # Foreign key constraints
        sa.ForeignKeyConstraint(['execution_id'], ['executions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    )

    # Create indexes for efficient querying
    op.create_index('ix_execution_artifacts_execution_id', 'execution_artifacts', ['execution_id'])
    op.create_index('ix_execution_artifacts_tenant_id', 'execution_artifacts', ['tenant_id'])
    op.create_index('ix_execution_artifacts_artifact_type', 'execution_artifacts', ['artifact_type'])
    op.create_index('ix_execution_artifacts_version_number', 'execution_artifacts', ['version_number'])
    op.create_index('ix_execution_artifacts_expires_at', 'execution_artifacts', ['expires_at'])

    # Composite index for execution + version lookup
    op.create_index(
        'ix_execution_artifacts_execution_version',
        'execution_artifacts',
        ['execution_id', 'version_number']
    )

    # Composite index for cleanup job (expired artifacts by tenant)
    op.create_index(
        'ix_execution_artifacts_tenant_expires',
        'execution_artifacts',
        ['tenant_id', 'expires_at']
    )


def downgrade() -> None:
    """Downgrade schema - drop execution_artifacts table."""

    # Drop indexes
    op.drop_index('ix_execution_artifacts_tenant_expires', table_name='execution_artifacts')
    op.drop_index('ix_execution_artifacts_execution_version', table_name='execution_artifacts')
    op.drop_index('ix_execution_artifacts_expires_at', table_name='execution_artifacts')
    op.drop_index('ix_execution_artifacts_version_number', table_name='execution_artifacts')
    op.drop_index('ix_execution_artifacts_artifact_type', table_name='execution_artifacts')
    op.drop_index('ix_execution_artifacts_tenant_id', table_name='execution_artifacts')
    op.drop_index('ix_execution_artifacts_execution_id', table_name='execution_artifacts')

    # Drop table
    op.drop_table('execution_artifacts')

    # Drop enum
    sa.Enum(name='artifacttype').drop(op.get_bind(), checkfirst=True)
