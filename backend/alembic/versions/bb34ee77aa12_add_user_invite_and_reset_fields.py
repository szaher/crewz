"""add user invite/reset fields

Revision ID: bb34ee77aa12
Revises: ab12cd34ef56
Create Date: 2025-10-08 02:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bb34ee77aa12'
down_revision: Union[str, Sequence[str], None] = 'ab12cd34ef56'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('password_reset_token', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('password_reset_expires', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('require_password_change', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.alter_column('users', 'require_password_change', server_default=None)


def downgrade() -> None:
    op.drop_column('users', 'require_password_change')
    op.drop_column('users', 'password_reset_expires')
    op.drop_column('users', 'password_reset_token')

