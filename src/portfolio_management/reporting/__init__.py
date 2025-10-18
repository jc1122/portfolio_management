"""Reporting and visualization package.

This package provides utilities for preparing backtest results for visualization
and generating comprehensive performance reports.

Main Modules:
    - visualization: Data preparation utilities for charts and plots
"""

from .visualization import (
    create_summary_report,
    prepare_allocation_history,
    prepare_drawdown_series,
    prepare_equity_curve,
    prepare_metrics_comparison,
    prepare_monthly_returns_heatmap,
    prepare_returns_distribution,
    prepare_rolling_metrics,
    prepare_trade_analysis,
    prepare_transaction_costs_summary,
)

__all__ = [
    "create_summary_report",
    "prepare_allocation_history",
    "prepare_drawdown_series",
    "prepare_equity_curve",
    "prepare_metrics_comparison",
    "prepare_monthly_returns_heatmap",
    "prepare_returns_distribution",
    "prepare_rolling_metrics",
    "prepare_trade_analysis",
    "prepare_transaction_costs_summary",
]
