"""Core backtesting engine for historical portfolio simulation.

This module provides the BacktestEngine class that orchestrates portfolio
simulation over historical data with rebalancing and transaction costs.
"""

from __future__ import annotations

import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from portfolio_management.portfolio import PortfolioStrategy

from portfolio_management.backtesting.models import (
    BacktestConfig,
    PerformanceMetrics,
    RebalanceEvent,
    RebalanceFrequency,
    RebalanceTrigger,
)
from portfolio_management.backtesting.performance.metrics import calculate_metrics
from portfolio_management.backtesting.transactions.costs import TransactionCostModel
from portfolio_management.core.exceptions import (
    InsufficientHistoryError,
    RebalanceError,
)


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
        # Convert index to dates for comparison
        price_dates = pd.to_datetime(self.prices.index).date
        mask = (price_dates >= self.config.start_date) & (
            price_dates <= self.config.end_date
        )
        period_prices = self.prices.loc[mask].copy()
        period_returns = self.returns.loc[mask].copy()

        if len(period_prices) == 0:
            raise InsufficientHistoryError(
                required_start=self.config.start_date,
                available_start=self.config.start_date,
                asset_ticker="No data in period",
            )

        # Simulate each trading day
        for i in range(len(period_prices)):
            date_idx = period_prices.index[i]
            date = date_idx.date()
            prices_row = period_prices.iloc[i]

            # Calculate current portfolio value
            portfolio_value = self._calculate_portfolio_value(prices_row)
            self.equity_curve.append((date, float(portfolio_value)))

            has_min_history = (i + 1) >= self.strategy.min_history_periods

            # Only create lookback slices when actually rebalancing
            should_rebalance_forced = not self.rebalance_events and has_min_history
            should_rebalance_scheduled = (
                has_min_history and self._should_rebalance_scheduled(date)
            )

            if should_rebalance_forced or should_rebalance_scheduled:
                # Create lookback window only when needed
                # Use rolling window for parameter estimation (standard practice in quant finance)
                lookback_window = min(self.config.lookback_periods, i + 1)
                start_idx = max(0, i + 1 - lookback_window)
                lookback_returns = period_returns.iloc[start_idx : i + 1]
                lookback_prices = period_prices.iloc[start_idx : i + 1]

                trigger = (
                    RebalanceTrigger.FORCED
                    if should_rebalance_forced
                    else RebalanceTrigger.SCHEDULED
                )
                self._rebalance(
                    date,
                    lookback_returns,
                    lookback_prices,
                    trigger,
                )
                if should_rebalance_forced:
                    continue

        # Calculate performance metrics
        equity_df = pd.DataFrame(
            self.equity_curve,
            columns=["date", "equity"],
        ).set_index("date")
        metrics = calculate_metrics(equity_df, self.rebalance_events)

        return equity_df, metrics, self.rebalance_events

    def _calculate_portfolio_value(self, prices: pd.Series) -> Decimal:
        """Calculate total portfolio value at current prices."""
        holdings_value = Decimal(0)
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
        if freq == RebalanceFrequency.WEEKLY:
            return (date - last_rebalance).days >= 7
        if freq == RebalanceFrequency.MONTHLY:
            return (
                date.month != last_rebalance.month or date.year != last_rebalance.year
            )
        if freq == RebalanceFrequency.QUARTERLY:
            months_diff = (date.year - last_rebalance.year) * 12 + (
                date.month - last_rebalance.month
            )
            return months_diff >= 3
        if freq == RebalanceFrequency.ANNUAL:
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
            date_prices = (
                historical_prices.iloc[-1]
                if len(historical_prices) > 0
                else pd.Series()
            )

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
            total_target_value = float(pre_value) * (1 - self.config.cash_reserve_pct)

            # Calculate target shares for each asset
            target_shares: dict[str, int] = {}
            for ticker in target_weights.index:
                if ticker not in date_prices.index or pd.isna(date_prices[ticker]):
                    continue
                # Access series element properly
                ticker_price = date_prices.loc[ticker]
                price = float(ticker_price)
                if price <= 0:
                    continue
                ticker_weight = target_weights.loc[ticker]
                target_value = total_target_value * float(ticker_weight)
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
            total_cost = Decimal(0)
            for ticker, share_change in trades.items():
                if share_change == 0:
                    continue
                if ticker not in date_prices.index or pd.isna(date_prices[ticker]):
                    continue
                price = float(date_prices[ticker])
                if price <= 0:
                    continue

                cost = self.cost_model.calculate_cost(
                    ticker,
                    abs(share_change),
                    price,
                    share_change > 0,
                )
                total_cost += cost

            # Check if we have enough cash for buys + costs
            total_buys = Decimal(0)
            for ticker, share_change in trades.items():
                if share_change > 0:  # Buy
                    if ticker not in date_prices.index or pd.isna(date_prices[ticker]):
                        continue
                    price = Decimal(str(float(date_prices[ticker])))
                    total_buys += Decimal(str(share_change)) * price

            if total_buys + total_cost > self.cash:
                # Scale back trades to fit cash constraints
                scale_factor = float(self.cash * Decimal("0.95")) / float(
                    total_buys + total_cost,
                )
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
                    ticker,
                    abs(share_change),
                    price,
                    share_change > 0,
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
        holdings_value = Decimal(0)
        for ticker, shares in self.holdings.items():
            if ticker in prices.index and not pd.isna(prices[ticker]):
                price = Decimal(str(float(prices[ticker])))
                holdings_value += Decimal(str(shares)) * price
        return holdings_value
