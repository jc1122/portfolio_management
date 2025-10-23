# Membership Policy

## Overview

The **Membership Policy** controls how assets enter and exit the portfolio during rebalancing events. It reduces portfolio churn and stabilizes holdings by applying configurable rules that override raw optimization results.

## Purpose

Without membership control, portfolio optimization can lead to:

- **High turnover**: Assets frequently entering/exiting increase transaction costs
- **Whipsaw trades**: Assets bouncing in and out due to noisy signals
- **Tax inefficiency**: Short holding periods trigger higher tax rates

Membership policy addresses these issues by applying deterministic rules to candidate portfolios.

## Architecture

### Core Components

```python
from portfolio_management.portfolio import MembershipPolicy, apply_membership_policy

# Create policy
policy = MembershipPolicy(
    buffer_rank=5,              # Rank buffer for existing holdings
    min_holding_periods=3,      # Minimum rebalance periods to hold
    max_turnover=0.30,          # Maximum 30% turnover per rebalance
    max_new_assets=5,           # Maximum 5 new assets per rebalance
    max_removed_assets=3,       # Maximum 3 removals per rebalance
)

# Apply policy during rebalancing
filtered_assets = apply_membership_policy(
    candidate_assets=["AAPL", "MSFT", "GOOGL", "META", "TSLA"],
    current_holdings={"AAPL": 100, "AMZN": 150},
    holding_periods={"AAPL": 5, "AMZN": 2},
    policy=policy,
    candidate_rankings=pd.Series([1, 2, 3, 4, 5], index=["AAPL", "MSFT", ...]),
)
```

### Policy Rules

The policy applies rules in a deterministic pipeline:

1. **Minimum Holding Periods** (Step 1)

   - Keep assets that haven't reached `min_holding_periods`
   - Prevents premature exits
   - Example: If `min_holding_periods=3`, asset must be held for at least 3 rebalances

1. **Buffer Rank Protection** (Step 2)

   - Give existing holdings a ranking advantage
   - Keep holdings ranked within `buffer_rank` positions of cutoff
   - Example: If `buffer_rank=5` and portfolio size is 20, keep holdings ranked up to 25

1. **Max New Assets** (Step 3)

   - Limit number of new entries per rebalancing
   - Prevents excessive portfolio changes
   - Applied after removing candidates that violate other rules

1. **Max Removed Assets** (Step 4)

   - Limit number of exits per rebalancing
   - Smooths portfolio transitions
   - Keeps lowest-ranked removals if limit exceeded

### Turnover Calculation

Turnover is calculated as:

```
turnover = (additions + removals) / portfolio_size
```

Where:

- `additions` = number of new assets entering
- `removals` = number of assets exiting
- `portfolio_size` = number of current holdings

Example: If portfolio has 20 assets, adds 4, removes 2:

```
turnover = (4 + 2) / 20 = 0.30 (30%)
```

## Usage

### Command Line Interface

Enable membership policy via CLI flags:

```bash
# Basic usage with default policy
python scripts/run_backtest.py equal_weight \
    --membership-enabled \
    --start-date 2020-01-01 \
    --end-date 2023-12-31

# Custom policy parameters
python scripts/run_backtest.py risk_parity \
    --membership-enabled \
    --membership-buffer-rank 10 \
    --membership-min-hold 5 \
    --membership-max-turnover 0.25 \
    --membership-max-new 3 \
    --membership-max-removed 2
```

### Available Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--membership-enabled` | flag | False | Enable membership policy |
| `--membership-buffer-rank` | int | 5 | Rank buffer for existing holdings |
| `--membership-min-hold` | int | 3 | Minimum holding periods |
| `--membership-max-turnover` | float | None | Maximum turnover (0-1) |
| `--membership-max-new` | int | None | Maximum new assets per rebalance |
| `--membership-max-removed` | int | None | Maximum removals per rebalance |

### Programmatic Usage

