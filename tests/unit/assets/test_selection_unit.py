"""Unit tests for the asset selection filters."""

from __future__ import annotations

import pandas as pd
import pytest

from portfolio_management.assets.selection.selection import AssetSelector, FilterCriteria
from portfolio_management.core.exceptions import AssetSelectionError, DataValidationError

pytestmark = pytest.mark.unit


@pytest.fixture
def sample_matches() -> pd.DataFrame:
    """Create a minimal matches DataFrame for testing."""

    return pd.DataFrame(
        {
            "symbol": ["AAA", "BBB", "CCC"],
            "isin": ["AAA111", "BBB222", "CCC333"],
            "name": ["Alpha", "Beta", "Gamma"],
            "market": ["US", "US", "DE"],
            "region": ["NA", "NA", "EU"],
            "currency": ["USD", "USD", "EUR"],
            "category": ["ETF", "ETF", "ETF"],
            "price_start": ["2010-01-01"] * 3,
            "price_end": ["2024-01-01"] * 3,
            "price_rows": [4000, 3000, 200],
            "data_status": ["ok", "ok", "ok"],
            "data_flags": [
                "zero_volume_severity=low",
                "zero_volume_severity=high",
                "zero_volume_severity=medium",
            ],
            "stooq_path": ["a.txt", "b.txt", "c.txt"],
            "resolved_currency": ["USD", "USD", "EUR"],
            "currency_status": ["matched", "matched", "matched"],
        }
    )


def test_filter_criteria_default_is_valid() -> None:
    """The default factory should produce valid criteria."""

    criteria = FilterCriteria.default()
    # Should not raise
    criteria.validate()


def test_filter_criteria_validate_rejects_negative_history() -> None:
    """Negative history requirements are invalid."""

    criteria = FilterCriteria(min_history_days=-10)
    with pytest.raises(ValueError):
        criteria.validate()


def test_asset_selector_filters_by_status(sample_matches: pd.DataFrame) -> None:
    """Only rows with acceptable data status should be kept."""

    matches = sample_matches.copy()
    matches.loc[1, "data_status"] = "warning"

    criteria = FilterCriteria(data_status=["ok"], min_price_rows=3500)
    selector = AssetSelector()

    selected = selector.select_assets(matches, criteria)

    assert [asset.symbol for asset in selected] == ["AAA"]


def test_asset_selector_respects_allowlist(sample_matches: pd.DataFrame) -> None:
    """Allowlisted symbols should be retained even if other filters remove them."""

    criteria = FilterCriteria(data_status=["ok"], allowlist={"BBB"})
    selector = AssetSelector()

    selected = selector.select_assets(sample_matches, criteria)

    assert [asset.symbol for asset in selected] == ["BBB"]


def test_asset_selector_blocklist_removes_assets(sample_matches: pd.DataFrame) -> None:
    """Blocklisted assets should be excluded from the output."""

    criteria = FilterCriteria(blocklist={"AAA"}, min_price_rows=1)
    selector = AssetSelector()

    selected = selector.select_assets(sample_matches, criteria)

    assert {asset.symbol for asset in selected} == {"BBB", "CCC"}


def test_asset_selector_allowlist_missing_raises(sample_matches: pd.DataFrame) -> None:
    """If allowlist is provided and nothing matches, raise an error."""

    criteria = FilterCriteria(allowlist={"ZZZ"})
    selector = AssetSelector()

    with pytest.raises(AssetSelectionError):
        selector.select_assets(sample_matches, criteria)


def test_asset_selector_missing_columns_raises(sample_matches: pd.DataFrame) -> None:
    """Missing required columns should result in DataValidationError."""

    selector = AssetSelector()
    criteria = FilterCriteria()

    with pytest.raises(DataValidationError):
        selector.select_assets(sample_matches[["symbol", "isin"]], criteria)
