# Warning Messages Guide

This document explains all warning messages in the portfolio management system, what they mean, and when you should take action.

## Understanding Warnings

Warnings are **non-fatal** - your code will continue to execute. However, they indicate:
- Suboptimal configurations that may hurt performance
- Potential issues that could become problems
- Best practice violations

### Severity Levels

- 🟡 **Low**: Informational, consider addressing
- 🟠 **Medium**: Likely to impact results, should address
- 🔴 **High**: Will significantly impact performance/results, address urgently

---

## Preselection Warnings

### 🟠 "top_k is very small (<10 assets)"

**Severity**: Medium

**When it appears**:
```python
PreselectionConfig(top_k=5)  # Triggers warning
```

**What it means**:
- Your portfolio will contain very few assets (< 10)
- High concentration risk - portfolio heavily dependent on few positions
- Increased volatility due to lack of diversification
- Single asset failures have large impact

**Impact on your portfolio**:
- Higher risk (volatility, drawdowns)
- Correlation to individual companies rather than market
- Potential regulatory issues if managing others' money
- Reduced robustness to stock-specific shocks

**When to ignore**:
- High-conviction strategy where you want concentrated bets
- Hedge fund / alternative strategy with active risk management
- You have strong fundamental analysis supporting few positions
- You understand and accept the concentration risk

**Recommended action**:
```python
# For typical portfolios, use 20-50 assets
PreselectionConfig(top_k=30)  # Better diversification

# For conservative portfolios
PreselectionConfig(top_k=50)  # Even better diversification
```

**Academic context**: Modern portfolio theory suggests 20-30 stocks capture most diversification benefits. Fewer than 10 leaves significant idiosyncratic risk.

---

### 🟠 "lookback is very short (<63 days / 3 months)"

**Severity**: Medium

**When it appears**:
```python
PreselectionConfig(lookback=30)  # Triggers warning
```

**What it means**:
- Factor signals based on only 30-60 days of data
- High sensitivity to short-term noise and volatility
- Likely to produce unstable rankings that change frequently
- Increased transaction costs due to high turnover

**Impact on your portfolio**:
- High turnover (monthly changes to holdings)
- Increased transaction costs eating into returns
- Chasing short-term trends that may reverse
- More noise, less signal in factor scores

**When to ignore**:
- Momentum strategy explicitly targeting short-term trends
- Tactical allocation with frequent rebalancing
- You have very low transaction costs
- Strategy is based on short-term market inefficiencies

**Recommended action**:
```python
# For typical momentum strategies
PreselectionConfig(lookback=252)  # 1 year (classic momentum)

# For balanced approach
PreselectionConfig(lookback=126)  # 6 months

# For short-term tactical (still longer than 30)
PreselectionConfig(lookback=63)  # 3 months minimum
```

**Academic context**: Jegadeesh and Titman (1993) classic momentum uses 6-12 month formation periods. Shorter periods capture more noise than signal.

---

## Membership Policy Warnings

### 🟠 "buffer_rank very close to top_k (gap < 20%)"

**Severity**: Medium

**When it appears**:
```python
policy = MembershipPolicy(
    buffer_rank=35,  # Only 5 positions buffer
    top_k=30
)  # Gap = 5, 16% - triggers warning
```

**What it means**:
- Buffer zone is too narrow to effectively stabilize portfolio
- Assets ranked 31-35 are borderline - small changes cause churn
- Policy won't significantly reduce turnover
- Defeats purpose of having a buffer

**Impact on your portfolio**:
- Still high turnover despite having membership policy
- Assets frequently flip in/out of portfolio
- Increased transaction costs
- Membership policy not providing intended stability benefit

**When to ignore**:
- You want aggressive rebalancing with minimal buffer
- Your strategy requires tight tracking of top-ranked assets
- Other turnover controls (min_holding_periods) provide stability

**Recommended action**:
```python
# Adequate buffer (20% gap)
policy = MembershipPolicy(
    buffer_rank=36,  # 20% above top_k=30
    top_k=30
)

# Better buffer (33% gap)  
policy = MembershipPolicy(
    buffer_rank=40,  # 33% above top_k=30
    top_k=30
)

# Conservative buffer (67% gap)
policy = MembershipPolicy(
    buffer_rank=50,  # 67% above top_k=30
    top_k=30
)
```

**Rule of thumb**: `buffer_rank` should be at least `top_k * 1.2` (20% higher).

**Example calculation**:
- top_k = 30
- Minimum buffer_rank = 30 * 1.2 = 36
- Recommended buffer_rank = 30 * 1.3 = 39 or 30 * 1.5 = 45

---

## Cache Warnings

### 🔴 "Caching disabled for large universe (>500 assets)"

**Severity**: High (performance impact)

**When it appears**:
```python
# 800 assets but cache disabled
returns = pd.DataFrame(...)  # 800 columns
cache = FactorCache(cache_dir, enabled=False)
preselect = Preselection(config, cache=cache)
```

