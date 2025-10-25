"""Tests for factor score and PIT eligibility caching."""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
pytestmark = pytest.mark.integration

from portfolio_management.data.factor_caching import CacheMetadata, FactorCache


@pytest.fixture
def sample_returns():
    """Create sample returns DataFrame."""
    dates = pd.date_range("2020-01-01", periods=500, freq="D")
    assets = [f"ASSET_{i}" for i in range(10)]
    np.random.seed(42)
    data = np.random.randn(500, 10) * 0.01
    return pd.DataFrame(data, index=dates, columns=assets)


@pytest.fixture
def cache_dir():
    """Create temporary cache directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def factor_cache(cache_dir):
    """Create FactorCache instance."""
    return FactorCache(cache_dir, enabled=True)


class TestCacheMetadata:
    """Test CacheMetadata dataclass."""

    def test_to_dict(self):
        """Test serialization to dict."""
        metadata = CacheMetadata(
            cache_key="abc123",
            dataset_hash="hash1",
            config_hash="hash2",
            start_date="2020-01-01",
            end_date="2020-12-31",
            created_at="2025-10-24T00:00:00",
            entry_type="factor_scores",
            params={"method": "momentum", "lookback": 252},
        )

        data = metadata.to_dict()
        assert data["cache_key"] == "abc123"
        assert data["dataset_hash"] == "hash1"
        assert data["entry_type"] == "factor_scores"
        assert data["params"]["method"] == "momentum"

    def test_from_dict(self):
        """Test deserialization from dict."""
        data = {
            "cache_key": "abc123",
            "dataset_hash": "hash1",
            "config_hash": "hash2",
            "start_date": "2020-01-01",
            "end_date": "2020-12-31",
            "created_at": "2025-10-24T00:00:00",
            "entry_type": "factor_scores",
            "params": {"method": "momentum"},
        }

        metadata = CacheMetadata.from_dict(data)
        assert metadata.cache_key == "abc123"
        assert metadata.dataset_hash == "hash1"
        assert metadata.params["method"] == "momentum"

    def test_roundtrip(self):
        """Test serialization roundtrip."""
        original = CacheMetadata(
            cache_key="test",
            dataset_hash="d1",
            config_hash="c1",
            start_date="2020-01-01",
            end_date="2020-12-31",
            created_at="2025-10-24T00:00:00",
            entry_type="pit_eligibility",
            params={},
        )

        data = original.to_dict()
        restored = CacheMetadata.from_dict(data)

        assert restored.cache_key == original.cache_key
        assert restored.dataset_hash == original.dataset_hash
        assert restored.entry_type == original.entry_type


class TestFactorCache:
    """Test FactorCache functionality."""

    def test_initialization(self, cache_dir):
        """Test cache initialization."""
        cache = FactorCache(cache_dir, enabled=True)
        assert cache.enabled
        assert (cache_dir / "metadata").exists()
        assert (cache_dir / "data").exists()

    def test_disabled_cache(self, cache_dir):
        """Test that disabled cache doesn't create directories."""
        cache = FactorCache(cache_dir / "disabled", enabled=False)
        assert not cache.enabled
        assert not (cache_dir / "disabled").exists()

    def test_dataset_hash_computation(self, factor_cache, sample_returns):
        """Test dataset hash is computed consistently."""
        hash1 = factor_cache._compute_dataset_hash(sample_returns)
        hash2 = factor_cache._compute_dataset_hash(sample_returns)
        assert hash1 == hash2
        assert len(hash1) == 16  # SHA256 truncated to 16 chars

    def test_dataset_hash_differs_for_different_data(
        self, factor_cache, sample_returns
    ):
        """Test dataset hash changes when data changes."""
        hash1 = factor_cache._compute_dataset_hash(sample_returns)

        # Modify data
        modified = sample_returns.copy()
        modified.iloc[0, 0] = 999.0
        hash2 = factor_cache._compute_dataset_hash(modified)

        assert hash1 != hash2

    def test_config_hash_computation(self, factor_cache):
        """Test config hash is computed consistently."""
        config = {"method": "momentum", "lookback": 252, "skip": 1}
        hash1 = factor_cache._compute_config_hash(config)
        hash2 = factor_cache._compute_config_hash(config)
        assert hash1 == hash2
        assert len(hash1) == 16

    def test_config_hash_key_order_independent(self, factor_cache):
        """Test config hash is independent of key order."""
        config1 = {"lookback": 252, "method": "momentum", "skip": 1}
        config2 = {"method": "momentum", "skip": 1, "lookback": 252}
        hash1 = factor_cache._compute_config_hash(config1)
        hash2 = factor_cache._compute_config_hash(config2)
        assert hash1 == hash2

    def test_config_hash_differs_for_different_config(self, factor_cache):
        """Test config hash changes when config changes."""
        config1 = {"method": "momentum", "lookback": 252}
        config2 = {"method": "momentum", "lookback": 504}
        hash1 = factor_cache._compute_config_hash(config1)
        hash2 = factor_cache._compute_config_hash(config2)
        assert hash1 != hash2


