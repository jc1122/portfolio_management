"""Service entry-points for universe management operations."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from portfolio_management.assets.universes import (
    UniverseConfigLoader,
    UniverseDefinition,
    UniverseManager,
)


class UniverseManagementService:
    """Provide programmatic access to universe management workflows."""

    def __init__(
        self,
        *,
        config_loader: type[UniverseConfigLoader] | None = None,
        manager_cls: type[UniverseManager] | None = None,
    ) -> None:
        self._config_loader = config_loader or UniverseConfigLoader
        self._manager_cls = manager_cls or UniverseManager

    def list_universes(self, config_path: Path) -> list[str]:
        """Return available universe names."""

        definitions = self._config_loader.load_config(Path(config_path))
        return sorted(definitions)

    def get_universe_definition(
        self, config_path: Path, name: str
    ) -> UniverseDefinition:
        """Return the parsed definition for a single universe."""

        definitions = self._config_loader.load_config(Path(config_path))
        try:
            return definitions[name]
        except KeyError as exc:  # pragma: no cover - defensive
            available = ", ".join(sorted(definitions))
            raise KeyError(
                f"Unknown universe '{name}'. Available universes: {available}",
            ) from exc

    def load_universe(
        self,
        *,
        config_path: Path,
        matches: pd.DataFrame,
        prices_dir: Path,
        name: str,
    ) -> Mapping[str, Any]:
        """Execute the full load workflow for the requested universe."""

        manager = self._manager_cls(Path(config_path), matches, Path(prices_dir))
        return manager.load_universe(name)

    def compare_universes(
        self,
        *,
        config_path: Path,
        matches: pd.DataFrame,
        prices_dir: Path,
        names: list[str],
    ) -> pd.DataFrame:
        """Compare multiple universes and return the resulting DataFrame."""

        manager = self._manager_cls(Path(config_path), matches, Path(prices_dir))
        return manager.compare_universes(names)

    def validate_universe(
        self,
        *,
        config_path: Path,
        matches: pd.DataFrame,
        prices_dir: Path,
        name: str,
    ) -> Any:
        """Validate a universe configuration and return diagnostics."""

        manager = self._manager_cls(Path(config_path), matches, Path(prices_dir))
        return manager.validate_universe(name)