**What it means**:
- Every preselection call recomputes factor scores from scratch
- For large universes, this is computationally expensive
- Monthly rebalancing over 10 years = 120 recomputations
- Each computation processes 800 assets * lookback periods

**Impact on performance**:

| Assets | Lookback | Time per call | 120 calls | With cache |
|--------|----------|---------------|-----------|-----------|
| 500 | 252 | ~2 sec | 4 min | ~10 sec |
| 1000 | 252 | ~5 sec | 10 min | ~15 sec |
| 2000 | 252 | ~15 sec | 30 min | ~20 sec |

**When to ignore**:
- Running a one-off backtest (no repeated runs)
- Disk space is severely limited
- Cache directory is not writable
- Data changes every run (cache wouldn't help)

**Recommended action**:
```python
# Enable caching for large universes
cache = FactorCache(
    Path(".cache/factors"),
    enabled=True,
    max_cache_age_days=7  # Auto-expire after 1 week
)
preselect = Preselection(config, cache=cache)
```

**When working with different datasets**:
```python
# Use separate cache directories for different datasets
cache_spy = FactorCache(Path(".cache/spy_universe"))
cache_russell = FactorCache(Path(".cache/russell_2000"))
```

---

### 🟡 "Cache write failed. Continuing without caching."

**Severity**: Low (one-time issue) to Medium (recurring)

**When it appears**:
- Disk is full
- Permission denied on cache directory
- Quota exceeded
- Network drive disconnected

**What it means**:
- Current computation completed successfully
- Result NOT cached for future use
- Next run will recompute everything
- Not a fatal error - execution continues

**Immediate impact**: None (current run succeeds)

**Future impact**: Slower subsequent runs

**When to ignore**:
- First occurrence - might be transient
- Running final production backtest (no future runs)
- You plan to clear cache anyway

**Recommended action**:

1. **Check disk space**:
```bash
df -h  # On Unix/Linux/Mac
# Look for cache directory mount point
```

2. **Check cache size**:
```bash
du -sh ~/.cache/portfolio
# If > 1GB, consider clearing
```

3. **Clear old cache**:
```python
cache.clear()  # Removes all entries
```

4. **Check permissions**:
```bash
ls -la ~/.cache/portfolio
# Should be writable by your user
```

5. **If recurring, disable cache**:
```python
# Disable to stop warnings
cache = FactorCache(cache_dir, enabled=False)
```

---

## Data Quality Warnings

### 🔴 "All factor scores are NaN"

**Severity**: High (no valid output)

**When it appears**:
```python
# Returns insufficient data across all assets
selected = preselect.select_assets(returns, rebalance_date)
# Returns: []  (empty list)
```

**What it means**:
- No asset has sufficient data to compute factor scores
- Either lookback period too long or data too sparse
- Cannot construct portfolio - no valid candidates

**Common causes**:
1. **Lookback too long for early periods**:
   - Rebalancing in 2020 but data starts in 2019
   - lookback=252 requires 1 year of history

2. **Data quality issues**:
   - Many NaN values in returns
   - Assets have sparse price histories
   - Recent IPOs without sufficient history

3. **Configuration mismatch**:
   - min_periods > available data
   - All assets fail data sufficiency checks

**Recommended action**:

1. **Check data availability**:
```python
# When does each asset have data?
first_valid = returns.apply(pd.Series.first_valid_index)
print(f"Earliest data: {first_valid.min()}")
print(f"Latest start: {first_valid.max()}")

# How much data per asset?
data_points = returns.notna().sum()
print(f"Data points per asset:\n{data_points.describe()}")
```

2. **Adjust configuration**:
```python
# Reduce requirements
config = PreselectionConfig(
    lookback=126,    # Reduced from 252
    min_periods=30   # Reduced from 60
)
```

3. **Filter assets before preselection**:
```python
# Only use assets with sufficient history
min_date = rebalance_date - timedelta(days=300)
eligible_assets = [
    col for col in returns.columns
    if returns[col].first_valid_index() <= min_date
]
returns_filtered = returns[eligible_assets]
```

---

### 🟡 "No historical data available up to {date}"

**Severity**: Low (expected for early dates)

**When it appears**:
```python
# Trying to compute eligibility before data starts
eligibility = compute_pit_eligibility(
    returns,  # Starts 2020-01-01
    date=date(2019, 12, 31)  # Before data range
)
# Returns: all False
```

**What it means**:
- Eligibility date is before data begins
- All assets correctly marked as ineligible
- This is expected behavior, not an error

**Impact**: None if handled correctly in backtest loop

**When to worry**:
- If you expected data to exist at this date
- If this happens for many rebalance periods
- If you're iterating through dates incorrectly

**Recommended action**:

1. **Check date range**:
```python
print(f"Data range: {returns.index.min()} to {returns.index.max()}")
```

2. **Adjust backtest start date**:
```python
# Start after data is available + lookback
backtest_start = returns.index.min() + timedelta(days=252)
```

3. **Handle in backtest loop**:
```python
for date in rebalance_dates:
    # Skip if before data range
    if date < returns.index.min():
        logger.warning(f"Skipping {date} - before data range")
        continue
    
    # Compute eligibility
    eligible = compute_pit_eligibility(returns, date)
```

---

## Performance Warnings

### 🟠 "Only X valid assets available, less than requested top_k"

**Severity**: Medium (portfolio under-invested)

**When it appears**:
```python
# Requested 30 assets, only 15 valid
selected = preselect.select_assets(returns, rebalance_date)
# len(selected) = 15 < top_k=30
```

**What it means**:
- Fewer assets pass data sufficiency checks than requested
- Portfolio will be under-diversified (< target asset count)
- Could indicate data quality issues
- Common in early backtest periods or with young universes

**Impact on portfolio**:
- Lower diversification than intended
- Higher concentration risk
- May not meet portfolio constraints (e.g., min 20 assets)

**Recommended action**:

1. **Understand the cause**:
```python
# Check asset eligibility
for ticker in returns.columns:
    data_points = returns[ticker].notna().sum()
    first_date = returns[ticker].first_valid_index()
    print(f"{ticker}: {data_points} points, starts {first_date}")
```

2. **Adjust configuration**:
```python
# More lenient requirements
config = PreselectionConfig(
    top_k=30,
    lookback=126,    # Reduced from 252
    min_periods=30   # Reduced from 60
)
```

3. **Handle in portfolio construction**:
```python
# Adjust position sizing based on actual count
if len(selected) < target_positions:
    logger.warning(
        f"Only {len(selected)} assets selected, "
        f"adjusting position size from {1/target_positions:.2%} "
        f"to {1/len(selected):.2%}"
    )
```

---

## Warning Configuration

### Suppressing Specific Warnings

If you've assessed a warning and decided it doesn't apply to your use case:

```python
import warnings

# Suppress specific warning type
warnings.filterwarnings(
    'ignore',
    message='top_k is very small',
    category=UserWarning
)

# Or suppress all UserWarnings (not recommended)
warnings.filterwarnings('ignore', category=UserWarning)
```

### Making Warnings More Visible

To ensure warnings aren't missed:

```python
import warnings

# Convert warnings to errors (fail fast)
warnings.filterwarnings('error', category=UserWarning)

# Or just make them always visible
warnings.simplefilter('always', UserWarning)
```

### Logging Warnings

To capture warnings in your logs:

```python
import logging
logging.captureWarnings(True)

# Now warnings go to logging system
logger = logging.getLogger()
logger.setLevel(logging.WARNING)
```

---

## Warning Best Practices

### Do's ✅

- **Read warning messages carefully** - they contain specific guidance
- **Understand the implication** for your strategy before dismissing
- **Log warnings** for post-analysis
- **Test with warned configurations** to measure actual impact
- **Document your decision** if ignoring a warning

### Don'ts ❌

- **Don't blindly suppress all warnings** - you'll miss real issues
- **Don't ignore high-severity warnings** (🔴 Red)
- **Don't assume warnings are bugs** - they're usually valid concerns
- **Don't treat warnings as errors** - code runs, but suboptimally

### Decision Framework

When you see a warning:

1. **Understand**: Read the warning and this guide
2. **Assess**: Does it apply to your use case?
3. **Measure**: Test impact if uncertain
4. **Decide**: Fix, acknowledge, or suppress
5. **Document**: Record your decision

Example decision log:
```python
# Decision: Ignoring "top_k is very small" warning
# Rationale: High-conviction strategy, target 5 positions
# Risk: Accepted concentration risk, monitored via separate alerts
# Date: 2024-01-15
# Reviewer: Portfolio Manager
config = PreselectionConfig(top_k=5)
warnings.filterwarnings('ignore', message='top_k is very small')
```

---

## Summary Table

| Warning | Severity | When to Address | Quick Fix |
|---------|----------|----------------|-----------|
| top_k < 10 | 🟠 Medium | Most portfolios | `top_k=30` |
| lookback < 63 | 🟠 Medium | Most strategies | `lookback=126` |
| buffer_rank close | 🟠 Medium | If using membership | `buffer_rank = top_k * 1.2` |
| No cache + large | 🔴 High | Always (unless one-off) | `enabled=True` |
| Cache write fail | 🟡 → 🟠 | If recurring | Free disk, clear cache |
| All NaN scores | 🔴 High | Always | Reduce lookback/min_periods |
| No historical data | 🟡 Low | Usually OK | Check date range |
| Fewer than top_k | 🟠 Medium | If frequent | Reduce requirements |

---

## Getting Help

If a warning is unclear or you're unsure whether to address it:

1. Check this guide for detailed explanation
2. Review `docs/troubleshooting.md` for solutions
3. Test both configurations (with/without warning) to measure impact
4. File an issue if warning seems incorrect or unhelpful
5. Consult with domain experts for strategy-specific decisions
