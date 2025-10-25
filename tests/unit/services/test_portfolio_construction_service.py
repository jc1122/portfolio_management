from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from portfolio_management.portfolio import PortfolioConstraints
from portfolio_management.services.portfolio_construction import (
    PortfolioConstructionService,
)


def _write_returns(tmp_path: Path) -> Path:
    df = pd.DataFrame(
        {
            "AAA": [0.01, 0.02, -0.01, 0.005],
            "BBB": [0.0, 0.01, 0.015, -0.005],
            "CCC": [0.02, -0.015, 0.01, 0.007],
        },
        index=pd.date_range("2020-01-01", periods=4, freq="D"),
    )
    path = tmp_path / "returns.csv"
    df.to_csv(path)
    return path


def _write_classifications(tmp_path: Path) -> Path:
    df = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB", "CCC"],
            "asset_class": ["equity", "equity", "fixed_income"],
        }
    )
    path = tmp_path / "classifications.csv"
    df.to_csv(path, index=False)
    return path


def test_construct_single_strategy(tmp_path: Path) -> None:
    returns_path = _write_returns(tmp_path)
    classes_path = _write_classifications(tmp_path)

    service = PortfolioConstructionService()
    constraints = PortfolioConstraints(
        max_weight=1.0,
        min_weight=0.0,
        max_equity_exposure=1.0,
        min_bond_exposure=0.0,
    )

    result = service.run_workflow(
        returns=returns_path,
        constraints=constraints,
        strategy="equal_weight",
        asset_classes=classes_path,
    )

    assert result.portfolio is not None
    weights = result.portfolio.weights
    assert pytest.approx(weights.sum(), rel=1e-6) == 1.0
    assert set(weights.index) == {"AAA", "BBB", "CCC"}


def test_compare_strategies(tmp_path: Path) -> None:
    returns_path = _write_returns(tmp_path)

    service = PortfolioConstructionService()
    constraints = PortfolioConstraints(
        max_weight=1.0,
        min_bond_exposure=0.0,
        max_equity_exposure=1.0,
    )

    result = service.run_workflow(
        returns=returns_path,
        constraints=constraints,
        compare=True,
    )

    assert result.comparison is not None
    assert set(result.comparison.columns) == set(result.strategies_evaluated)
    assert not result.comparison.empty


def test_missing_classification_columns_returns_none(tmp_path: Path) -> None:
    returns_path = _write_returns(tmp_path)
    bad_path = tmp_path / "bad.csv"
    pd.DataFrame({"ticker": ["AAA"], "not_asset_class": ["equity"]}).to_csv(
        bad_path, index=False
    )

    service = PortfolioConstructionService()
    constraints = PortfolioConstraints(
        max_weight=1.0,
        min_bond_exposure=0.0,
        max_equity_exposure=1.0,
    )

    result = service.run_workflow(
        returns=returns_path,
        constraints=constraints,
        strategy="equal_weight",
        asset_classes=bad_path,
    )

    assert result.asset_classes is None
    assert result.portfolio is not None
