"""add_judge_and_human_review_fields_to_ai_suggestions

Revision ID: de6110153bb8
Revises: ac938dff9acc
Create Date: 2026-05-05 18:41:23.859797

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'de6110153bb8'
down_revision: Union[str, Sequence[str], None] = 'ac938dff9acc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add LLM-as-Judge and human review fields to ai_suggestions."""
    from sqlalchemy.dialects import postgresql

    op.add_column("ai_suggestions", sa.Column("judge_verdict",          sa.String(20),                  nullable=True))
    op.add_column("ai_suggestions", sa.Column("judge_correct_points",   postgresql.JSONB(),              nullable=True))
    op.add_column("ai_suggestions", sa.Column("judge_incorrect_points", postgresql.JSONB(),              nullable=True))
    op.add_column("ai_suggestions", sa.Column("judge_confidence",       sa.Float(),                     nullable=True))
    op.add_column("ai_suggestions", sa.Column("judge_evaluated_at",     sa.DateTime(timezone=True),     nullable=True))

    op.add_column("ai_suggestions", sa.Column("human_verdict",          sa.String(20),                  nullable=True))
    op.add_column("ai_suggestions", sa.Column("human_notes",            sa.Text(),                      nullable=True))
    op.add_column("ai_suggestions", sa.Column("human_reviewed_by",      sa.String(255),                 nullable=True))
    op.add_column("ai_suggestions", sa.Column("human_reviewed_at",      sa.DateTime(timezone=True),     nullable=True))


def downgrade() -> None:
    """Remove LLM-as-Judge and human review fields from ai_suggestions."""
    op.drop_column("ai_suggestions", "human_reviewed_at")
    op.drop_column("ai_suggestions", "human_reviewed_by")
    op.drop_column("ai_suggestions", "human_notes")
    op.drop_column("ai_suggestions", "human_verdict")

    op.drop_column("ai_suggestions", "judge_evaluated_at")
    op.drop_column("ai_suggestions", "judge_confidence")
    op.drop_column("ai_suggestions", "judge_incorrect_points")
    op.drop_column("ai_suggestions", "judge_correct_points")
    op.drop_column("ai_suggestions", "judge_verdict")
