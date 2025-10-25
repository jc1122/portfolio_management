"""Core data models for the backtesting framework.

This module defines the data structures used to configure, run, and analyze
backtests. It includes models for configuration settings, event tracking, and
performance results, ensuring a standardized and type-safe interface across
the backtesting engine.

Key Classes:
    - BacktestConfig: A dataclass for all backtest configuration settings.
    - RebalanceEvent: A record of a single portfolio rebalancing event.
    - PerformanceMetrics: A container for all calculated performance metrics.
    - RebalanceFrequency: An Enum for specifying rebalancing frequency.
    - RebalanceTrigger: An Enum for the cause of a rebalancing event.

Usage Example:
    >>> from datetime import date
    >>> from decimal import Decimal
    >>> from portfolio_management.backtesting.models import (
    ...     BacktestConfig, RebalanceFrequency, RebalanceEvent, RebalanceTrigger
    ... )
    >>>
    >>> # 1. Configure a backtest
    >>> config = BacktestConfig(
    ...     start_date=date(2022, 1, 1),
    ...     end_date=date(2023, 12, 31),
    ...     rebalance_frequency=RebalanceFrequency.QUARTERLY,
    ...     commission_pct=0.001
    ... )
    >>> print(f"Backtest will run from {config.start_date} to {config.end_date}.")
    Backtest will run from 2022-01-01 to 2023-12-31.
    >>>
    >>> # 2. Record a rebalancing event
    >>> event = RebalanceEvent(
    ...     date=date(2022, 4, 1),
    ...     trigger=RebalanceTrigger.SCHEDULED,
    ...     trades={'AAPL': 100, 'MSFT': -50},
    ...     costs=Decimal('25.50'),
    ...     pre_rebalance_value=Decimal('105000.00'),
    ...     post_rebalance_value=Decimal('104974.50'),
    ...     cash_before=Decimal('10000.00'),
    ...     cash_after=Decimal('2474.50')
    ... )
    >>> print(f"Rebalanced on {event.date}, incurred ${event.costs} in costs.")
    Rebalanced on 2022-04-01, incurred $25.50 in costs.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from portfolio_management.core.exceptions import InvalidBacktestConfigError


class RebalanceFrequency(Enum):
    """Enumeration for supported rebalancing frequencies."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


class RebalanceTrigger(Enum):
    """Enumeration for the cause of a rebalance event."""

    SCHEDULED = "scheduled"  # Calendar-based (e.g., monthly)
    OPPORTUNISTIC = "opportunistic"  # Threshold-based (e.g., weight drift)
    FORCED = "forced"  # Manual override or initial portfolio setup


@dataclass(frozen=True)
class BacktestConfig:
    """Configuration for a backtest run.

    This dataclass holds all the parameters needed to define a backtest simulation.
    It is immutable to ensure that the configuration cannot be changed during a run.

    Attributes:
        start_date (datetime.date): The first date of the backtest period.
        end_date (datetime.date): The last date of the backtest period.
        initial_capital (Decimal): The starting portfolio value.
        rebalance_frequency (RebalanceFrequency): How often to rebalance.
        rebalance_threshold (float): The weight drift threshold for opportunistic rebalancing.
        commission_pct (float): Commission as a percentage of trade value.
        commission_min (float): Minimum commission fee per trade.
        slippage_bps (float): Slippage cost in basis points.
        cash_reserve_pct (float): The minimum percentage of the portfolio to hold as cash.
        lookback_periods (int): The rolling window size for parameter estimation (e.g., returns).
        use_pit_eligibility (bool): If True, enables point-in-time eligibility filtering.
        min_history_days (int): The minimum calendar days of history for PIT eligibility.
        min_price_rows (int): The minimum number of price observations for PIT eligibility.
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
    use_pit_eligibility: bool = False  # Enable point-in-time eligibility filtering
    min_history_days: int = 252  # Minimum days for eligibility (1 year)
    min_price_rows: int = 252  # Minimum price rows for eligibility

    def __post_init__(self) -> None:
        """Validate configuration values after initialization."""
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
        if self.min_history_days <= 0:
            raise InvalidBacktestConfigError(
                config_field="min_history_days",
                invalid_value=self.min_history_days,
                reason="Must be positive",
            )
        if self.min_price_rows <= 0:
            raise InvalidBacktestConfigError(
                config_field="min_price_rows",
                invalid_value=self.min_price_rows,
                reason="Must be positive",
            )


@dataclass
class RebalanceEvent:
    """A detailed record of a single portfolio rebalancing event.

    This dataclass captures the state of the portfolio immediately before and
    after a rebalance, along with details of the trades executed and costs incurred.

    Attributes:
        date (datetime.date): The date on which the rebalance occurred.
        trigger (RebalanceTrigger): The reason for the rebalance (e.g., scheduled, forced).
        trades (dict[str, int]): A mapping of asset tickers to the number of shares
            traded. Positive values are buys, negative values are sells.
        costs (Decimal): The total transaction costs (commission + slippage) for the event.
        pre_rebalance_value (Decimal): The total portfolio value before rebalancing.
        post_rebalance_value (Decimal): The total portfolio value after rebalancing.
        cash_before (Decimal): The cash balance before the rebalance.
        cash_after (Decimal): The cash balance after executing trades and paying costs.
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
    """A container for the performance metrics of a backtest run.

    This dataclass holds all the key statistics calculated from a backtest's
    equity curve, providing a comprehensive summary of the strategy's performance
    and risk characteristics.

    Attributes:
        total_return (float): The cumulative return over the entire backtest period.
        annualized_return (float): The annualized geometric mean return (CAGR).
        annualized_volatility (float): The annualized standard deviation of daily returns.
        sharpe_ratio (float): The risk-adjusted return (assumes a 0% risk-free rate).
        sortino_ratio (float): The downside risk-adjusted return.
        max_drawdown (float): The largest peak-to-trough decline in portfolio value.
        calmar_ratio (float): The annualized return divided by the max drawdown.
        expected_shortfall_95 (float): The average loss on the worst 5% of days (CVaR).
        win_rate (float): The percentage of days with positive returns.
        avg_win (float): The average return on days with positive returns.
        avg_loss (float): The average return on days with negative returns.
        turnover (float): The average portfolio turnover per rebalancing period.
        total_costs (Decimal): The sum of all transaction costs incurred.
        num_rebalances (int): The total number of rebalancing events.
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
    final_value: Decimal = Decimal("0.0")