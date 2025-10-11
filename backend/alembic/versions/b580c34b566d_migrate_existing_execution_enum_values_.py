"""migrate_existing_execution_enum_values_to_lowercase

Revision ID: b580c34b566d
Revises: 5e71ca458ae3
Create Date: 2025-10-10 12:07:20.154034

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b580c34b566d'
down_revision: Union[str, Sequence[str], None] = '5e71ca458ae3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Migrate existing execution_type values from uppercase to lowercase
    # Enum values were added in previous migration (5e71ca458ae3)
    op.execute("UPDATE executions SET execution_type = LOWER(execution_type::text)::executiontype WHERE execution_type::text != LOWER(execution_type::text)")

    # Migrate existing status values from uppercase to lowercase
    op.execute("UPDATE executions SET status = LOWER(status::text)::executionstatus WHERE status::text != LOWER(status::text)")


def downgrade() -> None:
    """Downgrade schema."""
    # Migrate back to uppercase (if needed)
    op.execute("UPDATE executions SET execution_type = UPPER(execution_type::text)::executiontype WHERE execution_type::text != UPPER(execution_type::text)")
    op.execute("UPDATE executions SET status = UPPER(status::text)::executionstatus WHERE status::text != UPPER(status::text)")
