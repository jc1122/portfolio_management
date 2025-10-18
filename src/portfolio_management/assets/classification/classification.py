"""Asset classification for portfolio construction.

This module provides a taxonomy and data models for classifying assets into
different categories, such as asset class, geography, and sector. This
classification is a key input for portfolio construction and analysis.

Key components:
- AssetClass, Geography, SubClass: Enums for the classification taxonomy.
- AssetClassification: Dataclass to hold the classification result for an asset.
- ClassificationOverrides: A class to manage manual classification overrides from a CSV file.
- AssetClassifier: The main class that performs rule-based classification.

Usage Example:
    from pathlib import Path
    import pandas as pd
    from portfolio_management.assets.selection import SelectedAsset
    from portfolio_management.assets.classification import (
        AssetClassifier,
        ClassificationOverrides
    )

    # 1. Load selected assets
    selected_assets = [
        SelectedAsset(
            symbol="TEST.US", isin="US0000000000", name="Test Equity Fund", market="US",
            region="North America", currency="USD", category="etf", price_start="2020-01-01",
            price_end="2023-01-01", price_rows=756, data_status="ok", data_flags="",
            stooq_path="path/test.us.txt", resolved_currency="USD", currency_status="matched"
        )
    ]

    # 2. Load overrides (optional)
    overrides = ClassificationOverrides.from_csv(Path("path/to/overrides.csv"))

    # 3. Classify assets
    classifier = AssetClassifier(overrides=overrides)
    classified_df = classifier.classify_universe(selected_assets)

    # 4. Review results
    print(classified_df.head())

Limitations and Recommendations:
    The current rule-based classifier is simple and relies on keywords in the asset's
    name and category. This can be effective for many assets, but it has limitations:
    - It may misclassify assets with ambiguous names.
    - It does not handle complex financial instruments well.
    - The sub-class and sector classifications are very basic.

    For improved accuracy, consider the following:
    - Expanding the keyword lists.
    - Using more sophisticated NLP techniques for name analysis.
    - Integrating with external data sources for more detailed asset information.
    - Utilizing the manual override system for known exceptions.
"""

from __future__ import annotations

import logging
import pathlib
from dataclasses import dataclass, field
from enum import Enum
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
    """Represents the classification of a single asset."""

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
    """Holds manual classification overrides, loaded from a CSV file."""

    overrides: dict[str, dict[str, str]] = field(default_factory=dict)

    @classmethod
    def from_csv(cls, path: pathlib.Path | str) -> ClassificationOverrides:
        """Load overrides from a CSV file."""
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
    """Rule-based classifier for assets.

    This classifier uses a series of rules to determine the asset class, geography,
    and sub-class of an asset. It also supports manual overrides for specific assets.
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
        """Classify a single asset using keyword rules and manual overrides."""
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
        """Classify an iterable of assets and return a DataFrame of results."""
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

        classifications: list[AssetClassification] = []
        for asset in assets:
            try:
                classifications.append(self.classify_asset(asset))
            except Exception as exc:  # pragma: no cover - defensive
                raise ClassificationError(
                    f"Failed to classify asset '{getattr(asset, 'symbol', repr(asset))}': {exc}",
                ) from exc

        df = pd.DataFrame([c.__dict__ for c in classifications])

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
        df = pd.DataFrame([c.__dict__ for c in classifications])
        df.to_csv(path, index=False)
