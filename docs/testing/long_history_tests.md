# Long-History Integration Tests - User Guide

## Overview

The long-history integration tests provide comprehensive validation of the portfolio management system using 20 years of historical data (2005-2025). These tests ensure all Sprint 2 features work correctly together across different market conditions.

## Purpose

### What These Tests Validate

1. **Feature Integration** - All features work together without conflicts
1. **Determinism** - Results are reproducible across multiple runs
1. **Backward Compatibility** - New features don't break existing functionality
1. **Market Regime Handling** - System behaves correctly in crisis and normal periods
1. **Performance** - Execution completes in reasonable time
1. **Correctness** - Constraints and policies are honored

### Why 20 Years?

- **Market Regimes:** Covers multiple market cycles (bull, bear, crisis)
- **Edge Cases:** Long periods expose rare conditions (delistings, data gaps)
- **Realistic Validation:** Production use cases span decades
- **Feature Interactions:** Complex interactions emerge over time

## Test Structure

### Test Classes

```
TestEqualWeightLongHistory
├── test_equal_weight_momentum_preselection_20_years
├── test_equal_weight_membership_policy_20_years
└── test_equal_weight_all_features_20_years

TestMeanVarianceLongHistory
├── test_mean_variance_low_vol_preselection_20_years
└── test_mean_variance_membership_20_years

TestRiskParityLongHistory
├── test_risk_parity_combined_factors_20_years
└── test_risk_parity_all_features_20_years

TestDeterminismAndBackwardCompatibility
├── test_determinism_multiple_runs
├── test_backward_compatibility_features_disabled
└── test_cached_vs_uncached_equivalence

TestMarketRegimes
├── test_financial_crisis_2007_2008
├── test_covid_crash_2020
└── test_bull_market_2021_2022

TestValidationChecks
├── test_pit_eligibility_no_lookahead
├── test_preselection_top_k_honored
├── test_membership_policy_constraints
└── test_cache_hit_rates

TestPerformanceMetrics
└── test_execution_time_tracking
```

## Feature Combinations Tested

### 1. Strategy Types

| Strategy | Description | Characteristics |
|----------|-------------|-----------------|
| Equal Weight | All assets weighted equally (1/N) | Simple, fast, baseline |
| Mean-Variance | Optimizes return/risk ratio | Concentrated, optimization |
| Risk Parity | Equal risk contribution | Balanced, moderate complexity |

### 2. Preselection Methods

| Method | Description | Use Case |
|--------|-------------|----------|
| MOMENTUM | Ranks by trailing returns | Trend following |
| LOW_VOL | Ranks by inverse volatility | Risk reduction |
| COMBINED | Weighted combination | Balanced approach |

**Parameters:**

- `top_k`: Number of assets to select (20-50 typical)
- `lookback`: Historical period for calculation (252 days typical)
- `skip`: Recent period to skip for momentum (21 days typical)

### 3. Membership Policy

Controls portfolio turnover to reduce trading costs:

```python
MembershipPolicy(
    buffer_rank=35,           # Rank buffer for entry/exit
    min_holding_periods=2,    # Minimum quarters to hold
    max_turnover=0.30,       # Max 30% turnover per rebalance
    max_new_assets=10,       # Max new assets per rebalance
    max_removed_assets=10,   # Max removals per rebalance
    enabled=True,
)
```

### 4. PIT Eligibility

Point-in-time filtering to prevent lookahead bias:

```python
BacktestConfig(
    use_pit_eligibility=True,
    min_history_days=252,    # Minimum historical data
    min_price_rows=200,      # Minimum data points
)
```

### 5. Caching

Caches factor calculations for faster repeated runs:

```python
factor_cache = FactorCache(cache_dir, enabled=True)
preselection = Preselection(config, cache=factor_cache)
```

## Expected Behaviors

### Equal Weight Strategy

**Characteristics:**

- All selected assets have weight 1/N
- No optimization required
- Fast execution (2-5 minutes)
- Deterministic results

**With Preselection:**

- Portfolio size = `top_k` assets
- Assets change at each rebalance based on factor ranks

**With Membership Policy:**

- Gradual portfolio evolution
- Reduced turnover vs baseline
- Smoother transitions

### Mean-Variance Strategy

**Characteristics:**

- Optimizes Sharpe ratio (return/risk)
- Concentrated portfolios (10-30 active positions)
- Some assets may have zero weight
- Slower execution (5-10 minutes)

**Potential Issues:**

- May fail if too few assets (min ~15 recommended)
- Sensitive to estimation error
- Can produce extreme weights (constraints help)

**With Preselection:**

