# Long-History Integration Tests - Troubleshooting Guide

## Overview

The long-history integration tests (`tests/integration/test_long_history_comprehensive.py`) validate all Sprint 2 features using 20 years of historical data (2005-2025). This guide helps diagnose and resolve test failures.

## Prerequisites

### Required Data Files

Tests require the following data files in `outputs/long_history_1000/`:

- `long_history_1000_prices_daily.csv` - Daily price data (~5000 days, 100+ assets)
- `long_history_1000_returns_daily.csv` - Daily return data
- `long_history_1000_selection.csv` - Asset selection metadata (optional)

**If missing:** Tests will skip with message "Long history data not available"

### Running Tests

```bash
# Run all long-history tests
pytest tests/integration/test_long_history_comprehensive.py -v

# Run specific test class
pytest tests/integration/test_long_history_comprehensive.py::TestEqualWeightLongHistory -v

# Run single test
pytest tests/integration/test_long_history_comprehensive.py::TestDeterminismAndBackwardCompatibility::test_determinism_multiple_runs -v

# Run with performance summary
pytest tests/integration/test_long_history_comprehensive.py::TestPerformanceMetrics -v -s
```

## Common Issues

### 1. Test Timeouts

**Symptom:** Test exceeds 20-minute execution limit

**Causes:**

- Large universe size (>500 assets)
- Complex optimization strategies (mean-variance, risk parity)
- Many rebalance events (monthly over 20 years)

**Solutions:**

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

### 2. Optimization Failures

**Symptom:** `PortfolioConstructionError` or solver failures

**Causes:**

- Insufficient data for optimization (covariance matrix singular)
- Too few assets selected
- Numerical instability in optimization

**Solutions:**

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

### 3. PIT Eligibility Issues

**Symptom:** Very few assets selected in early periods

**Cause:** Point-in-time filtering correctly excludes assets with insufficient history

**Expected Behavior:**

- Early rebalances have fewer eligible assets
- Asset count grows over time as more assets meet min_history_days
- This is correct behavior to prevent lookahead bias

**Verify:**

```python
# Check first vs last event asset counts
first_event = events[0]
last_event = events[-1]

print(f"First event assets: {len(first_event.new_weights)}")
print(f"Last event assets: {len(last_event.new_weights)}")
# First should be <= Last
```

### 4. Determinism Failures

**Symptom:** Multiple runs produce different results

**Causes:**

- Random number generator not seeded (should not happen in production code)
- Caching issues
- Floating point precision differences
- Non-deterministic dictionary/set iteration (Python 3.7+ guarantees order)

**Solutions:**

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

### 5. Cache Validation Failures

**Symptom:** Cached vs uncached results don't match

**Causes:**

- Cache key collision
- Data mutation between runs
- Cache invalidation not working correctly

**Debugging:**

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

### 6. Membership Policy Violations

**Symptom:** AssertionError about too many assets added/removed

**Cause:** Policy constraints too strict for the data

**Solutions:**

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

### 7. Memory Issues

**Symptom:** Out of memory errors

**Causes:**

- Loading full 20-year dataset for all assets
- Creating too many intermediate DataFrames
- Cache growing too large

**Solutions:**

```bash
# Run with memory profiling
python -m memory_profiler tests/integration/test_long_history_comprehensive.py

# Reduce data size
# - Use subset of date range
# - Use fewer assets
# - Clear intermediate results
```

## Expected Test Results

### Execution Times (Approximate)

Test execution times on a modern machine:

- **Equal Weight tests:** 2-5 minutes each
- **Mean-Variance tests:** 5-10 minutes each
- **Risk Parity tests:** 5-10 minutes each
- **Determinism tests:** 5-15 minutes (runs config 3x)
- **Full suite:** 60-120 minutes

**Note:** Times scale with:

- Number of assets
- Rebalance frequency (monthly vs quarterly)
- Optimization complexity
- Cache state (first run slower)

### Cache Hit Rates

Expected cache performance:

- **First run:** 0% hits (cache empty)
- **Second run (same config):** 80-100% hits
- **Different config:** Varies based on overlap

Good hit rate: >50% on repeated runs

### Portfolio Characteristics

**Equal Weight:**

- All assets have equal weight (1/N)
- Simple, no optimization
- Fast execution

**Mean-Variance:**

- Concentrated portfolios (10-30 assets actively weighted)
- Some assets may have 0 weight
- Optimization-driven allocation

**Risk Parity:**

- Balanced risk contribution
- No single asset >30% weight typically
- More computational cost

## Debugging Workflow

### 1. Isolate the Issue

