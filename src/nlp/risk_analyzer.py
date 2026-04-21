"""
Risk Analysis Module with LLM
Functions for interacting with the UTC LLM platform (OpenAI-compatible)
"""

import os
from openai import OpenAI
import json
from typing import List, Dict, Optional


class RiskAnalyzer:
    """
    Class for risk analysis using the UTC LLM platform
    """

    def __init__(self, api_key: str, model_name: str | None = None, temperature: float = 0.3, language: str = 'en'):
        """
        Initialize risk analyzer

        Args:
            api_key:    UTC platform API key
            model_name: Model ID to use (defaults to LLM_DEFAULT_MODEL env var)
            temperature: Temperature parameter (0.0 = conservative, 1.0 = creative)
            language:   Language for risk analysis (en, fr, pt-br)
        """
        base_url = os.getenv("LLM_BASE_URL", "https://ia.beta.utc.fr/api/v1")
        self.model_name  = model_name or os.getenv("LLM_DEFAULT_MODEL", "qwen3527b-no-think")
        self.temperature = temperature
        self.language    = language
        self.client      = OpenAI(api_key=api_key, base_url=base_url)
    
    
    def analyze_risks(self, text: str, max_chars: int = 25000) -> List[Dict]:
        """
        Analyze text and identify risks
        
        Args:
            text: Text to analyze
            max_chars: Character limit to send to model
        
        Returns:
            List[Dict]: List of identified risks
        """
        # Limit text size
        truncated_text = text[:max_chars]
        
        # Build prompt
        prompt = self._build_risk_analysis_prompt(truncated_text)
        
        try:
            # Generate analysis
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "user", "content": prompt},
                ],
                temperature=self.temperature,
                max_tokens=8192,
            )
            raw = response.choices[0].message.content

            # Process response
            risks = self._parse_response(raw)

            return risks
        
        except Exception as e:
            raise Exception(f"Error in risk analysis: {str(e)}")
    
    
    def _build_risk_analysis_prompt(self, text: str) -> str:
        """
        Build engineering prompt for risk analysis
        
        Args:
            text: Text to analyze
        
        Returns:
            str: Formatted prompt
        """
        from .prompts import get_risk_analysis_prompt, get_field_names
        
        # Get prompt template and field names for selected language
        prompt_template = get_risk_analysis_prompt(self.language)
        fields = get_field_names(self.language)
        
        # Replace placeholder with actual text
        prompt = prompt_template.replace('{{text}}', text)
        
        return prompt
    
    
    def _parse_response(self, response_text: str) -> List[Dict]:
        """
        Parse JSON response from model
        
        Args:
            response_text: Model response text
        
        Returns:
            List[Dict]: List of parsed risks
        """
        # Clean response
        cleaned = response_text.strip()
        cleaned = cleaned.replace("```json", "").replace("```", "").strip()
        
        # Try to parse JSON
        try:
            data = json.loads(cleaned)
            
            # Validate structure
            if not isinstance(data, list):
                raise ValueError("Response is not a list")
            
            return data
        
        except json.JSONDecodeError as e:
            raise Exception(f"Error parsing JSON: {str(e)}\nResponse: {cleaned[:500]}")
    
    
    def categorize_by_severity(self, risks: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Categorize risks by severity (Probability × Impact)
        
        Args:
            risks: List of risks
        
        Returns:
            Dict: Risks grouped by severity
        """
        from .prompts import get_field_names
        
        fields = get_field_names(self.language)
        prob_field = fields['probability']
        impact_field = fields['impact']
        
        prob_high = fields['probability_levels']['high']
        prob_medium = fields['probability_levels']['medium']
        prob_low = fields['probability_levels']['low']
        
        impact_high = fields['impact_levels']['high']
        impact_medium = fields['impact_levels']['medium']
        impact_low = fields['impact_levels']['low']
        
        severity_map = {
            (prob_high, impact_high): "Critical",
            (prob_high, impact_medium): "High",
            (prob_high, impact_low): "Medium",
            (prob_medium, impact_high): "High",
            (prob_medium, impact_medium): "Medium",
            (prob_medium, impact_low): "Low",
            (prob_low, impact_high): "Medium",
            (prob_low, impact_medium): "Low",
            (prob_low, impact_low): "Low",
        }
        
        categorized = {
            "Critical": [],
            "High": [],
            "Medium": [],
            "Low": []
        }
        
        for risk in risks:
            prob = risk.get(prob_field, prob_medium)
            impact = risk.get(impact_field, impact_medium)
            severity = severity_map.get((prob, impact), "Medium")
            
            categorized[severity].append(risk)
        
        return categorized
