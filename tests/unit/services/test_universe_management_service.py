from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from portfolio_management.services import UniverseComparison, UniverseList, UniverseManagementService


def test_list_universes_returns_sorted_names(tmp_path: Path) -> None:
    def loader(_path: Path) -> dict[str, Any]:
        return {"z": {}, "a": {}, "m": {}}

    service = UniverseManagementService(config_loader=loader)
    result = service.list_universes(tmp_path / "config.yaml")

    assert isinstance(result, UniverseList)
    assert result.names == ["a", "m", "z"]


def test_compare_universes_uses_manager(tmp_path: Path) -> None:
    matches_path = tmp_path / "matches.csv"
    matches_path.write_text("col\nval\n")

    recorded: dict[str, Any] = {}

    class StubManager:
        def __init__(self, config_path: Path, matches: pd.DataFrame, prices_dir: Path) -> None:
            recorded["config"] = config_path
            recorded["matches"] = matches.shape
            recorded["prices_dir"] = prices_dir

        def compare_universes(self, names: list[str]) -> pd.DataFrame:
            recorded["names"] = names
            return pd.DataFrame({"metric": [1, 2]}, index=names)

        def load_universe(self, name: str):  # pragma: no cover - unused
            raise NotImplementedError

        def validate_universe(self, name: str):  # pragma: no cover - unused
            raise NotImplementedError

    service = UniverseManagementService(
        config_loader=lambda path: {"foo": {}},
        matches_loader=lambda path: pd.read_csv(matches_path),
        manager_factory=lambda config, matches, prices: StubManager(config, matches, prices),
    )

    result = service.compare_universes(
        config_path=tmp_path / "config.yaml",
        matches_path=matches_path,
        prices_dir=tmp_path / "prices",
        names=["foo", "bar"],
    )

    assert isinstance(result, UniverseComparison)
    assert recorded["config"].name == "config.yaml"
    assert recorded["matches"] == (1, 1)
    assert recorded["names"] == ["foo", "bar"]


def test_load_universe_writes_exports(tmp_path: Path) -> None:
    matches_path = tmp_path / "matches.csv"
    matches_path.write_text("ticker\nAAA\n")

    class StubManager:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            pass

        def load_universe(self, name: str):
            return {"holdings": pd.DataFrame({"ticker": ["AAA"], "weight": [1.0]})}

        def compare_universes(self, *_args: Any, **_kwargs: Any):  # pragma: no cover
            raise NotImplementedError

        def validate_universe(self, *_args: Any, **_kwargs: Any):  # pragma: no cover
            raise NotImplementedError

    output_dir = tmp_path / "out"

    service = UniverseManagementService(
        config_loader=lambda path: {"core": {}},
        matches_loader=lambda path: pd.read_csv(matches_path),
        manager_factory=lambda *args: StubManager(),
    )

    service.load_universe(
        config_path=tmp_path / "config.yaml",
        matches_path=matches_path,
        prices_dir=tmp_path / "prices",
        name="core",
        output_dir=output_dir,
    )

    exported = output_dir / "core_holdings.csv"
    assert exported.exists()
    df = pd.read_csv(exported)
    assert list(df.columns) == ["ticker", "weight"]
    assert df.shape == (1, 2)
