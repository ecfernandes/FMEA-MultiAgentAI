"""
backend/schemas.py
------------------
Pydantic v2 contracts for the FMEA 5.0 FastAPI server.

These models serve as the strict data contract between:
  - The extraction services (PDF/Excel → JSON)
  - The AI agents (field suggestion requests)
  - The HTTP API (request / response shapes)

They are intentionally decoupled from src/preprocessing/fmea_schema.py
so the backend can evolve independently.
"""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


# ============================================================================
# CORE FMEA RECORD — one row of a FMEA table
# ============================================================================

class FMEARecordSchema(BaseModel):
    """
    A single FMEA table row.
    Core fields are explicitly typed; any column discovered from the source
    document is stored as an extra field (model_config extra='allow').
    """

    model_config = ConfigDict(extra="allow")

    # Identity
    component: str = Field(..., description="Component / item name")
    function: Optional[str] = Field(None, description="What the component is designed to do")

    # Core FMEA columns
    failure_mode: str = Field(..., description="How the function fails physically")
    effect: str = Field(..., description="Potential effect on the customer / system")
    cause: str = Field(..., description="Root technical cause / failure mechanism")

    # Risk ratings (1-10)
    severity: Optional[int] = Field(None, ge=1, le=10, description="Severity rating 1-10")
    occurrence: Optional[int] = Field(None, ge=1, le=10, description="Occurrence rating 1-10")
    detection: Optional[int] = Field(None, ge=1, le=10, description="Detection rating 1-10")
    rpn: Optional[int] = Field(None, ge=1, description="Risk Priority Number (S×O×D)")

    # Traceability
    source_file: Optional[str] = Field(None, description="Original file this row came from")
    sheet_name: Optional[str] = None
    row_number: Optional[int] = None

    @field_validator("severity", "occurrence", "detection", mode="before")
    @classmethod
    def coerce_sod(cls, v):
        """Accept numeric strings like '7' and coerce to int."""
        if v is None or v == "" or v == "?":
            return None
        try:
            return int(v)
        except (ValueError, TypeError):
            return None

    def compute_rpn(self) -> Optional[int]:
        """Calculate RPN — returns None if any field is missing."""
        if self.severity and self.occurrence and self.detection:
            return self.severity * self.occurrence * self.detection
        return None


# ============================================================================
# FMEA DOCUMENT — header + list of records
# ============================================================================

class FMEADocumentSchema(BaseModel):
    """Complete FMEA document as returned by the /extract endpoint."""

    part_name: str = Field(..., description="Part / component name")
    supplier: str = Field("Unknown", description="Supplier company name")
    source_file: str = Field(..., description="Original uploaded filename")
    extraction_date: str = Field(..., description="ISO-8601 extraction timestamp")

    # Optional document-level metadata
    project_name: Optional[str] = None
    team: Optional[str] = None
    phase: Optional[str] = None

    records: List[FMEARecordSchema] = Field(
        default_factory=list,
        description="All FMEA rows extracted from the document",
    )

    @property
    def total_records(self) -> int:
        return len(self.records)

    @property
    def high_risk_records(self) -> List[FMEARecordSchema]:
        """Records with RPN > 100."""
        return [r for r in self.records if r.rpn and r.rpn > 100]


# ============================================================================
# EXTRACTION RESPONSE — what the /extract endpoint returns
# ============================================================================

class ExtractionResponse(BaseModel):
    """Top-level response from POST /extract."""

    success: bool = True
    message: str = "Extraction completed"
    document: FMEADocumentSchema


# ============================================================================
# AI AGENT REQUEST / RESPONSE
# ============================================================================

class AgentRequest(BaseModel):
    """Request body for POST /analyze — asks a specialist agent for a suggestion."""

    field: str = Field(
        ...,
        description=(
            "FMEA field to assess — any column key present in the record "
            "(e.g. failure_mode, effect, cause, severity, occurrence, detection, "
            "current_controls_prevention, recommended_action, or any other "
            "document-specific column discovered during extraction)."
        ),
    )
    function: str = Field(..., description="Item function text from the FMEA row")
    failure_mode: str = Field(
        "",
        description="Current failure mode text (empty when field IS failure_mode)",
    )
    context: str = Field(
        "",
        description="Additional context: part name, component, environment, etc.",
    )
    model_name: Optional[str] = Field(
        None,
        description="Override LLM model id (falls back to LLM_DEFAULT_MODEL env var)",
    )


class AgentResponse(BaseModel):
    """Structured response from a specialist agent."""

    agent_name: str = Field(..., description="Name of the specialist agent that answered")
    agent_color: str = Field(..., description="Hex colour for the agent badge")
    suggested_value: Optional[str | int] = Field(
        None,
        description="Suggested value (int for S/O/D, string for text fields)",
    )
    justification: str = Field(..., description="Dense engineering rationale (3-5 sentences)")
    sources: List[str] = Field(
        default_factory=list,
        description="Reference books / standards used by the agent",
    )

    # LLM-as-Judge evaluation fields (None when judge call fails)
    judge_verdict: Optional[str] = Field(
        None,
        description="'correct' | 'partial' | 'incorrect' (incorrect is retried server-side)",
    )
    judge_correct_points: Optional[List[str]] = Field(
        None, description="Technically valid statements identified by the judge"
    )
    judge_incorrect_points: Optional[List[str]] = Field(
        None, description="Technically incoherent statements identified by the judge"
    )
    judge_confidence: Optional[float] = Field(
        None, description="Judge confidence score 0.0 to 1.0"
    )


