"""
Machine Learning-based Probability Calibrator.
Learns from RAG history to quantify probabilities objectively.
"""

from typing import Dict, List, Optional, Tuple
import numpy as np
from dataclasses import dataclass


@dataclass
class HistoricalRisk:
    """Historical risk from RAG."""
    description: str
    category: str
    stated_probability: str  # "High", "Medium", "Low"
    actually_occurred: bool  # True if risk occurred
    impact_realized: Optional[float] = None  # Realized impact if occurred


@dataclass
class ProbabilityCalibration:
    """Probability calibration."""
    qualitative: str  # "High", "Medium", "Low"
    quantitative_range: Tuple[float, float]  # (min, max) in %
    quantitative_mean: float  # Mean value in %
    confidence: float  # Calibration confidence (0-1)
    sample_size: int  # Number of historical cases
    accuracy: float  # Historical accuracy for this category


class ProbabilityCalibrator:
    """
    Calibrates subjective probabilities into quantitative values
    using Machine Learning over RAG history.
    
    Usage:
        calibrator = ProbabilityCalibrator()
        
        # Load RAG history
        historical_risks = [...]
        calibrator.train(historical_risks)
        
        # Convert "High" to numeric probability
        prob = calibrator.calibrate("High", category="schedule")
        print(f"Probability: {prob.quantitative_mean}%")
        print(f"Range: {prob.quantitative_range[0]}-{prob.quantitative_range[1]}%")
    """
    
    def __init__(self):
        """Initialize calibrator with PMBOK default values."""
        # PMBOK default values before training
        self.default_calibrations = {
            "High": (70.0, 90.0, 80.0),  # (min, max, mean)
            "Medium": (40.0, 70.0, 50.0),
            "Low": (10.0, 40.0, 20.0),
            "Very High": (85.0, 100.0, 90.0),
            "Very Low": (0.0, 10.0, 5.0)
        }
        
        # English/French/Portuguese mapping to internal labels
        self.language_mapping = {
            # Portuguese
            "Alta": "High",
            "Média": "Medium",
            "Baixa": "Low",
            "Muito Alta": "Very High",
            "Muito Baixa": "Very Low",
            # French
            "Haute": "High",
            "Moyenne": "Medium",
            "Faible": "Low",
            "Très Haute": "Very High",
            "Très Faible": "Very Low"
        }
        
        self.calibrations = {}  # Filled after training
        self.is_trained = False
    
    def train(self, historical_risks: List[HistoricalRisk]) -> Dict[str, ProbabilityCalibration]:
        """
        Train calibrator using historical RAG data.
        
        Args:
            historical_risks: List of historical risks.
            
        Returns:
            Learned calibrations by category.
        """
        if not historical_risks:
            print("⚠️ No historical data. Using PMBOK default calibration.")
            return self._get_default_calibrations()
        
        # Group by stated probability
        grouped = {}
        for risk in historical_risks:
            prob = self._normalize_probability(risk.stated_probability)
            if prob not in grouped:
                grouped[prob] = []
            grouped[prob].append(risk)
        
        # Compute calibrations
        calibrations = {}
        for prob_label, risks in grouped.items():
            # Observed occurrence rate
            occurred = [r.actually_occurred for r in risks]
            occurrence_rate = np.mean(occurred) * 100 if occurred else 50.0
            
            # Compute interval (±10% by default)
            min_prob = max(0, occurrence_rate - 10)
            max_prob = min(100, occurrence_rate + 10)
            
            # Accuracy: how close to expected value
            expected = self.default_calibrations.get(prob_label, (0, 100, 50))[2]
            accuracy = 1 - abs(occurrence_rate - expected) / 100
            
            calibrations[prob_label] = ProbabilityCalibration(
                qualitative=prob_label,
                quantitative_range=(min_prob, max_prob),
                quantitative_mean=occurrence_rate,
                confidence=min(1.0, len(risks) / 10),  # More data = more confidence
                sample_size=len(risks),
                accuracy=accuracy
            )
        
        self.calibrations = calibrations
        self.is_trained = True
        
        return calibrations
    
    def calibrate(
        self, 
        probability_label: str,
        category: Optional[str] = None,
        use_conservative: bool = False
    ) -> ProbabilityCalibration:
        """
        Convert qualitative probability to quantitative value.
        
        Args:
            probability_label: "High", "Medium", "Low", etc.
            category: Risk category (to refine calibration).
            use_conservative: If True, use a more conservative value.
            
        Returns:
            Calibration with numeric value.
        """
        # Normalize label
        prob_label = self._normalize_probability(probability_label)
        
        # Use trained calibration if available
        if self.is_trained and prob_label in self.calibrations:
            calibration = self.calibrations[prob_label]
            
            # If conservative, use upper bound
            if use_conservative:
                calibration.quantitative_mean = calibration.quantitative_range[1]
            
            return calibration
        
        # Fallback: use PMBOK default calibration
        default = self.default_calibrations.get(prob_label, (0, 100, 50))
        
        return ProbabilityCalibration(
            qualitative=prob_label,
            quantitative_range=(default[0], default[1]),
            quantitative_mean=default[2],
            confidence=0.5,  # Medium confidence (untrained)
            sample_size=0,
            accuracy=0.7  # Assume 70% default accuracy
        )
    
    def _normalize_probability(self, label: str) -> str:
        """Normalize label to internal English standard."""
        label = label.strip().title()
        
        # Map labels from other languages
        if label in self.language_mapping:
            return self.language_mapping[label]
        
        # Already in internal standard (or unknown label)
        return label
    
    def _get_default_calibrations(self) -> Dict[str, ProbabilityCalibration]:
        """Return PMBOK default calibrations."""
        calibrations = {}
        
        for label, (min_p, max_p, mean_p) in self.default_calibrations.items():
            calibrations[label] = ProbabilityCalibration(
                qualitative=label,
                quantitative_range=(min_p, max_p),
                quantitative_mean=mean_p,
                confidence=0.5,
                sample_size=0,
                accuracy=0.7
            )
        
        return calibrations
    
    def get_statistics(self) -> Dict:
        """Return calibrator statistics."""
        if not self.is_trained:
            return {
                "trained": False,
                "using": "PMBOK defaults"
            }
        
        return {
            "trained": True,
            "categories": len(self.calibrations),
            "total_samples": sum(c.sample_size for c in self.calibrations.values()),
            "average_confidence": np.mean([c.confidence for c in self.calibrations.values()]),
            "average_accuracy": np.mean([c.accuracy for c in self.calibrations.values()])
        }


