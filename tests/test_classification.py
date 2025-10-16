# ruff: noqa
"""Tests for the asset classification module."""

from pathlib import Path

import pytest

from src.portfolio_management.classification import (
    AssetClass,
    AssetClassification,
    AssetClassifier,
    ClassificationOverrides,
    Geography,
    SubClass,
)
from src.portfolio_management.selection import SelectedAsset


@pytest.fixture
def classifier() -> AssetClassifier:
    """Returns an instance of the AssetClassifier."""
    return AssetClassifier()


@pytest.fixture
def sample_asset() -> SelectedAsset:
    """Returns a sample SelectedAsset for testing."""
    return SelectedAsset(
        symbol="TEST.US",
        isin="US0000000000",
        name="Test Equity Fund",
        market="US",
        region="North America",
        currency="USD",
        category="etf",
        price_start="2020-01-01",
        price_end="2023-01-01",
        price_rows=756,
        data_status="ok",
        data_flags="",
        stooq_path="path/test.us.txt",
        resolved_currency="USD",
        currency_status="matched",
    )


class TestAssetClassifier:
    """Tests for the AssetClassifier class."""

    def test_classify_by_name(
        self, classifier: AssetClassifier, sample_asset: SelectedAsset
    ) -> None:
        """Test classification by name."""
        assert classifier._classify_by_name(sample_asset) == AssetClass.EQUITY

        sample_asset.name = "Test Government Bond"
        assert classifier._classify_by_name(sample_asset) == AssetClass.FIXED_INCOME

        sample_asset.name = "Test Gold Commodity"
        assert classifier._classify_by_name(sample_asset) == AssetClass.COMMODITY

        sample_asset.name = "Test Real Estate REIT"
        assert classifier._classify_by_name(sample_asset) == AssetClass.REAL_ESTATE

        sample_asset.name = "An Unknown Asset"
        assert classifier._classify_by_name(sample_asset) == AssetClass.UNKNOWN

    def test_classify_by_category(
        self, classifier: AssetClassifier, sample_asset: SelectedAsset
    ) -> None:
        """Test classification by category."""
        sample_asset.category = "lse stocks"
        assert classifier._classify_by_category(sample_asset) == AssetClass.EQUITY

        sample_asset.category = "etf"
        assert classifier._classify_by_category(sample_asset) == AssetClass.EQUITY

        sample_asset.category = "bonds"
        assert classifier._classify_by_category(sample_asset) == AssetClass.FIXED_INCOME

        sample_asset.category = "other"
        assert classifier._classify_by_category(sample_asset) == AssetClass.UNKNOWN

    def test_classify_geography(self, classifier: AssetClassifier) -> None:
        """Test geography classification."""
        asset1 = SelectedAsset(
            symbol="T1",
            isin="I1",
            name="N",
            market="US",
            region="North America",
            currency="USD",
            category="C",
            price_start="2022-01-01",
            price_end="2023-01-01",
            price_rows=252,
            data_status="ok",
            data_flags="",
            stooq_path="",
            resolved_currency="USD",
            currency_status="matched",
        )
        assert classifier._classify_geography(asset1) == Geography.NORTH_AMERICA

        asset2 = SelectedAsset(
            symbol="T2",
            isin="I2",
            name="N",
            market="LSE",
            region="UK",
            currency="GBP",
            category="C",
            price_start="2022-01-01",
            price_end="2023-01-01",
            price_rows=252,
            data_status="ok",
            data_flags="",
            stooq_path="",
            resolved_currency="GBP",
            currency_status="matched",
        )
        assert classifier._classify_geography(asset2) == Geography.UNITED_KINGDOM

        asset3 = SelectedAsset(
            symbol="T3",
            isin="I3",
            name="N",
            market="XETRA",
            region="Europe",
            currency="EUR",
            category="C",
            price_start="2022-01-01",
            price_end="2023-01-01",
            price_rows=252,
            data_status="ok",
            data_flags="",
            stooq_path="",
            resolved_currency="EUR",
            currency_status="matched",
        )
        assert classifier._classify_geography(asset3) == Geography.EUROPE

        asset4 = SelectedAsset(
            symbol="T4",
            isin="I4",
            name="Asian Dragon Fund",
            market="TSE",
            region="Asia",
            currency="JPY",
            category="C",
            price_start="2022-01-01",
            price_end="2023-01-01",
            price_rows=252,
            data_status="ok",
            data_flags="",
            stooq_path="",
            resolved_currency="JPY",
            currency_status="matched",
        )
        assert classifier._classify_geography(asset4) == Geography.ASIA_PACIFIC

    def test_classify_sub_class(
        self, classifier: AssetClassifier, sample_asset: SelectedAsset
    ) -> None:
        """Test sub-class classification."""
        sample_asset.name = "Large Cap Growth Fund"
        assert (
            classifier._classify_sub_class(sample_asset, AssetClass.EQUITY)
            == SubClass.LARGE_CAP
        )

        sample_asset.name = "Small Cap Value Stock"
        assert (
            classifier._classify_sub_class(sample_asset, AssetClass.EQUITY)
            == SubClass.SMALL_CAP
        )

        sample_asset.name = "Corporate Bond"
        assert (
            classifier._classify_sub_class(sample_asset, AssetClass.FIXED_INCOME)
            == SubClass.CORPORATE
        )

    def test_full_classification(
        self, classifier: AssetClassifier, sample_asset: SelectedAsset
    ) -> None:
        """Test the full classification pipeline."""
        classification = classifier.classify_asset(sample_asset)
        assert classification.asset_class == "equity"
        assert classification.geography == Geography.NORTH_AMERICA
        assert classification.confidence == 0.9  # From name and category

    def test_override(self, sample_asset: SelectedAsset) -> None:
        """Test that overrides take precedence."""
        overrides = ClassificationOverrides(
            overrides={
                "US0000000000": {
                    "asset_class": "fixed_income",
                    "sub_class": "government",
                    "geography": "global",
                    "sector": "government",
                },
            }
        )
        classifier = AssetClassifier(overrides=overrides)
        classification = classifier.classify_asset(sample_asset)

        assert classification.asset_class == "fixed_income"
        assert classification.sub_class == "government"
        assert classification.geography == Geography.GLOBAL
        assert classification.sector == "government"
        assert classification.confidence == 1.0

    def test_classify_universe(
        self, classifier: AssetClassifier, sample_asset: SelectedAsset
    ) -> None:
        """Test classifying a universe of assets."""
        assets = [sample_asset] * 5
        df = classifier.classify_universe(assets)
        assert len(df) == 5
        assert "asset_class" in df.columns
        assert df["asset_class"].iloc[0] == "equity"


