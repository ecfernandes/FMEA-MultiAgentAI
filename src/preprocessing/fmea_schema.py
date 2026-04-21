"""
FMEA 5.0 - JSON Schema and Data Models
Standardized format for FMEA data extraction and storage
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict, field
import json


@dataclass
class FMEARecord:
    """
    Single FMEA record. Core fields cover computation (RPN = S×O×D).
    All document-specific columns (controls, actions, dates, etc.) go in extra_fields
    so the system adapts to whatever columns the uploaded document contains.
    """
    # Core fields — required
    component: str
    failure_mode: str
    effect: str
    cause: str

    # Functional grouping (navigation)
    function: Optional[str] = None

    # Risk ratings (needed for RPN = S × O × D)
    severity: Optional[int] = None    # 1–10
    occurrence: Optional[int] = None  # 1–10
    detection: Optional[int] = None   # 1–10
    rpn: Optional[int] = None         # S × O × D

    # Dynamic: every other column discovered from the document
    extra_fields: Dict[str, Any] = field(default_factory=dict)

    # Traceability (metadata — never displayed in the table)
    _source_file: Optional[str] = None
    _sheet_name: Optional[str] = None
    _row_number: Optional[int] = None
    
    def to_dict(self, include_metadata: bool = True) -> Dict[str, Any]:
        """Convert to dictionary, merging core fields with dynamically discovered columns."""
        data: Dict[str, Any] = {
            'component': self.component,
            'function': self.function,
            'failure_mode': self.failure_mode,
            'effect': self.effect,
            'cause': self.cause,
            'severity': self.severity,
            'occurrence': self.occurrence,
            'detection': self.detection,
            'rpn': self.rpn,
            **(self.extra_fields or {}),
        }
        if include_metadata:
            data['metadata'] = {
                'source_file': self._source_file,
                'sheet_name': self._sheet_name,
                'row_number': self._row_number,
            }
        return data
    
    def to_rag_text(self) -> str:
        """
        Convert to minimal text for RAG embeddings.
        NO decorative headers, NO separators, just clean semantic content.
        """
        lines = []
        lines.append(f"Component: {self.component}")
        lines.append(f"Failure Mode: {self.failure_mode}")
        lines.append(f"Effect: {self.effect}")
        lines.append(f"Cause: {self.cause}")

        if self.severity is not None:
            lines.append(f"Severity: {self.severity}")
        if self.occurrence is not None:
            lines.append(f"Occurrence: {self.occurrence}")
        if self.detection is not None:
            lines.append(f"Detection: {self.detection}")
        if self.rpn is not None:
            lines.append(f"RPN: {self.rpn}")

        for key, val in (self.extra_fields or {}).items():
            if val:
                label = key.replace('_', ' ').title()
                lines.append(f"{label}: {val}")

        return "\n".join(lines)


@dataclass
class FMEADocument:
    """
    Complete FMEA document with multiple failures.
    Clean JSON structure for storage and analysis.
    """
    failures: List[FMEARecord]
    source_file: str
    extraction_date: str
    
    # Optional document-level metadata
    project_name: Optional[str] = None
    component: Optional[str] = None
    part_name: Optional[str] = None
    supplier: Optional[str] = None
    team: Optional[str] = None
    phase: Optional[str] = None
    
    def to_json(self, indent: int = 2) -> str:
        """Export to clean JSON string."""
        data = {
            'project_name': self.project_name,
            'component': self.component,
            'team': self.team,
            'phase': self.phase,
            'source_file': self.source_file,
            'extraction_date': self.extraction_date,
            'total_failures': len(self.failures),
            'failures': [failure.to_dict(include_metadata=True) for failure in self.failures]
        }
        return json.dumps(data, indent=indent, ensure_ascii=False)
    
    def to_rag_text(self) -> str:
        """
        Convert entire document to minimal RAG text.
        Each failure separated by double newline.
        """
        texts = [failure.to_rag_text() for failure in self.failures]
        return "\n\n".join(texts)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Calculate basic statistics for validation."""
        rpns = [f.rpn for f in self.failures if f.rpn is not None]
        severities = [f.severity for f in self.failures if f.severity is not None]
        
        return {
            'total_failures': len(self.failures),
            'components': len(set(f.component for f in self.failures if f.component)),
            'avg_rpn': sum(rpns) / len(rpns) if rpns else None,
            'max_rpn': max(rpns) if rpns else None,
            'avg_severity': sum(severities) / len(severities) if severities else None,
            'high_risk_count': len([r for r in rpns if r >= 100])
        }


@dataclass
class TextDocument:
    """
    Unstructured document (email, report, etc.) with extracted entities.
    Structured format for consistency with FMEA documents.
    """
    text: str
    source_file: str
    extraction_date: str
    document_type: str  # 'email', 'report', 'meeting_minutes', etc.
    
    # Extracted entities (optional, for future NLP)
    components: Optional[List[str]] = None
    risks: Optional[List[str]] = None
    actions: Optional[List[str]] = None
    
    def to_json(self, indent: int = 2) -> str:
        """Export to JSON."""
        data = {
            'document_type': self.document_type,
            'source_file': self.source_file,
            'extraction_date': self.extraction_date,
            'text': self.text,
            'entities': {
                'components': self.components or [],
                'risks': self.risks or [],
                'actions': self.actions or []
            }
        }
        return json.dumps(data, indent=indent, ensure_ascii=False)
    
    def to_rag_text(self) -> str:
        """Return clean text for RAG."""
        return self.text


def clean_cell_value(value: Any, expected_type: str = 'string') -> Any:
    """
    Clean individual cell value from Excel.
    Remove whitespace, normalize types, handle None/NaN/empty.
    
    Args:
        value: Raw cell value
        expected_type: 'string', 'int', 'float'
    
    Returns:
        Cleaned value or None
    """
    # Handle None, NaN, empty strings
    if value is None or value == '' or str(value).lower() in ['nan', 'n/a', 'na', 'none', '-']:
        return None
    
    # String cleaning
    if expected_type == 'string':
        cleaned = str(value).strip()
        # Remove multiple spaces
        cleaned = ' '.join(cleaned.split())
        return cleaned if cleaned else None
    
    # Integer cleaning (severity, occurrence, detection, rpn)
    elif expected_type == 'int':
        try:
            # Remove whitespace and convert
            cleaned = str(value).strip()
            return int(float(cleaned))  # Handle "8.0" -> 8
        except (ValueError, TypeError):
            return None
    
    # Float cleaning
    elif expected_type == 'float':
        try:
            cleaned = str(value).strip()
            return float(cleaned)
        except (ValueError, TypeError):
            return None
    
    return value


# Validation ranges for FMEA values
FMEA_VALIDATION = {
    'severity': {'min': 1, 'max': 10},
    'occurrence': {'min': 1, 'max': 10},
    'detection': {'min': 1, 'max': 10},
    'rpn': {'min': 1, 'max': 1000}
}


def validate_fmea_value(value: Optional[int], field: str) -> bool:
    """Validate FMEA numeric field is within expected range."""
    if value is None:
        return True  # None is acceptable
    
    if field not in FMEA_VALIDATION:
        return True
    
    limits = FMEA_VALIDATION[field]
    return limits['min'] <= value <= limits['max']
