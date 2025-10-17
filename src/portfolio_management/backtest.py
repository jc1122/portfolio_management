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
    
    from portfolio_management.portfolio import PortfolioStrategy

from portfolio_management.exceptions import (
    BacktestError,
    InsufficientHistoryError,
    InvalidBacktestConfigError,
    RebalanceError,
    TransactionCostError,
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
            raise TransactionCostError(
                transaction_type=f"{'buy' if is_buy else 'sell'} {ticker}",
                amount=float(shares),
                reason=f"Shares must be non-negative, got {shares}",
            )
        if price <= 0:
            raise TransactionCostError(
                transaction_type=f"{'buy' if is_buy else 'sell'} {ticker}",
                amount=price,
                reason=f"Price must be positive, got {price}",
            )

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
        self.prices = prices.copy()
        self.returns = returns.copy()
        self.classifications = classifications or {}

        # Validate date coverage
        data_start = self.prices.index.min()
        data_end = self.prices.index.max()
        
        if pd.isna(data_start) or pd.isna(data_end):
            raise InsufficientHistoryError(
                required_start=config.start_date,
                available_start=config.start_date,
                asset_ticker="N/A (no data)",
            )
        
        data_start_date = data_start.date()
        data_end_date = data_end.date()
        
        if data_start_date > config.start_date or data_end_date < config.end_date:
            raise InsufficientHistoryError(
                required_start=config.start_date,
                available_start=data_start_date,
                asset_ticker=f"data_end={data_end_date}",
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
        self.equity_curve: list[tuple[datetime.date, float]] = []

    def run(self) -> tuple[pd.DataFrame, PerformanceMetrics, list[RebalanceEvent]]:
        """Execute the backtest simulation.

        Returns:
            Tuple of (equity_curve_df, performance_metrics, rebalance_events).
        """
        # Filter data to backtest period
        mask = (self.prices.index.date >= self.config.start_date) & (
            self.prices.index.date <= self.config.end_date
        )
        period_prices = self.prices.loc[mask].copy()
        period_returns = self.returns.loc[mask].copy()

        if len(period_prices) == 0:
            raise InsufficientHistoryError(
                required_start=self.config.start_date,
                available_start=self.config.start_date,
                asset_ticker="No data in period",
            )

        # Initial rebalancing  
        first_date = period_prices.index[0].date()
        # Use returns for initial rebalance (need at least strategy min periods)
        initial_lookback = max(1, self.strategy.min_history_periods)
        self._rebalance(
            first_date, 
            period_returns.iloc[:initial_lookback],
            period_prices.iloc[:initial_lookback],
            RebalanceTrigger.FORCED
        )

        # Simulate each trading day
        for i in range(len(period_prices)):
            date_idx = period_prices.index[i]
            date = date_idx.date()
            prices_row = period_prices.iloc[i]

            # Calculate current portfolio value
            portfolio_value = self._calculate_portfolio_value(prices_row)
            self.equity_curve.append((date, float(portfolio_value)))

            # Check for scheduled rebalancing
            if self._should_rebalance_scheduled(date):
                lookback_returns = period_returns.iloc[:i+1]
                lookback_prices = period_prices.iloc[:i+1]
                self._rebalance(date, lookback_returns, lookback_prices, RebalanceTrigger.SCHEDULED)

        # Calculate performance metrics
        equity_df = pd.DataFrame(
            self.equity_curve, columns=["date", "equity"]
        ).set_index("date")
        metrics = self._calculate_metrics(equity_df)

        return equity_df, metrics, self.rebalance_events

    def _calculate_portfolio_value(self, prices: pd.Series) -> Decimal:
        """Calculate total portfolio value at current prices."""
        holdings_value = Decimal("0")
        for ticker, shares in self.holdings.items():
            if ticker in prices.index and not pd.isna(prices[ticker]):
                price = Decimal(str(float(prices[ticker])))
                holdings_value += Decimal(str(shares)) * price
        return holdings_value + self.cash

    def _should_rebalance_scheduled(self, date: datetime.date) -> bool:
        """Check if scheduled rebalancing is due."""
        if not self.rebalance_events:
            return False

        last_rebalance = self.rebalance_events[-1].date
        freq = self.config.rebalance_frequency

        if freq == RebalanceFrequency.DAILY:
            return (date - last_rebalance).days >= 1
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

    def _rebalance(
        self,
        date: datetime.date,
        historical_returns: pd.DataFrame,
        historical_prices: pd.DataFrame,
        trigger: RebalanceTrigger,
    ) -> None:
        """Execute a portfolio rebalancing.

        Args:
            date: Rebalancing date.
            historical_returns: Historical returns up to this point.
            historical_prices: Historical prices up to this point.
            trigger: What triggered this rebalance.

        Raises:
            RebalanceError: If rebalancing fails.
        """
        try:
            # Get current prices for this date (last row of prices)
            date_prices = historical_prices.iloc[-1] if len(historical_prices) > 0 else pd.Series()
            
            # Calculate current portfolio value
            pre_value = self._calculate_portfolio_value(date_prices)

            # Import here to avoid circular dependency
            from portfolio_management.portfolio import PortfolioConstraints

            # Get target weights from strategy using historical returns
            if len(historical_returns) < self.strategy.min_history_periods:
                # Not enough history yet, skip rebalance
                return

            constraints = PortfolioConstraints(
                max_weight=0.25,
                min_weight=0.0,
                max_equity_exposure=0.90,
                min_bond_exposure=0.10,
            )

            # Build asset class series if we have classifications
            asset_classes = None
            if self.classifications:
                asset_classes = pd.Series(self.classifications)

            # Construct target portfolio
            portfolio = self.strategy.construct(
                returns=historical_returns,
                constraints=constraints,
                asset_classes=asset_classes,
            )
            target_weights = portfolio.weights

            # Calculate investable cash (keeping reserve)
            investable_cash = float(self.cash) * (1 - self.config.cash_reserve_pct)
            total_target_value = float(pre_value) * (1 - self.config.cash_reserve_pct)

            # Calculate target shares for each asset
            target_shares: dict[str, int] = {}
            for ticker in target_weights.index:
                if ticker not in date_prices.index or pd.isna(date_prices[ticker]):
                    continue
                price = float(date_prices[ticker])
                if price <= 0:
                    continue
                target_value = total_target_value * float(target_weights[ticker])
                target_shares[ticker] = int(target_value / price)

            # Calculate trades needed
            trades: dict[str, int] = {}
            all_tickers = set(target_shares.keys()) | set(self.holdings.keys())
            
            for ticker in all_tickers:
                current = self.holdings.get(ticker, 0)
                target = target_shares.get(ticker, 0)
                if current != target:
                    trades[ticker] = target - current

            # Calculate transaction costs
            total_cost = Decimal("0")
            for ticker, share_change in trades.items():
                if share_change == 0:
                    continue
                if ticker not in date_prices.index or pd.isna(date_prices[ticker]):
                    continue
                price = float(date_prices[ticker])
                if price <= 0:
                    continue
                    
                cost = self.cost_model.calculate_cost(
                    ticker, abs(share_change), price, share_change > 0
                )
                total_cost += cost

            # Check if we have enough cash for buys + costs
            total_buys = Decimal("0")
            for ticker, share_change in trades.items():
                if share_change > 0:  # Buy
                    if ticker not in date_prices.index or pd.isna(date_prices[ticker]):
                        continue
                    price = Decimal(str(float(date_prices[ticker])))
                    total_buys += Decimal(str(share_change)) * price

            if total_buys + total_cost > self.cash:
                # Scale back trades to fit cash constraints
                scale_factor = float(self.cash * Decimal("0.95")) / float(total_buys + total_cost)
                trades = {
                    ticker: int(shares * scale_factor)
                    for ticker, shares in trades.items()
                }

            # Execute trades
            for ticker, share_change in trades.items():
                if share_change == 0:
                    continue
                if ticker not in date_prices.index or pd.isna(date_prices[ticker]):
                    continue
                price = float(date_prices[ticker])
                if price <= 0:
                    continue

                # Calculate cost for this trade
                cost = self.cost_model.calculate_cost(
                    ticker, abs(share_change), price, share_change > 0
                )
                
                trade_value = Decimal(str(abs(share_change) * price))

                if share_change > 0:  # Buy
                    self.cash -= trade_value
                    self.cash -= cost
                else:  # Sell
                    self.cash += trade_value
                    self.cash -= cost

                # Update holdings
                self.holdings[ticker] = self.holdings.get(ticker, 0) + share_change

            # Remove zero positions
            self.holdings = {t: s for t, s in self.holdings.items() if s != 0}

            # Calculate post-rebalance value
            post_value = self._calculate_portfolio_value(date_prices)

            # Record event
            event = RebalanceEvent(
                date=date,
                trigger=trigger,
                trades=trades,
                costs=total_cost,
                pre_rebalance_value=pre_value,
                post_rebalance_value=post_value,
                cash_before=pre_value - self._calculate_holdings_value(date_prices),
                cash_after=self.cash,
            )
            self.rebalance_events.append(event)

        except Exception as e:
            raise RebalanceError(
                rebalance_date=date,
                error_type=type(e).__name__,
                context={"message": str(e)},
            ) from e

    def _calculate_holdings_value(self, prices: pd.Series) -> Decimal:
        """Calculate value of current holdings only (excluding cash)."""
        holdings_value = Decimal("0")
        for ticker, shares in self.holdings.items():
            if ticker in prices.index and not pd.isna(prices[ticker]):
                price = Decimal(str(float(prices[ticker])))
                holdings_value += Decimal(str(shares)) * price
        return holdings_value

    def _calculate_metrics(self, equity_df: pd.DataFrame) -> PerformanceMetrics:
        """Calculate performance metrics from equity curve.
        
        Args:
            equity_df: DataFrame with equity values indexed by date.
            
        Returns:
            PerformanceMetrics with calculated statistics.
        """
        if len(equity_df) < 2:
            # Not enough data for meaningful metrics
            return PerformanceMetrics(
                total_return=0.0,
                annualized_return=0.0,
                annualized_volatility=0.0,
                sharpe_ratio=0.0,
                sortino_ratio=0.0,
                max_drawdown=0.0,
                calmar_ratio=0.0,
                expected_shortfall_95=0.0,
                win_rate=0.0,
                avg_win=0.0,
                avg_loss=0.0,
                turnover=0.0,
                total_costs=sum((e.costs for e in self.rebalance_events), Decimal("0")),
                num_rebalances=len(self.rebalance_events),
            )

        # Calculate returns
        returns = equity_df["equity"].pct_change().dropna()
        
        if len(returns) == 0:
            return PerformanceMetrics(
                total_return=0.0,
                annualized_return=0.0,
                annualized_volatility=0.0,
                sharpe_ratio=0.0,
                sortino_ratio=0.0,
                max_drawdown=0.0,
                calmar_ratio=0.0,
                expected_shortfall_95=0.0,
                win_rate=0.0,
                avg_win=0.0,
                avg_loss=0.0,
                turnover=0.0,
                total_costs=sum((e.costs for e in self.rebalance_events), Decimal("0")),
                num_rebalances=len(self.rebalance_events),
            )

        # Total and annualized returns
        total_return = float(
            (equity_df["equity"].iloc[-1] / equity_df["equity"].iloc[0]) - 1
        )
        days = len(equity_df)
        years = days / 252  # Approximate trading days per year
        annualized_return = (
            float((1 + total_return) ** (1 / years) - 1) if years > 0 else 0.0
        )

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
        calmar = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0.0

        # Expected Shortfall (95%)
        es_95 = float(returns.quantile(0.05)) if len(returns) > 0 else 0.0

        # Win rate and avg win/loss
        positive_returns = returns[returns > 0]
        negative_returns = returns[returns < 0]
        win_rate = (
            float(len(positive_returns) / len(returns)) if len(returns) > 0 else 0.0
        )
        avg_win = float(positive_returns.mean()) if len(positive_returns) > 0 else 0.0
        avg_loss = float(negative_returns.mean()) if len(negative_returns) > 0 else 0.0

        # Turnover and costs
        total_costs = sum((event.costs for event in self.rebalance_events), Decimal("0"))
        num_rebalances = len(self.rebalance_events)

        # Simple turnover calculation: sum of absolute trades / avg portfolio value
        if self.rebalance_events and not equity_df["equity"].empty:
            total_trade_volume = sum(
                sum(abs(qty) for qty in event.trades.values())
                for event in self.rebalance_events
            )
            avg_portfolio_value = float(equity_df["equity"].mean())
            avg_turnover = (
                total_trade_volume / (num_rebalances * avg_portfolio_value)
                if num_rebalances > 0 and avg_portfolio_value > 0
                else 0.0
            )
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
