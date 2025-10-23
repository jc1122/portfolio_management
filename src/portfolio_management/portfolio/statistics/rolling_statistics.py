"""Rolling statistics computation with caching for portfolio strategies.

This module provides efficient rolling window statistics (covariance, expected returns)
that can be incrementally updated when new data arrives, avoiding full recalculation
when most of the data window overlaps with the previous computation.
"""

from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd


class RollingStatistics:
    """Efficient rolling statistics computation with caching.

    This class maintains cached covariance matrices and expected returns that can be
    incrementally updated when new data is added, significantly improving performance
    for large universes with overlapping data windows (e.g., monthly rebalances).

    The cache is automatically invalidated when:
    - The asset set changes (different tickers)
    - The lookback window changes
    - The data window shifts beyond the cache validity

    Attributes:
        window_size: Number of periods for the rolling window (default: 252)
        annualization_factor: Factor to annualize statistics (default: 252)

    """

    def __init__(
        self,
        window_size: int = 252,
        annualization_factor: int = 252,
    ) -> None:
        """Initialize rolling statistics calculator.

        Args:
            window_size: Number of periods for rolling window
            annualization_factor: Factor to annualize returns (e.g., 252 for daily data)

        """
        self.window_size = window_size
        self.annualization_factor = annualization_factor

        # Cache state
        self._cached_data: pd.DataFrame | None = None
        self._cached_cov: pd.DataFrame | None = None
        self._cached_mean: pd.Series | None = None
        self._cache_key: str | None = None
        self._asset_columns: pd.Index | None = None
        self._sum_vector: np.ndarray | None = None
        self._cross_prod_matrix: np.ndarray | None = None
        self._count: int = 0

    def get_covariance_matrix(
        self,
        returns: pd.DataFrame,
        annualize: bool = True,
    ) -> pd.DataFrame:
        """Compute or retrieve cached covariance matrix.

        Args:
            returns: DataFrame of returns (dates as index, tickers as columns)
            annualize: Whether to annualize the covariance matrix

        Returns:
            Covariance matrix as DataFrame

        """
        _, cov_matrix = self._retrieve_statistics(returns)

        if annualize:
            return cov_matrix * self.annualization_factor
        return cov_matrix

    def get_expected_returns(
        self,
        returns: pd.DataFrame,
        annualize: bool = True,
    ) -> pd.Series:
        """Compute or retrieve cached expected returns.

        Args:
            returns: DataFrame of returns (dates as index, tickers as columns)
            annualize: Whether to annualize the expected returns

        Returns:
            Expected returns as Series

        """
        mean_returns, _ = self._retrieve_statistics(returns)

        if annualize:
            return mean_returns * self.annualization_factor
        return mean_returns

    def get_statistics(
        self,
        returns: pd.DataFrame,
        annualize: bool = True,
    ) -> tuple[pd.Series, pd.DataFrame]:
        """Compute or retrieve both expected returns and covariance matrix.

        This is more efficient than calling get_expected_returns and
        get_covariance_matrix separately as it computes both in one pass.

        Args:
            returns: DataFrame of returns (dates as index, tickers as columns)
            annualize: Whether to annualize the statistics

        Returns:
            Tuple of (expected_returns, covariance_matrix)

        """
        mean_returns, cov_matrix = self._retrieve_statistics(returns)

        if annualize:
            return (
                mean_returns * self.annualization_factor,
                cov_matrix * self.annualization_factor,
            )
        return mean_returns, cov_matrix

    def invalidate_cache(self) -> None:
        """Manually invalidate the cache.

        This forces recomputation on the next statistics request.
        """
        self._cached_data = None
        self._cached_cov = None
        self._cached_mean = None
        self._cache_key = None
        self._asset_columns = None
        self._sum_vector = None
        self._cross_prod_matrix = None
        self._count = 0

    def _retrieve_statistics(
        self, returns: pd.DataFrame,
    ) -> tuple[pd.Series, pd.DataFrame]:
        """Return statistics from cache or recompute them."""

        cache_key = self._compute_cache_key(returns)

        if self._can_incrementally_update(cache_key, returns):
            return self._update_incrementally(returns, cache_key)

        return self._recompute_statistics(returns, cache_key)

    def _compute_cache_key(self, returns: pd.DataFrame) -> str:
        """Compute a cache key based on data characteristics.

        Args:
            returns: DataFrame to compute key for

        Returns:
            Cache key string

        """
        # Include stable characteristics in cache key to preserve reuse across
        # overlapping windows.
        key_components = [
            str(sorted(returns.columns.tolist())),
            str(self.window_size),
        ]
        key_string = "|".join(key_components)
        return hashlib.md5(key_string.encode()).hexdigest()

    def _can_incrementally_update(self, cache_key: str, returns: pd.DataFrame) -> bool:
        """Determine whether cached state can service the new data."""

        if (
            self._cache_key is None
            or self._cached_data is None
            or self._asset_columns is None
            or self._sum_vector is None
            or self._cross_prod_matrix is None
        ):
            return False

        if cache_key != self._cache_key:
            return False

        if not self._asset_columns.equals(returns.columns):
            return False

        if returns.empty:
            # Allow incremental update so we preserve cached state when
            # consumers temporarily supply empty frames.
            return True

        if returns.isna().any().any() or self._cached_data.isna().any().any():
            # Pandas cov/mean handle NaNs with pairwise deletion. The incremental
            # update path assumes dense data, so fall back to a full recompute.
            return False

        overlap = self._cached_data.index.intersection(returns.index, sort=False)
        if overlap.empty:
            return False

        cached_overlap = self._cached_data.loc[overlap].to_numpy()
        new_overlap = returns.loc[overlap].to_numpy()

        return np.allclose(
            cached_overlap,
            new_overlap,
            rtol=1e-9,
            atol=1e-12,
        )

    def _recompute_statistics(
        self, returns: pd.DataFrame, cache_key: str,
    ) -> tuple[pd.Series, pd.DataFrame]:
        """Recompute statistics from scratch and refresh the cache."""

        self._cached_data = returns.copy()
        self._cache_key = cache_key
        self._asset_columns = returns.columns.copy()

        values = returns.to_numpy(dtype=float, copy=True)
        self._count = len(returns)

        if self._count == 0:
            self._sum_vector = np.zeros(len(self._asset_columns), dtype=float)
            self._cross_prod_matrix = np.zeros(
                (len(self._asset_columns), len(self._asset_columns)),
                dtype=float,
            )
            mean_returns = pd.Series(np.nan, index=self._asset_columns, dtype=float)
            cov_matrix = pd.DataFrame(
                np.nan,
                index=self._asset_columns,
                columns=self._asset_columns,
            )
        else:
            self._sum_vector = values.sum(axis=0)
            self._cross_prod_matrix = values.T @ values

            mean_vector = self._sum_vector / self._count
            mean_returns = pd.Series(mean_vector, index=self._asset_columns)

            if self._count <= 1:
                cov_values = np.full(
                    (len(self._asset_columns), len(self._asset_columns)),
                    np.nan,
                    dtype=float,
                )
            else:
                centered = self._cross_prod_matrix - self._count * np.outer(
                    mean_vector,
                    mean_vector,
                )
                cov_values = centered / (self._count - 1)
                # Numerical noise may introduce asymmetry; enforce symmetry.
                cov_values = (cov_values + cov_values.T) / 2

            cov_matrix = pd.DataFrame(
                cov_values,
                index=self._asset_columns,
                columns=self._asset_columns,
            )

        self._cached_mean = mean_returns
        self._cached_cov = cov_matrix

        return mean_returns, cov_matrix

    def _update_incrementally(
        self, returns: pd.DataFrame, cache_key: str,
    ) -> tuple[pd.Series, pd.DataFrame]:
        """Update cached statistics for a partially overlapping window."""

        assert self._cached_data is not None  # For type checkers
        assert self._asset_columns is not None
        assert self._sum_vector is not None
        assert self._cross_prod_matrix is not None

        overlap = self._cached_data.index.intersection(returns.index, sort=False)
        overlap_set = set(overlap)

        rows_to_remove = [
            idx for idx in self._cached_data.index if idx not in overlap_set
        ]
        rows_to_add = [idx for idx in returns.index if idx not in overlap_set]

        # Remove rows that fell out of the window
        for idx in rows_to_remove:
            row = self._cached_data.loc[idx].to_numpy(dtype=float)
            self._sum_vector -= row
            self._cross_prod_matrix -= np.outer(row, row)
            self._count -= 1

        # Add new rows that entered the window
        for idx in rows_to_add:
            row = returns.loc[idx].to_numpy(dtype=float)
            self._sum_vector += row
            self._cross_prod_matrix += np.outer(row, row)
            self._count += 1

        self._cached_data = returns.copy()
        self._cache_key = cache_key

        asset_count = len(self._asset_columns)
        if self._count == 0:
            self._sum_vector = np.zeros(asset_count, dtype=float)
            self._cross_prod_matrix = np.zeros((asset_count, asset_count), dtype=float)

        if self._count == 0:
            mean_vector = np.full(asset_count, np.nan, dtype=float)
            cov_values = np.full((asset_count, asset_count), np.nan, dtype=float)
        else:
            mean_vector = self._sum_vector / self._count
            if self._count <= 1:
                cov_values = np.full((asset_count, asset_count), np.nan, dtype=float)
            else:
                centered = self._cross_prod_matrix - self._count * np.outer(
                    mean_vector,
                    mean_vector,
                )
                cov_values = centered / (self._count - 1)
                cov_values = (cov_values + cov_values.T) / 2

        mean_returns = pd.Series(mean_vector, index=self._asset_columns)
        cov_matrix = pd.DataFrame(
            cov_values,
            index=self._asset_columns,
            columns=self._asset_columns,
        )

        self._cached_mean = mean_returns
        self._cached_cov = cov_matrix

        # Ensure the cache count matches the new window length for correctness.

        return mean_returns, cov_matrix
