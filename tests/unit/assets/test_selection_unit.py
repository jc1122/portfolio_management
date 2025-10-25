"""Focused unit tests for asset selection helpers."""

from __future__ import annotations

import pandas as pd
import pytest

from portfolio_management.assets.selection.selection import AssetSelector, FilterCriteria
from portfolio_management.core.exceptions import DataValidationError


@pytest.mark.unit
def test_parse_severity_handles_various_inputs() -> None:
    """Severity parsing handles populated, empty, and missing values."""

    selector = AssetSelector()
    assert selector._parse_severity("zero_volume_severity=high;foo=bar") == "high"
    assert selector._parse_severity("other_flag=value") is None
    assert selector._parse_severity("") is None
    assert selector._parse_severity(None) is None


@pytest.mark.unit
def test_filter_by_data_quality_applies_status_and_severity() -> None:
    """Data quality filter respects both status and severity criteria."""

    selector = AssetSelector()
    criteria = FilterCriteria(data_status=["ok"], zero_volume_severity=["low"])

    df = pd.DataFrame(
        {
            "data_status": ["ok", "ok", "error"],
            "data_flags": [
                "zero_volume_severity=low",
                "zero_volume_severity=high",
                "zero_volume_severity=low",
            ],
        }
    )

    filtered = selector._filter_by_data_quality(df, criteria)

    assert len(filtered) == 1
    assert filtered["data_flags"].iloc[0] == "zero_volume_severity=low"


@pytest.mark.unit
def test_filter_by_history_requires_minimum_days(mock_price_data: pd.DataFrame) -> None:
    """History filter removes assets without sufficient coverage."""

    selector = AssetSelector()
    criteria = FilterCriteria(min_history_days=5, min_price_rows=5)

    counts = mock_price_data.groupby("symbol").size()
    df = pd.DataFrame(
        {
            "symbol": ["AAPL", "MSFT"],
            "price_start": ["2020-01-01", "2020-01-01"],
            "price_end": ["2020-01-10", "2020-01-03"],
            "price_rows": [int(counts["AAPL"]), 3],
        }
    )

    filtered = selector._filter_by_history(df, criteria)
    assert filtered.shape[0] == 1
    assert filtered["symbol"].iloc[0] == "AAPL"


@pytest.mark.unit
def test_filter_by_characteristics_limits_markets() -> None:
    """Characteristic filter respects configured market list."""

    selector = AssetSelector()
    criteria = FilterCriteria(markets=["US"])

    df = pd.DataFrame(
        {
            "symbol": ["AAPL.US", "VOD.UK"],
            "market": ["US", "UK"],
            "region": ["North America", "Europe"],
            "resolved_currency": ["USD", "GBP"],
            "category": ["Stock", "Stock"],
        }
    )

    filtered = selector._filter_by_characteristics(df, criteria)
    assert filtered.shape[0] == 1
    assert filtered["symbol"].iloc[0] == "AAPL.US"


@pytest.mark.unit
def test_apply_lists_validates_required_columns() -> None:
    """Allow/block list application validates input schema."""

    selector = AssetSelector()
    criteria = FilterCriteria(allowlist={"AAPL.US"})

    with pytest.raises(DataValidationError):
        selector._apply_lists(pd.DataFrame({"symbol": ["AAPL.US"]}), criteria)


@pytest.mark.unit
def test_apply_lists_filters_using_allow_and_block_lists() -> None:
    """Allow and block lists combine to select the correct assets."""

    selector = AssetSelector()
    criteria = FilterCriteria(allowlist={"AAPL.US", "MSFT.US"}, blocklist={"MSFT.US"})

    df = pd.DataFrame(
        {
            "symbol": ["AAPL.US", "MSFT.US", "GOOG.US"],
            "isin": ["US0378331005", "US5949181045", "US02079K3059"],
        }
    )

    filtered = selector._apply_lists(df, criteria)

    assert filtered.shape[0] == 1
    assert filtered["symbol"].iloc[0] == "AAPL.US"
