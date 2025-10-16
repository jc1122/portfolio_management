# ruff: noqa
"""Tests for asset selection module.

Tests cover filtering logic, data quality checks, and the asset selection
pipeline.
"""

import logging

import pandas as pd
import pytest

from src.portfolio_management.exceptions import DataValidationError
from src.portfolio_management.selection import AssetSelector, FilterCriteria


class TestParseSeverity:
    """Tests for AssetSelector._parse_severity static method."""

    def test_parse_severity_with_value(self) -> None:
        """Test extracting severity value from properly formatted flags."""
        assert AssetSelector._parse_severity("zero_volume_severity=high") == "high"
        assert (
            AssetSelector._parse_severity(
                "zero_volume=10;zero_volume_severity=low",
            )
            == "low"
        )
        assert (
            AssetSelector._parse_severity(
                "zero_volume=100;zero_volume_ratio=0.1;zero_volume_severity=moderate",
            )
            == "moderate"
        )

    def test_parse_severity_missing(self) -> None:
        """Test that None is returned when severity is not in flags."""
        assert AssetSelector._parse_severity("other_flag=value") is None
        assert (
            AssetSelector._parse_severity("zero_volume=10;zero_volume_ratio=0.05")
            is None
        )

    def test_parse_severity_empty_string(self) -> None:
        """Test that None is returned for empty string."""
        assert AssetSelector._parse_severity("") is None

    def test_parse_severity_none(self) -> None:
        """Test that None is returned for None input."""
        assert AssetSelector._parse_severity(None) is None

    def test_parse_severity_nan(self) -> None:
        """Test that None is returned for NaN (float)."""
        import math

        assert AssetSelector._parse_severity(math.nan) is None

    def test_parse_severity_whitespace(self) -> None:
        """Test handling of whitespace in flags."""
        assert AssetSelector._parse_severity("zero_volume_severity= high ") == "high"


