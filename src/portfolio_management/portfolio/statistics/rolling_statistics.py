"""Rolling statistics computation with caching for portfolio strategies.

This module provides efficient rolling window statistics (covariance, expected returns)
that can be incrementally updated when new data arrives, avoiding full recalculation
when most of the data window overlaps with the previous computation.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from collections.abc import Hashable


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
        cache_key = self._compute_cache_key(returns)
        
        # Check if we can use cached result
        if self._is_cache_valid(cache_key, returns):
            # Use cached covariance matrix
            cov_matrix = self._cached_cov
        else:
            # Compute new covariance matrix
            cov_matrix = returns.cov()
            
            # Update cache (also cache mean for consistency)
            self._cached_data = returns.copy()
            self._cached_cov = cov_matrix
            self._cached_mean = returns.mean()  # Cache mean too
            self._cache_key = cache_key
        
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
        cache_key = self._compute_cache_key(returns)
        
        # Check if we can use cached result
        if self._is_cache_valid(cache_key, returns):
            # Use cached mean returns
            mean_returns = self._cached_mean
        else:
            # Compute new mean returns
            mean_returns = returns.mean()
            
            # Update cache (also update covariance for consistency)
            self._cached_data = returns.copy()
            self._cached_mean = mean_returns
            self._cached_cov = returns.cov()  # Cache covariance too
            self._cache_key = cache_key
        
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
        cache_key = self._compute_cache_key(returns)
        
        # Check if we can use cached result
        if self._is_cache_valid(cache_key, returns):
            # Use cached statistics
            mean_returns = self._cached_mean
            cov_matrix = self._cached_cov
        else:
            # Compute new statistics
            mean_returns = returns.mean()
            cov_matrix = returns.cov()
            
            # Update cache
            self._cached_data = returns.copy()
            self._cached_mean = mean_returns
            self._cached_cov = cov_matrix
            self._cache_key = cache_key
        
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

    def _compute_cache_key(self, returns: pd.DataFrame) -> str:
        """Compute a cache key based on data characteristics.

        Args:
            returns: DataFrame to compute key for

        Returns:
            Cache key string

        """
        # Include shape, columns, and date range in cache key
        key_components = [
            str(returns.shape),
            str(sorted(returns.columns.tolist())),
            str(returns.index[0]) if len(returns) > 0 else "",
            str(returns.index[-1]) if len(returns) > 0 else "",
        ]
        key_string = "|".join(key_components)
        return hashlib.md5(key_string.encode()).hexdigest()

    def _is_cache_valid(self, cache_key: str, returns: pd.DataFrame) -> bool:
        """Check if the cache is valid for the given data.

        Args:
            cache_key: Cache key for the new data
            returns: DataFrame to check against cache

        Returns:
            True if cache can be used, False otherwise

        """
        if self._cache_key is None or self._cached_data is None:
            return False
        
        if cache_key != self._cache_key:
            return False
        
        # Verify data integrity (shape and columns match)
        if (
            self._cached_data.shape != returns.shape
            or not self._cached_data.columns.equals(returns.columns)
        ):
            return False
        
        # Additional safety check: verify data is actually the same
        # For performance, just check a sample
        if len(returns) > 0:
            sample_idx = min(10, len(returns) - 1)
            if not np.allclose(
                self._cached_data.iloc[sample_idx].values,
                returns.iloc[sample_idx].values,
                rtol=1e-9,
                atol=1e-12,
            ):
                return False
        
        return True
