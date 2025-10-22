"""Core data models for backtesting framework.

This module contains configuration, event tracking, and results models.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from portfolio_management.core.exceptions import InvalidBacktestConfigError


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
    lookback_periods: int = (
        252  # Rolling window for parameter estimation (252 = 1 year)
    )

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if self.start_date >= self.end_date:
            raise InvalidBacktestConfigError(
                config_field="start_date",
                invalid_value=self.start_date,
                reason=f"Must be before end_date ({self.end_date})",
            )
        if self.initial_capital <= 0:
            raise InvalidBacktestConfigError(
                config_field="initial_capital",
                invalid_value=self.initial_capital,
                reason="Must be positive",
            )
        if not 0 <= self.rebalance_threshold <= 1:
            raise InvalidBacktestConfigError(
                config_field="rebalance_threshold",
                invalid_value=self.rebalance_threshold,
                reason="Must be between 0 and 1",
            )
        if self.commission_pct < 0:
            raise InvalidBacktestConfigError(
                config_field="commission_pct",
                invalid_value=self.commission_pct,
                reason="Cannot be negative",
            )
        if self.slippage_bps < 0:
            raise InvalidBacktestConfigError(
                config_field="slippage_bps",
                invalid_value=self.slippage_bps,
                reason="Cannot be negative",
            )
        if not 0 <= self.cash_reserve_pct < 1:
            raise InvalidBacktestConfigError(
                config_field="cash_reserve_pct",
                invalid_value=self.cash_reserve_pct,
                reason="Must be between 0 and 1",
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
