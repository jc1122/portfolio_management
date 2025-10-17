# Phase 4: Portfolio Construction - Implementation Plan

**Document Version:** 1.0
**Date Created:** October 16, 2025
**Status:** Ready to Start
**Objective:** Implement portfolio construction strategies with configurable allocation engines

______________________________________________________________________

## Executive Summary

### Overview

Phase 4 implements the core portfolio construction engine that transforms selected universe assets into actionable portfolio weights. This phase builds on the completed Phase 3 infrastructure (asset selection, classification, returns, universes) to deliver three allocation strategies: equal-weight (baseline), risk parity, and mean-variance optimization.

### Task Tracker (Updated 2025-10-17)

| ID | Task | Status | Notes |
|----|------|--------|-------|
| 1 | Portfolio Exceptions | ✅ Completed – typed fields added, smoke tests updated |
| 2 | Portfolio Data Models | 🚧 In Progress | Ready to resume once exceptions changes propagate |

### Success Criteria

- ✅ Strategy adapter interface with 3 implementations (equal-weight, risk parity, mean-variance)
- ✅ Portfolio constraint system enforcing investment rules (max 25% per asset, min 10% bonds/cash, max 90% equity)
- ✅ Rebalancing logic with configurable cadence and opportunistic bands (±20% default)
- ✅ CLI tool for portfolio construction with strategy selection
- ✅ Comprehensive test coverage (≥80%) with unit, integration, and CLI tests
- ✅ Full documentation with examples and API reference
- ✅ Zero mypy errors, minimal ruff warnings
- ✅ All changes maintain backward compatibility with Phase 3 modules

### Time Estimate

**Total: 20-28 hours** over 3-5 days

- Module implementation: 12-16 hours
- Testing: 5-7 hours
- Documentation: 2-3 hours
- Integration & polish: 1-2 hours

______________________________________________________________________

## Architecture Design

### Module Structure

```
src/portfolio_management/
├── portfolio.py              # NEW: Core portfolio construction module
│   ├── PortfolioStrategy (ABC)
│   ├── EqualWeightStrategy
│   ├── RiskParityStrategy
│   ├── MeanVarianceStrategy
│   ├── PortfolioConstraints
│   ├── RebalanceConfig
│   └── PortfolioConstructor
├── exceptions.py             # EXTEND: Add portfolio-specific exceptions
└── ... (existing modules)

scripts/
└── construct_portfolio.py    # NEW: CLI for portfolio construction

tests/
├── test_portfolio.py         # NEW: Unit tests for strategies
└── scripts/
    └── test_construct_portfolio.py  # NEW: CLI tests

docs/
└── portfolio_construction.md # NEW: Comprehensive guide
```

### Key Design Principles

1. **Strategy Pattern:** All allocation strategies implement a common `PortfolioStrategy` interface
1. **Dependency Injection:** Strategies receive configuration via dataclasses, not global state
1. **Immutability:** Strategies are stateless; all state lives in configuration objects
1. **Composability:** Constraints and rebalancing logic are independent of strategy choice
1. **Testability:** Mock-friendly design with clear interfaces and minimal external dependencies

______________________________________________________________________

## Part 1: Core Module Implementation (12-16 hours)

### Task 1.1: Define Exceptions (30 minutes) - ✅ COMPLETE

**File:** `src/portfolio_management/exceptions.py`

**Add the following exception classes:**

```python
class PortfolioConstructionError(PortfolioManagementError):
    """Base exception for portfolio construction errors."""
    pass


class InvalidStrategyError(PortfolioConstructionError):
    """Raised when an invalid or unsupported strategy is requested."""
    pass


class ConstraintViolationError(PortfolioConstructionError):
    """Raised when portfolio weights violate defined constraints."""

    def __init__(
        self,
        message: str,
        constraint_name: str,
        violated_value: float | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(message, **kwargs)
        self.constraint_name = constraint_name
        self.violated_value = violated_value


class OptimizationError(PortfolioConstructionError):
    """Raised when portfolio optimization fails to converge."""

    def __init__(
        self,
        message: str,
        strategy_name: str,
        **kwargs: object,
    ) -> None:
        super().__init__(message, **kwargs)
        self.strategy_name = strategy_name


class InsufficientDataError(PortfolioConstructionError):
    """Raised when insufficient return data is available for optimization."""

    def __init__(
        self,
        message: str,
        required_periods: int,
        available_periods: int,
        **kwargs: object,
    ) -> None:
        super().__init__(message, **kwargs)
        self.required_periods = required_periods
        self.available_periods = available_periods
```

**Deliverable:** Exception hierarchy extended for portfolio construction

______________________________________________________________________

### Task 1.2: Define Data Models (1-2 hours) - ✅ COMPLETE

**File:** `src/portfolio_management/portfolio.py`

**Create the following dataclasses at the top of the module:**

```python
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
    from collections.abc import Sequence


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
```

**Deliverable:** Core data models with validation and helper methods

______________________________________________________________________

### Task 1.3: Define Strategy Interface (30 minutes) - ✅ COMPLETE

**File:** `src/portfolio_management/portfolio.py` (continue)

**Add the abstract base class:**

