"""Protocol definitions for common interfaces.

This module defines protocols (structural interfaces) for common patterns
used throughout the portfolio management toolkit. Protocols allow for
better type safety without requiring explicit inheritance.

Protocols:
    - CacheProtocol: Interface for caching factor scores and eligibility
    - DataLoaderProtocol: Interface for data loading operations
    - FactorProtocol: Interface for factor computation

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    import datetime

    import pandas as pd


class CacheProtocol(Protocol):
    """Protocol for factor and eligibility caching.

    Defines the interface that cache implementations must provide for
    storing and retrieving computed factor scores and eligibility masks.
    """

    def get(
        self,
        dataset: pd.DataFrame,
        config: dict[str, Any],
        start_date: datetime.date,
        end_date: datetime.date,
    ) -> pd.Series | pd.DataFrame | None:
        """Retrieve cached result if available and valid.

        Args:
            dataset: Input data used for computation
            config: Configuration parameters
            start_date: Start date for the computation
            end_date: End date for the computation

        Returns:
            Cached result if available and valid, None otherwise

        """
        ...

    def put(
        self,
        dataset: pd.DataFrame,
        config: dict[str, Any],
        start_date: datetime.date,
        end_date: datetime.date,
        result: pd.Series | pd.DataFrame,
    ) -> None:
        """Store computed result in cache.

        Args:
            dataset: Input data used for computation
            config: Configuration parameters
            start_date: Start date for the computation
            end_date: End date for the computation
            result: Computed result to cache

        """
        ...


class DataLoaderProtocol(Protocol):
    """Protocol for data loading operations.

    Defines the interface for loading price or returns data from
    various sources (CSV, Parquet, databases, etc.).
    """

    def load_prices(self, symbols: list[str], start_date: datetime.date, end_date: datetime.date) -> pd.DataFrame:
        """Load price data for specified symbols and date range.

        Args:
            symbols: List of ticker symbols to load
            start_date: Start date for data
            end_date: End date for data

        Returns:
            DataFrame with prices (index=dates, columns=tickers)

        """
        ...

    def load_returns(self, symbols: list[str], start_date: datetime.date, end_date: datetime.date) -> pd.DataFrame:
        """Load returns data for specified symbols and date range.

        Args:
            symbols: List of ticker symbols to load
            start_date: Start date for data
            end_date: End date for data

        Returns:
            DataFrame with returns (index=dates, columns=tickers)

        """
        ...


class FactorProtocol(Protocol):
    """Protocol for factor computation.

    Defines the interface for computing factor scores (momentum,
    volatility, value, quality, etc.) from returns or other data.
    """

    def compute_scores(
        self,
        returns: pd.DataFrame,
        date: datetime.date,
        lookback: int,
    ) -> pd.Series:
        """Compute factor scores for assets at a given date.

        Args:
            returns: Historical returns data
            date: Date to compute scores for (uses data up to this date)
            lookback: Number of periods to look back

        Returns:
            Series of factor scores (index=tickers, higher is better)

        """
        ...

    @property
    def name(self) -> str:
        """Return the factor name (e.g., 'momentum', 'low_vol').

        Returns:
            Factor name string

        """
        ...


class EligibilityProtocol(Protocol):
    """Protocol for eligibility computation.

    Defines the interface for determining which assets are eligible
    for selection at each rebalance date (point-in-time filtering).
    """

    def compute_eligibility(
        self,
        returns: pd.DataFrame,
        date: datetime.date,
        min_history: int,
    ) -> pd.Series:
        """Compute eligibility mask for assets at a given date.

        Args:
            returns: Historical returns data
            date: Date to compute eligibility for
            min_history: Minimum history required

        Returns:
            Boolean Series indicating eligible assets (True = eligible)

        """
        ...
