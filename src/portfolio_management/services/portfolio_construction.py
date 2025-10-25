"""Service objects for high-level portfolio construction workflows."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

import pandas as pd

from portfolio_management.core.exceptions import PortfolioConstructionError
from portfolio_management.portfolio import Portfolio, PortfolioConstraints, PortfolioConstructor

logger = logging.getLogger(__name__)


def _default_returns_loader(path: Path) -> pd.DataFrame:
    """Load returns from disk using the repository's CSV conventions."""
    logger.info("Loading returns from %s", path)
    returns = pd.read_csv(path, index_col=0, parse_dates=True)
    if returns.empty:
        logger.warning("Returns file is empty: %s", path)
    else:
        logger.debug(
            "Loaded returns with %d periods and %d assets",
            len(returns),
            len(returns.columns),
        )
    return returns


def _default_classifications_loader(path: Path) -> pd.Series:
    """Load ticker classifications from a CSV with ticker/asset_class columns."""
    logger.info("Loading asset classifications from %s", path)
    classifications = pd.read_csv(path)
    required = {"ticker", "asset_class"}
    if not required.issubset(classifications.columns):
        missing = required - set(classifications.columns)
        logger.warning(
            "Classifications CSV missing required columns: %s",
            ", ".join(sorted(missing)),
        )
        return pd.Series(dtype="object")
    series = classifications.set_index("ticker")["asset_class"]
    logger.debug("Loaded %d asset classifications", len(series))
    return series


@dataclass(slots=True)
class PortfolioConstructionRequest:
    """Parameters describing a portfolio construction workflow."""

    returns: pd.DataFrame
    constraints: PortfolioConstraints
    asset_classes: pd.Series | None = None
    strategy: str | None = None
    compare: bool = False
    comparison_strategies: Sequence[str] | None = None


@dataclass(slots=True)
class PortfolioConstructionResult:
    """Result returned from :class:`PortfolioConstructionService`."""

    returns: pd.DataFrame
    constraints: PortfolioConstraints
    asset_classes: pd.Series | None
    strategy: str | None
    strategies_evaluated: tuple[str, ...]
    portfolio: Portfolio | None
    comparison: pd.DataFrame | None

    @property
    def is_comparison(self) -> bool:
        """Return ``True`` when the result represents a multi-strategy comparison."""

        return self.comparison is not None


class PortfolioConstructionService:
    """High-level service for orchestrating portfolio construction workflows."""

    def __init__(
        self,
        *,
        constructor_factory: Callable[[PortfolioConstraints | None], PortfolioConstructor]
        | None = None,
        returns_loader: Callable[[Path], pd.DataFrame] | None = None,
        classifications_loader: Callable[[Path], pd.Series] | None = None,
    ) -> None:
        self._constructor_factory = (
            constructor_factory or (lambda constraints: PortfolioConstructor(constraints=constraints))
        )
        self._returns_loader = returns_loader or _default_returns_loader
        self._classifications_loader = classifications_loader or _default_classifications_loader

    def load_returns(self, source: Path | pd.DataFrame) -> pd.DataFrame:
        """Load returns from a path or pass through a pre-loaded DataFrame."""

        if isinstance(source, Path):
            return self._returns_loader(source)
        return source

    def load_asset_classes(
        self, source: Path | pd.Series | None
    ) -> pd.Series | None:
        """Load optional asset class series from disk or pass through existing data."""

        if source is None:
            return None
        if isinstance(source, Path):
            series = self._classifications_loader(source)
            if series.empty:
                return None
            return series
        return source

    def construct_portfolio(
        self,
        *,
        returns: pd.DataFrame,
        constraints: PortfolioConstraints,
        strategy: str,
        asset_classes: pd.Series | None = None,
    ) -> Portfolio:
        """Construct a single-strategy portfolio."""

        constructor = self._constructor_factory(constraints)
        return constructor.construct(strategy, returns, constraints, asset_classes)

    def compare_strategies(
        self,
        *,
        returns: pd.DataFrame,
        constraints: PortfolioConstraints,
        strategies: Sequence[str],
        asset_classes: pd.Series | None = None,
    ) -> pd.DataFrame:
        """Construct and compare multiple strategies."""

        constructor = self._constructor_factory(constraints)
        return constructor.compare_strategies(strategies, returns, constraints, asset_classes)

    def run_workflow(
        self,
        *,
        returns: Path | pd.DataFrame,
        constraints: PortfolioConstraints,
        strategy: str | None = None,
        compare: bool = False,
        comparison_strategies: Sequence[str] | None = None,
        asset_classes: Path | pd.Series | None = None,
    ) -> PortfolioConstructionResult:
        """Execute the full portfolio construction workflow."""

        returns_df = self.load_returns(returns)
        classes = self.load_asset_classes(asset_classes)

        constructor = self._constructor_factory(constraints)
        evaluated: tuple[str, ...]
        portfolio: Portfolio | None = None
        comparison: pd.DataFrame | None = None

        if compare:
            strategies = tuple(
                comparison_strategies
                if comparison_strategies is not None
                else constructor.list_strategies()
            )
            logger.info("Comparing %d strategies", len(strategies))
            comparison = constructor.compare_strategies(
                strategies,
                returns_df,
                constraints,
                classes,
            )
            evaluated = tuple(comparison.columns)
        else:
            if strategy is None:
                msg = "A strategy name must be provided when compare=False"
                raise PortfolioConstructionError(msg)
            logger.info("Constructing portfolio using strategy '%s'", strategy)
            portfolio = constructor.construct(
                strategy,
                returns_df,
                constraints,
                classes,
            )
            evaluated = (strategy,)

        return PortfolioConstructionResult(
            returns=returns_df,
            constraints=constraints,
            asset_classes=classes,
            strategy=strategy,
            strategies_evaluated=evaluated,
            portfolio=portfolio,
            comparison=comparison,
        )
