"""Tests for optional fast IO backends (polars, pyarrow)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from portfolio_management.data.io.fast_io import (
    get_available_backends,
    is_backend_available,
    read_csv_fast,
    select_backend,
)


@pytest.fixture
def sample_csv(tmp_path: Path) -> Path:
    """Create a sample CSV file for testing."""
    csv_path = tmp_path / "sample.csv"
    data = {
        "date": ["2022-01-01", "2022-01-02", "2022-01-03"],
        "close": [100.0, 101.5, 102.3],
        "volume": [1000, 1200, 1100],
    }
    df = pd.DataFrame(data)
    df.to_csv(csv_path, index=False)
    return csv_path


@pytest.mark.integration
def test_get_available_backends():
    """Test that pandas is always available."""
    backends = get_available_backends()
    assert "pandas" in backends
    assert isinstance(backends, list)
    # polars and pyarrow may or may not be available


@pytest.mark.integration
def test_is_backend_available():
    """Test backend availability checks."""
    assert is_backend_available("pandas") is True
    # polars and pyarrow availability depends on installation
    assert isinstance(is_backend_available("polars"), bool)
    assert isinstance(is_backend_available("pyarrow"), bool)
    assert is_backend_available("nonexistent") is False


@pytest.mark.integration
def test_select_backend_pandas():
    """Test selecting pandas backend."""
    assert select_backend("pandas") == "pandas"


@pytest.mark.integration
def test_select_backend_auto():
    """Test auto-selection of backend."""
    selected = select_backend("auto")
    assert selected in ["pandas", "polars", "pyarrow"]


@pytest.mark.integration
def test_select_backend_unavailable_fallback():
    """Test that unavailable backends fall back to pandas."""
    # Request a backend that might not be available
    selected = select_backend("polars")
    assert selected in ["pandas", "polars"]  # Falls back if not available

    selected = select_backend("pyarrow")
    assert selected in ["pandas", "pyarrow"]  # Falls back if not available


@pytest.mark.integration
def test_read_csv_fast_pandas(sample_csv: Path):
    """Test reading CSV with pandas backend."""
    df = read_csv_fast(sample_csv, backend="pandas")
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 3
    assert "date" in df.columns
    assert "close" in df.columns
    assert df["close"].iloc[0] == 100.0


@pytest.mark.integration
def test_read_csv_fast_auto(sample_csv: Path):
    """Test reading CSV with auto backend selection."""
    df = read_csv_fast(sample_csv, backend="auto")
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 3
    assert "date" in df.columns
    assert "close" in df.columns


@pytest.mark.skipif(
    not is_backend_available("polars"),
    reason="polars not installed",
)
@pytest.mark.integration
def test_read_csv_fast_polars(sample_csv: Path):
    """Test reading CSV with polars backend (if available)."""
    df = read_csv_fast(sample_csv, backend="polars")
    assert isinstance(df, pd.DataFrame)  # Always returns pandas DataFrame
    assert len(df) == 3
    assert "date" in df.columns
    assert "close" in df.columns
    assert df["close"].iloc[0] == 100.0


@pytest.mark.skipif(
    not is_backend_available("pyarrow"),
    reason="pyarrow not installed",
)
@pytest.mark.integration
def test_read_csv_fast_pyarrow(sample_csv: Path):
    """Test reading CSV with pyarrow backend (if available)."""
    df = read_csv_fast(sample_csv, backend="pyarrow")
    assert isinstance(df, pd.DataFrame)  # Always returns pandas DataFrame
    assert len(df) == 3
    assert "date" in df.columns
    assert "close" in df.columns
    assert df["close"].iloc[0] == 100.0


@pytest.mark.integration
def test_read_csv_fast_with_usecols(sample_csv: Path):
    """Test reading CSV with column selection."""
    df = read_csv_fast(sample_csv, backend="pandas", usecols=["date", "close"])
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 3
    assert "date" in df.columns
    assert "close" in df.columns
    assert "volume" not in df.columns


@pytest.mark.integration
def test_backend_consistency(sample_csv: Path):
    """Test that all backends produce identical results."""
    df_pandas = read_csv_fast(sample_csv, backend="pandas")

    backends_to_test = ["pandas"]
    if is_backend_available("polars"):
        backends_to_test.append("polars")
    if is_backend_available("pyarrow"):
        backends_to_test.append("pyarrow")

    for backend in backends_to_test[1:]:  # Skip pandas since it's the baseline
        df_other = read_csv_fast(sample_csv, backend=backend)

        # Compare shape
        assert df_other.shape == df_pandas.shape, f"{backend} produced different shape"

        # Compare columns
        assert list(df_other.columns) == list(
            df_pandas.columns
        ), f"{backend} produced different columns"

        # Compare values (allowing for floating point differences)
        pd.testing.assert_frame_equal(
            df_pandas,
            df_other,
            check_dtype=False,  # Allow dtype differences between backends
        )
