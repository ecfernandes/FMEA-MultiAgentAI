"""
EMV (Expected Monetary Value) Analyzer
Simplified version for integration with RiskAIAnalyst
Calculates financial risk metrics for project risk management.
"""

import pandas as pd
from typing import List, Dict, Tuple, Optional


class SimpleEMVAnalyzer:
    """
    Simplified EMV Analyzer for risk financial analysis.
    
    EMV = Probability × Financial Impact
    Used to prioritize risks by their financial significance.
    """
    
    def __init__(self):
        # Convert qualitative levels to numeric values (%)
        self.probability_mapping = {
            'High': 70,
            'Medium': 40,
            'Low': 15
        }
        
        # Percentage buffer for management reserve (over total EMV)
        self.management_reserve_factor = 0.15  # 15% additional
    
    def calculate_emv(self, probability: float, impact: float) -> float:
        """
        Calculate EMV for an individual risk.
        
        Args:
            probability: Probability in % (0-100).
            impact: Financial impact (most likely value).
            
        Returns:
            EMV in monetary value.
        """
        return (probability / 100) * impact
    
    def calculate_three_point_estimate(self, min_val: float, likely: float, max_val: float) -> Dict[str, float]:
        """
        Calculate three-point estimate (PERT - Program Evaluation and Review Technique).
        
        Args:
            min_val: Minimum value (optimistic).
            likely: Most likely value.
            max_val: Maximum value (pessimistic).
            
        Returns:
            Dict with expected_value and standard_deviation.
        """
        # PERT formula: (Min + 4×Likely + Max) / 6
        expected_value = (min_val + 4 * likely + max_val) / 6
        
        # Standard deviation: (Max - Min) / 6
        std_dev = (max_val - min_val) / 6
        
        return {
            'expected_value': expected_value,
            'standard_deviation': std_dev,
            'range': max_val - min_val
        }
    
    def convert_qualitative_to_numeric(self, probability_level: str) -> float:
        """
        Convert qualitative level to numeric probability.
        
        Args:
            probability_level: 'High', 'Medium', or 'Low'.
            
        Returns:
            Probability in % (0-100).
        """
        return self.probability_mapping.get(probability_level, 40)
    
    def analyze_risks(self, risks_data: List[Dict]) -> pd.DataFrame:
        """
        Analyze risk list and compute EMV for each risk.
        
        Args:
            risks_data: List of dicts with financial data.
        
        Returns:
            DataFrame enriched with EMV and financial metrics.
        """
        results = []
        
        for risk in risks_data:
            # Extract probability (convert if qualitative)
            prob = risk.get('Probability')
            if isinstance(prob, str):
                prob_numeric = self.convert_qualitative_to_numeric(prob)
            else:
                prob_numeric = prob if prob else 40  # Default Medium
            
            # Check if financial data exists
            has_financial = all(k in risk for k in ['Financial_Impact_Min', 'Financial_Impact_Likely', 'Financial_Impact_Max'])
            
            if has_financial:
                min_impact = risk['Financial_Impact_Min']
                likely_impact = risk['Financial_Impact_Likely']
                max_impact = risk['Financial_Impact_Max']
                
                # Compute three-point estimate
                pert = self.calculate_three_point_estimate(min_impact, likely_impact, max_impact)
                expected_impact = pert['expected_value']
                std_dev = pert['standard_deviation']
            else:
                # No financial data
                expected_impact = None
                std_dev = None
                min_impact = None
                likely_impact = None
                max_impact = None
            
            # Compute EMV if financial impact is available
            emv = self.calculate_emv(prob_numeric, expected_impact) if expected_impact else None
            
            results.append({
                'Risk Description': risk.get('Risk Description', ''),
                'Category': risk.get('Category', ''),
                'Probability_Qualitative': risk.get('Probability', ''),
                'Probability_Numeric': prob_numeric,
                'Impact_Min': min_impact,
                'Impact_Likely': likely_impact,
                'Impact_Max': max_impact,
                'Impact_Expected': expected_impact,
                'Impact_StdDev': std_dev,
                'EMV': emv,
                'Strategy': risk.get('Strategy', ''),
                'Source': risk.get('Source', '')
            })
        
        df = pd.DataFrame(results)
        
        # Sort by EMV (highest to lowest)
        if 'EMV' in df.columns and df['EMV'].notna().any():
            df = df.sort_values('EMV', ascending=False, na_position='last')
        
        return df
    
    def calculate_contingency_reserve(self, risks_df: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate contingency reserve based on EMVs.
        
        Args:
            risks_df: DataFrame with EMV column.
            
        Returns:
            Dict with reserve metrics.
        """
        # Filter only risks with EMV
        risks_with_emv = risks_df[risks_df['EMV'].notna()]
        
        if len(risks_with_emv) == 0:
            return {
                'total_emv': 0,
                'contingency_reserve': 0,
                'management_reserve': 0,
                'total_reserve': 0,
                'num_risks_analyzed': 0
            }
        
        total_emv = risks_with_emv['EMV'].sum()
        
        # Contingency reserve = sum of EMVs
        contingency_reserve = total_emv
        
        # Management reserve = additional buffer (15% of EMV)
        management_reserve = total_emv * self.management_reserve_factor
        
        # Total reserve
        total_reserve = contingency_reserve + management_reserve
        
        return {
            'total_emv': total_emv,
            'contingency_reserve': contingency_reserve,
            'management_reserve': management_reserve,
            'total_reserve': total_reserve,
            'num_risks_analyzed': len(risks_with_emv)
        }
    
    def rank_by_emv(self, risks_df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
        """
        Return top N risks by EMV.
        """
        risks_with_emv = risks_df[risks_df['EMV'].notna()].copy()
        risks_with_emv['Rank'] = range(1, len(risks_with_emv) + 1)
        return risks_with_emv.head(top_n)
    
    def get_summary_statistics(self, risks_df: pd.DataFrame) -> Dict:
        """
        Return summary statistics of the analysis.
        """
        risks_with_emv = risks_df[risks_df['EMV'].notna()]
        
        if len(risks_with_emv) == 0:
            return {
                'total_risks': len(risks_df),
                'risks_with_financial_data': 0,
                'mean_emv': 0,
                'median_emv': 0,
                'max_emv': 0,
                'min_emv': 0
            }
        
        return {
            'total_risks': len(risks_df),
            'risks_with_financial_data': len(risks_with_emv),
            'mean_emv': risks_with_emv['EMV'].mean(),
            'median_emv': risks_with_emv['EMV'].median(),
            'max_emv': risks_with_emv['EMV'].max(),
            'min_emv': risks_with_emv['EMV'].min(),
            'total_emv': risks_with_emv['EMV'].sum()
        }


# Original complex implementation preserved below for future use
# ================================================================
# (Original code with Enum, dataclass, DecisionType, etc. commented out)
