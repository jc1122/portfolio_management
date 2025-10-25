"""Service objects for portfolio construction workflows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Sequence

import pandas as pd

from portfolio_management.portfolio import (
    Portfolio,
    PortfolioConstraints,
    PortfolioConstructor,
    Preselection,
    PreselectionConfig,
    PreselectionMethod,
)


@dataclass(slots=True)
class PortfolioConstructionResult:
    """Result of :class:`PortfolioConstructionService.construct_portfolio`."""

    portfolio: Portfolio
    returns_used: pd.DataFrame
    strategy_name: str
    preselection_applied: bool

    @property
    def weights(self) -> pd.Series:
        """Expose the portfolio weights for convenience."""

        return self.portfolio.weights


@dataclass(slots=True)
class PortfolioComparisonResult:
    """Container for bulk strategy comparisons."""

    comparison: pd.DataFrame
    strategies_evaluated: Sequence[str]


class PortfolioConstructionService:
    """High-level coordinator for portfolio construction workflows."""

    def __init__(
        self,
        *,
        constructor: PortfolioConstructor | None = None,
        default_constraints: PortfolioConstraints | None = None,
        returns_loader: Callable[[Path], pd.DataFrame] | None = None,
        classification_loader: Callable[[Path], pd.Series] | None = None,
    ) -> None:
        if constructor is not None:
            self._constructor = constructor
        else:
            self._constructor = PortfolioConstructor(constraints=default_constraints)
        self._returns_loader = returns_loader or self._default_returns_loader
        self._classification_loader = (
            classification_loader or self._default_classification_loader
        )

    def construct_portfolio(
        self,
        *,
        returns: pd.DataFrame | Path,
        strategy: str,
        constraints: PortfolioConstraints | None = None,
        top_k: int | None = None,
        preselection_method: PreselectionMethod | str = PreselectionMethod.MOMENTUM,
        preselection_date: pd.Timestamp | None = None,
        asset_classes: pd.Series | Path | None = None,
    ) -> PortfolioConstructionResult:
        """Construct a single portfolio from historical returns."""

        returns_df = self._ensure_returns(returns)
        asset_classes_series = self._ensure_asset_classes(asset_classes)

        preselection_applied = False
        if top_k is not None and top_k > 0:
            selected_assets = self._apply_preselection(
                returns_df,
                top_k=top_k,
                method=preselection_method,
                rebalance_date=preselection_date,
            )
            if selected_assets:
                returns_df = returns_df.loc[:, selected_assets]
                preselection_applied = True

        portfolio = self._constructor.construct(
            strategy_name=strategy,
            returns=returns_df,
            constraints=constraints,
            asset_classes=asset_classes_series,
        )

        return PortfolioConstructionResult(
            portfolio=portfolio,
            returns_used=returns_df,
            strategy_name=strategy,
            preselection_applied=preselection_applied,
        )

    def compare_strategies(
        self,
        *,
        returns: pd.DataFrame | Path,
        strategies: Iterable[str],
        constraints: PortfolioConstraints | None = None,
        asset_classes: pd.Series | Path | None = None,
    ) -> PortfolioComparisonResult:
        """Construct several strategies and return a comparison table."""

        returns_df = self._ensure_returns(returns)
        asset_classes_series = self._ensure_asset_classes(asset_classes)
        strategy_list = list(strategies)

        comparison = self._constructor.compare_strategies(
            strategy_list,
            returns_df,
            constraints=constraints,
            asset_classes=asset_classes_series,
        )

        return PortfolioComparisonResult(
            comparison=comparison,
            strategies_evaluated=strategy_list,
        )

    def list_strategies(self) -> list[str]:
        """Return the registered strategy names."""

        return self._constructor.list_strategies()

    def register_strategy(self, name: str, strategy: object) -> None:
        """Register an additional strategy with the underlying constructor."""

        self._constructor.register_strategy(name, strategy)

    def _ensure_returns(self, returns: pd.DataFrame | Path) -> pd.DataFrame:
        if isinstance(returns, pd.DataFrame):
            return returns.copy()
        return self._returns_loader(Path(returns))

    def _ensure_asset_classes(
        self, asset_classes: pd.Series | Path | None
    ) -> pd.Series | None:
        if asset_classes is None:
            return None
        if isinstance(asset_classes, pd.Series):
            return asset_classes.copy()
        return self._classification_loader(Path(asset_classes))

    def _apply_preselection(
        self,
        returns: pd.DataFrame,
        *,
        top_k: int,
        method: PreselectionMethod | str,
        rebalance_date: pd.Timestamp | None,
    ) -> list[str]:
        resolved_method = (
            method if isinstance(method, PreselectionMethod) else PreselectionMethod(method)
        )
        config = PreselectionConfig(method=resolved_method, top_k=top_k)
        preselection = Preselection(config)
        selected = preselection.select_assets(returns, rebalance_date=rebalance_date)
        return selected

    def _default_returns_loader(self, path: Path) -> pd.DataFrame:
        return pd.read_csv(path, index_col=0, parse_dates=True)

    def _default_classification_loader(self, path: Path) -> pd.Series:
        frame = pd.read_csv(path)
        if {"ticker", "asset_class"}.issubset(frame.columns):
            return frame.set_index("ticker")["asset_class"]
        raise ValueError(
            "Classification file must contain 'ticker' and 'asset_class' columns."
        )
