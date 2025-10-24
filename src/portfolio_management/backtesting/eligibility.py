"""Point-in-time (PIT) eligibility computation for backtesting.

This module provides functions to compute eligibility masks that ensure
no future information is used when selecting assets for portfolio construction.
Eligibility is based on data availability up to each rebalance date.

Supports optional caching to avoid recomputing eligibility across backtest runs.
"""

from __future__ import annotations

import datetime

import pandas as pd

from portfolio_management.core.protocols import CacheProtocol
from portfolio_management.utils.date_utils import date_to_timestamp


def compute_pit_eligibility(
    returns: pd.DataFrame,
    date: datetime.date,
    min_history_days: int = 252,
    min_price_rows: int = 252,
) -> pd.Series:
    """Compute point-in-time eligibility mask for assets at a given date.

    For each asset, compute:
    - days_since_first_valid: Days from first non-NaN return to the given date
    - rows_count_up_to_t: Count of non-NaN returns up to the given date

    An asset is eligible if:
    - days_since_first_valid >= min_history_days AND
    - rows_count_up_to_t >= min_price_rows

    This ensures we only use data available up to the rebalance date,
    avoiding future information leakage.

    Args:
        returns: Historical returns DataFrame (index=dates, columns=tickers).
            Should include all data up to and including the given date.
        date: The rebalance date to compute eligibility for.
        min_history_days: Minimum days from first valid observation (default: 252 = 1 year).
        min_price_rows: Minimum count of valid observations (default: 252).

    Returns:
        Boolean Series indicating eligibility for each asset (True = eligible).
        Index matches the columns of the returns DataFrame.

    Example:
        >>> returns = pd.DataFrame(...)  # Historical returns
        >>> eligible = compute_pit_eligibility(returns, date(2023, 12, 31))
        >>> eligible_assets = returns.columns[eligible]

    """
    # Filter returns to only include data up to the given date
    # Use date_to_timestamp for consistent date handling
    cutoff_datetime = date_to_timestamp(date)
    historical_data = returns[returns.index <= cutoff_datetime]

    if len(historical_data) == 0:
        # No data available yet - nothing is eligible
        return pd.Series(False, index=returns.columns)

    # For each asset, find first non-NaN observation
    first_valid_idx = historical_data.apply(pd.Series.first_valid_index)

    # Calculate days since first valid observation
    days_since_first = pd.Series(index=returns.columns, dtype=float)
    for ticker in returns.columns:
        first_date = first_valid_idx[ticker]
        if pd.isna(first_date):
            # No valid observations at all
            days_since_first[ticker] = 0
        else:
            # Calculate days between first valid and current date
            days_diff = (cutoff_datetime - date_to_timestamp(first_date)).days
            days_since_first[ticker] = days_diff

    # Count non-NaN observations up to the date
    rows_count = historical_data.notna().sum()

    # Apply eligibility criteria
    eligible = (days_since_first >= min_history_days) & (rows_count >= min_price_rows)

    return eligible


def compute_pit_eligibility_cached(
    returns: pd.DataFrame,
    date: datetime.date,
    min_history_days: int = 252,
    min_price_rows: int = 252,
    cache: CacheProtocol | None = None,
) -> pd.Series:
    """Compute PIT eligibility with optional caching.

    Same as compute_pit_eligibility but supports caching to avoid recomputation.

    Args:
        returns: Historical returns DataFrame
        date: Rebalance date
        min_history_days: Minimum history days requirement
        min_price_rows: Minimum price rows requirement
        cache: Optional cache instance (must implement CacheProtocol)

    Returns:
        Boolean Series indicating eligibility

    """
    # Build cache config
    cache_config = {
        "min_history_days": min_history_days,
        "min_price_rows": min_price_rows,
    }

    # Date range for cache key
    start_date = str(returns.index[0])
    end_date = str(date)

    # Try cache
    if cache is not None:
        cached_eligibility = cache.get_pit_eligibility(
            returns,
            cache_config,
            start_date,
            end_date,
        )
        if cached_eligibility is not None:
            return cached_eligibility

    # Compute
    eligibility = compute_pit_eligibility(
        returns,
        date,
        min_history_days,
        min_price_rows,
    )

    # Cache result
    if cache is not None:
        cache.put_pit_eligibility(
            eligibility,
            returns,
            cache_config,
            start_date,
            end_date,
        )

    return eligibility