class TestFactorScoreCaching:
    """Test factor score caching."""

    def test_cache_miss_on_first_access(self, factor_cache, sample_returns):
        """Test cache miss on first access."""
        config = {"method": "momentum", "lookback": 252}
        result = factor_cache.get_factor_scores(
            sample_returns, config, "2020-01-01", "2020-12-31"
        )
        assert result is None
        assert factor_cache.get_stats()["misses"] == 1

    def test_cache_put_and_get(self, factor_cache, sample_returns):
        """Test caching and retrieval of factor scores."""
        config = {"method": "momentum", "lookback": 252}
        scores = pd.Series(
            np.random.randn(len(sample_returns.columns)),
            index=sample_returns.columns,
        )

        # Cache scores
        factor_cache.put_factor_scores(
            scores, sample_returns, config, "2020-01-01", "2020-12-31"
        )
        assert factor_cache.get_stats()["puts"] == 1

        # Retrieve scores
        cached = factor_cache.get_factor_scores(
            sample_returns, config, "2020-01-01", "2020-12-31"
        )
        assert cached is not None
        assert factor_cache.get_stats()["hits"] == 1
        pd.testing.assert_series_equal(cached, scores)

    def test_cache_miss_on_different_config(self, factor_cache, sample_returns):
        """Test cache miss when config changes."""
        scores = pd.Series(np.random.randn(10), index=sample_returns.columns)
        config1 = {"method": "momentum", "lookback": 252}
        config2 = {"method": "momentum", "lookback": 504}

        # Cache with config1
        factor_cache.put_factor_scores(
            scores, sample_returns, config1, "2020-01-01", "2020-12-31"
        )

        # Try to get with config2
        cached = factor_cache.get_factor_scores(
            sample_returns, config2, "2020-01-01", "2020-12-31"
        )
        assert cached is None
        assert factor_cache.get_stats()["misses"] == 1

    def test_cache_miss_on_different_date_range(self, factor_cache, sample_returns):
        """Test cache miss when date range changes."""
        scores = pd.Series(np.random.randn(10), index=sample_returns.columns)
        config = {"method": "momentum", "lookback": 252}

        # Cache with date range 1
        factor_cache.put_factor_scores(
            scores, sample_returns, config, "2020-01-01", "2020-12-31"
        )

        # Try to get with date range 2
        cached = factor_cache.get_factor_scores(
            sample_returns, config, "2020-01-01", "2021-12-31"
        )
        assert cached is None

    def test_cache_with_different_data(self, factor_cache, sample_returns):
        """Test cache correctly handles different datasets."""
        scores = pd.Series(np.random.randn(10), index=sample_returns.columns)
        config = {"method": "momentum", "lookback": 252}

        # Cache with original data
        factor_cache.put_factor_scores(
            scores, sample_returns, config, "2020-01-01", "2020-12-31"
        )

        # Modify data and try to retrieve
        modified = sample_returns.copy()
        modified.iloc[0, 0] = 999.0
        cached = factor_cache.get_factor_scores(
            modified, config, "2020-01-01", "2020-12-31"
        )
        assert cached is None  # Should miss because data changed


