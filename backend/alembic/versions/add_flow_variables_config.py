"""add flow variables and config

Revision ID: add_flow_variables_config
Revises: 6cd7f6dba6b6
Create Date: 2025-10-19 17:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_flow_variables_config'
down_revision = '6cd7f6dba6b6'
branch_labels = None
depends_on = None


def upgrade():
    # Add variables and config columns to flows table
    op.add_column('flows', sa.Column('variables', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column('flows', sa.Column('config', postgresql.JSON(astext_type=sa.Text()), nullable=True))


def downgrade():
    # Remove variables and config columns
    op.drop_column('flows', 'config')
    op.drop_column('flows', 'variables')
