"""Service wrapper for the backtesting engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import pandas as pd

from portfolio_management.backtesting import (
    BacktestConfig,
    BacktestEngine,
    PerformanceMetrics,
    RebalanceEvent,
)
from portfolio_management.portfolio import (
    EqualWeightStrategy,
    MeanVarianceStrategy,
    PortfolioStrategy,
    RiskParityStrategy,
)


@dataclass(slots=True)
class BacktestResult:
    """Outcome of a backtest run."""

    strategy_name: str
    equity_curve: pd.DataFrame
    metrics: PerformanceMetrics
    rebalance_events: list[RebalanceEvent]


class BacktestService:
    """Coordinate backtest execution with dependency injection hooks."""

    def __init__(
        self,
        *,
        engine_cls: type[BacktestEngine] = BacktestEngine,
        strategy_registry: Mapping[str, PortfolioStrategy] | None = None,
    ) -> None:
        self._engine_cls = engine_cls
        if strategy_registry is None:
            strategy_registry = {
                "equal_weight": EqualWeightStrategy(),
                "risk_parity": RiskParityStrategy(),
                "mean_variance": MeanVarianceStrategy(),
            }
        self._strategies = dict(strategy_registry)

    def register_strategy(self, name: str, strategy: PortfolioStrategy) -> None:
        """Register or override a strategy in the service registry."""

        self._strategies[name] = strategy

    def list_strategies(self) -> list[str]:
        """Return available strategy identifiers."""

        return sorted(self._strategies)

    def run_backtest(
        self,
        *,
        config: BacktestConfig,
        strategy: str | PortfolioStrategy,
        prices: pd.DataFrame,
        returns: pd.DataFrame,
        classifications: dict[str, str] | None = None,
        preselection: Any = None,
        membership_policy: Any = None,
        cache: Any = None,
    ) -> BacktestResult:
        """Execute a backtest and return structured results."""

        strategy_obj, strategy_name = self._resolve_strategy(strategy)
        engine = self._engine_cls(
            config=config,
            strategy=strategy_obj,
            prices=prices,
            returns=returns,
            classifications=classifications,
            preselection=preselection,
            membership_policy=membership_policy,
            cache=cache,
        )
        equity_curve, metrics, events = engine.run()
        return BacktestResult(
            strategy_name=strategy_name,
            equity_curve=equity_curve,
            metrics=metrics,
            rebalance_events=events,
        )

    def _resolve_strategy(
        self, strategy: str | PortfolioStrategy
    ) -> tuple[PortfolioStrategy, str]:
        if isinstance(strategy, PortfolioStrategy):
            return strategy, strategy.__class__.__name__
        if strategy not in self._strategies:
            available = ", ".join(sorted(self._strategies))
            raise KeyError(f"Unknown strategy '{strategy}'. Available: {available}")
        return self._strategies[strategy], strategy
