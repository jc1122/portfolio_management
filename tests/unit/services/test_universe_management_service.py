from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from portfolio_management.services import (
    UniverseComparison,
    UniverseManagementResult,
    UniverseManagementService,
)
from portfolio_management.services import universe_management as module


@pytest.fixture
def matches_csv(tmp_path: Path) -> Path:
    path = tmp_path / "matches.csv"
    pd.DataFrame({"ticker": ["AAA"], "matched_ticker": ["AAA.US"]}).to_csv(path, index=False)
    return path


def test_list_and_describe_universe(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        module.UniverseConfigLoader,
        "load_config",
        staticmethod(lambda path: {"core": {"assets": ["AAA"]}, "satellite": {}}),
    )
    service = UniverseManagementService()

    names = service.list_universes(Path("config.yaml"))
    assert names == ["core", "satellite"]

    description = service.describe_universe(Path("config.yaml"), "core")
    assert isinstance(description, UniverseManagementResult)
    assert description.definition == {"assets": ["AAA"]}


def test_describe_universe_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        module.UniverseConfigLoader,
        "load_config",
        staticmethod(lambda path: {"only": {}}),
    )
    service = UniverseManagementService()

    with pytest.raises(KeyError):
        service.describe_universe(Path("config.yaml"), "missing")


def test_load_universe_filters_non_dataframes(
    monkeypatch: pytest.MonkeyPatch,
    matches_csv: Path,
    tmp_path: Path,
) -> None:
    def fake_manager(*args: Any, **kwargs: Any) -> Any:
        class _Manager:
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                pass

            def load_universe(self, name: str):
                return {
                    "holdings": pd.DataFrame({"ticker": ["AAA"]}),
                    "metadata": {"count": 1},
                }

            def compare_universes(self, names):  # pragma: no cover - unused in this test
                return pd.DataFrame()

            def validate_universe(self, name):  # pragma: no cover - unused in this test
                return {}

        return _Manager(*args, **kwargs)

    monkeypatch.setattr(module, "UniverseManager", fake_manager)
    monkeypatch.setattr(
        module.UniverseConfigLoader,
        "load_config",
        staticmethod(lambda path: {"core": {}}),
    )

    service = UniverseManagementService()
    result = service.load_universe(
        config_path=Path("config.yaml"),
        matches_path=matches_csv,
        prices_dir=tmp_path,
        name="core",
    )

    assert isinstance(result, UniverseManagementResult)
    assert set(result.datasets) == {"holdings"}


def test_compare_universes(monkeypatch: pytest.MonkeyPatch, matches_csv: Path, tmp_path: Path) -> None:
    comparison_frame = pd.DataFrame({"core": [10]})

    class _Manager:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def load_universe(self, name):  # pragma: no cover - unused
            return {}

        def compare_universes(self, names):
            return comparison_frame

        def validate_universe(self, name):  # pragma: no cover - unused
            return {}

    monkeypatch.setattr(module, "UniverseManager", lambda *args, **kwargs: _Manager())
    monkeypatch.setattr(
        module.UniverseConfigLoader,
        "load_config",
        staticmethod(lambda path: {"core": {}, "sat": {}}),
    )

    service = UniverseManagementService()
    result = service.compare_universes(
        config_path=Path("config.yaml"),
        matches_path=matches_csv,
        prices_dir=tmp_path,
        names=["core", "sat"],
    )

    assert isinstance(result, UniverseComparison)
    assert result.names == ("core", "sat")
    assert result.comparison is comparison_frame


def test_validate_universe(monkeypatch: pytest.MonkeyPatch, matches_csv: Path, tmp_path: Path) -> None:
    class _Manager:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def load_universe(self, name):  # pragma: no cover - unused
            return {}

        def compare_universes(self, names):  # pragma: no cover - unused
            return pd.DataFrame()

        def validate_universe(self, name):
            return {"name": name, "valid": True}

    monkeypatch.setattr(module, "UniverseManager", lambda *args, **kwargs: _Manager())
    monkeypatch.setattr(
        module.UniverseConfigLoader,
        "load_config",
        staticmethod(lambda path: {"core": {}}),
    )

    service = UniverseManagementService()
    result = service.validate_universe(
        config_path=Path("config.yaml"),
        matches_path=matches_csv,
        prices_dir=tmp_path,
        name="core",
    )

    assert isinstance(result, UniverseManagementResult)
    assert result.validation == {"name": "core", "valid": True}