```python
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
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the strategy name."""
        pass

    @property
    @abstractmethod
    def min_history_periods(self) -> int:
        """Return minimum number of return periods required."""
        pass
```

**Deliverable:** Strategy interface defining the contract for all implementations

______________________________________________________________________

### Task 1.4: Implement Equal-Weight Strategy (1 hour) - ✅ COMPLETE

**File:** `src/portfolio_management/portfolio.py` (continue)

**Add the equal-weight implementation:**

```python
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
            msg = "Returns DataFrame is empty"
            raise InsufficientDataError(
                msg,
                required_periods=self.min_history_periods,
                available_periods=0,
            )

        if len(returns) < self.min_history_periods:
            msg = (
                f"Insufficient data: {len(returns)} periods available, "
                f"{self.min_history_periods} required"
            )
            raise InsufficientDataError(
                msg,
                required_periods=self.min_history_periods,
                available_periods=len(returns),
            )

        # Calculate equal weights
        n_assets = len(returns.columns)
        equal_weight = 1.0 / n_assets

        # Check if equal weight violates max_weight constraint
        if equal_weight > constraints.max_weight:
            msg = (
                f"Equal weight {equal_weight:.4f} exceeds max_weight "
                f"{constraints.max_weight:.4f} with {n_assets} assets"
            )
            raise ConstraintViolationError(
                msg,
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
            msg = (
                f"Equity exposure {equity_exposure:.4f} exceeds max "
                f"{constraints.max_equity_exposure:.4f}"
            )
            raise ConstraintViolationError(
                msg,
                constraint_name="max_equity_exposure",
                violated_value=equity_exposure,
            )

        # Calculate bond/cash exposure
        bond_mask = asset_classes.str.contains("bond|cash", case=False, na=False)
        bond_tickers = asset_classes[bond_mask].index
        bond_exposure = weights[weights.index.isin(bond_tickers)].sum()

        if bond_exposure < constraints.min_bond_exposure:
            msg = (
                f"Bond/cash exposure {bond_exposure:.4f} below min "
                f"{constraints.min_bond_exposure:.4f}"
            )
            raise ConstraintViolationError(
                msg,
                constraint_name="min_bond_exposure",
                violated_value=bond_exposure,
            )
```

**Deliverable:** Working equal-weight strategy with constraint validation

______________________________________________________________________

### Task 1.5: Implement Risk Parity Strategy (2-3 hours) - ✅ COMPLETE

**File:** `src/portfolio_management/portfolio.py` (continue)

**Dependencies:** Add to `requirements.txt`:

```
riskparityportfolio>=0.2.0
```

**Implementation:**

```python
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
        from .exceptions import (
            DependencyError,
            InsufficientDataError,
            OptimizationError,
        )

        # Check for required library
        try:
            import riskparityportfolio as rpp
        except ImportError as err:
            msg = (
                "riskparityportfolio library required for risk parity strategy. "
                "Install with: pip install riskparityportfolio"
            )
            raise DependencyError(msg, dependency_name="riskparityportfolio") from err

        # Validate inputs
        if returns.empty:
            msg = "Returns DataFrame is empty"
            raise InsufficientDataError(
                msg,
                required_periods=self.min_history_periods,
                available_periods=0,
            )

        if len(returns) < self.min_history_periods:
            msg = (
                f"Insufficient data: {len(returns)} periods available, "
                f"{self.min_history_periods} required"
            )
            raise InsufficientDataError(
                msg,
                required_periods=self.min_history_periods,
                available_periods=len(returns),
            )

        # Calculate covariance matrix
        cov_matrix = returns.cov()

        # Check for positive definiteness
        eigenvalues = np.linalg.eigvalsh(cov_matrix.values)
        if np.any(eigenvalues <= 0):
            msg = (
                "Covariance matrix is not positive definite. "
                "Consider increasing min_periods or removing assets with insufficient data."
            )
            raise OptimizationError(msg, strategy_name=self.name)

        # Prepare constraints for riskparityportfolio
        # Note: riskparityportfolio uses different constraint format
        n_assets = len(returns.columns)

        try:
            # Basic risk parity optimization
            w = rpp.vanilla.design(cov_matrix.values)

            # Apply box constraints
            if constraints.max_weight < 1.0 / n_assets:
                # Need constrained optimization
                w = rpp.constrained_risk_parity.design(
                    cov_matrix.values,
                    w_ub=np.full(n_assets, constraints.max_weight),
                    w_lb=np.full(n_assets, constraints.min_weight),
                )
        except Exception as err:
            msg = f"Risk parity optimization failed: {err}"
            raise OptimizationError(msg, strategy_name=self.name) from err

        # Create weights Series
        weights = pd.Series(w, index=returns.columns)

        # Normalize to ensure sum = 1.0 (numerical stability)
        weights = weights / weights.sum()

        # Validate constraints
        self._validate_constraints(weights, constraints, asset_classes)

        # Calculate risk contributions for metadata
        portfolio_vol = np.sqrt(w @ cov_matrix.values @ w)
        marginal_risk = cov_matrix.values @ w
        risk_contrib = w * marginal_risk / portfolio_vol

        return Portfolio(
            weights=weights,
            strategy=self.name,
            metadata={
                "n_assets": n_assets,
                "portfolio_volatility": portfolio_vol,
                "risk_contributions": dict(zip(returns.columns, risk_contrib)),
            },
        )

    def _validate_constraints(
        self,
        weights: pd.Series,
        constraints: PortfolioConstraints,
        asset_classes: pd.Series | None,
    ) -> None:
        """Validate portfolio constraints."""
        from .exceptions import ConstraintViolationError

        # Check weight bounds
        if (weights > constraints.max_weight + 1e-6).any():
            violators = weights[weights > constraints.max_weight + 1e-6]
            msg = f"Weights exceed max_weight: {violators.to_dict()}"
            raise ConstraintViolationError(
                msg,
                constraint_name="max_weight",
                violated_value=violators.max(),
            )

        # Check asset class constraints if provided
        if asset_classes is not None:
            equity_mask = asset_classes.str.contains("equity", case=False, na=False)
            equity_tickers = asset_classes[equity_mask].index
            equity_exposure = weights[weights.index.isin(equity_tickers)].sum()

            if equity_exposure > constraints.max_equity_exposure + 1e-6:
                msg = (
                    f"Equity exposure {equity_exposure:.4f} exceeds max "
                    f"{constraints.max_equity_exposure:.4f}"
                )
                raise ConstraintViolationError(
                    msg,
                    constraint_name="max_equity_exposure",
                    violated_value=equity_exposure,
                )
```

