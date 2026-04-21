"""
Data Models for FMEA AI Suggestions
Structured classes for managing AI-generated content with metadata
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class SuggestionStatus(Enum):
    """Status for AI suggestions"""
    GENERATED = "generated"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    MODIFIED = "modified"
    PENDING = "pending"


class ConfidenceLevel(Enum):
    """Confidence levels for AI suggestions"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class AiSuggestion:
    """
    Represents a single AI-generated suggestion with metadata.
    Inspired by LLMRiskAnalyzer but enhanced for production use.
    """
    content: str
    reason: str
    comment: str = ""
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    status: SuggestionStatus = SuggestionStatus.GENERATED
    
    # Metadata
    generated_at: datetime = field(default_factory=datetime.now)
    accepted_at: Optional[datetime] = None
    modified_by_user: bool = False
    user_feedback: Optional[str] = None
    
    # Model info
    model_name: str = "gemini-1.5-pro"
    temperature: float = 0.3
    
    # Context
    source_text_snippet: str = ""  # Text that led to this suggestion
    
    def accept(self, feedback: str = None):
        """Mark suggestion as accepted"""
        self.status = SuggestionStatus.ACCEPTED
        self.accepted_at = datetime.now()
        if feedback:
            self.user_feedback = feedback
    
    def reject(self, feedback: str = None):
        """Mark suggestion as rejected"""
        self.status = SuggestionStatus.REJECTED
        if feedback:
            self.user_feedback = feedback
    
    def modify(self, new_content: str, feedback: str = None):
        """Mark suggestion as modified by user"""
        self.content = new_content
        self.status = SuggestionStatus.MODIFIED
        self.modified_by_user = True
        if feedback:
            self.user_feedback = feedback
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['confidence'] = self.confidence.value
        data['status'] = self.status.value
        data['generated_at'] = self.generated_at.isoformat()
        data['accepted_at'] = self.accepted_at.isoformat() if self.accepted_at else None
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AiSuggestion':
        """Create instance from dictionary"""
        # Parse enums
        data['confidence'] = ConfidenceLevel(data.get('confidence', 'medium'))
        data['status'] = SuggestionStatus(data.get('status', 'generated'))
        
        # Parse dates
        if 'generated_at' in data and isinstance(data['generated_at'], str):
            data['generated_at'] = datetime.fromisoformat(data['generated_at'])
        if 'accepted_at' in data and data['accepted_at']:
            data['accepted_at'] = datetime.fromisoformat(data['accepted_at'])
        
        return cls(**data)


@dataclass
class RiskEntry:
    """
    Represents a complete risk entry with AI suggestions.
    Enhanced version of the simple dict approach.
    """
    # Core risk data
    description: str
    category: str
    probability: str
    impact: str
    strategy: str
    suggested_action: str
    source: str = ""
    
    # AI metadata
    ai_suggestions: List[AiSuggestion] = field(default_factory=list)
    selected_suggestion_idx: Optional[int] = None
    
    # Reasoning
    reasoning: str = ""
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    
    # Temporal
    identified_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    
    # Quantitative (for EMV, Monte Carlo)
    severity_score: Optional[int] = None  # 1-10
    occurrence_score: Optional[int] = None  # 1-10
    detection_score: Optional[int] = None  # 1-10
    rpn: Optional[int] = None  # Risk Priority Number
    
    financial_impact: Optional[float] = None  # In currency
    
    def calculate_rpn(self):
        """Calculate Risk Priority Number"""
        if all([self.severity_score, self.occurrence_score, self.detection_score]):
            self.rpn = self.severity_score * self.occurrence_score * self.detection_score
        return self.rpn
    
    def add_suggestion(self, suggestion: AiSuggestion):
        """Add an AI suggestion"""
        self.ai_suggestions.append(suggestion)
        self.last_updated = datetime.now()
    
    def select_suggestion(self, idx: int):
        """Select a specific suggestion"""
        if 0 <= idx < len(self.ai_suggestions):
            self.selected_suggestion_idx = idx
            suggestion = self.ai_suggestions[idx]
            
            # Apply suggestion content to main fields
            if suggestion.content:
                # Parse suggestion content if structured
                pass  # Can be extended
            
            suggestion.accept()
            self.last_updated = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['confidence'] = self.confidence.value
        data['identified_at'] = self.identified_at.isoformat()
        data['last_updated'] = self.last_updated.isoformat()
        data['ai_suggestions'] = [s.to_dict() for s in self.ai_suggestions]
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RiskEntry':
        """Create from dictionary"""
        # Parse nested suggestions
        if 'ai_suggestions' in data:
            data['ai_suggestions'] = [
                AiSuggestion.from_dict(s) for s in data['ai_suggestions']
            ]
        
        # Parse enums and dates
        if 'confidence' in data:
            data['confidence'] = ConfidenceLevel(data['confidence'])
        if 'identified_at' in data and isinstance(data['identified_at'], str):
            data['identified_at'] = datetime.fromisoformat(data['identified_at'])
        if 'last_updated' in data and isinstance(data['last_updated'], str):
            data['last_updated'] = datetime.fromisoformat(data['last_updated'])
        
        return cls(**data)


