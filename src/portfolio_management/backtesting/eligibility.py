"""Point-in-time (PIT) eligibility computation for backtesting.

This module provides functions to determine which assets are eligible for
inclusion in a portfolio at a specific point in time during a backtest. This
is critical for preventing lookahead bias, where information from the future
is accidentally used to make decisions in the past.

The core function, `compute_pit_eligibility`, creates a filter based on data
availability, ensuring that an asset has a sufficient history of prices before
it can be considered for trading.

Key Functions:
    - compute_pit_eligibility: Determines asset eligibility based on data history.
    - compute_pit_eligibility_cached: A cached version for performance.
    - detect_delistings: Identifies assets that are no longer trading.
    - get_asset_history_stats: Provides detailed data availability stats for debugging.

Usage Example:
    >>> import pandas as pd
    >>> import numpy as np
    >>> from datetime import date
    >>> from portfolio_management.backtesting.eligibility import compute_pit_eligibility
    >>>
    >>> # Create dummy returns data
    >>> dates = pd.to_datetime(pd.date_range(start='2022-01-01', periods=300))
    >>> returns_data = {
    ...     'AAPL': [0.01] * 300,  # Full history
    ...     'NEW_IPO': [np.nan] * 100 + [0.02] * 200 # Partial history
    ... }
    >>> returns = pd.DataFrame(returns_data, index=dates)
    >>>
    >>> # Check eligibility on a specific date
    >>> rebalance_date = date(2022, 10, 27) # Day 300
    >>> eligibility_mask = compute_pit_eligibility(
    ...     returns,
    ...     rebalance_date,
    ...     min_history_days=252, # Require ~1 year of history
    ...     min_price_rows=252
    ... )
    >>>
    >>> print(eligibility_mask)
    AAPL        True
    NEW_IPO    False
    Name: 0, dtype: bool
"""

from __future__ import annotations

import datetime
import logging
import warnings
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


