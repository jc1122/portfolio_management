# Portfolio Management Examples

This directory contains complete working examples demonstrating advanced features of the portfolio management toolkit.

______________________________________________________________________

## Quick Start

```bash
# Run any example
python examples/<example_name>.py
```

______________________________________________________________________

## Examples

### 1. **S&P 500 Blue Chip Portfolio** (`sp500_blue_chips_advanced.py`)

**🎯 Best for learning advanced features**

Demonstrates sophisticated workflow:

- Filter 100 blue chip US stocks from S&P 500
- Multi-factor preselection (momentum + low-volatility) to select 30 stocks
- Membership policy to control turnover and force holding periods
- Backtest 2005-2025 with realistic transaction costs
- Compare strategies (equal-weight vs. momentum vs. combined factors)

**Features showcased:**

- ✅ Custom universe configuration (YAML)
- ✅ Quality filtering (20 years history, US markets)
- ✅ Combined factor scoring (60% momentum, 40% low-vol)
- ✅ Membership policy (reduce churn, 4-quarter minimum hold)
- ✅ Point-in-time eligibility (no lookahead bias)
- ✅ Factor caching (5-10x speedup)
- ✅ Transaction cost modeling
- ✅ Strategy comparison

**Run time:** 2-5 minutes (with test data)

**Documentation:** See `docs/advanced_features_guide.md` for detailed explanation

______________________________________________________________________

### 2. **Low-Volatility Defensive Strategy** (`lowvol_strategy.py`)

Conservative portfolio focusing on low-volatility assets.

**Strategy:**

- Select assets with lowest realized volatility
- Tight membership policy (low turnover)
- Quarterly rebalancing
- Focus on stability and drawdown minimization

**Best for:** Risk-averse investors, retirement portfolios

______________________________________________________________________

### 3. **Momentum Strategy** (`momentum_strategy.py`)

Trend-following portfolio selecting winners.

**Strategy:**

- Select assets with highest past returns
- Monthly rebalancing (more responsive)
- Higher turnover (follows trends aggressively)

**Best for:** Growth-oriented investors, tactical allocation

______________________________________________________________________

### 4. **Multi-Factor Strategy** (`multifactor_strategy.py`)

Balanced approach combining multiple factors.

**Strategy:**

- Combines momentum, value, quality factors
- Diversified across factor exposures
- Moderate turnover

**Best for:** Diversified factor exposure, institutional portfolios

______________________________________________________________________

### 5. **Batch Backtesting** (`batch_backtest.py`)

Run multiple backtests in parallel for strategy comparison.

**Features:**

- Test multiple strategies simultaneously
- Compare across different time periods
- Aggregate results for analysis

**Best for:** Strategy research, robustness testing

______________________________________________________________________

### 6. **Cache Management** (`cache_management.py`)

Demonstrates factor caching for performance optimization.

**Features:**

- Factor cache configuration
- Cache invalidation triggers
- Performance benchmarking

**Best for:** Understanding caching system, optimizing backtests

______________________________________________________________________

## Common Requirements

All examples require:

- Python 3.10+
- Installed dependencies (`pip install -r requirements.txt`)
- Price and return data (from data preparation stage)

______________________________________________________________________

## Data Requirements

Most examples expect test data in `outputs/long_history_1000/`:

- `long_history_1000_prices_daily.csv` - Daily prices
- `long_history_1000_returns_daily.csv.gz` - Daily returns

If you don't have this data, you can:

1. **Use pre-configured universes:**

   ```bash
   python scripts/manage_universes.py load core_global
   ```

1. **Prepare your own data:**

   ```bash
   python scripts/prepare_tradeable_data.py [options]
   ```

______________________________________________________________________

## Customization

Each example is fully documented and designed to be modified:

1. **Copy example:** `cp examples/sp500_blue_chips_advanced.py my_strategy.py`
1. **Modify parameters:** Adjust universe, factors, constraints
1. **Run:** `python my_strategy.py`

See inline comments for guidance.

______________________________________________________________________

## Advanced Usage

### Custom Universe

Edit the universe configuration in each example:

```python
universe_config = {
    "my_universe": {
        "filter_criteria": {
            "markets": ["NYSE", "NSQ"],
            "min_history_days": 3650,
            # ... more filters
        },
        "preselection": {
            "method": "combined",
            "momentum_weight": 0.7,  # Adjust weights
            "low_vol_weight": 0.3,
        },
        # ... more config
    }
}
```

### Preselection Tuning

Experiment with different factor combinations:

```python
# Conservative: High low-vol weight
config = PreselectionConfig(
    method=PreselectionMethod.COMBINED,
    momentum_weight=0.3,
    low_vol_weight=0.7,  # 70% defensive
)

# Aggressive: High momentum weight
config = PreselectionConfig(
    method=PreselectionMethod.COMBINED,
    momentum_weight=0.8,  # 80% trend-following
    low_vol_weight=0.2,
)
```

### Membership Policy Tuning

Control turnover and holding periods:

```python
# Tight (low turnover)
policy = MembershipPolicy(
    buffer_rank=50,            # Wide buffer
    min_holding_periods=8,     # 2 years (quarterly)
    max_turnover=0.10,         # 10% max
)

# Loose (high turnover)
policy = MembershipPolicy(
    buffer_rank=32,            # Narrow buffer
    min_holding_periods=2,     # 6 months
    max_turnover=0.40,         # 40% max
)
```

______________________________________________________________________

## Troubleshooting

### "No module named 'portfolio_management'"

**Solution:** Install dependencies:

```bash
pip install -r requirements.txt
```

### "File not found: long_history_1000_returns_daily.csv.gz"

**Solution:** Examples need test data. Either:

1. Run data preparation: `python scripts/prepare_tradeable_data.py`
1. Use pre-configured universe: `python scripts/manage_universes.py load core_global`
1. Modify example to use your data path

### "Insufficient assets in universe"

**Solution:** Lower quality requirements:

```python
"min_history_days": 1260,  # 5 years instead of 20
"min_price_rows": 1000,
```

______________________________________________________________________

## Performance Tips

1. **Enable caching:**

   ```python
   cache = FactorCache(cache_dir=Path(".cache"), enabled=True)
   ```

1. **Use fast IO:**

   ```bash
   pip install polars pyarrow
   ```

1. **Reduce universe size:**

   ```python
   "constraints": {
       "max_assets": 50,  # Smaller universe = faster
   }
   ```

______________________________________________________________________

## Documentation

- **Advanced Features Guide:** `docs/advanced_features_guide.md`
- **Preselection:** `docs/preselection.md`
- **Membership Policy:** `docs/membership_policy.md`
- **Backtesting:** `docs/backtesting.md`
- **Workflow:** `docs/workflow.md`

______________________________________________________________________

## Contributing

Have a useful example? Add it to this directory:

1. Create new file: `examples/my_example.py`
1. Add documentation at top of file
1. Follow existing example structure
1. Add entry to this README
1. Submit PR

______________________________________________________________________

**Questions?** See `docs/` directory or open an issue on GitHub.
