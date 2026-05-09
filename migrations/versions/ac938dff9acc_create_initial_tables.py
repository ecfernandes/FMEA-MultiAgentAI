"""Create initial tables

Revision ID: ac938dff9acc
Revises: 
Create Date: 2026-05-04 19:21:16.903695

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'ac938dff9acc'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "fmea_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_id", sa.String(length=255), nullable=True),
        sa.Column("part_name", sa.String(length=500), nullable=True),
        sa.Column("supplier", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("language", sa.String(length=10), nullable=True),
        sa.Column("industry", sa.String(length=255), nullable=True),
    )

    op.create_table(
        "agent_telemetry",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("called_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("agent_name", sa.String(length=100), nullable=True),
        sa.Column("model_name", sa.String(length=100), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("token_input", sa.Integer(), nullable=True),
        sa.Column("token_output", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=True),
        sa.Column("error_msg", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["fmea_sessions.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "fmea_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("format", sa.String(length=20), nullable=True),
        sa.Column("content", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("minio_bucket", sa.String(length=255), nullable=True),
        sa.Column("minio_key", sa.String(length=1000), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["fmea_sessions.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "meetings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=True),
        sa.Column("language", sa.String(length=10), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["fmea_sessions.id"], ondelete="SET NULL"),
    )

    op.create_table(
        "session_artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("artifact_type", sa.String(length=100), nullable=False),
        sa.Column("artifact_format", sa.String(length=20), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("content", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("minio_bucket", sa.String(length=255), nullable=True),
        sa.Column("minio_key", sa.String(length=1000), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["fmea_sessions.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "uploaded_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("original_filename", sa.String(length=500), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("minio_bucket", sa.String(length=255), nullable=True),
        sa.Column("minio_key", sa.String(length=1000), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["fmea_sessions.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "fmea_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("component", sa.String(length=500), nullable=True),
        sa.Column("failure_mode", sa.Text(), nullable=True),
        sa.Column("effect", sa.Text(), nullable=True),
        sa.Column("cause", sa.Text(), nullable=True),
        sa.Column("severity", sa.Integer(), nullable=True),
        sa.Column("occurrence", sa.Integer(), nullable=True),
        sa.Column("detection", sa.Integer(), nullable=True),
        sa.Column("rpn", sa.Integer(), nullable=True),
        sa.Column("recommended_action", sa.Text(), nullable=True),
        sa.Column("responsible", sa.String(length=255), nullable=True),
        sa.Column("target_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("extra_fields", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["fmea_sessions.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "meeting_transcripts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("meeting_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("full_text", sa.Text(), nullable=True),
        sa.Column("segments", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("stt_model", sa.String(length=100), nullable=True),
        sa.Column("minio_bucket", sa.String(length=255), nullable=True),
        sa.Column("minio_key", sa.String(length=1000), nullable=True),
        sa.ForeignKeyConstraint(["meeting_id"], ["meetings.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "ai_suggestions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fmea_record_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("agent_name", sa.String(length=100), nullable=True),
        sa.Column("field", sa.String(length=100), nullable=True),
        sa.Column("model_name", sa.String(length=100), nullable=True),
        sa.Column("suggested_value", sa.Text(), nullable=True),
        sa.Column("justification", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("prompt_context", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["fmea_record_id"], ["fmea_records.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["fmea_sessions.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "meeting_fmea_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("meeting_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fmea_record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("segment_index", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["fmea_record_id"], ["fmea_records.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["meeting_id"], ["meetings.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "suggestion_feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("suggestion_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column("original_value", sa.Text(), nullable=True),
        sa.Column("suggested_value", sa.Text(), nullable=True),
        sa.Column("final_value", sa.Text(), nullable=True),
        sa.Column("time_to_decide_seconds", sa.Integer(), nullable=True),
        sa.Column("snap_component", sa.Text(), nullable=True),
        sa.Column("snap_failure_mode", sa.Text(), nullable=True),
        sa.Column("snap_effect", sa.Text(), nullable=True),
        sa.Column("snap_cause", sa.Text(), nullable=True),
        sa.Column("snap_industry", sa.String(length=255), nullable=True),
        sa.Column("snap_agent_name", sa.String(length=100), nullable=True),
        sa.Column("snap_field", sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(["suggestion_id"], ["ai_suggestions.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("suggestion_id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("suggestion_feedback")
    op.drop_table("meeting_fmea_links")
    op.drop_table("ai_suggestions")
    op.drop_table("meeting_transcripts")
    op.drop_table("fmea_records")
    op.drop_table("uploaded_files")
    op.drop_table("session_artifacts")
    op.drop_table("meetings")
    op.drop_table("fmea_reports")
    op.drop_table("agent_telemetry")
    op.drop_table("fmea_sessions")
