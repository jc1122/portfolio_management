"""Core backtesting engine for historical portfolio simulation.

This module provides the `BacktestEngine`, a class that orchestrates portfolio
simulation over historical data. It handles rebalancing, transaction costs,
cash management, and performance tracking to provide a realistic assessment
of a given portfolio strategy.

Key Classes:
    - BacktestEngine: The main engine for running backtest simulations.

Usage Example:
    >>> import pandas as pd
    >>> from portfolio_management.backtesting.models import BacktestConfig
    >>> from portfolio_management.backtesting.engine.backtest import BacktestEngine
    >>> from portfolio_management.portfolio.strategy import PortfolioStrategy
    >>>
    >>> # Assume config, strategy, prices, and returns are defined
    >>> # config = BacktestConfig(...)
    >>> # strategy = PortfolioStrategy(...)
    >>> # prices = pd.DataFrame(...)
    >>> # returns = pd.DataFrame(...)
    >>>
    >>> # engine = BacktestEngine(config, strategy, prices, returns)
    >>> # try:
    ... #     equity_curve, metrics, events = engine.run()
    ... #     print(f"Final Equity: {equity_curve['equity'].iloc[-1]:.2f}")
    ... #     print(f"Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
    ... # except InsufficientHistoryError as e:
    ... #     print(f"Error: {e}")

"""

from __future__ import annotations

import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from portfolio_management.portfolio import PortfolioStrategy

