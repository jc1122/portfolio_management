"""Equal weight portfolio strategy."""

from __future__ import annotations

import logging

import pandas as pd

from ...core.exceptions import ConstraintViolationError, InsufficientDataError
from ..constraints.models import PortfolioConstraints
from ..models import Portfolio
from .base import PortfolioStrategy

logger = logging.getLogger(__name__)


class EqualWeightStrategy(PortfolioStrategy):
    """Equal-weight (1/N) portfolio strategy.

    Assigns equal weight to all assets, subject to constraints.
    This is the simplest baseline strategy and requires minimal historical data.
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
