"""add_task_variables_column

Revision ID: 1a372377f75e
Revises: f8a2b5c3d7e9
Create Date: 2025-10-09 18:00:24.566576

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1a372377f75e'
down_revision: Union[str, Sequence[str], None] = 'f8a2b5c3d7e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add variables column to tasks table
    op.add_column('tasks', sa.Column('variables', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove variables column from tasks table
    op.drop_column('tasks', 'variables')
