# Backtesting Framework Guide

## Table of Contents

1. [Overview](#overview)
1. [Quick Start](#quick-start)
1. [Core Concepts](#core-concepts)
1. [API Reference](#api-reference)
1. [CLI Usage](#cli-usage)
1. [Examples](#examples)
1. [Performance Metrics](#performance-metrics)
1. [Advanced Usage](#advanced-usage)
1. [Troubleshooting](#troubleshooting)

## Overview

The backtesting framework provides a comprehensive historical simulation system for portfolio strategies. It supports:

- **Multiple Strategies**: Equal-weight, risk parity, mean-variance optimization
- **Flexible Rebalancing**: Daily, weekly, monthly, quarterly, or annual
- **Realistic Costs**: Commission and slippage modeling
- **Performance Metrics**: 14 key metrics including Sharpe ratio, drawdown, etc.
- **Visualization Data**: Pre-calculated data for chart generation
- **CLI Interface**: Easy-to-use command-line tools

## Quick Start

### Python API

```python
from portfolio_management.backtest import BacktestConfig, BacktestEngine
from portfolio_management.portfolio import EqualWeightStrategy
from datetime import date
from decimal import Decimal
import pandas as pd

# Load your data
prices = pd.read_csv("prices.csv", index_col=0, parse_dates=True)
returns = pd.read_csv("returns.csv", index_col=0, parse_dates=True)

# Configure backtest
config = BacktestConfig(
    start_date=date(2020, 1, 1),
    end_date=date(2023, 12, 31),
    initial_capital=Decimal("100000"),
    rebalance_frequency=RebalanceFrequency.MONTHLY,
    commission_pct=0.001,  # 0.1%
    slippage_bps=5.0,  # 5 basis points
)

# Run backtest
engine = BacktestEngine(
    config=config,
    strategy=EqualWeightStrategy(),
    prices=prices,
    returns=returns,
)

equity_curve, metrics, events = engine.run()

# Access results
print(f"Total Return: {metrics.total_return:.2%}")
print(f"Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
print(f"Max Drawdown: {metrics.max_drawdown:.2%}")
print(f"Number of Rebalances: {metrics.num_rebalances}")
```

### Command Line

```bash
python scripts/run_backtest.py equal_weight \
  --start-date 2020-01-01 \
  --end-date 2023-12-31 \
  --initial-capital 100000 \
  --rebalance-frequency monthly \
  --commission-pct 0.001 \
  --slippage-bps 5
```

## Core Concepts

### BacktestConfig

Configuration object for backtest parameters:

```python
@dataclass
class BacktestConfig:
    start_date: datetime.date  # Backtest start date
    end_date: datetime.date    # Backtest end date
    initial_capital: Decimal = Decimal("100000.00")  # Starting capital
    rebalance_frequency: RebalanceFrequency = RebalanceFrequency.MONTHLY
    rebalance_threshold: float = 0.20  # Drift tolerance for opportunistic rebalancing
    commission_pct: float = 0.001      # Commission as % of trade value
    commission_min: float = 0.0        # Minimum commission per trade
    slippage_bps: float = 5.0          # Slippage in basis points
    cash_reserve_pct: float = 0.01     # Minimum cash reserve %
```

**Validation Rules**:

- `start_date` must be before `end_date`
- `initial_capital` must be positive
- `rebalance_threshold` must be between 0 and 1
- `cash_reserve_pct` must be between 0 and 1

### RebalanceFrequency

Enum for rebalancing frequency:

```python
class RebalanceFrequency(Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
```

### RebalanceTrigger

Enum for rebalance trigger type:

```python
class RebalanceTrigger(Enum):
    SCHEDULED = "scheduled"         # Calendar-based
    OPPORTUNISTIC = "opportunistic" # Threshold-based (drift)
    FORCED = "forced"               # Manual override (initial)
```

### RebalanceEvent

Record of a portfolio rebalancing:

```python
@dataclass
class RebalanceEvent:
    date: datetime.date
    trigger: RebalanceTrigger
    trades: dict[str, int]          # ticker -> share change
    costs: Decimal                  # transaction costs
    pre_rebalance_value: Decimal    # portfolio value before
    post_rebalance_value: Decimal   # portfolio value after
    cash_before: Decimal
    cash_after: Decimal
```

### PerformanceMetrics

Results of a backtest simulation:

```python
@dataclass
class PerformanceMetrics:
    total_return: float             # Cumulative return
    annualized_return: float        # CAGR
    annualized_volatility: float    # Annualized std dev
    sharpe_ratio: float             # Risk-adjusted return
    sortino_ratio: float            # Downside-adjusted return
    max_drawdown: float             # Peak-to-trough decline
    calmar_ratio: float             # Return / Max Drawdown
    expected_shortfall_95: float    # Average of worst 5% days
    win_rate: float                 # % of positive days
    avg_win: float                  # Average gain on up days
    avg_loss: float                 # Average loss on down days
    turnover: float                 # Average portfolio turnover
    total_costs: Decimal            # Total transaction costs
    num_rebalances: int             # Number of rebalancing events
```

## API Reference

### BacktestEngine

Main simulation engine.

**Constructor**:

```python
def __init__(
    self,
    config: BacktestConfig,
    strategy: PortfolioStrategy,
    prices: pd.DataFrame,  # index=dates, columns=tickers
    returns: pd.DataFrame, # index=dates, columns=tickers
    classifications: dict[str, str] | None = None,
) -> None:
```

**run() Method**:

```python
def run(self) -> tuple[pd.DataFrame, PerformanceMetrics, list[RebalanceEvent]]:
    """
    Execute the backtest simulation.

    Returns:
        equity_curve: DataFrame with daily equity values
        metrics: PerformanceMetrics object with results
        events: List of RebalanceEvent objects
    """
```

### TransactionCostModel

Transaction cost calculator.

**Constructor**:

```python
def __init__(
    self,
    commission_pct: float = 0.001,
    commission_min: float = 0.0,
    slippage_bps: float = 5.0,
) -> None:
```

**calculate_cost() Method**:

```python
def calculate_cost(
    self,
    ticker: str,
    shares: int,
    price: float,
    is_buy: bool,
) -> Decimal:
    """
    Calculate cost for a single trade.

    Args:
        ticker: Asset ticker symbol
        shares: Number of shares (absolute value)
        price: Execution price per share
        is_buy: True for buy, False for sell

    Returns:
        Total cost as Decimal
    """
```

**calculate_batch_cost() Method**:

```python
def calculate_batch_cost(
    self,
    trades: dict[str, tuple[int, float]],
) -> dict[str, Decimal]:
    """
    Calculate costs for multiple trades.

    Args:
        trades: Dict mapping ticker to (shares, price)

    Returns:
        Dict mapping ticker to cost
    """
```

## CLI Usage

### Basic Syntax

```bash
python scripts/run_backtest.py <strategy> [options]
```

### Required Arguments

- `strategy`: Strategy name (equal_weight, risk_parity, mean_variance)

### Date Options

```bash
--start-date YYYY-MM-DD     # Backtest start date (required)
--end-date YYYY-MM-DD       # Backtest end date (required)
```

### Capital Options

```bash
--initial-capital AMOUNT    # Starting capital (default: 100000)
```

### Rebalancing Options

```bash
--rebalance-frequency FREQ  # daily|weekly|monthly|quarterly|annual (default: monthly)
--rebalance-threshold PCT   # Drift threshold 0-1 (default: 0.20)
```

### Cost Options

```bash
--commission-pct PCT        # Commission % (default: 0.001)
--commission-min AMOUNT     # Minimum commission (default: 0)
--slippage-bps BPS          # Slippage in bps (default: 5)
--cash-reserve-pct PCT      # Minimum cash % (default: 0.01)
```

### Data Options

```bash
--universe-path FILE        # YAML universe definition
--universe-name NAME        # Universe name to select
--prices-path FILE          # CSV with prices
--returns-path FILE         # CSV with returns
```

### Output Options

```bash
--output-dir DIR            # Output directory (default: results/)
--save-trades               # Save trade history
--verbose                   # Detailed output
```

### Examples

```bash
# Basic monthly rebalance
python scripts/run_backtest.py equal_weight \
  --start-date 2020-01-01 --end-date 2023-12-31

# Quarterly with costs
python scripts/run_backtest.py risk_parity \
  --start-date 2020-01-01 --end-date 2023-12-31 \
  --rebalance-frequency quarterly \
  --commission-pct 0.001 --slippage-bps 5

# With universe and full output
python scripts/run_backtest.py mean_variance \
  --universe-name SP500 \
  --initial-capital 500000 \
  --save-trades --verbose
```

## Examples

### Example 1: Simple Monthly Rebalance

```python
from portfolio_management.backtest import (
    BacktestConfig,
    BacktestEngine,
    RebalanceFrequency,
)
from portfolio_management.portfolio import EqualWeightStrategy
from datetime import date
from decimal import Decimal
import pandas as pd

# Load data
prices = pd.read_csv("prices.csv", index_col=0, parse_dates=True)
returns = pd.read_csv("returns.csv", index_col=0, parse_dates=True)

# Simple config
config = BacktestConfig(
    start_date=date(2020, 1, 1),
    end_date=date(2023, 12, 31),
)

# Run backtest
engine = BacktestEngine(
    config=config,
    strategy=EqualWeightStrategy(),
    prices=prices,
    returns=returns,
)

equity_curve, metrics, events = engine.run()

# Print results
print(f"Starting Value: $100,000")
print(f"Ending Value: ${equity_curve['equity'].iloc[-1]:,.0f}")
print(f"Total Return: {metrics.total_return:.2%}")
print(f"Annualized Return: {metrics.annualized_return:.2%}")
print(f"Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
print(f"Max Drawdown: {metrics.max_drawdown:.2%}")
print(f"Number of Rebalances: {metrics.num_rebalances}")
```

### Example 2: Risk Parity with Costs

```python
from portfolio_management.backtest import (
    BacktestConfig,
    BacktestEngine,
    RebalanceFrequency,
)
from portfolio_management.portfolio import RiskParityStrategy
from datetime import date
from decimal import Decimal

config = BacktestConfig(
    start_date=date(2020, 1, 1),
    end_date=date(2023, 12, 31),
    initial_capital=Decimal("500000"),
    rebalance_frequency=RebalanceFrequency.QUARTERLY,
    commission_pct=0.001,      # 0.1%
    commission_min=10.0,       # $10 minimum
    slippage_bps=5.0,          # 5 bps
)

engine = BacktestEngine(
    config=config,
    strategy=RiskParityStrategy(),
    prices=prices,
    returns=returns,
)

equity_curve, metrics, events = engine.run()

print(f"Total Transaction Costs: ${metrics.total_costs:,.2f}")
print(f"Cost as % of Returns: {metrics.total_costs / (metrics.total_return * 500000):.2%}")
```

### Example 3: Analyzing Rebalance Events

```python
equity_curve, metrics, events = engine.run()

print(f"Total Rebalances: {len(events)}")
for i, event in enumerate(events[:5], 1):  # First 5 events
    print(f"\nRebalance {i}:")
    print(f"  Date: {event.date}")
    print(f"  Trigger: {event.trigger.value}")
    print(f"  Trades: {event.trades}")
    print(f"  Costs: ${event.costs:,.2f}")
    print(f"  Pre-Value: ${event.pre_rebalance_value:,.0f}")
    print(f"  Post-Value: ${event.post_rebalance_value:,.0f}")
```

### Example 4: Comparing Strategies

```python
from portfolio_management.portfolio import (
    EqualWeightStrategy,
    RiskParityStrategy,
    MeanVarianceStrategy,
)

strategies = [
    ("Equal Weight", EqualWeightStrategy()),
    ("Risk Parity", RiskParityStrategy()),
    ("Mean Variance", MeanVarianceStrategy()),
]

results = {}
for name, strategy in strategies:
    engine = BacktestEngine(
        config=config,
        strategy=strategy,
        prices=prices,
        returns=returns,
    )
    _, metrics, _ = engine.run()
    results[name] = metrics

# Compare
for name, metrics in results.items():
    print(f"\n{name}:")
    print(f"  Return: {metrics.total_return:.2%}")
    print(f"  Sharpe: {metrics.sharpe_ratio:.2f}")
    print(f"  Drawdown: {metrics.max_drawdown:.2%}")
```

## Performance Metrics

### Return Metrics

**Total Return**

- Cumulative return over entire backtest period
- Formula: (Ending Value - Starting Value) / Starting Value

**Annualized Return (CAGR)**

- Compound annual growth rate
- Formula: (Ending Value / Starting Value)^(1/years) - 1

### Risk Metrics

**Annualized Volatility**

- Annualized standard deviation of returns
- Formula: daily_std_dev * sqrt(252)

**Max Drawdown**

- Maximum peak-to-trough percentage decline
- Represents worst single continuous loss

**Drawdown Duration**

- Length of time from peak to recovery

### Risk-Adjusted Return Metrics

**Sharpe Ratio**

- Excess return per unit of risk
- Formula: (annualized_return - risk_free_rate) / volatility
- Assumes 0% risk-free rate

**Sortino Ratio**

- Similar to Sharpe but only penalizes downside
- Only uses negative returns for volatility

**Calmar Ratio**

- Return per unit of drawdown risk
- Formula: annualized_return / abs(max_drawdown)

### Trading Metrics

**Win Rate**

- Percentage of days with positive returns
- Example: 55% = 55% of trading days had gains

**Average Win**

- Average gain on winning days

**Average Loss**

- Average loss on losing days

**Profit Factor**

- Total wins / Total losses (derived from above)

### Cost Metrics

**Total Transaction Costs**

- Sum of all commissions and slippage

**Turnover**

- Average portfolio turnover per rebalancing period
- Measures trading activity

**Expected Shortfall (95%)**

- Average loss in the worst 5% of days
- Also called Conditional Value at Risk (CVaR)

## Advanced Usage

### Custom Asset Classifications

```python
classifications = {
    "AAPL": "TECH",
    "JPM": "FINANCE",
    "XOM": "ENERGY",
    # ...
}

engine = BacktestEngine(
    config=config,
    strategy=strategy,
    prices=prices,
    returns=returns,
    classifications=classifications,
)
```

### Constraints Integration

```python
from portfolio_management.portfolio import PortfolioConstraints

# Constraints are used within the strategy
config = BacktestConfig(...)

# Strategy automatically respects constraints
strategy = MeanVarianceStrategy()
engine = BacktestEngine(
    config=config,
    strategy=strategy,
    prices=prices,
    returns=returns,
)
```

### Visualization Data

```python
from portfolio_management.visualization import prepare_equity_curve, prepare_drawdown_series

equity_curve, metrics, events = engine.run()

# Prepare visualization data
viz_equity = prepare_equity_curve(equity_curve)
viz_drawdown = prepare_drawdown_series(equity_curve)

# Export for plotting
viz_equity.to_csv("equity_curve.csv")
viz_drawdown.to_csv("drawdown.csv")
```

## Troubleshooting

### "InsufficientHistoryError"

**Problem**: Backtest period not covered by data\
**Solution**: Ensure prices and returns cover the entire backtest period

```python
# Check data coverage
print(f"Data Start: {prices.index.min()}")
print(f"Data End: {prices.index.max()}")
print(f"Backtest Start: {config.start_date}")
print(f"Backtest End: {config.end_date}")
```

### "InvalidBacktestConfigError"

**Problem**: Invalid configuration\
**Solution**: Verify configuration values

```python
# Valid config example
config = BacktestConfig(
    start_date=date(2020, 1, 1),      # Before end_date
    end_date=date(2023, 12, 31),      # After start_date
    initial_capital=Decimal("100000"), # Positive
    rebalance_threshold=0.20,          # Between 0 and 1
    cash_reserve_pct=0.01,             # Between 0 and 1
)
```

### "RebalanceError"

**Problem**: Error during portfolio rebalancing\
**Solution**: Check strategy compatibility and constraints

```python
# Ensure strategy works with asset universe
strategy = EqualWeightStrategy()
# Verify enough history for strategy
print(f"Min History: {strategy.min_history_periods} days")
```

### Negative Equity Curve

**Problem**: Portfolio goes negative\
**Solution**: Check transaction costs and volatility

```python
# Review costs
print(f"Total Costs: ${metrics.total_costs:,.2f}")
print(f"Cost Impact: {float(metrics.total_costs) / float(config.initial_capital):.2%}")

# Consider reducing leverage or costs
config = BacktestConfig(
    commission_pct=0.0005,  # Reduce commission
    slippage_bps=2.0,       # Reduce slippage
)
```

### Performance Issues

**Problem**: Backtest runs slowly\
**Solution**: Optimize data and reduce frequency

```python
# Use fewer assets
prices = prices[['AAPL', 'MSFT', 'GOOGL']]
returns = returns[['AAPL', 'MSFT', 'GOOGL']]

# Use lower rebalancing frequency
config = BacktestConfig(
    rebalance_frequency=RebalanceFrequency.QUARTERLY,
)
```

## Best Practices

1. **Use Realistic Costs**: Include typical commissions and slippage
1. **Sufficient History**: Ensure strategy has enough data for initialization
1. **Monitor Drawdown**: Consider investor psychology and risk tolerance
1. **Test Multiple Periods**: Validate across different market environments
1. **Validate Results**: Compare with industry benchmarks
1. **Document Assumptions**: Record all configuration choices
1. **Use Constraints**: Apply realistic portfolio constraints
1. **Track Costs**: Monitor impact of transaction costs

## Performance Tips

- Use monthly or quarterly rebalancing for efficiency
- Consider daily only for high-volume testing
- Use constraint-based strategies for faster computation
- Minimize data precision (avoid extreme precision needs)
- Cache results for repeated analysis

## Further Reading

- [Portfolio Construction Guide](portfolio_construction.md)
- [Returns Calculation](returns.md)
- [Universe Management](universes.md)