def compute_pit_eligibility(
    returns: pd.DataFrame,
    date: datetime.date,
    min_history_days: int = 252,
    min_price_rows: int = 252,
) -> pd.Series:
    """Compute a point-in-time eligibility mask for assets at a given date.

    This function prevents lookahead bias by ensuring that only assets with a
    sufficiently long and dense history of data are considered for inclusion in
    the portfolio on a given rebalancing date.

    An asset is considered eligible if it meets two criteria:
    1.  The time since its first valid data point is at least `min_history_days`.
    2.  The number of non-missing data points up to the given `date` is at
        least `min_price_rows`.

    Args:
        returns (pd.DataFrame): A DataFrame of historical returns, with dates as
            the index and asset tickers as columns.
        date (datetime.date): The rebalancing date for which to compute eligibility.
        min_history_days (int): The minimum number of calendar days of history
            required for an asset to be eligible. Defaults to 252.
        min_price_rows (int): The minimum number of non-missing return data points
            required. Defaults to 252.

    Returns:
        pd.Series: A boolean Series where the index is the asset tickers and the
        values indicate eligibility (True if eligible, False otherwise).

    Raises:
        ValueError: If the input `returns` DataFrame is invalid or the `date` is
            outside the data range.
    """
    # Validate inputs
    if returns is None or returns.empty:
        raise ValueError(
            "returns DataFrame is empty or None. "
            "To fix: provide a non-empty DataFrame with returns data. "
            "Expected format: DataFrame with dates as index, assets as columns."
        )

    if not isinstance(returns, pd.DataFrame):
        raise ValueError(
            f"returns must be a pandas DataFrame, got {type(returns).__name__}. "
            "To fix: convert your data to a DataFrame. "
            "Example: returns = pd.DataFrame(data, index=dates, columns=tickers)"
        )

    if not isinstance(date, datetime.date):
        raise ValueError(
            f"date must be a datetime.date, got {type(date).__name__}. "
            "To fix: use datetime.date object. "
            "Example: from datetime import date; eligibility_date = date(2023, 12, 31)"
        )

    if min_history_days <= 0:
        raise ValueError(
            f"min_history_days must be > 0, got {min_history_days}. "
            "min_history_days defines the minimum time span required. "
            "Common values: 63 (3 months), 126 (6 months), 252 (1 year). "
            "To fix: use a positive integer. "
            "Example: min_history_days=252"
        )

    if min_price_rows <= 0:
        raise ValueError(
            f"min_price_rows must be > 0, got {min_price_rows}. "
            "min_price_rows defines the minimum number of valid data points. "
            "Common values: 60, 126, 252. "
            "To fix: use a positive integer. "
            "Example: min_price_rows=252"
        )

    # Check if date is within data range
    max_date = returns.index.max()
    if isinstance(max_date, pd.Timestamp):
        max_date = max_date.date()

    if date > max_date:
        raise ValueError(
            f"date ({date}) is after the last available date ({max_date}). "
            "To fix: use a date within your data range. "
            f"Available date range: {returns.index.min()} to {max_date}"
        )

    # Filter returns to only include data up to the given date
    # Convert date to datetime for comparison
    cutoff_datetime = pd.Timestamp(date)
    historical_data = returns[returns.index <= cutoff_datetime]

    if len(historical_data) == 0:
        # No data available yet - nothing is eligible
        logger.warning(
            f"No historical data available up to {date}. "
            "Returning all assets as ineligible."
        )
        return pd.Series(False, index=returns.columns, name=0)

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
            days_diff = (cutoff_datetime - pd.Timestamp(first_date)).days
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
    cache: Any | None = None,
) -> pd.Series:
    """Compute PIT eligibility with optional caching to improve performance.

    This function is a wrapper around `compute_pit_eligibility` that adds a
    caching layer. This can significantly speed up backtests by avoiding
    redundant computations.

    Args:
        returns (pd.DataFrame): Historical returns DataFrame.
        date (datetime.date): The rebalance date.
        min_history_days (int): Minimum history days requirement.
        min_price_rows (int): Minimum price rows requirement.
        cache (Any | None): An optional cache object (e.g., `FactorCache`) that
            supports `get_pit_eligibility` and `put_pit_eligibility` methods.

    Returns:
        pd.Series: A boolean Series indicating eligibility for each asset.
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
    """Detect assets that have been or will soon be delisted.

    This utility identifies assets whose last available data point occurs at or
    before the `current_date`, and for which no new data appears within the
    `lookforward_days` window. It is used to gracefully liquidate positions
    in assets that are no longer trading.

    Note:
        This function involves a small degree of lookahead, which is a
        pragmatic choice for handling delistings in a backtest. In a live
        trading environment, delisting information would be received from a
        data provider.

    Args:
        returns (pd.DataFrame): The entire historical returns DataFrame.
        current_date (datetime.date): The current date in the backtest simulation.
        lookforward_days (int): The number of days to look ahead to confirm that
            an asset has truly been delisted. Defaults to 30.

    Returns:
        dict[str, datetime.date]: A dictionary mapping the ticker of each
        delisted asset to its last known date with valid data.
    """
    cutoff_datetime = pd.Timestamp(current_date)
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

        last_valid_date = pd.Timestamp(last_valid_idx)

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

    This function computes comprehensive statistics about data availability for
    each asset, which is useful for debugging eligibility filters and
    understanding the data quality of the universe.

    Args:
        returns (pd.DataFrame): The historical returns DataFrame.
        date (datetime.date): The date up to which statistics should be computed.

    Returns:
        pd.DataFrame: A DataFrame where each row corresponds to an asset and
        columns include 'ticker', 'first_valid_date', 'last_valid_date',
        'days_since_first', 'total_rows', and 'coverage_pct'.
    """
    cutoff_datetime = pd.Timestamp(date)
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
            first_valid_ts = pd.Timestamp(first_valid)
            last_valid_ts = pd.Timestamp(last_valid)

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