"""Service façade for universe management workflows."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence

import pandas as pd

from portfolio_management.assets.universes import UniverseConfigLoader, UniverseManager

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class UniverseList:
    """Represents a collection of available universes."""

    names: Sequence[str]


@dataclass(frozen=True)
class UniverseLoadResult:
    """Result of loading a universe definition."""

    name: str
    artefacts: dict[str, pd.DataFrame | Any]
    output_dir: Path | None = None


@dataclass(frozen=True)
class UniverseComparison:
    """Represents a comparison across multiple universes."""

    table: pd.DataFrame


class UniverseManagementService:
    """High-level orchestration for managing universes."""

    def __init__(
        self,
        *,
        config_loader: Callable[[Path], dict[str, Any]] | None = None,
        matches_loader: Callable[[Path], pd.DataFrame] | None = None,
        manager_factory: Callable[[Path, pd.DataFrame, Path], UniverseManager] | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._config_loader = config_loader or UniverseConfigLoader.load_config
        self._matches_loader = matches_loader or pd.read_csv
        self._manager_factory = manager_factory or UniverseManager
        self._logger = logger or _LOGGER

    def list_universes(self, config_path: Path) -> UniverseList:
        universes = self._config_loader(config_path)
        names = sorted(universes)
        self._logger.debug("Loaded %s universes from %s", len(names), config_path)
        return UniverseList(names=names)

    def show_universe(self, config_path: Path, name: str) -> Any:
        universes = self._config_loader(config_path)
        if name not in universes:
            msg = f"Universe '{name}' not found in configuration {config_path}"
            raise KeyError(msg)
        return universes[name]

    def load_universe(
        self,
        config_path: Path,
        matches_path: Path,
        prices_dir: Path,
        name: str,
        *,
        output_dir: Path | None = None,
    ) -> UniverseLoadResult:
        matches = self._matches_loader(matches_path)
        manager = self._manager_factory(config_path, matches, prices_dir)
        artefacts = manager.load_universe(name)
        if artefacts is None:
            raise KeyError(f"Universe '{name}' not found")
        if output_dir is not None:
            output_dir.mkdir(parents=True, exist_ok=True)
            for key, df in artefacts.items():
                if isinstance(df, pd.DataFrame):
                    df.to_csv(output_dir / f"{name}_{key}.csv", index=False)
        return UniverseLoadResult(name=name, artefacts=artefacts, output_dir=output_dir)

    def compare_universes(
        self,
        config_path: Path,
        matches_path: Path,
        prices_dir: Path,
        names: Sequence[str],
    ) -> UniverseComparison:
        matches = self._matches_loader(matches_path)
        manager = self._manager_factory(config_path, matches, prices_dir)
        comparison = manager.compare_universes(list(names))
        return UniverseComparison(table=comparison)

    def validate_universe(
        self,
        config_path: Path,
        matches_path: Path,
        prices_dir: Path,
        name: str,
    ) -> Any:
        matches = self._matches_loader(matches_path)
        manager = self._manager_factory(config_path, matches, prices_dir)
        return manager.validate_universe(name)


__all__ = [
    "UniverseComparison",
    "UniverseList",
    "UniverseLoadResult",
    "UniverseManagementService",
]
