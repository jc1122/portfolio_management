"""Utility modules for common operations across the portfolio management toolkit.

This package contains helper functions for common, reusable tasks that are not
specific to a single domain. These include date manipulation, data validation,
and other general-purpose utilities.

Key Functions:
- `date_utils`: Provides functions for handling dates, timestamps, and
  filtering time-series data.
- `validation`: Offers a suite of functions to validate inputs like date
  ranges, numeric values, and configuration parameters.

Usage Example:
    >>> from portfolio_management.utils import validate_date_range, date_to_timestamp
    >>> from datetime import date
    >>>
    >>> # Validate a date range
    >>> try:
    ...     validate_date_order(date(2023, 12, 31), date(2023, 1, 1))
    ... except ValueError as e:
    ...     print(e)
    start_date (2023-12-31) must be before end_date (2023-01-01)
    >>>
    >>> # Convert a date string to a timestamp
    >>> ts = date_to_timestamp("2023-01-01 12:00:00")
    >>> print(ts)
    2023-01-01 12:00:00

"""

from portfolio_management.utils.date_utils import (
    date_to_timestamp,
    filter_data_by_date_range,
    timestamp_to_date,
    validate_date_order,
)
from portfolio_management.utils.validation import (
    validate_date_range,
    validate_numeric_range,
    validate_positive_int,
    validate_probability,
)

__all__ = [
    # Date utilities
    "date_to_timestamp",
    "timestamp_to_date",
    "filter_data_by_date_range",
    "validate_date_order",
    # Validation utilities
    "validate_positive_int",
    "validate_probability",
    "validate_date_range",
    "validate_numeric_range",
]
