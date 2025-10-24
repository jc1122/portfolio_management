# Configuration Validation & Sensible Defaults

## Overview

The portfolio management toolkit includes comprehensive configuration validation to help users avoid common mistakes, detect invalid parameter combinations, and identify suboptimal settings. Validation runs automatically before expensive operations begin, providing immediate feedback with clear, actionable error messages and warnings.

## Key Features

- **Early Detection**: Validation runs before data loading and computation
- **Parameter Range Checking**: Ensures all values are within valid bounds
- **Conflict Detection**: Identifies incompatible feature combinations
- **Optimality Warnings**: Flags suboptimal but valid configurations
- **Dependency Checks**: Verifies optional dependencies are available
- **Sensible Defaults**: Provides recommended starting values
- **Flexible Modes**: Strict mode, warning suppression, or standard validation

## Validation Categories

### 1. Parameter Ranges

Validates that individual parameters are within acceptable bounds.

#### Preselection Parameters
- `top_k`: Must be > 0 if provided (None disables preselection)
- `lookback`: Must be >= 1
- `skip`: Must be >= 0 and < lookback
- `min_periods`: Must be > 0
- `method`: Must be one of "momentum", "low_vol", "combined"

#### Membership Policy Parameters
- `buffer_rank`: Must be > 0 if provided
- `min_holding_periods`: Must be >= 0
- `max_turnover`: Must be in [0, 1]
- `max_new_assets`: Must be > 0 if provided
- `max_removed_assets`: Must be > 0 if provided

#### Point-in-Time Eligibility Parameters
- `min_history_days`: Must be > 0
- `min_price_rows`: Must be > 0

#### Cache Parameters
- `max_age_days`: Must be >= 0 if provided
- `max_size_mb`: Must be >= 0 if provided
- `cache_dir`: Must be writable if caching enabled

### 2. Feature Conflicts

Detects invalid combinations of features that cannot work together.

#### Buffer Rank < Top K
**Invalid:** `buffer_rank=20` with `top_k=30`

Buffer rank must be greater than top_k. The buffer provides hysteresis to prevent churn, so it needs to be looser than the selection threshold.

```bash
# ❌ Invalid
python scripts/run_backtest.py equal_weight \
  --preselect-top-k=30 \
  --membership-enabled \
  --membership-buffer-rank=20

# ✅ Valid
python scripts/run_backtest.py equal_weight \
  --preselect-top-k=30 \
  --membership-enabled \
  --membership-buffer-rank=50
```

#### Min Holding Periods > Total Periods
**Invalid:** `min_holding_periods=10` when backtest only has 5 rebalance periods

This constraint is impossible to satisfy.

#### Preselection Disabled with Membership Policy
**Warning:** Membership policy enabled but preselection disabled

Membership policy works best with preselection. Consider enabling preselection with `--preselect-top-k`.

#### Cache Directory Not Writable
**Invalid:** Caching enabled but cache directory cannot be created or written

Disable caching or choose a different directory.

### 3. Optimality Warnings

Identifies configurations that are valid but suboptimal.

#### Small Top K (< 10 assets)
**Warning:** Limited diversification

```bash
# ⚠️ Warning: Poor diversification
python scripts/run_backtest.py equal_weight --preselect-top-k=5

# ✅ Better: Improved diversification
python scripts/run_backtest.py equal_weight --preselect-top-k=30
```

**Rationale:** Modern portfolio theory suggests 20-30 assets are needed for effective diversification. Fewer assets increase idiosyncratic risk.

#### Short Lookback (< 63 days / ~3 months)
**Warning:** Unstable factor estimates

```bash
# ⚠️ Warning: Unstable factors
python scripts/run_backtest.py equal_weight --preselect-lookback=30

# ✅ Better: More stable estimates
python scripts/run_backtest.py equal_weight --preselect-lookback=252
```

**Rationale:** Factor estimates need sufficient history for stability. At least 3 months (63 trading days) recommended; 1 year (252 days) is standard.

#### Buffer Rank Too Close to Top K (< 20% gap)
**Warning:** Insufficient hysteresis

```bash
# ⚠️ Warning: Minimal hysteresis
python scripts/run_backtest.py equal_weight \
  --preselect-top-k=30 \
  --membership-buffer-rank=32

# ✅ Better: Meaningful buffer
python scripts/run_backtest.py equal_weight \
  --preselect-top-k=30 \
  --membership-buffer-rank=50
```

