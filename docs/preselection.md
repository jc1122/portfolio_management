# Asset Preselection

## Overview

The asset preselection module provides a deterministic, factor-based approach to reducing the investment universe size before portfolio optimization. This is particularly useful for:

- Large universes (100+ assets) where optimization becomes computationally expensive
- Factor-tilted strategies that want to emphasize momentum or low-volatility characteristics
- Multi-stage portfolio construction workflows

**Key Feature**: All preselection logic uses only data available up to the rebalance date, ensuring no lookahead bias.

## Supported Methods

### 1. Momentum

Selects assets with the highest cumulative returns over a lookback period.

**Formula**: Cumulative return = (1+r₁) × (1+r₂) × ... × (1+rₙ) - 1

**Parameters**:

- `lookback`: Number of periods to look back (default: 252 days = 1 year)
- `skip`: Number of most recent periods to skip (default: 1)
  - Common practice: skip most recent day to avoid short-term reversals
  - Example: with `lookback=252, skip=1`, uses 12-month return excluding last day (aka "12-1 momentum")

**Example**:

```python
from portfolio_management.portfolio import Preselection, PreselectionConfig, PreselectionMethod

config = PreselectionConfig(
    method=PreselectionMethod.MOMENTUM,
    top_k=30,
    lookback=252,  # 1 year
    skip=1,        # Skip most recent day
)
preselection = Preselection(config)
selected_assets = preselection.select_assets(returns, rebalance_date)
```

### 2. Low-Volatility

Selects assets with the lowest realized volatility over a lookback period.

**Formula**: Inverse volatility = 1 / std(returns)

Higher scores indicate lower volatility (more attractive for defensive strategies).

**Parameters**:

- `lookback`: Number of periods for volatility calculation (default: 252 days)

**Example**:

```python
config = PreselectionConfig(
    method=PreselectionMethod.LOW_VOL,
    top_k=30,
    lookback=252,
)
preselection = Preselection(config)
selected_assets = preselection.select_assets(returns, rebalance_date)
```

### 3. Combined

Combines momentum and low-volatility factors using weighted Z-scores.

**Process**:

1. Compute momentum scores for all assets
1. Compute low-volatility scores for all assets
1. Standardize each factor to Z-scores (mean=0, std=1)
1. Combine: `combined_score = w₁ × momentum_z + w₂ × low_vol_z`
1. Select top-K assets by combined score

**Parameters**:

- `momentum_weight`: Weight for momentum factor (default: 0.5)
- `low_vol_weight`: Weight for low-volatility factor (default: 0.5)
- Weights must sum to 1.0

**Example**:

```python
config = PreselectionConfig(
    method=PreselectionMethod.COMBINED,
    top_k=30,
    lookback=252,
    momentum_weight=0.6,  # 60% momentum
    low_vol_weight=0.4,   # 40% low-vol
)
preselection = Preselection(config)
selected_assets = preselection.select_assets(returns, rebalance_date)
```

## Deterministic Tie-Breaking

When multiple assets have identical scores at the cutoff point, ties are broken alphabetically by asset symbol. This ensures:

- Reproducible results across runs
- Consistent behavior in backtests
- No random selection bias

**Example**:
If selecting top-5 assets and ranks 4-7 all have score 0.15:

1. Asset D (score 0.20)
1. Asset A (score 0.18)
1. Asset B (score 0.16)
1. **Asset C (score 0.15)** ← Selected (first alphabetically)
1. Asset E (score 0.15) ← Not selected
1. Asset F (score 0.15) ← Not selected
1. Asset G (score 0.14)

## No Lookahead Guarantee

The preselection engine strictly uses only data available up to (but not including) the rebalance date:

```python
# Correct: Uses only data before rebalance date
rebalance_date = date(2023, 6, 1)
selected = preselection.select_assets(returns, rebalance_date)
# Uses returns from start through 2023-05-31

# Also correct: Without date, uses all available data
selected = preselection.select_assets(returns)
```

This prevents lookahead bias in backtests.

## CLI Usage

### Basic Command

Run a backtest with momentum preselection selecting top 30 assets:

