"""Performance metrics comparison utilities for visualization.

This module provides utilities to prepare performance metrics comparison
tables for multi-strategy analysis.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from portfolio_management.backtesting import PerformanceMetrics


def prepare_metrics_comparison(
    metrics_list: list[tuple[str, PerformanceMetrics]],
) -> pd.DataFrame:
    """Prepare performance metrics comparison table.

    Args:
        metrics_list: List of tuples (strategy_name, metrics).

    Returns:
        DataFrame with strategies as rows and metrics as columns.

    """
    records = []

    for strategy_name, metrics in metrics_list:
        records.append(
            {
                "Strategy": strategy_name,
                "Total Return %": metrics.total_return * 100,
                "Annual Return %": metrics.annualized_return * 100,
                "Volatility %": metrics.annualized_volatility * 100,
                "Sharpe Ratio": metrics.sharpe_ratio,
                "Sortino Ratio": metrics.sortino_ratio,
                "Max Drawdown %": metrics.max_drawdown * 100,
                "Calmar Ratio": metrics.calmar_ratio,
                "Win Rate %": metrics.win_rate * 100,
                "Total Costs $": float(metrics.total_costs),
                "Num Rebalances": metrics.num_rebalances,
            },
        )

    return pd.DataFrame(records).set_index("Strategy")
