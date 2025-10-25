"""Common types, protocols, and type aliases for the toolkit.

This module provides a centralized location for shared type definitions,
ensuring consistency and improving static analysis across the application.
It includes simple type aliases for domain-specific concepts like symbols
and dates, as well as `typing.Protocol` definitions for key architectural
components.

Using these shared types helps create a common language for data structures
and interfaces, making the system easier to understand, maintain, and extend.

Type Aliases:
    SymbolType: Represents a unique stock ticker symbol (e.g., "AAPL.US").
    DateType: Represents a date, accepting `datetime.date`, `pd.Timestamp`,
        or a string in "YYYY-MM-DD" format.
    DateLike: A more specific alias for objects that can be reliably
        converted to a `datetime.date`.
    PriceDataFrame: A pandas DataFrame expected to contain pricing data,
        typically with columns like 'open', 'high', 'low', 'close', 'volume'.
    ReturnsDataFrame: A pandas DataFrame where the index represents dates
        and columns represent asset tickers, with values being periodic returns.
    FactorScores: A pandas Series where the index contains asset tickers
        and the values are the computed factor scores for those assets.

Protocols:
    IDataLoader: Defines the interface for data loading classes.
    IAssetFilter: Defines the interface for asset filtering logic.
    IPortfolioStrategy: Defines the interface for portfolio construction strategies.

Example:
    Using type aliases and implementing a protocol.

    >>> import pandas as pd
    >>> from datetime import date
    >>> from portfolio_management.core.types import SymbolType, DateLike, IDataLoader
    >>>
    >>> def get_last_trading_day(for_date: DateLike) -> date:
    ...     # In a real implementation, this would handle weekends and holidays
    ...     if isinstance(for_date, str):
    ...         return date.fromisoformat(for_date)
    ...     return for_date
    >>>
    >>> class SimpleCSVLoader(IDataLoader):
    ...     def load(self, path: str) -> pd.DataFrame:
    ...         # A simplified implementation of the IDataLoader protocol
    ...         print(f"Loading data from {path}...")
    ...         data = {'price': [100, 101, 102]}
    ...         return pd.DataFrame(data)
    ...
    >>> my_loader = SimpleCSVLoader()
    >>> df = my_loader.load("my_data.csv")
    Loading data from my_data.csv...
    >>> print(df.iloc[0]['price'])
    100
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    import datetime

    import pandas as pd

# Type aliases for improved readability and consistency
SymbolType = str
"""A type alias for a string representing a unique asset symbol, e.g., "AAPL.US"."""

DateType = "date | str"
"""A type alias for a flexible date representation, accepting standard date/datetime
objects or ISO-formatted strings."""

DateLike = "datetime.date | pd.Timestamp | str"
"""A more specific type alias for objects that can be reliably converted to a date,
often used in function signatures for flexibility."""

PriceDataFrame = "pd.DataFrame"
"""A pandas DataFrame containing time-series price data. Expected columns often
include 'open', 'high', 'low', 'close', and 'volume'."""

ReturnsDataFrame = "pd.DataFrame"
"""A pandas DataFrame where the index consists of dates and columns are asset symbols.
The values represent the periodic returns of each asset."""

FactorScores = "pd.Series"
"""A pandas Series where the index contains asset symbols and the values are the
numeric factor scores for a given date."""


class IDataLoader(Protocol):
    """Protocol for data loading operations.

    This protocol defines a standard interface for classes that load data.
    Implementers must provide a `load` method that takes a path and returns
    a pandas DataFrame. This allows different data sources (e.g., CSV, Parquet,
    database) to be used interchangeably.

    Example:
        >>> import pandas as pd
        >>> class CSVLoader:  # Implicitly implements IDataLoader
        ...     def load(self, path: str) -> pd.DataFrame:
        ...         # In a real implementation, this would read from the path.
        ...         return pd.DataFrame({'asset': ['A', 'B'], 'value': [10, 20]})
        >>>
        >>> def process_data(loader: IDataLoader, file_path: str):
        ...     df = loader.load(file_path)
        ...     print(df.head())
        >>>
        >>> process_data(CSVLoader(), "data.csv")
          asset  value
        0     A     10
        1     B     20
    """

    def load(self, path: str) -> pd.DataFrame:
        """Loads data from the specified path.

        Args:
            path: The path to the data source (e.g., file path, database URL).

        Returns:
            A pandas DataFrame containing the loaded data.
        """
        ...


class IAssetFilter(Protocol):
    """Protocol for asset filtering operations.

    This protocol defines a standard interface for classes that filter a list
    of assets based on specific criteria. This is a key step in defining a
    tradable universe.

    Example:
        >>> class MinimumVolumeFilter:  # Implicitly implements IAssetFilter
        ...     def filter(self, assets: list[str], criteria: dict) -> list[str]:
        ...         min_volume = criteria.get("min_volume", 0)
        ...         # In a real implementation, would check actual volume data.
        ...         return [asset for asset in assets if len(asset) > min_volume]
        >>>
        >>> my_filter = MinimumVolumeFilter()
        >>> assets = ["A", "BB", "CCC", "DDDD"]
        >>> filtered_assets = my_filter.filter(assets, {"min_volume": 2})
        >>> print(filtered_assets)
        ['CCC', 'DDDD']
    """

    def filter(self, assets: list, criteria: object) -> list:
        """Filters a list of assets based on specified criteria.

        Args:
            assets: The list of asset identifiers to filter.
            criteria: An object containing the filtering parameters. The structure
                of this object is specific to the implementing class.

        Returns:
            A filtered list of assets that meet the criteria.
        """
        ...


class IPortfolioStrategy(Protocol):
    """Protocol for portfolio construction strategies.

    This protocol defines a standard interface for classes that generate
    portfolio weights from historical return data. This allows for different
algotithmic strategies (e.g., momentum, equal weight, minimum variance)
    to be used interchangeably within the backtesting engine.

    Example:
        >>> import pandas as pd
        >>> class EqualWeightStrategy:  # Implicitly implements IPortfolioStrategy
        ...     def construct(self, returns: pd.DataFrame) -> pd.Series:
        ...         num_assets = len(returns.columns)
        ...         weights = pd.Series(1 / num_assets, index=returns.columns)
        ...         return weights
        >>>
        >>> returns_data = pd.DataFrame({
        ...     'AAPL': [0.01, 0.02],
        ...     'GOOG': [-0.01, 0.03]
        ... })
        >>> strategy = EqualWeightStrategy()
        >>> weights = strategy.construct(returns_data)
        >>> print(weights)
        AAPL    0.5
        GOOG    0.5
        dtype: float64
    """

    def construct(self, returns: pd.DataFrame) -> pd.Series:
        """Constructs portfolio weights from historical return data.

        Args:
            returns: A DataFrame of historical returns, where columns are asset
                tickers and the index is dates.

        Returns:
            A pandas Series where the index contains the asset tickers and the
            values are their corresponding weights in the portfolio. The weights
            should ideally sum to 1.0.
        """
        ...