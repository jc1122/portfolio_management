"""Data model for portfolio rebalancing configuration.

This module defines the `RebalanceConfig` class, which encapsulates all
parameters related to portfolio rebalancing logic. This includes rules for
triggering rebalances, such as fixed time intervals or tolerance bands,
as well as transaction cost assumptions.

Key Classes:
    - RebalanceConfig: Specifies the rules and costs for rebalancing.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RebalanceConfig:
    """Specifies the rules and costs for portfolio rebalancing.

    This data class defines the parameters that govern when and how a portfolio
    should be rebalanced. It supports both calendar-based (frequency) and
    drift-based (tolerance bands) rebalancing triggers.

    Attributes:
        frequency (int): The calendar-based rebalance frequency in days (e.g.,
            30 for monthly, 90 for quarterly).
        tolerance_bands (float): The maximum allowed drift for a position's weight
            (as a percentage of target weight) before triggering a rebalance.
            For example, 0.20 means a 20% drift is allowed.
        min_trade_size (float): The minimum trade size as a fraction of the total
            portfolio value. Trades smaller than this will be suppressed to avoid
            incurring excessive transaction costs for minor adjustments.
        cost_per_trade (float): The estimated transaction cost as a percentage of
            the trade value (e.g., 0.001 for 10 basis points).

    Configuration Example (YAML):
        ```yaml
        rebalancing:
          frequency: 90  # Quarterly rebalance
          tolerance_bands: 0.15  # 15% drift tolerance
          min_trade_size: 0.005  # 0.5% of portfolio
          cost_per_trade: 0.0005 # 5 bps
        ```
    """

    frequency: int = 30  # Monthly default
    tolerance_bands: float = 0.20
    min_trade_size: float = 0.01
    cost_per_trade: float = 0.001

    def __post_init__(self) -> None:
        """Validate rebalance parameters."""
        if self.frequency < 1:
            msg = f"Invalid frequency: {self.frequency} (must be >= 1)"
            raise ValueError(msg)

        if not 0.0 <= self.tolerance_bands <= 1.0:
            msg = f"Invalid tolerance_bands: {self.tolerance_bands}"
            raise ValueError(msg)

        if not 0.0 <= self.min_trade_size <= 1.0:
            msg = f"Invalid min_trade_size: {self.min_trade_size}"
            raise ValueError(msg)

        if not 0.0 <= self.cost_per_trade <= 1.0:
            msg = f"Invalid cost_per_trade: {self.cost_per_trade}"
            raise ValueError(msg)
