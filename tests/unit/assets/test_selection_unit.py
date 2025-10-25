"""Unit tests for AssetSelector helpers without I/O."""

from __future__ import annotations

import pandas as pd
import pytest

from portfolio_management.assets.selection.selection import AssetSelector, FilterCriteria
from portfolio_management.core.exceptions import DataValidationError

pytestmark = pytest.mark.unit


@pytest.fixture
def selector() -> AssetSelector:
    """Return a selector instance for helper testing."""
    return AssetSelector()


@pytest.fixture
def sample_quality_df() -> pd.DataFrame:
    """Create an in-memory DataFrame for quality filtering tests."""
    return pd.DataFrame(
        {
            "symbol": ["AAA", "BBB", "CCC", "DDD"],
            "data_status": ["ok", "warning", "ok", "warning"],
            "data_flags": [
                "",
                "zero_volume_severity=low",
                "zero_volume_severity=high",
                "zero_volume_severity=moderate",
            ],
        }
    )


def test_parse_severity_extracts_value(selector: AssetSelector) -> None:
    """Severity parser should extract the value from flag strings."""
    assert selector._parse_severity("zero_volume_severity=high") == "high"
    assert selector._parse_severity("zero_volume=1;zero_volume_severity=low") == "low"


def test_parse_severity_handles_missing(selector: AssetSelector) -> None:
    """Parser should return ``None`` for missing values."""
    assert selector._parse_severity(None) is None
    assert selector._parse_severity("") is None


def test_filter_by_data_status(selector: AssetSelector, sample_quality_df: pd.DataFrame) -> None:
    """Filtering by status should return only the requested rows."""
    criteria = FilterCriteria(data_status=["ok"], zero_volume_severity=None)

    filtered = selector._filter_by_data_quality(sample_quality_df, criteria)

    assert set(filtered["symbol"]) == {"AAA", "CCC"}


def test_filter_by_severity(selector: AssetSelector, sample_quality_df: pd.DataFrame) -> None:
    """Filtering by severity should retain matching rows only."""
    criteria = FilterCriteria(data_status=["ok", "warning"], zero_volume_severity=["low"])

    filtered = selector._filter_by_data_quality(sample_quality_df, criteria)

    assert list(filtered["symbol"]) == ["BBB"]


def test_filter_by_data_quality_missing_columns(selector: AssetSelector) -> None:
    """Missing required columns should raise a validation error."""
    df = pd.DataFrame({"symbol": ["AAA", "BBB"]})

    with pytest.raises(DataValidationError):
        selector._filter_by_data_quality(df, FilterCriteria())


def test_filter_by_characteristics_combined(selector: AssetSelector) -> None:
    """Characteristics filter should apply market and region requirements."""
    df = pd.DataFrame(
        {
            "symbol": ["AAA", "BBB", "CCC"],
            "market": ["US", "US", "UK"],
            "region": ["North America", "North America", "Europe"],
            "resolved_currency": ["USD", "USD", "GBP"],
            "category": ["Stock", "Stock", "ETF"],
        }
    )
    criteria = FilterCriteria(markets=["US"], regions=["North America"], currencies=["USD"])

    filtered = selector._filter_by_characteristics(df, criteria)

    assert list(filtered["symbol"]) == ["AAA", "BBB"]
