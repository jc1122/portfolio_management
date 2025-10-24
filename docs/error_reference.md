# Error Reference Guide

Quick reference for all error messages and their solutions.

## Quick Index

- [Configuration Errors](#configuration-errors)
- [Data Validation Errors](#data-validation-errors)
- [Runtime Errors](#runtime-errors)
- [Cache Errors](#cache-errors)

---

## Configuration Errors

### Preselection Configuration

| Error Message | Fix |
|--------------|-----|
| `top_k must be >= 0` | Use 0, None, or positive integer: `top_k=30` |
| `lookback must be >= 1` | Use positive integer: `lookback=252` |
| `skip must be >= 0` | Use 0 or positive integer: `skip=1` |
| `skip must be < lookback` | Reduce skip or increase lookback |
| `min_periods must be >= 1` | Use positive integer: `min_periods=60` |
| `min_periods must be <= lookback` | Reduce min_periods or increase lookback |
| `Combined weights must sum to 1.0` | Adjust `momentum_weight` and `low_vol_weight` to sum to 1.0 |

### Membership Policy Configuration

| Error Message | Fix |
|--------------|-----|
| `buffer_rank must be >= 1` | Use positive integer > top_k: `buffer_rank=50` |
| `min_holding_periods must be non-negative` | Use 0 or positive integer: `min_holding_periods=3` |
| `max_turnover must be in [0, 1]` | Use fraction: `max_turnover=0.30` (not 30) |
| `max_new_assets must be non-negative` | Use 0 or positive integer: `max_new_assets=5` |
| `max_removed_assets must be non-negative` | Use 0 or positive integer: `max_removed_assets=5` |

### Eligibility Configuration

| Error Message | Fix |
|--------------|-----|
| `min_history_days must be > 0` | Use positive integer: `min_history_days=252` |
| `min_price_rows must be > 0` | Use positive integer: `min_price_rows=252` |

### Cache Configuration

| Error Message | Fix |
|--------------|-----|
| `max_cache_age_days must be >= 0` | Use None or non-negative integer: `max_cache_age_days=7` |
| `cache_dir must be a Path or str` | Use Path: `cache_dir=Path('.cache')` |

---

## Data Validation Errors

### Input Type Errors

| Error Message | Fix | Example |
|--------------|-----|---------|
| `returns must be a pandas DataFrame` | Convert to DataFrame | `returns = pd.DataFrame(data)` |
| `returns DataFrame is empty or None` | Load data | `returns = pd.read_csv('returns.csv')` |
| `returns DataFrame has no columns` | Ensure columns exist | Check `returns.columns` |
| `rebalance_date must be a datetime.date` | Use date type | `from datetime import date; d = date(2023, 1, 1)` |
| `date must be a datetime.date` | Use date type | Same as above |
| `current_holdings must be a list` | Convert to list | `current_holdings = list(holdings)` |
| `preselected_ranks must be a pandas Series` | Convert to Series | `ranks = pd.Series(data)` |
| `holding_periods must be a dict` | Convert to dict | `holding_periods = dict(periods)` |

### Data Range Errors

| Error Message | Fix | Check |
|--------------|-----|-------|
| `rebalance_date is after the last available date` | Use date within range | `returns.index.max()` |
| `date is after the last available date` | Use date within range | `returns.index.max()` |
| `Insufficient data: need X periods, have Y` | Load more data or reduce requirements | `len(returns)` |

### Data Content Errors

| Error Message | Fix |
|--------------|-----|
| `preselected_ranks is empty` | Check preselection results |
| `holding_periods contains negative values` | Ensure all values >= 0 |
| `top_k must be > 0` | Use positive integer |

---

## Runtime Errors

### Preselection Runtime

| Error/Warning | Cause | Solution |
|--------------|-------|----------|
| `All factor scores are NaN` | Insufficient valid data | Reduce lookback/min_periods or check data quality |
| `No valid scores after filtering NaN` | All assets have insufficient data | Check data availability |
| `Only X valid assets available, less than requested top_k` | Limited valid assets | Accept fewer assets or improve data quality |

### Membership Policy Runtime

| Error Message | Cause | Solution |
|--------------|-------|----------|
| `holding_periods required when min_holding_periods is set` | Missing required parameter | Provide `holding_periods` dict |
| `current_weights and candidate_weights required when max_turnover is set` | Missing required parameters | Provide weight dicts |

### Eligibility Runtime

| Warning | Cause | Solution |
|---------|-------|----------|
| `No historical data available up to {date}` | Date too early | Use later date or load earlier data |

---

## Cache Errors

### Cache Initialization

| Error Message | Cause | Solution |
|--------------|-------|----------|
| `Cache directory {path} is not writable` | Permission denied | Use `~/.cache/portfolio` or check permissions |
| `Failed to create cache directories` | Permission or disk issue | Check `df -h` and permissions |

### Cache Operations

| Warning | Cause | Solution |
|---------|-------|----------|
| `Cache write failed. Continuing without caching.` | Disk full or permission denied | Free disk space or clear cache |
| `Corrupted metadata for factor scores` | File corruption | Clear cache: `cache.clear()` |
| `Failed to load cached data` | Pickle error or corruption | Clear cache: `cache.clear()` |
| `Corrupted metadata for PIT eligibility` | File corruption | Clear cache: `cache.clear()` |
| `Cache expired for factor scores` | Exceeded max_cache_age_days | Normal behavior, will recompute |

---

## Warnings Reference

### Configuration Warnings

| Warning | Threshold | Impact | Recommendation |
|---------|-----------|--------|----------------|
| `top_k is very small` | < 10 assets | Concentration risk | Use top_k >= 10 |
| `lookback is very short` | < 63 days | Noisy signals, high turnover | Use lookback >= 63 |
| `buffer_rank very close to top_k` | Gap < 20% | Ineffective buffer | buffer_rank >= top_k * 1.2 |
| `Caching disabled for large universe` | > 500 assets | Slow performance | Enable caching |

### Runtime Warnings

| Warning | Cause | Action |
|---------|-------|--------|
| `All factor scores are NaN` | No valid data | Check data quality |
| `No valid scores after filtering` | Insufficient data | Reduce requirements |
| `Cache directory not accessible` | Permission issue | Fix permissions or disable cache |
| `max_turnover policy configured but not enforced` | Future enhancement | Informational only |

---

## Error Code Matrix

### By Module

| Module | Validation Errors | Runtime Errors | Warnings |
|--------|------------------|----------------|----------|
| `preselection.py` | 7 | 3 | 2 |
| `membership.py` | 5 | 3 | 1 |
| `eligibility.py` | 4 | 1 | 0 |
| `factor_cache.py` | 2 | 2 | 2 |

### By Severity

| Severity | Count | Action |
|----------|-------|--------|
| **Critical** (ValueError) | 18 | Fix immediately - prevents execution |
| **Warning** (UserWarning) | 6 | Address for optimal performance |
| **Info** (logging.warning) | 8 | Informational - execution continues |

---

## Common Resolution Patterns

### Pattern 1: Parameter Out of Range

**Symptoms**: ValueError mentioning "must be >= X" or "must be in [X, Y]"

**Resolution**:
1. Check error message for valid range
2. Adjust parameter to valid value
3. See error message for example

**Example**:
```python
# Error: max_turnover must be in [0, 1]
MembershipPolicy(max_turnover=30)  # ❌

# Fix: Use fraction
MembershipPolicy(max_turnover=0.30)  # ✅
```

### Pattern 2: Insufficient Data

**Symptoms**: "Insufficient data", "need X periods, have Y"

**Resolution**:
1. Check data length: `len(returns)`
2. Either load more data or reduce requirements
3. Ensure data quality (check NaN percentage)

**Example**:
```python
# Check data
print(f"Rows: {len(returns)}, Columns: {len(returns.columns)}")
print(f"NaN%: {returns.isna().sum().sum() / returns.size * 100:.1f}%")

# Option 1: Load more data
returns = load_returns(start_date="2020-01-01")

# Option 2: Reduce requirements
config = PreselectionConfig(lookback=126, min_periods=30)
```

### Pattern 3: Type Mismatch

**Symptoms**: "must be a pandas DataFrame", "must be a dict"

**Resolution**:
1. Check actual type: `type(variable)`
2. Convert to expected type
3. Verify structure matches expectations

**Example**:
```python
# Check type
print(type(returns))  # Should be <class 'pandas.core.frame.DataFrame'>

# Convert if needed
if not isinstance(returns, pd.DataFrame):
    returns = pd.DataFrame(returns)
```

### Pattern 4: Cache Issues

**Symptoms**: "Cache write failed", "not writable", "disk full"

**Resolution**:
1. Check disk space: `df -h`
2. Check permissions: `ls -la ~/.cache`
3. Clear old cache: `cache.clear()`
4. As last resort, disable caching

**Example**:
```python
# Check cache status
print(f"Cache enabled: {cache.enabled}")
print(f"Cache stats: {cache.get_stats()}")

# Clear if needed
cache.clear()

# Or disable
cache = FactorCache(cache_dir, enabled=False)
```

---

## Debugging Checklist

When encountering an error:

- [ ] Read the full error message (includes fix guidance)
- [ ] Check parameter values and types
- [ ] Verify data shape and range: `returns.shape`, `returns.index.min()`, `returns.index.max()`
- [ ] Check for NaN values: `returns.isna().sum()`
- [ ] Enable debug logging: `logging.basicConfig(level=logging.DEBUG)`
- [ ] Review similar examples in `examples/` directory
- [ ] Check this error reference guide
- [ ] Consult troubleshooting guide (`docs/troubleshooting.md`)
- [ ] If still stuck, file an issue on GitHub with:
  - Complete error message
  - Minimal reproducible example
  - Python version, package versions
  - Data shape and statistics

---

## Quick Command Reference

### Data Inspection
```python
# Check data
print(f"Shape: {returns.shape}")
print(f"Dates: {returns.index.min()} to {returns.index.max()}")
print(f"Assets: {len(returns.columns)}")
print(f"NaN%: {returns.isna().sum().sum() / returns.size * 100:.1f}%")
```

### Cache Management
```python
# Check cache
cache.print_stats()
print(f"Cache enabled: {cache.enabled}")

# Clear cache
cache.clear()

# Disable cache
cache = FactorCache(cache_dir, enabled=False)
```

### Logging
```python
# Enable debug logging
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Data Quality Checks
```python
# Check coverage per asset
coverage = returns.notna().sum() / len(returns)
print(f"Assets with <50% coverage: {(coverage < 0.5).sum()}")

# Check first/last valid dates per asset
first_valid = returns.apply(pd.Series.first_valid_index)
last_valid = returns.apply(pd.Series.last_valid_index)
```
