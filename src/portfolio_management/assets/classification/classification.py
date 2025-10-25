"""Provides a rule-based engine for asset classification.

This module defines the taxonomy (enums), data structures, and logic required
to classify assets into categories such as asset class, geography, and sub-class.
The classification process is a crucial step in preparing a filtered asset
universe for portfolio construction and analysis.

Pipeline Position:
    Asset Selection -> **Asset Classification** -> Universe Loading

    1.  **Input**: A list of `SelectedAsset` objects that have passed initial
       filtering.
    2.  **Process**: The `AssetClassifier` applies a set of rules based on asset
       metadata (e.g., name, category, currency) to assign a classification.
       Manual overrides can be provided to handle exceptions.
    3.  **Output**: A pandas DataFrame containing the original asset identifiers
       along with their assigned classifications and a confidence score.

Key Components:
    - `AssetClass`, `Geography`, `SubClass`: Enums for the classification taxonomy.
    - `AssetClassification`: Dataclass holding the classification result for an asset.
    - `ClassificationOverrides`: Manages manual classification overrides from a CSV file.
    - `AssetClassifier`: The main engine that performs the rule-based classification.

Usage Example:
    from pathlib import Path
    import pandas as pd
    from portfolio_management.assets.selection import SelectedAsset
    from portfolio_management.assets.classification import (
        AssetClassifier,
        ClassificationOverrides
    )

    # 1. Define selected assets (output from the selection stage)
    selected_assets = [
        SelectedAsset(
            symbol="FUND.US", isin="US0123456789", name="Global Equity Fund",
            market="US", region="North America", currency="USD", category="etf",
            price_start="2020-01-01", price_end="2023-01-01", price_rows=756,
            data_status="ok", data_flags="", stooq_path="path/fund.us.txt",
            resolved_currency="USD", currency_status="matched"
        ),
        SelectedAsset(
            symbol="BOND.UK", isin="GB0009876543", name="UK Government Gilt",
            market="UK", region="Europe", currency="GBP", category="bond",
            price_start="2018-01-01", price_end="2023-01-01", price_rows=1260,
            data_status="ok", data_flags="", stooq_path="path/bond.uk.txt",
            resolved_currency="GBP", currency_status="matched"
        )
    ]

    # 2. Load manual overrides from a CSV file (optional)
    # Assume 'overrides.csv' contains a row to re-classify FUND.US
    # overrides = ClassificationOverrides.from_csv(Path("path/to/overrides.csv"))

    # 3. Initialize and run the classifier
    classifier = AssetClassifier() # or AssetClassifier(overrides=overrides)
    classified_df = classifier.classify_universe(selected_assets)

    # 4. Review results
    print(classified_df[['symbol', 'asset_class', 'geography', 'confidence']].head())
    # Expected output might look like:
    #     symbol   asset_class        geography  confidence
    # 0  FUND.US        equity    north_america         0.9
    # 1  BOND.UK  fixed_income   united_kingdom         0.7
"""

from __future__ import annotations

import logging
import pathlib
import re
from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

import pandas as pd

from ...core.exceptions import ClassificationError, DataValidationError

if TYPE_CHECKING:
    from ..selection.selection import SelectedAsset


class AssetClass(str, Enum):
    """Broad asset classes."""

    EQUITY = "equity"
    FIXED_INCOME = "fixed_income"
    ALTERNATIVE = "alternative"
    CASH = "cash"
    COMMODITY = "commodity"
    REAL_ESTATE = "real_estate"
    UNKNOWN = "unknown"


class Geography(str, Enum):
    """Geographical classifications for assets."""

    DEVELOPED_MARKETS = "developed_markets"
    EMERGING_MARKETS = "emerging_markets"
    GLOBAL = "global"
    NORTH_AMERICA = "north_america"
    EUROPE = "europe"
    ASIA_PACIFIC = "asia_pacific"
    UNITED_KINGDOM = "united_kingdom"
    UNKNOWN = "unknown"


class SubClass(str, Enum):
    """Granular asset sub-classes."""

    LARGE_CAP = "large_cap"
    SMALL_CAP = "small_cap"
    VALUE = "value"
    GROWTH = "growth"
    DIVIDEND = "dividend"
    GOVERNMENT = "government"
    CORPORATE = "corporate"
    HIGH_YIELD = "high_yield"
    INFLATION_LINKED = "inflation_linked"
    GOLD = "gold"
    COMMODITIES = "commodities"
    REIT = "reit"
    HEDGE_FUND = "hedge_fund"
    UNKNOWN = "unknown"