```bash
python scripts/run_backtest.py equal_weight \
    --universe config/universes.yaml:core_global \
    --start-date 2020-01-01 \
    --end-date 2023-12-31 \
    --preselect-method momentum \
    --preselect-top-k 30
```

### Advanced Examples

#### Example 1: Combined Factor with Custom Weights

Run mean-variance optimization with 60% momentum, 40% low-volatility:

```bash
python scripts/run_backtest.py mean_variance \
    --universe config/universes.yaml:satellite_factor \
    --start-date 2020-01-01 \
    --end-date 2023-12-31 \
    --preselect-method combined \
    --preselect-top-k 30 \
    --preselect-lookback 252 \
    --preselect-skip 1 \
    --preselect-momentum-weight 0.6 \
    --preselect-low-vol-weight 0.4 \
    --rebalance-frequency monthly
```

**Expected Output**: Backtest results showing ~30 assets selected per month, with performance metrics.

#### Example 2: Defensive Low-Volatility Strategy

Select top 25 lowest-volatility assets quarterly:

```bash
python scripts/run_backtest.py risk_parity \
    --universe config/universes.yaml:core_global \
    --start-date 2018-01-01 \
    --end-date 2023-12-31 \
    --preselect-method low_vol \
    --preselect-top-k 25 \
    --preselect-lookback 252 \
    --rebalance-frequency quarterly
```

**Expected Output**: Lower volatility portfolio with more stable asset selection.

#### Example 3: Aggressive Momentum with Monthly Skip

Classic "12-1 momentum" strategy:

```bash
python scripts/run_backtest.py equal_weight \
    --universe config/universes.yaml:satellite_factor \
    --start-date 2015-01-01 \
    --end-date 2023-12-31 \
    --preselect-method momentum \
    --preselect-top-k 40 \
    --preselect-lookback 252 \
    --preselect-skip 21 \
    --rebalance-frequency monthly
```

**Expected Output**: Higher turnover, momentum-tilted portfolio excluding most recent month.

#### Example 4: Large Universe Reduction

Reduce 1000-asset universe to 50 for optimization:

```bash
python scripts/run_backtest.py mean_variance \
    --universe config/universes.yaml:long_history_1000 \
    --start-date 2010-01-01 \
    --end-date 2023-12-31 \
    --preselect-method combined \
    --preselect-top-k 50 \
    --preselect-lookback 252 \
    --preselect-momentum-weight 0.5 \
    --preselect-low-vol-weight 0.5 \
    --rebalance-frequency monthly \
    --verbose
```

**Expected Output**: Dramatic speedup (hours → minutes), comparable performance to full universe.

### CLI Parameters Reference

| Parameter | Type | Description | Default | Valid Values |
|-----------|------|-------------|---------|--------------|
| `--preselect-method` | str | Factor method | None | `momentum`, `low_vol`, `combined` |
| `--preselect-top-k` | int | Number of assets to select | None | 1-N (N=universe size) |
| `--preselect-lookback` | int | Lookback period (days) | 252 | 30-1260 |
| `--preselect-skip` | int | Skip recent N days | 1 | 0-lookback |
| `--preselect-momentum-weight` | float | Momentum weight (combined) | 0.5 | 0.0-1.0 |
| `--preselect-low-vol-weight` | float | Low-vol weight (combined) | 0.5 | 0.0-1.0 |

**Notes**:
- If `--preselect-method` is not specified, preselection is disabled
- Weights must sum to 1.0 when using `combined` method
- `--verbose` flag provides factor score statistics in output

## Universe Configuration

Preselection can be configured directly in universe YAML files:

```yaml
universes:
  satellite_factor:
    description: "Factor sleeve with momentum/low-vol preselection"
    filter_criteria:
      # ... asset selection criteria ...
    preselection:
      method: "combined"           # momentum, low_vol, or combined
      top_k: 25                    # Select top 25 assets
      lookback: 252                # 1 year lookback
      skip: 1                      # Skip most recent day
      momentum_weight: 0.5         # 50% momentum
      low_vol_weight: 0.5          # 50% low-volatility
      min_periods: 60              # Minimum data required
```

### Loading from Universe

When using `manage_universes.py` or loading universes programmatically, preselection is automatically configured:

