"""Rolling performance metrics calculation for visualization.

This module provides utilities to calculate rolling performance metrics
such as rolling Sharpe ratio, volatility, and returns.
"""

from __future__ import annotations

import pandas as pd


def prepare_rolling_metrics(
    equity_df: pd.DataFrame,
    window: int = 60,
) -> pd.DataFrame:
    """Calculate rolling performance metrics.

    Args:
        equity_df: DataFrame with equity values.
        window: Rolling window size in days (default: 60).

    Returns:
        DataFrame with rolling Sharpe, volatility, and return.

    """
    # Calculate daily returns
    returns = equity_df["equity"].pct_change()

    # Rolling statistics
    rolling_return = returns.rolling(window).mean() * 252  # Annualized
    rolling_vol = returns.rolling(window).std() * (252**0.5)  # Annualized
    rolling_sharpe = rolling_return / rolling_vol

    # Rolling max drawdown
    equity = equity_df["equity"]
    rolling_max = equity.rolling(window).max()
    rolling_dd = (equity - rolling_max) / rolling_max * 100

    return pd.DataFrame(
        {
            "rolling_return_annual": rolling_return,
            "rolling_volatility_annual": rolling_vol,
            "rolling_sharpe": rolling_sharpe,
            "rolling_max_drawdown": rolling_dd.rolling(window).min(),
        },
    )