```python
# Run single test
pytest tests/integration/test_long_history_comprehensive.py::TestClass::test_name -v -s

# Add verbose output
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 2. Reduce Data Size

```python
# Test with smaller date range
start_date = datetime.date(2020, 1, 1)
end_date = datetime.date(2022, 12, 31)

# Or subset of assets
prices_subset = prices[prices.columns[:100]]  # First 100 assets only
```

### 3. Simplify Configuration

```python
# Minimal config
config = BacktestConfig(
    start_date=start_date,
    end_date=end_date,
    initial_capital=Decimal(100000),
    rebalance_frequency=RebalanceFrequency.QUARTERLY,
    # No PIT eligibility
    # No other features
)

# Simplest strategy
strategy = EqualWeightStrategy()

# No preselection or membership
engine = BacktestEngine(
    config=config,
    strategy=strategy,
    prices=prices,
    returns=returns,
)
```

### 4. Check Data Quality

```python
# Verify data
print(f"Price data shape: {prices.shape}")
print(f"Date range: {prices.index.min()} to {prices.index.max()}")
print(f"Missing values: {prices.isnull().sum().sum()}")
print(f"Inf values: {np.isinf(prices).sum().sum()}")

# Check returns
print(f"Return data shape: {returns.shape}")
print(f"Return range: [{returns.min().min():.4f}, {returns.max().max():.4f}]")
```

### 5. Examine Events

```python
# Inspect rebalance events
for i, event in enumerate(events[:5]):  # First 5 events
    print(f"\nEvent {i} - {event.date}")
    print(f"  Assets: {len(event.new_weights)}")
    print(f"  Total weight: {sum(event.new_weights.values()):.4f}")
    if i > 0:
        prev_assets = set(events[i-1].new_weights.keys())
        curr_assets = set(event.new_weights.keys())
        print(f"  Added: {len(curr_assets - prev_assets)}")
        print(f"  Removed: {len(prev_assets - curr_assets)}")
```

## Test-Specific Notes

### TestDeterminismAndBackwardCompatibility

**Purpose:** Ensures reproducibility and backward compatibility

**Key Validations:**

- Three runs produce identical numerical results
- Equity curves match exactly
- Metrics match to full precision

**If failing:** Check for non-deterministic code (random generators, dict/set iteration in Python \<3.7)

### TestMarketRegimes

**Purpose:** Validates behavior during specific market conditions

**Expected Behaviors:**

- 2008 crisis: Negative returns, large drawdowns
- 2020 COVID: Sharp drawdown followed by recovery
- 2021-2022: Mixed performance (bull then correction)

**If failing:** Verify date ranges align with actual market events in the data

### TestValidationChecks

**Purpose:** Verifies correctness of feature implementations

**Critical Checks:**

- PIT eligibility prevents lookahead
- Preselection top_k honored
- Membership constraints respected
- Cache produces identical results

**If failing:** Likely a bug in the feature implementation, not test code

## Performance Optimization

### Faster Test Development

```python
# Use smaller date range during development
start_date = datetime.date(2015, 1, 1)  # 10 years instead of 20
end_date = datetime.date(2024, 12, 31)

# Use quarterly rebalancing
rebalance_frequency = RebalanceFrequency.QUARTERLY

# Use equal weight (fastest)
strategy = EqualWeightStrategy()

# Reduce top_k
top_k = 20  # Instead of 30-50
```

### Caching for Repeated Runs

Tests automatically use temporary cache directories. For development:

```python
# Persistent cache across test runs
cache_dir = Path(".cache/test_cache")
cache_dir.mkdir(exist_ok=True)
factor_cache = FactorCache(cache_dir, enabled=True)
```

## Getting Help

If tests fail and you can't diagnose the issue:

1. Check error message and stack trace carefully
1. Review this troubleshooting guide
1. Try simpler configuration (see "Simplify Configuration" above)
1. Check data quality (see "Check Data Quality" above)
1. Review test expectations (see "Expected Test Results" above)
1. Check GitHub Issues for similar problems
1. Create new issue with:
   - Full error message and stack trace
   - Test configuration used
   - Data characteristics (shape, date range)
   - Steps to reproduce

## Reference

### Key Files

- Tests: `tests/integration/test_long_history_comprehensive.py`
- Data: `outputs/long_history_1000/`
- Fixtures: `tests/integration/conftest.py`

### Related Documentation

- `docs/backtesting.md` - Backtest framework overview
- `docs/preselection.md` - Preselection feature details
- `docs/membership_policy.md` - Membership policy details
- `memory-bank/activeContext.md` - Current project state
