"""
SQLAlchemy ORM models — FMEA-MultiAgentAI
All tables for PostgreSQL persistence.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# 1. fmea_sessions — anchor for every FMEA analysis session
# ---------------------------------------------------------------------------
class FMEASession(Base):
    __tablename__ = "fmea_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    user_id = Column(String(255))
    part_name = Column(String(500))
    supplier = Column(String(255))
    status = Column(String(50), default="draft")       # draft | in_progress | completed
    language = Column(String(10), default="en")        # en | fr | pt-br
    industry = Column(String(255))                     # automotive | aerospace | medical | ...

    # relationships
    uploaded_files = relationship("UploadedFile", back_populates="session")
    fmea_records = relationship("FMEARecord", back_populates="session")
    ai_suggestions = relationship("AISuggestion", back_populates="session")
    reports = relationship("FMEAReport", back_populates="session")
    meetings = relationship("Meeting", back_populates="session")


# ---------------------------------------------------------------------------
# 2. uploaded_files — metadata for every file uploaded to a session
# ---------------------------------------------------------------------------
class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("fmea_sessions.id", ondelete="CASCADE"), nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    original_filename = Column(String(500), nullable=False)
    content_type = Column(String(100))
    size_bytes = Column(BigInteger)
    minio_bucket = Column(String(255))
    minio_key = Column(String(1000))

    session = relationship("FMEASession", back_populates="uploaded_files")


# ---------------------------------------------------------------------------
# 3. fmea_records — individual FMEA rows (one failure mode per row)
# ---------------------------------------------------------------------------
class FMEARecord(Base):
    __tablename__ = "fmea_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("fmea_sessions.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    component = Column(String(500))
    failure_mode = Column(Text)
    effect = Column(Text)
    cause = Column(Text)
    severity = Column(Integer)
    occurrence = Column(Integer)
    detection = Column(Integer)
    # rpn is computed: severity * occurrence * detection (set by app layer)
    rpn = Column(Integer)
    recommended_action = Column(Text)
    responsible = Column(String(255))
    target_date = Column(DateTime(timezone=True))
    extra_fields = Column(JSONB)      # any extra columns from source document

    session = relationship("FMEASession", back_populates="fmea_records")
    ai_suggestions = relationship("AISuggestion", back_populates="fmea_record")
    meeting_links = relationship("MeetingFMEALink", back_populates="fmea_record")


# ---------------------------------------------------------------------------
# 4. ai_suggestions — one row per LLM-generated suggestion for a field
# ---------------------------------------------------------------------------
class AISuggestion(Base):
    __tablename__ = "ai_suggestions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("fmea_sessions.id", ondelete="CASCADE"), nullable=False)
    fmea_record_id = Column(UUID(as_uuid=True), ForeignKey("fmea_records.id", ondelete="CASCADE"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    agent_name = Column(String(100))         # e.g. severity_agent, occurrence_agent
    field = Column(String(100))              # severity | occurrence | detection | cause | ...
    model_name = Column(String(100))
    suggested_value = Column(Text)
    justification = Column(Text)
    confidence = Column(Float)
    prompt_context = Column(JSONB)           # snapshot of input sent to LLM

    session = relationship("FMEASession", back_populates="ai_suggestions")
    fmea_record = relationship("FMEARecord", back_populates="ai_suggestions")
    feedback = relationship("SuggestionFeedback", back_populates="suggestion", uselist=False)


# ---------------------------------------------------------------------------
# 5. suggestion_feedback — engineer decision on each AI suggestion (ML data)
# ---------------------------------------------------------------------------
class SuggestionFeedback(Base):
    __tablename__ = "suggestion_feedback"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    suggestion_id = Column(UUID(as_uuid=True), ForeignKey("ai_suggestions.id", ondelete="CASCADE"), nullable=False, unique=True)
    decided_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    action = Column(String(20), nullable=False)   # accepted | rejected | modified
    original_value = Column(Text)
    suggested_value = Column(Text)
    final_value = Column(Text)
    time_to_decide_seconds = Column(Integer)

    # denormalized snapshot for ML training (no JOINs needed)
    snap_component = Column(Text)
    snap_failure_mode = Column(Text)
    snap_effect = Column(Text)
    snap_cause = Column(Text)
    snap_industry = Column(String(255))
    snap_agent_name = Column(String(100))
    snap_field = Column(String(100))

    suggestion = relationship("AISuggestion", back_populates="feedback")


# ---------------------------------------------------------------------------
# 6. fmea_reports — JSON/PDF snapshots of completed analyses
# ---------------------------------------------------------------------------
class FMEAReport(Base):
    __tablename__ = "fmea_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("fmea_sessions.id", ondelete="CASCADE"), nullable=False)
    generated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    format = Column(String(20), default="json")   # json | pdf
    content = Column(JSONB)                        # full report as JSON
    minio_bucket = Column(String(255))
    minio_key = Column(String(1000))               # populated when PDF is stored in MinIO

    session = relationship("FMEASession", back_populates="reports")


# ---------------------------------------------------------------------------
# 7. meetings — meeting sessions optionally linked to an FMEA session
# ---------------------------------------------------------------------------
class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("fmea_sessions.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    title = Column(String(500))
    language = Column(String(10), default="en")
    status = Column(String(50), default="pending")  # pending | processing | completed

    session = relationship("FMEASession", back_populates="meetings")
    transcripts = relationship("MeetingTranscript", back_populates="meeting")
    fmea_links = relationship("MeetingFMEALink", back_populates="meeting")


# ---------------------------------------------------------------------------
# 8. meeting_transcripts — STT output for a meeting
# ---------------------------------------------------------------------------
class MeetingTranscript(Base):
    __tablename__ = "meeting_transcripts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id = Column(UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    full_text = Column(Text)
    segments = Column(JSONB)    # [{start, end, text, speaker?}]
    stt_model = Column(String(100))
    minio_bucket = Column(String(255))
    minio_key = Column(String(1000))    # audio/video file in MinIO

    meeting = relationship("Meeting", back_populates="transcripts")


# ---------------------------------------------------------------------------
# 9. meeting_fmea_links — connects transcript segments to fmea_records
# ---------------------------------------------------------------------------
class MeetingFMEALink(Base):
    __tablename__ = "meeting_fmea_links"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id = Column(UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    fmea_record_id = Column(UUID(as_uuid=True), ForeignKey("fmea_records.id", ondelete="CASCADE"), nullable=False)
    segment_index = Column(Integer)     # which segment in transcript.segments[]
    confidence = Column(Float)
    note = Column(Text)

    meeting = relationship("Meeting", back_populates="fmea_links")
    fmea_record = relationship("FMEARecord", back_populates="meeting_links")


# ---------------------------------------------------------------------------
# 10. agent_telemetry — latency, token usage, errors per LLM call
# ---------------------------------------------------------------------------
class AgentTelemetry(Base):
    __tablename__ = "agent_telemetry"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("fmea_sessions.id", ondelete="CASCADE"))
    called_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    agent_name = Column(String(100))
    model_name = Column(String(100))
    latency_ms = Column(Integer)
    token_input = Column(Integer)
    token_output = Column(Integer)
    status = Column(String(20), default="ok")   # ok | error | timeout
    error_msg = Column(Text)
