"""add chat_folders and folder_id to chat_sessions

Revision ID: cd12ef34aa56
Revises: bb34ee77aa12
Create Date: 2025-10-08 03:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cd12ef34aa56'
down_revision: Union[str, Sequence[str], None] = 'bb34ee77aa12'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create chat_folders table if it doesn't exist
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_folders (
            tenant_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            name VARCHAR(255) NOT NULL,
            id SERIAL NOT NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
            PRIMARY KEY (id)
        );
        """
    )

    # Create indexes if not exist
    op.execute("CREATE INDEX IF NOT EXISTS ix_chat_folders_tenant_id ON chat_folders(tenant_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_chat_folders_user_id ON chat_folders(user_id);")

    # Add folder_id to chat_sessions if not exists
    op.execute("ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS folder_id INTEGER;")

    # Add FK if not exists
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'chat_sessions_folder_id_fkey'
            ) THEN
                ALTER TABLE chat_sessions
                ADD CONSTRAINT chat_sessions_folder_id_fkey
                FOREIGN KEY (folder_id) REFERENCES chat_folders(id);
            END IF;
        END $$;
        """
    )

    # Index on folder_id
    op.execute("CREATE INDEX IF NOT EXISTS ix_chat_sessions_folder_id ON chat_sessions(folder_id);")


def downgrade() -> None:
    # Drop index and FK/column safely
    op.execute("DROP INDEX IF EXISTS ix_chat_sessions_folder_id;")
    op.execute("ALTER TABLE chat_sessions DROP CONSTRAINT IF EXISTS chat_sessions_folder_id_fkey;")
    op.execute("ALTER TABLE chat_sessions DROP COLUMN IF EXISTS folder_id;")

    # Drop folders indexes and table safely
    op.execute("DROP INDEX IF EXISTS ix_chat_folders_user_id;")
    op.execute("DROP INDEX IF EXISTS ix_chat_folders_tenant_id;")
    op.execute("DROP TABLE IF EXISTS chat_folders;")