def suggest_probability_from_text(text: str) -> Tuple[str, float]:
    """
    Suggest probability based on keywords in text.
    Useful for initial document analysis.
    
    Args:
        text: Risk description.
        
    Returns:
        (category, suggestion confidence)
    """
    text_lower = text.lower()
    
    # Keywords by category
    keywords = {
        "Very High": ["certainly", "inevitable", "definitely", "always", "constantly"],
        "High": ["probable", "frequent", "common", "recurring", "expected"],
        "Medium": ["possible", "may", "perhaps", "moderate", "reasonable"],
        "Low": ["unlikely", "rare", "improbable", "hardly"],
        "Very Low": ["almost impossible", "extremely rare", "never", "impossible"]
    }
    
    # Count matches
    scores = {}
    for category, words in keywords.items():
        score = sum(1 for word in words if word in text_lower)
        scores[category] = score
    
    # If no match, return Medium
    if all(score == 0 for score in scores.values()):
        return ("Medium", 0.3)
    
    # Category with most matches
    best_category = max(scores, key=scores.get)
    max_score = scores[best_category]
    
    # Confidence based on number of matches
    confidence = min(0.9, 0.4 + (max_score * 0.2))
    
    return (best_category, confidence)


def format_calibration(calibration: ProbabilityCalibration) -> str:
    """
    Format calibration for display.
    
    Args:
        calibration: Probability calibration.
        
    Returns:
        Formatted string.
    """
    output = []
    output.append(f"🎯 Probability Calibration: {calibration.qualitative}")
    output.append(f"")
    output.append(f"📊 Quantitative Value:")
    output.append(f"   • Mean: {calibration.quantitative_mean:.1f}%")
    output.append(f"   • Range: {calibration.quantitative_range[0]:.1f}% - {calibration.quantitative_range[1]:.1f}%")
    output.append(f"")
    output.append(f"📈 Reliability:")
    output.append(f"   • Confidence: {calibration.confidence*100:.0f}%")
    output.append(f"   • Historical Accuracy: {calibration.accuracy*100:.0f}%")
    output.append(f"   • Based on: {calibration.sample_size} cases")
    
    return "\n".join(output)
