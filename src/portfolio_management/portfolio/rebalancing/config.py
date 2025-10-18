"""Rebalancing configuration."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RebalanceConfig:
    """Configuration for portfolio rebalancing decisions.

    Attributes:
        frequency: Rebalance frequency in days (e.g., 30 for monthly, 90 for quarterly)
        tolerance_bands: Percentage drift tolerance before rebalancing (default: 0.20)
        min_trade_size: Minimum trade size as fraction of portfolio (default: 0.01)
        cost_per_trade: Transaction cost as percentage (default: 0.001 for 10 bps)

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