**Rationale:** Buffer rank should be at least 20% higher than top_k to provide meaningful turnover reduction.

#### Caching Disabled for Large Universe (> 500 assets)
**Warning:** Performance impact

```bash
# ⚠️ Warning: Slow without caching
python scripts/run_backtest.py equal_weight \
  --universe-name=large_universe  # 1000 assets

# ✅ Better: Enable caching
python scripts/run_backtest.py equal_weight \
  --universe-name=large_universe \
  --enable-cache
```

**Rationale:** Factor computation and eligibility checks can be expensive for large universes. Caching can provide 10-100x speedups.

### 4. Dependency Checks

Verifies that optional dependencies are available when needed.

#### Polars/PyArrow for Fast IO
When fast IO is enabled, checks for `polars` or `pyarrow` installation.

```bash
# Install if missing
pip install polars pyarrow
```

#### Disk Space for Caching
Warns if available disk space is low (< 1 GB).

## Sensible Defaults

The toolkit provides sensible defaults based on industry best practices and empirical research.

### Preselection
```yaml
top_k: 30              # Sufficient for diversification
lookback: 252          # 1 year of daily data
skip: 1                # Skip most recent day (common practice)
min_periods: 63        # ~3 months minimum
momentum_weight: 0.5   # Balanced combined strategy
low_vol_weight: 0.5    # Balanced combined strategy
```

**Rationale:**
- `top_k=30`: Balances diversification benefits with computational efficiency. Research suggests diminishing returns beyond 20-30 assets.
- `lookback=252`: Standard one-year window provides stable estimates while remaining responsive to market changes.
- `skip=1`: Skipping the most recent day reduces microstructure noise and potential lookahead bias.
- `min_periods=63`: Minimum 3 months of data required for meaningful statistics.

### Membership Policy
```yaml
buffer_rank: None      # Disabled by default (opt-in feature)
min_holding_periods: 0 # No minimum holding period
max_turnover: 1.0      # No turnover limit (100%)
max_new_assets: None   # No limit on additions
max_removed_assets: None  # No limit on removals
```

**Rationale:**
- Membership policy is opt-in to avoid unintended behavior
- When enabled, users should explicitly configure constraints
- Default to no restrictions, letting users add constraints as needed

### Point-in-Time Eligibility
```yaml
enabled: False         # Opt-in feature
min_history_days: 252  # 1 year of history
min_price_rows: 252    # 1 year of price data
```

**Rationale:**
- PIT filtering is opt-in to avoid unexpected asset exclusions
- 1 year minimum ensures sufficient data for portfolio construction
- Prevents including assets with insufficient history

### Caching
```yaml
enabled: False         # Opt-in feature
cache_dir: ".cache/backtest"  # Standard location
max_age_days: None     # No expiration (invalidation by content)
max_size_mb: None      # No size limit
```

**Rationale:**
- Caching is opt-in to avoid unexpected disk usage
- Cache invalidation by content hash more reliable than age
- No size limit avoids cache thrashing

## CLI Usage

### View Defaults
Display all sensible defaults:
```bash
python scripts/run_backtest.py --show-defaults
```

Output:
```
📋 Sensible Configuration Defaults
======================================================================

Preselection:
  --preselect-top-k: 30
  --preselect-lookback: 252
  --preselect-skip: 1
  --preselect-min-periods: 63
  ...

Membership Policy:
  --membership-buffer-rank: None
  --membership-min-hold: 0
  ...

Point-in-Time Eligibility:
  --min-history-days: 252
  --min-price-rows: 252

Caching:
  --cache-dir: .cache/backtest
  --cache-max-age-days: None
  ...
```

### Standard Validation (Default)
Warnings are displayed but do not prevent execution:
```bash
python scripts/run_backtest.py equal_weight \
  --preselect-top-k=5 \
  --preselect-lookback=30
```

Output:
```
⚠️  Configuration Warnings:
======================================================================

🟡 MEDIUM Severity:
  • top_k: top_k=5 may be too small for meaningful diversification
  • lookback: lookback=30 may be too short for stable factor estimates

======================================================================
Run with --verbose for detailed suggestions.

[Backtest continues...]
```

### Strict Mode
Treat warnings as errors and exit immediately:
```bash
python scripts/run_backtest.py equal_weight \
  --preselect-top-k=5 \
  --strict
```

Output:
```
ConfigurationError: High-severity optimality warnings:
top_k: top_k=5 may be too small for meaningful diversification
```

