"""Tests for date_utils module."""

from datetime import date

import pandas as pd
import pytest

from portfolio_management.utils.date_utils import (
    date_to_timestamp,
    filter_data_by_date_range,
    timestamp_to_date,
    validate_date_order,
)


class TestDateToTimestamp:
    """Tests for date_to_timestamp function."""

    def test_date_object(self):
        """Test conversion from datetime.date."""
        d = date(2023, 1, 15)
        ts = date_to_timestamp(d)
        assert isinstance(ts, pd.Timestamp)
        assert ts.date() == d

    def test_timestamp_object(self):
        """Test that Timestamp is returned unchanged."""
        ts = pd.Timestamp("2023-01-15")
        result = date_to_timestamp(ts)
        assert result is ts

    def test_string_date(self):
        """Test conversion from string."""
        ts = date_to_timestamp("2023-01-15")
        assert isinstance(ts, pd.Timestamp)
        assert ts.date() == date(2023, 1, 15)

    def test_invalid_date(self):
        """Test error on invalid date string."""
        with pytest.raises(ValueError, match="Cannot convert"):
            date_to_timestamp("invalid-date")


class TestTimestampToDate:
    """Tests for timestamp_to_date function."""

    def test_conversion(self):
        """Test conversion from Timestamp to date."""
        ts = pd.Timestamp("2023-01-15")
        d = timestamp_to_date(ts)
        assert isinstance(d, date)
        assert d == date(2023, 1, 15)

    def test_with_time(self):
        """Test that time component is dropped."""
        ts = pd.Timestamp("2023-01-15 14:30:00")
        d = timestamp_to_date(ts)
        assert d == date(2023, 1, 15)


class TestFilterDataByDateRange:
    """Tests for filter_data_by_date_range function."""

    @pytest.fixture
    def sample_data(self):
        """Create sample DataFrame with date index."""
        dates = pd.date_range("2023-01-01", periods=10, freq="D")
        return pd.DataFrame({"value": range(10)}, index=dates)

    def test_no_bounds(self, sample_data):
        """Test with no start or end date (returns all data)."""
        result = filter_data_by_date_range(sample_data)
        pd.testing.assert_frame_equal(result, sample_data)

    def test_start_date_only(self, sample_data):
        """Test filtering with only start date."""
        result = filter_data_by_date_range(sample_data, start_date=date(2023, 1, 5))
        assert len(result) == 6  # Jan 5-10
        assert result.index[0].date() == date(2023, 1, 5)

    def test_end_date_only(self, sample_data):
        """Test filtering with only end date."""
        result = filter_data_by_date_range(sample_data, end_date=date(2023, 1, 5))
        assert len(result) == 5  # Jan 1-5
        assert result.index[-1].date() == date(2023, 1, 5)

    def test_both_dates(self, sample_data):
        """Test filtering with both start and end dates."""
        result = filter_data_by_date_range(
            sample_data, start_date=date(2023, 1, 3), end_date=date(2023, 1, 7)
        )
        assert len(result) == 5  # Jan 3-7
        assert result.index[0].date() == date(2023, 1, 3)
        assert result.index[-1].date() == date(2023, 1, 7)

    def test_inclusive_both(self, sample_data):
        """Test inclusive='both' (default)."""
        result = filter_data_by_date_range(
            sample_data,
            start_date=date(2023, 1, 5),
            end_date=date(2023, 1, 5),
            inclusive="both",
        )
        assert len(result) == 1
        assert result.index[0].date() == date(2023, 1, 5)

    def test_inclusive_neither(self, sample_data):
        """Test inclusive='neither' (excludes boundaries)."""
        result = filter_data_by_date_range(
            sample_data,
            start_date=date(2023, 1, 3),
            end_date=date(2023, 1, 7),
            inclusive="neither",
        )
        assert len(result) == 3  # Jan 4-6
        assert result.index[0].date() == date(2023, 1, 4)
        assert result.index[-1].date() == date(2023, 1, 6)

    def test_invalid_range(self, sample_data):
        """Test error when start > end."""
        with pytest.raises(ValueError, match="must be before"):
            filter_data_by_date_range(
                sample_data, start_date=date(2023, 1, 7), end_date=date(2023, 1, 3)
            )


class TestValidateDateOrder:
    """Tests for validate_date_order function."""

    def test_valid_order(self):
        """Test that valid order raises no exception."""
        validate_date_order(date(2023, 1, 1), date(2023, 12, 31))
        # No exception should be raised

    def test_equal_dates_allowed(self):
        """Test that equal dates are allowed by default."""
        validate_date_order(date(2023, 1, 1), date(2023, 1, 1))
        # No exception should be raised

    def test_equal_dates_not_allowed(self):
        """Test that equal dates can be disallowed."""
        with pytest.raises(ValueError, match="must be strictly before"):
            validate_date_order(date(2023, 1, 1), date(2023, 1, 1), allow_equal=False)

    def test_invalid_order(self):
        """Test error when start > end."""
        with pytest.raises(ValueError, match="must be before"):
            validate_date_order(date(2023, 12, 31), date(2023, 1, 1))

    def test_with_timestamps(self):
        """Test that pd.Timestamp inputs work."""
        validate_date_order(
            pd.Timestamp("2023-01-01"), pd.Timestamp("2023-12-31")
        )
        # No exception should be raised

    def test_with_strings(self):
        """Test that string inputs work."""
        validate_date_order("2023-01-01", "2023-12-31")
        # No exception should be raised