@dataclass
class AssetClassification:
    """Represents the classification of a single asset.

    This data structure holds the complete classification profile for an asset
    after it has been processed by the `AssetClassifier`.

    Attributes:
        symbol: The unique ticker symbol for the asset.
        isin: The International Securities Identification Number.
        name: The human-readable name of the asset.
        asset_class: The broad asset class (e.g., 'equity', 'fixed_income').
        sub_class: The more granular sub-class (e.g., 'large_cap', 'government').
        geography: The geographical region of the asset.
        sector: The industry sector (optional, often populated by external data).
        confidence: A score from 0.0 to 1.0 indicating the classifier's
            confidence in the result. 1.0 indicates a manual override.
    """

    symbol: str
    isin: str
    name: str
    asset_class: str
    sub_class: str
    geography: Geography
    sector: str | None = None
    confidence: float = 1.0


@dataclass
class ClassificationOverrides:
    """Manages manual classification overrides loaded from a CSV file.

    This class provides a mechanism to manually set the classification for
    specific assets, bypassing the rule-based engine. Overrides are indexed by
    ISIN or symbol, with ISIN taking precedence.

    Attributes:
        overrides: A dictionary where keys are asset identifiers (ISIN or symbol)
            and values are dictionaries of classification fields to override.

    Configuration (CSV Format):
        The CSV file should contain columns that match the `AssetClassification`
        attributes. The 'symbol' or 'isin' column is required for matching.

        Example `overrides.csv`:
        ```csv
        symbol,isin,asset_class,sub_class,geography
        AMZN.US,US0231351067,equity,large_cap,north_america
        BRK.A,US0846701086,equity,value,north_america
        ```

    Example:
        >>> from pathlib import Path
        >>> import io
        >>>
        >>> csv_lines = [
        ...     "symbol,isin,asset_class,sub_class,geography",
        ...     "AMZN.US,US0231351067,equity,large_cap,north_america",
        ...     "BRK.A,US0846701086,equity,value,north_america"
        ... ]
        >>> csv_content = "\\n".join(csv_lines)
        >>>
        >>> # In a real scenario, you would provide a file path.
        >>> # For this example, we simulate the file with an in-memory buffer.
        >>> with open("overrides.csv", "w") as f:
        ...     _ = f.write(csv_content)
        >>>
        >>> overrides = ClassificationOverrides.from_csv("overrides.csv")
        >>> amzn_override = overrides.overrides.get("US0231351067")
        >>> print(amzn_override['asset_class'])
        equity
        >>> import os
        >>> os.remove("overrides.csv")
    """

    overrides: dict[str, dict[str, str]] = field(default_factory=dict)

    @classmethod
    def from_csv(cls, path: pathlib.Path | str) -> ClassificationOverrides:
        """Load classification overrides from a CSV file.

        The CSV file must contain a 'symbol' or 'isin' column to identify the
        asset. Other columns should correspond to `AssetClassification` fields
        (e.g., 'asset_class', 'sub_class', 'geography').

        Args:
            path: The file path to the CSV containing the overrides.

        Returns:
            A `ClassificationOverrides` instance populated with the data from
            the CSV file. Returns an empty instance if the path does not exist.
        """
        csv_path = pathlib.Path(path)
        if not csv_path.exists():
            return cls()
        overrides_df = pd.read_csv(csv_path)
        overrides: dict[str, dict[str, object]] = {}
        for _, row in overrides_df.iterrows():
            key = row["isin"] if pd.notna(row["isin"]) else row["symbol"]
            overrides[key] = row.to_dict()
        return cls(overrides=overrides)