# ============================================================================
# MISSING FAILURES ANALYSIS
# ============================================================================

class FunctionFailureList(BaseModel):
    """One function with its already-documented failure modes."""
    function: str = Field(..., description="Function name as it appears in the FMEA")
    existing_failures: List[str] = Field(
        default_factory=list,
        description="Failure modes already listed for this function",
    )


class MissingFailuresRequest(BaseModel):
    """Request body for POST /suggest-missing-failures."""
    part_name: str = Field(..., description="Part / system name")
    functions: List[FunctionFailureList] = Field(
        ..., description="All functions with their currently documented failure modes"
    )
    model_name: Optional[str] = Field(
        None,
        description="Override LLM model id (falls back to LLM_DEFAULT_MODEL env var)",
    )


class MissingFailureSuggestion(BaseModel):
    """A single suggested failure mode that was not yet in the FMEA."""
    function: str
    failure_mode: str
    effect: str
    cause: str
    justification: str


class MissingFailuresResponse(BaseModel):
    """Response from POST /suggest-missing-failures."""
    all_covered: bool = Field(
        ..., description="True when the AI finds no relevant missing failure modes"
    )
    message: str
    suggestions: List[MissingFailureSuggestion] = Field(default_factory=list)


# ============================================================================
# SESSIONS
# ============================================================================

class SessionCreate(BaseModel):
    """Request body for POST /sessions."""
    part_name: Optional[str] = Field(None, description="Part or component name")
    supplier: Optional[str] = Field(None, description="Supplier company name")
    language: Optional[str] = Field("en", description="Interface language: en | fr | pt-br")
    industry: Optional[str] = Field(None, description="Industry sector (e.g. automotive)")
    user_id: Optional[str] = Field(None, description="User identifier (email or id)")


class SessionResponse(BaseModel):
    """A single FMEA session record."""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Session UUID")
    created_at: str = Field(..., description="ISO-8601 creation timestamp")
    updated_at: Optional[str] = Field(None, description="ISO-8601 last-updated timestamp")
    user_id: Optional[str] = None
    part_name: Optional[str] = None
    supplier: Optional[str] = None
    status: str = Field("draft", description="draft | in_progress | completed")
    language: str = Field("en")
    industry: Optional[str] = None


class SessionUpdate(BaseModel):
    """Request body for PUT /sessions/{session_id}."""
    part_name: Optional[str] = None
    supplier: Optional[str] = None
    language: Optional[str] = None
    industry: Optional[str] = None
    user_id: Optional[str] = None
    status: Optional[str] = Field(None, description="draft | in_progress | completed")


class SessionListResponse(BaseModel):
    """Response from GET /sessions."""
    total: int
    sessions: List[SessionResponse]


# ============================================================================
# SESSION PERSISTENCE — save extraction + AI suggestions
# ============================================================================

class SaveExtractionRequest(BaseModel):
    """Request body for POST /sessions/from-extraction."""
    part_name: str
    supplier: Optional[str] = "Unknown"
    source_file: str
    records: List[dict] = Field(default_factory=list)
    language: Optional[str] = "en"
    industry: Optional[str] = None
    user_id: Optional[str] = None


class SaveExtractionResponse(BaseModel):
    """Response from POST /sessions/from-extraction."""
    session_id: str
    records_saved: int


class SaveSuggestionRequest(BaseModel):
    """Request body for POST /sessions/{id}/suggestions."""
    field: str
    function: str
    failure_mode: str
    current_value: Optional[str] = None
    suggested_value: Optional[str] = None
    justification: Optional[str] = None
    agent_name: Optional[str] = None
    agent_color: Optional[str] = None
    sources: Optional[List[str]] = None
    judge_verdict: Optional[str] = None
    judge_correct_points: Optional[List[str]] = None
    judge_incorrect_points: Optional[List[str]] = None
    judge_confidence: Optional[float] = None
    human_verdict: str = Field(..., description="'accepted' | 'rejected'")
    model_name: Optional[str] = None


class SaveSuggestionResponse(BaseModel):
    suggestion_id: str
    human_verdict: str


class SessionRecordsResponse(BaseModel):
    """Response from GET /sessions/{id}/records."""
    session_id: str
    part_name: Optional[str] = None
    supplier: Optional[str] = None
    source_file: Optional[str] = None
    records: List[dict] = Field(default_factory=list)


# ============================================================================
# HEALTH CHECK
# ============================================================================

class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "5.0.0"
    description: str = "AI-Driven FMEA 5.0 — Backend API"
