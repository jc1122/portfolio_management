"""Portfolio construction orchestration service."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import pandas as pd

from portfolio_management.core.exceptions import PortfolioConstructionError
from portfolio_management.portfolio import (
    Portfolio,
    PortfolioConstraints,
    PortfolioConstructor,
)

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class PortfolioConstructionConfig:
    """Configuration describing how to construct portfolios."""

    returns_path: Path
    strategy: str = "equal_weight"
    compare: bool = False
    compare_strategies: Sequence[str] | None = None
    classifications_path: Path | None = None
    max_weight: float = 0.25
    min_weight: float = 0.0
    max_equity: float = 0.90
    min_bond: float = 0.10


@dataclass(frozen=True)
class PortfolioConstructionResult:
    """Result of running the portfolio construction workflow."""

    returns: pd.DataFrame
    asset_classes: pd.Series | None
    constraints: PortfolioConstraints
    portfolio: Portfolio | None
    comparison: pd.DataFrame | None
    strategies_used: tuple[str, ...]


class PortfolioConstructionService:
    """Service coordinating portfolio construction workflows."""

    def __init__(self, *, logger: logging.Logger | None = None) -> None:
        self._logger = logger or LOGGER

    def run(self, config: PortfolioConstructionConfig) -> PortfolioConstructionResult:
        """Execute the requested workflow and return its result."""

        returns = self._load_returns(config.returns_path)
        asset_classes = self._load_classifications(config.classifications_path)
        constraints = PortfolioConstraints(
            max_weight=config.max_weight,
            min_weight=config.min_weight,
            max_equity_exposure=config.max_equity,
            min_bond_exposure=config.min_bond,
        )

        constructor = PortfolioConstructor(constraints=constraints)

        if config.compare:
            strategy_names = (
                tuple(config.compare_strategies)
                if config.compare_strategies
                else tuple(constructor.list_strategies())
            )
            comparison = constructor.compare_strategies(
                strategy_names,
                returns,
                constraints,
                asset_classes,
            )
            return PortfolioConstructionResult(
                returns=returns,
                asset_classes=asset_classes,
                constraints=constraints,
                portfolio=None,
                comparison=comparison,
                strategies_used=strategy_names,
            )

        try:
            portfolio = constructor.construct(
                config.strategy,
                returns,
                constraints,
                asset_classes,
            )
        except PortfolioConstructionError:
            self._logger.exception("Portfolio construction failed for strategy '%s'", config.strategy)
            raise

        return PortfolioConstructionResult(
            returns=returns,
            asset_classes=asset_classes,
            constraints=constraints,
            portfolio=portfolio,
            comparison=None,
            strategies_used=(config.strategy,),
        )

    def _load_returns(self, path: Path) -> pd.DataFrame:
        self._logger.debug("Loading returns from %s", path)
        returns = pd.read_csv(path, index_col=0, parse_dates=True)
        if returns.empty:
            self._logger.warning("Returns file is empty: %s", path)
        else:
            self._logger.debug(
                "Loaded returns with %d periods and %d assets",
                len(returns),
                len(returns.columns),
            )
        return returns

    def _load_classifications(self, path: Path | None) -> pd.Series | None:
        if path is None:
            return None
        self._logger.debug("Loading asset classifications from %s", path)
        df = pd.read_csv(path)
        if not {"ticker", "asset_class"}.issubset(df.columns):
            missing = {"ticker", "asset_class"} - set(df.columns)
            self._logger.warning(
                "Classifications CSV missing required columns: %s",
                ", ".join(sorted(missing)),
            )
            return None
        series = df.set_index("ticker")["asset_class"]
        self._logger.debug("Loaded %d asset classifications", len(series))
        return series