```python
from portfolio_management.assets.universes import UniverseConfigLoader
from portfolio_management.portfolio import create_preselection_from_dict

# Load universe
config_loader = UniverseConfigLoader()
universes = config_loader.load_config(Path("config/universes.yaml"))
universe_def = universes["satellite_factor"]

# Create preselection if configured
if universe_def.preselection:
    preselection = create_preselection_from_dict(universe_def.preselection)
```

## Integration with Backtesting

Preselection integrates seamlessly with the backtesting engine:

```python
from portfolio_management.backtesting import BacktestEngine, BacktestConfig
from portfolio_management.portfolio import (
    EqualWeightStrategy,
    Preselection,
    PreselectionConfig,
    PreselectionMethod,
)

# Configure preselection
preselection_config = PreselectionConfig(
    method=PreselectionMethod.MOMENTUM,
    top_k=30,
    lookback=252,
)
preselection = Preselection(preselection_config)

# Run backtest with preselection
engine = BacktestEngine(
    config=backtest_config,
    strategy=EqualWeightStrategy(),
    prices=prices,
    returns=returns,
    preselection=preselection,  # Add preselection here
)
equity_curve, metrics, events = engine.run()
```

The engine automatically applies preselection at each rebalance:

1. Compute factor scores using data up to rebalance date
1. Select top-K assets
1. Pass filtered returns to portfolio strategy
1. Optimize portfolio on selected subset only

**No changes to portfolio strategies are required** - preselection is applied transparently before strategy execution.

## Use Cases

### 1. Large Universe Optimization

Problem: Optimizing 500+ assets is computationally expensive.

Solution: Use preselection to reduce to manageable size (e.g., 50 assets).

```python
config = PreselectionConfig(
    method=PreselectionMethod.COMBINED,
    top_k=50,
    lookback=252,
)
```

### 2. Momentum-Tilted Portfolio

Problem: Want to emphasize recent winners without explicit momentum overlay.

Solution: Preselect high-momentum assets, then optimize weights.

```python
config = PreselectionConfig(
    method=PreselectionMethod.MOMENTUM,
    top_k=30,
    lookback=252,
    skip=21,  # Skip most recent month
)
```

### 3. Low-Volatility Strategy

Problem: Want defensive portfolio with minimal drawdowns.

Solution: Preselect low-volatility assets, then apply equal-weight or risk-parity.

```python
config = PreselectionConfig(
    method=PreselectionMethod.LOW_VOL,
    top_k=25,
    lookback=252,
)
```

### 4. Balanced Factor Exposure

Problem: Want both momentum and stability.

Solution: Use combined method with equal weights.

```python
config = PreselectionConfig(
    method=PreselectionMethod.COMBINED,
    top_k=30,
    lookback=252,
    momentum_weight=0.5,
    low_vol_weight=0.5,
)
```

## Performance Considerations

### Computational Complexity

**Factor Computation**: All factors exhibit linear O(N × L) complexity:

- **Momentum**: O(N × L) - cumulative product over lookback
- **Low-volatility**: O(N × L) - standard deviation computation  
- **Combined**: O(N × L) - both factors computed, then combined with Z-scores

**Typical Timings** (from benchmarks on GitHub Actions runner):

| Universe Size | Lookback | Momentum | Low-Vol | Combined | Memory |
|---------------|----------|----------|---------|----------|--------|
| 100 assets | 252 days | 2.3ms | 2.5ms | 4.8ms | 2MB |
| 500 assets | 252 days | 11.5ms | 12.8ms | 24.3ms | 10MB |
| 1000 assets | 252 days | 24.6ms | 27.1ms | 51.7ms | 20MB |
| 5000 assets | 252 days | 125.8ms | 138.5ms | 264.3ms | 100MB |

**Key Finding**: Preselection adds \<0.1 second per rebalance for typical universes (500-1000 assets).

**Lookback Impact**: Minimal performance variance (\<10%) across lookback periods 30-504 days.

### Memory Usage

Preselection operates on returns DataFrame directly without creating large intermediate structures:

- **Formula**: N assets × L periods × 8 bytes (float64)
- **Examples**:
  - 500 assets × 252 days ≈ 1 MB
  - 1000 assets × 252 days ≈ 2 MB  
  - 5000 assets × 252 days ≈ 10 MB

