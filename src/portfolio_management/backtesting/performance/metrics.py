"""Performance metrics calculation for backtesting results.

This module provides `calculate_metrics`, a function for computing a comprehensive
set of performance statistics from a backtest's equity curve and rebalancing events.
These metrics are essential for evaluating the effectiveness and risk profile of
a trading strategy.

Key Functions:
    - calculate_metrics: Computes all performance metrics from backtest results.

Metric Definitions:
    - **Annualized Return**: The geometric average amount of money earned by an
      investment each year over a given time period.
      Formula: `(1 + Total Return) ^ (1 / Years) - 1`
    - **Annualized Volatility**: A measure of the dispersion of returns for a given
      security or market index. It is the standard deviation of returns, scaled
      by the square root of the number of trading periods in a year.
      Formula: `stdev(Returns) * sqrt(252)`
    - **Sharpe Ratio**: Measures the performance of an investment compared to a
      risk-free asset, after adjusting for its risk. It is the average return
      earned in excess of the risk-free rate per unit of volatility.
      Formula: `(Annualized Return - Risk-Free Rate) / Annualized Volatility`
    - **Sortino Ratio**: A variation of the Sharpe ratio that differentiates
      harmful volatility from total overall volatility by using the asset's
      standard deviation of negative portfolio returns—downside deviation.
      Formula: `(Annualized Return - Risk-Free Rate) / Downside Deviation`
    - **Maximum Drawdown (MDD)**: The maximum observed loss from a peak to a
      trough of a portfolio, before a new peak is attained. It is an indicator
      of downside risk over a specified time period.
      Formula: `min((Current Value - Peak Value) / Peak Value)`
    - **Calmar Ratio**: A measure of risk-adjusted return based on max drawdown.
      Formula: `Annualized Return / abs(Max Drawdown)`
    - **Expected Shortfall (CVaR)**: The expected return of the portfolio in the
      worst q% of cases. For q=5%, it's the average of the worst 5% of returns.
      It is a measure of tail risk.
    - **Turnover**: A measure of how frequently assets in a portfolio are bought
      and sold by the managers. High turnover can lead to higher transaction costs.

Usage Example:
    >>> import pandas as pd
    >>> from decimal import Decimal
    >>> from portfolio_management.backtesting.models import RebalanceEvent
    >>> from portfolio_management.backtesting.performance.metrics import calculate_metrics
    >>>
    >>> equity_data = {'date': pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03']),
    ...                'equity': [100000.0, 101000.0, 100500.0]}
    >>> equity_df = pd.DataFrame(equity_data).set_index('date')
    >>> events = [RebalanceEvent(date=equity_df.index[0], trigger='initial', trades={}, costs=Decimal('10.0'))]
    >>>
    >>> metrics = calculate_metrics(equity_df, events)
    >>> print(f"Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
    >>> print(f"Max Drawdown: {metrics.max_drawdown:.2%}")
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from portfolio_management.backtesting.models import (
        PerformanceMetrics,
        RebalanceEvent,
    )


def calculate_metrics(
    equity_df: pd.DataFrame,
    rebalance_events: list[RebalanceEvent],
) -> PerformanceMetrics:
    """Calculate performance metrics from an equity curve and rebalance events.

    This function takes the results of a backtest and computes a wide range of
    standard performance and risk metrics.

    Args:
        equity_df (pd.DataFrame): A DataFrame with a 'equity' column containing
            the portfolio's total value, indexed by date.
        rebalance_events (list[RebalanceEvent]): A list of all rebalancing
            events that occurred during the backtest, used for cost and
            turnover calculations.

    Returns:
        PerformanceMetrics: A dataclass containing all calculated statistics.
            Returns a zeroed-out metrics object if the equity curve has
            insufficient data (< 2 periods).
    """
    # Import here to avoid circular dependency
    from portfolio_management.backtesting.models import PerformanceMetrics

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
            total_costs=sum((e.costs for e in rebalance_events), Decimal(0)),
            num_rebalances=len(rebalance_events),
            final_value=Decimal(0),
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
            total_costs=sum((e.costs for e in rebalance_events), Decimal(0)),
            num_rebalances=len(rebalance_events),
            final_value=Decimal(equity_df["equity"].iloc[-1]) if not equity_df.empty else Decimal(0),
        )

    # Total and annualized returns
    total_return = float(
        (equity_df["equity"].iloc[-1] / equity_df["equity"].iloc[0]) - 1,
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
    win_rate = float(len(positive_returns) / len(returns)) if len(returns) > 0 else 0.0
    avg_win = float(positive_returns.mean()) if len(positive_returns) > 0 else 0.0
    avg_loss = float(negative_returns.mean()) if len(negative_returns) > 0 else 0.0

    # Turnover and costs
    total_costs = sum((event.costs for event in rebalance_events), Decimal(0))
    num_rebalances = len(rebalance_events)

    # Simple turnover calculation: sum of absolute trades / avg portfolio value
    if rebalance_events and not equity_df["equity"].empty:
        total_trade_volume = sum(
            sum(abs(qty) for qty in event.trades.values()) for event in rebalance_events
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
        final_value=Decimal(equity_df["equity"].iloc[-1]),
    )