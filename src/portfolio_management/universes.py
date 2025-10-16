# ruff: noqa
"""Universe management for portfolio construction.

This module provides data models and logic for defining, loading, and managing
investment universes.

Key components:
- UniverseDefinition: A dataclass to hold the definition of a single universe.
- UniverseConfigLoader: A class to load universe definitions from a YAML file.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from src.portfolio_management.classification import AssetClassifier
from src.portfolio_management.exceptions import (
    AssetSelectionError,
    ClassificationError,
    ConfigurationError,
    DataValidationError,
    InsufficientDataError,
    ReturnCalculationError,
    UniverseLoadError,
)
from src.portfolio_management.returns import ReturnCalculator, ReturnConfig
from src.portfolio_management.selection import (
    AssetSelector,
    FilterCriteria,
    SelectedAsset,
)


@dataclass
class UniverseDefinition:
    """Definition of an investment universe."""

    description: str
    filter_criteria: FilterCriteria
    classification_requirements: dict[str, list[str]] = field(default_factory=dict)
    return_config: ReturnConfig = field(default_factory=ReturnConfig)
    constraints: dict[str, int | float] = field(default_factory=dict)

    def validate(self) -> None:
        """Validate the universe definition."""
        self.filter_criteria.validate()
        self.return_config.validate()
        # Add more validation rules as needed


class UniverseConfigLoader:
    """Loads universe definitions from a YAML file."""

    @staticmethod
    def load_config(path: Path) -> dict[str, UniverseDefinition]:
        """Load and parse the universe configuration file."""
        if not path.exists():
            raise ConfigurationError(f"Universe config file not found: {path}")

        try:
            with open(path, encoding="utf-8") as stream:
                config = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            raise ConfigurationError(f"Failed to parse universe config: {exc}") from exc

        if not isinstance(config, dict) or "universes" not in config:
            raise ConfigurationError("'universes' key not found in the config file")

        universe_defs: dict[str, UniverseDefinition] = {}
        for name, u_def in config["universes"].items():
            try:
                filter_criteria = FilterCriteria(**u_def.get("filter_criteria", {}))
                return_config = ReturnConfig(**u_def.get("return_config", {}))
            except (TypeError, ValueError) as exc:
                raise ConfigurationError(
                    f"Invalid configuration for universe '{name}': {exc}",
                ) from exc

            definition = UniverseDefinition(
                description=u_def.get("description", ""),
                filter_criteria=filter_criteria,
                classification_requirements=u_def.get(
                    "classification_requirements", {}
                ),
                return_config=return_config,
                constraints=u_def.get("constraints", {}),
            )

            try:
                definition.validate()
            except ValueError as exc:
                raise ConfigurationError(
                    f"Universe '{name}' failed validation: {exc}",
                ) from exc

            universe_defs[name] = definition

        return universe_defs


class UniverseManager:
    """Manages the creation and loading of investment universes."""

    def __init__(self, config_path: Path, matches_df: pd.DataFrame, prices_dir: Path):
        """Initialize the UniverseManager."""
        self.config_path = config_path
        self.matches_df = matches_df
        self.prices_dir = prices_dir
        self.universes = UniverseConfigLoader.load_config(config_path)
        self.asset_selector = AssetSelector()
        self.asset_classifier = AssetClassifier()
        self.return_calculator = ReturnCalculator()
        self._cache: dict[str, dict[str, pd.DataFrame | pd.Series]] = {}

    def list_universes(self) -> list[str]:
        """List the names of all available universes."""
        return list(self.universes.keys())

    def get_definition(self, name: str) -> UniverseDefinition:
        """Get the definition for a named universe."""
        if name not in self.universes:
            raise ConfigurationError(
                f"Universe '{name}' not found in the configuration."
            )
        return self.universes[name]

    def load_universe(
        self,
        name: str,
        use_cache: bool = True,
        strict: bool = True,
    ) -> dict[str, pd.DataFrame] | None:
        """Load a universe by name.

        Args:
            name: Universe identifier.
            use_cache: Whether to return cached results when available.
            strict: When False, recover from errors by returning ``None`` or partial results.

        """
        logger = logging.getLogger(__name__)

        if use_cache and strict and name in self._cache:
            logger.info("Loading universe '%s' from cache.", name)
            return self._cache[name]

        logger.info("Loading universe '%s' from scratch.", name)

        try:
            definition = self.get_definition(name)
        except ConfigurationError as exc:
            if strict:
                raise
            logger.error("Universe definition lookup failed: %s", exc)
            return None

        try:
            selected_assets = self._select_assets(definition)
        except (AssetSelectionError, DataValidationError) as exc:
            if strict:
                raise UniverseLoadError(f"Asset selection failed: {exc}") from exc
            logger.exception("Asset selection failed: %s", exc)
            return None

        if not selected_assets:
            message = f"No assets selected for universe '{name}'."
            if strict:
                raise InsufficientDataError(message, asset_count=0)
            logger.warning(message)
            return None

        try:
            classified_df = self._classify_assets(selected_assets)
        except (ClassificationError, DataValidationError) as exc:
            if strict:
                raise UniverseLoadError(f"Classification failed: {exc}") from exc
            logger.exception("Classification failed: %s", exc)
            classified_df = pd.DataFrame([asset.__dict__ for asset in selected_assets])

        try:
            classified_df = self._filter_by_classification(classified_df, definition)
        except KeyError as exc:
            if strict:
                raise UniverseLoadError(
                    f"Classification filtering failed: {exc}",
                ) from exc
            logger.exception("Classification filtering failed: %s", exc)

        if classified_df.empty:
            message = f"No assets remain after classification filtering for universe '{name}'."
            if strict:
                raise InsufficientDataError(message, asset_count=0)
            logger.warning(message)
            return None

        final_symbols = set(classified_df["symbol"])
        final_assets = [
            asset for asset in selected_assets if asset.symbol in final_symbols
        ]

        try:
            returns_df = self._calculate_returns(final_assets, definition)
        except (ReturnCalculationError, InsufficientDataError) as exc:
            if strict:
                raise UniverseLoadError(f"Return calculation failed: {exc}") from exc
            logger.exception("Return calculation failed: %s", exc)
            returns_df = pd.DataFrame()

        if "max_assets" in definition.constraints and not returns_df.empty:
            returns_df = returns_df.iloc[:, : int(definition.constraints["max_assets"])]

        universe_data: dict[str, pd.DataFrame | pd.Series] = {
            "assets": pd.DataFrame([asset.__dict__ for asset in final_assets]),
            "classifications": classified_df,
            "returns": returns_df,
            "metadata": pd.Series(definition.__dict__),
        }

        if use_cache and strict:
            self._cache[name] = universe_data

        return universe_data

    def _select_assets(self, definition: UniverseDefinition) -> list[SelectedAsset]:
        """Select assets based on the universe definition."""
        return self.asset_selector.select_assets(
            self.matches_df,
            definition.filter_criteria,
        )

    def _classify_assets(self, assets: list[SelectedAsset]) -> pd.DataFrame:
        """Classify a list of assets."""
        return self.asset_classifier.classify_universe(assets)

    def _filter_by_classification(
        self,
        classified_df: pd.DataFrame,
        definition: UniverseDefinition,
    ) -> pd.DataFrame:
        """Filter classified assets based on requirements."""
        df = classified_df.copy()
        for key, values in definition.classification_requirements.items():
            if key in df.columns:
                df = df[df[key].isin(values)]
        return df

    def _calculate_returns(
        self,
        assets: list[SelectedAsset],
        definition: UniverseDefinition,
    ) -> pd.DataFrame:
        """Calculate returns for a list of assets."""
        return self.return_calculator.load_and_prepare(
            assets,
            self.prices_dir,
            definition.return_config,
        )

    def compare_universes(self, names: list[str]) -> pd.DataFrame:
        """Compare multiple universes."""
        stats = []
        for name in names:
            universe = self.load_universe(name, strict=False)
            if not universe:
                stats.append({"name": name, "error": "Failed to load"})
                continue

            returns_df = universe["returns"]
            stats.append(
                {
                    "name": name,
                    "asset_count": len(universe["assets"]),
                    "mean_return": returns_df.mean().mean() * 252,
                    "volatility": returns_df.std().mean() * (252**0.5),
                },
            )
        return pd.DataFrame(stats)

    def get_universe_overlap(self, name1: str, name2: str) -> set[str]:
        """Get the overlap of assets between two universes."""
        u1 = self.load_universe(name1, strict=False)
        u2 = self.load_universe(name2, strict=False)
        if not u1 or not u2:
            return set()
        return set(u1["assets"]["symbol"]) & set(u2["assets"]["symbol"])

    def validate_universe(self, name: str) -> dict[str, Any]:
        """Validate a universe against its constraints."""
        definition = self.get_definition(name)
        universe = self.load_universe(name, strict=False)
        issues: list[str] = []
        warnings_list: list[str] = []

        if not universe:
            issues.append("Failed to load universe")
            return {
                "is_valid": False,
                "issues": issues,
                "warnings": warnings_list,
                "statistics": {},
            }

        asset_count = len(universe["assets"])
        if (
            "min_assets" in definition.constraints
            and asset_count < definition.constraints["min_assets"]
        ):
            issues.append(
                f"Asset count {asset_count} is below min_assets of {definition.constraints['min_assets']}",
            )
        if (
            "max_assets" in definition.constraints
            and asset_count > definition.constraints["max_assets"]
        ):
            warnings_list.append(
                f"Asset count {asset_count} is above max_assets of {definition.constraints['max_assets']}",
            )

        return {
            "is_valid": not issues,
            "issues": issues,
            "warnings": warnings_list,
            "statistics": {"asset_count": asset_count},
        }
