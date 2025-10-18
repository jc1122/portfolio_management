"""Trade analysis utilities for visualization.

This module provides utilities to analyze individual trades from
rebalance events for detailed trade-level reporting.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from portfolio_management.backtesting import RebalanceEvent


def prepare_trade_analysis(
    rebalance_events: list[RebalanceEvent],
) -> pd.DataFrame:
    """Analyze individual trades from rebalance events.

    Args:
        rebalance_events: List of rebalance events from backtest.

    Returns:
        DataFrame with trade-level details.

    """
    if not rebalance_events:
        return pd.DataFrame()

    records = []

    for event in rebalance_events:
        for ticker, shares in event.trades.items():
            if shares == 0:
                continue

            records.append(
                {
                    "date": event.date,
                    "ticker": ticker,
                    "shares": shares,
                    "direction": "BUY" if shares > 0 else "SELL",
                    "abs_shares": abs(shares),
                    "trigger": event.trigger.value,
                    "portfolio_value": float(event.pre_rebalance_value),
                },
            )

    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records)

    # Add aggregations
    df["trade_count"] = 1

    return df