**Deliverable:** Risk parity strategy with covariance-based optimization

______________________________________________________________________

### Task 1.6: Implement Mean-Variance Strategy (2-3 hours) - 🚧 IN PROGRESS

**File:** `src/portfolio_management/portfolio.py` (continue)

**Dependencies:** Add to `requirements.txt`:

```
PyPortfolioOpt>=1.5.0
cvxpy>=1.3.0
```

**Implementation:**

```python
class MeanVarianceStrategy(PortfolioStrategy):
    """Mean-variance optimization portfolio strategy.

    Constructs efficient portfolios using modern portfolio theory.
    Uses PyPortfolioOpt for optimization with multiple objective options.

    Attributes:
        objective: Optimization objective ('max_sharpe', 'min_volatility', 'efficient_risk')
        risk_free_rate: Annual risk-free rate for Sharpe calculation (default: 0.02)
        min_periods: Minimum periods for estimation (default: 252, ~1 year)
    """

    def __init__(
        self,
        objective: str = "max_sharpe",
        risk_free_rate: float = 0.02,
        min_periods: int = 252,
    ) -> None:
        """Initialize mean-variance strategy.

        Args:
            objective: One of 'max_sharpe', 'min_volatility', 'efficient_risk'
            risk_free_rate: Annual risk-free rate (e.g., 0.02 for 2%)
            min_periods: Minimum periods for estimation
        """
        valid_objectives = {"max_sharpe", "min_volatility", "efficient_risk"}
        if objective not in valid_objectives:
            msg = f"Invalid objective '{objective}', must be one of {valid_objectives}"
            raise ValueError(msg)

        self._objective = objective
        self._risk_free_rate = risk_free_rate
        self._min_periods = min_periods

    @property
    def name(self) -> str:
        """Return the strategy name."""
        return f"mean_variance_{self._objective}"

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
        """Construct a mean-variance optimized portfolio.

        Args:
            returns: DataFrame with returns (assets as columns, dates as index)
            constraints: Portfolio constraints to enforce
            asset_classes: Optional Series mapping tickers to asset classes

        Returns:
            Portfolio with optimized weights

        Raises:
            InsufficientDataError: If insufficient data for estimation
            OptimizationError: If optimization fails to converge
            DependencyError: If PyPortfolioOpt library is not installed
        """
        from .exceptions import (
            DependencyError,
            InsufficientDataError,
            OptimizationError,
        )

        # Check for required library
        try:
            from pypfopt import EfficientFrontier, expected_returns, risk_models
        except ImportError as err:
            msg = (
                "PyPortfolioOpt library required for mean-variance strategy. "
                "Install with: pip install PyPortfolioOpt"
            )
            raise DependencyError(msg, dependency_name="PyPortfolioOpt") from err

        # Validate inputs
        if returns.empty:
            msg = "Returns DataFrame is empty"
            raise InsufficientDataError(
                msg,
                required_periods=self.min_history_periods,
                available_periods=0,
            )

        if len(returns) < self.min_history_periods:
            msg = (
                f"Insufficient data: {len(returns)} periods available, "
                f"{self.min_history_periods} required"
            )
            raise InsufficientDataError(
                msg,
                required_periods=self.min_history_periods,
                available_periods=len(returns),
            )

        # Calculate expected returns and covariance
        mu = expected_returns.mean_historical_return(returns, frequency=252)
        S = risk_models.sample_cov(returns, frequency=252)

        # Initialize efficient frontier with constraints
        ef = EfficientFrontier(
            mu,
            S,
            weight_bounds=(constraints.min_weight, constraints.max_weight),
        )

        # Add sector constraints if provided
        if constraints.sector_limits and asset_classes is not None:
            for sector, limit in constraints.sector_limits.items():
                sector_mask = asset_classes.str.contains(sector, case=False, na=False)
                sector_tickers = asset_classes[sector_mask].index.tolist()
                if sector_tickers:
                    ef.add_constraint(
                        lambda w, tickers=sector_tickers, lim=limit: sum(
                            w[i] for i, t in enumerate(mu.index) if t in tickers
                        )
                        <= lim
                    )

        # Add asset class constraints
        if asset_classes is not None:
            # Equity constraint
            equity_mask = asset_classes.str.contains("equity", case=False, na=False)
            equity_tickers = asset_classes[equity_mask].index.tolist()
            if equity_tickers:
                ef.add_constraint(
                    lambda w, tickers=equity_tickers, limit=constraints.max_equity_exposure: sum(
                        w[i] for i, t in enumerate(mu.index) if t in tickers
                    )
                    <= limit
                )

            # Bond/cash constraint
            bond_mask = asset_classes.str.contains("bond|cash", case=False, na=False)
            bond_tickers = asset_classes[bond_mask].index.tolist()
            if bond_tickers:
                ef.add_constraint(
                    lambda w, tickers=bond_tickers, limit=constraints.min_bond_exposure: sum(
                        w[i] for i, t in enumerate(mu.index) if t in tickers
                    )
                    >= limit
                )

        # Optimize based on objective
        try:
            if self._objective == "max_sharpe":
                ef.max_sharpe(risk_free_rate=self._risk_free_rate)
            elif self._objective == "min_volatility":
                ef.min_volatility()
            elif self._objective == "efficient_risk":
                # Target a moderate risk level (10% annual volatility)
                ef.efficient_risk(target_volatility=0.10)
        except Exception as err:
            msg = f"Optimization failed for {self._objective}: {err}"
            raise OptimizationError(msg, strategy_name=self.name) from err

        # Get cleaned weights (removes near-zero positions)
        cleaned_weights = ef.clean_weights()
        weights = pd.Series(cleaned_weights)

        # Remove zero weights
        weights = weights[weights > 0]

        # Renormalize
        weights = weights / weights.sum()

        # Get performance metrics
        perf = ef.portfolio_performance(
            verbose=False,
            risk_free_rate=self._risk_free_rate,
        )

        return Portfolio(
            weights=weights,
            strategy=self.name,
            metadata={
                "n_assets": len(weights),
                "expected_return": perf[0],
                "volatility": perf[1],
                "sharpe_ratio": perf[2],
                "objective": self._objective,
            },
        )
```

