"""Mean-variance optimization strategy."""

from __future__ import annotations

import importlib
import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING, ClassVar

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
from .risk_parity import RiskParityStrategy

if TYPE_CHECKING:
    from portfolio_management.portfolio.constraints.models import PortfolioConstraints
    from portfolio_management.portfolio.statistics.rolling_statistics import (
        RollingStatistics,
    )

logger = logging.getLogger(__name__)

LARGE_UNIVERSE_THRESHOLD = 300


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
        statistics_cache: RollingStatistics | None = None,
    ) -> None:
        """Initialise the strategy configuration.

        Args:
            objective: Optimization objective
            risk_free_rate: Risk-free rate for Sharpe ratio calculation
            min_periods: Minimum periods for estimation
            statistics_cache: Optional statistics cache to avoid redundant calculations

        """
        if objective not in self._VALID_OBJECTIVES:
            msg = (
                f"Invalid objective '{objective}'. Expected one of "
                f"{sorted(self._VALID_OBJECTIVES)}."
            )
            raise ValueError(msg)

        self._objective = objective
        self._risk_free_rate = risk_free_rate
        self._min_periods = min_periods
        self._statistics_cache = statistics_cache
        self._cached_signature: (
            tuple[tuple[str, ...], tuple[pd.Timestamp, ...]] | None
        ) = None
        self._cached_weights: pd.Series | None = None
        self._cached_metadata: dict[str, float] | None = None

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
        efficient_frontier_cls, expected_returns, risk_models, objective_functions = (
            self._load_backend()
        )

        self._validate_returns(returns)
        prepared_returns = self._prepare_returns(returns)
        self._validate_returns(prepared_returns)
        n_assets = prepared_returns.shape[1]

        signature = (
            tuple(prepared_returns.columns),
            tuple(prepared_returns.index),
        )
        if (
            self._cached_signature == signature
            and self._cached_weights is not None
            and self._cached_metadata is not None
        ):
            return Portfolio(
                weights=self._cached_weights.copy(),
                strategy=self.name,
                metadata={**self._cached_metadata},
            )

        if n_assets > LARGE_UNIVERSE_THRESHOLD:
            mu = prepared_returns.mean() * 252
            cov_matrix = prepared_returns.cov() * 252

            weights, performance = self._analytic_tangency_fallback(
                mu,
                cov_matrix,
                constraints,
            )
            RiskParityStrategy.validate_constraints(weights, constraints, asset_classes)
            return Portfolio(
                weights=weights,
                strategy=self.name,
                metadata={
                    "n_assets": int(weights.size),
                    **performance,
                    "objective": self._objective,
                    "method": "analytic_tangency_fallback",
                },
            )

        mu, cov_matrix = self._estimate_moments(
            prepared_returns,
            expected_returns,
            risk_models,
        )

        attempts = [
            {
                "cov": cov_matrix,
                "solver": None,
                "l2_gamma": None,
                "objective": self._objective,
            },
        ]

        if self._objective == "max_sharpe":
            reg_cov_array = (
                cov_matrix.to_numpy() + np.eye(len(cov_matrix), dtype=float) * 1e-4
            )
            regularised_cov = pd.DataFrame(
                reg_cov_array,
                index=cov_matrix.index,
                columns=cov_matrix.columns,
            )
            attempts.append(
                {
                    "cov": regularised_cov,
                    "solver": "ECOS",
                    "l2_gamma": 1e-3,
                    "objective": "max_sharpe",
                },
            )
            attempts.append(
                {
                    "cov": regularised_cov,
                    "solver": "ECOS",
                    "l2_gamma": 1e-3,
                    "objective": "min_volatility",
                },
            )

        final_weights: pd.Series | None = None
        final_ef = None
        last_error: OptimizationError | None = None

        for attempt in attempts:
            try:
                candidate_ef = self._build_frontier(
                    efficient_frontier_cls,
                    mu,
                    attempt["cov"],
                    constraints,
                    asset_classes,
                )
                if attempt["l2_gamma"]:
                    # Import objective_functions only when needed
                    objective_functions = importlib.import_module(
                        "pypfopt.objective_functions",
                    )
                    candidate_ef.add_objective(
                        objective_functions.L2_reg,
                        gamma=attempt["l2_gamma"],
                    )
                if attempt["solver"]:
                    candidate_ef._solver = attempt["solver"]
                self._optimise_frontier(candidate_ef, objective=attempt["objective"])
                weights_candidate = self._extract_weights(candidate_ef)
                weight_sum = float(weights_candidate.sum())
                if weight_sum <= 0:
                    last_error = OptimizationError(
                        strategy_name=self.name,
                        message="Optimisation produced non-positive total weight.",
                    )
                    continue
                final_weights = weights_candidate / weight_sum
                final_ef = candidate_ef
                break
            except OptimizationError as error:
                last_error = error
                continue

        if final_weights is None or final_ef is None:
            raise (
                last_error
                if last_error
                else OptimizationError(
                    strategy_name=self.name,
                    message="Mean-variance optimisation failed for all fallback strategies.",
                )
            )

        weights = self._enforce_weight_bounds(final_weights, constraints)
        ef = final_ef
        try:
            RiskParityStrategy.validate_constraints(weights, constraints, asset_classes)
            performance = self._summarise_portfolio(ef)
        except ConstraintViolationError:
            fallback_weights = pd.Series(
                np.full(
                    len(prepared_returns.columns),
                    1.0 / len(prepared_returns.columns),
                ),
                index=prepared_returns.columns,
                dtype=float,
            )
            RiskParityStrategy.validate_constraints(
                fallback_weights,
                constraints,
                asset_classes,
            )
            cov_matrix = prepared_returns.cov() * 252
            mu_vector = prepared_returns.mean() * 252
            exp_ret = float(fallback_weights @ mu_vector)
            vol = float(np.sqrt(fallback_weights @ cov_matrix @ fallback_weights))
            sharpe = exp_ret / vol if vol > 0 else 0.0
            metadata = {
                "n_assets": int(fallback_weights.size),
                "expected_return": exp_ret,
                "volatility": vol,
                "sharpe_ratio": sharpe,
                "objective": self._objective,
                "method": "fallback_equal_weight",
            }
            self._cached_signature = signature
            self._cached_weights = fallback_weights.copy()
            self._cached_metadata = metadata.copy()
            return Portfolio(
                weights=fallback_weights,
                strategy=self.name,
                metadata=metadata,
            )
        performance = self._summarise_portfolio(ef)

        metadata = {
            "n_assets": int(weights.size),
            **performance,
            "objective": self._objective,
        }
        self._cached_signature = signature
        self._cached_weights = weights.copy()
        self._cached_metadata = metadata.copy()
        return Portfolio(
            weights=weights,
            strategy=self.name,
            metadata=metadata,
        )

    def _load_backend(self):
        try:
            module = importlib.import_module("pypfopt")
            expected_returns = importlib.import_module("pypfopt.expected_returns")
            risk_models = importlib.import_module("pypfopt.risk_models")
            try:
                objective_functions = importlib.import_module(
                    "pypfopt.objective_functions",
                )
            except ImportError:
                objective_functions = None
        except ImportError as err:
            msg = (
                "PyPortfolioOpt is required for mean-variance optimisation. "
                "Install it with `pip install PyPortfolioOpt`."
            )
            raise DependencyError(
                dependency_name="PyPortfolioOpt",
                message=msg,
            ) from err

        return (
            module.EfficientFrontier,
            expected_returns,
            risk_models,
            objective_functions,
        )

    def _prepare_returns(self, returns: pd.DataFrame) -> pd.DataFrame:
        """Replace invalid observations and drop assets without complete history."""
        sanitized = returns.replace([np.inf, -np.inf], np.nan)

        # Drop assets that have missing observations in the estimation window.
        valid_assets = sanitized.columns[sanitized.notna().all()]
        sanitized = sanitized[valid_assets]

        sanitized = sanitized.dropna(axis=0, how="any")
        if sanitized.empty:
            raise InsufficientDataError(
                required_periods=self.min_history_periods,
                available_periods=0,
                message="No valid return observations after sanitising data.",
            )
        return sanitized

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
        # Use cached statistics if available
        if self._statistics_cache is not None:
            # Populate cache metadata for consistency without relying on it
            # to drive the optimisation path.
            self._statistics_cache.get_statistics(returns, annualize=False)

        # Original implementation
        mu = expected_returns.mean_historical_return(returns, frequency=252)
        if hasattr(risk_models, "CovarianceShrinkage"):
            try:
                shrinker = risk_models.CovarianceShrinkage(
                    returns,
                    frequency=252,
                    returns_data=True,
                )
                cov_matrix = shrinker.ledoit_wolf()
            except (
                ModuleNotFoundError,
                AttributeError,
                ImportError,
                ValueError,
                np.linalg.LinAlgError,
            ):
                cov_matrix = self._fallback_covariance(returns, risk_models)
        else:
            cov_matrix = self._fallback_covariance(returns, risk_models)

        # Ensure covariance matrix is positive semi-definite to keep the solver stable.
        cov_array = cov_matrix.to_numpy()
        eigvals = np.linalg.eigvalsh(cov_array)
        if np.any(eigvals < 0):
            adjustment = np.eye(len(cov_matrix), dtype=float) * (
                abs(eigvals.min()) + 1e-6
            )
            cov_array = cov_array + adjustment
        # Add a small jitter to improve conditioning even when matrix is PSD.
        cov_array = cov_array + np.eye(len(cov_matrix), dtype=float) * 1e-6
        cov_matrix = pd.DataFrame(
            cov_array,
            index=cov_matrix.index,
            columns=cov_matrix.columns,
        )

        return mu, cov_matrix

    def _fallback_covariance(self, returns: pd.DataFrame, risk_models) -> pd.DataFrame:
        """Compute a regularised covariance matrix without optional dependencies."""
        cov_matrix = risk_models.sample_cov(returns, frequency=252)
        base = cov_matrix.to_numpy()
        diag = np.diag(np.diag(base))
        shrinkage_intensity = 0.05
        shrunk = (1 - shrinkage_intensity) * base + shrinkage_intensity * diag
        return pd.DataFrame(
            shrunk,
            index=cov_matrix.index,
            columns=cov_matrix.columns,
        )

    def _analytic_tangency_fallback(
        self,
        mu: pd.Series,
        cov_matrix: pd.DataFrame,
        constraints,
    ) -> tuple[pd.Series, dict[str, float]]:
        """Compute a long-only tangency portfolio using a closed-form approximation."""
        subset = min(200, len(mu))
        diag = np.sqrt(np.diag(cov_matrix.to_numpy()))
        scores = mu.to_numpy() / np.where(diag > 0, diag, np.nan)
        order = np.argsort(np.nan_to_num(scores, nan=-np.inf))
        selected_indices = order[-subset:]
        selected_tickers = mu.index[selected_indices]
        mu_work = mu.loc[selected_tickers]
        cov_work = cov_matrix.loc[selected_tickers, selected_tickers]

        cov_array = cov_work.to_numpy()
        mu_vec = mu_work.to_numpy()
        inv_cov = np.linalg.pinv(cov_array)
        raw = inv_cov @ mu_vec
        raw = np.clip(raw, 0.0, None)
        if not np.any(raw):
            raw = np.ones_like(raw)
        weights = raw / raw.sum()
        series = pd.Series(0.0, index=mu.index)
        series.loc[mu_work.index] = weights
        series = self._enforce_weight_bounds(series, constraints)
        total = float(series.sum())
        if not np.isfinite(total) or total <= 0:
            series = pd.Series(
                np.full(len(series), 1.0 / len(series)),
                index=series.index,
            )
        else:
            series = series / total
        series = series.fillna(0.0)
        weights_array = series.to_numpy()
        full_mu = mu.to_numpy()
        full_cov = cov_matrix.to_numpy()
        exp_return = float(weights_array @ full_mu)
        volatility = float(np.sqrt(weights_array @ full_cov @ weights_array))
        sharpe = exp_return / volatility if volatility > 0 else 0.0
        return series, {
            "expected_return": exp_return,
            "volatility": volatility,
            "sharpe_ratio": sharpe,
        }

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

    def _build_frontier(
        self,
        efficient_frontier_cls,
        mu: pd.Series,
        cov_matrix: pd.DataFrame,
        constraints: PortfolioConstraints,
        asset_classes: pd.Series | None,
    ):
        """Create an EfficientFrontier instance with all applicable constraints."""
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

        return ef

    def _enforce_weight_bounds(
        self,
        weights: pd.Series,
        constraints: PortfolioConstraints,
    ) -> pd.Series:
        """Project weights onto the feasible region defined by portfolio constraints."""
        projected = weights.copy()
        upper = constraints.max_weight
        lower = constraints.min_weight

        if upper < 1.0:
            projected = projected.clip(upper=upper)
        if lower > 0.0:
            projected = projected.clip(lower=lower)

        target_sum = 1.0 if constraints.require_full_investment else projected.sum()
        diff = target_sum - float(projected.sum())
        iteration = 0
        tolerance = 1e-8
        max_iterations = 100

        while abs(diff) > tolerance and iteration < max_iterations:
            if diff > 0:
                room = upper - projected
                room = room[room > 0]
                if room.empty:
                    break
                allocation = room / room.sum()
                projected.loc[allocation.index] += allocation * diff
            else:
                excess = projected - lower
                excess = excess[excess > 0]
                if excess.empty:
                    break
                allocation = excess / excess.sum()
                projected.loc[allocation.index] += allocation * diff

            if upper < 1.0:
                projected = projected.clip(upper=upper)
            if lower > 0.0:
                projected = projected.clip(lower=lower)
            diff = target_sum - float(projected.sum())
            iteration += 1

        if constraints.require_full_investment and projected.sum() > 0:
            projected = projected / projected.sum()

        return projected

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

    def _optimise_frontier(self, ef, objective: str | None = None) -> None:
        target_objective = objective or self._objective
        try:
            if target_objective == "max_sharpe":
                ef.max_sharpe(risk_free_rate=self._risk_free_rate)
            elif target_objective == "min_volatility":
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
