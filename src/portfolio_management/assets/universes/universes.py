"""Orchestrates the creation of investment universes from configuration.

This module brings together asset selection and classification to construct
complete, analysis-ready investment universes. It is the primary entry point
for the business logic layer when it needs to access a defined set of assets
and their associated data, such as historical returns.

Pipeline Position:
    Asset Selection & Classification -> **Universe Loading** -> Portfolio Construction

    1.  **Input**: A universe name and a YAML configuration file that defines
       the rules for one or more universes.
    2.  **Process**:
        - The `UniverseConfigLoader` parses the YAML file into `UniverseDefinition` objects.
        - The `UniverseManager` uses the definition to:
            a. Run the `AssetSelector` to get a filtered list of assets.
            b. Run the `AssetClassifier` on the filtered assets.
            c. Apply any final classification-based filters.
            d. Calculate historical returns for the final asset list.
    3.  **Output**: A dictionary containing DataFrames for the final assets,
       their classifications, and their historical returns.

Key Components:
    - `UniverseManager`: The main engine for loading and managing universes.
    - `UniverseDefinition`: A dataclass that holds the complete configuration for a universe.
    - `UniverseConfigLoader`: A static class for loading universe definitions from YAML.

Example:
    >>> from pathlib import Path
    >>> import pandas as pd
    >>> from portfolio_management.assets.universes import UniverseManager

    # Assume the following are available:
    # - A 'universes.yaml' file in the 'config/' directory.
    # - A 'tradeable_matches.csv' file with asset metadata.
    # - A 'prices/' directory with historical price data.

    # Conceptual example:
    # >>> manager = UniverseManager(
    # ...     config_path=Path("config/universes.yaml"),
    # ...     matches_df=pd.read_csv("data/tradeable_matches.csv"),
    ...     prices_dir=Path("data/prices/")
    # ... )
    # >>>
    # >>> # Load a universe defined in the YAML file
    # >>> my_universe = manager.load_universe("my_equity_universe")
    # >>>
    # >>> if my_universe:
    # ...     print(f"Loaded {len(my_universe['assets'])} assets.")
    # ...     print("Columns in returns table:", my_universe['returns'].columns.tolist())
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from portfolio_management.analytics.indicators import IndicatorConfig
from portfolio_management.analytics.returns import ReturnCalculator, ReturnConfig

from ...core.exceptions import (
    AssetSelectionError,
    ClassificationError,
    ConfigurationError,
    DataValidationError,
    InsufficientDataError,
    ReturnCalculationError,
    UniverseLoadError,
)
from ..classification.classification import AssetClassifier
from ..selection.selection import AssetSelector, FilterCriteria, SelectedAsset


@dataclass
class UniverseDefinition:
    """Represents the complete configuration for a single investment universe.

    This dataclass holds all the parameters needed to construct a universe,
    from initial filtering to final return calculation. It is typically
    instantiated by `UniverseConfigLoader` from a YAML file.

    Attributes:
        description: A human-readable description of the universe.
        filter_criteria: An instance of `FilterCriteria` defining the rules for
            the initial asset selection.
        classification_requirements: A dictionary specifying required classification
            values. Assets not matching these values will be filtered out after
            classification. Example: `{'asset_class': ['equity']}`.
        return_config: A `ReturnConfig` object defining how historical returns
            should be calculated for the assets in the universe.
        constraints: A dictionary of hard constraints for the universe, such as
            `{'max_assets': 100}`.
        technical_indicators: An `IndicatorConfig` object for configuring
            the calculation of technical indicators like SMA or RSI.
    """

    description: str
    filter_criteria: FilterCriteria
    classification_requirements: dict[str, list[str]] = field(default_factory=dict)
    return_config: ReturnConfig = field(default_factory=ReturnConfig)
    constraints: dict[str, int | float] = field(default_factory=dict)
    technical_indicators: IndicatorConfig = field(
        default_factory=IndicatorConfig.disabled
    )

    def validate(self) -> None:
        """Validate the universe definition."""
        self.filter_criteria.validate()
        self.return_config.validate()
        self.technical_indicators.validate()
        # Add more validation rules as needed


class UniverseConfigLoader:
    """Loads and parses universe definitions from a YAML configuration file.

    This is a static utility class that provides a single method, `load_config`,
    to read a YAML file and convert it into a dictionary of `UniverseDefinition`
    objects.

    Configuration (YAML Format):
        The YAML file must have a top-level key `universes`, which contains a
        mapping of universe names to their definitions.

        Example `universes.yaml`:
        ```yaml
        universes:
          us_equity_large_cap:
            description: "US Large Cap Equities"
            filter_criteria:
              min_history_days: 1825 # 5 years
              markets: ["US"]
              categories: ["Stock"]
            classification_requirements:
              asset_class: ["equity"]
              sub_class: ["large_cap"]
            return_config:
              window: 252
              min_periods: 200
        ```
    """

    @staticmethod
    def load_config(path: Path) -> dict[str, UniverseDefinition]:
        """Loads and parses the universe configuration file.

        Args:
            path: The file path to the universe YAML configuration.

        Returns:
            A dictionary mapping universe names to `UniverseDefinition` instances.

        Raises:
            ConfigurationError: If the file is not found, cannot be parsed,
                is badly structured, or contains invalid parameter values.
        """
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
                # Parse technical_indicators configuration if present
                indicators_def = u_def.get("technical_indicators", {})
                if indicators_def:
                    technical_indicators = IndicatorConfig(**indicators_def)
                else:
                    technical_indicators = IndicatorConfig.disabled()
            except (TypeError, ValueError) as exc:
                raise ConfigurationError(
                    f"Invalid configuration for universe '{name}': {exc}",
                ) from exc

            definition = UniverseDefinition(
                description=u_def.get("description", ""),
                filter_criteria=filter_criteria,
                classification_requirements=u_def.get(
                    "classification_requirements",
                    {},
                ),
                return_config=return_config,
                constraints=u_def.get("constraints", {}),
                technical_indicators=technical_indicators,
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
    """Orchestrates the loading and construction of investment universes.

    This class is the main entry point for accessing investment universes. It
    combines configuration, asset metadata, and price data to produce a
    fully-formed universe, including selected assets, their classifications,
    and their historical returns.

    Attributes:
        config_path (Path): Path to the universe YAML configuration file.
        matches_df (pd.DataFrame): DataFrame containing metadata for all
            tradeable assets.
        prices_dir (Path): Path to the directory containing historical price data.
        universes (dict[str, UniverseDefinition]): A dictionary of loaded
            universe definitions, keyed by universe name.
        asset_selector (AssetSelector): An instance of the asset selection engine.
        asset_classifier (AssetClassifier): An instance of the asset classification engine.
        return_calculator (ReturnCalculator): An instance of the return calculation engine.

    Example:
        # This is a conceptual example. In a real scenario, you would provide
        # valid paths and a pre-populated DataFrame.
        #
        # from pathlib import Path
        # import pandas as pd
        #
        # manager = UniverseManager(
        #     config_path=Path("config/universes.yaml"),
        #     matches_df=pd.read_csv("data/tradeable_matches.csv"),
        #     prices_dir=Path("data/prices/")
        # )
        #
        # # List available universes
        # print(manager.list_universes())
        #
        # # Load a specific universe
        # us_equity = manager.load_universe("us_equity_large_cap")
    """

    def __init__(self, config_path: Path, matches_df: pd.DataFrame, prices_dir: Path):
        """Initializes the UniverseManager.

        Args:
            config_path: Path to the universe YAML configuration file.
            matches_df: DataFrame containing metadata for all tradeable assets.
            prices_dir: Path to the directory containing historical price data.
        """
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
                f"Universe '{name}' not found in the configuration.",
            )
        return self.universes[name]

    def load_universe(
        self,
        name: str,
        use_cache: bool = True,
        strict: bool = True,
    ) -> dict[str, pd.DataFrame | pd.Series] | None:
        """Loads and constructs a universe by its configured name.

        This method executes the full universe creation pipeline:
        1. Selects assets based on the universe's `filter_criteria`.
        2. Classifies the selected assets.
        3. Filters the assets based on `classification_requirements`.
        4. Calculates returns for the final set of assets.

        Args:
            name: The name of the universe to load, as defined in the YAML config.
            use_cache: If True, returns a cached result if available.
            strict: If True, exceptions during the loading process will be
                raised. If False, errors are logged and the method may return
                None or partial results.

        Returns:
            A dictionary containing the universe data, including DataFrames for
            'assets', 'classifications', and 'returns', and a Series for
            'metadata'. Returns None if the universe cannot be loaded and
            `strict` is False.

        Raises:
            UniverseLoadError: If any stage of the loading process fails and
                `strict` is True.
            InsufficientDataError: If no assets are selected or remain after
                filtering and `strict` is True.
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
