"""Handles the definition, selection, and classification of financial assets.

This package forms the core of the asset management layer, responsible for
transforming raw instrument data into well-defined, filtered, and classified
investment universes. It acts as the bridge between raw data sources and the
portfolio construction engine.

Pipeline Position:
    Data Layer -> **Assets Layer** -> Portfolio Layer

    1.  **Input**: Raw asset metadata (e.g., from `tradeable_matches.csv`).
    2.  **Process**:
        - `selection`: Filters assets based on data quality, history, and market criteria.
        - `classification`: Assigns assets to categories like asset class, geography, and sub-class.
        - `universes`: Combines selection and classification rules defined in YAML
          to build complete, investable universes.
    3.  **Output**: A structured collection of assets, their classifications, and
       associated returns, ready for analysis and optimization.

Key Classes:
    - `AssetSelector`: Filters assets using a multi-stage pipeline.
    - `AssetClassifier`: Classifies assets using a rule-based engine.
    - `UniverseManager`: The main entry point for loading and managing universes
      defined in a configuration file.
    - `FilterCriteria`: Defines the rules for asset selection.
    - `UniverseDefinition`: Defines the complete configuration for a universe.

Usage Example:
    # This example demonstrates the end-to-end workflow of loading a universe.
    # In a real application, the config file and data would already exist.

    from pathlib import Path
    import pandas as pd
    from portfolio_management.assets import UniverseManager

    # Assume the following setup:
    # 1. A universe configuration file 'config/universes.yaml' with a
    #    'global_equity' universe defined.
    # 2. A DataFrame 'matches_df' containing metadata for all tradeable assets.
    # 3. A directory 'prices/' containing historical price data for the assets.

    # Conceptual initialization (replace with actual paths and data):
    # >>> manager = UniverseManager(
    # ...     config_path=Path("config/universes.yaml"),
    # ...     matches_df=matches_df,
    # ...     prices_dir=Path("prices/")
    # ... )

    # Load the 'global_equity' universe:
    # >>> universe_data = manager.load_universe("global_equity")

    # The resulting 'universe_data' is a dictionary containing:
    # - universe_data['assets']: DataFrame of selected asset metadata.
    # - universe_data['classifications']: DataFrame of asset classifications.
    # - universe_data['returns']: DataFrame of historical asset returns.
    # - universe_data['metadata']: Series containing universe definition.

    # >>> if universe_data:
    # ...     print(f"Loaded {len(universe_data['assets'])} assets for 'global_equity'.")
    # ...     print("Asset Classifications:")
    # ...     print(universe_data['classifications'][['symbol', 'asset_class']].head())
"""

# Classification
from .classification import (
    AssetClass,
    AssetClassification,
    AssetClassifier,
    ClassificationOverrides,
    Geography,
    SubClass,
)

# Selection
from .selection import AssetSelector, FilterCriteria, SelectedAsset

# Universes
from .universes import UniverseConfigLoader, UniverseDefinition, UniverseManager

__all__ = [
    # Selection
    "FilterCriteria",
    "SelectedAsset",
    "AssetSelector",
    # Classification
    "AssetClass",
    "Geography",
    "SubClass",
    "AssetClassification",
    "AssetClassifier",
    "ClassificationOverrides",
    # Universes
    "UniverseDefinition",
    "UniverseConfigLoader",
    "UniverseManager",
]