**Memory Efficiency**: Peak usage \<200MB for 5000 assets (validated in profiling).

### Optimization Impact

Reducing universe from N to K assets dramatically improves portfolio optimization:

**Mean-Variance Optimization**: O(N³) → O(K³)
- 500 → 50 assets: **1000× speedup**
- 1000 → 100 assets: **1000× speedup**
- 5000 → 500 assets: **1000× speedup**

**Risk Parity**: O(N²) → O(K²)
- 500 → 50 assets: **100× speedup**
- 1000 → 100 assets: **100× speedup**

**Real-World Impact**: For large universes (1000+ assets), preselection can reduce backtest time from hours to minutes.

### Scalability

Based on comprehensive profiling (`benchmarks/benchmark_preselection.py`):

- ✅ **Linear scaling**: Confirmed O(N) complexity through N=5000
- ✅ **No bottlenecks**: Dominant cost is factor computation (70-80% of time)
- ✅ **Multiple rebalances**: 24 monthly rebalances on 1000 assets \<2 seconds total
- ✅ **Stable performance**: No performance degradation with repeated calls

**Recommendation**: Safe to use with universes up to 5000 assets without caching.

## Edge Cases

### Insufficient Data

If an asset has fewer than `min_periods` returns:

- Factor score is set to NaN
- Asset is excluded from selection

### All NaN Scores

If all assets have insufficient data:

- Returns empty list
- Backtest will fail (no assets to invest in)

### Top-K Exceeds Universe Size

If `top_k` > number of valid assets:

- Returns all valid assets
- No error raised

### Tied Scores at Cutoff

Multiple assets with identical scores at position K:

- Ties broken alphabetically by symbol
- First K (alphabetically) selected

## Tuning Guidance

### Lookback Period Selection

**Rule of Thumb**: Align lookback with rebalance frequency for stability.

| Rebalance Frequency | Recommended Lookback | Rationale |
|---------------------|---------------------|-----------|
| Weekly | 63 days (3 months) | Captures short-term trends |
| Monthly | 252 days (1 year) | Standard annual momentum |
| Quarterly | 504 days (2 years) | Long-term factor stability |
| Annual | 756 days (3 years) | Very stable, less responsive |

**Trade-offs**:
- **Shorter lookback** (60-126 days): More responsive, higher turnover, noisier signals
- **Longer lookback** (252-504 days): More stable, lower turnover, slower adaptation
- **Impact on performance**: Lookback has minimal computational impact (\<10% variance)

### Top-K Selection Guidelines

**Universe Size vs. Top-K Recommendations**:

| Universe Size | Conservative K | Moderate K | Aggressive K | Impact |
|---------------|----------------|------------|--------------|--------|
| 100-200 | 15-25 | 25-40 | 40-60 | High concentration risk if too low |
| 200-500 | 20-35 | 35-60 | 60-100 | Balance optimization benefit vs. diversification |
| 500-1000 | 30-50 | 50-100 | 100-200 | Optimization speedup: O(N³) → O(K³) |
| 1000+ | 50-75 | 75-150 | 150-300 | Maximum computational savings |

**Considerations**:
- **Too small** (K\<20): High concentration risk, few diversification benefits
- **Too large** (K>100 for small universe): Loses preselection benefit, minimal speedup
- **Sweet spot**: K ≈ 10-30% of universe size for most strategies

### Skip Period Tuning

**Common Skip Configurations**:

| Skip Days | Use Case | Evidence |
|-----------|----------|----------|
| 0 | No skip | Use most recent data, may include noise |
| 1 | Standard (default) | Skip last day to avoid short-term reversals |
| 5 | Weekly skip | Skip last week for cleaner signals |
| 21 | Monthly skip | Classic "12-1 momentum" (12 months excluding last month) |

**Research-backed recommendation**: Skip 1-21 days for momentum strategies to avoid short-term mean reversion.

### Combined Factor Weights

**Common Weight Configurations**:

| Momentum Weight | Low-Vol Weight | Strategy Type | Characteristics |
|-----------------|----------------|---------------|-----------------|
| 0.5 | 0.5 | Balanced | Equal factor exposure |
| 0.6-0.7 | 0.3-0.4 | Growth-oriented | Emphasis on momentum |
| 0.3-0.4 | 0.6-0.7 | Defensive | Emphasis on low-volatility |
| 0.8+ | 0.2- | Aggressive momentum | Maximum return chase |
| 0.2- | 0.8+ | Maximum defense | Minimal drawdowns |

**Tuning process**:
1. Start with equal weights (0.5/0.5)
2. Run backtest to measure turnover and performance
3. Adjust weights based on risk tolerance
4. Validate with out-of-sample data

### Validation Best Practices

1. **Backtest First**:
   - Run with and without preselection
   - Compare performance metrics (Sharpe ratio, turnover, max drawdown)
   - Measure computational time savings

2. **Monitor Turnover**:
   - Calculate asset turnover at each rebalance
   - High turnover (>50% per rebalance) may indicate:
     * Lookback too short
     * Top-K too small
     * Factor signals too noisy
   - Consider adding membership policy for turnover control

3. **Performance Impact**:
   - Expected computational savings: 10-100x for large universes
   - Memory usage: Minimal (factor scores \<1MB per 1000 assets)
   - Time per rebalance: \<0.1s for 1000 assets with typical lookback

4. **Robustness Checks**:
   - Test with different market conditions (bull, bear, sideways)
   - Verify no lookahead bias (use rebalance_date parameter)
   - Check factor score distributions for extremes/outliers

## Limitations

1. **Factor Timing**: Preselection assumes factors persist across rebalance periods. May not work well with short rebalance frequencies.

1. **Transaction Costs**: Preselection adds turnover (assets enter/exit selected set). Factor this into cost model.

1. **Survivorship Bias**: Preselection on recent performance can amplify survivorship bias if dead assets aren't in the universe.

1. **Strategy Compatibility**: Works best with:

   - Equal-weight (no optimization needed)
   - Risk parity (scales well to smaller universes)
   - Mean-variance (benefits from universe reduction)

## Testing

Comprehensive test suite covers:

- Factor computation accuracy
- Deterministic tie-breaking
- No-lookahead validation
- Edge cases (NaN, insufficient data, ties)
- Integration with strategies

Run tests:

```bash
pytest tests/portfolio/test_preselection.py -v
```

## References

### Academic Research

- **Momentum**: Jegadeesh & Titman (1993) - "Returns to Buying Winners and Selling Losers"
  - Foundational momentum research showing 12-month returns predict future performance
  - Skip period (1 month) important to avoid short-term reversals

- **Low-Volatility**: Ang, Hodrick, Xing & Zhang (2006) - "The Cross-Section of Volatility and Expected Returns"
  - Documents low-volatility anomaly (defensive assets outperform high-volatility)
  - Theory: volatility-averse investors drive up prices of stable assets

- **Combined Factors**: Asness, Moskowitz & Pedersen (2013) - "Value and Momentum Everywhere"
  - Shows momentum and value work together across asset classes
  - Factor combination improves risk-adjusted returns

### Performance Documentation

- **Benchmarks**: See [`docs/performance/preselection_profiling.md`](performance/preselection_profiling.md)
  - Detailed profiling results
  - Scalability analysis (100-5000 assets)
  - Memory usage characterization
  - Optimization recommendations

- **Integration Tests**: `tests/portfolio/test_preselection.py`
  - Factor computation accuracy tests
  - Deterministic behavior validation
  - Edge case handling

- **Edge Cases**: `tests/integration/test_preselection_edge_cases.py`
  - Insufficient data scenarios
  - Tie-breaking validation
  - Lookback boundary conditions

### Related Documentation

- [Portfolio Construction](portfolio_construction.md) - Strategy implementation details
- [Backtesting](backtesting.md) - Full backtest workflow with preselection
- [Membership Policy](membership_policy_guide.md) - Turnover control to complement preselection
- [Universe Management](universes.md) - Universe configuration with preselection blocks
- [Fast I/O](fast_io.md) - Optional speedups for loading large datasets
- [Statistics Caching](statistics_caching.md) - Cache preselection factor scores
