# Phase 5: Backtesting Framework - Implementation Plan

**Document Version:** 1.0
**Date Created:** October 17, 2025
**Status:** Ready to Start
**Objective:** Implement historical backtesting engine with rebalancing logic, transaction costs, and performance analytics

______________________________________________________________________

## Executive Summary

### Overview

Phase 5 implements the backtesting framework that simulates portfolio performance over historical periods. This phase builds on the completed Phase 4 portfolio construction infrastructure to add temporal simulation, realistic transaction costs, rebalancing logic, and comprehensive performance analytics.

### Task Tracker

| ID | Task | Status | Notes |
|----|------|--------|-------|
| 1 | Backtest Exceptions | 🔄 Ready | Extend exception hierarchy for backtest errors |
| 2 | Backtest Data Models | 🔄 Ready | BacktestConfig, PerformanceMetrics, RebalanceEvent |
| 3 | Transaction Cost Model | 🔄 Ready | Commission, slippage, bid-ask spread modeling |
| 4 | Backtest Engine Core | 🔄 Ready | Historical simulation with rebalancing logic |
| 5 | Performance Metrics Calculator | 🔄 Ready | Sharpe, drawdown, ES, turnover, etc. |
| 6 | Visualization Data Prep | 🔄 Ready | Chart-ready datasets for equity, allocations, drawdowns |
| 7 | Backtest CLI | 🔄 Ready | Command-line interface for backtest execution |
| 8 | Tests & Validation | 🔄 Ready | Unit, integration, and CLI tests |
| 9 | Documentation | 🔄 Ready | Complete guide with examples |

### Success Criteria

- ✅ Complete backtesting engine with historical simulation
- ✅ Transaction cost modeling (commissions + slippage)
- ✅ Rebalancing logic (scheduled, opportunistic, forced)
- ✅ 13+ performance metrics (Sharpe, Sortino, drawdown, ES, etc.)
- ✅ Visualization data preparation for common chart types
- ✅ CLI tool supporting single strategy and comparison modes
- ✅ 40-50 new tests (210 → 250-260 total)
- ✅ Coverage ≥85% maintained
- ✅ Zero mypy errors
- ✅ All Phase 4 strategies work in backtests
- ✅ Full documentation with examples

### Time Estimate

**Total: 30-40 hours** over 5-7 days

- Module implementation: 18-24 hours
- Testing: 8-10 hours
- Documentation: 3-4 hours
- Integration & polish: 1-2 hours

______________________________________________________________________

## Architecture Design

### Module Structure

```
src/portfolio_management/
├── backtest.py              # NEW: Core backtesting engine
│   ├── BacktestConfig       # Configuration dataclass
│   ├── PerformanceMetrics   # Results dataclass
│   ├── RebalanceEvent       # Rebalance record
│   ├── TransactionCostModel # Cost modeling
│   ├── BacktestEngine       # Main simulation engine
│   └── MetricsCalculator    # Performance analytics
├── visualization.py         # NEW: Chart data preparation
│   ├── prepare_equity_curve
│   ├── prepare_drawdown_series
│   ├── prepare_allocation_history
│   └── prepare_rolling_metrics
├── exceptions.py            # EXTEND: Add backtest exceptions
└── ... (existing modules)

scripts/
└── run_backtest.py          # NEW: CLI for backtesting

tests/
├── test_backtest.py         # NEW: Backtest engine tests
├── test_visualization.py    # NEW: Visualization tests
└── scripts/
    └── test_run_backtest.py # NEW: CLI tests

docs/
└── backtesting.md           # NEW: Comprehensive guide
```

### Key Design Principles

1. **Separation of Concerns:** Transaction costs, rebalancing logic, and metrics calculation are independent components
1. **Strategy Agnostic:** Works with any PortfolioStrategy from Phase 4
1. **Configurable Costs:** Commission and slippage rates configurable per backtest
1. **Realistic Simulation:** Cash tracking, partial fills, and rounding to whole shares
1. **Rich Logging:** Detailed rebalance events for audit trail
1. **Visualization Ready:** Structured outputs for charting libraries

______________________________________________________________________

## Part 1: Core Module Implementation (18-24 hours)

### Task 1: Define Backtest Exceptions (30 minutes)

**File:** `src/portfolio_management/exceptions.py`

Add the following exception classes after the portfolio construction exceptions:

