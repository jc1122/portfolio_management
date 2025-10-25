from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from portfolio_management.services import (
    PortfolioConstructionConfig,
    PortfolioConstructionService,
)


def _write_returns(tmp_path: Path) -> Path:
    returns = pd.DataFrame(
        {
            "AAA": [0.01, 0.02, -0.01, 0.005],
            "BBB": [0.015, -0.005, 0.02, 0.0],
        },
        index=pd.date_range("2020-01-01", periods=4, freq="D"),
    )
    path = tmp_path / "returns.csv"
    returns.to_csv(path)
    return path


def test_construct_single_strategy(tmp_path: Path) -> None:
    returns_path = _write_returns(tmp_path)
    service = PortfolioConstructionService()
    config = PortfolioConstructionConfig(
        returns_path=returns_path,
        strategy="equal_weight",
        max_weight=0.6,
    )

    result = service.run(config)

    assert result.portfolio is not None
    assert result.comparison is None
    assert result.strategies_used == ("equal_weight",)
    assert pytest.approx(result.portfolio.weights.sum(), rel=1e-9) == 1.0


def test_compare_subset_of_strategies(tmp_path: Path) -> None:
    returns_path = _write_returns(tmp_path)
    service = PortfolioConstructionService()
    config = PortfolioConstructionConfig(
        returns_path=returns_path,
        compare=True,
        compare_strategies=["equal_weight"],
        max_weight=0.6,
    )

    result = service.run(config)

    assert result.portfolio is None
    assert result.comparison is not None
    assert list(result.comparison.columns) == ["equal_weight"]