@dataclass
class FMEASession:
    """
    Represents a complete FMEA analysis session.
    Aggregates multiple risk entries with session metadata.
    """
    session_id: str
    product_name: str
    project_phase: str
    
    # Risks
    risks: List[RiskEntry] = field(default_factory=list)
    
    # Session metadata
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    
    # Source documents
    source_files: List[str] = field(default_factory=list)
    
    # Configuration
    model_name: str = "gemini-1.5-pro"
    language: str = "en"
    use_rag: bool = False
    
    # Statistics
    total_suggestions_generated: int = 0
    total_suggestions_accepted: int = 0
    total_suggestions_rejected: int = 0
    total_suggestions_modified: int = 0
    
    def add_risk(self, risk: RiskEntry):
        """Add a risk to session"""
        self.risks.append(risk)
        self.last_updated = datetime.now()
    
    def update_statistics(self):
        """Recalculate statistics from risks"""
        self.total_suggestions_generated = sum(
            len(r.ai_suggestions) for r in self.risks
        )
        self.total_suggestions_accepted = sum(
            sum(1 for s in r.ai_suggestions if s.status == SuggestionStatus.ACCEPTED)
            for r in self.risks
        )
        self.total_suggestions_rejected = sum(
            sum(1 for s in r.ai_suggestions if s.status == SuggestionStatus.REJECTED)
            for r in self.risks
        )
        self.total_suggestions_modified = sum(
            sum(1 for s in r.ai_suggestions if s.status == SuggestionStatus.MODIFIED)
            for r in self.risks
        )
    
    def get_acceptance_rate(self) -> float:
        """Calculate suggestion acceptance rate"""
        if self.total_suggestions_generated == 0:
            return 0.0
        return self.total_suggestions_accepted / self.total_suggestions_generated
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        self.update_statistics()
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['last_updated'] = self.last_updated.isoformat()
        data['risks'] = [r.to_dict() for r in self.risks]
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FMEASession':
        """Create from dictionary"""
        if 'risks' in data:
            data['risks'] = [RiskEntry.from_dict(r) for r in data['risks']]
        
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if 'last_updated' in data and isinstance(data['last_updated'], str):
            data['last_updated'] = datetime.fromisoformat(data['last_updated'])
        
        return cls(**data)


# Example usage and testing
if __name__ == "__main__":
    # Create a suggestion
    suggestion = AiSuggestion(
        content="Implement redundant power supply",
        reason="High criticality component with single point of failure",
        comment="Consider N+1 configuration",
        confidence=ConfidenceLevel.HIGH
    )
    
    print("Suggestion created:")
    print(f"  Content: {suggestion.content}")
    print(f"  Reason: {suggestion.reason}")
    print(f"  Status: {suggestion.status.value}")
    
    # Accept it
    suggestion.accept("Great suggestion, implemented!")
    print(f"\nAfter acceptance:")
    print(f"  Status: {suggestion.status.value}")
    print(f"  Feedback: {suggestion.user_feedback}")
    
    # Create a risk entry
    risk = RiskEntry(
        description="Power supply failure in ECU",
        category="Technical",
        probability="Medium",
        impact="High",
        strategy="Mitigate",
        suggested_action="Add redundancy",
        reasoning="Critical component analysis",
        severity_score=8,
        occurrence_score=5,
        detection_score=6
    )
    
    risk.add_suggestion(suggestion)
    risk.calculate_rpn()
    
    print(f"\nRisk created:")
    print(f"  Description: {risk.description}")
    print(f"  RPN: {risk.rpn}")
    print(f"  Suggestions: {len(risk.ai_suggestions)}")
    
    # Serialize
    risk_dict = risk.to_dict()
    print(f"\nSerialized to dict: {len(str(risk_dict))} chars")
    
    # Deserialize
    risk_restored = RiskEntry.from_dict(risk_dict)
    print(f"Restored from dict: {risk_restored.description}")