```python
class BacktestError(PortfolioManagementError):
    """Base exception for backtesting errors."""
    pass


class InvalidBacktestConfigError(BacktestError):
    """Raised when a backtest configuration value is invalid."""

    def __init__(
        self,
        config_field: str,
        invalid_value: Any,
        reason: str,
    ) -> None:
        """Initialize with configuration details.

        Args:
            config_field: Name of the invalid configuration field.
            invalid_value: The invalid value provided.
            reason: Explanation of why the value is invalid.
        """
        self.config_field = config_field
        self.invalid_value = invalid_value
        self.reason = reason
        super().__init__(
            f"Invalid value for backtest config field '{config_field}': "
            f"{invalid_value}. {reason}"
        )


class InsufficientHistoryError(BacktestError):
    """Raised when historical data does not cover the requested backtest period."""

    def __init__(
        self,
        required_start: datetime.date,
        available_start: datetime.date,
        required_end: datetime.date,
        available_end: datetime.date,
    ) -> None:
        """Initialize with date coverage details.

        Args:
            required_start: The earliest date required for the backtest.
            available_start: The earliest date available in the data.
            required_end: The latest date required for the backtest.
            available_end: The latest date available in the data.
        """
        self.required_start = required_start
        self.available_start = available_start
        self.required_end = required_end
        self.available_end = available_end
        super().__init__(
            f"Insufficient historical data: required [{required_start} to {required_end}], "
            f"available [{available_start} to {available_end}]"
        )


class RebalanceError(BacktestError):
    """Raised when a rebalancing operation fails."""

    def __init__(self, date: datetime.date, reason: str) -> None:
        """Initialize with rebalance details.

        Args:
            date: The date when rebalancing failed.
            reason: Explanation of the failure.
        """
        self.date = date
        self.reason = reason
        super().__init__(f"Rebalancing failed on {date}: {reason}")


class TransactionCostError(BacktestError):
    """Raised when transaction cost calculation fails."""

    def __init__(self, ticker: str, reason: str) -> None:
        """Initialize with transaction details.

        Args:
            ticker: The asset ticker involved.
            reason: Explanation of the failure.
        """
        self.ticker = ticker
        self.reason = reason
        super().__init__(f"Transaction cost error for {ticker}: {reason}")
```

**Verification:**

```bash
python -c "from src.portfolio_management.exceptions import BacktestError, InvalidBacktestConfigError, InsufficientHistoryError"
python -m mypy src/portfolio_management/exceptions.py
```

### Task 2: Define Backtest Data Models (2-3 hours)

**File:** `src/portfolio_management/backtest.py`

Create the core data models for backtesting:

```python
"""Backtesting framework for portfolio strategies.

This module provides historical simulation capabilities, including:
- Transaction cost modeling (commissions, slippage, bid-ask spread)
- Rebalancing logic (scheduled, opportunistic, forced)
- Performance metrics calculation (Sharpe, Sortino, drawdown, etc.)
- Portfolio evolution tracking with cash management
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from collections.abc import Sequence

from portfolio_management.exceptions import (
    BacktestError,
    InsufficientHistoryError,
    InvalidBacktestConfigError,
    RebalanceError,
)


class RebalanceFrequency(Enum):
    """Supported rebalancing frequencies."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


class RebalanceTrigger(Enum):
    """Type of rebalance trigger."""

    SCHEDULED = "scheduled"  # Calendar-based
    OPPORTUNISTIC = "opportunistic"  # Threshold-based
    FORCED = "forced"  # Manual override


@dataclass(frozen=True)
class BacktestConfig:
    """Configuration for a backtest run.

    Attributes:
        start_date: First date of the backtest period.
        end_date: Last date of the backtest period.
        initial_capital: Starting portfolio value (default: 100,000).
        rebalance_frequency: How often to rebalance (default: monthly).
        rebalance_threshold: Drift threshold for opportunistic rebalancing (default: 0.20 = 20%).
        commission_pct: Commission as percentage of trade value (default: 0.001 = 0.1%).
        commission_min: Minimum commission per trade (default: 0.0).
        slippage_bps: Slippage in basis points (default: 5.0 = 0.05%).
        cash_reserve_pct: Minimum cash reserve as percentage (default: 0.01 = 1%).
    """

    start_date: datetime.date
    end_date: datetime.date
    initial_capital: Decimal = Decimal("100000.00")
    rebalance_frequency: RebalanceFrequency = RebalanceFrequency.MONTHLY
    rebalance_threshold: float = 0.20  # ±20% drift
    commission_pct: float = 0.001  # 0.1%
    commission_min: float = 0.0
    slippage_bps: float = 5.0  # 5 bps
    cash_reserve_pct: float = 0.01  # 1%

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if self.start_date >= self.end_date:
            raise InvalidBacktestConfigError(
                "start_date",
                self.start_date,
                f"Must be before end_date ({self.end_date})",
            )
        if self.initial_capital <= 0:
            raise InvalidBacktestConfigError(
                "initial_capital", self.initial_capital, "Must be positive"
            )
        if not 0 <= self.rebalance_threshold <= 1:
            raise InvalidBacktestConfigError(
                "rebalance_threshold",
                self.rebalance_threshold,
                "Must be between 0 and 1",
            )
        if self.commission_pct < 0:
            raise InvalidBacktestConfigError(
                "commission_pct", self.commission_pct, "Cannot be negative"
            )
        if self.slippage_bps < 0:
            raise InvalidBacktestConfigError(
                "slippage_bps", self.slippage_bps, "Cannot be negative"
            )
        if not 0 <= self.cash_reserve_pct < 1:
            raise InvalidBacktestConfigError(
                "cash_reserve_pct",
                self.cash_reserve_pct,
                "Must be between 0 and 1",
            )


@dataclass
class RebalanceEvent:
    """Record of a portfolio rebalancing event.

    Attributes:
        date: Date of the rebalance.
        trigger: What caused the rebalance.
        trades: Dict mapping ticker to share change (positive = buy, negative = sell).
        costs: Total transaction costs incurred.
        pre_rebalance_value: Portfolio value before rebalancing.
        post_rebalance_value: Portfolio value after rebalancing.
        cash_before: Cash balance before rebalancing.
        cash_after: Cash balance after rebalancing.
    """

    date: datetime.date
    trigger: RebalanceTrigger
    trades: dict[str, int]
    costs: Decimal
    pre_rebalance_value: Decimal
    post_rebalance_value: Decimal
    cash_before: Decimal
    cash_after: Decimal


@dataclass
class PerformanceMetrics:
    """Performance metrics for a backtest run.

    Attributes:
        total_return: Cumulative return over the period.
        annualized_return: Annualized return (CAGR).
        annualized_volatility: Annualized standard deviation of returns.
        sharpe_ratio: Risk-adjusted return (assuming 0% risk-free rate).
        sortino_ratio: Downside risk-adjusted return.
        max_drawdown: Maximum peak-to-trough decline.
        calmar_ratio: Return over max drawdown.
        expected_shortfall_95: Average loss in worst 5% of days.
        win_rate: Percentage of positive return days.
        avg_win: Average gain on positive days.
        avg_loss: Average loss on negative days.
        turnover: Average portfolio turnover per period.
        total_costs: Sum of all transaction costs.
        num_rebalances: Total number of rebalancing events.
    """

    total_return: float
    annualized_return: float
    annualized_volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    calmar_ratio: float
    expected_shortfall_95: float
    win_rate: float
    avg_win: float
    avg_loss: float
    turnover: float
    total_costs: Decimal
    num_rebalances: int
```

