"""Macroeconomic signal provider for loading time series from Stooq."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from portfolio_management.core.exceptions import (
    DataDirectoryNotFoundError,
    DataValidationError,
)
from portfolio_management.macro.models import MacroSeries

LOGGER = logging.getLogger(__name__)


class MacroSignalProvider:
    """Load macroeconomic time series from local Stooq data directories.

    This class provides methods to locate and load macro series (e.g., GDP,
    PMI, yields) from structured Stooq data directories. It supports both
    individual series loading and batch operations.

    The provider currently locates series files and returns metadata about
    them. Future versions may add data loading, transformation, and regime
    signal generation.

    Attributes:
        data_dir: Path to the Stooq data directory root.

    Example:
        >>> from portfolio_management.macro import MacroSignalProvider
        >>> provider = MacroSignalProvider(Path("data/stooq"))
        >>> # Locate series (returns paths/metadata, doesn't load data yet)
        >>> series = provider.locate_series(["gdp.us", "pmi.us"])
        >>> print(f"Found {len(series)} series")
        >>> # Load data for a specific date range
        >>> data = provider.load_series_data("gdp.us", "2020-01-01", "2025-10-23")

    """

    def __init__(self, data_dir: Path | str) -> None:
        """Initialize the MacroSignalProvider.

        Args:
            data_dir: Path to the Stooq data directory root.

        Raises:
            DataDirectoryNotFoundError: If data_dir doesn't exist.

        Example:
            >>> provider = MacroSignalProvider("data/stooq")

        """
        self.data_dir = Path(data_dir)
        if not self.data_dir.exists():
            raise DataDirectoryNotFoundError(self.data_dir)

        LOGGER.info("Initialized MacroSignalProvider with data_dir=%s", self.data_dir)

    def locate_series(self, ticker: str) -> MacroSeries | None:
        """Locate a macro series file in the Stooq data directory.

        This method searches for a series file by ticker, following Stooq's
        directory structure. It returns metadata about the series if found.

        Args:
            ticker: Ticker symbol for the macro series (e.g., "gdp.us").

        Returns:
            MacroSeries object with metadata if found, None otherwise.

        Example:
            >>> provider = MacroSignalProvider("data/stooq")
            >>> series = provider.locate_series("gdp.us")
            >>> if series:
            ...     print(f"Found series at {series.rel_path}")

        """
        # Try multiple potential paths for the ticker
        # Stooq structure could be: data/daily/{region}/{category}/{ticker}.txt
        potential_paths = self._generate_search_paths(ticker)

        for potential_path in potential_paths:
            full_path = self.data_dir / potential_path
            if full_path.exists():
                LOGGER.debug("Located series %s at %s", ticker, potential_path)
                # Parse metadata from path
                region, category = self._parse_path_metadata(potential_path)
                # For now, return basic metadata without loading the file
                # In production, we might want to read first/last dates from the file
                return MacroSeries(
                    ticker=ticker,
                    rel_path=potential_path,
                    start_date="",  # To be filled when data is loaded
                    end_date="",  # To be filled when data is loaded
                    region=region,
                    category=category,
                )

        LOGGER.warning("Could not locate series for ticker: %s", ticker)
        return None

    def locate_multiple_series(self, tickers: list[str]) -> dict[str, MacroSeries]:
        """Locate multiple macro series files.

        Args:
            tickers: List of ticker symbols to locate.

        Returns:
            Dictionary mapping found tickers to their MacroSeries metadata.
            Missing tickers are excluded from the result.

        Example:
            >>> provider = MacroSignalProvider("data/stooq")
            >>> series = provider.locate_multiple_series(["gdp.us", "pmi.us"])
            >>> print(f"Found {len(series)} out of 2 requested series")

        """
        result = {}
        for ticker in tickers:
            series = self.locate_series(ticker)
            if series is not None:
                result[ticker] = series
            else:
                LOGGER.info("Series not found: %s", ticker)

        LOGGER.info(
            "Located %d out of %d requested series",
            len(result),
            len(tickers),
        )
        return result

    def load_series_data(
        self,
        ticker: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> pd.DataFrame | None:
        """Load data for a macro series from its file.

        Args:
            ticker: Ticker symbol for the macro series.
            start_date: Optional start date filter (ISO format YYYY-MM-DD).
            end_date: Optional end date filter (ISO format YYYY-MM-DD).

        Returns:
            DataFrame with the series data if found, None otherwise.
            DataFrame has 'date' as index and columns for price/value data.

        Raises:
            DataValidationError: If the file exists but can't be read.

        Example:
            >>> provider = MacroSignalProvider("data/stooq")
            >>> df = provider.load_series_data("gdp.us", "2020-01-01", "2025-10-23")
            >>> if df is not None:
            ...     print(f"Loaded {len(df)} rows")

        """
        # First locate the series
        series = self.locate_series(ticker)
        if series is None:
            return None

        full_path = self.data_dir / series.rel_path

        try:
            # Load the CSV file (assuming Stooq format)
            # Typical Stooq columns: ticker,per,date,time,open,high,low,close,volume,openint
            df = pd.read_csv(full_path, parse_dates=["date"])

            # Filter by date range if specified
            if start_date:
                df = df[df["date"] >= pd.to_datetime(start_date)]
            if end_date:
                df = df[df["date"] <= pd.to_datetime(end_date)]

            # Set date as index
            df = df.set_index("date").sort_index()

            LOGGER.debug(
                "Loaded %d rows for series %s (date range: %s to %s)",
                len(df),
                ticker,
                df.index[0] if len(df) > 0 else "N/A",
                df.index[-1] if len(df) > 0 else "N/A",
            )

            return df

        except Exception as e:
            raise DataValidationError(
                f"Failed to load series {ticker} from {full_path}: {e}",
            ) from e

    def _generate_search_paths(self, ticker: str) -> list[str]:
        """Generate potential file paths for a ticker.

        Args:
            ticker: Ticker symbol (e.g., "gdp.us", "pmi.us").

        Returns:
            List of potential relative paths to search.

        """
        # Extract region from ticker (e.g., "gdp.us" -> "us")
        parts = ticker.lower().split(".")
        if len(parts) >= 2:
            base_ticker = parts[0]
            region = parts[1]
        else:
            base_ticker = ticker.lower()
            region = "us"  # Default to US if no region specified

        # Generate potential paths following Stooq structure
        paths = [
            f"data/daily/{region}/economic/{base_ticker}.txt",
            f"data/daily/{region}/indicators/{base_ticker}.txt",
            f"data/daily/{region}/macro/{base_ticker}.txt",
            f"data/daily/{region}/{base_ticker}.txt",
            f"{region}/economic/{base_ticker}.txt",
            f"{region}/indicators/{base_ticker}.txt",
            f"{region}/{base_ticker}.txt",
            f"{base_ticker}.txt",
        ]

        return paths

    def _parse_path_metadata(self, rel_path: str) -> tuple[str, str]:
        """Parse region and category from a relative path.

        Args:
            rel_path: Relative path to the series file.

        Returns:
            Tuple of (region, category) extracted from path.

        Example:
            >>> provider = MacroSignalProvider("data/stooq")
            >>> region, category = provider._parse_path_metadata(
            ...     "data/daily/us/economic/gdp.txt"
            ... )
            >>> print(region, category)
            us economic

        """
        parts = Path(rel_path).parts
        region = ""
        category = ""

        # Try to extract region and category from path structure
        if "daily" in parts:
            idx = parts.index("daily")
            if idx + 1 < len(parts):
                region = parts[idx + 1]
            if idx + 2 < len(parts) - 1:  # -1 to exclude filename
                category = parts[idx + 2]
        elif len(parts) >= 2:
            region = parts[0]
            if len(parts) >= 3:
                category = parts[1]

        return region, category
