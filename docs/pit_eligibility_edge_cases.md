# Point-in-Time (PIT) Eligibility Edge Cases

## Overview

This document describes the edge cases tested for PIT eligibility computation and known limitations of the current implementation.

## Test Coverage

The comprehensive edge case tests are located in `tests/integration/test_pit_edge_cases.py` and cover:

### 1. Sparse Data Handling

**Test Cases:**

- Large gaps in price history (30+ day gaps)
- Irregular trading patterns (low-volume assets with ~25% data availability)
- Sparse data with long calendar period but few rows
- Assets with data only at backtest start
- Assets with data only at backtest end
- Assets appearing mid-backtest

**Validation:**

- ✅ System handles gaps gracefully without crashes
- ✅ Both `min_history_days` and `min_price_rows` are enforced correctly
- ✅ Sparse assets can be eligible with appropriate thresholds
- ✅ Assets accumulate history over time regardless of gaps

**Key Finding:**
The PIT eligibility implementation considers **all historical data** up to the check date, not just recent contiguous data. This means:

- An asset with gaps is still eligible if it has sufficient total rows and calendar days since first observation
- Example: 100 rows from period 1 (days 50-150) + 150 rows from period 2 (days 300-450) = 250 rows eligible at day 500

### 2. Delisting Scenarios

**Test Cases:**

- Abrupt delisting (last price then no data)
- Gradual delisting (sparse data before stopping)
- Temporary delisting (data resumes after gap)
- Relisting after extended absence
- Delisting detection accuracy validation

**Validation:**

- ✅ Abrupt delistings detected with >95% accuracy
- ✅ Gradual delistings detected correctly
- ✅ Temporary gaps (where data resumes) are not flagged as permanent delistings
- ✅ Relisted assets become eligible again after resumption

**Key Finding:**
The `detect_delistings()` function uses a lookforward window (default 30 days) to distinguish between:

- **Permanent delistings**: No data in lookforward window → flagged as delisted
- **Temporary gaps**: Data resumes within lookforward → not flagged

**Accuracy:**

- Tested with diverse delisting patterns
- > 95% accuracy in detecting true permanent delistings
- No false positives for assets that resume trading

### 3. Universe Changes Mid-Backtest

**Test Cases:**

- Assets added during backtest period (IPOs, new listings)
- Assets removed during backtest period (delistings, mergers)
- Multiple universe changes in sequence
- Assets with intermittent presence (multiple entry/exit cycles)

**Validation:**

- ✅ Assets become eligible once they meet history requirements
- ✅ Late-starting assets correctly excluded until sufficient history
- ✅ Removed assets retain eligibility based on historical data
- ✅ Multiple entry/exit cycles handled correctly (cumulative history)

**Key Finding:**
Eligibility is based on cumulative history from **first observation to check date**, not just most recent continuous period. This is appropriate for ensuring sufficient data for statistical analysis.

### 4. History Requirements at Boundaries

**Test Cases:**

- Exactly meets `min_history_days` (boundary case)
- Just misses `min_price_rows` by 1
- Exactly meets `min_price_rows` (boundary case)
- Just exceeds minimum requirements

**Validation:**

- ✅ Exact boundary conditions (252 days, 252 rows) handled correctly
- ✅ Off-by-one cases properly rejected or accepted
- ✅ Both criteria enforced independently (AND logic)
- ✅ Sparse data can meet day requirement but fail row requirement

**Key Finding:**
The implementation uses strict `>=` comparison:

- `days_since_first >= min_history_days` AND `rows_count >= min_price_rows`
- Assets with exactly 252 rows and 252 days are eligible
- Assets with 251 rows or 251 days are not eligible (with default thresholds)

### 5. Date Boundary Cases

**Test Cases:**

- First rebalance date (minimal history available)
- Last rebalance date (no future data used)
- Weekend/holiday rebalance dates
- Assets eligible at one rebalance but not the next

**Validation:**