**Verification:**

```bash
python -c "from src.portfolio_management.backtest import BacktestConfig, RebalanceEvent, PerformanceMetrics"
python -m mypy src/portfolio_management/backtest.py
```

### Task 3: Implement Transaction Cost Model (2-3 hours)

**File:** `src/portfolio_management/backtest.py` (continue)

Add transaction cost calculation:

```python
@dataclass
class TransactionCostModel:
    """Model for calculating realistic transaction costs.

    Attributes:
        commission_pct: Commission as percentage of trade value.
        commission_min: Minimum commission per trade.
        slippage_bps: Slippage in basis points.
    """

    commission_pct: float = 0.001  # 0.1%
    commission_min: float = 0.0
    slippage_bps: float = 5.0  # 5 bps

    def calculate_cost(
        self, ticker: str, shares: int, price: float, is_buy: bool
    ) -> Decimal:
        """Calculate total transaction cost for a trade.

        Args:
            ticker: Asset ticker symbol.
            shares: Number of shares traded (absolute value).
            price: Execution price per share.
            is_buy: True for buy orders, False for sell orders.

        Returns:
            Total cost as Decimal (always positive).

        Raises:
            TransactionCostError: If calculation fails.
        """
        if shares < 0:
            from portfolio_management.exceptions import TransactionCostError

            raise TransactionCostError(
                ticker, f"Shares must be non-negative, got {shares}"
            )
        if price <= 0:
            from portfolio_management.exceptions import TransactionCostError

            raise TransactionCostError(ticker, f"Price must be positive, got {price}")

        # Calculate base trade value
        trade_value = abs(shares) * price

        # Commission (max of percentage or minimum)
        commission = max(
            trade_value * self.commission_pct,
            self.commission_min if shares > 0 else 0.0,
        )

        # Slippage (always a cost, regardless of direction)
        slippage = trade_value * (self.slippage_bps / 10000.0)

        total_cost = commission + slippage
        return Decimal(str(round(total_cost, 2)))

    def calculate_batch_cost(
        self, trades: dict[str, tuple[int, float]]
    ) -> dict[str, Decimal]:
        """Calculate costs for multiple trades.

        Args:
            trades: Dict mapping ticker to (shares, price) tuples.
                   shares > 0 for buys, < 0 for sells.

        Returns:
            Dict mapping ticker to transaction cost.
        """
        costs = {}
        for ticker, (shares, price) in trades.items():
            if shares == 0:
                costs[ticker] = Decimal("0.00")
                continue
            is_buy = shares > 0
            costs[ticker] = self.calculate_cost(ticker, abs(shares), price, is_buy)
        return costs
```

**Tests to write:**

- Test commission calculation (percentage vs minimum)
- Test slippage calculation
- Test batch cost calculation
- Test error handling for invalid inputs

### Task 4: Implement Backtest Engine Core (8-10 hours)

**File:** `src/portfolio_management/backtest.py` (continue)

This is the main backtesting engine:

