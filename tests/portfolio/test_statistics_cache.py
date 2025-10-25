"""Tests for rolling statistics with caching."""

import numpy as np
import pandas as pd
import pytest

from portfolio_management.portfolio.statistics import StatisticsCache


class TestStatisticsCache:
    """Tests for StatisticsCache class."""

    @pytest.fixture
    def sample_returns(self):
        """Create sample returns DataFrame."""
        np.random.seed(42)
        dates = pd.date_range("2020-01-01", periods=252, freq="D")
        tickers = ["AAPL", "MSFT", "GOOGL", "AMZN"]
        data = np.random.randn(252, 4) * 0.02  # 2% daily vol
        return pd.DataFrame(data, index=dates, columns=tickers)

    def test_initialization(self):
        """Test StatisticsCache initialization."""
        stats = StatisticsCache(window_size=252, annualization_factor=252)
        assert stats.window_size == 252
        assert stats.annualization_factor == 252
        assert stats._cached_data is None
        assert stats._cached_cov is None
        assert stats._cached_mean is None
        assert stats._cache_key is None

    def test_get_covariance_matrix_no_cache(self, sample_returns):
        """Test covariance matrix computation without cache."""
        stats = StatisticsCache()
        cov_matrix = stats.get_covariance_matrix(sample_returns, annualize=False)

        # Verify it matches pandas cov()
        expected_cov = sample_returns.cov()
        assert np.allclose(cov_matrix.values, expected_cov.values)

        # Verify cache is populated
        assert stats._cached_cov is not None
        assert stats._cached_data is not None
        assert stats._cache_key is not None

    def test_get_covariance_matrix_annualized(self, sample_returns):
        """Test annualized covariance matrix computation."""
        stats = StatisticsCache(annualization_factor=252)
        cov_matrix = stats.get_covariance_matrix(sample_returns, annualize=True)

        # Verify it matches annualized pandas cov()
        expected_cov = sample_returns.cov() * 252
        assert np.allclose(cov_matrix.values, expected_cov.values)

    def test_get_expected_returns_no_cache(self, sample_returns):
        """Test expected returns computation without cache."""
        stats = StatisticsCache()
        mean_returns = stats.get_expected_returns(sample_returns, annualize=False)

        # Verify it matches pandas mean()
        expected_mean = sample_returns.mean()
        assert np.allclose(mean_returns.values, expected_mean.values)

        # Verify cache is populated
        assert stats._cached_mean is not None
        assert stats._cached_data is not None

    def test_get_expected_returns_annualized(self, sample_returns):
        """Test annualized expected returns computation."""
        stats = StatisticsCache(annualization_factor=252)
        mean_returns = stats.get_expected_returns(sample_returns, annualize=True)

        # Verify it matches annualized pandas mean()
        expected_mean = sample_returns.mean() * 252
        assert np.allclose(mean_returns.values, expected_mean.values)

    def test_get_statistics_no_cache(self, sample_returns):
        """Test combined statistics computation without cache."""
        stats = StatisticsCache()
        mean_returns, cov_matrix = stats.get_statistics(sample_returns, annualize=False)

        # Verify both match pandas computations
        expected_mean = sample_returns.mean()
        expected_cov = sample_returns.cov()
        assert np.allclose(mean_returns.values, expected_mean.values)
        assert np.allclose(cov_matrix.values, expected_cov.values)

        # Verify cache is populated for both
        assert stats._cached_mean is not None
        assert stats._cached_cov is not None
        assert stats._cached_data is not None

    def test_get_statistics_annualized(self, sample_returns):
        """Test combined annualized statistics computation."""
        stats = StatisticsCache(annualization_factor=252)
        mean_returns, cov_matrix = stats.get_statistics(sample_returns, annualize=True)

        # Verify both match annualized pandas computations
        expected_mean = sample_returns.mean() * 252
        expected_cov = sample_returns.cov() * 252
        assert np.allclose(mean_returns.values, expected_mean.values)
        assert np.allclose(cov_matrix.values, expected_cov.values)

    def test_cache_hit_same_data(self, sample_returns):
        """Test that cache is used when computing on same data twice."""
        stats = StatisticsCache()

        # First computation - no cache
        cov1 = stats.get_covariance_matrix(sample_returns, annualize=False)
        cache_key1 = stats._cache_key

        # Second computation - should use cache
        cov2 = stats.get_covariance_matrix(sample_returns, annualize=False)
        cache_key2 = stats._cache_key

        # Verify cache was used (same key)
        assert cache_key1 == cache_key2
        assert np.allclose(cov1.values, cov2.values)

    def test_cache_invalidation_different_columns(self, sample_returns):
        """Test that cache is invalidated when columns change."""
        stats = StatisticsCache()

        # First computation
        _ = stats.get_covariance_matrix(sample_returns, annualize=False)
        cache_key1 = stats._cache_key

        # Second computation with different columns
        different_returns = sample_returns[["AAPL", "MSFT", "GOOGL"]]
        _ = stats.get_covariance_matrix(different_returns, annualize=False)
        cache_key2 = stats._cache_key

        # Verify cache was invalidated (different key)
        assert cache_key1 != cache_key2

    def test_cache_updates_when_shape_changes(self, sample_returns):
        """The cache should adapt when the window size changes."""
        stats = StatisticsCache()

        # Populate cache with the full window
        _ = stats.get_covariance_matrix(sample_returns, annualize=False)
        cache_key1 = stats._cache_key

        # Provide a shorter window and ensure statistics reflect the new data
        different_returns = sample_returns.iloc[:200]
        updated_cov = stats.get_covariance_matrix(different_returns, annualize=False)

        pd.testing.assert_frame_equal(updated_cov, different_returns.cov())
        assert stats._cached_data is not None
        assert stats._cached_data.equals(different_returns)
        assert stats._count == len(different_returns)
        # Cache key stays stable because the asset universe is unchanged.
        assert cache_key1 == stats._cache_key

    def test_cache_updates_when_dates_shift(self, sample_returns):
        """The cache should reuse statistics when the window slides forward."""
        stats = StatisticsCache()

        # Populate cache with the initial window
        _ = stats.get_covariance_matrix(sample_returns, annualize=False)
        cache_key1 = stats._cache_key

        # Shift the window forward by one month worth of data
        different_dates = pd.date_range("2020-02-01", periods=252, freq="D")
        different_returns = sample_returns.copy()
        different_returns.index = different_dates
        updated_cov = stats.get_covariance_matrix(different_returns, annualize=False)

        pd.testing.assert_frame_equal(updated_cov, different_returns.cov())
        assert stats._cached_data is not None
        assert stats._cached_data.equals(different_returns)
        assert stats._count == len(different_returns)
        assert cache_key1 == stats._cache_key

    def test_manual_invalidate_cache(self, sample_returns):
        """Test manual cache invalidation."""
        stats = StatisticsCache()

        # Populate cache
        _ = stats.get_covariance_matrix(sample_returns, annualize=False)
        assert stats._cache_key is not None

        # Manually invalidate
        stats.clear_cache()

        # Verify cache is cleared
        assert stats._cached_data is None
        assert stats._cached_cov is None
        assert stats._cached_mean is None
        assert stats._cache_key is None

    def test_cache_with_both_methods(self, sample_returns):
        """Test that cache works correctly when mixing covariance and mean calls."""
        stats = StatisticsCache()

        # Get covariance first
        cov1 = stats.get_covariance_matrix(sample_returns, annualize=False)

        # Then get mean - should reuse cached data
        mean1 = stats.get_expected_returns(sample_returns, annualize=False)

        # Then get covariance again - should use cache
        cov2 = stats.get_covariance_matrix(sample_returns, annualize=False)

        # Verify results are consistent
        assert np.allclose(cov1.values, cov2.values)

        # Verify cache was populated with both
        assert stats._cached_cov is not None
        assert stats._cached_mean is not None

    def test_get_statistics_single_call(self, sample_returns):
        """Test that get_statistics efficiently computes both in one pass."""
        stats = StatisticsCache()

        # Get both statistics in one call
        mean, cov = stats.get_statistics(sample_returns, annualize=False)

        # Verify both are cached
        assert stats._cached_mean is not None
        assert stats._cached_cov is not None

        # Verify they match separate computations
        assert np.allclose(mean.values, sample_returns.mean().values)
        assert np.allclose(cov.values, sample_returns.cov().values)

    def test_empty_dataframe(self):
        """Test behavior with empty DataFrame."""
        stats = StatisticsCache()
        empty_df = pd.DataFrame()

        # Should compute without error (pandas behavior)
        cov = stats.get_covariance_matrix(empty_df, annualize=False)
        assert cov.empty

    def test_single_asset(self):
        """Test behavior with single asset."""
        stats = StatisticsCache()
        dates = pd.date_range("2020-01-01", periods=100, freq="D")
        single_asset = pd.DataFrame(
            np.random.randn(100) * 0.02,
            index=dates,
            columns=["AAPL"],
        )

        cov = stats.get_covariance_matrix(single_asset, annualize=False)
        assert cov.shape == (1, 1)
        assert cov.iloc[0, 0] > 0  # Variance should be positive

    def test_different_window_sizes(self):
        """Test with different window sizes."""
        # Window size doesn't directly affect computation (just a parameter)
        stats_short = StatisticsCache(window_size=60)
        stats_long = StatisticsCache(window_size=252)

        dates = pd.date_range("2020-01-01", periods=100, freq="D")
        returns = pd.DataFrame(
            np.random.randn(100, 2) * 0.02,
            index=dates,
            columns=["AAPL", "MSFT"],
        )

        # Both should compute correctly
        cov_short = stats_short.get_covariance_matrix(returns, annualize=False)
        cov_long = stats_long.get_covariance_matrix(returns, annualize=False)

        # Results should be the same (window_size doesn't affect computation)
        assert np.allclose(cov_short.values, cov_long.values)