def detect_delistings(
    returns: pd.DataFrame,
    current_date: datetime.date,
    lookforward_days: int = 30,
) -> dict[str, datetime.date]:
    """Detect assets that have been delisted or will be delisted soon.

    Identifies assets whose last valid observation is at or before the current date,
    and no future observations exist within lookforward_days.

    Args:
        returns: Historical returns DataFrame (index=dates, columns=tickers).
        current_date: The current date in the backtest.
        lookforward_days: Days to look forward to confirm delisting (default: 30).

    Returns:
        Dictionary mapping ticker to last available date for delisted assets.

    Note:
        This function is used to detect when assets should be liquidated.
        In a true PIT implementation, we would not look forward. However,
        this is a pragmatic approach to handle delistings gracefully during backtesting.

    """
    cutoff_datetime = date_to_timestamp(current_date)
    lookforward_datetime = cutoff_datetime + pd.Timedelta(days=lookforward_days)

    delistings: dict[str, datetime.date] = {}

    for ticker in returns.columns:
        # Get all data for this ticker
        ticker_data = returns[ticker]

        # Find last valid observation
        last_valid_idx = ticker_data.last_valid_index()

        if pd.isna(last_valid_idx):
            # No valid data at all
            continue

        last_valid_date = date_to_timestamp(last_valid_idx)

        # Check if last valid date is at or before current date
        if last_valid_date <= cutoff_datetime:
            # Check if there's any valid data in the lookforward period
            future_data = ticker_data[
                (ticker_data.index > cutoff_datetime)
                & (ticker_data.index <= lookforward_datetime)
            ]

            if future_data.notna().sum() == 0:
                # No future data - asset is delisted
                delistings[ticker] = last_valid_date.date()

    return delistings


def get_asset_history_stats(
    returns: pd.DataFrame,
    date: datetime.date,
) -> pd.DataFrame:
    """Get detailed history statistics for each asset up to a given date.

    Computes comprehensive statistics about data availability for each asset,
    useful for debugging and validation.

    Args:
        returns: Historical returns DataFrame (index=dates, columns=tickers).
        date: The date to compute statistics up to.

    Returns:
        DataFrame with columns:
        - ticker: Asset ticker
        - first_valid_date: Date of first non-NaN observation
        - last_valid_date: Date of last non-NaN observation
        - days_since_first: Days from first valid to given date
        - total_rows: Count of non-NaN observations
        - coverage_pct: Percentage of days with valid data

    """
    cutoff_datetime = date_to_timestamp(date)
    historical_data = returns[returns.index <= cutoff_datetime]

    if len(historical_data) == 0:
        return pd.DataFrame(
            columns=[
                "ticker",
                "first_valid_date",
                "last_valid_date",
                "days_since_first",
                "total_rows",
                "coverage_pct",
            ],
        )

    stats = []

    for ticker in returns.columns:
        ticker_data = historical_data[ticker]

        first_valid = ticker_data.first_valid_index()
        last_valid = ticker_data.last_valid_index()

        if pd.isna(first_valid):
            stats.append(
                {
                    "ticker": ticker,
                    "first_valid_date": None,
                    "last_valid_date": None,
                    "days_since_first": 0,
                    "total_rows": 0,
                    "coverage_pct": 0.0,
                },
            )
        else:
            first_valid_ts = date_to_timestamp(first_valid)
            last_valid_ts = date_to_timestamp(last_valid)

            days_since = (cutoff_datetime - first_valid_ts).days
            total_rows = ticker_data.notna().sum()

            # Calculate coverage percentage
            total_days = (cutoff_datetime - first_valid_ts).days + 1
            coverage_pct = (total_rows / total_days * 100) if total_days > 0 else 0.0

            stats.append(
                {
                    "ticker": ticker,
                    "first_valid_date": first_valid_ts.date(),
                    "last_valid_date": last_valid_ts.date(),
                    "days_since_first": days_since,
                    "total_rows": total_rows,
                    "coverage_pct": coverage_pct,
                },
            )

    return pd.DataFrame(stats)
