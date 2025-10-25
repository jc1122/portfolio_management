"""Allocation history data preparation for visualization.

This module provides utilities to prepare portfolio allocation history
for stacked area charts and allocation tracking.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from portfolio_management.backtesting import RebalanceEvent


from typing import Any

def prepare_allocation_history(
    rebalance_events: list[RebalanceEvent],
) -> pd.DataFrame:
    """Prepare allocation history for stacked area chart.

    Args:
        rebalance_events: List of rebalance events from backtest.

    Returns:
        DataFrame with dates and allocation percentages per asset.

    """
    if not rebalance_events:
        return pd.DataFrame()

    records: list[dict[str, Any]] = []
    for event in rebalance_events:
        total_value = float(event.post_rebalance_value)
        if total_value == 0:
            continue

        record: dict[str, Any] = {"date": event.date}

        # Calculate cash percentage
        record["cash_pct"] = float(event.cash_after) / total_value * 100

        # Calculate holdings percentages
        holdings_value = float(event.post_rebalance_value - event.cash_after)
        record["holdings_pct"] = (
            holdings_value / total_value * 100 if total_value > 0 else 0.0
        )

        # Add trigger type
        record["trigger"] = event.trigger.value

        records.append(record)

    return pd.DataFrame(records).set_index("date")
