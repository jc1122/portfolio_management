"""Date handling utilities for consistent date operations.

This module provides common date conversion, filtering, and validation
operations used across the portfolio management toolkit. It aims to reduce
duplication and ensure consistency when working with time-series data.

Key Functions:
- `date_to_timestamp`: Converts various date-like objects to a pandas Timestamp.
- `timestamp_to_date`: Converts a pandas Timestamp back to a `datetime.date`.
- `filter_data_by_date_range`: Filters a DataFrame with a DatetimeIndex.
- `validate_date_order`: Ensures that a start date is not after an end date.

Usage Example:
    >>> import pandas as pd
    >>> from datetime import date
    >>> from portfolio_management.utils.date_utils import (
    ...     filter_data_by_date_range,
    ...     validate_date_order
    ... )
    >>>
    >>> # Create a sample DataFrame
    >>> df = pd.DataFrame(
    ...     {"value": range(5)},
    ...     index=pd.to_datetime([
    ...         "2023-01-01", "2023-01-02", "2023-01-03", "2023-01-04", "2023-01-05"
    ...     ])
    ... )
    >>>
    >>> # Filter the data for a specific date range
    >>> filtered_df = filter_data_by_date_range(
    ...     df,
    ...     start_date="2023-01-02",
    ...     end_date="2023-01-04"
    ... )
    >>> print(filtered_df.index.date)
    [datetime.date(2023, 1, 2) datetime.date(2023, 1, 3)
     datetime.date(2023, 1, 4)]
"""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    pass


def date_to_timestamp(date: datetime.date | pd.Timestamp | str) -> pd.Timestamp:
    """Convert a date-like object to a pandas Timestamp.

    This function standardizes various date representations (string,
    `datetime.date`, `pd.Timestamp`) into a consistent `pd.Timestamp` type,
    which is used throughout the application for date calculations.

    Args:
        date: The date-like object to convert. It can be a `datetime.date`,
              `pd.Timestamp`, or a date string in a recognizable format.

    Returns:
        The pandas Timestamp representation of the input date.

    Raises:
        ValueError: If the input `date` cannot be parsed into a valid
                    Timestamp.

    Example:
        >>> from datetime import date
        >>>
        >>> # From a datetime.date object
        >>> d = date(2023, 1, 1)
        >>> ts = date_to_timestamp(d)
        >>> print(ts)
        2023-01-01 00:00:00
    """
    if isinstance(date, pd.Timestamp):
        return date
    if isinstance(date, datetime.date):
        return pd.Timestamp(date)
    try:
        return pd.Timestamp(date)
    except Exception as e:
        raise ValueError(f"Cannot convert {date} to Timestamp: {e}") from e


def timestamp_to_date(timestamp: pd.Timestamp) -> datetime.date:
    """Convert a pandas Timestamp to a `datetime.date` object.

    This function truncates the time part of a Timestamp, returning only
    the date portion. It is useful for standardizing dates after
    time-based calculations.

    Args:
        timestamp: The pandas Timestamp to convert.

    Returns:
        A `datetime.date` object representing the date part of the timestamp.

    Example:
        >>> import pandas as pd
        >>>
        >>> # Timestamp with time component
        >>> ts = pd.Timestamp('2023-01-01 15:30:00')
        >>> d = timestamp_to_date(ts)
        >>> print(d)
        2023-01-01
    """
    return timestamp.date()


def filter_data_by_date_range(
    data: pd.DataFrame,
    start_date: datetime.date | pd.Timestamp | str | None = None,
    end_date: datetime.date | pd.Timestamp | str | None = None,
    inclusive: str = "both",
) -> pd.DataFrame:
    """Filter a DataFrame with a DatetimeIndex by a date range.

    This function selects rows from the DataFrame where the index falls
    within the specified `start_date` and `end_date`. It gracefully handles
    open-ended ranges where either `start_date` or `end_date` is `None`.

    Args:
        data: The DataFrame to filter. Must have a `DatetimeIndex`.
        start_date: The start date of the range. If `None`, the range is
                    unbounded at the start.
        end_date: The end date of the range. If `None`, the range is
                  unbounded at the end.
        inclusive: How to handle the boundaries. Can be "both" (default),
                   "left", "right", or "neither".

    Returns:
        A new DataFrame containing only the rows within the specified date range.

    Raises:
        ValueError: If `start_date` is after `end_date` when both are provided.

    Example:
        >>> import pandas as pd
        >>>
        >>> df = pd.DataFrame(
        ...     {"value": range(4)},
        ...     index=pd.to_datetime(["2023-01-01", "2023-01-02", "2023-01-03", "2023-01-04"])
        ... )
        >>>
        >>> # Non-inclusive filtering
        >>> filtered = filter_data_by_date_range(
        ...     df, "2023-01-02", "2023-01-04", inclusive="neither"
        ... )
        >>> print(filtered.index.date)
        [datetime.date(2023, 1, 3)]
    """
    if start_date is not None and end_date is not None:
        validate_date_order(start_date, end_date)

    result = data.copy()

    if start_date is not None:
        start_ts = date_to_timestamp(start_date)
        if inclusive in ("both", "left"):
            result = result[result.index >= start_ts]
        else:
            result = result[result.index > start_ts]

    if end_date is not None:
        end_ts = date_to_timestamp(end_date)
        if inclusive in ("both", "right"):
            result = result[result.index <= end_ts]
        else:
            result = result[result.index < end_ts]

    return result


def validate_date_order(
    start_date: datetime.date | pd.Timestamp | str,
    end_date: datetime.date | pd.Timestamp | str,
    allow_equal: bool = True,
) -> None:
    """Validate that a start date comes before or on the end date.

    This is a common check to prevent logical errors when defining date
    ranges for queries or calculations.

    Args:
        start_date: The start date of the period.
        end_date: The end date of the period.
        allow_equal: If `True` (default), the start and end dates can be
                     the same. If `False`, the start date must be strictly
                     before the end date.

    Raises:
        ValueError: If `start_date` is after `end_date`, or if they are
                    equal when `allow_equal` is `False`.

    Example:
        >>> from datetime import date
        >>>
        >>> # Invalid order
        >>> try:
        ...     validate_date_order(date(2023, 12, 31), date(2023, 1, 1))
        ... except ValueError as e:
        ...     print(e)
        start_date (2023-12-31) must be before end_date (2023-01-01)
    """
    start_ts = date_to_timestamp(start_date)
    end_ts = date_to_timestamp(end_date)

    if start_ts > end_ts:
        raise ValueError(
            f"start_date ({start_ts.date()}) must be before end_date ({end_ts.date()})"
        )

    if not allow_equal and start_ts == end_ts:
        raise ValueError(
            f"start_date ({start_ts.date()}) must be strictly before end_date ({end_ts.date()})"
        )