**Deliverable:** Mean-variance strategy with multiple optimization objectives

______________________________________________________________________

### Task 1.7: Implement Portfolio Constructor (2 hours)

**File:** `src/portfolio_management/portfolio.py` (continue)

**Add the orchestration class:**

```python
class PortfolioConstructor:
    """Main orchestrator for portfolio construction.

    Coordinates strategy selection, constraint application, and validation.
    """

    def __init__(
        self,
        constraints: PortfolioConstraints | None = None,
    ) -> None:
        """Initialize portfolio constructor.

        Args:
            constraints: Default constraints (can be overridden per construction)
        """
        self._default_constraints = constraints or PortfolioConstraints()
        self._strategies: dict[str, PortfolioStrategy] = {}

        # Register default strategies
        self.register_strategy("equal_weight", EqualWeightStrategy())
        self.register_strategy("risk_parity", RiskParityStrategy())
        self.register_strategy("mean_variance_max_sharpe", MeanVarianceStrategy("max_sharpe"))
        self.register_strategy("mean_variance_min_vol", MeanVarianceStrategy("min_volatility"))

    def register_strategy(self, name: str, strategy: PortfolioStrategy) -> None:
        """Register a custom strategy.

        Args:
            name: Strategy identifier
            strategy: Strategy implementation
        """
        self._strategies[name] = strategy

    def list_strategies(self) -> list[str]:
        """Return list of registered strategy names."""
        return list(self._strategies.keys())

    def construct(
        self,
        strategy_name: str,
        returns: pd.DataFrame,
        constraints: PortfolioConstraints | None = None,
        asset_classes: pd.Series | None = None,
    ) -> Portfolio:
        """Construct a portfolio using the specified strategy.

        Args:
            strategy_name: Name of registered strategy to use
            returns: DataFrame with returns (assets as columns, dates as index)
            constraints: Optional constraints (uses default if not provided)
            asset_classes: Optional Series mapping tickers to asset classes

        Returns:
            Constructed Portfolio object

        Raises:
            InvalidStrategyError: If strategy_name is not registered
        """
        from .exceptions import InvalidStrategyError

        if strategy_name not in self._strategies:
            msg = (
                f"Unknown strategy '{strategy_name}'. "
                f"Available strategies: {self.list_strategies()}"
            )
            raise InvalidStrategyError(msg)

        strategy = self._strategies[strategy_name]
        active_constraints = constraints or self._default_constraints

        return strategy.construct(returns, active_constraints, asset_classes)

    def compare_strategies(
        self,
        strategy_names: Sequence[str],
        returns: pd.DataFrame,
        constraints: PortfolioConstraints | None = None,
        asset_classes: pd.Series | None = None,
    ) -> pd.DataFrame:
        """Construct portfolios using multiple strategies for comparison.

        Args:
            strategy_names: List of strategy names to compare
            returns: DataFrame with returns
            constraints: Optional constraints
            asset_classes: Optional asset class mappings

        Returns:
            DataFrame with strategies as columns and assets as rows (weights)
        """
        portfolios = {}

        for name in strategy_names:
            try:
                portfolio = self.construct(name, returns, constraints, asset_classes)
                portfolios[name] = portfolio.weights
            except Exception as err:
                # Log error but continue with other strategies
                print(f"Warning: Strategy '{name}' failed: {err}")
                continue

        if not portfolios:
            msg = "All strategies failed to construct portfolios"
            raise RuntimeError(msg)

        # Combine into DataFrame (align indices)
        comparison = pd.DataFrame(portfolios).fillna(0.0)

        return comparison
```

