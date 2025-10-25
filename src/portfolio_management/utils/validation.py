"""Validation utilities for configuration and data parameters.

This module provides a suite of common validation functions for checking
numeric ranges, probabilities, date ranges, and other input parameters. Using
these helpers ensures consistent validation logic and error messaging across
the application.

Key Functions:
- `validate_positive_int`: Checks if an integer is positive.
- `validate_probability`: Ensures a value is between 0 and 1.
- `validate_date_range`: Validates the logic of a start/end date pair.
- `validate_numeric_range`: Checks if a number falls within a min/max range.

Usage Example:
    >>> from portfolio_management.utils.validation import (
    ...     validate_numeric_range,
    ...     validate_probability
    ... )
    >>>
    >>> # Validate a portfolio weight
    >>> try:
    ...     validate_numeric_range(1.2, "weight", min_value=0.0, max_value=1.0)
    ... except ValueError as e:
    ...     print(e)
    weight must be <= 1.0, got 1.2
"""

from __future__ import annotations

import datetime


def validate_positive_int(value: int, name: str, allow_zero: bool = False) -> None:
    """Validate that an integer value is positive (or optionally non-negative).

    This check is useful for parameters that represent counts, lookback
    periods, or other quantities that cannot be negative.

    Args:
        value: The integer value to validate.
        name: The name of the parameter being validated, used in error messages.
        allow_zero: If `True`, zero is considered a valid value. If `False`
                    (default), the value must be strictly positive (>= 1).

    Raises:
        ValueError: If the value is not a valid positive (or non-negative)
                    integer as per the `allow_zero` flag.
        TypeError: If the input `value` is not an integer.

    Example:
        >>> # Must be strictly positive
        >>> try:
        ...     validate_positive_int(0, "lookback_days")
        ... except ValueError as e:
        ...     print(e)
        lookback_days must be >= 1, got 0
    """
    if not isinstance(value, int):
        raise TypeError(f"{name} must be an integer, got {type(value).__name__}")
    if allow_zero:
        if value < 0:
            raise ValueError(f"{name} must be >= 0, got {value}")
    else:
        if value < 1:
            raise ValueError(f"{name} must be >= 1, got {value}")


def validate_probability(value: float, name: str) -> None:
    """Validate that a float value is in the [0, 1] range, inclusive.

    This is used to check parameters that represent probabilities,
    proportions, or percentages, such as turnover constraints or confidence
    scores.

    Args:
        value: The float value to validate.
        name: The name of the parameter for clear error messages.

    Raises:
        ValueError: If the `value` is not between 0.0 and 1.0.
        TypeError: If the `value` is not a float or integer.

    Example:
        >>> try:
        ...     validate_probability(1.5, "max_turnover")
        ... except ValueError as e:
        ...     print(e)
        max_turnover must be in [0, 1], got 1.5
    """
    if not isinstance(value, (float, int)):
        raise TypeError(f"{name} must be a number, got {type(value).__name__}")
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be in [0, 1], got {value}")


def validate_date_range(
    start_date: datetime.date | None,
    end_date: datetime.date | None,
    param_name: str = "date range",
) -> None:
    """Validate a date range, ensuring consistency and logical order.

    This validator performs two checks:
    1.  Ensures that if one of `start_date` or `end_date` is specified, the
        other must also be specified. A half-specified range is invalid.
    2.  If both are specified, it ensures `start_date` is not after `end_date`.

    Args:
        start_date: The start date of the range, or `None`.
        end_date: The end date of the range, or `None`.
        param_name: The name of the date range parameter for error messages.

    Raises:
        ValueError: If only one of `start_date` or `end_date` is provided,
                    or if `start_date > end_date`.

    Example:
        >>> from datetime import date
        >>>
        >>> # Incomplete range
        >>> try:
        ...     validate_date_range(date(2023, 1, 1), None)
        ... except ValueError as e:
        ...     print(e)
        Both start and end dates must be specified for date range
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

    This function can handle open-ended ranges (by setting `min_value` or
    `max_value` to `None`) and can configure inclusive or exclusive
    boundaries.

    Args:
        value: The numeric value to validate.
        name: The name of the parameter for error messages.
        min_value: The minimum allowed value. If `None`, there is no lower bound.
        max_value: The maximum allowed value. If `None`, there is no upper bound.
        min_inclusive: If `True` (default), the minimum bound is inclusive (`>=`).
                       If `False`, it is exclusive (`>`).
        max_inclusive: If `True` (default), the maximum bound is inclusive (`<=`).
                       If `False`, it is exclusive (`<`).

    Raises:
        ValueError: If the `value` is outside the specified range.
        TypeError: If `value` is not a number.

    Example:
        >>> # Exclusive range check
        >>> try:
        ...     validate_numeric_range(1.0, "score", min_value=0.0, max_value=1.0, max_inclusive=False)
        ... except ValueError as e:
        ...     print(e)
        score must be < 1.0, got 1.0
    """
    if not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a number, got {type(value).__name__}")
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
