"""Date handling utilities for consistent date operations.

This module provides common date conversion and filtering operations
used across the portfolio management toolkit to reduce duplication
and ensure consistency.

Functions:
    date_to_timestamp: Convert date to pandas Timestamp
    timestamp_to_date: Convert pandas Timestamp to date
    filter_data_by_date_range: Filter DataFrame by date range
    validate_date_order: Validate that start date is before end date

"""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from portfolio_management.core.types import DateLike


def date_to_timestamp(date: datetime.date | pd.Timestamp | str) -> pd.Timestamp:
    """Convert a date-like object to pandas Timestamp.

    Args:
        date: A datetime.date, pandas Timestamp, or date string

    Returns:
        pandas Timestamp representation of the date

    Raises:
        ValueError: If date cannot be converted

    Example:
        >>> from datetime import date
        >>> ts = date_to_timestamp(date(2023, 1, 1))
        >>> isinstance(ts, pd.Timestamp)
        True

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
    """Convert pandas Timestamp to datetime.date.

    Args:
        timestamp: pandas Timestamp to convert

    Returns:
        datetime.date representation

    Example:
        >>> import pandas as pd
        >>> from datetime import date
        >>> ts = pd.Timestamp('2023-01-01')
        >>> d = timestamp_to_date(ts)
        >>> d == date(2023, 1, 1)
        True

    """
    return timestamp.date()


def filter_data_by_date_range(
    data: pd.DataFrame,
    start_date: datetime.date | pd.Timestamp | str | None = None,
    end_date: datetime.date | pd.Timestamp | str | None = None,
    inclusive: str = "both",
) -> pd.DataFrame:
    """Filter DataFrame by date range.

    Filters rows where the index (assumed to be dates) falls within
    the specified range. Handles None values for open-ended ranges.

    Args:
        data: DataFrame with DatetimeIndex
        start_date: Start date (None for no lower bound)
        end_date: End date (None for no upper bound)
        inclusive: Whether to include boundaries ("left", "right", "both", "neither")

    Returns:
        Filtered DataFrame

    Raises:
        ValueError: If start_date > end_date when both are provided

    Example:
        >>> import pandas as pd
        >>> from datetime import date
        >>> df = pd.DataFrame(
        ...     {"value": [1, 2, 3]},
        ...     index=pd.date_range("2023-01-01", periods=3)
        ... )
        >>> filtered = filter_data_by_date_range(df, end_date=date(2023, 1, 2))
        >>> len(filtered)
        2

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
    """Validate that start date comes before (or equals) end date.

    Args:
        start_date: Start date
        end_date: End date
        allow_equal: Whether start_date == end_date is valid

    Raises:
        ValueError: If start_date > end_date, or if equal when not allowed

    Example:
        >>> from datetime import date
        >>> validate_date_order(date(2023, 1, 1), date(2023, 12, 31))
        >>> # No exception raised
        >>>
        >>> validate_date_order(date(2023, 12, 31), date(2023, 1, 1))
        Traceback (most recent call last):
            ...
        ValueError: start_date (2023-12-31) must be before end_date (2023-01-01)

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