class TestClassificationOverrides:
    """Tests for the ClassificationOverrides class."""

    def test_from_csv(self, tmp_path: Path) -> None:
        """Test loading overrides from a CSV file."""
        csv_content = (
            "isin,symbol,asset_class,sub_class,geography,sector\n"
            "US0000000000,TEST.US,fixed_income,corporate,global,industrials\n"
            "GB0000000001,TEST.UK,equity,large_cap,united_kingdom,technology\n"
        )
        csv_path = tmp_path / "overrides.csv"
        csv_path.write_text(csv_content)

        overrides = ClassificationOverrides.from_csv(csv_path)
        assert len(overrides.overrides) == 2
        assert overrides.overrides["US0000000000"]["asset_class"] == "fixed_income"

    def test_export_for_review(self, tmp_path: Path) -> None:
        """Test exporting classifications for review."""
        classifications = [
            AssetClassification(
                symbol="TEST.US",
                isin="US0000000000",
                name="Test Equity Fund",
                asset_class="equity",
                sub_class="large_cap",
                geography=Geography.NORTH_AMERICA,
                confidence=0.9,
            ),
        ]
        export_path = tmp_path / "review.csv"
        AssetClassifier.export_for_review(classifications, export_path)

        assert export_path.exists()
        content = export_path.read_text()
        assert "TEST.US" in content
        assert "large_cap" in content