class AssetClassifier:
    """Applies a rule-based engine to classify assets.

    This classifier determines an asset's class, sub-class, and geography by
    applying a series of rules based on keywords found in the asset's metadata
    (e.g., name, category). It is designed to provide a baseline classification
    that can be augmented with manual overrides for improved accuracy.

    The classification logic is primarily handled by the `_classify_dataframe`
    method, which uses vectorized pandas operations for efficiency.

    Attributes:
        overrides (ClassificationOverrides): A collection of manual overrides
            that will take precedence over the rule-based engine.

    Methods:
        - `classify_universe`: Classifies a list of assets and returns a DataFrame.
        - `classify_asset`: Classifies a single asset.

    Example:
        >>> from portfolio_management.assets.selection import SelectedAsset
        >>>
        >>> assets = [
        ...     SelectedAsset(
        ...         symbol="AAPL.US", isin="US0378331005", name="Apple Inc. Equity",
        ...         market="US", region="North America", currency="USD", category="stock",
        ...         price_start="2010-01-01", price_end="2023-01-01", price_rows=3276,
        ...         data_status="ok", data_flags="", stooq_path="", resolved_currency="USD",
        ...         currency_status="matched"
        ...     )
        ... ]
        >>> classifier = AssetClassifier()
        >>> results = classifier.classify_universe(assets)
        >>> result_series = results.iloc[0]
        >>> result_series['symbol']
        'AAPL.US'
        >>> result_series['asset_class']
        'equity'
        >>> result_series['geography']
        'north_america'
    """

    EQUITY_KEYWORDS: ClassVar[set[str]] = {"stock", "equity", "shares", "fund", "etf"}
    BOND_KEYWORDS: ClassVar[set[str]] = {"bond", "gilt", "treasury", "credit"}
    COMMODITY_KEYWORDS: ClassVar[set[str]] = {"gold", "silver", "oil", "commodity"}
    REAL_ESTATE_KEYWORDS: ClassVar[set[str]] = {"reit", "real estate"}
    LOW_CONFIDENCE_THRESHOLD: ClassVar[float] = 0.6

    GEOGRAPHY_PATTERNS: ClassVar[dict[Geography, list[str]]] = {
        Geography.NORTH_AMERICA: ["us", "usa", "america", "usd", "north america"],
        Geography.UNITED_KINGDOM: ["uk", "gbr", "gbp", "british", "united kingdom"],
        Geography.EUROPE: ["de", "fr", "eur", "europe"],
        Geography.ASIA_PACIFIC: ["jp", "jpy", "asia"],
    }

    def __init__(self, overrides: ClassificationOverrides | None = None):
        """Initialise the classifier with optional manual overrides."""
        self.overrides = overrides or ClassificationOverrides()

    def classify_asset(self, asset: SelectedAsset) -> AssetClassification:
        """Classifies a single asset using keyword-based rules.

        This method first checks for a manual override for the asset. If none
        is found, it applies rules based on the asset's name and category to
        determine its classification. This method is suitable for classifying
        individual assets but is less efficient than `classify_universe` for
        large batches.

        Args:
            asset: The `SelectedAsset` instance to classify.

        Returns:
            An `AssetClassification` instance containing the classification results.
        """
        override = self.overrides.overrides.get(
            asset.isin,
        ) or self.overrides.overrides.get(asset.symbol)
        if override:
            return AssetClassification(
                symbol=asset.symbol,
                isin=asset.isin,
                name=asset.name,
                asset_class=str(override.get("asset_class", AssetClass.UNKNOWN.value)),
                sub_class=str(override.get("sub_class", SubClass.UNKNOWN.value)),
                geography=Geography(override.get("geography", Geography.UNKNOWN)),
                sector=override.get("sector"),
                confidence=1.0,
            )

        asset_class_from_name = self._classify_by_name(asset)
        asset_class_from_cat = self._classify_by_category(asset)

        if {
            asset_class_from_name,
            asset_class_from_cat,
        } == {AssetClass.UNKNOWN}:
            asset_class = AssetClass.UNKNOWN
            confidence = 0.5
        elif AssetClass.UNKNOWN not in {
            asset_class_from_name,
            asset_class_from_cat,
        }:
            asset_class = asset_class_from_name
            confidence = 0.9
        elif asset_class_from_name != AssetClass.UNKNOWN:
            asset_class = asset_class_from_name
            confidence = 0.7
        else:
            asset_class = asset_class_from_cat
            confidence = 0.7

        geography = self._classify_geography(asset)
        sub_class = self._classify_sub_class(asset, asset_class)

        return AssetClassification(
            symbol=asset.symbol,
            isin=asset.isin,
            name=asset.name,
            asset_class=(
                asset_class.value
                if isinstance(asset_class, AssetClass)
                else str(asset_class)
            ),
            sub_class=(
                sub_class.value if isinstance(sub_class, SubClass) else str(sub_class)
            ),
            geography=geography,
            confidence=confidence,
        )

    def classify_universe(self, assets: list[SelectedAsset]) -> pd.DataFrame:
        """Classifies a list of assets and returns a DataFrame of results.

        This is the primary method for bulk classification. It converts the list
        of assets into a pandas DataFrame and uses efficient, vectorized
        operations to apply the classification rules.

        Args:
            assets: A list of `SelectedAsset` objects to be classified.

        Returns:
            A pandas DataFrame where each row represents an asset and columns
            contain the classification results (e.g., 'asset_class', 'geography').

        Raises:
            DataValidationError: If the input is None or not a list.
            ClassificationError: If assets cannot be serialized for processing.
        """
        if assets is None:
            raise DataValidationError(
                "Assets to classify cannot be None.",
            )
        if not isinstance(assets, list):
            raise DataValidationError(
                "Assets must be provided as a list.",
            )
        if not assets:
            logging.getLogger(__name__).info("No assets supplied for classification.")
            return pd.DataFrame(
                columns=[
                    "symbol",
                    "isin",
                    "name",
                    "asset_class",
                    "sub_class",
                    "geography",
                    "sector",
                    "confidence",
                ],
            )

        try:
            asset_dicts = [asdict(asset) for asset in assets]
        except TypeError as exc:  # pragma: no cover - defensive
            raise ClassificationError(
                "Failed to serialise assets for classification."
            ) from exc

        assets_df = pd.DataFrame(asset_dicts)
        df = self._classify_dataframe(assets_df)

        logger = logging.getLogger(__name__)
        logger.info("Classified %d assets.", len(df))
        logger.info("Asset class breakdown:\n%s", df["asset_class"].value_counts())
        logger.info("Geography breakdown:\n%s", df["geography"].value_counts())
        low_confidence = df[df["confidence"] < self.LOW_CONFIDENCE_THRESHOLD]
        if not low_confidence.empty:
            logger.warning(
                "%d assets with low classification confidence.",
                len(low_confidence),
            )
            logger.warning(
                "\n%s",
                low_confidence[["symbol", "name", "asset_class", "confidence"]],
            )

        return df

    def _contains_keywords(self, series: pd.Series, keywords: set[str]) -> pd.Series:
        if series.empty or not keywords:
            return pd.Series(False, index=series.index)
        pattern = "|".join(re.escape(keyword) for keyword in keywords if keyword)
        if not pattern:
            return pd.Series(False, index=series.index)
        return series.str.contains(pattern, na=False)

    def _classify_dataframe(self, assets_df: pd.DataFrame) -> pd.DataFrame:
        def column_or_empty(column: str) -> pd.Series:
            if column in assets_df:
                return assets_df[column]
            return pd.Series([""] * len(assets_df), index=assets_df.index, dtype=object)

        name_lower = column_or_empty("name").fillna("").astype(str).str.lower()
        category_lower = column_or_empty("category").fillna("").astype(str).str.lower()
        region_lower = column_or_empty("region").fillna("").astype(str).str.lower()
        currency_lower = column_or_empty("currency").fillna("").astype(str).str.lower()

        result_df = pd.DataFrame(
            {
                "symbol": column_or_empty("symbol"),
                "isin": column_or_empty("isin"),
                "name": column_or_empty("name"),
            },
            index=assets_df.index,
        )

        unknown_class = AssetClass.UNKNOWN.value
        asset_class_name = pd.Series(unknown_class, index=result_df.index, dtype=object)

        equity_mask = self._contains_keywords(name_lower, self.EQUITY_KEYWORDS)
        asset_class_name[equity_mask] = AssetClass.EQUITY.value

        remaining = asset_class_name == unknown_class
        bond_mask = remaining & self._contains_keywords(name_lower, self.BOND_KEYWORDS)
        asset_class_name[bond_mask] = AssetClass.FIXED_INCOME.value

        remaining = asset_class_name == unknown_class
        commodity_mask = remaining & self._contains_keywords(
            name_lower, self.COMMODITY_KEYWORDS
        )
        asset_class_name[commodity_mask] = AssetClass.COMMODITY.value

        remaining = asset_class_name == unknown_class
        real_estate_mask = remaining & self._contains_keywords(
            name_lower, self.REAL_ESTATE_KEYWORDS
        )
        asset_class_name[real_estate_mask] = AssetClass.REAL_ESTATE.value

        class_from_category = pd.Series(
            unknown_class, index=result_df.index, dtype=object
        )
        stock_mask = category_lower.str.contains("stock", na=False)
        class_from_category[stock_mask] = AssetClass.EQUITY.value

        remaining_cat = class_from_category == unknown_class
        etf_mask = remaining_cat & category_lower.str.contains("etf", na=False)
        class_from_category[etf_mask] = AssetClass.EQUITY.value

        remaining_cat = class_from_category == unknown_class
        bond_cat_mask = remaining_cat & category_lower.str.contains("bond", na=False)
        class_from_category[bond_cat_mask] = AssetClass.FIXED_INCOME.value

        unknown_name_mask = asset_class_name == unknown_class
        unknown_cat_mask = class_from_category == unknown_class

        asset_class = asset_class_name.copy()
        confidence = pd.Series(0.7, index=result_df.index, dtype=float)

        both_unknown = unknown_name_mask & unknown_cat_mask
        asset_class[both_unknown] = unknown_class
        confidence[both_unknown] = 0.5

        both_known = (~unknown_name_mask) & (~unknown_cat_mask)
        confidence[both_known] = 0.9

        name_only_known = (~unknown_name_mask) & unknown_cat_mask
        asset_class[name_only_known] = asset_class_name[name_only_known]
        confidence[name_only_known] = 0.7

        cat_only_known = unknown_name_mask & (~unknown_cat_mask)
        asset_class[cat_only_known] = class_from_category[cat_only_known]
        confidence[cat_only_known] = 0.7

        geography = pd.Series(Geography.UNKNOWN, index=result_df.index, dtype=object)
        assigned_geo = geography != Geography.UNKNOWN

        for geo_enum, patterns in self.GEOGRAPHY_PATTERNS.items():
            patterns_lower = [pattern.lower() for pattern in patterns]
            mask_region = region_lower.isin(patterns_lower)
            mask_currency = currency_lower.isin(patterns_lower)
            pattern_regex = "|".join(
                re.escape(pattern) for pattern in patterns_lower if pattern
            )
            mask_name = (
                name_lower.str.contains(pattern_regex, na=False)
                if pattern_regex
                else pd.Series(False, index=result_df.index)
            )
            combined = (~assigned_geo) & (mask_region | mask_currency | mask_name)
            geography[combined] = geo_enum
            assigned_geo = geography != Geography.UNKNOWN

        sub_class = pd.Series(
            SubClass.UNKNOWN.value, index=result_df.index, dtype=object
        )
        equity_asset_mask = asset_class == AssetClass.EQUITY.value
        sub_class[
            equity_asset_mask & name_lower.str.contains("large cap", na=False)
        ] = SubClass.LARGE_CAP.value
        sub_class[
            equity_asset_mask & name_lower.str.contains("small cap", na=False)
        ] = SubClass.SMALL_CAP.value
        sub_class[equity_asset_mask & name_lower.str.contains("value", na=False)] = (
            SubClass.VALUE.value
        )
        sub_class[equity_asset_mask & name_lower.str.contains("growth", na=False)] = (
            SubClass.GROWTH.value
        )
        sub_class[equity_asset_mask & name_lower.str.contains("dividend", na=False)] = (
            SubClass.DIVIDEND.value
        )

        fixed_income_mask = asset_class == AssetClass.FIXED_INCOME.value
        sub_class[
            fixed_income_mask
            & name_lower.str.contains("government|gilt|treasury", na=False)
        ] = SubClass.GOVERNMENT.value
        sub_class[
            fixed_income_mask & name_lower.str.contains("corporate", na=False)
        ] = SubClass.CORPORATE.value
        sub_class[
            fixed_income_mask & name_lower.str.contains("high yield", na=False)
        ] = SubClass.HIGH_YIELD.value

        commodity_asset_mask = asset_class == AssetClass.COMMODITY.value
        sub_class[commodity_asset_mask & name_lower.str.contains("gold", na=False)] = (
            SubClass.GOLD.value
        )

        real_estate_asset_mask = asset_class == AssetClass.REAL_ESTATE.value
        sub_class[
            real_estate_asset_mask & name_lower.str.contains("reit", na=False)
        ] = SubClass.REIT.value

        result_df["asset_class"] = asset_class.astype(str)
        result_df["sub_class"] = sub_class.astype(str)
        result_df["geography"] = geography.apply(lambda x: x.value)
        result_df["sector"] = None
        result_df["confidence"] = confidence

        if self.overrides.overrides:
            isin_series = assets_df.get("isin", pd.Series([], dtype=str)).fillna("")
            symbol_series = assets_df.get("symbol", pd.Series([], dtype=str)).fillna("")
            override_keys = isin_series.where(isin_series != "", symbol_series)
            for idx, key in enumerate(override_keys):
                override = self.overrides.overrides.get(key)
                if not override:
                    continue
                asset_class_override = override.get(
                    "asset_class", AssetClass.UNKNOWN.value
                )
                if isinstance(asset_class_override, AssetClass):
                    asset_class_override = asset_class_override.value
                result_df.at[idx, "asset_class"] = str(asset_class_override)

                sub_class_override = override.get("sub_class", SubClass.UNKNOWN.value)
                if isinstance(sub_class_override, SubClass):
                    sub_class_override = sub_class_override.value
                result_df.at[idx, "sub_class"] = str(sub_class_override)

                geography_override = override.get("geography", Geography.UNKNOWN)
                if not isinstance(geography_override, Geography):
                    try:
                        geography_override = Geography(geography_override)
                    except ValueError:
                        geography_override = Geography.UNKNOWN
                result_df.at[idx, "geography"] = geography_override

                result_df.at[idx, "sector"] = override.get("sector")
                confidence_override = override.get("confidence", 1.0)
                try:
                    result_df.at[idx, "confidence"] = float(confidence_override)
                except (TypeError, ValueError):
                    result_df.at[idx, "confidence"] = 1.0

        return result_df

    def _classify_by_name(self, asset: SelectedAsset) -> AssetClass:
        if pd.isna(asset.name):
            return AssetClass.UNKNOWN
        name = asset.name.lower()
        if any(keyword in name for keyword in self.EQUITY_KEYWORDS):
            return AssetClass.EQUITY
        if any(keyword in name for keyword in self.BOND_KEYWORDS):
            return AssetClass.FIXED_INCOME
        if any(keyword in name for keyword in self.COMMODITY_KEYWORDS):
            return AssetClass.COMMODITY
        if any(keyword in name for keyword in self.REAL_ESTATE_KEYWORDS):
            return AssetClass.REAL_ESTATE
        return AssetClass.UNKNOWN

    def _classify_by_category(self, asset: SelectedAsset) -> AssetClass:
        if pd.isna(asset.category):
            return AssetClass.UNKNOWN
        category = asset.category.lower()
        if "stock" in category:
            return AssetClass.EQUITY
        if "etf" in category:
            return AssetClass.EQUITY
        if "bond" in category:
            return AssetClass.FIXED_INCOME
        return AssetClass.UNKNOWN

    def _classify_geography(self, asset: SelectedAsset) -> Geography:
        for geo, patterns in self.GEOGRAPHY_PATTERNS.items():
            if not pd.isna(asset.region) and asset.region.lower() in patterns:
                return geo
            if not pd.isna(asset.currency) and asset.currency.lower() in patterns:
                return geo
            if not pd.isna(asset.name) and any(
                pattern.lower() in asset.name.lower() for pattern in patterns
            ):
                return geo
        return Geography.UNKNOWN

    def _classify_sub_class(  # noqa: C901, PLR0911, PLR0912
        self,
        asset: SelectedAsset,
        asset_class: AssetClass,
    ) -> str:
        if pd.isna(asset.name):
            return SubClass.UNKNOWN
        name = asset.name.lower()
        if asset_class == AssetClass.EQUITY:
            if "large cap" in name:
                return SubClass.LARGE_CAP
            if "small cap" in name:
                return SubClass.SMALL_CAP
            if "value" in name:
                return SubClass.VALUE
            if "growth" in name:
                return SubClass.GROWTH
            if "dividend" in name:
                return SubClass.DIVIDEND
        if asset_class == AssetClass.FIXED_INCOME:
            if "government" in name or "gilt" in name or "treasury" in name:
                return SubClass.GOVERNMENT
            if "corporate" in name:
                return SubClass.CORPORATE
            if "high yield" in name:
                return SubClass.HIGH_YIELD
        if asset_class == AssetClass.COMMODITY and "gold" in name:
            return SubClass.GOLD
        if asset_class == AssetClass.REAL_ESTATE:
            if "reit" in name:
                return SubClass.REIT
        return SubClass.UNKNOWN

    @staticmethod
    def export_for_review(
        classifications: list[AssetClassification],
        path: Path,
    ) -> None:
        records = []
        for classification in classifications:
            if is_dataclass(classification):
                records.append(asdict(classification))
            elif isinstance(classification, dict):
                records.append(classification)
            elif hasattr(classification, "__dict__"):
                records.append(vars(classification))
            else:
                raise ValueError("Unsupported classification record type for export.")

        df = pd.DataFrame(records)
        df.to_csv(path, index=False)
