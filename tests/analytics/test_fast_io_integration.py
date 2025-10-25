"""Integration tests for fast IO with PriceLoader."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from portfolio_management.analytics.returns.loaders import PriceLoader
from portfolio_management.data.io.fast_io import get_available_backends


@pytest.fixture
def price_files_dir(tmp_path: Path) -> Path:
    """Create multiple price files for testing."""
    prices_dir = tmp_path / "prices"
    prices_dir.mkdir()

    # Create test price files
    for i in range(3):
        price_file = prices_dir / f"asset_{i}.csv"
        data = {
            "date": pd.date_range("2022-01-01", periods=10, freq="D"),
            "close": [100.0 + i * 10 + j for j in range(10)],
        }
        df = pd.DataFrame(data)
        df.to_csv(price_file, index=False)

    return prices_dir


@pytest.mark.integration
def test_price_loader_with_pandas_backend(price_files_dir: Path):
    """Test PriceLoader with pandas backend (always available)."""
    loader = PriceLoader(io_backend="pandas")

    # Load a single file
    price_path = price_files_dir / "asset_0.csv"
    series = loader.load_price_file(price_path)

    assert isinstance(series, pd.Series)
    assert len(series) == 10
    assert series.iloc[0] == 100.0


@pytest.mark.integration
def test_price_loader_with_auto_backend(price_files_dir: Path):
    """Test PriceLoader with auto backend selection."""
    loader = PriceLoader(io_backend="auto")

    # Load a single file
    price_path = price_files_dir / "asset_0.csv"
    series = loader.load_price_file(price_path)

    assert isinstance(series, pd.Series)
    assert len(series) == 10
    assert series.iloc[0] == 100.0


@pytest.mark.skipif(
    "polars" not in get_available_backends(),
    reason="polars not installed",
)
@pytest.mark.integration
def test_price_loader_with_polars_backend(price_files_dir: Path):
    """Test PriceLoader with polars backend (if available)."""
    loader = PriceLoader(io_backend="polars")

    # Load a single file
    price_path = price_files_dir / "asset_0.csv"
    series = loader.load_price_file(price_path)

    assert isinstance(series, pd.Series)
    assert len(series) == 10
    assert series.iloc[0] == 100.0


@pytest.mark.skipif(
    "pyarrow" not in get_available_backends(),
    reason="pyarrow not installed",
)
@pytest.mark.integration
def test_price_loader_with_pyarrow_backend(price_files_dir: Path):
    """Test PriceLoader with pyarrow backend (if available)."""
    loader = PriceLoader(io_backend="pyarrow")

    # Load a single file
    price_path = price_files_dir / "asset_0.csv"
    series = loader.load_price_file(price_path)

    assert isinstance(series, pd.Series)
    assert len(series) == 10
    assert series.iloc[0] == 100.0


@pytest.mark.integration
def test_price_loader_backend_consistency(price_files_dir: Path):
    """Test that all available backends produce consistent results."""
    price_path = price_files_dir / "asset_0.csv"

    # Test with all available backends
    results = {}
    for backend in get_available_backends():
        loader = PriceLoader(io_backend=backend)
        series = loader.load_price_file(price_path)
        results[backend] = series

    # All backends should produce identical results
    pandas_result = results["pandas"]
    for backend, series in results.items():
        if backend != "pandas":
            pd.testing.assert_series_equal(
                pandas_result,
                series,
                check_names=False,  # Name might differ between backends
            )


@pytest.mark.integration
def test_price_loader_caching_with_fast_io(price_files_dir: Path):
    """Test that caching works correctly with fast IO backends."""
    loader = PriceLoader(io_backend="auto", cache_size=10)

    price_path = price_files_dir / "asset_0.csv"

    # Load twice - second load should be from cache
    series1 = loader.load_price_file(price_path)
    cache_info_before = loader.cache_info()

    series2 = loader.load_price_file(price_path)
    cache_info_after = loader.cache_info()

    # Both loads should produce identical results
    pd.testing.assert_series_equal(series1, series2)

    # Cache size should remain the same (hit from cache)
    assert cache_info_before["size"] == cache_info_after["size"]


@pytest.mark.integration
def test_price_loader_unavailable_backend_fallback(price_files_dir: Path):
    """Test fallback when requested backend is unavailable."""
    # This test ensures that requesting an unavailable backend doesn't crash
    # but instead falls back to pandas
    loader = PriceLoader(io_backend="polars")  # May or may not be available

    price_path = price_files_dir / "asset_0.csv"
    series = loader.load_price_file(price_path)

    # Should still work (either with polars or pandas fallback)
    assert isinstance(series, pd.Series)
    assert len(series) == 10