**Deliverable:** Portfolio constructor with strategy registry and comparison tools

______________________________________________________________________

## Part 2: CLI Implementation (2-3 hours)

### Task 2.1: Create CLI Script (2-3 hours)

**File:** `scripts/construct_portfolio.py`

**Implementation:**

```python
#!/usr/bin/env python3
"""CLI for constructing portfolios from universe returns.

Usage:
    python scripts/construct_portfolio.py \\
        --returns data/processed/universe_returns.csv \\
        --strategy equal_weight \\
        --output portfolio_weights.csv

    python scripts/construct_portfolio.py \\
        --returns data/processed/universe_returns.csv \\
        --strategy mean_variance_max_sharpe \\
        --classifications data/processed/classifications.csv \\
        --max-equity 0.80 \\
        --output portfolio_weights.csv \\
        --compare
"""

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from portfolio_management.exceptions import PortfolioConstructionError
from portfolio_management.portfolio import (
    Portfolio,
    PortfolioConstraints,
    PortfolioConstructor,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Construct portfolios using various allocation strategies",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Input/output
    parser.add_argument(
        "--returns",
        type=Path,
        required=True,
        help="Path to returns CSV (assets as columns, dates as index)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Path to output portfolio weights CSV",
    )
    parser.add_argument(
        "--classifications",
        type=Path,
        help="Optional path to asset classifications CSV (ticker, asset_class columns)",
    )

    # Strategy selection
    parser.add_argument(
        "--strategy",
        type=str,
        default="equal_weight",
        choices=[
            "equal_weight",
            "risk_parity",
            "mean_variance_max_sharpe",
            "mean_variance_min_vol",
        ],
        help="Portfolio construction strategy to use",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Compare multiple strategies and output comparison table",
    )

    # Constraints
    parser.add_argument(
        "--max-weight",
        type=float,
        default=0.25,
        help="Maximum weight for any single asset (default: 0.25)",
    )
    parser.add_argument(
        "--min-weight",
        type=float,
        default=0.0,
        help="Minimum weight for any single asset (default: 0.0)",
    )
    parser.add_argument(
        "--max-equity",
        type=float,
        default=0.90,
        help="Maximum total equity exposure (default: 0.90)",
    )
    parser.add_argument(
        "--min-bond",
        type=float,
        default=0.10,
        help="Minimum total bond/cash exposure (default: 0.10)",
    )

    # Output options
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    return parser.parse_args()


def load_returns(path: Path) -> pd.DataFrame:
    """Load returns DataFrame from CSV.

    Args:
        path: Path to returns CSV file

    Returns:
        DataFrame with dates as index, tickers as columns
    """
    logger.info(f"Loading returns from {path}")
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    logger.info(f"Loaded returns: {len(df)} periods, {len(df.columns)} assets")
    return df


def load_classifications(path: Path | None) -> pd.Series | None:
    """Load asset classifications from CSV.

    Args:
        path: Path to classifications CSV (or None)

    Returns:
        Series mapping tickers to asset classes, or None
    """
    if path is None:
        return None

    logger.info(f"Loading classifications from {path}")
    df = pd.read_csv(path)

    if "ticker" not in df.columns or "asset_class" not in df.columns:
        logger.warning("Classifications CSV missing 'ticker' or 'asset_class' columns")
        return None

    series = df.set_index("ticker")["asset_class"]
    logger.info(f"Loaded {len(series)} asset classifications")
    return series


def save_portfolio(portfolio: Portfolio, output_path: Path) -> None:
    """Save portfolio weights to CSV.

    Args:
        portfolio: Portfolio object to save
        output_path: Path to output CSV file
    """
    logger.info(f"Saving portfolio to {output_path}")

    # Create output directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Save weights
    portfolio.weights.to_csv(output_path, header=True)

    logger.info(f"Portfolio saved: {portfolio.get_position_count()} positions")
    logger.info(f"Top 5 holdings:\n{portfolio.get_top_holdings(5)}")


def save_comparison(comparison: pd.DataFrame, output_path: Path) -> None:
    """Save strategy comparison to CSV.

    Args:
        comparison: DataFrame with strategy comparison
        output_path: Path to output CSV file
    """
    logger.info(f"Saving strategy comparison to {output_path}")

    # Create output directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Save comparison
    comparison.to_csv(output_path)

    logger.info(f"Comparison saved: {len(comparison.columns)} strategies")


def main() -> int:
    """Main CLI entry point."""
    args = parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    try:
        # Load data
        returns = load_returns(args.returns)
        asset_classes = load_classifications(args.classifications)

        # Build constraints
        constraints = PortfolioConstraints(
            max_weight=args.max_weight,
            min_weight=args.min_weight,
            max_equity_exposure=args.max_equity,
            min_bond_exposure=args.min_bond,
        )

        # Initialize constructor
        constructor = PortfolioConstructor(constraints=constraints)

        # Compare strategies or construct single portfolio
        if args.compare:
            logger.info("Comparing all available strategies")
            strategies = constructor.list_strategies()
            comparison = constructor.compare_strategies(
                strategies,
                returns,
                constraints,
                asset_classes,
            )
            save_comparison(comparison, args.output)
        else:
            logger.info(f"Constructing portfolio using '{args.strategy}' strategy")
            portfolio = constructor.construct(
                args.strategy,
                returns,
                constraints,
                asset_classes,
            )
            save_portfolio(portfolio, args.output)

        logger.info("✅ Portfolio construction completed successfully")
        return 0

    except PortfolioConstructionError as err:
        logger.error(f"Portfolio construction failed: {err}")
        return 1
    except Exception as err:
        logger.exception(f"Unexpected error: {err}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
```