class TestFilterByDataQuality:
    """Tests for AssetSelector._filter_by_data_quality method."""

    @pytest.fixture
    def selector(self) -> AssetSelector:
        """Create an AssetSelector instance for testing."""
        return AssetSelector()

    @pytest.fixture
    def sample_df(self) -> pd.DataFrame:
        """Create a sample DataFrame with test data."""
        return pd.DataFrame(
            {
                "symbol": ["AAPL.US", "MSFT.US", "GOOGL.US", "TSLA.US"],
                "isin": [
                    "US0378331005",
                    "US5949181045",
                    "US02079K3059",
                    "US88160R1014",
                ],
                "data_status": ["ok", "warning", "ok", "warning"],
                "data_flags": [
                    "",
                    "zero_volume_severity=low",
                    "zero_volume_severity=high",
                    "zero_volume_severity=moderate",
                ],
            },
        )

    def test_filter_by_data_status_ok_only(
        self,
        selector: AssetSelector,
        sample_df: pd.DataFrame,
    ) -> None:
        """Test filtering for 'ok' status only."""
        criteria = FilterCriteria(data_status=["ok"])
        result = selector._filter_by_data_quality(sample_df, criteria)

        assert len(result) == 2
        assert set(result["symbol"]) == {"AAPL.US", "GOOGL.US"}

    def test_filter_by_data_status_multiple(
        self,
        selector: AssetSelector,
        sample_df: pd.DataFrame,
    ) -> None:
        """Test filtering for multiple status values."""
        criteria = FilterCriteria(data_status=["ok", "warning"])
        result = selector._filter_by_data_quality(sample_df, criteria)

        assert len(result) == 4

    def test_filter_by_severity_low_only(
        self,
        selector: AssetSelector,
        sample_df: pd.DataFrame,
    ) -> None:
        """Test filtering by zero_volume_severity=low."""
        criteria = FilterCriteria(
            data_status=["ok", "warning"],
            zero_volume_severity=["low"],
        )
        result = selector._filter_by_data_quality(sample_df, criteria)

        assert len(result) == 1
        assert result.iloc[0]["symbol"] == "MSFT.US"

    def test_filter_by_severity_multiple(
        self,
        selector: AssetSelector,
        sample_df: pd.DataFrame,
    ) -> None:
        """Test filtering by multiple severity levels."""
        criteria = FilterCriteria(
            data_status=["ok", "warning"],
            zero_volume_severity=["low", "moderate"],
        )
        result = selector._filter_by_data_quality(sample_df, criteria)

        assert len(result) == 2
        assert set(result["symbol"]) == {"MSFT.US", "TSLA.US"}

    def test_filter_combined_status_and_severity(
        self,
        selector: AssetSelector,
        sample_df: pd.DataFrame,
    ) -> None:
        """Test combined filtering by status and severity."""
        criteria = FilterCriteria(
            data_status=["ok"],
            zero_volume_severity=["high"],
        )
        result = selector._filter_by_data_quality(sample_df, criteria)

        assert len(result) == 1
        assert result.iloc[0]["symbol"] == "GOOGL.US"

    def test_filter_empty_result(
        self,
        selector: AssetSelector,
        sample_df: pd.DataFrame,
    ) -> None:
        """Test when filtering results in empty DataFrame."""
        criteria = FilterCriteria(
            data_status=["error"],
        )
        result = selector._filter_by_data_quality(sample_df, criteria)

        assert len(result) == 0
        assert isinstance(result, pd.DataFrame)

    def test_filter_missing_columns_raises(
        self,
        selector: AssetSelector,
    ) -> None:
        """Test that missing required columns raises ValueError."""
        df = pd.DataFrame({"symbol": ["A", "B"]})
        criteria = FilterCriteria()

        with pytest.raises(DataValidationError, match="missing required columns"):
            selector._filter_by_data_quality(df, criteria)

    def test_filter_empty_input_dataframe(
        self,
        selector: AssetSelector,
    ) -> None:
        """Test handling of empty input DataFrame."""
        df = pd.DataFrame({"data_status": [], "data_flags": []})
        criteria = FilterCriteria()

        result = selector._filter_by_data_quality(df, criteria)

        assert len(result) == 0

    def test_filter_with_nan_data_flags(
        self,
        selector: AssetSelector,
    ) -> None:
        """Test handling of NaN values in data_flags column."""
        df = pd.DataFrame(
            {
                "symbol": ["A", "B", "C"],
                "data_status": ["ok", "ok", "ok"],
                "data_flags": ["", None, "zero_volume_severity=low"],
            },
        )
        criteria = FilterCriteria(
            data_status=["ok"],
            zero_volume_severity=["low"],
        )

        result = selector._filter_by_data_quality(df, criteria)

        assert len(result) == 1
        assert result.iloc[0]["symbol"] == "C"

    def test_filter_no_severity_filtering(
        self,
        selector: AssetSelector,
        sample_df: pd.DataFrame,
    ) -> None:
        """Test that severity filtering is skipped when not specified."""
        criteria = FilterCriteria(
            data_status=["ok", "warning"],
            zero_volume_severity=None,
        )
        result = selector._filter_by_data_quality(sample_df, criteria)

        assert len(result) == 4


class TestAssetSelectorIntegration:
    """Integration tests with real fixture data."""

    @pytest.fixture
    def selector(self) -> AssetSelector:
        """Create an AssetSelector instance for testing."""
        return AssetSelector()

    @pytest.fixture
    def match_fixture_df(self) -> pd.DataFrame:
        """Load the match report fixture."""
        return pd.read_csv("tests/fixtures/metadata/selected_matches.csv")

    def test_filter_by_status_on_fixture(
        self,
        selector: AssetSelector,
        match_fixture_df: pd.DataFrame,
    ) -> None:
        """Test filtering on real fixture data."""
        criteria = FilterCriteria(data_status=["ok", "warning"])
        result = selector._filter_by_data_quality(match_fixture_df, criteria)

        # Should have at least some results
        assert len(result) > 0
        # All should have ok or warning status
        assert all(result["data_status"].isin(["ok", "warning"]))

    def test_filter_by_severity_on_fixture(
        self,
        selector: AssetSelector,
        match_fixture_df: pd.DataFrame,
    ) -> None:
        """Test severity filtering on real fixture data."""
        criteria = FilterCriteria(
            data_status=["ok", "warning"],
            zero_volume_severity=["low"],
        )
        result = selector._filter_by_data_quality(match_fixture_df, criteria)

        # Should have results
        assert len(result) > 0
        # All should have low severity or no severity info
        for _, row in result.iterrows():
            severity = AssetSelector._parse_severity(row["data_flags"])
            if severity is not None:
                assert severity == "low"


