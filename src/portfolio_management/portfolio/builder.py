"""Portfolio construction orchestration."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Optional

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
    """Coordinate portfolio strategy selection and construction."""

    def __init__(self, constraints: Optional[PortfolioConstraints] = None) -> None:
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
        constraints: Optional[PortfolioConstraints] = None,
        asset_classes: Optional[pd.Series] = None,
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
        constraints: Optional[PortfolioConstraints] = None,
        asset_classes: Optional[pd.Series] = None,
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