**Deliverable:** Fully functional CLI with strategy selection and comparison mode

______________________________________________________________________

## Part 3: Testing (5-7 hours)

### Task 3.1: Unit Tests for Strategies (3-4 hours)

**File:** `tests/test_portfolio.py`

**Create comprehensive unit tests covering:**

1. **PortfolioConstraints validation** (30 min)

   - Valid constraint combinations
   - Invalid bounds raising ValueError
   - Edge cases (0.0, 1.0 boundaries)

1. **RebalanceConfig validation** (30 min)

   - Valid configurations
   - Invalid parameters raising ValueError

1. **Portfolio dataclass** (30 min)

   - Valid construction
   - Negative weights rejection
   - Non-normalized weights rejection
   - Helper methods (get_position_count, get_top_holdings)

1. **EqualWeightStrategy** (1 hour)

   - Basic equal weighting
   - Constraint violations
   - Asset class constraints
   - Insufficient data handling

1. **RiskParityStrategy** (1 hour)

   - Basic risk parity construction
   - Covariance estimation
   - Box constraints
   - Missing library handling
   - Singular covariance matrix handling

1. **MeanVarianceStrategy** (1 hour)

   - All three objectives (max_sharpe, min_volatility, efficient_risk)
   - Constraint enforcement
   - Missing library handling
   - Optimization failures

1. **PortfolioConstructor** (30 min)

   - Strategy registration
   - Invalid strategy handling
   - Strategy comparison
   - Default constraints

**Test Structure:**

```python
"""Tests for portfolio construction module."""

import numpy as np
import pandas as pd
import pytest

from portfolio_management.exceptions import (
    ConstraintViolationError,
    InsufficientDataError,
    InvalidStrategyError,
    OptimizationError,
)
from portfolio_management.portfolio import (
    EqualWeightStrategy,
    MeanVarianceStrategy,
    Portfolio,
    PortfolioConstraints,
    PortfolioConstructor,
    RebalanceConfig,
    RiskParityStrategy,
)


class TestPortfolioConstraints:
    """Tests for PortfolioConstraints dataclass."""

    def test_valid_constraints(self):
        """Test valid constraint initialization."""
        constraints = PortfolioConstraints(
            max_weight=0.25,
            min_weight=0.0,
            max_equity_exposure=0.90,
            min_bond_exposure=0.10,
        )
        assert constraints.max_weight == 0.25
        assert constraints.min_weight == 0.0

    def test_invalid_weight_bounds(self):
        """Test invalid weight bounds raise ValueError."""
        with pytest.raises(ValueError, match="Invalid weight bounds"):
            PortfolioConstraints(max_weight=0.1, min_weight=0.2)

    # Add 8-10 more test methods...


class TestEqualWeightStrategy:
    """Tests for equal-weight strategy."""

    @pytest.fixture
    def sample_returns(self):
        """Create sample returns DataFrame."""
        dates = pd.date_range("2020-01-01", periods=100, freq="D")
        tickers = ["AAPL", "MSFT", "GOOGL", "AMZN"]
        data = np.random.randn(100, 4) * 0.02  # 2% daily vol
        return pd.DataFrame(data, index=dates, columns=tickers)

    def test_basic_equal_weight(self, sample_returns):
        """Test basic equal weighting."""
        strategy = EqualWeightStrategy()
        constraints = PortfolioConstraints()

        portfolio = strategy.construct(sample_returns, constraints)

        assert len(portfolio.weights) == 4
        assert np.allclose(portfolio.weights, 0.25)
        assert np.isclose(portfolio.weights.sum(), 1.0)

    # Add 10-15 more test methods...


# Similar test classes for RiskParityStrategy, MeanVarianceStrategy, etc.
```

