"""update_execution_status_enum_values

Revision ID: e318835252bb
Revises: 683528a68e0f
Create Date: 2025-10-10 12:03:32.055230

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e318835252bb'
down_revision: Union[str, Sequence[str], None] = '683528a68e0f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add lowercase enum values for ExecutionStatus
    op.execute("ALTER TYPE executionstatus ADD VALUE IF NOT EXISTS 'pending'")
    op.execute("ALTER TYPE executionstatus ADD VALUE IF NOT EXISTS 'running'")
    op.execute("ALTER TYPE executionstatus ADD VALUE IF NOT EXISTS 'completed'")
    op.execute("ALTER TYPE executionstatus ADD VALUE IF NOT EXISTS 'failed'")
    op.execute("ALTER TYPE executionstatus ADD VALUE IF NOT EXISTS 'cancelled'")


def downgrade() -> None:
    """Downgrade schema."""
    # Note: PostgreSQL does not support removing enum values
    # This would require recreating the enum type
    pass
