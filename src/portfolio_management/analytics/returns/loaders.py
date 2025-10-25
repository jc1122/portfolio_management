"""Price data loaders for return calculation.

This module provides the `PriceLoader` class, a robust utility for reading
financial price data from CSV files into pandas DataFrames. It is designed
for efficiency and resilience, with features like parallel loading for speed,
a configurable LRU cache to manage memory, and automatic data cleaning.

Key Classes:
    - PriceLoader: Loads, caches, and standardizes price data from files.

Usage Example:
    >>> from pathlib import Path
    >>> from portfolio_management.analytics.returns.loaders import PriceLoader
    >>> from portfolio_management.assets.selection.models import SelectedAsset
    >>>
    >>> # Assume 'tests/data/prices/AAPL.csv' exists
    >>> prices_dir = Path("tests/data/prices")
    >>> assets = [SelectedAsset(symbol="AAPL", exchange="NASDAQ")]
    >>>
    >>> loader = PriceLoader(cache_size=100)
    >>> try:
    ...     price_df = loader.load_multiple_prices(assets, prices_dir)
    ...     if not price_df.empty:
    ...         print(f"Loaded prices for {price_df.shape[1]} asset(s).")
    ...         print(price_df.head())
    ... except FileNotFoundError:
    ...     print("Skipping example: Test data not found.")
    ... except Exception as e:
    ...     print(f"An error occurred: {e}")

"""

from __future__ import annotations

import logging
import os
from collections import OrderedDict, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from collections.abc import Iterable

    from portfolio_management.assets.selection.selection import SelectedAsset

logger = logging.getLogger(__name__)

# Import fast IO utilities
from portfolio_management.data.io.fast_io import Backend, read_csv_fast, select_backend


