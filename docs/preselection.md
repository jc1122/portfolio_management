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

```bash
python scripts/run_backtest.py equal_weight \
    --preselect-method momentum \
    --preselect-top-k 30
```

### Full Options

```bash
python scripts/run_backtest.py mean_variance \
    --preselect-method combined \
    --preselect-top-k 30 \
    --preselect-lookback 252 \
    --preselect-skip 1 \
    --preselect-momentum-weight 0.6 \
    --preselect-low-vol-weight 0.4
```

### CLI Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--preselect-method` | Method: `momentum`, `low_vol`, or `combined` | None (disabled) |
| `--preselect-top-k` | Number of assets to select | None (disabled) |
| `--preselect-lookback` | Lookback period (days) | 252 |
| `--preselect-skip` | Skip most recent N days | 1 |
| `--preselect-momentum-weight` | Momentum weight (combined only) | 0.5 |
| `--preselect-low-vol-weight` | Low-vol weight (combined only) | 0.5 |

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

- **Momentum**: O(N × L) where N = assets, L = lookback
- **Low-volatility**: O(N × L)
- **Combined**: O(N × L) (both factors computed in parallel)

For typical parameters (N=500, L=252), preselection adds \<1 second per rebalance.

### Memory Usage

Preselection operates on the returns DataFrame directly without creating large intermediate structures. Memory usage is proportional to:

- Number of assets × Lookback period × 8 bytes (float64)
- Example: 500 assets × 252 days ≈ 1 MB

### Optimization Impact

Reducing universe from N to K assets:

- Mean-variance optimization: O(N³) → O(K³)
- Risk parity: O(N²) → O(K²)

Example: 500 → 50 assets = 1000× speedup for mean-variance.

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

## Best Practices

1. **Lookback Period**:

   - Use 252 days (1 year) for annual rebalancing
   - Use 63 days (3 months) for quarterly rebalancing
   - Align lookback with rebalance frequency

1. **Skip Period**:

   - Always skip at least 1 day (avoid short-term noise)
   - For momentum, skip 1-21 days (1 day to 1 month)

1. **Top-K Selection**:

   - Too small (K\<20): High concentration risk
   - Too large (K>100): Loses preselection benefit
   - Sweet spot: 20-50 assets for most strategies

1. **Combined Weights**:

   - Equal (0.5/0.5): Balanced approach
   - Momentum-heavy (0.7/0.3): Growth-oriented
   - Vol-heavy (0.3/0.7): Defensive

1. **Validation**:

   - Always test preselection in backtest first
   - Compare vs. no preselection to measure impact
   - Check turnover (high turnover = higher costs)

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

- **Momentum**: Jegadeesh & Titman (1993) - "Returns to Buying Winners and Selling Losers"
- **Low-Volatility**: Ang, Hodrick, Xing & Zhang (2006) - "The Cross-Section of Volatility and Expected Returns"
- **Combined Factors**: Asness, Moskowitz & Pedersen (2013) - "Value and Momentum Everywhere"

## See Also

- [Portfolio Construction](portfolio_construction.md) - Strategy implementation details
- [Backtesting](backtesting.md) - Full backtest workflow
- [Universe Management](universes.md) - Universe configuration and loading
