"""Orchestrates the construction of portfolios using various strategies.

This module provides the `PortfolioConstructor`, a high-level class that acts as a
factory and manager for different portfolio construction strategies. It allows users
to register custom strategies and construct portfolios by name, applying a consistent
set of constraints.

Key Classes:
    - PortfolioConstructor: Selects and executes portfolio construction strategies.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

import pandas as pd

from ..core.exceptions import InvalidStrategyError, PortfolioConstructionError
from .constraints.models import PortfolioConstraints
from .models import Portfolio, StrategyType
from .strategies.base import PortfolioStrategy
from .strategies.equal_weight import EqualWeightStrategy
from .strategies.mean_variance import MeanVarianceStrategy
from .strategies.risk_parity import RiskParityStrategy

logger = logging.getLogger(__name__)


class PortfolioConstructor:
    """Coordinates portfolio strategy selection and construction.

    This class acts as a factory for portfolio construction, allowing users to
    register different `PortfolioStrategy` implementations and then construct
    portfolios by referencing their registered names. It simplifies the process
    of comparing different strategies under the same constraints.

    It comes with several common strategies pre-registered, such as equal weight,
    minimum volatility, and maximum Sharpe ratio.

    Attributes:
        _default_constraints (PortfolioConstraints): Default constraints to apply
            if none are provided during construction.
        _strategies (dict[str, PortfolioStrategy]): A registry of available
            portfolio construction strategies.

    Example:
        >>> import pandas as pd
        >>> from portfolio_management.portfolio import (
        ...     PortfolioConstructor, PortfolioConstraints
        ... )
        >>>
        >>> import numpy as np
        >>> np.random.seed(42)
        >>> returns = pd.DataFrame({
        ...     'ASSET_A': np.random.normal(0, 0.01, 30),
        ...     'ASSET_B': np.random.normal(0, 0.02, 30),
        ... })
        >>>
        >>> # Initialize with default constraints
        >>> constraints = PortfolioConstraints(max_weight=0.7)
        >>> from portfolio_management.portfolio.strategies.mean_variance import MeanVarianceStrategy
        >>> constructor = PortfolioConstructor(constraints=constraints)
        >>> # The default min_periods for MeanVarianceStrategy is 252. We override it for the example.
        >>> constructor.register_strategy(
        ...     "mean_variance_min_vol",
        ...     MeanVarianceStrategy(objective="min_volatility", min_periods=30)
        ... )
        >>>
        >>> # Construct a minimum volatility portfolio
        >>> portfolio = constructor.construct("mean_variance_min_vol", returns)
        >>> # The exact weights will vary, but the sum should be 1.0
        >>> print(portfolio.weights.sum().round(2))
        1.0
        >>>
        >>> # Compare multiple strategies
        >>> comparison = constructor.compare_strategies(
        ...     ["equal_weight", "mean_variance_min_vol"],
        ...     returns
        ... )
        >>> # The exact weights will vary, but the sums should be 1.0
        >>> print(comparison.sum().round(2))
        equal_weight             1.0
        mean_variance_min_vol    1.0
        dtype: float64

    """

    def __init__(self, constraints: PortfolioConstraints | None = None) -> None:
        """Initialise the constructor with optional default constraints."""
        self._default_constraints = constraints or PortfolioConstraints()
        self._strategies: dict[str, PortfolioStrategy] = {}

        # Register baseline strategies
        self.register_strategy(StrategyType.EQUAL_WEIGHT.value, EqualWeightStrategy())
        self.register_strategy(StrategyType.RISK_PARITY.value, RiskParityStrategy())
        self.register_strategy(
            "mean_variance_max_sharpe",
            MeanVarianceStrategy(objective="max_sharpe"),
        )
        self.register_strategy(
            "mean_variance_min_vol",
            MeanVarianceStrategy(objective="min_volatility"),
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
