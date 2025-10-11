"""merge_prompt_registry_with_main

Revision ID: ccf2db223d72
Revises: b580c34b566d, g9h3j4k5l6m7
Create Date: 2025-10-11 18:45:45.805344

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ccf2db223d72'
down_revision: Union[str, Sequence[str], None] = ('b580c34b566d', 'g9h3j4k5l6m7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