**Deliverable:** 40-50 unit tests with >90% coverage on portfolio.py

______________________________________________________________________

### Task 3.2: CLI Tests (1-2 hours)

**File:** `tests/scripts/test_construct_portfolio.py`

**Create CLI regression tests:**

```python
"""Tests for construct_portfolio CLI."""

import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest


@pytest.fixture
def test_returns_csv(tmp_path):
    """Create a test returns CSV."""
    dates = pd.date_range("2020-01-01", periods=252, freq="D")
    tickers = ["SPY", "AGG", "GLD", "VNQ"]
    data = {
        "SPY": [0.001] * 252,  # Equity
        "AGG": [0.0002] * 252,  # Bonds
        "GLD": [0.0005] * 252,  # Commodities
        "VNQ": [0.0008] * 252,  # Real estate
    }
    df = pd.DataFrame(data, index=dates)

    csv_path = tmp_path / "test_returns.csv"
    df.to_csv(csv_path)
    return csv_path


@pytest.fixture
def test_classifications_csv(tmp_path):
    """Create a test classifications CSV."""
    data = {
        "ticker": ["SPY", "AGG", "GLD", "VNQ"],
        "asset_class": ["equity", "bond", "commodity", "equity"],
    }
    df = pd.DataFrame(data)

    csv_path = tmp_path / "test_classifications.csv"
    df.to_csv(csv_path, index=False)
    return csv_path


class TestConstructPortfolioCLI:
    """Tests for construct_portfolio.py CLI."""

    def test_equal_weight_construction(self, test_returns_csv, tmp_path):
        """Test equal-weight portfolio construction."""
        output = tmp_path / "portfolio.csv"

        result = subprocess.run(
            [
                sys.executable,
                "scripts/construct_portfolio.py",
                "--returns", str(test_returns_csv),
                "--strategy", "equal_weight",
                "--output", str(output),
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert output.exists()

        # Verify output
        weights = pd.read_csv(output, index_col=0, squeeze=True)
        assert len(weights) == 4
        assert abs(weights.sum() - 1.0) < 0.01

    # Add 8-10 more CLI test methods...
```

**Deliverable:** 10-12 CLI tests covering all strategies and error cases

______________________________________________________________________

### Task 3.3: Integration Tests (1 hour)

**File:** `tests/integration/test_portfolio_integration.py`

**Create end-to-end integration tests:**

```python
"""Integration tests for portfolio construction pipeline."""

import pandas as pd
import pytest

from portfolio_management.portfolio import (
    PortfolioConstraints,
    PortfolioConstructor,
)
from portfolio_management.returns import ReturnCalculator, ReturnConfig
from portfolio_management.selection import AssetSelector, FilterCriteria
from portfolio_management.universes import UniverseManager


class TestPortfolioIntegration:
    """Test end-to-end portfolio construction workflows."""

    def test_universe_to_portfolio_pipeline(self, integration_test_data_dir):
        """Test complete flow from universe to portfolio."""
        # This test would use real fixture data to:
        # 1. Load universe definition
        # 2. Select assets
        # 3. Calculate returns
        # 4. Construct portfolio
        # 5. Validate results
        pass

    # Add 5-8 more integration tests...
```

**Deliverable:** 5-8 integration tests validating end-to-end workflows

______________________________________________________________________

## Part 4: Documentation (2-3 hours)

### Task 4.1: Create Module Documentation (1.5-2 hours)

**File:** `docs/portfolio_construction.md`

**Content outline:**

```markdown
# Portfolio Construction Guide

## Overview
[Introduction to portfolio construction module]

## Concepts
- Strategy pattern and interface
- Portfolio constraints
- Rebalancing logic

## Strategies

### Equal Weight
[Description, use cases, parameters, examples]

### Risk Parity
[Description, use cases, parameters, examples]

### Mean-Variance
[Description, use cases, parameters, examples]

## API Reference

### PortfolioStrategy
[Full API documentation]

### PortfolioConstraints
[Full API documentation]

### Portfolio
[Full API documentation]

## Examples

### Example 1: Basic Portfolio Construction
[Code example with explanation]

### Example 2: Custom Constraints
[Code example with explanation]

### Example 3: Strategy Comparison
[Code example with explanation]

## CLI Usage

### construct_portfolio.py
[Full CLI documentation with examples]

## Advanced Topics

### Custom Strategies
[How to implement custom strategies]

### Constraint Customization
[Advanced constraint scenarios]

### Performance Considerations
[Optimization tips]
```

**Deliverable:** Comprehensive documentation (~1500-2000 words)

______________________________________________________________________

### Task 4.2: Update README and Memory Bank (30 min - 1 hour)

**Files to update:**

1. **README.md**

   - Add portfolio construction section
   - Update workflow diagram
   - Add CLI example for construct_portfolio.py

1. **memory-bank/activeContext.md**

   - Update current focus to Phase 4 in progress
   - Document key decisions

1. **memory-bank/progress.md**

   - Mark Phase 4 as in progress
   - Update metrics table

1. **memory-bank/systemPatterns.md**

   - Document portfolio construction patterns
   - Update component relationships

**Deliverable:** All documentation files updated and synchronized

