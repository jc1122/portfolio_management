"""Equity curve data preparation for visualization.

This module provides utilities to prepare equity curve data for plotting,
including normalization and percentage change calculations.
"""

from __future__ import annotations

import pandas as pd


def prepare_equity_curve(equity_df: pd.DataFrame) -> pd.DataFrame:
    """Prepare equity curve data for plotting.

    Args:
        equity_df: DataFrame with equity values (from BacktestEngine.run).

    Returns:
        DataFrame with date index and normalized equity column.

    """
    result = equity_df.copy()
    initial_value = result["equity"].iloc[0]
    result["equity_normalized"] = result["equity"] / initial_value * 100
    result["equity_change_pct"] = (result["equity"] / initial_value - 1) * 100
    return result
