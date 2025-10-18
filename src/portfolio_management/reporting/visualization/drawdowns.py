"""Drawdown calculation utilities for visualization.

This module provides utilities to calculate drawdown series and
underwater periods for portfolio performance analysis.
"""

from __future__ import annotations

import pandas as pd


def prepare_drawdown_series(equity_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate drawdown series for plotting.

    Args:
        equity_df: DataFrame with equity values.

    Returns:
        DataFrame with drawdown percentages and underwater periods.

    """
    equity = equity_df["equity"]

    # Calculate running maximum
    running_max = equity.expanding().max()

    # Calculate drawdown as percentage
    drawdown = (equity - running_max) / running_max * 100

    # Identify underwater periods (when in drawdown)
    underwater = drawdown < 0

    return pd.DataFrame(
        {
            "drawdown_pct": drawdown,
            "running_max": running_max,
            "underwater": underwater,
        },
    )
