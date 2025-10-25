"""Tests for the return calculation pipeline."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
pytestmark = pytest.mark.integration

from portfolio_management.analytics.returns import (
    PriceLoader,
    ReturnCalculator,
    ReturnConfig,
    ReturnSummary,
)
from src.portfolio_management.assets.selection.selection import SelectedAsset


@pytest.fixture
def price_loader() -> PriceLoader:
    return PriceLoader()


@pytest.fixture
def return_calculator() -> ReturnCalculator:
    return ReturnCalculator()


@pytest.fixture
def sample_asset() -> SelectedAsset:
    return SelectedAsset(
        symbol="TEST.US",
        isin="US0000000000",
        name="Test Equity Fund",
        market="US",
        region="North America",
        currency="USD",
        category="etf",
        price_start="2022-01-03",
        price_end="2022-01-10",
        price_rows=5,
        data_status="ok",
        data_flags="",
        stooq_path="test.us.txt",
        resolved_currency="USD",
        currency_status="matched",
    )


@pytest.fixture
def prices_dir(tmp_path: Path) -> Path:
    prices_dir = tmp_path / "prices"
    prices_dir.mkdir()
    price_file = prices_dir / "test.us.txt"
    price_file.write_text(
        "<TICKER>,<PER>,<DATE>,<TIME>,<OPEN>,<HIGH>,<LOW>,<CLOSE>,<VOL>,<OPENINT>\n"
        "TEST.US,D,20220103,000000,100,102,99,101,1000,0\n"
        "TEST.US,D,20220104,000000,101,103,100,102,1200,0\n"
        "TEST.US,D,20220105,000000,102,105,101,104,1500,0\n"
        "TEST.US,D,20220106,000000,104,105,102,104,900,0\n"
        "TEST.US,D,20220107,000000,103,106,102,105,850,0\n",
    )
    return prices_dir


def test_return_config_validation() -> None:
    config = ReturnConfig.default()
    config.validate()  # should not raise

    with pytest.raises(ValueError):
        ReturnConfig(method="invalid").validate()

    with pytest.raises(ValueError):
        ReturnConfig(align_method="sideways").validate()

    with pytest.raises(ValueError):
        ReturnConfig(min_coverage=1.5).validate()


class TestPriceLoader:
    def test_load_price_file_sorts_and_filters(
        self, price_loader: PriceLoader, prices_dir: Path
    ) -> None:
        price_path = prices_dir / "test.us.txt"
        prices = price_loader.load_price_file(price_path)

        assert list(prices.index) == sorted(prices.index)
        assert (prices > 0).all()

    def test_load_price_file_drops_non_positive(
        self, price_loader: PriceLoader, prices_dir: Path
    ) -> None:
        bad_path = prices_dir / "bad.us.txt"
        bad_path.write_text(
            "<TICKER>,<PER>,<DATE>,<TIME>,<OPEN>,<HIGH>,<LOW>,<CLOSE>,<VOL>,<OPENINT>\n"
            "BAD.US,D,20220103,000000,100,102,99,-1,1000,0\n"
            "BAD.US,D,20220104,000000,101,103,100,0,1200,0\n"
            "BAD.US,D,20220105,000000,102,105,101,104,1500,0\n",
        )

        prices = price_loader.load_price_file(bad_path)
        assert len(prices) == 1
        assert np.isclose(prices.iloc[0], 104)

    def test_load_price_file_csv(
        self, price_loader: PriceLoader, tmp_path: Path
    ) -> None:
        csv_path = tmp_path / "sample.csv"
        csv_path.write_text(
            "date,close\n" "2022-01-03,100\n" "2022-01-04,101\n",
        )

        prices = price_loader.load_price_file(csv_path)
        assert isinstance(prices, pd.Series)
        assert prices.index[0] == pd.Timestamp("2022-01-03")
        assert prices.iloc[-1] == 101

    def test_load_multiple_prices_missing_file(
        self,
        price_loader: PriceLoader,
        prices_dir: Path,
        sample_asset: SelectedAsset,
    ) -> None:
        sample_asset.stooq_path = "missing.txt"
        df = price_loader.load_multiple_prices([sample_asset], prices_dir)
        assert df.empty

    def test_cache_bounds_eviction(self, tmp_path: Path) -> None:
        """Test that cache evicts oldest entries when full."""
        # Create a loader with small cache
        loader = PriceLoader(cache_size=3)
        prices_dir = tmp_path / "prices"
        prices_dir.mkdir()

        # Create 5 test price files
        for i in range(5):
            price_file = prices_dir / f"asset{i}.csv"
            price_file.write_text(
                f"date,close\n2022-01-03,{100 + i}\n2022-01-04,{101 + i}\n"
            )

        # Load files to fill and overflow cache
        paths = [prices_dir / f"asset{i}.csv" for i in range(5)]
        for path in paths:
            loader._load_price_with_cache(path)

        # Check cache size is bounded
        cache_info = loader.cache_info()
        assert cache_info["size"] == 3
        assert cache_info["maxsize"] == 3

        # Verify LRU eviction - first 2 files should be evicted
        with loader._cache_lock:
            assert paths[0] not in loader._cache
            assert paths[1] not in loader._cache
            assert paths[2] in loader._cache
            assert paths[3] in loader._cache
            assert paths[4] in loader._cache

    def test_cache_lru_ordering(self, tmp_path: Path) -> None:
        """Test that accessing cached entries updates LRU order."""
        loader = PriceLoader(cache_size=3)
        prices_dir = tmp_path / "prices"
        prices_dir.mkdir()

        # Create test files
        for i in range(4):
            price_file = prices_dir / f"asset{i}.csv"
            price_file.write_text(f"date,close\n2022-01-03,{100 + i}\n")

        paths = [prices_dir / f"asset{i}.csv" for i in range(4)]

        # Load first 3 files (fills cache)
        for i in range(3):
            loader._load_price_with_cache(paths[i])

        # Access first file again (should move it to end)
        loader._load_price_with_cache(paths[0])

        # Load 4th file (should evict paths[1], not paths[0])
        loader._load_price_with_cache(paths[3])

        with loader._cache_lock:
            assert paths[0] in loader._cache  # Recently accessed
            assert paths[1] not in loader._cache  # Evicted (oldest)
            assert paths[2] in loader._cache
            assert paths[3] in loader._cache

    def test_cache_disabled_when_size_zero(self, tmp_path: Path) -> None:
        """Test that setting cache_size=0 disables caching."""
        loader = PriceLoader(cache_size=0)
        prices_dir = tmp_path / "prices"
        prices_dir.mkdir()

        price_file = prices_dir / "asset.csv"
        price_file.write_text("date,close\n2022-01-03,100\n")

        # Load file multiple times
        for _ in range(3):
            loader._load_price_with_cache(price_file)

        # Cache should remain empty
        cache_info = loader.cache_info()
        assert cache_info["size"] == 0
        assert cache_info["maxsize"] == 0

    def test_clear_cache(self, tmp_path: Path) -> None:
        """Test that clear_cache empties the cache."""
        loader = PriceLoader(cache_size=10)
        prices_dir = tmp_path / "prices"
        prices_dir.mkdir()

        # Load some files
        for i in range(5):
            price_file = prices_dir / f"asset{i}.csv"
            price_file.write_text(f"date,close\n2022-01-03,{100 + i}\n")
            loader._load_price_with_cache(price_file)

        # Verify cache has entries
        assert loader.cache_info()["size"] == 5

        # Clear cache
        loader.clear_cache()

        # Verify cache is empty
        assert loader.cache_info()["size"] == 0

    def test_cache_thread_safety(self, tmp_path: Path) -> None:
        """Test that cache operations are thread-safe."""
        import concurrent.futures

        loader = PriceLoader(cache_size=10, max_workers=4)
        prices_dir = tmp_path / "prices"
        prices_dir.mkdir()

        # Create multiple price files
        num_files = 20
        for i in range(num_files):
            price_file = prices_dir / f"asset{i}.csv"
            price_file.write_text(f"date,close\n2022-01-03,{100 + i}\n")

        paths = [prices_dir / f"asset{i}.csv" for i in range(num_files)]

        # Load files concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(loader._load_price_with_cache, path) for path in paths
            ]
            results = [f.result() for f in futures]

        # All files should have been loaded successfully
        assert all(not series.empty for series in results)

        # Cache should be bounded
        cache_info = loader.cache_info()
        assert cache_info["size"] <= cache_info["maxsize"]

    def test_cache_empty_series_not_cached(self, tmp_path: Path) -> None:
        """Test that empty series are not cached."""
        loader = PriceLoader(cache_size=10)
        prices_dir = tmp_path / "prices"
        prices_dir.mkdir()

        # Create a file that will result in empty series after filtering
        bad_file = prices_dir / "bad.csv"
        bad_file.write_text("date,close\n2022-01-03,-1\n2022-01-04,0\n")

        loader._load_price_with_cache(bad_file)

        # Empty series should not be cached
        assert loader.cache_info()["size"] == 0

    def test_stress_many_unique_files(self, tmp_path: Path) -> None:
        """Stress test: load thousands of unique files and verify memory bounds."""
        # Use smaller cache for faster test
        loader = PriceLoader(cache_size=100, max_workers=4)
        prices_dir = tmp_path / "prices"
        prices_dir.mkdir()

        # Create many unique files (simulating wide universe workflow)
        num_files = 500
        for i in range(num_files):
            price_file = prices_dir / f"asset{i:04d}.csv"
            price_file.write_text(
                f"date,close\n2022-01-03,{100 + i % 100}\n2022-01-04,{101 + i % 100}\n"
            )

        paths = [prices_dir / f"asset{i:04d}.csv" for i in range(num_files)]

        # Load all files
        for path in paths:
            loader._load_price_with_cache(path)

        # Cache should be bounded to cache_size
        cache_info = loader.cache_info()
        assert cache_info["size"] == 100
        assert cache_info["maxsize"] == 100

        # Most recently loaded files should be in cache
        with loader._cache_lock:
            # Last 100 files should be cached
            for i in range(num_files - 100, num_files):
                assert paths[i] in loader._cache
            # Earlier files should have been evicted
            assert paths[0] not in loader._cache


class TestReturnCalculator:
    @pytest.fixture
    def prices_df(self) -> pd.DataFrame:
        return pd.DataFrame(
            {"TEST.US": [100, 101, 102, 101.5, 103]},
            index=pd.to_datetime(
                [
                    "2022-01-03",
                    "2022-01-04",
                    "2022-01-05",
                    "2022-01-06",
                    "2022-01-07",
                ],
            ),
        )

    def test_calculate_simple_returns(
        self,
        return_calculator: ReturnCalculator,
        prices_df: pd.DataFrame,
    ) -> None:
        config = ReturnConfig(method="simple")
        returns = return_calculator.calculate_returns(prices_df, config)
        assert "TEST.US" in returns.columns
        assert len(returns) == 4
        assert np.isclose(returns.iloc[0, 0], 0.01)

    def test_calculate_log_returns(
        self,
        return_calculator: ReturnCalculator,
        prices_df: pd.DataFrame,
    ) -> None:
        config = ReturnConfig(method="log")
        returns = return_calculator.calculate_returns(prices_df, config)
        assert np.isclose(returns.iloc[0, 0], np.log(101 / 100))

    def test_calculate_excess_returns(
        self,
        return_calculator: ReturnCalculator,
        prices_df: pd.DataFrame,
    ) -> None:
        config = ReturnConfig(method="excess", risk_free_rate=0.05)
        returns = return_calculator.calculate_returns(prices_df, config)
        daily_rf = (1 + 0.05) ** (1 / 252) - 1
        assert np.isclose(returns.iloc[0, 0], 0.01 - daily_rf)

    def test_calculate_returns_respects_min_periods(
        self,
        return_calculator: ReturnCalculator,
        prices_df: pd.DataFrame,
    ) -> None:
        config = ReturnConfig(method="simple", min_periods=10)
        returns = return_calculator.calculate_returns(prices_df, config)
        assert returns.empty

    def test_handle_missing_interpolate_limit(
        self,
        return_calculator: ReturnCalculator,
    ) -> None:
        df = pd.DataFrame(
            {
                "TEST.US": [
                    100,
                    np.nan,
                    np.nan,
                    np.nan,
                    103,
                ],
            },
            index=pd.to_datetime(
                [
                    "2022-01-03",
                    "2022-01-04",
                    "2022-01-05",
                    "2022-01-06",
                    "2022-01-07",
                ],
            ),
        )
        interpolated = return_calculator._handle_missing_interpolate(df, max_days=1)
        assert not np.isnan(interpolated.iloc[1, 0])
        assert np.isnan(interpolated.iloc[2, 0])

    def test_align_dates_business_days(
        self,
        return_calculator: ReturnCalculator,
    ) -> None:
        returns = pd.DataFrame(
            {
                "A": {
                    pd.Timestamp("2022-01-03"): 0.01,
                    pd.Timestamp("2022-01-05"): 0.02,
                },
            },
        )
        config = ReturnConfig(reindex_to_business_days=True)
        aligned = return_calculator._align_dates(returns, config)
        assert pd.Timestamp("2022-01-04") in aligned.index

    def test_resample_to_frequency(self, return_calculator: ReturnCalculator) -> None:
        returns = pd.DataFrame(
            {
                "TEST.US": [0.01, 0.02, 0.03, 0.04, 0.05],
            },
            index=pd.date_range("2022-01-03", periods=5, freq="B"),
        )
        resampled = return_calculator._resample_to_frequency(
            returns, "weekly", "simple"
        )
        assert len(resampled) == 1
        assert np.isclose(resampled.iloc[0, 0], (1.01 * 1.02 * 1.03 * 1.04 * 1.05) - 1)

    def test_apply_coverage_filter(self, return_calculator: ReturnCalculator) -> None:
        returns = pd.DataFrame(
            {
                "KEEP": [0.01, 0.02, 0.03, 0.02],
                "DROP": [0.01, np.nan, np.nan, np.nan],
            },
            index=pd.date_range("2022-01-03", periods=4, freq="B"),
        )
        filtered = return_calculator._apply_coverage_filter(returns, min_coverage=0.75)
        assert list(filtered.columns) == ["KEEP"]

    def test_load_and_prepare_populates_summary(
        self,
        return_calculator: ReturnCalculator,
        prices_dir: Path,
        sample_asset: SelectedAsset,
    ) -> None:
        config = ReturnConfig.default()
        returns = return_calculator.load_and_prepare([sample_asset], prices_dir, config)
        assert not returns.empty

        summary = return_calculator.latest_summary
        assert isinstance(summary, ReturnSummary)
        assert "TEST.US" in summary.mean_returns.index
        assert summary.correlation.shape == (1, 1)
