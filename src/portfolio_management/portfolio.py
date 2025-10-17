"""Portfolio construction strategies and utilities.

This module provides a unified interface for constructing portfolios using
various allocation strategies (equal-weight, risk parity, mean-variance).
It includes constraint enforcement, rebalancing logic, and strategy orchestration.
"""

from __future__ import annotations

import importlib
import logging
from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import ClassVar

import numpy as np
import pandas as pd

from .exceptions import (
    ConstraintViolationError,
    DependencyError,
    InsufficientDataError,
    InvalidStrategyError,
    OptimizationError,
    PortfolioConstructionError,
)

logger = logging.getLogger(__name__)


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


class PortfolioConstructor:
    """Coordinate portfolio strategy selection and construction."""

    def __init__(self, constraints: PortfolioConstraints | None = None) -> None:
        """Initialise the constructor with optional default constraints."""
        self._default_constraints = constraints or PortfolioConstraints()
        self._strategies: dict[str, PortfolioStrategy] = {}

        # Register baseline strategies
        self.register_strategy(StrategyType.EQUAL_WEIGHT.value, EqualWeightStrategy())
        self.register_strategy(StrategyType.RISK_PARITY.value, RiskParityStrategy())
        self.register_strategy(
            "mean_variance_max_sharpe",
            MeanVarianceStrategy("max_sharpe"),
        )
        self.register_strategy(
            "mean_variance_min_vol",
            MeanVarianceStrategy("min_volatility"),
        )

    def register_strategy(self, name: str, strategy: PortfolioStrategy) -> None:
        """Register a strategy implementation under the provided name."""
        self._strategies[name] = strategy

    def list_strategies(self) -> list[str]:
        """Return the registered strategy names."""
        return sorted(self._strategies)

    def construct(
        self,
        strategy_name: str,
        returns: pd.DataFrame,
        constraints: PortfolioConstraints | None = None,
        asset_classes: pd.Series | None = None,
    ) -> Portfolio:
        """Construct a portfolio using the requested strategy."""
        strategy = self._strategies.get(strategy_name)
        if strategy is None:
            msg = (
                f"Unknown strategy '{strategy_name}'. "
                f"Available strategies: {', '.join(self.list_strategies())}"
            )
            raise InvalidStrategyError(msg)

        active_constraints = constraints or self._default_constraints
        return strategy.construct(returns, active_constraints, asset_classes)

    def compare_strategies(
        self,
        strategy_names: Sequence[str],
        returns: pd.DataFrame,
        constraints: PortfolioConstraints | None = None,
        asset_classes: pd.Series | None = None,
    ) -> pd.DataFrame:
        """Construct and compare multiple strategies."""
        portfolios: dict[str, pd.Series] = {}
        for name in strategy_names:
            try:
                portfolio = self.construct(name, returns, constraints, asset_classes)
            except (
                PortfolioConstructionError
            ) as err:  # pragma: no cover - tolerant comparison
                logger.warning("Strategy '%s' failed: %s", name, err)
                continue
            portfolios[name] = portfolio.weights

        if not portfolios:
            msg = "All requested strategies failed to construct portfolios."
            raise RuntimeError(msg)

        return pd.DataFrame(portfolios).fillna(0.0)


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