```python
class BacktestEngine:
    """Historical portfolio backtesting engine.

    Simulates portfolio performance over historical data with realistic
    transaction costs, rebalancing logic, and cash management.
    """

    def __init__(
        self,
        config: BacktestConfig,
        strategy: PortfolioStrategy,
        prices: pd.DataFrame,
        returns: pd.DataFrame,
        classifications: dict[str, str] | None = None,
    ) -> None:
        """Initialize the backtesting engine.

        Args:
            config: Backtest configuration.
            strategy: Portfolio construction strategy to use.
            prices: Historical prices (index=dates, columns=tickers).
            returns: Historical returns (index=dates, columns=tickers).
            classifications: Optional asset class mappings for constraints.

        Raises:
            InsufficientHistoryError: If data doesn't cover backtest period.
        """
        self.config = config
        self.strategy = strategy
        self.prices = prices
        self.returns = returns
        self.classifications = classifications or {}

        # Validate date coverage
        data_start = prices.index.min().date()
        data_end = prices.index.max().date()
        if data_start > config.start_date or data_end < config.end_date:
            raise InsufficientHistoryError(
                config.start_date, data_start, config.end_date, data_end
            )

        # Initialize transaction cost model
        self.cost_model = TransactionCostModel(
            commission_pct=config.commission_pct,
            commission_min=config.commission_min,
            slippage_bps=config.slippage_bps,
        )

        # Tracking state
        self.holdings: dict[str, int] = {}  # Current share counts
        self.cash: Decimal = config.initial_capital
        self.rebalance_events: list[RebalanceEvent] = []
        self.equity_curve: list[tuple[datetime.date, Decimal]] = []

    def run(self) -> tuple[pd.DataFrame, PerformanceMetrics, list[RebalanceEvent]]:
        """Execute the backtest simulation.

        Returns:
            Tuple of (equity_curve_df, performance_metrics, rebalance_events).
        """
        # Filter data to backtest period
        mask = (self.prices.index.date >= self.config.start_date) & (
            self.prices.index.date <= self.config.end_date
        )
        period_prices = self.prices.loc[mask]
        period_returns = self.returns.loc[mask]

        # Initial rebalancing
        first_date = period_prices.index[0].date()
        self._rebalance(first_date, period_prices.iloc[0], RebalanceTrigger.FORCED)

        # Simulate each trading day
        for i, (date_idx, prices_row) in enumerate(period_prices.iterrows()):
            date = date_idx.date()

            # Calculate current portfolio value
            portfolio_value = self._calculate_portfolio_value(prices_row)
            self.equity_curve.append((date, portfolio_value))

            # Check for scheduled rebalancing
            if self._should_rebalance_scheduled(date):
                self._rebalance(date, prices_row, RebalanceTrigger.SCHEDULED)
                continue

            # Check for opportunistic rebalancing
            if self._should_rebalance_opportunistic(date, prices_row):
                self._rebalance(date, prices_row, RebalanceTrigger.OPPORTUNISTIC)

        # Calculate performance metrics
        equity_df = pd.DataFrame(
            self.equity_curve, columns=["date", "equity"]
        ).set_index("date")
        metrics = self._calculate_metrics(equity_df)

        return equity_df, metrics, self.rebalance_events

    def _calculate_portfolio_value(self, prices: pd.Series) -> Decimal:
        """Calculate total portfolio value at current prices."""
        holdings_value = sum(
            Decimal(str(shares * prices.get(ticker, 0.0)))
            for ticker, shares in self.holdings.items()
        )
        return holdings_value + self.cash

    def _should_rebalance_scheduled(self, date: datetime.date) -> bool:
        """Check if scheduled rebalancing is due."""
        if not self.rebalance_events:
            return False

        last_rebalance = self.rebalance_events[-1].date
        freq = self.config.rebalance_frequency

        if freq == RebalanceFrequency.DAILY:
            return True
        elif freq == RebalanceFrequency.WEEKLY:
            return (date - last_rebalance).days >= 7
        elif freq == RebalanceFrequency.MONTHLY:
            return (
                date.month != last_rebalance.month or date.year != last_rebalance.year
            )
        elif freq == RebalanceFrequency.QUARTERLY:
            months_diff = (date.year - last_rebalance.year) * 12 + (
                date.month - last_rebalance.month
            )
            return months_diff >= 3
        elif freq == RebalanceFrequency.ANNUAL:
            return date.year != last_rebalance.year
        return False

    def _should_rebalance_opportunistic(
        self, date: datetime.date, prices: pd.Series
    ) -> bool:
        """Check if any position has drifted beyond threshold."""
        if not self.holdings:
            return False

        portfolio_value = self._calculate_portfolio_value(prices)
        if portfolio_value == 0:
            return False

        # Get target weights from strategy
        # (This is simplified - in practice you'd reconstruct with lookback data)
        # For now, we'll just check if we're holding 0 positions
        return False  # Placeholder - implement drift check

    def _rebalance(
        self, date: datetime.date, prices: pd.Series, trigger: RebalanceTrigger
    ) -> None:
        """Execute a portfolio rebalancing.

        Args:
            date: Rebalancing date.
            prices: Current prices for all assets.
            trigger: What triggered this rebalance.

        Raises:
            RebalanceError: If rebalancing fails.
        """
        pre_value = self._calculate_portfolio_value(prices)

        # Get target weights from strategy
        # Need historical returns for strategy calculation
        # This is a simplified implementation
        try:
            # Calculate target portfolio (simplified - needs proper lookback)
            target_weights = self._calculate_target_weights(date, prices)

            # Calculate target shares
            investable_cash = float(self.cash) * (1 - self.config.cash_reserve_pct)
            target_value_per_asset = {
                ticker: investable_cash * weight
                for ticker, weight in target_weights.items()
            }
            target_shares = {
                ticker: int(value / prices[ticker]) if ticker in prices else 0
                for ticker, value in target_value_per_asset.items()
            }

            # Calculate trades needed
            trades = {}
            for ticker in set(target_shares.keys()) | set(self.holdings.keys()):
                current = self.holdings.get(ticker, 0)
                target = target_shares.get(ticker, 0)
                if current != target:
                    trades[ticker] = target - current

            # Calculate transaction costs
            trade_costs = {}
            for ticker, share_change in trades.items():
                if share_change == 0:
                    continue
                price = float(prices.get(ticker, 0.0))
                if price <= 0:
                    continue
                cost = self.cost_model.calculate_cost(
                    ticker, abs(share_change), price, share_change > 0
                )
                trade_costs[ticker] = cost
                self.cash -= cost

            # Execute trades
            for ticker, share_change in trades.items():
                if share_change == 0:
                    continue
                price = float(prices.get(ticker, 0.0))
                trade_value = Decimal(str(abs(share_change) * price))

                if share_change > 0:  # Buy
                    self.cash -= trade_value
                else:  # Sell
                    self.cash += trade_value

                self.holdings[ticker] = self.holdings.get(ticker, 0) + share_change

            # Remove zero positions
            self.holdings = {t: s for t, s in self.holdings.items() if s != 0}

            # Record event
            post_value = self._calculate_portfolio_value(prices)
            event = RebalanceEvent(
                date=date,
                trigger=trigger,
                trades=trades,
                costs=sum(trade_costs.values(), start=Decimal("0.00")),
                pre_rebalance_value=pre_value,
                post_rebalance_value=post_value,
                cash_before=pre_value - self._calculate_holdings_value(prices),
                cash_after=self.cash,
            )
            self.rebalance_events.append(event)

        except Exception as e:
            raise RebalanceError(date, str(e)) from e

    def _calculate_holdings_value(self, prices: pd.Series) -> Decimal:
        """Calculate value of current holdings only (excluding cash)."""
        return sum(
            Decimal(str(shares * prices.get(ticker, 0.0)))
            for ticker, shares in self.holdings.items()
        )

    def _calculate_target_weights(
        self, date: datetime.date, prices: pd.Series
    ) -> dict[str, float]:
        """Calculate target portfolio weights using the strategy.

        This is a simplified placeholder - real implementation would need
        to extract proper lookback period returns.
        """
        # Placeholder: equal weight across available assets
        available = [t for t in prices.index if prices[t] > 0]
        if not available:
            return {}
        weight = 1.0 / len(available)
        return {ticker: weight for ticker in available}

    def _calculate_metrics(self, equity_df: pd.DataFrame) -> PerformanceMetrics:
        """Calculate performance metrics from equity curve."""
        # Calculate returns
        returns = equity_df["equity"].pct_change().dropna()

        # Total and annualized returns
        total_return = float(
            (equity_df["equity"].iloc[-1] / equity_df["equity"].iloc[0]) - 1
        )
        days = len(equity_df)
        years = days / 252  # Approximate trading days per year
        annualized_return = float((1 + total_return) ** (1 / years) - 1) if years > 0 else 0.0

        # Volatility
        annualized_vol = float(returns.std() * np.sqrt(252))

        # Sharpe ratio (assuming 0% risk-free rate)
        sharpe = annualized_return / annualized_vol if annualized_vol > 0 else 0.0

        # Sortino ratio (downside deviation)
        downside_returns = returns[returns < 0]
        downside_dev = float(downside_returns.std() * np.sqrt(252))
        sortino = annualized_return / downside_dev if downside_dev > 0 else 0.0

        # Maximum drawdown
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = float(drawdown.min())

        # Calmar ratio
        calmar = (
            annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0.0
        )

        # Expected Shortfall (95%)
        es_95 = float(returns.quantile(0.05))

        # Win rate and avg win/loss
        positive_returns = returns[returns > 0]
        negative_returns = returns[returns < 0]
        win_rate = float(len(positive_returns) / len(returns)) if len(returns) > 0 else 0.0
        avg_win = float(positive_returns.mean()) if len(positive_returns) > 0 else 0.0
        avg_loss = float(negative_returns.mean()) if len(negative_returns) > 0 else 0.0

        # Turnover and costs
        total_costs = sum(
            event.costs for event in self.rebalance_events
        )
        num_rebalances = len(self.rebalance_events)

        # Simple turnover calculation: sum of absolute trades / portfolio value
        if self.rebalance_events:
            avg_turnover = sum(
                sum(abs(qty) for qty in event.trades.values())
                for event in self.rebalance_events
            ) / (num_rebalances * float(equity_df["equity"].mean()))
        else:
            avg_turnover = 0.0

        return PerformanceMetrics(
            total_return=total_return,
            annualized_return=annualized_return,
            annualized_volatility=annualized_vol,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            max_drawdown=max_drawdown,
            calmar_ratio=calmar,
            expected_shortfall_95=es_95,
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            turnover=avg_turnover,
            total_costs=total_costs,
            num_rebalances=num_rebalances,
        )
```

