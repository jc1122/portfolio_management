"""Service wrapper around the backtesting engine."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence

import pandas as pd

from portfolio_management.backtesting import (
    BacktestConfig,
    BacktestEngine,
    PerformanceMetrics,
    RebalanceEvent,
)
from portfolio_management.core.exceptions import BacktestError, InsufficientHistoryError
from portfolio_management.portfolio import PortfolioStrategy

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class BacktestRequest:
    """Inputs required to run a backtest."""

    config: BacktestConfig
    strategy: PortfolioStrategy
    prices: pd.DataFrame
    returns: pd.DataFrame
    classifications: dict[str, str] | None = None
    preselection: Any = None
    membership_policy: Any = None
    cache: Any = None
    output_dir: Path | None = None
    save_trades: bool = False
    visualize: bool = True
    verbose: bool = False


@dataclass(frozen=True)
class BacktestResult:
    """Represents the outcome of a backtest run."""

    equity_curve: pd.DataFrame
    metrics: PerformanceMetrics
    rebalance_events: Sequence[RebalanceEvent]
    output_dir: Path | None


class BacktestService:
    """Orchestrates execution of a backtest via :class:`BacktestEngine`."""

    def __init__(
        self,
        *,
        engine_factory: Callable[..., BacktestEngine] | None = None,
        results_printer: Callable[[PerformanceMetrics, bool], None] | None = None,
        results_saver: Callable[
            [Path, BacktestConfig, pd.DataFrame, Sequence[RebalanceEvent], PerformanceMetrics, bool, bool, bool],
            None,
        ]
        | None = None,
        cache_reporter: Callable[[Any], None] | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._engine_factory = engine_factory or BacktestEngine
        self._results_printer = results_printer
        self._results_saver = results_saver
        self._cache_reporter = cache_reporter
        self._logger = logger or _LOGGER

    def run(self, request: BacktestRequest) -> BacktestResult:
        """Execute a backtest and optionally persist the outputs."""

        self._logger.info(
            "Starting backtest: start=%s end=%s strategy=%s",
            request.config.start_date,
            request.config.end_date,
            request.strategy.__class__.__name__,
        )

        engine = self._engine_factory(
            config=request.config,
            strategy=request.strategy,
            prices=request.prices,
            returns=request.returns,
            classifications=request.classifications,
            preselection=request.preselection,
            membership_policy=request.membership_policy,
            cache=request.cache,
        )

        try:
            equity_curve, metrics, rebalance_events = engine.run()
        except (BacktestError, InsufficientHistoryError):
            self._logger.exception("Backtest run failed")
            raise

        if self._results_printer is not None:
            self._results_printer(metrics, request.verbose)

        if request.cache is not None and request.verbose and self._cache_reporter is not None:
            self._cache_reporter(request.cache)

        if request.output_dir is not None and self._results_saver is not None:
            request.output_dir.mkdir(parents=True, exist_ok=True)
            self._results_saver(
                request.output_dir,
                request.config,
                equity_curve,
                rebalance_events,
                metrics,
                request.save_trades,
                request.visualize,
                request.verbose,
            )

        self._logger.info(
            "Backtest completed: final_value=%.2f sharpe=%.2f",
            metrics.final_value,
            metrics.sharpe_ratio,
        )

        return BacktestResult(
            equity_curve=equity_curve,
            metrics=metrics,
            rebalance_events=rebalance_events,
            output_dir=request.output_dir,
        )


__all__ = ["BacktestRequest", "BacktestResult", "BacktestService"]
