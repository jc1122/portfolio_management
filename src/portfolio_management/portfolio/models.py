"""Portfolio data models and types."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import numpy as np
import pandas as pd


class StrategyType(str, Enum):
    """Supported portfolio construction strategies."""

    EQUAL_WEIGHT = "equal_weight"
    RISK_PARITY = "risk_parity"
    MEAN_VARIANCE = "mean_variance"


@dataclass(frozen=True)
class Portfolio:
    """Represents a constructed portfolio with weights and metadata.

    Attributes:
        weights: Series mapping ticker symbols to portfolio weights
        strategy: Name of the strategy used to construct the portfolio
        timestamp: When the portfolio was constructed
        metadata: Optional dict with strategy-specific information

    """

    weights: pd.Series
    strategy: str
    timestamp: pd.Timestamp = field(default_factory=pd.Timestamp.now)
    metadata: dict[str, object] | None = None

    def __post_init__(self) -> None:
        """Validate portfolio construction."""
        if not isinstance(self.weights, pd.Series):
            msg = "weights must be a pandas Series"
            raise TypeError(msg)

        if len(self.weights) == 0:
            msg = "Portfolio must contain at least one asset"
            raise ValueError(msg)

        if (self.weights < 0).any():
            msg = "Portfolio weights cannot be negative"
            raise ValueError(msg)

        # Allow small numerical errors in sum
        total_weight = self.weights.sum()
        if not np.isclose(total_weight, 1.0, atol=1e-6):
            msg = f"Portfolio weights must sum to 1.0, got {total_weight:.6f}"
            raise ValueError(msg)

    def get_position_count(self) -> int:
        """Return the number of positions with non-zero weights."""
        return (self.weights > 0).sum()

    def get_top_holdings(self, n: int = 10) -> pd.Series:
        """Return the top N holdings by weight."""
        return self.weights.nlargest(n)

    def to_dict(self) -> dict[str, object]:
        """Convert portfolio to dictionary representation."""
        return {
            "weights": self.weights.to_dict(),
            "strategy": self.strategy,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }
