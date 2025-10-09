"""add tenant.settings JSON column

Revision ID: ab12cd34ef56
Revises: e9a1b4c3d6f7
Create Date: 2025-10-08 02:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ab12cd34ef56'
down_revision: Union[str, Sequence[str], None] = 'e9a1b4c3d6f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('tenants', sa.Column('settings', sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")))
    # Drop server default after backfilling
    op.alter_column('tenants', 'settings', server_default=None)


def downgrade() -> None:
    op.drop_column('tenants', 'settings')

