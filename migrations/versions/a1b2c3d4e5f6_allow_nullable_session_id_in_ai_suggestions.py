"""allow_nullable_session_id_in_ai_suggestions

Allows session_id to be NULL in ai_suggestions so that pinned/hardcoded
responses can be inserted without belonging to a specific session.

Revision ID: a1b2c3d4e5f6
Revises: de6110153bb8
Create Date: 2026-05-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'de6110153bb8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "ai_suggestions",
        "session_id",
        existing_type=sa.UUID(),
        nullable=True,
    )


def downgrade() -> None:
    # Remove orphan rows before restoring NOT NULL
    op.execute(
        "DELETE FROM ai_suggestions WHERE session_id IS NULL"
    )
    op.alter_column(
        "ai_suggestions",
        "session_id",
        existing_type=sa.UUID(),
        nullable=False,
    )