class PriceLoader:
    """Utilities for reading price files into pandas objects.

    This loader is designed to efficiently read and process numerous price files.
    It includes a bounded LRU cache to prevent unbounded memory growth during
    long-running workflows and uses a thread pool for parallel I/O operations
    to accelerate data loading.

    The loader also performs data validation and cleaning, such as removing
    duplicate timestamps and non-positive price values.

    Attributes:
        max_workers (int | None): Maximum number of concurrent threads for
            parallel loading. If None, a default is calculated based on CPU cores.
        cache_size (int): Maximum number of price series to hold in the LRU cache.
            Set to 0 to disable caching.
        io_backend (Backend): The backend to use for reading CSV files. Options
            include 'pandas', 'polars', and 'pyarrow'. 'auto' selects the
            fastest available option.

    Example:
        >>> from pathlib import Path
        >>> from portfolio_management.analytics.returns.loaders import PriceLoader
        >>> from portfolio_management.assets.selection.models import SelectedAsset
        >>>
        >>> prices_dir = Path("tests/data/prices") # Dummy path
        >>> assets = [
        ...     SelectedAsset(symbol="AAPL"),
        ...     SelectedAsset(symbol="MSFT")
        ... ]
        >>> loader = PriceLoader(max_workers=4, cache_size=500)
        >>> # price_df = loader.load_multiple_prices(assets, prices_dir)
        >>> # if price_df is not None:
        ... #     print(price_df.info())
        >>>
        >>> # Check cache status
        >>> stats = loader.get_cache_stats()
        >>> print(f"Cache entries: {stats['cache_entries']}, "
        ...       f"Cache size: {stats['cache_size']}")
        Cache entries: 0, Cache size: 500
    """

    def __init__(
        self,
        max_workers: int | None = None,
        cache_size: int = 1000,
        io_backend: Backend = "pandas",
    ):
        """Initializes the PriceLoader.

        Args:
            max_workers: Maximum number of concurrent threads for parallel loading.
            cache_size: Maximum number of price series to cache. Default is 1000.
                Set to 0 to disable caching entirely.
            io_backend: IO backend for reading CSV files. Options:
                - 'pandas' (default): Standard pandas CSV reader
                - 'polars': Use polars for faster CSV parsing (requires polars)
                - 'pyarrow': Use pyarrow for faster CSV parsing (requires pyarrow)
                - 'auto': Automatically select fastest available backend
        """
        self.max_workers = max_workers
        self.cache_size = max(0, cache_size)  # Ensure non-negative
        self.io_backend = io_backend
        self._cache: OrderedDict[Path, pd.Series] = OrderedDict()
        self._cache_lock = Lock()

    def load_price_file(self, path: Path) -> pd.Series:
        """Load a single price file into a ``Series`` indexed by date.

        This method reads a CSV file, standardizes its columns, cleans the data
        (handles duplicates, non-positive values), and returns a sorted Series
        of close prices.

        Args:
            path (Path): The path to the price CSV file.

        Returns:
            pd.Series: A Series of close prices, indexed by date. The Series
                will be empty if the file is empty or contains no valid data.

        Raises:
            FileNotFoundError: If the specified path does not exist.
            ValueError: If the CSV file has an unsupported column structure.
        """
        if not path.exists():
            raise FileNotFoundError(path)

        selected_backend = select_backend(self.io_backend)

        if path.suffix.lower() == ".csv" and selected_backend == "pandas":
            df = read_csv_fast(
                path,
                backend=self.io_backend,
                header=0,
                usecols=["date", "close"],
                parse_dates=["date"],
                index_col="date",
            )
        else:
            raw_kwargs = {}
            if selected_backend == "pandas":
                raw_kwargs["header"] = 0
            raw = read_csv_fast(path, backend=self.io_backend, **raw_kwargs)
            df = self._standardize_price_dataframe(raw, path)

        df = df.sort_index()

        if df.index.duplicated().any():
            duplicate_count = int(df.index.duplicated().sum())
            logger.warning(
                "%s contains %d duplicate dates; keeping latest entries",
                path,
                duplicate_count,
            )
            df = df[~df.index.duplicated(keep="last")]

        non_positive_mask = df["close"] <= 0
        if non_positive_mask.any():
            count = int(non_positive_mask.sum())
            logger.warning("Dropping %d non-positive close values from %s", count, path)
            df = df.loc[~non_positive_mask]

        if df.empty:
            logger.warning("Price file %s is empty after cleaning", path)
            return pd.Series(dtype="float64")

        if len(df.index) > 1:
            gaps = df.index.to_series().diff().dt.days.dropna()
            max_gap = int(gaps.max()) if not gaps.empty else 0
            if max_gap > 10:
                logger.warning("Detected maximum gap of %d days in %s", max_gap, path)

        return df["close"].astype(float)

    def load_multiple_prices(
        self,
        assets: list[SelectedAsset],
        prices_dir: Path,
    ) -> pd.DataFrame:
        """Load price data for many assets and align on the union of dates.

        This method orchestrates the loading of price files for a list of assets
        in parallel. It resolves file paths, submits loading tasks to a thread
        pool, and assembles the resulting Series into a single DataFrame.

        Args:
            assets (list[SelectedAsset]): The list of assets to load prices for.
            prices_dir (Path): The base directory containing the price CSV files.

        Returns:
            pd.DataFrame: A DataFrame containing the close prices for all successfully
                loaded assets. The index is the union of all dates, and columns
                are the asset symbols. Returns an empty DataFrame if no price
                files can be loaded.
        """
        logger.info(
            "Loading price series for %d assets from %s",
            len(assets),
            prices_dir,
        )
        symbol_to_path: dict[str, Path] = {}
        path_to_symbols: dict[Path, list[str]] = defaultdict(list)

        for asset in assets:
            resolved_path = self._resolve_price_path(prices_dir, asset)
            if resolved_path is None:
                continue
            symbol_to_path[asset.symbol] = resolved_path
            path_to_symbols[resolved_path].append(asset.symbol)

        if not symbol_to_path:
            logger.warning("No price files were successfully resolved")
            return pd.DataFrame()

        unique_paths = list(path_to_symbols.keys())
        logger.debug("Resolved %d unique price files", len(unique_paths))

        price_series: dict[Path, pd.Series] = {}
        tasks = self._submit_load_tasks(unique_paths)
        for path, series in tasks:
            if series is None or series.empty:
                logger.warning("Skipping %s because the price series is empty", path)
                continue
            price_series[path] = series

        if not price_series:
            logger.warning("No price files were successfully loaded")
            return pd.DataFrame()

        all_prices: dict[str, pd.Series] = {}
        for path, symbols in path_to_symbols.items():
            series = price_series.get(path)
            if series is None or series.empty:
                missing = ", ".join(symbols[:5])
                logger.warning("Price data missing for assets: %s", missing)
                continue
            for symbol in symbols:
                all_prices[symbol] = series

        if not all_prices:
            logger.warning("No price files were successfully loaded")
            return pd.DataFrame()

        df = pd.DataFrame(all_prices).sort_index()
        logger.info("Loaded price matrix with shape %s", df.shape)
        return df

    @staticmethod
    def _standardize_price_dataframe(raw: pd.DataFrame, path: Path) -> pd.DataFrame:
        """Normalize various price file column conventions to a standard format."""
        if "<DATE>" in raw.columns and "<CLOSE>" in raw.columns:
            df = (
                raw[["<DATE>", "<CLOSE>"]]
                .copy()
                .rename(columns={"<DATE>": "date", "<CLOSE>": "close"})
            )
        elif "DATE" in raw.columns and "CLOSE" in raw.columns:
            df = (
                raw[["DATE", "CLOSE"]]
                .copy()
                .rename(columns={"DATE": "date", "CLOSE": "close"})
            )
        elif "date" in raw.columns and "close" in raw.columns:
            df = raw[["date", "close"]].copy()
        else:
            raise ValueError(
                f"Unsupported price file structure for {path}: columns={list(raw.columns)}",
            )

        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.set_index("date")
        return df

    def _load_price_with_cache(self, path: Path) -> pd.Series:
        """Load price file with LRU cache eviction when cache is full."""
        # Check cache first (and update LRU order if hit)
        with self._cache_lock:
            if path in self._cache:
                # Move to end (most recently used)
                self._cache.move_to_end(path)
                return self._cache[path]

        # Cache miss - load from disk
        series = self.load_price_file(path)

        # Store in cache if non-empty and caching is enabled
        if not series.empty and self.cache_size > 0:
            with self._cache_lock:
                # Remove oldest entry if at capacity
                if len(self._cache) >= self.cache_size:
                    # Remove from beginning (least recently used)
                    self._cache.popitem(last=False)
                # Add new entry at end (most recently used)
                self._cache[path] = series

        return series

    def clear_cache(self) -> None:
        """Clear all cached price series.

        This is useful after bulk operations where cached data is unlikely
        to be reused, helping to free memory immediately rather than waiting
        for LRU eviction.
        """
        with self._cache_lock:
            self._cache.clear()
            logger.debug("Cleared price loader cache")

    def get_cache_stats(self) -> dict[str, int]:
        """Get cache statistics.

        Returns:
            Dictionary with 'size' (current entries) and 'maxsize' (capacity).

        Useful for testing and monitoring.
        """
        with self._cache_lock:
            return {
                "size": len(self._cache),
                "maxsize": self.cache_size,
            }

    def cache_info(self) -> dict[str, int]:
        """Return cache statistics for monitoring.

        This method is an alias for get_cache_stats for backward compatibility.
        """
        return self.get_cache_stats()

    def _submit_load_tasks(
        self,
        paths: Iterable[Path],
    ) -> list[tuple[Path, pd.Series | None]]:
        paths = list(paths)
        if not paths:
            return []

        # If only one path or concurrency disabled, fall back to sequential loading.
        if len(paths) == 1 or (self.max_workers is not None and self.max_workers <= 1):
            return [(path, self._load_price_with_cache(path)) for path in paths]

        max_workers = self.max_workers
        if max_workers is None:
            cpu_count = os.cpu_count() or 1
            max_workers = min(32, cpu_count * 5, len(paths))
        else:
            max_workers = min(max_workers, len(paths))

        if max_workers <= 1:
            return [(path, self._load_price_with_cache(path)) for path in paths]

        results: list[tuple[Path, pd.Series | None]] = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_path = {
                executor.submit(self._load_price_with_cache, path): path
                for path in paths
            }
            for future in as_completed(future_to_path):
                path = future_to_path[future]
                try:
                    series = future.result()
                except Exception:  # pragma: no cover - defensive logging
                    logger.exception("Failed to load %s", path)
                    series = None
                results.append((path, series))

        return results

    def _resolve_price_path(
        self,
        prices_dir: Path,
        asset: SelectedAsset,
    ) -> Path | None:
        price_path = prices_dir / asset.stooq_path
        if price_path.exists():
            return price_path

        alt_name = Path(asset.stooq_path).stem.lower()
        alt_path = prices_dir / f"{alt_name}.csv"
        if alt_path.exists():
            return alt_path

        logger.warning(
            "Price file not found for %s (%s)",
            asset.symbol,
            price_path,
        )
        return None