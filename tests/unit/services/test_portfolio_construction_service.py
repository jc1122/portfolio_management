from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from portfolio_management.portfolio import PortfolioConstraints
from portfolio_management.services import PortfolioConstructionRequest, PortfolioConstructionService


def _sample_returns() -> pd.DataFrame:
    data = {
        "AAA": [0.01, 0.02, -0.01, 0.005],
        "BBB": [0.0, 0.01, 0.015, -0.002],
        "CCC": [0.02, -0.01, 0.005, 0.01],
    }
    return pd.DataFrame(data, index=pd.date_range("2024-01-01", periods=4))


def test_construct_single_strategy_writes_output(tmp_path: Path) -> None:
    returns_path = tmp_path / "returns.csv"
    _sample_returns().to_csv(returns_path)
    output_path = tmp_path / "weights.csv"

    service = PortfolioConstructionService()
    result = service.construct_from_files(
        returns_path=returns_path,
        output_path=output_path,
        strategy="equal_weight",
        compare=False,
        max_weight=0.5,
        min_weight=0.0,
        max_equity=0.9,
        min_bond=0.0,
    )

    assert result.portfolio is not None
    assert result.comparison is None
    assert output_path.exists()
    written = pd.read_csv(output_path, index_col=0)
    assert pytest.approx(float(written["weight"].sum()), rel=1e-6) == 1.0


def test_compare_strategies_uses_custom_constructor() -> None:
    recorded: dict[str, object] = {}

    class StubConstructor:
        def __init__(self, constraints: PortfolioConstraints) -> None:
            self.constraints = constraints

        def list_strategies(self) -> list[str]:
            return ["foo", "bar"]

        def compare_strategies(self, names, returns, constraints, asset_classes):
            recorded["names"] = list(names)
            recorded["constraints"] = constraints
            recorded["asset_classes"] = asset_classes
            return pd.DataFrame({name: returns.iloc[0] * 0 for name in names})

        def construct(self, *args, **kwargs):  # pragma: no cover - not used in test
            raise AssertionError("construct should not be called")

    request = PortfolioConstructionRequest(
        returns=_sample_returns(),
        strategy="equal_weight",
        constraints=PortfolioConstraints(),
        compare=True,
        strategy_names=["foo", "bar"],
    )

    service = PortfolioConstructionService(constructor_factory=lambda _: StubConstructor(_))
    result = service.construct(request)

    assert result.comparison is not None
    assert recorded["names"] == ["foo", "bar"]
    assert recorded["constraints"] is request.constraints
    assert recorded["asset_classes"] is None


def test_construct_from_files_uses_injected_dependencies(tmp_path: Path) -> None:
    returns_path = tmp_path / "returns.csv"
    output_path = tmp_path / "out.csv"
    classes_path = tmp_path / "classes.csv"

    calls: dict[str, Path] = {}

    def load_returns(path: Path) -> pd.DataFrame:
        calls["returns"] = path
        return _sample_returns()

    def load_classes(path: Path | None):
        calls["classes"] = path
        return pd.Series({"AAA": "equity", "BBB": "equity", "CCC": "bond"})

    def write_portfolio(portfolio, path: Path) -> None:
        calls["write"] = path

    service = PortfolioConstructionService(
        returns_loader=load_returns,
        classifications_loader=load_classes,
        portfolio_writer=write_portfolio,
    )

    result = service.construct_from_files(
        returns_path=returns_path,
        output_path=output_path,
        strategy="equal_weight",
        compare=False,
        max_weight=0.6,
        min_weight=0.0,
        max_equity=0.9,
        min_bond=0.0,
        classifications_path=classes_path,
    )

    assert result.portfolio is not None
    assert calls["returns"] == returns_path
    assert calls["classes"] == classes_path
    assert calls["write"] == output_path
