"""Common types, protocols, and type aliases used across packages.

This module defines common interfaces and type aliases used throughout
the portfolio management toolkit for better type safety and consistency.

Type Aliases:
    - SymbolType: Represents stock ticker symbols
    - DateType: Flexible date representation
    - DateLike: More specific date-like type for conversions
    - PriceDataFrame: DataFrame with expected price/volume columns
    - ReturnsDataFrame: DataFrame with returns data
    - FactorScores: Series with factor scores for assets

Protocols:
    - IDataLoader: Interface for data loading operations
    - IAssetFilter: Interface for asset filtering operations
    - IPortfolioStrategy: Interface for portfolio construction strategies
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    import datetime

    import pandas as pd

# Type aliases for improved readability and consistency
SymbolType = str
DateType = "date | str"
DateLike = "datetime.date | pd.Timestamp | str"
PriceDataFrame = "pd.DataFrame"  # DataFrame with specific columns expected
ReturnsDataFrame = "pd.DataFrame"  # DataFrame with returns (index=dates, columns=tickers)
FactorScores = "pd.Series"  # Series with factor scores (index=tickers)


class IDataLoader(Protocol):
    """Protocol for data loading operations.

    Implementers must provide a load method that reads data from a path
    and returns it as a pandas DataFrame.
    """

    def load(self, path: str) -> pd.DataFrame:
        """Load data from the specified path.

        Args:
            path: Path to the data file to load

        Returns:
            DataFrame containing the loaded data

        """
        ...


class IAssetFilter(Protocol):
    """Protocol for asset filtering operations.

    Implementers must provide a filter method that applies criteria
    to a list of assets and returns the filtered subset.
    """

    def filter(self, assets: list, criteria: object) -> list:
        """Filter assets based on specified criteria.

        Args:
            assets: List of assets to filter
            criteria: Filtering criteria to apply

        Returns:
            Filtered list of assets meeting the criteria

        """
        ...


class IPortfolioStrategy(Protocol):
    """Protocol for portfolio construction strategies.

    Implementers must provide a construct method that takes historical
    returns and produces portfolio weights.
    """

    def construct(self, returns: pd.DataFrame) -> pd.Series:
        """Construct portfolio weights from return data.

        Args:
            returns: DataFrame of historical returns for assets

        Returns:
            Series of portfolio weights (must sum to 1.0)

        """
        ...
