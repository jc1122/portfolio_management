"""Macroeconomic signal provider for loading time series from Stooq.

This module provides the `MacroSignalProvider` class, which is responsible for
locating and loading macroeconomic time series data from a local directory
of files downloaded from Stooq.
"""

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
    PMI, yields) from a structured local directory containing data from Stooq.
    It supports locating single or multiple series and loading their data into
    pandas DataFrames.

    Attributes:
        data_dir (Path): The root directory where the Stooq data is stored.

    Data Source:
        This provider expects data files to be in the format provided by
        Stooq (https://stooq.com/) and organized in a searchable directory
        structure.
    """

    def __init__(self, data_dir: Path | str) -> None:
        """Initialize the MacroSignalProvider.

        Args:
            data_dir: The path to the Stooq data directory root.

        Raises:
            DataDirectoryNotFoundError: If the specified `data_dir` does not
                                        exist.
        """
        self.data_dir = Path(data_dir)
        if not self.data_dir.exists():
            raise DataDirectoryNotFoundError(self.data_dir)

        LOGGER.info("Initialized MacroSignalProvider with data_dir=%s", self.data_dir)

    def locate_series(self, ticker: str) -> MacroSeries | None:
        """Locate a macro series file in the Stooq data directory.

        This method searches for a series file by its ticker, following a set
        of predefined potential directory structures common to Stooq data.

        Args:
            ticker: The ticker symbol for the macro series (e.g., "gdp.us").

        Returns:
            A `MacroSeries` object with metadata if the file is found,
            otherwise `None`.
        """
        potential_paths = self._generate_search_paths(ticker)

        for potential_path in potential_paths:
            full_path = self.data_dir / potential_path
            if full_path.exists():
                LOGGER.debug("Located series %s at %s", ticker, potential_path)
                region, category = self._parse_path_metadata(potential_path)
                return MacroSeries(
                    ticker=ticker,
                    rel_path=str(potential_path),
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
            tickers: A list of ticker symbols to locate.

        Returns:
            A dictionary mapping the tickers that were found to their
            `MacroSeries` metadata. Tickers that are not found are excluded.
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

        This method first locates the series file and then loads its contents
        into a pandas DataFrame. It can optionally filter the data by a
        date range.

        Args:
            ticker: The ticker symbol for the macro series.
            start_date: An optional start date to filter the data (inclusive),
                        in "YYYY-MM-DD" format.
            end_date: An optional end date to filter the data (inclusive),
                      in "YYYY-MM-DD" format.

        Returns:
            A pandas DataFrame with the series data, indexed by date, if the
            file is found and valid. Otherwise, returns `None`.

        Raises:
            DataValidationError: If the series file exists but cannot be read
                                 or parsed as a valid CSV.
        """
        series = self.locate_series(ticker)
        if series is None:
            return None

        full_path = self.data_dir / series.rel_path

        try:
            df = pd.read_csv(full_path, parse_dates=["date"])

            if start_date:
                df = df[df["date"] >= pd.to_datetime(start_date)]
            if end_date:
                df = df[df["date"] <= pd.to_datetime(end_date)]

            df = df.set_index("date").sort_index()

            LOGGER.debug(
                "Loaded %d rows for series %s (date range: %s to %s)",
                len(df),
                ticker,
                df.index[0].date() if not df.empty else "N/A",
                df.index[-1].date() if not df.empty else "N/A",
            )

            return df

        except Exception as e:
            raise DataValidationError(
                f"Failed to load series {ticker} from {full_path}: {e}",
            ) from e

    def _generate_search_paths(self, ticker: str) -> list[str]:
        """Generate potential file paths for a given ticker.

        This helper method constructs a list of likely file paths based on
        common Stooq directory structures.

        Args:
            ticker: The ticker symbol (e.g., "gdp.us").

        Returns:
            A list of potential relative file paths to search for.
        """
        parts = ticker.lower().split(".")
        if len(parts) >= 2:
            base_ticker = parts[0]
            region = parts[1]
        else:
            base_ticker = ticker.lower()
            region = "us"  # Default to US if no region specified

        return [
            f"data/daily/{region}/economic/{base_ticker}.txt",
            f"data/daily/{region}/indicators/{base_ticker}.txt",
            f"data/daily/{region}/macro/{base_ticker}.txt",
            f"data/daily/{region}/{base_ticker}.txt",
            f"{region}/economic/{base_ticker}.txt",
            f"{region}/indicators/{base_ticker}.txt",
            f"{region}/{base_ticker}.txt",
            f"{base_ticker}.txt",
        ]

    def _parse_path_metadata(self, rel_path: str) -> tuple[str, str]:
        """Parse the region and category from a relative file path.

        Args:
            rel_path: The relative path to the series file.

        Returns:
            A tuple containing the extracted region and category as strings.

        Example:
            >>> provider = MacroSignalProvider("data/stooq")
            >>> region, category = provider._parse_path_metadata(
            ...     "data/daily/us/economic/gdp.txt"
            ... )
            >>> print(f"Region: {region}, Category: {category}")
            Region: us, Category: economic
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
