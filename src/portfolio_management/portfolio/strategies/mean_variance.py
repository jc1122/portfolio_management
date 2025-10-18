"""Mean-variance optimization strategy."""

from __future__ import annotations

import importlib
import logging
from collections.abc import Sequence
from typing import ClassVar

import pandas as pd

from ...core.exceptions import DependencyError, InsufficientDataError, OptimizationError
from ..constraints.models import PortfolioConstraints
from ..models import Portfolio
from .base import PortfolioStrategy

logger = logging.getLogger(__name__)


class MeanVarianceStrategy(PortfolioStrategy):
    """Mean-variance optimization strategy powered by PyPortfolioOpt."""

    _VALID_OBJECTIVES: ClassVar[set[str]] = {
        "max_sharpe",
        "min_volatility",
        "efficient_risk",
    }

    def __init__(
        self,
        objective: str = "max_sharpe",
        risk_free_rate: float = 0.02,
        min_periods: int = 252,
    ) -> None:
        """Initialise the strategy configuration."""
        if objective not in self._VALID_OBJECTIVES:
            msg = (
                f"Invalid objective '{objective}'. Expected one of "
                f"{sorted(self._VALID_OBJECTIVES)}."
            )
            raise ValueError(msg)

        self._objective = objective
        self._risk_free_rate = risk_free_rate
        self._min_periods = min_periods

    @property
    def name(self) -> str:
        """Return the registered strategy name."""
        return f"mean_variance_{self._objective}"

    @property
    def min_history_periods(self) -> int:
        """Return the minimum number of periods needed for estimation."""
        return self._min_periods

    def construct(
        self,
        returns: pd.DataFrame,
        constraints: PortfolioConstraints,
        asset_classes: pd.Series | None = None,
    ) -> Portfolio:
        """Construct a mean-variance optimised portfolio."""
        efficient_frontier_cls, expected_returns, risk_models = self._load_backend()

        self._validate_returns(returns)
        mu, cov_matrix = self._estimate_moments(returns, expected_returns, risk_models)

        ef = self._initialise_frontier(
            efficient_frontier_cls,
            mu,
            cov_matrix,
            constraints,
        )
        index_map = {ticker: idx for idx, ticker in enumerate(mu.index)}

        if constraints.sector_limits and asset_classes is not None:
            self._apply_sector_limits(ef, constraints, asset_classes, index_map)

        if asset_classes is not None:
            self._apply_asset_class_limits(ef, constraints, asset_classes, index_map)

        self._optimise_frontier(ef)

        weights = self._extract_weights(ef)
        # Import at runtime to avoid circular dependency
        from .risk_parity import RiskParityStrategy

        RiskParityStrategy.validate_constraints(weights, constraints, asset_classes)
        performance = self._summarise_portfolio(ef)

        return Portfolio(
            weights=weights,
            strategy=self.name,
            metadata={
                "n_assets": int(weights.size),
                **performance,
                "objective": self._objective,
            },
        )

    def _load_backend(self):
        try:
            module = importlib.import_module("pypfopt")
            expected_returns = importlib.import_module("pypfopt.expected_returns")
            risk_models = importlib.import_module("pypfopt.risk_models")
        except ImportError as err:
            msg = (
                "PyPortfolioOpt is required for mean-variance optimisation. "
                "Install it with `pip install PyPortfolioOpt`."
            )
            raise DependencyError(
                dependency_name="PyPortfolioOpt",
                message=msg,
            ) from err

        return module.EfficientFrontier, expected_returns, risk_models

    def _validate_returns(self, returns: pd.DataFrame) -> None:
        if returns.empty:
            raise InsufficientDataError(
                required_periods=self.min_history_periods,
                available_periods=0,
                message="Returns DataFrame is empty.",
            )

        n_periods = len(returns)
        if n_periods < self.min_history_periods:
            raise InsufficientDataError(
                required_periods=self.min_history_periods,
                available_periods=n_periods,
                message="Not enough return observations for mean-variance optimisation.",
            )

    def _estimate_moments(self, returns: pd.DataFrame, expected_returns, risk_models):
        mu = expected_returns.mean_historical_return(returns, frequency=252)
        cov_matrix = risk_models.sample_cov(returns, frequency=252)
        return mu, cov_matrix

    def _initialise_frontier(
        self,
        efficient_frontier_cls,
        mu: pd.Series,
        cov_matrix: pd.DataFrame,
        constraints: PortfolioConstraints,
    ):
        """Initialise the efficient frontier with box constraints."""
        return efficient_frontier_cls(
            mu,
            cov_matrix,
            weight_bounds=(constraints.min_weight, constraints.max_weight),
        )

    def _apply_sector_limits(
        self,
        ef,
        constraints: PortfolioConstraints,
        asset_classes: pd.Series,
        index_map: dict[str, int],
    ) -> None:
        tickers = list(index_map.keys())
        sector_series = asset_classes.reindex(tickers)
        for sector, limit in constraints.sector_limits.items():
            mask = sector_series.str.lower() == sector.lower()
            tickers = sector_series[mask].index.tolist()
            idxs = self._indices_for(index_map, tickers)
            if idxs:
                ef.add_constraint(
                    lambda w, idxs=idxs, limit=limit: sum(w[i] for i in idxs) <= limit,
                )

    def _apply_asset_class_limits(
        self,
        ef,
        constraints: PortfolioConstraints,
        asset_classes: pd.Series,
        index_map: dict[str, int],
    ) -> None:
        tickers = list(index_map.keys())
        normalized = asset_classes.reindex(tickers)
        equity_mask = normalized.str.contains("equity", case=False, na=False)
        bond_mask = normalized.str.contains("bond|cash", case=False, na=False)

        equity_indices = self._indices_for(
            index_map,
            normalized[equity_mask].index.tolist(),
        )
        if equity_indices:
            ef.add_constraint(
                lambda w, idxs=equity_indices, limit=constraints.max_equity_exposure: sum(
                    w[i] for i in idxs
                )
                <= limit,
            )

        bond_indices = self._indices_for(
            index_map,
            normalized[bond_mask].index.tolist(),
        )
        if bond_indices:
            ef.add_constraint(
                lambda w, idxs=bond_indices, limit=constraints.min_bond_exposure: sum(
                    w[i] for i in idxs
                )
                >= limit,
            )

    def _optimise_frontier(self, ef) -> None:
        try:
            if self._objective == "max_sharpe":
                ef.max_sharpe(risk_free_rate=self._risk_free_rate)
            elif self._objective == "min_volatility":
                ef.min_volatility()
            else:
                ef.efficient_risk(target_volatility=0.10)
        except Exception as err:  # pragma: no cover - backend raises diverse errors
            raise OptimizationError(
                strategy_name=self.name,
                message=f"Mean-variance optimisation failed: {err}",
            ) from err

    def _extract_weights(self, ef) -> pd.Series:
        cleaned_weights = ef.clean_weights()
        weights = pd.Series(cleaned_weights, dtype=float)
        weights = weights[weights > 0]
        if weights.empty:
            raise OptimizationError(
                strategy_name=self.name,
                message="Optimisation produced an empty portfolio.",
            )
        return weights / weights.sum()

    def _summarise_portfolio(self, ef) -> dict[str, float]:
        try:
            expected_ret, volatility, sharpe = ef.portfolio_performance(
                verbose=False,
                risk_free_rate=self._risk_free_rate,
            )
        except Exception as err:  # pragma: no cover - defensive guard
            raise OptimizationError(
                strategy_name=self.name,
                message=f"Failed to compute portfolio performance: {err}",
            ) from err

        return {
            "expected_return": float(expected_ret),
            "volatility": float(volatility),
            "sharpe_ratio": float(sharpe),
        }

    @staticmethod
    def _indices_for(index_map: dict[str, int], tickers: Sequence[str]) -> list[int]:
        if not isinstance(tickers, Sequence):  # Defensive guard for dynamic inputs.
            tickers = list(tickers)
        return [index_map[t] for t in tickers if t in index_map]
