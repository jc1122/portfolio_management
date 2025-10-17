"""Portfolio construction strategies and utilities.

This module provides a unified interface for constructing portfolios using
various allocation strategies (equal-weight, risk parity, mean-variance).
It includes constraint enforcement, rebalancing logic, and strategy orchestration.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from collections.abc import Sequence  # noqa: F401


class StrategyType(str, Enum):
    """Supported portfolio construction strategies."""

    EQUAL_WEIGHT = "equal_weight"
    RISK_PARITY = "risk_parity"
    MEAN_VARIANCE = "mean_variance"


@dataclass(frozen=True)
class PortfolioConstraints:
    """Portfolio investment constraints and guardrails.

    Attributes:
        max_weight: Maximum weight for any single asset (default: 0.25)
        min_weight: Minimum weight for any single asset (default: 0.0)
        max_equity_exposure: Maximum total equity allocation (default: 0.90)
        min_bond_exposure: Minimum total bond/cash allocation (default: 0.10)
        sector_limits: Optional dict mapping sector names to max weights
        require_full_investment: Whether weights must sum to 1.0 (default: True)

    """

    max_weight: float = 0.25
    min_weight: float = 0.0
    max_equity_exposure: float = 0.90
    min_bond_exposure: float = 0.10
    sector_limits: dict[str, float] | None = None
    require_full_investment: bool = True

    def __post_init__(self) -> None:
        """Validate constraint parameters."""
        if not 0.0 <= self.min_weight <= self.max_weight <= 1.0:
            msg = (
                f"Invalid weight bounds: min_weight={self.min_weight}, "
                f"max_weight={self.max_weight}"
            )
            raise ValueError(msg)

        if not 0.0 <= self.min_bond_exposure <= 1.0:
            msg = f"Invalid min_bond_exposure: {self.min_bond_exposure}"
            raise ValueError(msg)

        if not 0.0 <= self.max_equity_exposure <= 1.0:
            msg = f"Invalid max_equity_exposure: {self.max_equity_exposure}"
            raise ValueError(msg)

        if self.min_bond_exposure + self.max_equity_exposure < 1.0:
            msg = (
                f"Infeasible constraints: min_bond_exposure={self.min_bond_exposure} "
                f"+ max_equity_exposure={self.max_equity_exposure} < 1.0"
            )
            raise ValueError(msg)


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
        from .exceptions import ConstraintViolationError, InsufficientDataError

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
        from .exceptions import ConstraintViolationError

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
