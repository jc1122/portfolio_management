"""Unit tests for cache isolation mechanisms."""

import pytest
from portfolio_management.analytics.returns.loaders import PriceLoader
from portfolio_management.portfolio.statistics.rolling_statistics import StatisticsCache
from portfolio_management.data.factor_caching.factor_cache import FactorCache


@pytest.mark.unit
def test_price_loader_has_clear_method():
    """PriceLoader should have clear_cache method."""
    loader = PriceLoader()
    assert hasattr(loader, "clear_cache")
    assert callable(loader.clear_cache)


@pytest.mark.unit
def test_price_loader_clear_works():
    """Clearing PriceLoader cache should empty it."""
    loader = PriceLoader()

    # Manually add something to cache
    import pandas as pd
    loader._cache["test"] = pd.DataFrame()

    assert loader.get_cache_stats()["size"] == 1

    loader.clear_cache()

    assert loader.get_cache_stats()["size"] == 0


@pytest.mark.unit
def test_statistics_cache_has_clear_method():
    """StatisticsCache should have clear_cache method."""
    cache = StatisticsCache()
    assert hasattr(cache, "clear_cache")
    assert callable(cache.clear_cache)


@pytest.mark.unit
def test_statistics_cache_clear_works():
    """Clearing StatisticsCache should empty it."""
    cache = StatisticsCache()

    # Manually add something to caches
    import pandas as pd
    cache._cached_cov = pd.DataFrame()
    cache._cached_mean = pd.Series()

    stats = cache.get_cache_stats()
    assert stats["covariance_entries"] == 1
    assert stats["returns_entries"] == 1

    cache.clear_cache()

    stats = cache.get_cache_stats()
    assert stats["covariance_entries"] == 0
    assert stats["returns_entries"] == 0


@pytest.mark.unit
def test_factor_cache_has_clear_method(tmp_path):
    """FactorCache should have clear_cache method."""
    cache = FactorCache(tmp_path)
    assert hasattr(cache, "clear_cache")
    assert callable(cache.clear_cache)


@pytest.mark.unit
def test_factor_cache_clear_works(tmp_path):
    """Clearing FactorCache should empty it."""
    cache = FactorCache(tmp_path)

    # Manually add something to caches
    cache._memory_cache["test"] = "test"
    (tmp_path / "data").mkdir(parents=True, exist_ok=True)
    (tmp_path / "data" / "test.pkl").touch()

    stats = cache.get_cache_stats()
    assert stats["memory_entries"] == 1
    assert stats["disk_entries"] == 1

    deleted_count = cache.clear_cache()
    assert deleted_count == 0 # Metadata dir is empty

    stats = cache.get_cache_stats()
    assert stats["memory_entries"] == 0
    assert stats["disk_entries"] == 0


@pytest.mark.unit
def test_cache_stats_methods_exist(tmp_path):
    """All caches should have get_cache_stats method."""
    loader = PriceLoader()
    stats_cache = StatisticsCache()
    factor_cache = FactorCache(tmp_path)

    assert hasattr(loader, "get_cache_stats")
    assert hasattr(stats_cache, "get_cache_stats")
    assert hasattr(factor_cache, "get_cache_stats")

    # Should return dict
    assert isinstance(loader.get_cache_stats(), dict)
    assert isinstance(stats_cache.get_cache_stats(), dict)
    assert isinstance(factor_cache.get_cache_stats(), dict)