class TestFilterByCharacteristics:
    """Tests for AssetSelector._filter_by_characteristics method."""

    @pytest.fixture
    def selector(self) -> AssetSelector:
        """Create an AssetSelector instance for testing."""
        return AssetSelector()

    @pytest.fixture
    def sample_df_characteristics(self) -> pd.DataFrame:
        """Create a sample DataFrame with characteristics data."""
        return pd.DataFrame(
            {
                "symbol": ["A", "B", "C", "D", "E", "F"],
                "market": ["UK", "US", "UK", "DE", "UK", "US"],
                "region": [
                    "Europe",
                    "Americas",
                    "Europe",
                    "Europe",
                    "Europe",
                    "Americas",
                ],
                "resolved_currency": ["GBP", "USD", "GBP", "EUR", "GBP", "USD"],
                "category": ["ETF", "Stock", "Bond", "ETF", "Stock", "ETF"],
            },
        )

    @pytest.fixture
    def match_fixture_df(self) -> pd.DataFrame:
        """Load the match report fixture."""
        return pd.read_csv("tests/fixtures/metadata/selected_matches.csv")

    def test_filter_by_market_single(
        self,
        selector: AssetSelector,
        sample_df_characteristics: pd.DataFrame,
    ) -> None:
        """Test filtering by single market."""
        criteria = FilterCriteria(markets=["UK"])
        result = selector._filter_by_characteristics(
            sample_df_characteristics, criteria
        )

        assert len(result) == 3
        assert set(result["symbol"]) == {"A", "C", "E"}
        assert all(result["market"] == "UK")

    def test_filter_by_market_multiple(
        self,
        selector: AssetSelector,
        sample_df_characteristics: pd.DataFrame,
    ) -> None:
        """Test filtering by multiple markets."""
        criteria = FilterCriteria(markets=["UK", "US"])
        result = selector._filter_by_characteristics(
            sample_df_characteristics, criteria
        )

        assert len(result) == 5
        assert set(result["symbol"]) == {"A", "B", "C", "E", "F"}

    def test_filter_by_region_single(
        self,
        selector: AssetSelector,
        sample_df_characteristics: pd.DataFrame,
    ) -> None:
        """Test filtering by single region."""
        criteria = FilterCriteria(regions=["Europe"])
        result = selector._filter_by_characteristics(
            sample_df_characteristics, criteria
        )

        assert len(result) == 4
        assert set(result["symbol"]) == {"A", "C", "D", "E"}

    def test_filter_by_currency_single(
        self,
        selector: AssetSelector,
        sample_df_characteristics: pd.DataFrame,
    ) -> None:
        """Test filtering by single currency."""
        criteria = FilterCriteria(currencies=["GBP"])
        result = selector._filter_by_characteristics(
            sample_df_characteristics, criteria
        )

        assert len(result) == 3
        assert set(result["symbol"]) == {"A", "C", "E"}

    def test_filter_by_currency_multiple(
        self,
        selector: AssetSelector,
        sample_df_characteristics: pd.DataFrame,
    ) -> None:
        """Test filtering by multiple currencies."""
        criteria = FilterCriteria(currencies=["GBP", "USD"])
        result = selector._filter_by_characteristics(
            sample_df_characteristics, criteria
        )

        assert len(result) == 5
        assert set(result["symbol"]) == {"A", "B", "C", "E", "F"}

    def test_filter_by_category_single(
        self,
        selector: AssetSelector,
        sample_df_characteristics: pd.DataFrame,
    ) -> None:
        """Test filtering by single category."""
        criteria = FilterCriteria(categories=["ETF"])
        result = selector._filter_by_characteristics(
            sample_df_characteristics, criteria
        )

        assert len(result) == 3
        assert set(result["symbol"]) == {"A", "D", "F"}

    def test_filter_combined_market_and_currency(
        self,
        selector: AssetSelector,
        sample_df_characteristics: pd.DataFrame,
    ) -> None:
        """Test combined filtering by market and currency."""
        criteria = FilterCriteria(markets=["UK"], currencies=["GBP"])
        result = selector._filter_by_characteristics(
            sample_df_characteristics, criteria
        )

        assert len(result) == 3
        assert set(result["symbol"]) == {"A", "C", "E"}
        assert all(result["market"] == "UK")
        assert all(result["resolved_currency"] == "GBP")

    def test_filter_combined_all_characteristics(
        self,
        selector: AssetSelector,
        sample_df_characteristics: pd.DataFrame,
    ) -> None:
        """Test filtering with all characteristic filters."""
        criteria = FilterCriteria(
            markets=["UK", "US"],
            regions=["Europe"],
            currencies=["GBP"],
            categories=["ETF", "Bond"],
        )
        result = selector._filter_by_characteristics(
            sample_df_characteristics, criteria
        )

        # A (UK, Europe, GBP, ETF) and C (UK, Europe, GBP, Bond) match
        assert len(result) == 2
        assert set(result["symbol"]) == {"A", "C"}

    def test_filter_no_results(
        self,
        selector: AssetSelector,
        sample_df_characteristics: pd.DataFrame,
    ) -> None:
        """Test when filtering results in no matches."""
        criteria = FilterCriteria(markets=["JP"], categories=["Crypto"])
        result = selector._filter_by_characteristics(
            sample_df_characteristics, criteria
        )

        assert len(result) == 0

    def test_filter_empty_dataframe(
        self,
        selector: AssetSelector,
    ) -> None:
        """Test with empty input DataFrame."""
        df = pd.DataFrame(
            {"market": [], "region": [], "resolved_currency": [], "category": []},
        )
        criteria = FilterCriteria(markets=["UK"])

        result = selector._filter_by_characteristics(df, criteria)

        assert len(result) == 0

    def test_filter_missing_columns(
        self,
        selector: AssetSelector,
    ) -> None:
        """Test that missing columns raises ValueError."""
        df = pd.DataFrame({"symbol": ["A", "B"]})
        criteria = FilterCriteria()

        with pytest.raises(DataValidationError, match="missing required columns"):
            selector._filter_by_characteristics(df, criteria)

    def test_filter_no_criteria_specified(
        self,
        selector: AssetSelector,
        sample_df_characteristics: pd.DataFrame,
    ) -> None:
        """Test when no filter criteria are specified."""
        criteria = FilterCriteria(
            markets=None,
            regions=None,
            currencies=None,
            categories=None,
        )
        result = selector._filter_by_characteristics(
            sample_df_characteristics, criteria
        )

        # Should return all rows since no filters applied
        assert len(result) == 6

    def test_filter_preserves_all_rows_and_columns(
        self,
        selector: AssetSelector,
        sample_df_characteristics: pd.DataFrame,
    ) -> None:
        """Test that filtering preserves all columns."""
        criteria = FilterCriteria(markets=["UK"])
        result = selector._filter_by_characteristics(
            sample_df_characteristics, criteria
        )

        # Should have all original columns
        assert set(result.columns) == set(sample_df_characteristics.columns)

    def test_filter_integration_with_fixture(
        self,
        selector: AssetSelector,
        match_fixture_df: pd.DataFrame,
    ) -> None:
        """Test characteristics filtering on real fixture data."""
        # Filter for specific category that we know exists
        criteria = FilterCriteria(
            categories=["lse etfs/1"],
        )
        result = selector._filter_by_characteristics(match_fixture_df, criteria)

        # Should have results
        assert len(result) > 0
        # All should match criteria
        assert all(result["category"] == "lse etfs/1")

    def test_filter_multiple_characteristics_real_data(
        self,
        selector: AssetSelector,
        match_fixture_df: pd.DataFrame,
    ) -> None:
        """Test combined characteristics filtering on real fixture data."""
        # Filter for specific categories
        criteria = FilterCriteria(
            categories=["lse etfs/1", "lse etfs/2"],
        )
        result = selector._filter_by_characteristics(match_fixture_df, criteria)

        # Should have results
        assert len(result) > 0
        # All should match criteria
        assert all(result["category"].isin(["lse etfs/1", "lse etfs/2"]))