### Suppress Warnings
Disable warning output (not recommended):
```bash
python scripts/run_backtest.py equal_weight \
  --preselect-top-k=5 \
  --ignore-warnings
```

### Verbose Mode
Show detailed suggestions:
```bash
python scripts/run_backtest.py equal_weight \
  --preselect-top-k=5 \
  --verbose
```

Output:
```
⚠️  Configuration Warnings:
======================================================================

🟡 MEDIUM Severity:
  • OPTIMALITY: top_k
    Problem: top_k=5 may be too small for meaningful diversification
    Suggestion: Consider using top_k >= 10 for better diversification

======================================================================
```

## Programmatic API

### Validate Individual Components
```python
from portfolio_management.config.validation import (
    validate_preselection_config,
    validate_membership_config,
    validate_pit_config,
    validate_cache_config,
)

# Validate preselection
result = validate_preselection_config(
    top_k=30,
    lookback=252,
    skip=1,
    method="momentum",
)

if not result.valid:
    print("Errors:", result.errors)
for warning in result.warnings:
    print(f"{warning.severity}: {warning.message}")
```

### Strict Mode
```python
# Raises ConfigurationError if validation fails
validate_preselection_config(
    top_k=5,
    lookback=30,
    strict=True,  # Treat warnings as errors
)
```

### Get Defaults
```python
from portfolio_management.config.validation import get_sensible_defaults

defaults = get_sensible_defaults()
print(defaults["preselection"]["top_k"])  # 30
print(defaults["membership"]["buffer_rank"])  # None
```

### Check Optimality
```python
from portfolio_management.config.validation import check_optimality_warnings

config = {
    "preselection": {"top_k": 5, "lookback": 30},
    "universe": {"size": 1000},
    "cache": {"enabled": False},
}

result = check_optimality_warnings(config)
for warning in result.warnings:
    print(f"{warning.parameter}: {warning.message}")
```

## Best Practices

### 1. Review Warnings
Always review configuration warnings before running production backtests. Warnings indicate potential issues that could affect results.

### 2. Use Sensible Defaults
Start with sensible defaults and adjust based on your specific needs:
```bash
python scripts/run_backtest.py --show-defaults
```

### 3. Enable Validation in CI/CD
Use `--strict` mode in automated pipelines to catch configuration errors early:
```bash
python scripts/run_backtest.py equal_weight --strict
```

### 4. Document Deviations
If you deviate from sensible defaults, document why in your backtest configuration or comments.

### 5. Test with Small Universes First
Test new configurations with small universes before scaling to production size.

## Troubleshooting

### Common Errors

#### Error: "buffer_rank (20) must be > top_k (30)"
**Solution:** Increase buffer_rank to be greater than top_k:
```bash
--preselect-top-k=30 --membership-buffer-rank=50
```

#### Error: "Cache directory not writable"
**Solutions:**
1. Create directory: `mkdir -p .cache/backtest`
2. Check permissions: `chmod 755 .cache/backtest`
3. Specify different directory: `--cache-dir=/tmp/cache`
4. Disable caching: Remove `--enable-cache` flag

#### Error: "skip (252) must be < lookback (252)"
**Solution:** Ensure skip < lookback:
```bash
--preselect-lookback=252 --preselect-skip=1  # or any value < 252
```

#### Warning: "Fast IO requested but polars/pyarrow not installed"
**Solution:** Install dependencies:
```bash
pip install polars pyarrow
```

### FAQ

**Q: Can I disable validation entirely?**
A: Yes, use `--ignore-warnings` to suppress warnings. However, errors for invalid configurations cannot be disabled.

**Q: Why am I getting warnings for my configuration?**
A: Warnings indicate suboptimal settings. Review the suggestion to understand the recommended approach.

**Q: What's the difference between strict mode and normal mode?**
A: Normal mode displays warnings but continues. Strict mode treats warnings as errors and exits immediately.

**Q: How do I know if my configuration is good?**
A: A good configuration produces no warnings in validation. Use `--show-defaults` as a starting point.

**Q: Can I validate universe YAML files separately?**
A: Currently, validation runs during backtest execution. Standalone YAML validation is planned for a future release.

## See Also

- [Asset Selection Documentation](asset_selection.md)
- [Universe Management Documentation](universes.md)
- [Backtesting Guide](backtesting.md)
- [Membership Policy Documentation](membership_policy.md)
