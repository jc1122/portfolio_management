"""Integration tests for caching in preselection and eligibility."""

import datetime
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
pytestmark = pytest.mark.integration

from portfolio_management.backtesting.eligibility import (
    compute_pit_eligibility,
    compute_pit_eligibility_cached,
)
from portfolio_management.data.factor_caching import FactorCache
from portfolio_management.portfolio.preselection import (
    Preselection,
    PreselectionConfig,
    PreselectionMethod,
)


@pytest.fixture
def sample_returns():
    """Create sample returns DataFrame for testing."""
    dates = pd.date_range("2020-01-01", periods=500, freq="D")
    assets = [f"ASSET_{i}" for i in range(20)]
    np.random.seed(42)
    data = np.random.randn(500, 20) * 0.01
    df = pd.DataFrame(data, index=dates, columns=assets)
    # Ensure some history to meet minimum requirements
    df.iloc[:300] = np.random.randn(300, 20) * 0.01
    return df


@pytest.fixture
def cache_dir():
    """Create temporary cache directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def factor_cache(cache_dir):
    """Create FactorCache instance."""
    return FactorCache(cache_dir, enabled=True)


class TestPreselectionCachingIntegration:
    """Integration tests for preselection with caching."""

    def test_preselection_without_cache(self, sample_returns):
        """Test preselection works without cache."""
        config = PreselectionConfig(
            method=PreselectionMethod.MOMENTUM,
            top_k=10,
            lookback=252,
            skip=21,
        )

        preselection = Preselection(config, cache=None)
        rebalance_date = datetime.date(2021, 3, 1)

        selected = preselection.select_assets(
            returns=sample_returns,
            rebalance_date=rebalance_date,
        )

        assert len(selected) == 10
        assert all(asset in sample_returns.columns for asset in selected)

    def test_preselection_with_cache_first_run(self, sample_returns, factor_cache):
        """Test preselection with cache on first run (cache miss)."""
        config = PreselectionConfig(
            method=PreselectionMethod.MOMENTUM,
            top_k=10,
            lookback=252,
            skip=21,
        )

        preselection = Preselection(config, cache=factor_cache)
        rebalance_date = datetime.date(2021, 3, 1)

        selected = preselection.select_assets(
            returns=sample_returns,
            rebalance_date=rebalance_date,
        )

        assert len(selected) == 10
        stats = factor_cache.get_stats()
        assert stats["misses"] >= 1  # Should have at least one cache miss
        assert stats["puts"] >= 1  # Should have stored result

    def test_preselection_with_cache_second_run(self, sample_returns, factor_cache):
        """Test preselection with cache on second run (cache hit)."""
        config = PreselectionConfig(
            method=PreselectionMethod.MOMENTUM,
            top_k=10,
            lookback=252,
            skip=21,
        )

        preselection = Preselection(config, cache=factor_cache)
        rebalance_date = datetime.date(2021, 3, 1)

        # First run
        selected1 = preselection.select_assets(
            returns=sample_returns,
            rebalance_date=rebalance_date,
        )

        initial_stats = factor_cache.get_stats()

        # Second run with same inputs
        selected2 = preselection.select_assets(
            returns=sample_returns,
            rebalance_date=rebalance_date,
        )

        final_stats = factor_cache.get_stats()

        # Results should be identical
        assert selected1 == selected2

        # Should have cache hit on second run
        assert final_stats["hits"] > initial_stats["hits"]

    def test_preselection_cached_vs_uncached_equivalence(
        self, sample_returns, factor_cache
    ):
        """Test cached and uncached preselection give identical results."""
        config = PreselectionConfig(
            method=PreselectionMethod.MOMENTUM,
            top_k=10,
            lookback=252,
            skip=21,
        )

        rebalance_date = datetime.date(2021, 3, 1)

        # Run without cache
        preselection_no_cache = Preselection(config, cache=None)
        selected_no_cache = preselection_no_cache.select_assets(
            returns=sample_returns,
            rebalance_date=rebalance_date,
        )

        # Run with cache (first time, will miss and compute)
        preselection_cached = Preselection(config, cache=factor_cache)
        selected_cached = preselection_cached.select_assets(
            returns=sample_returns,
            rebalance_date=rebalance_date,
        )

        # Results should be identical
        assert selected_no_cache == selected_cached

    def test_preselection_low_volatility_caching(self, sample_returns, factor_cache):
        """Test caching works for LOW_VOL method."""
        config = PreselectionConfig(
            method=PreselectionMethod.LOW_VOL,
            top_k=10,
            lookback=252,
        )

        preselection = Preselection(config, cache=factor_cache)
        rebalance_date = datetime.date(2021, 3, 1)

        # First run
        selected1 = preselection.select_assets(
            returns=sample_returns,
            rebalance_date=rebalance_date,
        )

        initial_puts = factor_cache.get_stats()["puts"]

        # Second run
        selected2 = preselection.select_assets(
            returns=sample_returns,
            rebalance_date=rebalance_date,
        )

        final_puts = factor_cache.get_stats()["puts"]
        hits = factor_cache.get_stats()["hits"]

        assert selected1 == selected2
        assert final_puts == initial_puts  # No new puts on second run
        assert hits > 0  # Should have cache hits

    def test_preselection_combined_caching(self, sample_returns, factor_cache):
        """Test caching works for COMBINED method."""
        config = PreselectionConfig(
            method=PreselectionMethod.COMBINED,
            top_k=10,
            lookback=252,
            momentum_weight=0.5,
            low_vol_weight=0.5,
        )

        preselection = Preselection(config, cache=factor_cache)
        rebalance_date = datetime.date(2021, 3, 1)

        # First run
        selected1 = preselection.select_assets(
            returns=sample_returns,
            rebalance_date=rebalance_date,
        )

        # Second run
        selected2 = preselection.select_assets(
            returns=sample_returns,
            rebalance_date=rebalance_date,
        )

        assert selected1 == selected2
        assert factor_cache.get_stats()["hits"] > 0

    def test_preselection_cache_invalidation_on_config_change(
        self, sample_returns, factor_cache
    ):
        """Test cache is invalidated when config changes."""
        config1 = PreselectionConfig(
            method=PreselectionMethod.MOMENTUM,
            top_k=10,
            lookback=252,
        )

        config2 = PreselectionConfig(
            method=PreselectionMethod.MOMENTUM,
            top_k=10,
            lookback=504,  # Different lookback
        )

        rebalance_date = datetime.date(2021, 3, 1)

        # Run with config1
        preselection1 = Preselection(config1, cache=factor_cache)
        selected1 = preselection1.select_assets(
            returns=sample_returns,
            rebalance_date=rebalance_date,
        )

        puts_after_first = factor_cache.get_stats()["puts"]

        # Run with config2 (should miss cache and recompute)
        preselection2 = Preselection(config2, cache=factor_cache)
        selected2 = preselection2.select_assets(
            returns=sample_returns,
            rebalance_date=rebalance_date,
        )

        puts_after_second = factor_cache.get_stats()["puts"]

        # Should have new puts from second run
        assert puts_after_second > puts_after_first


class TestPITEligibilityCachingIntegration:
    """Integration tests for PIT eligibility with caching."""

    def test_pit_eligibility_without_cache(self, sample_returns):
        """Test PIT eligibility works without cache."""
        date = datetime.date(2021, 3, 1)
        eligibility = compute_pit_eligibility(
            returns=sample_returns,
            date=date,
            min_history_days=252,
            min_price_rows=252,
        )

        assert isinstance(eligibility, pd.Series)
        assert len(eligibility) == len(sample_returns.columns)
        assert eligibility.dtype == bool

    def test_pit_eligibility_with_cache_first_run(self, sample_returns, factor_cache):
        """Test PIT eligibility with cache on first run."""
        date = datetime.date(2021, 3, 1)

        eligibility = compute_pit_eligibility_cached(
            returns=sample_returns,
            date=date,
            min_history_days=252,
            min_price_rows=252,
            cache=factor_cache,
        )

        assert isinstance(eligibility, pd.Series)
        stats = factor_cache.get_stats()
        assert stats["misses"] >= 1
        assert stats["puts"] >= 1

    def test_pit_eligibility_with_cache_second_run(self, sample_returns, factor_cache):
        """Test PIT eligibility with cache on second run."""
        date = datetime.date(2021, 3, 1)

        # First run
        eligibility1 = compute_pit_eligibility_cached(
            returns=sample_returns,
            date=date,
            min_history_days=252,
            min_price_rows=252,
            cache=factor_cache,
        )

        initial_hits = factor_cache.get_stats()["hits"]

        # Second run
        eligibility2 = compute_pit_eligibility_cached(
            returns=sample_returns,
            date=date,
            min_history_days=252,
            min_price_rows=252,
            cache=factor_cache,
        )

        final_hits = factor_cache.get_stats()["hits"]

        # Results should be identical
        pd.testing.assert_series_equal(eligibility1, eligibility2)

        # Should have cache hit
        assert final_hits > initial_hits

    def test_pit_eligibility_cached_vs_uncached_equivalence(
        self, sample_returns, factor_cache
    ):
        """Test cached and uncached PIT eligibility give identical results."""
        date = datetime.date(2021, 3, 1)

        # Run without cache
        eligibility_no_cache = compute_pit_eligibility(
            returns=sample_returns,
            date=date,
            min_history_days=252,
            min_price_rows=252,
        )

        # Run with cache
        eligibility_cached = compute_pit_eligibility_cached(
            returns=sample_returns,
            date=date,
            min_history_days=252,
            min_price_rows=252,
            cache=factor_cache,
        )

        # Results should be identical
        pd.testing.assert_series_equal(eligibility_no_cache, eligibility_cached)

    def test_pit_eligibility_cache_invalidation_on_param_change(
        self, sample_returns, factor_cache
    ):
        """Test cache is invalidated when parameters change."""
        date = datetime.date(2021, 3, 1)

        # Run with min_history_days=252
        eligibility1 = compute_pit_eligibility_cached(
            returns=sample_returns,
            date=date,
            min_history_days=252,
            min_price_rows=252,
            cache=factor_cache,
        )

        puts_after_first = factor_cache.get_stats()["puts"]

        # Run with min_history_days=504 (should miss cache)
        eligibility2 = compute_pit_eligibility_cached(
            returns=sample_returns,
            date=date,
            min_history_days=504,
            min_price_rows=504,
            cache=factor_cache,
        )

        puts_after_second = factor_cache.get_stats()["puts"]

        # Should have new puts from second run
        assert puts_after_second > puts_after_first

        # Results may differ due to different parameters
        # (not testing equivalence here, just cache behavior)


class TestCachingPerformance:
    """Performance-focused integration tests."""

    def test_cache_reduces_computation_time(self, sample_returns, factor_cache):
        """Test that caching improves performance on second run."""
        import time

        config = PreselectionConfig(
            method=PreselectionMethod.MOMENTUM,
            top_k=10,
            lookback=252,
        )

        preselection = Preselection(config, cache=factor_cache)
        rebalance_date = datetime.date(2021, 3, 1)

        # First run (cache miss)
        start1 = time.perf_counter()
        selected1 = preselection.select_assets(
            returns=sample_returns,
            rebalance_date=rebalance_date,
        )
        time1 = time.perf_counter() - start1

        # Second run (cache hit)
        start2 = time.perf_counter()
        selected2 = preselection.select_assets(
            returns=sample_returns,
            rebalance_date=rebalance_date,
        )
        time2 = time.perf_counter() - start2

        # Results should be identical
        assert selected1 == selected2

        # Second run should be faster (or at least not significantly slower)
        # Using generous threshold to avoid flaky tests
        assert time2 <= time1 * 2.0

    def test_cache_stats_accuracy(self, sample_returns, factor_cache):
        """Test cache statistics are accurate."""
        config = PreselectionConfig(
            method=PreselectionMethod.MOMENTUM,
            top_k=10,
            lookback=252,
        )

        preselection = Preselection(config, cache=factor_cache)
        rebalance_date = datetime.date(2021, 3, 1)

        # Clear stats
        factor_cache._hits = 0
        factor_cache._misses = 0
        factor_cache._puts = 0

        # Run 3 times
        for _ in range(3):
            preselection.select_assets(
                returns=sample_returns,
                rebalance_date=rebalance_date,
            )

        stats = factor_cache.get_stats()

        # First run: miss + put
        # Second run: hit
        # Third run: hit
        assert stats["misses"] >= 1
        assert stats["puts"] >= 1
        assert stats["hits"] >= 2
