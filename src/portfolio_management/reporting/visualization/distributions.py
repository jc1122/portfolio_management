"""Returns distribution data preparation for visualization.

This module provides utilities to prepare returns distribution data
for histogram plotting and statistical analysis.
"""

from __future__ import annotations

import pandas as pd


def prepare_returns_distribution(equity_df: pd.DataFrame) -> pd.DataFrame:
    """Prepare returns distribution data for histogram plotting.

    Args:
        equity_df: DataFrame with equity values.

    Returns:
        DataFrame with returns and distribution statistics.

    """
    returns = equity_df["equity"].pct_change().dropna()

    # Calculate statistics
    mean_return = returns.mean()
    std_return = returns.std()

    # Create bins for histogram
    return pd.DataFrame(
        {
            "returns": returns,
            "returns_pct": returns * 100,
            "positive": returns > 0,
            "mean": mean_return,
            "std": std_return,
        },
    )
