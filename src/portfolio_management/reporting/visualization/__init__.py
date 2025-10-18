"""Visualization data preparation utilities for reporting.

This module provides functions to prepare backtest results for charting
libraries like Matplotlib, Plotly, or web dashboards.
"""

from .allocations import prepare_allocation_history
from .comparison import prepare_metrics_comparison
from .costs import prepare_transaction_costs_summary
from .distributions import prepare_returns_distribution
from .drawdowns import prepare_drawdown_series
from .equity_curves import prepare_equity_curve
from .heatmaps import prepare_monthly_returns_heatmap
from .metrics import prepare_rolling_metrics
from .summary import create_summary_report
from .trade_analysis import prepare_trade_analysis

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