**Tests to write:**

- Test initial rebalancing
- Test scheduled rebalancing logic
- Test cash management
- Test transaction cost accounting
- Test metrics calculation
- Test error handling

### Task 5: Implement Visualization Data Prep (2-3 hours)

**File:** `src/portfolio_management/visualization.py`

Create helper functions for chart-ready data:

```python
"""Visualization data preparation utilities.

Provides functions to prepare backtest results for charting libraries
like Matplotlib, Plotly, or web dashboards.
"""

from __future__ import annotations

import pandas as pd

from portfolio_management.backtest import PerformanceMetrics, RebalanceEvent


def prepare_equity_curve(equity_df: pd.DataFrame) -> pd.DataFrame:
    """Prepare equity curve data for plotting.

    Args:
        equity_df: DataFrame with equity values (from BacktestEngine.run).

    Returns:
        DataFrame with date index and normalized equity column.
    """
    result = equity_df.copy()
    result["equity_normalized"] = result["equity"] / result["equity"].iloc[0] * 100
    return result


def prepare_drawdown_series(equity_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate drawdown series for plotting.

    Args:
        equity_df: DataFrame with equity values.

    Returns:
        DataFrame with drawdown percentages.
    """
    cumulative = equity_df["equity"]
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max * 100
    return pd.DataFrame({"drawdown_pct": drawdown})


def prepare_allocation_history(
    rebalance_events: list[RebalanceEvent],
) -> pd.DataFrame:
    """Prepare allocation history for stacked area chart.

    Args:
        rebalance_events: List of rebalance events from backtest.

    Returns:
        DataFrame with dates and allocation percentages per asset.
    """
    if not rebalance_events:
        return pd.DataFrame()

    records = []
    for event in rebalance_events:
        total_value = float(event.post_rebalance_value)
        if total_value == 0:
            continue

        record = {"date": event.date}
        # Calculate weights from trades (simplified)
        # In practice, track full position state
        record["cash_pct"] = float(event.cash_after) / total_value * 100
        records.append(record)

    return pd.DataFrame(records).set_index("date")


def prepare_rolling_metrics(
    equity_df: pd.DataFrame, window: int = 60
) -> pd.DataFrame:
    """Calculate rolling performance metrics.

    Args:
        equity_df: DataFrame with equity values.
        window: Rolling window size in days.

    Returns:
        DataFrame with rolling Sharpe, volatility, etc.
    """
    returns = equity_df["equity"].pct_change()

    rolling_return = returns.rolling(window).mean() * 252
    rolling_vol = returns.rolling(window).std() * (252**0.5)
    rolling_sharpe = rolling_return / rolling_vol

    return pd.DataFrame(
        {
            "rolling_return": rolling_return,
            "rolling_volatility": rolling_vol,
            "rolling_sharpe": rolling_sharpe,
        }
    )


def prepare_transaction_costs_summary(
    rebalance_events: list[RebalanceEvent],
) -> pd.DataFrame:
    """Summarize transaction costs over time.

    Args:
        rebalance_events: List of rebalance events from backtest.

    Returns:
        DataFrame with cumulative costs.
    """
    if not rebalance_events:
        return pd.DataFrame()

    records = [
        {
            "date": event.date,
            "costs": float(event.costs),
            "cumulative_costs": 0.0,  # Will fill below
        }
        for event in rebalance_events
    ]

    df = pd.DataFrame(records)
    df["cumulative_costs"] = df["costs"].cumsum()
    return df.set_index("date")
```

