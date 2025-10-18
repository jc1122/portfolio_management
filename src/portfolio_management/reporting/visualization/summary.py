"""Summary report generation for visualization.

This module provides utilities to create comprehensive summary reports
combining performance, risk, trading, and portfolio evolution data.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from portfolio_management.backtesting import PerformanceMetrics, RebalanceEvent


def create_summary_report(
    equity_df: pd.DataFrame,
    metrics: PerformanceMetrics,
    rebalance_events: list[RebalanceEvent],
) -> dict[str, object]:
    """Create a comprehensive summary report dictionary.

    Args:
        equity_df: DataFrame with equity values.
        metrics: Performance metrics from backtest.
        rebalance_events: List of rebalance events.

    Returns:
        Dictionary with all key statistics and data for reporting.

    """
    returns = equity_df["equity"].pct_change().dropna()

    return {
        # Performance
        "performance": {
            "total_return_pct": round(metrics.total_return * 100, 2),
            "annualized_return_pct": round(metrics.annualized_return * 100, 2),
            "volatility_pct": round(metrics.annualized_volatility * 100, 2),
            "sharpe_ratio": round(metrics.sharpe_ratio, 2),
            "sortino_ratio": round(metrics.sortino_ratio, 2),
            "max_drawdown_pct": round(metrics.max_drawdown * 100, 2),
            "calmar_ratio": round(metrics.calmar_ratio, 2),
        },
        # Risk metrics
        "risk": {
            "expected_shortfall_95_pct": round(metrics.expected_shortfall_95 * 100, 2),
            "win_rate_pct": round(metrics.win_rate * 100, 1),
            "avg_win_pct": round(metrics.avg_win * 100, 2),
            "avg_loss_pct": round(metrics.avg_loss * 100, 2),
            "best_day_pct": round(returns.max() * 100, 2) if len(returns) > 0 else 0.0,
            "worst_day_pct": round(returns.min() * 100, 2) if len(returns) > 0 else 0.0,
        },
        # Trading activity
        "trading": {
            "num_rebalances": metrics.num_rebalances,
            "total_costs_usd": float(metrics.total_costs),
            "avg_turnover": round(metrics.turnover, 2),
            "total_trades": sum(
                len([t for t in event.trades.values() if t != 0])
                for event in rebalance_events
            ),
        },
        # Portfolio evolution
        "portfolio": {
            "initial_value": float(equity_df["equity"].iloc[0]),
            "final_value": float(equity_df["equity"].iloc[-1]),
            "peak_value": float(equity_df["equity"].max()),
            "num_days": len(equity_df),
        },
    }
