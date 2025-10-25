"""Defines the abstract base class for all portfolio construction strategies.

This module provides the `PortfolioStrategy` interface, which ensures that all
concrete strategy implementations adhere to a common contract. This allows for
polymorphic use of different strategies within the portfolio construction
framework, making it easy to swap, test, and compare them.

Key Components:
    - PortfolioStrategy (ABC): An abstract base class that defines the `construct`
      method required by all portfolio construction strategies.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

from ..constraints.models import PortfolioConstraints
from ..models import Portfolio


class PortfolioStrategy(ABC):
    """Abstract base class for all portfolio construction strategies.

    This class defines the common interface for all strategies. Concrete
    implementations must provide the logic for constructing a portfolio, which
    involves calculating asset weights based on return data and a set of
    constraints.

    The interface is designed to be flexible, accommodating strategies ranging
    from simple heuristics (like equal weight) to complex optimizations (like
    mean-variance or risk parity).
    """

    @abstractmethod
    def construct(
        self,
        returns: pd.DataFrame,
        constraints: PortfolioConstraints,
        asset_classes: pd.Series | None = None,
    ) -> Portfolio:
        """Construct a portfolio based on the strategy's logic.

        This is the core method of the strategy. It takes historical or expected
        returns, a set of investment constraints, and optional asset-level
        metadata to calculate and return the target portfolio weights.

        Args:
            returns (pd.DataFrame): A DataFrame of asset returns, with assets
                as columns and dates as the index.
            constraints (PortfolioConstraints): An object defining the investment
                rules, such as weight limits and exposure constraints.
            asset_classes (pd.Series | None): An optional Series that maps asset
                tickers to their respective asset classes (e.g., 'EQUITY', 'BOND').
                This is used for applying group-level constraints.

        Returns:
            Portfolio: A `Portfolio` object containing the calculated weights
            and other relevant metadata about the constructed portfolio.

        Raises:
            InsufficientDataError: If the provided `returns` DataFrame does not
                contain enough data to perform the necessary calculations.
            OptimizationError: If a numerical optimization fails to converge to
                a valid solution.
            InfeasibleError: If the optimization problem is determined to be
                infeasible under the given constraints.
        """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the strategy name."""

    @property
    @abstractmethod
    def min_history_periods(self) -> int:
        """Return minimum number of return periods required."""
