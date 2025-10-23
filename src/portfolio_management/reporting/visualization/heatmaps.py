"""Monthly returns heatmap data preparation for visualization.

This module provides utilities to prepare monthly returns data
in a heatmap format with years and months.
"""

from __future__ import annotations

import pandas as pd


def prepare_monthly_returns_heatmap(equity_df: pd.DataFrame) -> pd.DataFrame:
    """Prepare monthly returns data for heatmap visualization.

    Args:
        equity_df: DataFrame with equity values.

    Returns:
        DataFrame with years as index and months as columns.

    """
    # Calculate daily returns
    returns = equity_df["equity"].pct_change()

    # Resample to monthly (ME = month end, replaces deprecated 'M')
    monthly_returns = (1 + returns).resample("ME").prod() - 1

    # Create pivot table with years and months
    monthly_returns_df = pd.DataFrame(
        {
            "return": monthly_returns.values,
            "year": monthly_returns.index.year,
            "month": monthly_returns.index.month,
        },
    )

    # Pivot to create heatmap structure
    heatmap = (
        monthly_returns_df.pivot(
            index="year",
            columns="month",
            values="return",
        )
        * 100
    )  # Convert to percentage

    # Rename columns to month names
    month_names = {
        1: "Jan",
        2: "Feb",
        3: "Mar",
        4: "Apr",
        5: "May",
        6: "Jun",
        7: "Jul",
        8: "Aug",
        9: "Sep",
        10: "Oct",
        11: "Nov",
        12: "Dec",
    }
    heatmap.columns = [month_names.get(m, str(m)) for m in heatmap.columns]

    return heatmap
