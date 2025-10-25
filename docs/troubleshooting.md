# Troubleshooting Guide

This comprehensive guide helps you diagnose and fix common issues when using the portfolio management system.

## Table of Contents

1. [Data Issues](#data-issues)
2. [Preselection Errors](#preselection-errors)
3. [Membership Policy Errors](#membership-policy-errors)
4. [Eligibility Errors](#eligibility-errors)
5. [Cache Issues](#cache-issues)
6. [Performance Issues](#performance-issues)
7. [Backtesting Issues](#backtesting-issues)
8. [Configuration Errors](#configuration-errors)
9. [Long-History Test Issues](#long-history-test-issues)
10. [Warnings and Their Meaning](#warnings-and-their-meaning)
11. [Quick Reference](#quick-reference)
12. [Getting Help](#getting-help)

---

## Data Issues

### InsufficientHistoryError

**Symptom**: The backtest fails with an `InsufficientHistoryError`.

**Solution**: This error means that at a given rebalancing date, no assets in the universe met the minimum history requirements to be included in the portfolio.

- **Check `min_history_days`**: Your `use_pit_eligibility` setting might be too strict for your data. Try reducing `min_history_days`.
- **Check Your Data**: Your price/return data might have large gaps or start later than you think. Inspect the CSV files.
- **Broaden Your Universe**: The assets in your chosen universe might all be relatively new. Try using a universe with assets that have a longer history.

### Missing Assets in Data Files

**Symptom**: The backtest fails with `ValueError: Missing assets in prices file...`

**Solution**: The asset list in your universe configuration does not match the columns in your `prices.csv` or `returns.csv` files.

- **Check Universe vs. Data**: Make sure that every asset listed in your universe's `assets` list exists as a column header in your data files.
- **Regenerate Data**: If you've recently changed your universe, you may need to regenerate your processed data files using `prepare_tradeable_data.py` to ensure they are consistent.

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

## Cache Issues

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

### Cache Not Invalidating (Stale Results)

**Symptom**: You've updated your data or configuration, but the backtest results don't change. The cache statistics show all hits.

**Solution**: This is rare, as the hashing mechanism is robust. However, if you suspect the cache is stale, you can force a refresh.

- **Clear the Cache**: The simplest solution is to delete the cache directory (e.g., `rm -rf .cache/`). The cache will be rebuilt on the next run.
- **Use a New Cache Directory**: Use the `--cache-dir .cache/new_experiment` argument to force the backtest to use a new, empty cache.

---

### Cache Corruption

**Symptom**: The backtest fails with a `pickle.UnpicklingError` or a similar error related to reading a file from the cache directory.

**Solution**: This can happen if a backtest is terminated abruptly while writing to the cache.

- **Clear the Cache**: Delete the cache directory. This will remove the corrupted file and allow the cache to be rebuilt cleanly on the next run.

---

## Performance Issues

### Slow Backtests

If your backtests are running slower than expected, here are the most common causes and solutions.

#### 1. Caching is Disabled

**Symptom**: Running the same backtest twice takes the same amount of time. Subsequent runs are not faster.

**Solution**: Ensure that caching is enabled.

- **CLI**: Add the `--enable-cache` flag to your `run_backtest.py` command.
- **Programmatic**: Make sure you are creating a `FactorCache` object with `enabled=True` and passing it to the `BacktestEngine`.

#### 2. Large Universe Without Filtering

**Symptom**: The backtest is slow, especially during the initial data loading and factor calculation phases.

**Solution**: Pre-filter your universe if possible.

- If your strategy only applies to a subset of assets (e.g., equities only, US stocks only), create a smaller universe using `manage_universes.py`.
- Even if the preselection step will reduce the number of assets, the initial factor calculation is still performed on the entire universe. A smaller starting universe will always be faster.

#### 3. High Rebalancing Frequency

**Symptom**: The backtest is very slow, and the console output shows it processing day by day.

**Solution**: Use a lower rebalancing frequency if appropriate for your strategy.

- Changing from `--rebalance-frequency daily` to `monthly` or `quarterly` will dramatically reduce the number of calculations and speed up the backtest.

---

### Slow Preselection on Large Universes

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

### High Memory Usage

**Problem**: System uses too much memory.

**Solutions**:
1. **Process in chunks**: If backtesting multiple periods, process incrementally

2. **Clear cache periodically**:
   ```python
   cache.clear()  # Remove all cached entries
   ```

3. **Reduce lookback window**: Shorter lookback = less data in memory

---

### Excessive Turnover

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

## Backtesting Issues

### Test Timeouts

**Symptom**: Test exceeds 20-minute execution limit

**Causes**:

- Large universe size (>500 assets)
- Complex optimization strategies (mean-variance, risk parity)
- Many rebalance events (monthly over 20 years)

**Solutions**:

```python
# Reduce test period
config = BacktestConfig(
    start_date=datetime.date(2010, 1, 1),  # Instead of 2006
    end_date=datetime.date(2020, 12, 31),   # Instead of 2024
    ...
)

# Use quarterly instead of monthly rebalancing
rebalance_frequency=RebalanceFrequency.QUARTERLY  # Instead of MONTHLY

# Reduce top_k for preselection
preselection_config = PreselectionConfig(
    top_k=20,  # Instead of 30+
    ...
)
```

---

### Optimization Failures

**Symptom**: `PortfolioConstructionError` or solver failures

**Causes**:

- Insufficient data for optimization (covariance matrix singular)
- Too few assets selected
- Numerical instability in optimization

**Solutions**:

```python
# Increase minimum data requirements
config = BacktestConfig(
    min_history_days=365,  # More history
    min_price_rows=300,    # More data points
    ...
)

# Use more assets for optimization
preselection_config = PreselectionConfig(
    top_k=40,  # More assets = more stable covariance
    ...
)

# Fall back to simpler strategy
strategy = EqualWeightStrategy()  # Instead of MeanVarianceStrategy
```

---

## Configuration Errors

### Universe Not Found

**Symptom**: The CLI fails with `ValueError: Universe 'my_universe' not found.`

**Solution**: The `--universe-name` you provided doesn't exist in the specified `--universe-file`.

- **Check Spelling**: Double-check the spelling of the universe name.
- **Check File**: Make sure you are pointing to the correct YAML file and that the universe is defined within it.

---

### Invalid Strategy Name

**Symptom**: The CLI fails with an error related to an unknown strategy.

**Solution**: You have provided a strategy name that is not recognized.

- **Check `strategy` argument**: The first argument to `run_backtest.py` must be one of the implemented strategies: `equal_weight`, `risk_parity`, or `mean_variance`.

---

## Long-History Test Issues

### PIT Eligibility Issues

**Symptom**: Very few assets selected in early periods

**Cause**: Point-in-time filtering correctly excludes assets with insufficient history

**Expected Behavior**:

- Early rebalances have fewer eligible assets
- Asset count grows over time as more assets meet min_history_days
- This is correct behavior to prevent lookahead bias

**Verify**:

```python
# Check first vs last event asset counts
first_event = events[0]
last_event = events[-1]

print(f"First event assets: {len(first_event.new_weights)}")
print(f"Last event assets: {len(last_event.new_weights)}")
# First should be <= Last
```

---

### Determinism Failures

**Symptom**: Multiple runs produce different results

**Causes**:

- Random number generator not seeded (should not happen in production code)
- Caching issues
- Floating point precision differences
- Non-deterministic dictionary/set iteration (Python 3.7+ guarantees order)

**Solutions**:

```python
# Verify identical inputs
assert prices1.equals(prices2), "Price data should be identical"
assert returns1.equals(returns2), "Return data should be identical"

# Check for random state
# Production code should NOT use random generators
# If using numpy: np.random.seed(42)

# Compare with tolerance for floating point
np.testing.assert_allclose(
    result1.total_return,
    result2.total_return,
    rtol=1e-10,  # Relative tolerance
)
```

---

### Cache Validation Failures

**Symptom**: Cached vs uncached results don't match

**Causes**:

- Cache key collision
- Data mutation between runs
- Cache invalidation not working correctly

**Debugging**:

```python
# Clear cache between runs
factor_cache = FactorCache(cache_dir, enabled=True)
factor_cache.clear()  # Explicit clear

# Verify cache stats
stats = factor_cache.get_stats()
print(f"Hits: {stats['hits']}")
print(f"Misses: {stats['misses']}")
print(f"Puts: {stats['puts']}")

# Check cache keys
# Keys should be deterministic based on inputs
```

---

### Membership Policy Violations

**Symptom**: AssertionError about too many assets added/removed

**Cause**: Policy constraints too strict for the data

**Solutions**:

```python
# Relax constraints
membership_policy = MembershipPolicy(
    max_new_assets=15,       # Increased from 10
    max_removed_assets=15,   # Increased from 10
    max_turnover=0.50,       # Increased from 0.30
    ...
)

# Or disable for debugging
membership_policy = MembershipPolicy(enabled=False)
```

---

### Memory Issues

**Symptom**: Out of memory errors

**Causes**:

- Loading full 20-year dataset for all assets
- Creating too many intermediate DataFrames
- Cache growing too large

**Solutions**:

```bash
# Run with memory profiling
python -m memory_profiler tests/integration/test_long_history_comprehensive.py

# Reduce data size
# - Use subset of date range
# - Use fewer assets
# - Clear intermediate results
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

## Quick Reference

### Common Error Quick Fixes

| Error | Quick Fix |
|-------|-----------|
| `top_k must be >= 0` | Use positive integer or None |
| `skip must be < lookback` | Reduce skip or increase lookback |
| `Combined weights must sum to 1.0` | Adjust momentum_weight and low_vol_weight |
| `InsufficientHistoryError` | Reduce min_history_days or provide more data |
| `Missing assets in prices file` | Regenerate data or update universe config |
| `cache_dir is not writable` | Use user directory (e.g., ~/.cache) |
| `Universe not found` | Check spelling and YAML file |
| Slow backtest | Enable caching, reduce universe, or lower rebalance frequency |

---

### Recommended Parameter Ranges

| Parameter | Recommended Range | Notes |
|-----------|-------------------|-------|
| `top_k` | 20-50 assets | Balance diversification vs. focus |
| `lookback` | 126-252 days | 6 months to 1 year |
| `min_periods` | 20-50% of lookback | Minimum data for calculation |
| `buffer_rank` | top_k + 20% or more | Stability buffer |
| `min_holding_periods` | 2-4 rebalances | Reduce turnover |
| `max_turnover` | 0.20-0.40 | 20-40% per rebalance |
| `min_history_days` | 252-365 days | 1 year recommended |

---

### Debugging Workflow

1. **Isolate the Issue**:
   ```python
   # Run single test with verbose output
   pytest tests/integration/test_name.py -v -s
   
   # Add debug logging
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **Reduce Data Size**:
   ```python
   # Test with smaller date range
   start_date = datetime.date(2020, 1, 1)
   end_date = datetime.date(2022, 12, 31)
   
   # Or subset of assets
   prices_subset = prices[prices.columns[:100]]  # First 100 assets only
   ```

3. **Simplify Configuration**:
   ```python
   # Minimal config
   config = BacktestConfig(
       start_date=start_date,
       end_date=end_date,
       initial_capital=Decimal(100000),
       rebalance_frequency=RebalanceFrequency.QUARTERLY,
   )
   
   # Simplest strategy
   strategy = EqualWeightStrategy()
   ```

4. **Check Data Quality**:
   ```python
   # Verify data
   print(f"Price data shape: {prices.shape}")
   print(f"Date range: {prices.index.min()} to {prices.index.max()}")
   print(f"Missing values: {prices.isnull().sum().sum()}")
   print(f"Inf values: {np.isinf(prices).sum().sum()}")
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
6. **Check documentation**: Review relevant docs in `docs/` directory
7. **Run with minimal config**: Simplify to isolate the problem
8. **Test with small dataset**: Verify behavior on small, controlled data

### Creating a Good Issue Report

When reporting an issue, include:

1. **Full error message and stack trace**
2. **Minimal reproduction case**:
   ```python
   # Simplest code that reproduces the issue
   ```
3. **Environment details**:
   - Python version
   - Package versions (pip freeze)
   - Operating system
4. **Data characteristics**:
   - Shape (rows, columns)
   - Date range
   - Sample of data (if not sensitive)
5. **Configuration used**:
   - BacktestConfig parameters
   - Strategy settings
   - Universe configuration
6. **Expected vs. actual behavior**

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

8. **Check data quality regularly**:
   - Monitor for gaps, outliers, anomalies
   - Validate against expected ranges
   - Review diagnostics output

9. **Keep backups of configuration**:
   - Version control for universe configs
   - Document parameter choices
   - Track changes over time

10. **Profile before optimizing**:
    - Measure performance first
    - Identify actual bottlenecks
    - Test improvements systematically

---

## Related Documentation

- [Backtesting Guide](backtesting.md) - Backtest framework overview
- [Preselection Guide](preselection.md) - Asset preselection feature
- [Membership Policy](membership_policy.md) - Turnover management
- [Testing Guide](testing/README.md) - Test organization and strategy
- [Performance Guide](performance/README.md) - Optimization techniques
- [Caching Reliability](caching_reliability.md) - Cache behavior and best practices
- [Configuration Best Practices](configuration_best_practices.md) - Config guidelines
- [Error Reference](error_reference.md) - Complete error catalog
