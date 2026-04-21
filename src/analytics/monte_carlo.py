"""
Simplified Monte Carlo Simulation for Risk Analysis
Estimates probabilistic ranges for project costs based on risks
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from scipy import stats


class SimpleMonteCarloSimulator:
    """
    Simplified Monte Carlo simulator for project risk cost analysis.
    """
    
    def __init__(self, n_simulations: int = 10000, random_seed: Optional[int] = None):
        """
        Initialize simulator.
        
        Args:
            n_simulations: Number of Monte Carlo iterations
            random_seed: Random seed for reproducibility
        """
        self.n_simulations = n_simulations
        if random_seed:
            np.random.seed(random_seed)
    
    def simulate_risk_costs(self, risks_df: pd.DataFrame) -> Dict:
        """
        Run Monte Carlo simulation for risks with financial data.
        
        Args:
            risks_df: DataFrame with columns Impact_Min, Impact_Likely, Impact_Max, Probability_Numeric
            
        Returns:
            Dict with simulation results and statistics
        """
        # Filter risks with complete financial data
        risks_with_financial = risks_df[
            risks_df['Impact_Min'].notna() & 
            risks_df['Impact_Likely'].notna() & 
            risks_df['Impact_Max'].notna()
        ].copy()
        
        if len(risks_with_financial) == 0:
            return self._empty_result()
        
        # Run simulation
        total_costs = np.zeros(self.n_simulations)
        
        for idx, risk in risks_with_financial.iterrows():
            # PERT distribution (Beta distribution variant)
            min_val = risk['Impact_Min']
            likely = risk['Impact_Likely']
            max_val = risk['Impact_Max']
            prob = risk['Probability_Numeric'] / 100  # Convert % to 0-1
            
            # Generate PERT distribution samples
            risk_impacts = self._pert_distribution(min_val, likely, max_val, self.n_simulations)
            
            # Apply probability (risk occurrence)
            risk_occurs = np.random.random(self.n_simulations) < prob
            risk_costs = risk_impacts * risk_occurs
            
            total_costs += risk_costs
        
        # Calculate statistics
        results = self._calculate_statistics(total_costs, risks_with_financial)
        
        return results
    
    def _pert_distribution(self, min_val: float, likely: float, max_val: float, size: int) -> np.ndarray:
        """
        Generate samples from PERT distribution.
        
        PERT uses Beta distribution with parameters derived from min, likely, max.
        """
        # PERT formula for Beta parameters
        # Mean = (min + 4*likely + max) / 6
        # Alpha and Beta parameters for Beta distribution
        
        if max_val == min_val:
            return np.full(size, likely)
        
        # Standard PERT calculation
        mean = (min_val + 4 * likely + max_val) / 6
        
        # Shape parameters for Beta distribution
        range_val = max_val - min_val
        
        if range_val == 0:
            return np.full(size, likely)
        
        # Simplified Beta parameters
        # Using PERT approximation
        alpha = 1 + 4 * (likely - min_val) / range_val
        beta = 1 + 4 * (max_val - likely) / range_val
        
        # Generate Beta samples and scale to [min, max]
        beta_samples = np.random.beta(alpha, beta, size)
        pert_samples = min_val + beta_samples * range_val
        
        return pert_samples
    
    def _calculate_statistics(self, samples: np.ndarray, risks_df: pd.DataFrame) -> Dict:
        """
        Calculate statistical metrics from simulation samples.
        """
        return {
            'mean': float(np.mean(samples)),
            'median': float(np.median(samples)),
            'std_dev': float(np.std(samples)),
            'min': float(np.min(samples)),
            'max': float(np.max(samples)),
            'percentiles': {
                'P10': float(np.percentile(samples, 10)),
                'P25': float(np.percentile(samples, 25)),
                'P50': float(np.percentile(samples, 50)),
                'P75': float(np.percentile(samples, 75)),
                'P90': float(np.percentile(samples, 90)),
                'P95': float(np.percentile(samples, 95)),
                'P99': float(np.percentile(samples, 99))
            },
            'confidence_intervals': {
                '90%': (float(np.percentile(samples, 5)), float(np.percentile(samples, 95))),
                '95%': (float(np.percentile(samples, 2.5)), float(np.percentile(samples, 97.5))),
                '99%': (float(np.percentile(samples, 0.5)), float(np.percentile(samples, 99.5)))
            },
            'num_risks': len(risks_df),
            'num_simulations': self.n_simulations,
            'samples': samples  # For plotting S-curve
        }
    
    def _empty_result(self) -> Dict:
        """Return empty result when no financial data available."""
        return {
            'mean': 0,
            'median': 0,
            'std_dev': 0,
            'min': 0,
            'max': 0,
            'percentiles': {k: 0 for k in ['P10', 'P25', 'P50', 'P75', 'P90', 'P95', 'P99']},
            'confidence_intervals': {'90%': (0, 0), '95%': (0, 0), '99%': (0, 0)},
            'num_risks': 0,
            'num_simulations': 0,
            'samples': np.array([])
        }
    
    def generate_s_curve_data(self, samples: np.ndarray, num_points: int = 100) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate S-curve (cumulative distribution) data for plotting.
        
        Args:
            samples: Simulation samples
            num_points: Number of points in curve
            
        Returns:
            (x_values, cumulative_probabilities)
        """
        if len(samples) == 0:
            return np.array([]), np.array([])
        
        # Sort samples
        sorted_samples = np.sort(samples)
        
        # Calculate cumulative probabilities
        percentiles = np.linspace(0, 100, num_points)
        x_values = np.percentile(sorted_samples, percentiles)
        y_values = percentiles / 100  # Convert to 0-1 scale
        
        return x_values, y_values


def run_monte_carlo_simulation(risks: List[Dict], num_simulations: int = 10000) -> Dict:
    """
    Wrapper function for running Monte Carlo simulation with PERT distribution.
    
    Args:
        risks: List of dicts with {'min': float, 'likely': float, 'max': float, 'probability': float (0-1 or 0-100)}
        num_simulations: Number of simulations
        
    Returns:
        Dict with simulation results
    """
    # Convert to DataFrame format expected by SimpleMonteCarloSimulator
    risks_data = []
    for risk in risks:
        # Handle probability: convert to 0-100 scale
        prob = risk.get('probability', 0.5)
        # If probability is 0-1 (like 0.5 for 50%), convert to percentage
        if prob <= 1.0:
            prob_percent = prob * 100
        else:
            prob_percent = prob
            
        risks_data.append({
            'Impact_Min': risk['min'],
            'Impact_Likely': risk['likely'],
            'Impact_Max': risk['max'],
            'Probability_Numeric': prob_percent  # Always 0-100 scale
        })
    
    df = pd.DataFrame(risks_data)
    
    # Run simulation
    simulator = SimpleMonteCarloSimulator(n_simulations=num_simulations)
    results = simulator.simulate_risk_costs(df)
    
    # Add VaR calculations for different confidence levels
    samples = results.get('samples', np.array([]))
    if len(samples) > 0:
        results['var_80'] = float(np.percentile(samples, 80))
        results['var_85'] = float(np.percentile(samples, 85))
        results['var_90'] = float(np.percentile(samples, 90))
        results['var_95'] = float(np.percentile(samples, 95))
        results['var_99'] = float(np.percentile(samples, 99))
        results['simulations'] = samples
    
    return results
