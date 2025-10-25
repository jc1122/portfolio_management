"""Tests for :class:`portfolio_management.services.universe_management`."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from portfolio_management.services import UniverseManagementService


class _StubLoader:
    """Stub loader returning a deterministic configuration mapping."""

    called_with: Path | None = None

    @staticmethod
    def load_config(path: Path) -> dict[str, str]:
        _StubLoader.called_with = path
        return {"b": "second", "a": "first"}


@dataclass
class _StubManager:
    """Stub manager that records the arguments it receives."""

    config_path: Path
    matches: pd.DataFrame
    prices_dir: Path

    def load_universe(self, name: str) -> dict[str, pd.DataFrame]:
        return {"name": pd.Series([name]).to_frame(name="universe")}

    def compare_universes(self, names: list[str]) -> pd.DataFrame:
        return pd.DataFrame({"names": names})

    def validate_universe(self, name: str) -> str:
        return f"validated:{name}"


def test_list_universes_returns_sorted_names(tmp_path: Path) -> None:
    config_path = tmp_path / "universes.yaml"
    config_path.write_text("universes: {}\n")

    service = UniverseManagementService(
        config_loader=_StubLoader,
        manager_cls=_StubManager,
    )

    names = service.list_universes(config_path)

    assert names == ["a", "b"]
    assert _StubLoader.called_with == config_path


def test_load_compare_and_validate_use_stub_manager(tmp_path: Path) -> None:
    config_path = tmp_path / "universes.yaml"
    config_path.write_text("universes: {}\n")
    matches = pd.DataFrame({"symbol": ["AAPL"]})
    prices_dir = tmp_path / "prices"

    service = UniverseManagementService(
        config_loader=_StubLoader,
        manager_cls=_StubManager,
    )

    loaded = service.load_universe(
        config_path=config_path,
        matches=matches,
        prices_dir=prices_dir,
        name="core",
    )
    comparison = service.compare_universes(
        config_path=config_path,
        matches=matches,
        prices_dir=prices_dir,
        names=["core", "alt"],
    )
    validation = service.validate_universe(
        config_path=config_path,
        matches=matches,
        prices_dir=prices_dir,
        name="core",
    )

    assert "name" in loaded
    assert list(comparison["names"]) == ["core", "alt"]
    assert validation == "validated:core"
