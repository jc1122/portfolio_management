"""Tests for :class:`portfolio_management.services.portfolio_construction`."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from portfolio_management.core.exceptions import InvalidStrategyError
from portfolio_management.portfolio import PortfolioConstraints
from portfolio_management.services import PortfolioConstructionService


def test_construct_portfolio_equal_weight(mock_returns: pd.DataFrame) -> None:
    service = PortfolioConstructionService()
    result = service.construct_portfolio(
        returns=mock_returns,
        strategy="equal_weight",
    )

    assert pytest.approx(result.weights.sum(), rel=1e-6) == 1.0
    assert not result.preselection_applied
    assert result.portfolio.strategy == "equal_weight"


def test_construct_portfolio_with_preselection(mock_returns: pd.DataFrame) -> None:
    service = PortfolioConstructionService()
    result = service.construct_portfolio(
        returns=mock_returns,
        strategy="equal_weight",
        top_k=3,
        constraints=PortfolioConstraints(max_weight=0.4, min_weight=0.0),
    )

    assert result.preselection_applied
    assert result.returns_used.shape[1] == 3


def test_construct_portfolio_raises_for_unknown_strategy(mock_returns: pd.DataFrame) -> None:
    service = PortfolioConstructionService()
    with pytest.raises(InvalidStrategyError):
        service.construct_portfolio(returns=mock_returns, strategy="does_not_exist")


def test_compare_strategies_returns_dataframe(mock_returns: pd.DataFrame) -> None:
    service = PortfolioConstructionService()
    comparison = service.compare_strategies(
        returns=mock_returns,
        strategies=["equal_weight", "risk_parity"],
    )

    assert set(comparison.strategies_evaluated) == {"equal_weight", "risk_parity"}
    assert list(comparison.comparison.columns) == sorted(comparison.strategies_evaluated)


def test_construct_portfolio_with_classification_file(tmp_path: Path, mock_returns: pd.DataFrame) -> None:
    classifications = pd.DataFrame(
        {
            "ticker": mock_returns.columns,
            "asset_class": ["equity"] * len(mock_returns.columns),
        }
    )
    path = tmp_path / "classes.csv"
    classifications.to_csv(path, index=False)

    service = PortfolioConstructionService()
    result = service.construct_portfolio(
        returns=mock_returns,
        strategy="equal_weight",
        asset_classes=path,
        constraints=PortfolioConstraints(
            max_weight=0.4,
            min_weight=0.0,
            max_equity_exposure=1.0,
            min_bond_exposure=0.0,
        ),
    )

    assert result.portfolio.weights.index.equals(mock_returns.columns)
