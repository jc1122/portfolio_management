"""Performance metrics calculation for backtesting results.

This module provides utilities for calculating various performance metrics
from equity curves and rebalancing events.
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
    """Calculate performance metrics from equity curve.

    Args:
        equity_df: DataFrame with equity values indexed by date.
        rebalance_events: List of rebalancing events.

    Returns:
        PerformanceMetrics with calculated statistics.

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
    )