- Preselection filters to top_k
- Optimization selects subset of filtered assets
- Typical active positions: 50-70% of top_k

### Risk Parity Strategy

**Characteristics:**

- Equal risk contribution from each asset
- Balanced portfolios
- No single asset >30% typically
- Moderate execution time (5-10 minutes)

**With Preselection:**

- Balances risk across selected assets
- More stable than mean-variance
- Diversification benefits

## Test Scenarios

### Scenario 1: 20-Year Full Period (2005-2025)

**Purpose:** Validate long-term stability

**Expected:**

- Multiple market regimes captured
- Hundreds of rebalancing events
- All features tested together
- Realistic production scenario

**Date Range:** 2006-01-01 to 2024-12-31

### Scenario 2: Financial Crisis (2007-2008)

**Purpose:** Stress test during market crash

**Expected:**

- Negative returns likely
- Large drawdowns (>30% possible)
- Low volatility strategies should help
- System remains stable

**Date Range:** 2007-01-01 to 2009-12-31

### Scenario 3: COVID Crash (2020)

**Purpose:** Validate rapid shock response

**Expected:**

- Sharp March 2020 drawdown
- Fast recovery through 2021
- Monthly rebalancing captures volatility
- System adapts quickly

**Date Range:** 2019-01-01 to 2021-12-31

### Scenario 4: Bull Market (2021-2022)

**Purpose:** Test in positive market

**Expected:**

- Positive returns initially
- 2022 correction captured
- Momentum strategies should perform
- Gradual adjustments

**Date Range:** 2021-01-01 to 2023-12-31

## Validation Criteria

### 1. Determinism

**Test:** Run same configuration 3 times

**Success Criteria:**

```python
assert total_return_run1 == total_return_run2 == total_return_run3
assert sharpe_ratio_run1 == sharpe_ratio_run2 == sharpe_ratio_run3
assert equity_curve_run1.equals(equity_curve_run2)
```

**Why Important:** Reproducibility is critical for production use

### 2. Backward Compatibility

**Test:** Compare results with/without features

**Success Criteria:**

```python
# When features disabled, should match baseline
assert equity_curve_disabled.equals(equity_curve_baseline)
```

**Why Important:** Ensures new features are truly optional

### 3. Cache Equivalence

**Test:** Compare cached vs uncached runs

**Success Criteria:**

```python
assert equity_curve_cached.equals(equity_curve_uncached)
assert cache_stats['hits'] > 0  # Cache was used
```

**Why Important:** Caching must not change results

### 4. PIT Eligibility

**Test:** Verify no lookahead bias

**Success Criteria:**

```python
# Early rebalances have fewer eligible assets
assert len(first_event.new_weights) <= len(last_event.new_weights)
```

**Why Important:** Prevents unrealistic backtest results

### 5. Constraint Adherence

**Test:** Verify all constraints honored

**Success Criteria:**

```python
# Preselection top_k
assert len(event.new_weights) <= top_k

# Membership policy
assert len(added_assets) <= max_new_assets
assert len(removed_assets) <= max_removed_assets
```

**Why Important:** Constraints must be enforced

## Performance Benchmarks

### Execution Times

**Target:** Each test completes in \<20 minutes

**Actual (approximate):**

- Equal Weight: 2-5 minutes
- Mean-Variance: 5-10 minutes
- Risk Parity: 5-10 minutes
- Determinism (3x runs): 5-15 minutes

**Factors Affecting Speed:**

- Number of assets
- Rebalance frequency (monthly slower than quarterly)
- Strategy complexity
- Cache state (first run slower)

### Cache Performance

**First Run:**

- Hits: 0%
- All computations cached

**Second Run (identical config):**

- Hits: 80-100%
- Significant speedup

**Memory Usage:**

- Cache size: ~10-100 MB typical
- Peak memory: ~500 MB - 2 GB

## Example Configurations

### Conservative Long-Term

```python
config = BacktestConfig(
    start_date=datetime.date(2005, 1, 1),
    end_date=datetime.date(2024, 12, 31),
    initial_capital=Decimal(100000),
    rebalance_frequency=RebalanceFrequency.QUARTERLY,
    use_pit_eligibility=True,
    min_history_days=252,
)

preselection_config = PreselectionConfig(
    method=PreselectionMethod.LOW_VOL,
    top_k=30,
    lookback=252,
)

membership_policy = MembershipPolicy(
    buffer_rank=35,
    min_holding_periods=3,
    max_turnover=0.25,
    enabled=True,
)

strategy = RiskParityStrategy()
```

### Aggressive Momentum