class TestIsInList:
    """Tests for AssetSelector._is_in_list static method."""

    def test_is_in_list_symbol_match(self) -> None:
        """Test matching by symbol."""
        result = AssetSelector._is_in_list("AAPL.US", "US0378331005", {"AAPL.US"})
        assert result is True

    def test_is_in_list_isin_match(self) -> None:
        """Test matching by ISIN."""
        result = AssetSelector._is_in_list(
            "AAPL.US",
            "US0378331005",
            {"US0378331005"},
        )
        assert result is True

    def test_is_in_list_both_match(self) -> None:
        """Test when both symbol and ISIN are in list."""
        result = AssetSelector._is_in_list(
            "AAPL.US",
            "US0378331005",
            {"AAPL.US", "US0378331005"},
        )
        assert result is True

    def test_is_in_list_no_match(self) -> None:
        """Test when neither symbol nor ISIN are in list."""
        result = AssetSelector._is_in_list(
            "AAPL.US",
            "US0378331005",
            {"MSFT.US", "US5949181045"},
        )
        assert result is False

    def test_is_in_list_empty_list(self) -> None:
        """Test with empty list."""
        result = AssetSelector._is_in_list("AAPL.US", "US0378331005", set())
        assert result is False


class TestApplyLists:
    """Tests for AssetSelector._apply_lists method."""

    @pytest.fixture
    def selector(self) -> AssetSelector:
        """Create an AssetSelector instance for testing."""
        return AssetSelector()

    @pytest.fixture
    def sample_df_lists(self) -> pd.DataFrame:
        """Create a sample DataFrame for list testing."""
        return pd.DataFrame(
            {
                "symbol": ["AAPL.US", "MSFT.US", "GOOGL.US", "TSLA.US", "META.US"],
                "isin": [
                    "US0378331005",
                    "US5949181045",
                    "US02079K3059",
                    "US88160R1014",
                    "US30303M1027",
                ],
            },
        )

    @pytest.fixture
    def match_fixture_df(self) -> pd.DataFrame:
        """Load the match report fixture."""
        return pd.read_csv("tests/fixtures/metadata/selected_matches.csv")

    def test_no_lists_specified(
        self,
        selector: AssetSelector,
        sample_df_lists: pd.DataFrame,
    ) -> None:
        """Test when no allowlist or blocklist are specified."""
        criteria = FilterCriteria(allowlist=None, blocklist=None)
        result = selector._apply_lists(sample_df_lists, criteria)

        # Should return all rows
        assert len(result) == 5

    def test_blocklist_by_symbol(
        self,
        selector: AssetSelector,
        sample_df_lists: pd.DataFrame,
    ) -> None:
        """Test blocklist filtering by symbol."""
        criteria = FilterCriteria(blocklist={"AAPL.US", "MSFT.US"})
        result = selector._apply_lists(sample_df_lists, criteria)

        assert len(result) == 3
        assert set(result["symbol"]) == {"GOOGL.US", "TSLA.US", "META.US"}

    def test_blocklist_by_isin(
        self,
        selector: AssetSelector,
        sample_df_lists: pd.DataFrame,
    ) -> None:
        """Test blocklist filtering by ISIN."""
        criteria = FilterCriteria(blocklist={"US0378331005", "US02079K3059"})
        result = selector._apply_lists(sample_df_lists, criteria)

        assert len(result) == 3
        assert set(result["symbol"]) == {"MSFT.US", "TSLA.US", "META.US"}

    def test_blocklist_mixed_symbol_and_isin(
        self,
        selector: AssetSelector,
        sample_df_lists: pd.DataFrame,
    ) -> None:
        """Test blocklist with both symbols and ISINs."""
        criteria = FilterCriteria(
            blocklist={"AAPL.US", "US5949181045"},  # AAPL by symbol, MSFT by ISIN
        )
        result = selector._apply_lists(sample_df_lists, criteria)

        assert len(result) == 3
        assert set(result["symbol"]) == {"GOOGL.US", "TSLA.US", "META.US"}

    def test_allowlist_by_symbol(
        self,
        selector: AssetSelector,
        sample_df_lists: pd.DataFrame,
    ) -> None:
        """Test allowlist filtering by symbol."""
        criteria = FilterCriteria(allowlist={"AAPL.US", "MSFT.US"})
        result = selector._apply_lists(sample_df_lists, criteria)

        assert len(result) == 2
        assert set(result["symbol"]) == {"AAPL.US", "MSFT.US"}

    def test_allowlist_by_isin(
        self,
        selector: AssetSelector,
        sample_df_lists: pd.DataFrame,
    ) -> None:
        """Test allowlist filtering by ISIN."""
        criteria = FilterCriteria(allowlist={"US0378331005", "US5949181045"})
        result = selector._apply_lists(sample_df_lists, criteria)

        assert len(result) == 2
        assert set(result["symbol"]) == {"AAPL.US", "MSFT.US"}

    def test_blocklist_and_allowlist_combined(
        self,
        selector: AssetSelector,
        sample_df_lists: pd.DataFrame,
    ) -> None:
        """Test combined blocklist and allowlist."""
        # Allow: AAPL, MSFT, GOOGL, TSLA
        # Block: AAPL, TSLA
        # Result: MSFT, GOOGL
        criteria = FilterCriteria(
            allowlist={"AAPL.US", "MSFT.US", "GOOGL.US", "TSLA.US"},
            blocklist={"AAPL.US", "TSLA.US"},
        )
        result = selector._apply_lists(sample_df_lists, criteria)

        assert len(result) == 2
        assert set(result["symbol"]) == {"MSFT.US", "GOOGL.US"}

    def test_allowlist_and_blocklist_no_overlap(
        self,
        selector: AssetSelector,
        sample_df_lists: pd.DataFrame,
    ) -> None:
        """Test when allowlist and blocklist don't overlap."""
        criteria = FilterCriteria(
            allowlist={"AAPL.US", "MSFT.US"},
            blocklist={"GOOGL.US", "TSLA.US"},
        )
        result = selector._apply_lists(sample_df_lists, criteria)

        assert len(result) == 2
        assert set(result["symbol"]) == {"AAPL.US", "MSFT.US"}

    def test_blocklist_removes_all(
        self,
        selector: AssetSelector,
        sample_df_lists: pd.DataFrame,
    ) -> None:
        """Test when blocklist removes all assets."""
        criteria = FilterCriteria(
            blocklist={
                "AAPL.US",
                "MSFT.US",
                "GOOGL.US",
                "TSLA.US",
                "META.US",
            },
        )
        result = selector._apply_lists(sample_df_lists, criteria)

        assert len(result) == 0

    def test_allowlist_matches_nothing(
        self,
        selector: AssetSelector,
        sample_df_lists: pd.DataFrame,
    ) -> None:
        """Test when allowlist matches nothing."""
        criteria = FilterCriteria(allowlist={"UNKNOWN.US"})
        result = selector._apply_lists(sample_df_lists, criteria)

        assert len(result) == 0

    def test_empty_dataframe(
        self,
        selector: AssetSelector,
    ) -> None:
        """Test with empty input DataFrame."""
        df = pd.DataFrame({"symbol": [], "isin": []})
        criteria = FilterCriteria(blocklist={"AAPL.US"})

        result = selector._apply_lists(df, criteria)

        assert len(result) == 0

    def test_missing_columns(
        self,
        selector: AssetSelector,
    ) -> None:
        """Test that missing columns raises ValueError."""
        df = pd.DataFrame({"name": ["A", "B"]})
        criteria = FilterCriteria()

        with pytest.raises(DataValidationError, match="missing required columns"):
            selector._apply_lists(df, criteria)

    def test_preserves_columns(
        self,
        selector: AssetSelector,
        sample_df_lists: pd.DataFrame,
    ) -> None:
        """Test that all columns are preserved."""
        criteria = FilterCriteria(blocklist={"AAPL.US"})
        result = selector._apply_lists(sample_df_lists, criteria)

        assert set(result.columns) == set(sample_df_lists.columns)

    def test_integration_with_fixture(
        self,
        selector: AssetSelector,
        match_fixture_df: pd.DataFrame,
    ) -> None:
        """Test list filtering on real fixture data."""
        # Get some symbols from the fixture
        sample_symbols = set(match_fixture_df["symbol"].head(5))

        criteria = FilterCriteria(allowlist=sample_symbols)
        result = selector._apply_lists(match_fixture_df, criteria)

        # Should have exactly 5 results
        assert len(result) == 5
        assert set(result["symbol"]) == sample_symbols


class TestCalculateHistoryDays:
    """Tests for AssetSelector._calculate_history_days static method."""

    def test_valid_dates(self) -> None:
        """Test calculating days between valid dates."""
        days = AssetSelector._calculate_history_days("2020-01-01", "2025-10-15")
        assert days > 2000  # Approximately 2119 days

    def test_same_date(self) -> None:
        """Test when start and end dates are the same."""
        days = AssetSelector._calculate_history_days("2020-01-01", "2020-01-01")
        assert days == 0

    def test_one_day_difference(self) -> None:
        """Test when dates are one day apart."""
        days = AssetSelector._calculate_history_days("2020-01-01", "2020-01-02")
        assert days == 1

    def test_reversed_dates(self) -> None:
        """Test when end date is before start date."""
        days = AssetSelector._calculate_history_days("2025-10-15", "2020-01-01")
        assert days == 0

    def test_none_start_date(self) -> None:
        """Test with None as start date."""
        days = AssetSelector._calculate_history_days(None, "2025-10-15")
        assert days == 0

    def test_none_end_date(self) -> None:
        """Test with None as end date."""
        days = AssetSelector._calculate_history_days("2020-01-01", None)
        assert days == 0

    def test_both_none(self) -> None:
        """Test with both dates as None."""
        days = AssetSelector._calculate_history_days(None, None)
        assert days == 0

    def test_invalid_start_date_format(self) -> None:
        """Test with invalid start date format."""
        days = AssetSelector._calculate_history_days("invalid", "2025-10-15")
        assert days == 0

    def test_invalid_end_date_format(self) -> None:
        """Test with invalid end date format."""
        days = AssetSelector._calculate_history_days("2020-01-01", "invalid")
        assert days == 0

    def test_partial_date_format(self) -> None:
        """Test with partial date format (pandas will try to parse)."""
        # pandas.to_datetime is lenient and can parse partial formats
        days = AssetSelector._calculate_history_days("2020-01", "2025-10")
        assert days > 2000


class TestFilterByHistory:
    """Tests for AssetSelector._filter_by_history method."""

    @pytest.fixture
    def selector(self) -> AssetSelector:
        """Create an AssetSelector instance for testing."""
        return AssetSelector()

    @pytest.fixture
    def sample_df_history(self) -> pd.DataFrame:
        """Create a sample DataFrame with history data."""
        return pd.DataFrame(
            {
                "symbol": ["A", "B", "C", "D", "E"],
                "price_start": [
                    "2020-01-01",
                    "2024-09-01",
                    "2020-01-01",
                    "2025-10-01",
                    "2020-01-01",
                ],
                "price_end": [
                    "2025-10-15",
                    "2025-10-15",
                    "2025-10-15",
                    "2025-10-15",
                    "2020-06-01",
                ],
                "price_rows": [1500, 400, 1500, 15, 151],
            },
        )

    @pytest.fixture
    def match_fixture_df(self) -> pd.DataFrame:
        """Load the match report fixture."""
        return pd.read_csv("tests/fixtures/metadata/selected_matches.csv")

    def test_filter_by_min_history_days(
        self,
        selector: AssetSelector,
        sample_df_history: pd.DataFrame,
    ) -> None:
        """Test filtering by minimum history days."""
        criteria = FilterCriteria(min_history_days=252)
        result = selector._filter_by_history(sample_df_history, criteria)

        # A, B, C have more than 252 days; D has ~15 days; E has ~152 days
        assert len(result) == 3
        assert set(result["symbol"]) == {"A", "B", "C"}

    def test_filter_by_min_price_rows(
        self,
        selector: AssetSelector,
        sample_df_history: pd.DataFrame,
    ) -> None:
        """Test filtering by minimum price rows."""
        criteria = FilterCriteria(min_price_rows=200)
        result = selector._filter_by_history(sample_df_history, criteria)

        # A, B, C have >= 200 rows
        assert len(result) == 3
        assert set(result["symbol"]) == {"A", "B", "C"}

    def test_filter_combined_history_and_rows(
        self,
        selector: AssetSelector,
        sample_df_history: pd.DataFrame,
    ) -> None:
        """Test combined filtering by history and row count."""
        criteria = FilterCriteria(min_history_days=400, min_price_rows=200)
        result = selector._filter_by_history(sample_df_history, criteria)

        # A, B, C have both sufficient history and rows
        # But B has ~406 days (good) and 400 rows (good)
        assert len(result) >= 1
        assert "A" in result["symbol"].values

    def test_filter_no_results(
        self,
        selector: AssetSelector,
        sample_df_history: pd.DataFrame,
    ) -> None:
        """Test when filtering results in no matches."""
        criteria = FilterCriteria(min_history_days=5000, min_price_rows=1500)
        result = selector._filter_by_history(sample_df_history, criteria)

        assert len(result) == 0

    def test_filter_empty_dataframe(
        self,
        selector: AssetSelector,
    ) -> None:
        """Test with empty input DataFrame."""
        df = pd.DataFrame({"price_start": [], "price_end": [], "price_rows": []})
        criteria = FilterCriteria()

        result = selector._filter_by_history(df, criteria)

        assert len(result) == 0

    def test_filter_missing_columns(
        self,
        selector: AssetSelector,
    ) -> None:
        """Test that missing columns raises ValueError."""
        df = pd.DataFrame({"symbol": ["A", "B"]})
        criteria = FilterCriteria()

        with pytest.raises(DataValidationError, match="missing required columns"):
            selector._filter_by_history(df, criteria)

    def test_filter_invalid_dates(
        self,
        selector: AssetSelector,
    ) -> None:
        """Test handling of invalid date formats."""
        df = pd.DataFrame(
            {
                "price_start": ["invalid", "2020-01-01", "2020-01-01"],
                "price_end": ["2025-10-15", "invalid", "2025-10-15"],
                "price_rows": [1500, 1500, 1500],
            },
        )
        criteria = FilterCriteria(min_history_days=252)

        result = selector._filter_by_history(df, criteria)

        # Only the third row should pass (valid dates, sufficient history)
        assert len(result) == 1
        assert result.iloc[0]["price_start"] == "2020-01-01"

    def test_filter_preserves_all_columns(
        self,
        selector: AssetSelector,
        sample_df_history: pd.DataFrame,
    ) -> None:
        """Test that filtering preserves all original columns."""
        criteria = FilterCriteria(min_history_days=100)
        result = selector._filter_by_history(sample_df_history, criteria)

        # Should have all original columns (no temp columns)
        expected_cols = {"symbol", "price_start", "price_end", "price_rows"}
        assert expected_cols == set(result.columns)

    def test_filter_integration_with_fixture(
        self,
        selector: AssetSelector,
        match_fixture_df: pd.DataFrame,
    ) -> None:
        """Test history filtering on real fixture data."""
        criteria = FilterCriteria(min_history_days=252, min_price_rows=252)
        result = selector._filter_by_history(match_fixture_df, criteria)

        # Should have multiple results
        assert len(result) > 0
        # All should have sufficient history
        for _, row in result.iterrows():
            days = AssetSelector._calculate_history_days(
                row["price_start"],
                row["price_end"],
            )
            assert days >= 252
            assert row["price_rows"] >= 252


class TestSelectAssets:
    """Tests for the main select_assets method."""

    @pytest.fixture
    def selector(self) -> AssetSelector:
        """Create an AssetSelector instance for testing."""
        return AssetSelector()

    def test_select_assets_full_pipeline(
        self,
        selector: AssetSelector,
        selection_test_matches: pd.DataFrame,
    ) -> None:
        """Test the full asset selection pipeline with various criteria."""
        criteria = FilterCriteria(
            min_history_days=365,
            min_price_rows=250,
            markets=["UK", "US"],
            blocklist={"BLOCK.US"},
        )
        selected_assets = selector.select_assets(selection_test_matches, criteria)

        assert isinstance(selected_assets, list)
        assert len(selected_assets) > 0

        symbols = {asset.symbol for asset in selected_assets}
        assert "TSTA.UK" in symbols
        assert "TSTB.US" in symbols
        assert "BLOCK.US" not in symbols
        assert "ALLOW.US" not in symbols  # Not in markets

    def test_select_assets_empty_result(
        self,
        selector: AssetSelector,
        selection_test_matches: pd.DataFrame,
    ) -> None:
        """Test that an empty list is returned when no assets match."""
        criteria = FilterCriteria(min_history_days=99999)
        selected_assets = selector.select_assets(selection_test_matches, criteria)

        assert isinstance(selected_assets, list)
        assert len(selected_assets) == 0

    def test_select_assets_invalid_input_df(self, selector: AssetSelector) -> None:
        """Test that invalid DataFrame input raises an error."""
        with pytest.raises(
            DataValidationError, match="Input DataFrame is missing required columns"
        ):
            selector.select_assets(
                pd.DataFrame({"symbol": []}), FilterCriteria.default()
            )

    def test_select_assets_allowlist_overrides(
        self,
        selector: AssetSelector,
        selection_test_matches: pd.DataFrame,
    ) -> None:
        """Test that allowlist overrides other filters."""
        criteria = FilterCriteria(
            data_status=["ok", "warning"],
            allowlist={"ALLOW.US"},
            min_history_days=20,
            min_price_rows=20,
        )

        selected_assets = selector.select_assets(selection_test_matches, criteria)
        assert len(selected_assets) == 1
        assert selected_assets[0].symbol == "ALLOW.US"

    def test_select_assets_logging(
        self,
        selector: AssetSelector,
        selection_test_matches: pd.DataFrame,
        caplog,
    ) -> None:
        """Test that logging output is generated."""
        with caplog.at_level(logging.INFO):
            selector.select_assets(selection_test_matches, FilterCriteria.default())
            assert "Starting asset selection" in caplog.text
            assert "Finished asset selection" in caplog.text
            assert "Breakdown by market" in caplog.text
            assert "Breakdown by region" in caplog.text
