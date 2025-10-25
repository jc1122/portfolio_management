"""Backtest orchestration service."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import pandas as pd

from portfolio_management.backtesting import (
    BacktestConfig,
    BacktestEngine,
    PerformanceMetrics,
    RebalanceEvent,
)
from portfolio_management.core.exceptions import BacktestError
from portfolio_management.portfolio import PortfolioStrategy

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class BacktestRequest:
    """Request payload describing a backtest run."""

    config: BacktestConfig
    strategy: PortfolioStrategy
    prices: pd.DataFrame
    returns: pd.DataFrame
    classifications: dict[str, str] | None = None
    preselection: Any = None
    membership_policy: Any = None
    cache: Any = None


@dataclass(frozen=True)
class BacktestResult:
    """Result of executing a backtest."""

    equity_curve: pd.DataFrame
    metrics: PerformanceMetrics
    events: tuple[RebalanceEvent, ...]


class BacktestService:
    """Service coordinating backtest execution."""

    def __init__(
        self,
        *,
        logger: logging.Logger | None = None,
        engine_cls: type[BacktestEngine] = BacktestEngine,
    ) -> None:
        self._logger = logger or LOGGER
        self._engine_cls = engine_cls

    def run(self, request: BacktestRequest) -> BacktestResult:
        """Execute the backtest described by *request*."""

        self._logger.debug(
            "Starting backtest for strategy %s between %s and %s",
            request.strategy.__class__.__name__,
            request.config.start_date,
            request.config.end_date,
        )

        engine = self._engine_cls(
            request.config,
            request.strategy,
            request.prices,
            request.returns,
            classifications=request.classifications,
            preselection=request.preselection,
            membership_policy=request.membership_policy,
            cache=request.cache,
        )

        try:
            equity_curve, metrics, events = engine.run()
        except BacktestError:
            self._logger.exception("Backtest failed for strategy %s", request.strategy)
            raise

        self._logger.debug(
            "Completed backtest with %d events", len(events),
        )
        return BacktestResult(
            equity_curve=equity_curve,
            metrics=metrics,
            events=tuple(events),
        )
