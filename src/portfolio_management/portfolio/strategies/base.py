"""Base portfolio strategy interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

from ..constraints.models import PortfolioConstraints
from ..models import Portfolio


class PortfolioStrategy(ABC):
    """Abstract base class for portfolio construction strategies.

    All concrete strategies must implement the `construct` method which takes
    return data and optional asset classifications to produce portfolio weights.
    """

    @abstractmethod
    def construct(
        self,
        returns: pd.DataFrame,
        constraints: PortfolioConstraints,
        asset_classes: pd.Series | None = None,
    ) -> Portfolio:
        """Construct a portfolio given return data and constraints.

        Args:
            returns: DataFrame with returns (assets as columns, dates as index)
            constraints: Portfolio constraints to enforce
            asset_classes: Optional Series mapping tickers to asset classes

        Returns:
            Portfolio object with weights and metadata

        Raises:
            InsufficientDataError: If insufficient data for the strategy
            OptimizationError: If optimization fails to converge
            ConstraintViolationError: If constraints cannot be satisfied

        """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the strategy name."""

    @property
    @abstractmethod
    def min_history_periods(self) -> int:
        """Return minimum number of return periods required."""
