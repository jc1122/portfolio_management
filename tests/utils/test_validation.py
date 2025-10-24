"""Tests for validation module."""

from datetime import date

import pytest

from portfolio_management.utils.validation import (
    validate_date_range,
    validate_numeric_range,
    validate_positive_int,
    validate_probability,
)


class TestValidatePositiveInt:
    """Tests for validate_positive_int function."""

    def test_positive_value(self):
        """Test that positive values pass."""
        validate_positive_int(5, "lookback")
        validate_positive_int(1, "min_value")
        validate_positive_int(1000, "large_value")
        # No exceptions should be raised

    def test_zero_not_allowed(self):
        """Test that zero raises error by default."""
        with pytest.raises(ValueError, match="must be >= 1"):
            validate_positive_int(0, "lookback")

    def test_zero_allowed(self):
        """Test that zero is allowed when allow_zero=True."""
        validate_positive_int(0, "skip", allow_zero=True)
        # No exception should be raised

    def test_negative_value(self):
        """Test that negative values raise error."""
        with pytest.raises(ValueError, match="must be >= 1"):
            validate_positive_int(-5, "lookback")

    def test_negative_with_allow_zero(self):
        """Test that negative values raise error even with allow_zero."""
        with pytest.raises(ValueError, match="must be >= 0"):
            validate_positive_int(-1, "skip", allow_zero=True)

    def test_error_message_includes_name(self):
        """Test that error message includes parameter name."""
        with pytest.raises(ValueError, match="my_parameter"):
            validate_positive_int(-1, "my_parameter")


class TestValidateProbability:
    """Tests for validate_probability function."""

    def test_valid_probabilities(self):
        """Test that values in [0, 1] pass."""
        validate_probability(0.0, "prob")
        validate_probability(0.5, "prob")
        validate_probability(1.0, "prob")
        # No exceptions should be raised

    def test_below_zero(self):
        """Test that values < 0 raise error."""
        with pytest.raises(ValueError, match="must be in \\[0, 1\\]"):
            validate_probability(-0.1, "prob")

    def test_above_one(self):
        """Test that values > 1 raise error."""
        with pytest.raises(ValueError, match="must be in \\[0, 1\\]"):
            validate_probability(1.5, "prob")

    def test_error_message_includes_name(self):
        """Test that error message includes parameter name."""
        with pytest.raises(ValueError, match="max_turnover"):
            validate_probability(1.5, "max_turnover")


class TestValidateDateRange:
    """Tests for validate_date_range function."""

    def test_valid_range(self):
        """Test that valid date range passes."""
        validate_date_range(date(2023, 1, 1), date(2023, 12, 31))
        # No exception should be raised

    def test_equal_dates(self):
        """Test that equal dates are allowed."""
        validate_date_range(date(2023, 1, 1), date(2023, 1, 1))
        # No exception should be raised

    def test_invalid_order(self):
        """Test that start > end raises error."""
        with pytest.raises(ValueError, match="must be before or equal"):
            validate_date_range(date(2023, 12, 31), date(2023, 1, 1))

    def test_both_none(self):
        """Test that both None is allowed."""
        validate_date_range(None, None)
        # No exception should be raised

    def test_only_start(self):
        """Test that only start date raises error."""
        with pytest.raises(ValueError, match="Both start and end"):
            validate_date_range(date(2023, 1, 1), None)

    def test_only_end(self):
        """Test that only end date raises error."""
        with pytest.raises(ValueError, match="Both start and end"):
            validate_date_range(None, date(2023, 12, 31))

    def test_custom_param_name(self):
        """Test that custom parameter name appears in error."""
        with pytest.raises(ValueError, match="custom_range"):
            validate_date_range(date(2023, 12, 31), date(2023, 1, 1), "custom_range")


class TestValidateNumericRange:
    """Tests for validate_numeric_range function."""

    def test_within_range(self):
        """Test that values within range pass."""
        validate_numeric_range(0.5, "weight", min_value=0, max_value=1)
        validate_numeric_range(5.0, "value", min_value=0, max_value=10)
        # No exceptions should be raised

    def test_at_boundaries_inclusive(self):
        """Test that boundary values pass when inclusive."""
        validate_numeric_range(0.0, "weight", min_value=0, max_value=1)
        validate_numeric_range(1.0, "weight", min_value=0, max_value=1)
        # No exceptions should be raised

    def test_below_min_inclusive(self):
        """Test that values below min raise error."""
        with pytest.raises(ValueError, match="must be >= 0"):
            validate_numeric_range(-0.1, "weight", min_value=0, max_value=1)

    def test_above_max_inclusive(self):
        """Test that values above max raise error."""
        with pytest.raises(ValueError, match="must be <= 1"):
            validate_numeric_range(1.1, "weight", min_value=0, max_value=1)

    def test_at_min_exclusive(self):
        """Test that min boundary fails when exclusive."""
        with pytest.raises(ValueError, match="must be > 0"):
            validate_numeric_range(
                0.0, "weight", min_value=0, max_value=1, min_inclusive=False
            )

    def test_at_max_exclusive(self):
        """Test that max boundary fails when exclusive."""
        with pytest.raises(ValueError, match="must be < 1"):
            validate_numeric_range(
                1.0, "weight", min_value=0, max_value=1, max_inclusive=False
            )

    def test_no_lower_bound(self):
        """Test validation with no lower bound."""
        validate_numeric_range(-1000.0, "value", max_value=1)
        # No exception should be raised

    def test_no_upper_bound(self):
        """Test validation with no upper bound."""
        validate_numeric_range(1000.0, "value", min_value=0)
        # No exception should be raised

    def test_no_bounds(self):
        """Test validation with no bounds."""
        validate_numeric_range(12345.67, "value")
        # No exception should be raised

    def test_error_message_includes_name(self):
        """Test that error messages include parameter name."""
        with pytest.raises(ValueError, match="my_param"):
            validate_numeric_range(1.5, "my_param", min_value=0, max_value=1)
