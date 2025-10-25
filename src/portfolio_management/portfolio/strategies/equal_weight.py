"""A simple, non-optimizing strategy that assigns equal weight to all assets.

This module provides the `EqualWeightStrategy`, which implements the classic "1/N"
portfolio allocation. It serves as a fundamental baseline for comparison against
more complex optimization-based strategies.

Key Classes:
    - EqualWeightStrategy: Implements the equal-weight allocation logic.
"""

from __future__ import annotations

import logging

import pandas as pd

from ...core.exceptions import ConstraintViolationError, InsufficientDataError
from ..constraints.models import PortfolioConstraints
from ..models import Portfolio
from .base import PortfolioStrategy

logger = logging.getLogger(__name__)


class EqualWeightStrategy(PortfolioStrategy):
    """Implements the equal-weight (1/N) portfolio construction strategy.

    This strategy assigns an equal weight to every asset in the investment
    universe. It is a simple, transparent, and computationally inexpensive
    approach that serves as a common benchmark.

    The main assumption is that there is no information available to suggest
    that any single asset will outperform another.

    Mathematical Formulation:
        Given N assets in the portfolio, the weight for each asset i is:
        wᵢ = 1 / N

    This strategy does not perform any optimization and only considers the number
    of available assets. It will, however, validate the resulting portfolio
    against basic constraints (e.g., `max_weight`).

    Example:
        >>> import pandas as pd
        >>> from portfolio_management.portfolio.strategies import EqualWeightStrategy
        >>> from portfolio_management.portfolio.constraints import PortfolioConstraints
        >>>
        >>> returns = pd.DataFrame({
        ...     'ASSET_A': [0.01, 0.02],
        ...     'ASSET_B': [0.03, -0.01],
        ...     'ASSET_C': [0.02, 0.01],
        ...     'ASSET_D': [-0.01, 0.01],
        ... })
        >>>
        >>> strategy = EqualWeightStrategy()
        >>> constraints = PortfolioConstraints(max_weight=0.3)
        >>> portfolio = strategy.construct(returns, constraints)
        >>>
        >>> print(portfolio.weights)
        ASSET_A    0.25
        ASSET_B    0.25
        ASSET_C    0.25
        ASSET_D    0.25
        dtype: float64
    """

    @property
    def name(self) -> str:
        """Return the strategy name."""
        return "equal_weight"

    @property
    def min_history_periods(self) -> int:
        """Return minimum number of return periods required."""
        return 1  # Only need to know which assets exist

    def construct(
        self,
        returns: pd.DataFrame,
        constraints: PortfolioConstraints,
        asset_classes: pd.Series | None = None,
    ) -> Portfolio:
        """Construct an equal-weight portfolio.

        Args:
            returns: DataFrame with returns (assets as columns, dates as index)
            constraints: Portfolio constraints to enforce
            asset_classes: Optional Series mapping tickers to asset classes

        Returns:
            Portfolio with equal weights, adjusted for constraints

        Raises:
            InsufficientDataError: If returns DataFrame is empty
            ConstraintViolationError: If equal weighting violates constraints

        """
        # Validate inputs
        if returns.empty:
            raise InsufficientDataError(
                required_periods=self.min_history_periods,
                available_periods=0,
            )

        if len(returns) < self.min_history_periods:
            raise InsufficientDataError(
                required_periods=self.min_history_periods,
                available_periods=len(returns),
            )

        # Calculate equal weights
        n_assets = len(returns.columns)
        equal_weight = 1.0 / n_assets

        # Check if equal weight violates max_weight constraint
        if equal_weight > constraints.max_weight:
            raise ConstraintViolationError(
                constraint_name="max_weight",
                violated_value=equal_weight,
            )

        # Create weights Series
        weights = pd.Series(equal_weight, index=returns.columns)

        # Validate asset class constraints if provided
        if asset_classes is not None:
            self._validate_asset_class_constraints(
                weights,
                asset_classes,
                constraints,
            )

        return Portfolio(
            weights=weights,
            strategy=self.name,
            metadata={
                "n_assets": n_assets,
                "equal_weight": equal_weight,
            },
        )

    def _validate_asset_class_constraints(
        self,
        weights: pd.Series,
        asset_classes: pd.Series,
        constraints: PortfolioConstraints,
    ) -> None:
        """Validate that weights satisfy asset class exposure constraints.

        Args:
            weights: Portfolio weights
            asset_classes: Asset class mappings
            constraints: Portfolio constraints

        Raises:
            ConstraintViolationError: If exposure constraints are violated

        """
        # Calculate equity exposure (assuming "equity" in asset class name)
        equity_mask = asset_classes.str.contains("equity", case=False, na=False)
        equity_tickers = asset_classes[equity_mask].index
        equity_exposure = weights[weights.index.isin(equity_tickers)].sum()

        if equity_exposure > constraints.max_equity_exposure:
            raise ConstraintViolationError(
                constraint_name="max_equity_exposure",
                violated_value=equity_exposure,
            )

        # Calculate bond/cash exposure
        bond_mask = asset_classes.str.contains("bond|cash", case=False, na=False)
        bond_tickers = asset_classes[bond_mask].index
        bond_exposure = weights[weights.index.isin(bond_tickers)].sum()

        if bond_exposure < constraints.min_bond_exposure:
            raise ConstraintViolationError(
                constraint_name="min_bond_exposure",
                violated_value=bond_exposure,
            )