class TestPITEligibilityCaching:
    """Test PIT eligibility caching."""

    def test_pit_cache_put_and_get(self, factor_cache, sample_returns):
        """Test caching and retrieval of PIT eligibility."""
        config = {"min_history_days": 252, "min_price_rows": 252}
        eligibility = pd.Series(
            [True, False, True, False, True, False, True, False, True, False],
            index=sample_returns.columns,
        )

        # Cache eligibility
        factor_cache.put_pit_eligibility(
            eligibility, sample_returns, config, "2020-01-01", "2020-12-31"
        )

        # Retrieve eligibility
        cached = factor_cache.get_pit_eligibility(
            sample_returns, config, "2020-01-01", "2020-12-31"
        )
        assert cached is not None
        pd.testing.assert_series_equal(cached, eligibility)

    def test_pit_cache_independent_of_factor_cache(self, factor_cache, sample_returns):
        """Test PIT cache and factor cache are independent."""
        factor_config = {"method": "momentum", "lookback": 252}
        pit_config = {"min_history_days": 252, "min_price_rows": 252}

        factor_scores = pd.Series(np.random.randn(10), index=sample_returns.columns)
        eligibility = pd.Series([True] * 10, index=sample_returns.columns)

        # Cache both
        factor_cache.put_factor_scores(
            factor_scores, sample_returns, factor_config, "2020-01-01", "2020-12-31"
        )
        factor_cache.put_pit_eligibility(
            eligibility, sample_returns, pit_config, "2020-01-01", "2020-12-31"
        )

        # Retrieve both
        cached_factors = factor_cache.get_factor_scores(
            sample_returns, factor_config, "2020-01-01", "2020-12-31"
        )
        cached_pit = factor_cache.get_pit_eligibility(
            sample_returns, pit_config, "2020-01-01", "2020-12-31"
        )

        assert cached_factors is not None
        assert cached_pit is not None
        pd.testing.assert_series_equal(cached_factors, factor_scores)
        pd.testing.assert_series_equal(cached_pit, eligibility)


class TestCacheManagement:
    """Test cache management operations."""

    def test_clear_cache(self, factor_cache, sample_returns):
        """Test clearing all cache entries."""
        config = {"method": "momentum", "lookback": 252}
        scores = pd.Series(np.random.randn(10), index=sample_returns.columns)

        # Cache some data
        factor_cache.put_factor_scores(
            scores, sample_returns, config, "2020-01-01", "2020-12-31"
        )
        assert factor_cache.get_stats()["puts"] == 1

        # Clear cache
        count = factor_cache.clear()
        assert count == 1  # One entry deleted

        # Verify cache miss after clear
        cached = factor_cache.get_factor_scores(
            sample_returns, config, "2020-01-01", "2020-12-31"
        )
        assert cached is None

    def test_stats_tracking(self, factor_cache, sample_returns):
        """Test cache statistics tracking."""
        config = {"method": "momentum", "lookback": 252}
        scores = pd.Series(np.random.randn(10), index=sample_returns.columns)

        # Initial stats
        stats = factor_cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["puts"] == 0

        # Cache miss
        factor_cache.get_factor_scores(
            sample_returns, config, "2020-01-01", "2020-12-31"
        )
        stats = factor_cache.get_stats()
        assert stats["misses"] == 1

        # Cache put
        factor_cache.put_factor_scores(
            scores, sample_returns, config, "2020-01-01", "2020-12-31"
        )
        stats = factor_cache.get_stats()
        assert stats["puts"] == 1

        # Cache hit
        factor_cache.get_factor_scores(
            sample_returns, config, "2020-01-01", "2020-12-31"
        )
        stats = factor_cache.get_stats()
        assert stats["hits"] == 1

    def test_cache_age_validation(self, cache_dir, sample_returns):
        """Test cache invalidation based on age."""
        # Create cache with 1 day max age
        cache = FactorCache(cache_dir, enabled=True, max_cache_age_days=1)

        config = {"method": "momentum", "lookback": 252}
        scores = pd.Series(np.random.randn(10), index=sample_returns.columns)

        # Cache data
        cache.put_factor_scores(
            scores, sample_returns, config, "2020-01-01", "2020-12-31"
        )

        # Modify metadata to simulate old cache
        metadata_files = list((cache_dir / "metadata").glob("*.json"))
        assert len(metadata_files) == 1

        with open(metadata_files[0]) as f:
            metadata = json.load(f)

        # Set created_at to 3 days ago
        old_date = datetime.now() - timedelta(days=3)
        metadata["created_at"] = old_date.isoformat()

        with open(metadata_files[0], "w") as f:
            json.dump(metadata, f)

        # Try to retrieve - should be invalidated
        cached = cache.get_pit_eligibility(
            sample_returns, config, "2020-01-01", "2020-12-31"
        )
        assert cached is None