______________________________________________________________________

## Part 5: Integration & Polish (1-2 hours)

### Task 5.1: Dependencies and Requirements (30 min)

**Update `requirements.txt`:**

```
pandas>=2.3,<3.0
riskparityportfolio>=0.2.0
PyPortfolioOpt>=1.5.0
cvxpy>=1.3.0
numpy>=1.24.0
```

**Update `requirements-dev.txt`:**
(No changes needed, already has test dependencies)

**Deliverable:** Updated requirements files

______________________________________________________________________

### Task 5.2: Run Full Test Suite (30 min)

**Execute complete validation:**

```bash
# Run all tests
python -m pytest -v

# Check coverage
python -m pytest --cov=src/portfolio_management --cov-report=term

# Run mypy
mypy src/ scripts/

# Run ruff
ruff check src/ scripts/ tests/

# Run pre-commit hooks
pre-commit run --all-files
```

**Deliverable:** All tests passing, zero mypy errors, minimal ruff warnings

______________________________________________________________________

### Task 5.3: Update pyproject.toml (15 min)

**Add portfolio.py to per-file ignores if needed:**

```toml
[tool.ruff.lint.per-file-ignores]
# ... existing entries ...
"src/portfolio_management/portfolio.py" = [
  "TRY003",  # Long exception messages
  "PLR0913",  # Too many arguments (acceptable for config classes)
]
```

**Deliverable:** Lint configuration updated

______________________________________________________________________

## Acceptance Criteria

### Functional Requirements

- ✅ Three working strategies: equal-weight, risk parity, mean-variance
- ✅ Constraint system enforcing all investment rules
- ✅ CLI tool with strategy selection and comparison mode
- ✅ Strategies work with real universe data from Phase 3

### Quality Requirements

- ✅ Test coverage ≥80% on new portfolio.py module
- ✅ All tests passing (unit + CLI + integration)
- ✅ Zero mypy errors
- ✅ Ruff warnings ≤50 (all P4 severity)
- ✅ Pre-commit hooks passing

### Documentation Requirements

- ✅ Comprehensive module documentation in docs/
- ✅ All public APIs have docstrings
- ✅ README updated with portfolio construction workflow
- ✅ Memory bank synchronized

### Integration Requirements

- ✅ Works with Phase 3 universe/returns outputs
- ✅ No breaking changes to existing modules
- ✅ CLI follows same patterns as other scripts

______________________________________________________________________

## Risk Mitigation

### Risk 1: Optimization Library Issues

**Mitigation:**

- Graceful degradation with DependencyError
- Clear installation instructions in error messages
- Fallback to equal-weight if optimization fails

### Risk 2: Constraint Infeasibility

**Mitigation:**

- Validate constraints before optimization
- Clear error messages indicating which constraint is violated
- Documentation of common constraint conflicts

### Risk 3: Numerical Instability

**Mitigation:**

- Covariance matrix positive definiteness checks
- Weight normalization after optimization
- Tolerance parameters for sum checks

### Risk 4: Performance Issues

**Mitigation:**

- Cache covariance calculations where possible
- Document expected runtime for large universes
- Provide progress logging for long optimizations

______________________________________________________________________

## Timeline

### Day 1 (6-8 hours)

- Tasks 1.1-1.4: Exceptions, models, interface, equal-weight (3-4 hours)
- Tasks 1.5: Risk parity strategy (2-3 hours)
- Task 3.1 start: Basic unit tests (1 hour)

### Day 2 (6-8 hours)

- Task 1.6: Mean-variance strategy (2-3 hours)
- Task 1.7: Portfolio constructor (2 hours)
- Task 3.1 continue: Complete unit tests (2-3 hours)

### Day 3 (4-6 hours)

- Task 2.1: CLI implementation (2-3 hours)
- Task 3.2: CLI tests (1-2 hours)
- Task 3.3: Integration tests (1 hour)

### Day 4 (3-5 hours)

- Task 4.1: Module documentation (1.5-2 hours)
- Task 4.2: Update README and memory bank (1 hour)
- Tasks 5.1-5.3: Integration and polish (1-2 hours)

______________________________________________________________________

## Success Metrics

After Phase 4 completion:

| Metric | Target | Current | Phase 4 Goal |
|--------|--------|---------|--------------|
| Test count | 171 | 171 | 220-230 |
| Coverage | 85% | 85% | 85%+ |
| Mypy errors | 9 | 9 | ≤9 |
| Ruff warnings | ~30 | ~30 | ≤50 |
| Modules | 14 | 14 | 15 (portfolio.py) |
| Scripts | 5 | 5 | 6 (construct_portfolio.py) |
| Docs | 2 | 2 | 3 (portfolio_construction.md) |

______________________________________________________________________

## Next Phase Preview

**Phase 5: Backtesting Framework** will build on Phase 4 to add:

- Historical simulation engine
- Transaction cost modeling
- Performance analytics (Sharpe, drawdown, turnover)
- Rebalancing execution with opportunistic bands
- Portfolio evolution tracking
- Reporting and visualization

The portfolio construction module from Phase 4 will serve as the core allocation engine, with Phase 5 adding the temporal dimension and realistic trading simulation.
