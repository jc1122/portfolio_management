"""Risk parity portfolio strategy."""

from __future__ import annotations

import importlib
import logging
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from portfolio_management.core.exceptions import (
    ConstraintViolationError,
    DependencyError,
    InsufficientDataError,
    OptimizationError,
)
from portfolio_management.portfolio.models import Portfolio

from .base import PortfolioStrategy

if TYPE_CHECKING:
    from portfolio_management.portfolio.constraints.models import PortfolioConstraints

logger = logging.getLogger(__name__)

LARGE_UNIVERSE_THRESHOLD = 300
EIGENVALUE_TOLERANCE = 1e-8


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
        rpp = self._load_backend()
        self._validate_history(returns)

        n_assets = returns.shape[1]
        if n_assets > LARGE_UNIVERSE_THRESHOLD:
            return self._inverse_volatility_portfolio(
                returns,
                constraints,
                asset_classes,
            )

        cov_matrix = self._regularize_covariance(returns.cov(), n_assets)
        max_uniform_weight = 1.0 / n_assets

        try:
            portfolio = rpp.RiskParityPortfolio(covariance=cov_matrix.to_numpy())
            if constraints.max_weight < max_uniform_weight:
                portfolio.design(
                    Dmat=np.vstack([np.eye(n_assets), -np.eye(n_assets)]),
                    dvec=np.hstack(
                        [
                            np.full(n_assets, constraints.max_weight),
                            -np.full(n_assets, constraints.min_weight),
                        ],
                    ),
                    verbose=False,
                    maxiter=200,
                )
            else:
                portfolio.design(verbose=False, maxiter=200)
            weights_array = portfolio.weights
        except Exception as err:
            if (
                constraints.max_weight >= max_uniform_weight - 1e-6
                and constraints.min_weight <= max_uniform_weight + 1e-6
            ):
                weights_array = np.full(n_assets, max_uniform_weight)
            else:
                raise OptimizationError(strategy_name=self.name) from err

        weights = pd.Series(weights_array, index=returns.columns, dtype=float)
        weights = weights / weights.sum()

        if (
            constraints.max_weight >= max_uniform_weight - 1e-6
            and (weights > constraints.max_weight + 1e-6).any()
        ):
            weights = pd.Series(
                np.full(n_assets, max_uniform_weight),
                index=returns.columns,
                dtype=float,
            )
            weights_array = weights.to_numpy()

        self.validate_constraints(weights, constraints, asset_classes)

        portfolio_vol = self._portfolio_volatility(weights_array, cov_matrix)
        risk_contrib = self._risk_contributions(
            weights_array,
            cov_matrix,
            portfolio_vol,
            returns.columns,
        )

        return Portfolio(
            weights=weights,
            strategy=self.name,
            metadata={
                "n_assets": n_assets,
                "portfolio_volatility": portfolio_vol,
                "risk_contributions": risk_contrib,
            },
        )

    def _load_backend(self):
        try:
            return importlib.import_module("riskparityportfolio")
        except ImportError as err:  # pragma: no cover - dependency check
            raise DependencyError(dependency_name="riskparityportfolio") from err

    def _validate_history(self, returns: pd.DataFrame) -> None:
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

    def _inverse_volatility_portfolio(
        self,
        returns: pd.DataFrame,
        constraints: PortfolioConstraints,
        asset_classes: pd.Series | None,
    ) -> Portfolio:
        vols = returns.std(ddof=0)
        if (vols <= 0).any():
            raise OptimizationError(strategy_name=self.name)
        inv_vol = 1.0 / vols.to_numpy()
        weights = pd.Series(inv_vol / inv_vol.sum(), index=returns.columns, dtype=float)
        self.validate_constraints(weights, constraints, asset_classes)
        return Portfolio(
            weights=weights,
            strategy=self.name,
            metadata={
                "n_assets": len(returns.columns),
                "method": "inverse_volatility_fallback",
            },
        )

    def _regularize_covariance(
        self,
        cov_matrix: pd.DataFrame,
        n_assets: int,
    ) -> pd.DataFrame:
        eigenvalues = np.linalg.eigvalsh(cov_matrix.to_numpy())
        if np.any(eigenvalues < EIGENVALUE_TOLERANCE):
            min_eig = float(eigenvalues.min())
            jitter = (EIGENVALUE_TOLERANCE - min_eig) + 1e-6
            adjustment = pd.DataFrame(
                np.eye(n_assets) * jitter,
                index=cov_matrix.index,
                columns=cov_matrix.columns,
            )
            cov_matrix = cov_matrix + adjustment
            eigenvalues = np.linalg.eigvalsh(cov_matrix.to_numpy())
            if np.any(eigenvalues < EIGENVALUE_TOLERANCE):
                raise OptimizationError(strategy_name=self.name)
        return cov_matrix

    @staticmethod
    def _risk_contributions(
        weights_array: np.ndarray,
        cov_matrix: pd.DataFrame,
        portfolio_vol: float,
        tickers: pd.Index,
    ) -> dict[str, float]:
        marginal_risk = cov_matrix.to_numpy() @ weights_array
        contributions = weights_array * marginal_risk / portfolio_vol
        return {ticker: float(contributions[idx]) for idx, ticker in enumerate(tickers)}

    @staticmethod
    def _portfolio_volatility(
        weights_array: np.ndarray,
        cov_matrix: pd.DataFrame,
    ) -> float:
        return float(np.sqrt(weights_array @ cov_matrix.to_numpy() @ weights_array))

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
