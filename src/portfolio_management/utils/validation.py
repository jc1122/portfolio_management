"""Validation utilities for configuration and data parameters.

This module provides common validation functions for numeric ranges,
probabilities, and date ranges to reduce duplication and ensure
consistent error messages.

Functions:
    validate_positive_int: Validate integer is positive
    validate_probability: Validate value is in [0, 1] range
    validate_date_range: Validate date range parameters

"""

from __future__ import annotations

import datetime


def validate_positive_int(value: int, name: str, allow_zero: bool = False) -> None:
    """Validate that an integer value is positive.

    Args:
        value: Integer value to validate
        name: Parameter name for error messages
        allow_zero: Whether zero is considered valid

    Raises:
        ValueError: If value is not positive (or non-negative if allow_zero=True)

    Example:
        >>> validate_positive_int(5, "lookback")
        >>> # No exception raised
        >>>
        >>> validate_positive_int(0, "lookback")
        Traceback (most recent call last):
            ...
        ValueError: lookback must be >= 1, got 0
        >>>
        >>> validate_positive_int(0, "skip", allow_zero=True)
        >>> # No exception raised

    """
    if allow_zero:
        if value < 0:
            raise ValueError(f"{name} must be >= 0, got {value}")
    else:
        if value < 1:
            raise ValueError(f"{name} must be >= 1, got {value}")


def validate_probability(value: float, name: str) -> None:
    """Validate that a float value is in the [0, 1] range.

    Args:
        value: Float value to validate
        name: Parameter name for error messages

    Raises:
        ValueError: If value is not in [0, 1]

    Example:
        >>> validate_probability(0.5, "max_turnover")
        >>> # No exception raised
        >>>
        >>> validate_probability(1.5, "max_turnover")
        Traceback (most recent call last):
            ...
        ValueError: max_turnover must be in [0, 1], got 1.5

    """
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be in [0, 1], got {value}")


def validate_date_range(
    start_date: datetime.date | None,
    end_date: datetime.date | None,
    param_name: str = "date range",
) -> None:
    """Validate that a date range is valid.

    Checks that both dates are present if either is, and that start <= end.

    Args:
        start_date: Start date (None if not specified)
        end_date: End date (None if not specified)
        param_name: Parameter name for error messages

    Raises:
        ValueError: If only one date is specified, or if start > end

    Example:
        >>> from datetime import date
        >>> validate_date_range(date(2023, 1, 1), date(2023, 12, 31))
        >>> # No exception raised
        >>>
        >>> validate_date_range(date(2023, 1, 1), None)
        Traceback (most recent call last):
            ...
        ValueError: Both start and end dates must be specified for date range

    """
    # Check that both or neither are specified
    if (start_date is None) != (end_date is None):
        raise ValueError(f"Both start and end dates must be specified for {param_name}")

    # If both are specified, check order
    if start_date is not None and end_date is not None:
        if start_date > end_date:
            raise ValueError(
                f"{param_name}: start_date ({start_date}) must be before or equal to end_date ({end_date})"
            )


def validate_numeric_range(
    value: float,
    name: str,
    min_value: float | None = None,
    max_value: float | None = None,
    min_inclusive: bool = True,
    max_inclusive: bool = True,
) -> None:
    """Validate that a numeric value falls within a specified range.

    Args:
        value: Numeric value to validate
        name: Parameter name for error messages
        min_value: Minimum allowed value (None for no lower bound)
        max_value: Maximum allowed value (None for no upper bound)
        min_inclusive: Whether minimum bound is inclusive
        max_inclusive: Whether maximum bound is inclusive

    Raises:
        ValueError: If value is outside the specified range

    Example:
        >>> validate_numeric_range(0.5, "weight", min_value=0, max_value=1)
        >>> # No exception raised
        >>>
        >>> validate_numeric_range(1.5, "weight", min_value=0, max_value=1)
        Traceback (most recent call last):
            ...
        ValueError: weight must be <= 1, got 1.5

    """
    if min_value is not None:
        if min_inclusive and value < min_value:
            raise ValueError(f"{name} must be >= {min_value}, got {value}")
        if not min_inclusive and value <= min_value:
            raise ValueError(f"{name} must be > {min_value}, got {value}")

    if max_value is not None:
        if max_inclusive and value > max_value:
            raise ValueError(f"{name} must be <= {max_value}, got {value}")
        if not max_inclusive and value >= max_value:
            raise ValueError(f"{name} must be < {max_value}, got {value}")