from portfolio_management.backtesting.eligibility import (
    compute_pit_eligibility,
    compute_pit_eligibility_cached,
    detect_delistings,
)
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

    Simulates the performance of a portfolio strategy over a historical period,
    incorporating realistic constraints like transaction costs, rebalancing
    schedules, and point-in-time data eligibility.

    The engine iterates day by day through the historical price data, tracks the
    portfolio's value, and triggers rebalancing events based on the configured
    frequency. At each rebalance, it uses the provided strategy to determine a
    new target portfolio and executes the necessary trades.

    Workflow:
        1. Initialize with configuration, strategy, and historical data.
        2. Iterate through each day in the backtest period.
        3. On each day, update the total portfolio equity value.
        4. Check if a scheduled rebalancing is due.
        5. On a rebalancing day:
           a. Determine the universe of eligible assets (PIT eligibility).
           b. Apply preselection and membership policies to get candidate assets.
           c. Call the portfolio strategy to get target weights.
           d. Calculate required trades (buys/sells).
           e. Compute and deduct transaction costs.
           f. Update cash and holdings.
        6. After the simulation, calculate final performance metrics.

    Attributes:
        config (BacktestConfig): The configuration settings for the backtest.
        strategy (PortfolioStrategy): The portfolio construction strategy to be tested.
        prices (pd.DataFrame): DataFrame of historical prices.
        returns (pd.DataFrame): DataFrame of historical returns.
        classifications (dict[str, str] | None): Asset class mappings for constraints.
        preselection: Optional preselection filter for asset screening.
        membership_policy: Optional policy to control portfolio turnover.
        cache: Optional cache for factors and eligibility data to improve performance.
        cost_model (TransactionCostModel): The model for calculating trade costs.
        holdings (dict[str, int]): The current number of shares held for each asset.
        cash (Decimal): The current cash balance in the portfolio.
        rebalance_events (list[RebalanceEvent]): A log of all rebalancing events.
        equity_curve (list[tuple[datetime.date, float]]): A daily log of portfolio equity.

    Example:
        >>> from portfolio_management.backtesting.models import BacktestConfig
        >>> from portfolio_management.portfolio.strategy import EqualWeightStrategy
        >>> from portfolio_management.utils.testing import create_dummy_data
        >>>
        >>> start_date = datetime.date(2022, 1, 1)
        >>> end_date = datetime.date(2023, 12, 31)
        >>> prices, returns = create_dummy_data(['AAPL', 'MSFT'], start_date, end_date)
        >>>
        >>> config = BacktestConfig(
        ...     start_date=start_date,
        ...     end_date=end_date,
        ...     initial_capital=Decimal("100000.00"),
        ...     rebalance_frequency=RebalanceFrequency.QUARTERLY,
        ...     commission_pct=Decimal("0.001")
        ... )
        >>> strategy = EqualWeightStrategy(min_history_periods=60)
        >>>
        >>> engine = BacktestEngine(config, strategy, prices, returns)
        >>> equity_curve, metrics, events = engine.run()
        >>>
        >>> print(f"Backtest finished with {len(events)} rebalances.")
        >>> print(f"Final portfolio value: ${metrics.final_value:,.2f}")
        >>> print(f"Annualized Return: {metrics.annualized_return:.2%}")
        >>> print(f"Sharpe Ratio: {metrics.sharpe_ratio:.2f}")

    """

    def __init__(
        self,
        config: BacktestConfig,
        strategy: PortfolioStrategy,
        prices: pd.DataFrame,
        returns: pd.DataFrame,
        classifications: dict[str, str] | None = None,
        preselection=None,
        membership_policy=None,
        cache=None,
    ) -> None:
        """Initialize the backtesting engine.

        Args:
            config: Backtest configuration.
            strategy: Portfolio construction strategy to use.
            prices: Historical prices (index=dates, columns=tickers).
            returns: Historical returns (index=dates, columns=tickers).
            classifications: Optional asset class mappings for constraints.
            preselection: Optional Preselection instance for asset filtering.
            membership_policy: Optional MembershipPolicy for controlling portfolio churn.
            cache: Optional FactorCache instance for caching factor scores and PIT eligibility.

        Raises:
            InsufficientHistoryError: If data doesn't cover the backtest period.
        """
        self.config = config
        self.strategy = strategy
        self.prices = prices.copy()
        self.returns = returns.copy()
        self.classifications = classifications or {}
        self.preselection = preselection
        self.membership_policy = membership_policy
        self.cache = cache
        self.holding_periods: dict[str, int] = (
            {}
        )  # Track holding periods for membership policy

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
        self.delisted_assets: dict[str, datetime.date] = {}  # Track delisted assets

    def run(self) -> tuple[pd.DataFrame, PerformanceMetrics, list[RebalanceEvent]]:
        """Execute the backtest simulation.

        This is the main entry point to start the backtest. It iterates through
        the specified time period, manages the portfolio, and calculates results.

        Returns:
            A tuple containing:
            - pd.DataFrame: The daily equity curve of the portfolio.
            - PerformanceMetrics: A summary of key performance indicators.
            - list[RebalanceEvent]: A detailed log of all rebalancing events.

        Raises:
            InsufficientHistoryError: If the provided data does not cover the
                configured backtest period.
            RebalanceError: If a fatal error occurs during a rebalancing attempt.
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

            # Apply point-in-time eligibility mask if enabled
            eligible_returns = historical_returns
            if self.config.use_pit_eligibility:
                # Compute eligibility based only on data up to this date
                # Use cached version if cache is available
                if self.cache is not None:
                    eligibility_mask = compute_pit_eligibility_cached(
                        returns=historical_returns,
                        date=date,
                        min_history_days=self.config.min_history_days,
                        min_price_rows=self.config.min_price_rows,
                        cache=self.cache,
                    )
                else:
                    eligibility_mask = compute_pit_eligibility(
                        returns=historical_returns,
                        date=date,
                        min_history_days=self.config.min_history_days,
                        min_price_rows=self.config.min_price_rows,
                    )

                # Filter to only eligible assets
                eligible_tickers = historical_returns.columns[eligibility_mask]
                if len(eligible_tickers) == 0:
                    # No eligible assets yet, skip rebalance
                    return

                eligible_returns = historical_returns[eligible_tickers]

                # Detect delistings - assets that have stopped trading
                delistings = detect_delistings(
                    returns=self.returns,
                    current_date=date,
                    lookforward_days=30,
                )

                # Liquidate holdings in delisted assets
                for ticker, last_date in delistings.items():
                    if ticker in self.holdings and self.holdings[ticker] > 0:
                        # Mark as delisted
                        self.delisted_assets[ticker] = last_date

                        # Liquidate at last available price if we have it
                        if ticker in date_prices.index and not pd.isna(
                            date_prices[ticker],
                        ):
                            shares = self.holdings[ticker]
                            price = float(date_prices[ticker])

                            if price > 0:
                                # Calculate cost for selling
                                cost = self.cost_model.calculate_cost(
                                    ticker,
                                    shares,
                                    price,
                                    is_buy=False,
                                )

                                # Sell and add proceeds to cash
                                sale_value = Decimal(str(shares * price))
                                self.cash += sale_value
                                self.cash -= cost

                                # Remove from holdings
                                del self.holdings[ticker]

            constraints = PortfolioConstraints(
                max_weight=1.0,  # Allow any weight for single asset
                min_weight=0.0,
                max_equity_exposure=1.0,  # Allow full equity exposure
                min_bond_exposure=0.0,  # No minimum bond requirement
            )

            # Build asset class series if we have classifications
            asset_classes = None
            if self.classifications:
                # Filter to only eligible assets
                asset_classes = pd.Series(self.classifications)
                if self.config.use_pit_eligibility:
                    asset_classes = asset_classes[
                        asset_classes.index.isin(eligible_returns.columns)
                    ]

            # Apply preselection if configured
            candidate_assets = list(eligible_returns.columns)
            preselected_ranks: pd.Series | None = None
            membership_top_k = len(candidate_assets)
            if self.preselection is not None:
                # Preselect assets based on factors (momentum, low_vol, etc.)
                # Pass full self.returns dataset; preselection will filter by rebalance_date
                # Then intersect selected assets with eligible assets
                selected_assets = self.preselection.select_assets(
                    returns=self.returns,
                    rebalance_date=date,
                )
                # Only keep selected assets that are also eligible
                selected_assets = [
                    a for a in selected_assets if a in eligible_returns.columns
                ]
                candidate_assets = selected_assets
                membership_top_k = len(selected_assets)

                # Get ranks for membership policy (if needed)
                if (
                    self.membership_policy is not None
                    and self.membership_policy.enabled
                ):
                    if isinstance(eligible_returns.index, pd.DatetimeIndex):
                        date_mask = eligible_returns.index.date < date
                    else:
                        date_mask = eligible_returns.index < date
                    available_returns = eligible_returns.loc[date_mask]

                    if self.preselection.config.method.value == "momentum":
                        scores = self.preselection._compute_momentum(available_returns)
                    elif self.preselection.config.method.value == "low_vol":
                        scores = self.preselection._compute_low_volatility(
                            available_returns,
                        )
                    elif self.preselection.config.method.value == "combined":
                        scores = self.preselection._compute_combined(available_returns)
                    else:
                        scores = pd.Series(
                            range(len(available_returns.columns)),
                            index=available_returns.columns,
                        )

                    valid_scores = scores.dropna()
                    sorted_scores = valid_scores.sort_values(ascending=False)
                    preselected_ranks = pd.Series(
                        range(1, len(sorted_scores) + 1),
                        index=sorted_scores.index,
                    )

            # Apply membership policy if configured
            if self.membership_policy is not None and self.membership_policy.enabled:
                from portfolio_management.portfolio import apply_membership_policy

                current_holdings = list(self.holdings.keys())

                # If preselection not used, create simple rank by name for determinism
                if preselected_ranks is None:
                    # Simple ranking: alphabetical order
                    preselected_ranks = pd.Series(
                        range(1, len(candidate_assets) + 1),
                        index=sorted(candidate_assets),
                    )
                else:
                    # Ensure current holdings have ranks even if not in preselection results
                    missing_holdings = sorted(
                        set(current_holdings) - set(preselected_ranks.index),
                    )
                    if missing_holdings:
                        worst_rank = (
                            int(preselected_ranks.max())
                            if not preselected_ranks.empty
                            else 0
                        )
                        additional_ranks = pd.Series(
                            range(
                                worst_rank + 1,
                                worst_rank + len(missing_holdings) + 1,
                            ),
                            index=missing_holdings,
                        )
                        preselected_ranks = pd.concat(
                            [preselected_ranks, additional_ranks],
                        )

                current_weight_map = dict.fromkeys(current_holdings, 0.0)
                candidate_weight_map = dict.fromkeys(
                    set(candidate_assets) | set(current_holdings),
                    0.0,
                )

                # Apply membership policy
                final_candidates = apply_membership_policy(
                    current_holdings=current_holdings,
                    preselected_ranks=preselected_ranks,
                    policy=self.membership_policy,
                    holding_periods=self.holding_periods,
                    top_k=membership_top_k,
                    current_weights=current_weight_map,
                    candidate_weights=candidate_weight_map,
                )

                candidate_assets = [
                    c for c in final_candidates if c in eligible_returns.columns
                ]

            # Filter to final candidates determined by preselection/membership
            eligible_returns = eligible_returns[candidate_assets]

            if asset_classes is not None:
                asset_classes = asset_classes[
                    asset_classes.index.isin(candidate_assets)
                ]

            # Construct target portfolio (on selected subset)
            portfolio = self.strategy.construct(
                returns=eligible_returns,
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
            removed_tickers = [t for t, s in self.holdings.items() if s == 0]
            self.holdings = {t: s for t, s in self.holdings.items() if s != 0}

            # Update holding periods for membership policy
            if self.membership_policy is not None and self.membership_policy.enabled:
                # Increment holding periods for all current holdings
                for ticker in self.holdings.keys():
                    self.holding_periods[ticker] = (
                        self.holding_periods.get(ticker, 0) + 1
                    )

                # Reset holding periods for removed positions
                for ticker in removed_tickers:
                    if ticker in self.holding_periods:
                        del self.holding_periods[ticker]

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