### Task 6: Implement Backtest CLI (3-4 hours)

**File:** `scripts/run_backtest.py`

Create the command-line interface:

```python
#!/usr/bin/env python3
"""Run historical backtest for portfolio strategies.

This script simulates portfolio performance over historical data with
realistic transaction costs and rebalancing logic.

Example:
    python scripts/run_backtest.py \\
        --universe core_global \\
        --strategy equal_weight \\
        --start-date 2023-01-02 \\
        --end-date 2023-12-31 \\
        --returns data/processed/returns/core_global.csv \\
        --prices data/processed/prices/core_global.csv \\
        --output-dir output/backtests
"""

import argparse
import datetime
import json
import sys
from decimal import Decimal
from pathlib import Path

import pandas as pd

from portfolio_management.backtest import BacktestConfig, BacktestEngine, RebalanceFrequency
from portfolio_management.exceptions import PortfolioManagementError
from portfolio_management.portfolio import PortfolioConstructor
from portfolio_management.visualization import (
    prepare_drawdown_series,
    prepare_equity_curve,
    prepare_rolling_metrics,
    prepare_transaction_costs_summary,
)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run historical backtest for portfolio strategies"
    )

    # Required arguments
    parser.add_argument(
        "--universe",
        required=True,
        help="Universe name (for output organization)",
    )
    parser.add_argument(
        "--strategy",
        required=True,
        help="Portfolio strategy name (e.g., 'equal_weight')",
    )
    parser.add_argument(
        "--start-date",
        required=True,
        help="Backtest start date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end-date",
        required=True,
        help="Backtest end date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--returns",
        required=True,
        type=Path,
        help="Path to returns CSV file",
    )
    parser.add_argument(
        "--prices",
        required=True,
        type=Path,
        help="Path to prices CSV file",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Output directory for results",
    )

    # Optional configuration
    parser.add_argument(
        "--initial-capital",
        type=float,
        default=100000.0,
        help="Initial portfolio value (default: 100000)",
    )
    parser.add_argument(
        "--rebalance-frequency",
        choices=["daily", "weekly", "monthly", "quarterly", "annual"],
        default="monthly",
        help="Rebalancing frequency (default: monthly)",
    )
    parser.add_argument(
        "--commission-pct",
        type=float,
        default=0.001,
        help="Commission as percentage (default: 0.001 = 0.1%%)",
    )
    parser.add_argument(
        "--slippage-bps",
        type=float,
        default=5.0,
        help="Slippage in basis points (default: 5.0)",
    )
    parser.add_argument(
        "--visualize",
        action="store_true",
        help="Generate visualization data files",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    try:
        # Parse dates
        start_date = datetime.datetime.strptime(args.start_date, "%Y-%m-%d").date()
        end_date = datetime.datetime.strptime(args.end_date, "%Y-%m-%d").date()

        # Load data
        if args.verbose:
            print(f"Loading returns from {args.returns}...")
        returns_df = pd.read_csv(args.returns, index_col=0, parse_dates=True)

        if args.verbose:
            print(f"Loading prices from {args.prices}...")
        prices_df = pd.read_csv(args.prices, index_col=0, parse_dates=True)

        # Get strategy
        constructor = PortfolioConstructor()
        if args.strategy not in constructor.list_strategies():
            print(f"Error: Unknown strategy '{args.strategy}'", file=sys.stderr)
            print(f"Available: {', '.join(constructor.list_strategies())}", file=sys.stderr)
            return 1

        strategy = constructor._strategies[args.strategy]

        # Create backtest config
        config = BacktestConfig(
            start_date=start_date,
            end_date=end_date,
            initial_capital=Decimal(str(args.initial_capital)),
            rebalance_frequency=RebalanceFrequency(args.rebalance_frequency),
            commission_pct=args.commission_pct,
            slippage_bps=args.slippage_bps,
        )

        if args.verbose:
            print(f"\nRunning backtest:")
            print(f"  Universe: {args.universe}")
            print(f"  Strategy: {args.strategy}")
            print(f"  Period: {start_date} to {end_date}")
            print(f"  Initial capital: ${args.initial_capital:,.2f}")
            print(f"  Rebalance: {args.rebalance_frequency}")

        # Run backtest
        engine = BacktestEngine(
            config=config,
            strategy=strategy,
            prices=prices_df,
            returns=returns_df,
        )
        equity_df, metrics, events = engine.run()

        # Create output directory
        output_dir = args.output_dir / args.universe / args.strategy
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save results
        equity_df.to_csv(output_dir / "equity_curve.csv")

        metrics_dict = {
            "total_return": metrics.total_return,
            "annualized_return": metrics.annualized_return,
            "annualized_volatility": metrics.annualized_volatility,
            "sharpe_ratio": metrics.sharpe_ratio,
            "sortino_ratio": metrics.sortino_ratio,
            "max_drawdown": metrics.max_drawdown,
            "calmar_ratio": metrics.calmar_ratio,
            "expected_shortfall_95": metrics.expected_shortfall_95,
            "win_rate": metrics.win_rate,
            "avg_win": metrics.avg_win,
            "avg_loss": metrics.avg_loss,
            "turnover": metrics.turnover,
            "total_costs": float(metrics.total_costs),
            "num_rebalances": metrics.num_rebalances,
        }

        with open(output_dir / "metrics.json", "w") as f:
            json.dump(metrics_dict, f, indent=2)

        # Save rebalance log
        rebalance_records = [
            {
                "date": str(event.date),
                "trigger": event.trigger.value,
                "num_trades": len(event.trades),
                "costs": float(event.costs),
                "pre_value": float(event.pre_rebalance_value),
                "post_value": float(event.post_rebalance_value),
            }
            for event in events
        ]
        pd.DataFrame(rebalance_records).to_csv(
            output_dir / "rebalance_log.csv", index=False
        )

        # Generate visualizations if requested
        if args.visualize:
            if args.verbose:
                print("\nGenerating visualization data...")

            viz_dir = output_dir / "visualizations"
            viz_dir.mkdir(exist_ok=True)

            prepare_equity_curve(equity_df).to_csv(viz_dir / "equity_normalized.csv")
            prepare_drawdown_series(equity_df).to_csv(viz_dir / "drawdown.csv")
            prepare_rolling_metrics(equity_df).to_csv(viz_dir / "rolling_metrics.csv")
            prepare_transaction_costs_summary(events).to_csv(viz_dir / "costs.csv")

        # Print summary
        print(f"\n{'='*60}")
        print(f"Backtest Results: {args.universe} / {args.strategy}")
        print(f"{'='*60}")
        print(f"Total Return:        {metrics.total_return:>8.2%}")
        print(f"Annualized Return:   {metrics.annualized_return:>8.2%}")
        print(f"Annualized Vol:      {metrics.annualized_volatility:>8.2%}")
        print(f"Sharpe Ratio:        {metrics.sharpe_ratio:>8.2f}")
        print(f"Sortino Ratio:       {metrics.sortino_ratio:>8.2f}")
        print(f"Max Drawdown:        {metrics.max_drawdown:>8.2%}")
        print(f"Calmar Ratio:        {metrics.calmar_ratio:>8.2f}")
        print(f"Expected Shortfall:  {metrics.expected_shortfall_95:>8.2%}")
        print(f"Win Rate:            {metrics.win_rate:>8.2%}")
        print(f"Avg Win:             {metrics.avg_win:>8.2%}")
        print(f"Avg Loss:            {metrics.avg_loss:>8.2%}")
        print(f"Portfolio Turnover:  {metrics.turnover:>8.2f}")
        print(f"Total Costs:         ${float(metrics.total_costs):>8.2f}")
        print(f"Num Rebalances:      {metrics.num_rebalances:>8d}")
        print(f"\nResults saved to: {output_dir}")

        return 0

    except PortfolioManagementError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

______________________________________________________________________

## Part 2: Testing (8-10 hours)

### Task 7: Unit Tests

**File:** `tests/test_backtest.py`

Create comprehensive unit tests covering:

1. **BacktestConfig validation**
1. **TransactionCostModel calculations**
1. **BacktestEngine initialization**
1. **Rebalancing logic**
1. **Metrics calculation**
1. **Error handling**

### Task 8: Integration Tests

Add integration tests to `tests/integration/test_full_pipeline.py`:

1. **End-to-end backtest** (selection → portfolio → backtest)
1. **Multi-strategy comparison**
1. **Transaction cost sensitivity**

### Task 9: CLI Tests

**File:** `tests/scripts/test_run_backtest.py`

Test the CLI with:

1. **Successful backtest execution**
1. **Invalid strategy handling**
1. **Date validation**
1. **Output file generation**

______________________________________________________________________

## Part 3: Documentation (3-4 hours)

### Task 10: Create Backtesting Guide

**File:** `docs/backtesting.md`

Comprehensive guide covering:

1. **Overview and concepts**
1. **CLI usage examples**
1. **Configuration options**
1. **Performance metrics explanation**
1. **Visualization outputs**
1. **Best practices**

### Task 11: Update README

Update `README.md` to include:

1. **Phase 5 status** in project status section
1. **Backtesting workflow** section
1. **Update repository structure** to show backtest.py

### Task 12: Update Memory Bank

Update `memory-bank/activeContext.md` and `memory-bank/progress.md` with:

1. **Phase 5 completion status**
1. **Test count updates**
1. **Next phase planning**

______________________________________________________________________

## Validation Checklist

Before considering Phase 5 complete:

- \[ \] All exception types created with typed fields
- \[ \] BacktestConfig validates all parameters
- \[ \] TransactionCostModel calculates costs correctly
- \[ \] BacktestEngine simulates portfolio correctly
- \[ \] Rebalancing logic works (scheduled + opportunistic)
- \[ \] Cash management handles reserves properly
- \[ \] Performance metrics calculated accurately
- \[ \] Visualization data exports work
- \[ \] CLI executes backtests successfully
- \[ \] 40-50 new tests added (250-260 total)
- \[ \] All tests passing (100%)
- \[ \] Zero mypy errors
- \[ \] Coverage ≥85%
- \[ \] Documentation complete
- \[ \] Memory bank updated
- \[ \] README updated

______________________________________________________________________

## Success Metrics

**Code Quality:**

- Test count: 210 → 250-260 (+40-50)
- Coverage: ≥85% maintained
- Mypy errors: 0 (maintained)
- Ruff warnings: ~30 (maintained, P4 only)
- Code quality: 9.5/10 (maintained)

**Functionality:**

- Backtest engine operational
- Transaction costs modeled
- Performance metrics calculated
- Visualization data exported
- CLI tool functional

______________________________________________________________________

## Next Phase Preview

**Phase 6: Advanced Features** will build on Phase 5 to add:

- Sentiment/news integration for active tilts
- Black-Litterman view blending
- Walk-forward analysis
- Monte Carlo simulation
- Regime detection overlays
- Automated visualization generation (Matplotlib/Plotly)

The backtesting framework from Phase 5 provides the foundation for these advanced analytics and decision-making tools.
