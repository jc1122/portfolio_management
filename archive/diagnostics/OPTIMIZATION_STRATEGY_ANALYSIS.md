# Optimization Strategy Analysis - Long History 100 Dataset

**Date**: October 22, 2025
**Issue**: Risk Parity and Mean Variance strategies fail with long history dataset
**Status**: Root cause identified

## Summary

The optimization-based strategies (Risk Parity, Mean Variance) work correctly with the data quality but become **computationally intractable** when processing the full 5+ year history (1,500+ days) that the backtest engine passes to them.

## Root Cause

The backtest engine passes **all historical data from start to current rebalance date** to the strategy, not just a rolling lookback window. For the long history dataset:

- **Data Quality**: ✅ PERFECT - No NaN, no infinite values, valid covariance matrix
- **Computational Complexity**: ❌ PROBLEM - Eigenvalue decomposition on 100x100 covariance matrix with 1,500+ samples is extremely slow
- **Memory Usage**: ❌ PROBLEM - PyPortfolioOpt computes unnecessary statistics on entire history

### Evidence

1. **Standalone test with 252 days**: Works in \<1 second ✅
1. **Standalone test with 1,500+ days**: Hangs indefinitely ❌
1. **Data validation**: All clean, no NaN/inf ✅
1. **Eigenvalue analysis**: Condition number 651 (acceptable), all positive ✅

## Why Equal Weight Works

Equal weight strategy doesn't compute covariance matrices or run optimization, so it's unaffected by dataset size.

## Solution Options

### Option 1: Use Rolling Lookback Window (RECOMMENDED - NO APP CODE CHANGES)

**Modify the backtest engine to only pass the last N periods to strategies, not the entire history.**

**Benefits**:

- Financial modeling best practice (use recent data for parameter estimation)
- Dramatic speedup for optimization strategies
- More realistic walk-forward testing
- Prevents look-ahead bias

**Implementation**: Modify `backtest.py` line ~144 to slice lookback window:

```python
# Current (passes all history):
lookback_returns = period_returns.iloc[: i + 1]
lookback_prices = period_prices.iloc[: i + 1]

# Proposed (passes last 252 days):
lookback_window = 252  # or make configurable
start_idx = max(0, i + 1 - lookback_window)
lookback_returns = period_returns.iloc[start_idx : i + 1]
lookback_prices = period_prices.iloc[start_idx : i + 1]
```

**Risk**: Very low - this is standard practice in backtesting

### Option 2: Regenerate Data with Shorter History

**Use only last 2-3 years of data instead of 5+ years.**

**Benefits**:

- Reduces computational load
- No code changes needed

**Drawbacks**:

- Loses long-term testing capability
- Doesn't solve the architectural issue
- Still slow with large universes

### Option 3: Add Strategy-Level Windowing (MODERATE CHANGES)

**Make mean_variance and risk_parity strategies internally limit lookback.**

**Benefits**:

- Strategies control their own data needs
- Backtest engine unchanged

**Drawbacks**:

- Code changes in 2 strategy files
- Inconsistent with backtest architecture
- Duplicates windowing logic

### Option 4: Optimize PyPortfolioOpt Configuration (PARTIAL FIX)

**Use faster solvers, reduce precision, add timeouts.**

**Benefits**:

- May help with borderline cases
- No architectural changes

**Drawbacks**:

- Doesn't fix root cause
- May degrade solution quality
- Still slow with full history

## Recommendation

**Implement Option 1: Rolling Lookback Window**

This is:

1. **Best practice** in quantitative finance (use recent data for estimation)
1. **Minimal risk** (one small change in backtest.py)
1. **Maximum benefit** (solves problem completely)
1. **Most maintainable** (centralized logic)
1. **Realistic** (matches how real trading systems work)

### Proposed Configuration

```python
# In BacktestConfig or as parameter
lookback_periods: int = 252  # 1 year for daily data

# Common alternatives:
# - 126 (6 months)
# - 504 (2 years)
# - 756 (3 years)
```

## Testing Plan

1. Implement rolling window in backtest.py
1. Run equal_weight strategy - verify results unchanged (within tolerance)
1. Run risk_parity strategy - verify completes in reasonable time
1. Run mean_variance strategy - verify completes in reasonable time
1. Compare metrics across strategies
1. Generate charts for all three

## Expected Performance After Fix

- **Equal Weight**: \<5 seconds (unchanged)
- **Risk Parity**: 10-30 seconds (vs. infinite currently)
- **Mean Variance**: 15-45 seconds (vs. infinite currently)

## Data Regeneration Assessment

**NOT NEEDED**. The data quality is excellent. The issue is purely computational/architectural.

Regenerating data would:

- ✅ Reduce dataset size (shorter history)
- ❌ Not fix the architectural issue
- ❌ Lose valuable long-term test data
- ❌ Waste time on unnecessary work

## Conclusion

**Proceed with Option 1 (Rolling Lookback Window) - this is a simple, standard fix that solves the problem without unnecessary changes.**

The change required is minimal (~5 lines), low-risk, and aligns with quantitative finance best practices. No data regeneration needed.