```python
from portfolio_management.portfolio import MembershipPolicy
from portfolio_management.backtesting import BacktestConfig, BacktestEngine

# Create policy
policy = MembershipPolicy(
    buffer_rank=5,
    min_holding_periods=3,
    max_turnover=0.30,
    max_new_assets=5,
    max_removed_assets=3,
)

# Add to backtest config
config = BacktestConfig(
    start_date=date(2020, 1, 1),
    end_date=date(2023, 12, 31),
    initial_capital=Decimal("100000"),
    rebalance_frequency=RebalanceFrequency.MONTHLY,
    membership_policy=policy,  # Add policy here
)

# Run backtest
engine = BacktestEngine(config=config, strategy=strategy, prices=prices, returns=returns)
equity_curve, metrics, events = engine.run()
```

### Factory Methods

**Default Policy** - Balanced settings for moderate turnover control:

```python
policy = MembershipPolicy.default()
# Equivalent to:
# MembershipPolicy(buffer_rank=5, min_holding_periods=3)
```

**Disabled Policy** - No membership restrictions:

```python
policy = MembershipPolicy.disabled()
# Equivalent to:
# MembershipPolicy(buffer_rank=0, min_holding_periods=0)
```

## Configuration in Universe YAML

*Note: Universe YAML support is planned but not yet implemented.*

Future syntax:

```yaml
universes:
  my_universe:
    assets: [AAPL, MSFT, GOOGL, ...]
    membership_policy:
      buffer_rank: 5
      min_holding_periods: 3
      max_turnover: 0.30
      max_new_assets: 5
      max_removed_assets: 3
```

## Design Decisions

### Why Deterministic Pipeline?

The policy applies rules in a fixed order to ensure reproducible results. Alternative approaches (scoring, optimization) would add complexity and unpredictability.

### Why Buffer Rank Instead of Absolute Threshold?

Buffer rank adapts to portfolio size and prevents cliff effects. An asset ranked 21 (just outside top 20) shouldn't be immediately removed if it was previously held.

### Why Track Holding Periods?

Short holding periods often result from noise rather than signal. Forcing minimum holds reduces transaction costs and tax impacts.

### Integration with Preselection

Membership policy requires ranked candidates, which depends on the **Preselection** feature (Issue #31). Until preselection is implemented:

- Rankings can be derived from optimization weights
- Simple rank-by-weight approach serves as placeholder
- Full preselection will enable more sophisticated ranking strategies

## Performance Impact

Membership policy has minimal computational overhead:

- **Time complexity**: O(n) where n = number of candidates
- **Space complexity**: O(n) for tracking holding periods
- **Typical execution**: \<1ms per rebalance event

## Testing

Comprehensive test coverage (23 tests):

```bash
# Run membership policy tests
pytest tests/portfolio/test_membership.py -v

# Example tests:
# - test_min_holding_periods_enforcement
# - test_buffer_rank_protection
# - test_max_new_assets_limit
# - test_max_removed_assets_limit
# - test_turnover_limit_respected
# - test_combined_policies
```

## Limitations

1. **Requires Preselection**: Currently depends on optimization weights for ranking
1. **No Universe YAML Support**: Configuration must be done via CLI or programmatically
1. **No Backward Compatibility**: Existing backtests will need explicit policy configuration

## Future Enhancements

- \[ \] Universe YAML configuration support (Issue #35)
- \[ \] Integration with Preselection module (Issue #31)
- \[ \] Adaptive buffer rank based on market volatility
- \[ \] Time-decay for holding period requirements
- \[ \] Asset-specific membership rules (e.g., by sector)

## Related Documentation

- [Asset Selection](asset_selection.md) - Selection strategies
- [Portfolio Construction](portfolio_construction.md) - Optimization strategies
- [Backtesting](backtesting.md) - Running backtests
- [Universes](universes.md) - Universe configuration

## See Also

- Issue #35: Membership Policy Implementation
- Issue #31: Preselection Strategy (dependency)
- `src/portfolio_management/portfolio/membership.py` - Implementation
- `tests/portfolio/test_membership.py` - Test suite
