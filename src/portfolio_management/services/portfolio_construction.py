"""Service for orchestrating portfolio construction workflows."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Sequence

import pandas as pd

from portfolio_management.portfolio import (
    Portfolio,
    PortfolioConstraints,
    PortfolioConstructor,
)

_LOGGER = logging.getLogger(__name__)


def _load_returns(path: Path) -> pd.DataFrame:
    returns = pd.read_csv(path, index_col=0, parse_dates=True)
    if returns.empty:
        _LOGGER.warning("Returns file is empty: %%s", path)
    else:
        _LOGGER.debug(
            "Loaded returns from %%s with %%d periods and %%d assets",
            path,
            len(returns),
            len(returns.columns),
        )
    return returns


def _load_classifications(path: Path | None) -> pd.Series | None:
    if path is None:
        return None
    classifications = pd.read_csv(path)
    required = {"ticker", "asset_class"}
    if not required.issubset(classifications.columns):
        missing = ", ".join(sorted(required - set(classifications.columns)))
        _LOGGER.warning(
            "Classifications file %%s missing required columns: %%s",
            path,
            missing,
        )
        return None
    return classifications.set_index("ticker")["asset_class"]


def _write_portfolio(portfolio: Portfolio, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    portfolio.weights.to_frame(name="weight").to_csv(output_path)


def _write_comparison(comparison: pd.DataFrame, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    comparison.to_csv(output_path)


@dataclass(frozen=True)
class PortfolioConstructionRequest:
    """Inputs required for portfolio construction."""

    returns: pd.DataFrame
    strategy: str
    constraints: PortfolioConstraints
    asset_classes: pd.Series | None = None
    compare: bool = False
    strategy_names: Sequence[str] | None = None
    output_path: Path | None = None


@dataclass(frozen=True)
class PortfolioConstructionResult:
    """Result of running a portfolio construction workflow."""

    portfolio: Portfolio | None
    comparison: pd.DataFrame | None
    constraints: PortfolioConstraints
    strategies: Sequence[str]
    output_path: Path | None


class PortfolioConstructionService:
    """High-level orchestrator for portfolio construction workflows."""

    def __init__(
        self,
        *,
        constructor_factory: Callable[[PortfolioConstraints], PortfolioConstructor] | None = None,
        returns_loader: Callable[[Path], pd.DataFrame] | None = None,
        classifications_loader: Callable[[Path | None], pd.Series | None] | None = None,
        portfolio_writer: Callable[[Portfolio, Path], None] | None = None,
        comparison_writer: Callable[[pd.DataFrame, Path], None] | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._constructor_factory = constructor_factory or PortfolioConstructor
        self._returns_loader = returns_loader or _load_returns
        self._classifications_loader = classifications_loader or _load_classifications
        self._portfolio_writer = portfolio_writer or _write_portfolio
        self._comparison_writer = comparison_writer or _write_comparison
        self._logger = logger or _LOGGER

    def construct(self, request: PortfolioConstructionRequest) -> PortfolioConstructionResult:
        """Construct a portfolio according to the request."""

        constructor = self._constructor_factory(request.constraints)
        if request.compare:
            strategies = list(request.strategy_names or constructor.list_strategies())
            self._logger.info(
                "Comparing strategies: %%s",
                ", ".join(strategies),
            )
            comparison = constructor.compare_strategies(
                strategies,
                request.returns,
                request.constraints,
                request.asset_classes,
            )
            if request.output_path is not None:
                self._comparison_writer(comparison, request.output_path)
            return PortfolioConstructionResult(
                portfolio=None,
                comparison=comparison,
                constraints=request.constraints,
                strategies=strategies,
                output_path=request.output_path,
            )

        self._logger.info("Constructing portfolio using strategy '%s'", request.strategy)
        portfolio = constructor.construct(
            request.strategy,
            request.returns,
            request.constraints,
            request.asset_classes,
        )
        if request.output_path is not None:
            self._portfolio_writer(portfolio, request.output_path)
        return PortfolioConstructionResult(
            portfolio=portfolio,
            comparison=None,
            constraints=request.constraints,
            strategies=[request.strategy],
            output_path=request.output_path,
        )

    def construct_from_files(
        self,
        *,
        returns_path: Path,
        output_path: Path | None,
        strategy: str,
        compare: bool,
        max_weight: float,
        min_weight: float,
        max_equity: float,
        min_bond: float,
        classifications_path: Path | None = None,
        strategies: Iterable[str] | None = None,
    ) -> PortfolioConstructionResult:
        """Convenience wrapper that loads inputs from files."""

        returns = self._returns_loader(returns_path)
        asset_classes = self._classifications_loader(classifications_path)
        constraints = PortfolioConstraints(
            max_weight=max_weight,
            min_weight=min_weight,
            max_equity_exposure=max_equity,
            min_bond_exposure=min_bond,
        )
        request = PortfolioConstructionRequest(
            returns=returns,
            strategy=strategy,
            constraints=constraints,
            asset_classes=asset_classes,
            compare=compare,
            strategy_names=list(strategies) if strategies is not None else None,
            output_path=output_path,
        )
        return self.construct(request)

__all__ = [
    "PortfolioConstructionRequest",
    "PortfolioConstructionResult",
    "PortfolioConstructionService",
]
