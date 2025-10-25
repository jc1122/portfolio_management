"""Universe management orchestration service."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import pandas as pd

from portfolio_management.assets.universes import UniverseConfigLoader, UniverseManager

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class UniverseComparison:
    """Result of comparing multiple universes."""

    names: tuple[str, ...]
    comparison: pd.DataFrame


@dataclass(frozen=True)
class UniverseManagementResult:
    """Outcome of loading or validating a universe."""

    name: str
    definition: dict[str, Any] | None = None
    datasets: dict[str, pd.DataFrame] | None = None
    validation: Any | None = None


class UniverseManagementService:
    """Service providing programmatic universe management workflows."""

    def __init__(self, *, logger: logging.Logger | None = None) -> None:
        self._logger = logger or LOGGER

    def list_universes(self, config_path: Path) -> list[str]:
        """Return the available universe names."""

        universes = UniverseConfigLoader.load_config(config_path)
        names = sorted(universes)
        self._logger.debug("Loaded %d universes from %s", len(names), config_path)
        return names

    def describe_universe(self, config_path: Path, name: str) -> UniverseManagementResult:
        """Return the raw configuration for a single universe."""

        universes = UniverseConfigLoader.load_config(config_path)
        definition = universes.get(name)
        if definition is None:
            msg = f"Universe '{name}' not found in {config_path}"
            self._logger.error(msg)
            raise KeyError(msg)
        return UniverseManagementResult(name=name, definition=definition)

    def load_universe(
        self,
        *,
        config_path: Path,
        matches_path: Path,
        prices_dir: Path,
        name: str,
    ) -> UniverseManagementResult:
        """Load a universe and return its datasets."""

        matches_df = pd.read_csv(matches_path)
        manager = UniverseManager(config_path, matches_df, prices_dir)
        datasets = manager.load_universe(name) or {}
        if not datasets:
            self._logger.warning("Universe '%s' returned no datasets", name)
        frame_datasets = {
            key: value for key, value in datasets.items() if isinstance(value, pd.DataFrame)
        }
        return UniverseManagementResult(name=name, datasets=frame_datasets)

    def compare_universes(
        self,
        *,
        config_path: Path,
        matches_path: Path,
        prices_dir: Path,
        names: Sequence[str],
    ) -> UniverseComparison:
        """Compare multiple universes and return the resulting dataframe."""

        matches_df = pd.read_csv(matches_path)
        manager = UniverseManager(config_path, matches_df, prices_dir)
        comparison = manager.compare_universes(list(names))
        return UniverseComparison(names=tuple(names), comparison=comparison)

    def validate_universe(
        self,
        *,
        config_path: Path,
        matches_path: Path,
        prices_dir: Path,
        name: str,
    ) -> UniverseManagementResult:
        """Validate a universe definition."""

        matches_df = pd.read_csv(matches_path)
        manager = UniverseManager(config_path, matches_df, prices_dir)
        validation = manager.validate_universe(name)
        return UniverseManagementResult(name=name, validation=validation)
