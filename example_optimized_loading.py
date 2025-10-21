#!/usr/bin/env python3
"""Example demonstrating the optimized data loading in run_backtest.

This example shows how the CLI automatically uses the optimized data loading
when you specify start-date and end-date parameters.
"""

import subprocess
import sys
from pathlib import Path

# Example 1: Old behavior (still works) - loads all data without date filtering
print("Example 1: Running backtest without date filtering")
print("=" * 80)
print("Command:")
print("  python scripts/run_backtest.py equal_weight \\")
print("    --universe-file config/universes.yaml \\")
print("    --universe-name small_test")
print("\nThis will load ALL data from the CSV files, then filter in the backtest engine.")
print()

# Example 2: New optimized behavior - only loads needed columns and date range
print("\nExample 2: Running backtest with date filtering (OPTIMIZED)")
print("=" * 80)
print("Command:")
print("  python scripts/run_backtest.py equal_weight \\")
print("    --universe-file config/universes.yaml \\")
print("    --universe-name small_test \\")
print("    --start-date 2020-01-01 \\")
print("    --end-date 2023-12-31")
print("\nThis will:")
print("  1. Only load columns for assets in 'small_test' universe")
print("  2. Only load rows between 2020-01-01 and 2023-12-31")
print("  3. Significantly reduce memory usage for large universes")
print()

# Example 3: Performance benefit scenario
print("\nExample 3: Maximum benefit scenario")
print("=" * 80)
print("Command:")
print("  python scripts/run_backtest.py risk_parity \\")
print("    --universe-file config/universes.yaml \\")
print("    --universe-name balanced \\  # e.g., 20-50 assets")
print("    --prices-file data/wide_universe_prices.csv \\  # e.g., 1000 columns")
print("    --returns-file data/wide_universe_returns.csv \\")
print("    --start-date 2020-01-01 \\")
print("    --end-date 2023-12-31")
print("\nScenario:")
print("  - CSV files contain 1000 assets (columns)")
print("  - Universe only needs 20-50 assets")
print("  - 5 years of history but backtest only needs 4 years")
print("\nBenefit:")
print("  - ~95% reduction in columns loaded (50/1000)")
print("  - ~20% reduction in rows loaded (4/5 years)")
print("  - Combined: ~96% reduction in memory usage")
print("  - Faster startup time (less data to parse)")
print()

print("\nNOTE: The optimization is automatic - no code changes needed!")
print("Just use --start-date and --end-date flags to enable it.")