class TestDisabledCache:
    """Test that disabled cache works correctly."""

    def test_disabled_cache_operations(self, cache_dir, sample_returns):
        """Test all operations work correctly when cache is disabled."""
        cache = FactorCache(cache_dir, enabled=False)

        config = {"method": "momentum", "lookback": 252}
        scores = pd.Series(np.random.randn(10), index=sample_returns.columns)

        # Put should be no-op
        cache.put_factor_scores(
            scores, sample_returns, config, "2020-01-01", "2020-12-31"
        )
        assert cache.get_stats()["puts"] == 0

        # Get should always return None
        cached = cache.get_factor_scores(
            sample_returns, config, "2020-01-01", "2020-12-31"
        )
        assert cached is None

        # Clear should return 0
        count = cache.clear()
        assert count == 0


class TestCacheCorrectnessEquivalence:
    """Test that caching doesn't change computational results."""

    def test_cached_and_uncached_results_identical(self, factor_cache, sample_returns):
        """Test cached results are identical to uncached."""
        config = {"method": "momentum", "lookback": 252}

        # Compute scores
        original_scores = pd.Series(
            np.random.randn(len(sample_returns.columns)),
            index=sample_returns.columns,
        )

        # Cache scores
        factor_cache.put_factor_scores(
            original_scores, sample_returns, config, "2020-01-01", "2020-12-31"
        )

        # Retrieve and compare
        cached_scores = factor_cache.get_factor_scores(
            sample_returns, config, "2020-01-01", "2020-12-31"
        )

        pd.testing.assert_series_equal(cached_scores, original_scores)

    def test_multiple_cache_hits_consistent(self, factor_cache, sample_returns):
        """Test multiple cache hits return consistent results."""
        config = {"method": "momentum", "lookback": 252}
        scores = pd.Series(np.random.randn(10), index=sample_returns.columns)

        # Cache
        factor_cache.put_factor_scores(
            scores, sample_returns, config, "2020-01-01", "2020-12-31"
        )

        # Retrieve multiple times
        cached1 = factor_cache.get_factor_scores(
            sample_returns, config, "2020-01-01", "2020-12-31"
        )
        cached2 = factor_cache.get_factor_scores(
            sample_returns, config, "2020-01-01", "2020-12-31"
        )
        cached3 = factor_cache.get_factor_scores(
            sample_returns, config, "2020-01-01", "2020-12-31"
        )

        pd.testing.assert_series_equal(cached1, scores)
        pd.testing.assert_series_equal(cached2, scores)
        pd.testing.assert_series_equal(cached3, scores)
        assert factor_cache.get_stats()["hits"] == 3
