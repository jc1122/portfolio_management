"""Risk parity portfolio strategy."""

from __future__ import annotations

import importlib
import logging

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from ...core.exceptions import (
    ConstraintViolationError,
    DependencyError,
    InsufficientDataError,
    OptimizationError,
)
from ..constraints.models import PortfolioConstraints
from ..models import Portfolio
from .base import PortfolioStrategy

logger = logging.getLogger(__name__)


class RiskParityStrategy(PortfolioStrategy):
    """Risk parity portfolio strategy.

    Allocates capital such that each asset contributes equally to total portfolio risk.
    Uses the riskparityportfolio library for optimization.

    Attributes:
        min_periods: Minimum periods for covariance estimation (default: 252, ~1 year)

    """

    def __init__(self, min_periods: int = 252) -> None:
        """Initialize risk parity strategy.

        Args:
            min_periods: Minimum periods for covariance estimation

        """
        self._min_periods = min_periods

    @property
    def name(self) -> str:
        """Return the strategy name."""
        return "risk_parity"

    @property
    def min_history_periods(self) -> int:
        """Return minimum number of return periods required."""
        return self._min_periods

    def construct(
        self,
        returns: pd.DataFrame,
        constraints: PortfolioConstraints,
        asset_classes: pd.Series | None = None,
    ) -> Portfolio:
        """Construct a risk parity portfolio.

        Args:
            returns: DataFrame with returns (assets as columns, dates as index)
            constraints: Portfolio constraints to enforce
            asset_classes: Optional Series mapping tickers to asset classes

        Returns:
            Portfolio with risk-parity weights

        Raises:
            InsufficientDataError: If insufficient data for covariance estimation
            OptimizationError: If optimization fails to converge
            DependencyError: If riskparityportfolio library is not installed

        """
        # Check for required library
        try:
            rpp = importlib.import_module("riskparityportfolio")
        except ImportError as err:
            raise DependencyError(dependency_name="riskparityportfolio") from err

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

        # Calculate covariance matrix
        cov_matrix = returns.cov()

        # Check for positive definiteness with numerical tolerance
        eigenvalues = np.linalg.eigvalsh(cov_matrix.to_numpy())
        EIGENVALUE_TOLERANCE = 1e-8  # noqa: N806
        if np.any(eigenvalues < EIGENVALUE_TOLERANCE):
            raise OptimizationError(strategy_name=self.name)

        # Prepare constraints for riskparityportfolio
        # Note: riskparityportfolio uses different constraint format
        n_assets = len(returns.columns)

        max_uniform_weight = 1.0 / n_assets

        try:
            # Basic risk parity optimization
            portfolio = rpp.RiskParityPortfolio(covariance=cov_matrix.to_numpy())

            # Apply box constraints
            if constraints.max_weight < max_uniform_weight:
                # Need constrained optimization
                portfolio.design(
                    Dmat=np.vstack([np.eye(n_assets), -np.eye(n_assets)]),
                    dvec=np.hstack(
                        [
                            np.full(n_assets, constraints.max_weight),
                            -np.full(n_assets, constraints.min_weight),
                        ],
                    ),
                )
            else:
                portfolio.design()

            w = portfolio.weights
        except Exception as err:
            if (
                constraints.max_weight >= max_uniform_weight - 1e-6
                and constraints.min_weight <= max_uniform_weight + 1e-6
            ):
                w = np.full(n_assets, max_uniform_weight)
            else:
                raise OptimizationError(strategy_name=self.name) from err

        # Create weights Series
        weights = pd.Series(w, index=returns.columns)

        # Normalize to ensure sum = 1.0 (numerical stability)
        weights = weights / weights.sum()

        if (
            constraints.max_weight >= max_uniform_weight - 1e-6
            and (weights > constraints.max_weight + 1e-6).any()
        ):
            weights = pd.Series(
                np.full(n_assets, max_uniform_weight),
                index=returns.columns,
            )
            w = weights.to_numpy()

        # Validate constraints
        self.validate_constraints(weights, constraints, asset_classes)

        # Calculate risk contributions for metadata
        portfolio_vol = np.sqrt(w @ cov_matrix.to_numpy() @ w)
        marginal_risk = cov_matrix.to_numpy() @ w
        risk_contrib = w * marginal_risk / portfolio_vol

        return Portfolio(
            weights=weights,
            strategy=self.name,
            metadata={
                "n_assets": n_assets,
                "portfolio_volatility": portfolio_vol,
                "risk_contributions": {
                    ticker: float(risk_contrib[idx])
                    for idx, ticker in enumerate(returns.columns)
                },
            },
        )

    @staticmethod
    def validate_constraints(
        weights: pd.Series,
        constraints: PortfolioConstraints,
        asset_classes: pd.Series | None,
    ) -> None:
        """Validate portfolio constraints."""
        # Check weight bounds
        if (weights > constraints.max_weight + 1e-6).any():
            violators = weights[weights > constraints.max_weight + 1e-6]
            raise ConstraintViolationError(
                constraint_name="max_weight",
                violated_value=violators.max(),
            )

        # Check asset class constraints if provided
        if asset_classes is not None:
            equity_mask = asset_classes.str.contains("equity", case=False, na=False)
            equity_tickers = asset_classes[equity_mask].index
            equity_exposure = weights[weights.index.isin(equity_tickers)].sum()

            if equity_exposure > constraints.max_equity_exposure + 1e-6:
                raise ConstraintViolationError(
                    constraint_name="max_equity_exposure",
                    violated_value=equity_exposure,
                )
