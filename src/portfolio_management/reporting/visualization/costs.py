"""Transaction costs summary preparation for visualization.

This module provides utilities to summarize transaction costs over time,
including cumulative costs and cost breakdown analysis.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from portfolio_management.backtesting import RebalanceEvent


def prepare_transaction_costs_summary(
    rebalance_events: list[RebalanceEvent],
) -> pd.DataFrame:
    """Summarize transaction costs over time.

    Args:
        rebalance_events: List of rebalance events from backtest.

    Returns:
        DataFrame with cumulative costs and cost breakdown.

    """
    if not rebalance_events:
        return pd.DataFrame()

    records = []
    cumulative = 0.0

    for event in rebalance_events:
        costs = float(event.costs)
        cumulative += costs

        records.append(
            {
                "date": event.date,
                "costs": costs,
                "cumulative_costs": cumulative,
                "trigger": event.trigger.value,
                "num_trades": len([t for t in event.trades.values() if t != 0]),
                "portfolio_value": float(event.pre_rebalance_value),
                "costs_bps": (
                    (costs / float(event.pre_rebalance_value) * 10000)
                    if event.pre_rebalance_value > 0
                    else 0.0
                ),
            },
        )

    df = pd.DataFrame(records)
    return df.set_index("date")
