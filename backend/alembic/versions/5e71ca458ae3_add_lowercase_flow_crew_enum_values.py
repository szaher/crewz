"""add_lowercase_flow_crew_enum_values

Revision ID: 5e71ca458ae3
Revises: e318835252bb
Create Date: 2025-10-10 12:10:05.216104

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5e71ca458ae3'
down_revision: Union[str, Sequence[str], None] = 'e318835252bb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add lowercase enum values that are missing (flow and crew)
    # Note: agent, tool, task were already added in a previous migration
    op.execute("ALTER TYPE executiontype ADD VALUE IF NOT EXISTS 'flow'")
    op.execute("ALTER TYPE executiontype ADD VALUE IF NOT EXISTS 'crew'")


def downgrade() -> None:
    """Downgrade schema."""
    # Note: PostgreSQL does not support removing enum values
    # This would require recreating the enum type
    pass