```python
config = BacktestConfig(
    start_date=datetime.date(2010, 1, 1),
    end_date=datetime.date(2024, 12, 31),
    initial_capital=Decimal(100000),
    rebalance_frequency=RebalanceFrequency.MONTHLY,
)

preselection_config = PreselectionConfig(
    method=PreselectionMethod.MOMENTUM,
    top_k=20,
    lookback=126,  # 6 months
    skip=21,
)

strategy = MeanVarianceStrategy()
```

### Balanced Approach

```python
config = BacktestConfig(
    start_date=datetime.date(2006, 1, 1),
    end_date=datetime.date(2024, 12, 31),
    initial_capital=Decimal(100000),
    rebalance_frequency=RebalanceFrequency.QUARTERLY,
    use_pit_eligibility=True,
    min_history_days=252,
)

preselection_config = PreselectionConfig(
    method=PreselectionMethod.COMBINED,
    top_k=30,
    lookback=252,
    skip=21,
    momentum_weight=0.5,
    low_vol_weight=0.5,
)

membership_policy = MembershipPolicy(
    buffer_rank=35,
    min_holding_periods=2,
    max_turnover=0.30,
    enabled=True,
)

strategy = EqualWeightStrategy()
```

## Running the Tests

### Full Suite

```bash
# Run all long-history tests (60-120 minutes)
pytest tests/integration/test_long_history_comprehensive.py -v

# With performance output
pytest tests/integration/test_long_history_comprehensive.py::TestPerformanceMetrics -v -s
```

### Specific Test Classes

```bash
# Equal weight tests only
pytest tests/integration/test_long_history_comprehensive.py::TestEqualWeightLongHistory -v

# Determinism tests
pytest tests/integration/test_long_history_comprehensive.py::TestDeterminismAndBackwardCompatibility -v

# Market regime tests
pytest tests/integration/test_long_history_comprehensive.py::TestMarketRegimes -v
```

### Development/Debugging

```bash
# Single test with output
pytest tests/integration/test_long_history_comprehensive.py::TestEqualWeightLongHistory::test_equal_weight_momentum_preselection_20_years -v -s

# Skip slow tests during development
pytest tests/integration/ -v -m "not slow"

# Only long-history tests
pytest -v -m "integration and slow"
```

## Interpreting Results

### Success

All tests should pass with output like:

```
test_equal_weight_momentum_preselection_20_years PASSED [  10%]
test_determinism_multiple_runs PASSED                 [  50%]
test_cache_hit_rates PASSED                          [  90%]

=== Performance Summary ===
Equal Weight + Momentum: 245.32s
Risk Parity + Low Vol: 387.91s

========================= 15 passed in 1832.45s =========================
```

### Expected Metrics

**Total Return:** Varies widely based on period and strategy

- 2005-2025: Positive expected (despite crises)
- Crisis periods: Negative typical
- Bull markets: Strongly positive

**Sharpe Ratio:**

- > 1.0: Good risk-adjusted return
- 0.5-1.0: Acceptable
- \<0.5: Poor

**Max Drawdown:**

- \<20%: Excellent
- 20-40%: Normal for equity strategies
- > 40%: High risk (expected during crises)

## Next Steps

After running tests:

1. **Review Results:** Check all tests passed
1. **Examine Performance:** Verify execution times acceptable
1. **Check Edge Cases:** Look for warnings or edge case handling
1. **Document Findings:** Record any new edge cases discovered
1. **Update Tests:** Add new test cases for new features

## Troubleshooting Long-History Tests

For detailed troubleshooting of long-history test failures, see the [Troubleshooting Guide](../troubleshooting.md#long-history-test-issues) which includes:

- Test timeout solutions
- Optimization failure fixes
- PIT eligibility issues
- Determinism failures
- Cache validation problems
- Membership policy violations
- Memory issues

## Related Documentation

- [Troubleshooting Guide](../troubleshooting.md) - Comprehensive troubleshooting
- [Testing Overview](overview.md) - Test organization and structure
- [Test Strategy](test_strategy.md) - Testing best practices
- [Backtesting Guide](../backtesting.md) - Backtest framework details
- [Preselection Guide](../preselection.md) - Preselection feature
- [Membership Policy](../membership_policy.md) - Turnover management
- [Caching Reliability](../caching_reliability.md) - Performance optimization

## Maintenance

### When to Update Tests

- New features added
- New market data available (extend to 2026+)
- Performance requirements change
- New edge cases discovered

### Test Data Refresh

Long-history data should be refreshed:

- Annually (add new year of data)
- When new assets added to universe
- If data quality issues found

### Continuous Integration

Tests marked as `@pytest.mark.slow` should run:

- In nightly CI builds (not on every commit)
- Before releases
- When backtest code changes
- When data updated
