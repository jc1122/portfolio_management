# Troubleshooting Guide

This guide helps you diagnose and fix common issues when using the portfolio management system.

## Table of Contents

1. [Preselection Errors](#preselection-errors)
2. [Membership Policy Errors](#membership-policy-errors)
3. [Eligibility Errors](#eligibility-errors)
4. [Cache Errors](#cache-errors)
5. [Warnings and Their Meaning](#warnings-and-their-meaning)
6. [Performance Issues](#performance-issues)

---

## Preselection Errors

### Error: "top_k must be >= 0"

**Problem**: The `top_k` parameter is negative.

**Example**:
```python
PreselectionConfig(top_k=-5)  # ❌ Invalid
```

**Solution**: Use 0, None (to disable preselection), or a positive integer:
```python
PreselectionConfig(top_k=30)  # ✅ Select top 30 assets
PreselectionConfig(top_k=None)  # ✅ No preselection
```

---

### Error: "skip must be < lookback"

**Problem**: The `skip` parameter is greater than or equal to `lookback`, meaning you're skipping more periods than your lookback window.

**Example**:
```python
PreselectionConfig(lookback=252, skip=252)  # ❌ Invalid
```

**Solution**: Reduce `skip` or increase `lookback`:
```python
PreselectionConfig(lookback=252, skip=1)  # ✅ Skip last day
PreselectionConfig(lookback=252, skip=21)  # ✅ Skip last month
```

**Typical Usage**: `skip=1` to avoid short-term reversals in momentum strategies.

---

### Error: "min_periods must be <= lookback"

**Problem**: You're requiring more minimum periods than your lookback window.

**Example**:
```python
PreselectionConfig(lookback=126, min_periods=252)  # ❌ Invalid
```

**Solution**: Reduce `min_periods` or increase `lookback`:
```python
PreselectionConfig(lookback=252, min_periods=60)  # ✅ Valid
```

**Recommended Ratio**: `min_periods` should be 20-50% of `lookback`.

---

### Error: "Combined weights must sum to 1.0"

**Problem**: When using the `COMBINED` method, `momentum_weight` and `low_vol_weight` don't sum to 1.0.

**Example**:
```python
PreselectionConfig(
    method=PreselectionMethod.COMBINED,
    momentum_weight=0.6,
    low_vol_weight=0.5  # ❌ Sum = 1.1
)
```

**Solution**: Adjust weights to sum to 1.0:
```python
PreselectionConfig(
    method=PreselectionMethod.COMBINED,
    momentum_weight=0.6,
    low_vol_weight=0.4  # ✅ Sum = 1.0
)
```

---

### Error: "returns DataFrame is empty or None"

**Problem**: The returns DataFrame provided is empty.

**Solution**: Ensure you're loading data correctly:
```python
# ❌ Empty DataFrame
returns = pd.DataFrame()

# ✅ Load actual data
returns = pd.read_csv("returns.csv", index_col=0, parse_dates=True)
print(f"Loaded {len(returns)} rows and {len(returns.columns)} assets")
```

---

### Error: "rebalance_date is after the last available date"

**Problem**: Trying to rebalance at a date beyond your data range.

**Example**:
```python
# Data ends at 2023-12-31
preselect.select_assets(returns, rebalance_date=date(2024, 6, 1))  # ❌
```

**Solution**: Use a date within your data range:
```python
max_date = returns.index.max().date()
print(f"Data available until: {max_date}")
preselect.select_assets(returns, rebalance_date=date(2023, 12, 1))  # ✅
```

---

### Error: "Insufficient data: need X periods, have Y periods"

**Problem**: Not enough historical data for the configured lookback period.

**Solution**: Either:
1. Provide more historical data
2. Reduce `lookback` or `min_periods`

```python
# Option 1: Load more historical data
returns = load_returns(start_date="2020-01-01")  # ✅ More history

# Option 2: Reduce requirements
config = PreselectionConfig(
    lookback=126,  # ✅ Reduced from 252
    min_periods=30  # ✅ Reduced from 60
)
```

---

## Membership Policy Errors

### Error: "buffer_rank must be >= 1"

**Problem**: `buffer_rank` is zero or negative.

**Solution**: Use a positive integer greater than `top_k`:
```python
MembershipPolicy(
    buffer_rank=50,  # ✅ Should be > top_k (e.g., 30)
    top_k=30
)
```

**Best Practice**: Set `buffer_rank` to `top_k + 20%` or more for stability.

---

### Error: "max_turnover must be in [0, 1]"

**Problem**: `max_turnover` is outside the valid range.

**Example**:
```python
MembershipPolicy(max_turnover=30)  # ❌ Should be 0.30
```

**Solution**: Use a fraction between 0.0 and 1.0:
```python
MembershipPolicy(max_turnover=0.30)  # ✅ 30% turnover
MembershipPolicy(max_turnover=0.20)  # ✅ 20% turnover
```

---

### Error: "holding_periods required when min_holding_periods is set"

**Problem**: Policy requires minimum holding periods but you haven't provided the tracking dict.

**Solution**: Provide a dict mapping assets to holding periods:
```python
policy = MembershipPolicy(min_holding_periods=3)
holding_periods = {
    "AAPL": 5,  # Held for 5 rebalance periods
    "MSFT": 2,  # Held for 2 rebalance periods
    "GOOGL": 1  # Held for 1 rebalance period
}

apply_membership_policy(
    current_holdings=["AAPL", "MSFT", "GOOGL"],
    preselected_ranks=ranks,
    policy=policy,
    holding_periods=holding_periods,  # ✅ Required
    top_k=30
)
```

---

### Error: "holding_periods contains negative values"

**Problem**: Holding periods must be non-negative integers.

**Solution**: Ensure all values are >= 0:
```python
holding_periods = {
    "AAPL": 5,   # ✅
    "MSFT": 0,   # ✅ Just added
    "GOOGL": -1  # ❌ Invalid
}
```

---

### Error: "top_k must be > 0"

**Problem**: `top_k` parameter is zero or negative.

**Solution**: Use a positive integer:
```python
apply_membership_policy(
    ...,
    top_k=30  # ✅ Valid
)
```

---

## Eligibility Errors

### Error: "returns DataFrame is empty or None"

**Problem**: Returns DataFrame is empty.

**Solution**: Load data before computing eligibility:
```python
# ❌ Empty DataFrame
returns = pd.DataFrame()

# ✅ Load data
returns = pd.read_csv("returns.csv", index_col=0, parse_dates=True)
```

---

### Error: "min_history_days must be > 0"

**Problem**: `min_history_days` is zero or negative.

**Solution**: Use a positive integer:
```python
compute_pit_eligibility(
    returns,
    date=date(2023, 12, 31),
    min_history_days=252  # ✅ 1 year
)
```

**Common Values**:
- 63 days = 3 months
- 126 days = 6 months
- 252 days = 1 year

---

### Error: "date is after the last available date"

**Problem**: Eligibility date is beyond your data range.

**Solution**: Check data range and use a valid date:
```python
print(f"Data range: {returns.index.min()} to {returns.index.max()}")

# Use a date within range
compute_pit_eligibility(
    returns,
    date=date(2023, 10, 31)  # ✅ Within range
)
```

---

## Cache Errors

### Error: "cache_dir is not writable"

**Problem**: The cache directory doesn't have write permissions.

**Solution**: Use a writable directory:
```python
from pathlib import Path

# ❌ System directory (may not be writable)
cache = FactorCache(Path("/var/cache/portfolio"))

# ✅ User home directory
cache = FactorCache(Path("~/.cache/portfolio").expanduser())

# ✅ Project directory
cache = FactorCache(Path(".cache/factors"))
```

**Troubleshooting**:
1. Check permissions: `ls -la ~/.cache`
2. Create directory manually: `mkdir -p ~/.cache/portfolio`
3. Test write access: `touch ~/.cache/portfolio/test && rm ~/.cache/portfolio/test`

---

### Error: "max_cache_age_days must be >= 0"

**Problem**: Cache age is negative.

**Solution**: Use None (no expiration) or a non-negative integer:
```python
# ✅ No expiration
cache = FactorCache(cache_dir, max_cache_age_days=None)

# ✅ Expire after 7 days
cache = FactorCache(cache_dir, max_cache_age_days=7)
```

---

### Warning: "Cache write failed. Continuing without caching."

**Problem**: Failed to write cache (disk full, permissions, quota).

**Impact**: System continues but performance may degrade on subsequent runs.

**Troubleshooting**:
1. Check disk space: `df -h`
2. Check cache directory size: `du -sh ~/.cache/portfolio`
3. Clear old cache: `rm -rf ~/.cache/portfolio/*`
4. Check quota: `quota -s`

**Temporary Solution**:
```python
# Disable caching to avoid warnings
cache = FactorCache(cache_dir, enabled=False)
```

---

## Warnings and Their Meaning

### Warning: "top_k is very small (<10 assets)"

**Impact**: High concentration risk, under-diversification.

**Recommendation**: Use top_k >= 10 for better diversification.
```python
# ⚠️ Triggers warning
PreselectionConfig(top_k=5)

# ✅ Better diversification
PreselectionConfig(top_k=20)
```

**When it's OK**: Very high-conviction strategies, but be aware of concentration risk.

---

### Warning: "lookback is very short (<63 days)"

**Impact**: Noisy signals, high turnover, potential overreaction to short-term movements.

**Recommendation**: Use lookback >= 63 days (3 months) for more stable signals.
```python
# ⚠️ Triggers warning
PreselectionConfig(lookback=30)

# ✅ More stable
PreselectionConfig(lookback=126)  # 6 months
```

**When it's OK**: Short-term tactical strategies, but expect higher turnover.

---

### Warning: "buffer_rank very close to top_k (gap < 20%)"

**Impact**: Insufficient buffer for stability, may not effectively reduce turnover.

**Recommendation**: Set `buffer_rank` to at least `top_k + 20%`.
```python
# ⚠️ Triggers warning (gap = 5, 16%)
MembershipPolicy(buffer_rank=35, top_k=30)

# ✅ Adequate buffer (gap = 10, 33%)
MembershipPolicy(buffer_rank=40, top_k=30)
```

---

### Warning: "Caching disabled for large universe (>500 assets)"

**Impact**: Slower performance on repeated runs, higher CPU usage.

**Recommendation**: Enable caching for large universes.
```python
# ⚠️ No cache for 800 assets
cache = FactorCache(cache_dir, enabled=False)

# ✅ Enable caching
cache = FactorCache(cache_dir, enabled=True)
```

**Performance Impact**: Without caching, factor computation and eligibility checks are recomputed every run. For 800 assets with monthly rebalancing over 10 years, this can add minutes of computation time.

---

### Warning: "All factor scores are NaN"

**Impact**: No assets can be selected, returns empty list.

**Causes**:
1. Insufficient data across all assets
2. Data quality issues (all NaN returns)
3. Lookback period too long for available data

**Solutions**:
```python
# Check data availability
print(f"Data shape: {returns.shape}")
print(f"NaN percentage: {returns.isna().sum().sum() / returns.size * 100:.1f}%")

# Reduce requirements
config = PreselectionConfig(
    lookback=126,    # ✅ Reduced from 252
    min_periods=30   # ✅ Reduced from 60
)
```

---

## Performance Issues

### Slow preselection on large universes

**Problem**: Preselection takes too long with many assets.

**Solutions**:
1. **Enable caching**:
   ```python
   cache = FactorCache(Path(".cache/factors"), enabled=True)
   preselect = Preselection(config, cache=cache)
   ```

2. **Use faster methods**:
   - `MOMENTUM` or `LOW_VOL` are faster than `COMBINED`

3. **Reduce universe size**: Pre-filter assets before preselection

---

### High memory usage

**Problem**: System uses too much memory.

**Solutions**:
1. **Process in chunks**: If backtesting multiple periods, process incrementally

2. **Clear cache periodically**:
   ```python
   cache.clear()  # Remove all cached entries
   ```

3. **Reduce lookback window**: Shorter lookback = less data in memory

---

### Excessive turnover

**Problem**: Portfolio changes too frequently.

**Solutions**:
1. **Use membership policy**:
   ```python
   policy = MembershipPolicy(
       buffer_rank=50,           # Keep holdings within buffer
       min_holding_periods=3,    # Hold for at least 3 periods
       max_new_assets=5,         # Limit new positions
       max_removed_assets=5      # Limit exits
   )
   ```

2. **Increase lookback**: Longer lookback = more stable signals
   ```python
   PreselectionConfig(lookback=252)  # ✅ vs. lookback=63
   ```

3. **Adjust skip period**: Skip recent data to avoid chasing noise
   ```python
   PreselectionConfig(skip=21)  # Skip last month
   ```

---

## Getting Help

If you encounter an issue not covered in this guide:

1. **Check logs**: Look for detailed error messages and warnings
2. **Enable debug logging**:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```
3. **Validate inputs**: Use the validation methods explicitly
4. **Check GitHub issues**: [github.com/jc1122/portfolio_management/issues](https://github.com/jc1122/portfolio_management/issues)
5. **Review code examples**: See `examples/` directory for working code

---

## Best Practices Summary

1. **Always validate data before processing**:
   - Check shape, NaN percentage, date range
   - Verify data types (DataFrame, dates)

2. **Use reasonable parameter ranges**:
   - `top_k`: 20-50 assets
   - `lookback`: 126-252 days
   - `buffer_rank`: top_k + 20% or more
   - `min_holding_periods`: 2-4 rebalances

3. **Enable caching for large universes** (>100 assets)

4. **Monitor warnings**: They indicate suboptimal configurations

5. **Test with small datasets first** before scaling up

6. **Use membership policy** to control turnover

7. **Log everything** for debugging and auditability