- ✅ Early rebalances correctly exclude assets without sufficient history
- ✅ No future data leakage verified (checking future dates doesn't add information)
- ✅ Weekend/holiday dates handled gracefully
- ✅ Eligibility changes over time as expected

**Key Finding:**
The implementation correctly enforces point-in-time constraints:

- Only data up to `check_date` is considered
- Checking a future date (beyond available data) produces consistent or more restrictive results
- No lookahead bias detected in spot checks

### 6. Validation and Determinism

**Test Cases:**

- No lookahead bias (manual spot checks)
- Determinism (same inputs → same outputs)
- Graceful degradation with sparse data
- History enforcement at all boundaries

**Validation:**

- ✅ Same inputs produce identical outputs across multiple runs
- ✅ No exceptions raised with sparse data
- ✅ History requirements enforced consistently
- ✅ No lookahead bias in eligibility computation

## Known Limitations

### 1. Delisting Detection Lookforward

**Limitation:**
The `detect_delistings()` function uses a lookforward window (default 30 days) to confirm delistings. This is **not truly point-in-time** as it peeks into the future.

**Rationale:**
This is a pragmatic design choice for backtesting:

- Prevents premature liquidation of temporarily halted assets
- Reduces false positives from short trading gaps
- Acceptable for historical backtesting where we know the future

**Impact:**

- In live trading, this function cannot be used
- For live trading, a different approach is needed (e.g., delisting announcements)

**Documented in:** `src/portfolio_management/backtesting/eligibility.py` line 171

### 2. Historical Data Accumulation

**Limitation:**
Eligibility is based on **cumulative historical data**, not recent contiguous data.

**Example:**
An asset with:

- 100 days of data in 2020
- 200-day gap
- Currently trading in 2021

Would be eligible if cumulative history meets thresholds, even though it had a 200-day gap.

**Rationale:**
This approach ensures sufficient data points for statistical analysis (e.g., covariance estimation).

**Alternative:**
If you need contiguous data, add a custom filter checking for maximum gap size.

### 3. No Coverage Requirement

**Limitation:**
There's no minimum coverage percentage requirement (e.g., "must have data for 80% of calendar days").

**Example:**
An asset with 252 observations spread over 1000 calendar days would be eligible if thresholds are 252 days and 252 rows.

**Workaround:**
Use the `get_asset_history_stats()` function to check `coverage_pct` and add custom filtering.

### 4. Weekend/Holiday Handling

**Limitation:**
When checking eligibility on a weekend or holiday (no trading data), the function uses data up to that date without adjustment.

**Impact:**

- Generally not an issue as most backtests use business days
- For calendar-day scheduling, consider using business day logic

## Recommendations

### For Production Use

1. **Set Appropriate Thresholds:**

   - `min_history_days=252` (1 trading year) is standard
   - `min_price_rows=252` ensures ~1 year of actual observations
   - Adjust based on your analysis needs

1. **Monitor Sparse Assets:**

   - Use `get_asset_history_stats()` to check coverage
   - Consider requiring minimum coverage % (e.g., 80%)
   - Filter out assets with excessive gaps if needed

1. **Delisting Handling:**

   - The default `lookforward_days=30` is reasonable for most cases
   - Increase for more conservative liquidation
   - Decrease for faster delisting detection

1. **Validate Results:**

   - Periodically spot-check eligibility decisions
   - Verify no lookahead bias in your specific setup
   - Test edge cases specific to your data

### For Custom Requirements

**If you need contiguous data:**

```python
# After getting eligible assets, filter by gaps
stats = get_asset_history_stats(returns, check_date)
eligible_contiguous = stats[
    (stats['coverage_pct'] >= 80) &  # 80% coverage
    eligible  # Already meets basic requirements
]
```

**If you need recent data only:**

```python
# Custom filter for data in recent window
recent_window = 63  # ~3 months
recent_data = returns.iloc[-recent_window:]
has_recent_data = recent_data.notna().sum() >= (recent_window * 0.8)
eligible_recent = eligible & has_recent_data
```

## Test Summary

**Total Edge Case Tests:** 29 tests across 7 test classes

**Coverage:**

- Sparse data: 6 tests
- Delistings: 5 tests
- Universe changes: 3 tests
- History boundaries: 4 tests
- Date boundaries: 4 tests
- Validation: 4 tests
- Stats integration: 3 tests

**All tests passing:** ✅ 29/29 (100%)

**Delisting detection accuracy:** >95% (validated)

**No lookahead bias:** ✅ Verified with spot checks

**Determinism:** ✅ Verified (same inputs = same outputs)

## Related Documentation

- Implementation: `src/portfolio_management/backtesting/eligibility.py`
- Basic tests: `tests/backtesting/test_pit_eligibility.py`
- Acceptance tests: `tests/backtesting/test_pit_acceptance.py`
- Edge case tests: `tests/integration/test_pit_edge_cases.py`

## Version

**Documentation Version:** 1.0
**Date:** 2025-10-24
**Test Suite Version:** Comprehensive edge case coverage complete
