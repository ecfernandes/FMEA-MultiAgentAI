"""
Test script to verify Monte Carlo simulation functionality
"""

import sys
sys.path.insert(0, 'c:/Users/Usuário/OneDrive/_2025_POST DOC_UTFPR_UTC/_Management Project _AI/PM_AI')

from src.analytics.monte_carlo import run_monte_carlo_simulation

# Test data
test_risks = [
    {
        'min': 5000,
        'likely': 10000,
        'max': 20000,
        'probability': 0.50  # 50%
    },
    {
        'min': 2000,
        'likely': 5000,
        'max': 10000,
        'probability': 0.30  # 30%
    },
    {
        'min': 1000,
        'likely': 3000,
        'max': 8000,
        'probability': 0.70  # 70%
    }
]

print("Testing Monte Carlo simulation...")
print(f"Number of test risks: {len(test_risks)}")
print()

try:
    # Run simulation
    results = run_monte_carlo_simulation(test_risks, num_simulations=1000)
    
    print("✅ Simulation completed successfully!")
    print()
    print(f"Mean Total Loss: ${results['mean']:,.2f}")
    print(f"Median (P50): ${results['median']:,.2f}")
    print(f"Std Deviation: ${results['std_dev']:,.2f}")
    print()
    print("Key Percentiles:")
    print(f"  P10: ${results['percentiles']['P10']:,.0f}")
    print(f"  P25: ${results['percentiles']['P25']:,.0f}")
    print(f"  P50: ${results['percentiles']['P50']:,.0f}")
    print(f"  P75: ${results['percentiles']['P75']:,.0f}")
    print(f"  P90: ${results['percentiles']['P90']:,.0f}")
    print()
    print(f"VaR 95: ${results.get('var_95', 'N/A'):,.0f}")
    print()
    print(f"Number of simulations: {len(results.get('simulations', []))}")
    
except Exception as e:
    print(f"❌ Error running simulation: {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()
