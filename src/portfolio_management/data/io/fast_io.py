"""Optional fast IO backends using polars or pyarrow.

This module provides optional faster IO paths for reading CSV and Parquet files
using polars or pyarrow when available. Falls back gracefully to pandas if the
optional dependencies are not installed.

The fast IO backends can provide 2-5x speedups for CSV reading and even more for
Parquet files, especially beneficial for large datasets (1000+ assets, 5+ years).

Usage:
    # Check which backends are available
    from portfolio_management.data.io.fast_io import get_available_backends
    print(get_available_backends())  # ['pandas', 'polars', 'pyarrow']

    # Read CSV with automatic backend selection
    from portfolio_management.data.io.fast_io import read_csv_fast
    df = read_csv_fast('prices.csv', backend='polars')  # or 'pyarrow' or 'pandas'

    # The result is always a pandas DataFrame for compatibility
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    import pandas as pd

logger = logging.getLogger(__name__)

# Track which optional dependencies are available
_POLARS_AVAILABLE = False
_PYARROW_AVAILABLE = False

try:
    import polars as pl  # noqa: F401

    _POLARS_AVAILABLE = True
    logger.debug("Polars backend available for fast IO")
except ImportError:
    logger.debug("Polars not installed - falling back to pandas for IO")

try:
    import pyarrow as pa  # noqa: F401
    import pyarrow.csv as pa_csv  # noqa: F401

    _PYARROW_AVAILABLE = True
    logger.debug("PyArrow backend available for fast IO")
except ImportError:
    logger.debug("PyArrow not installed - falling back to pandas for IO")

# Always import pandas as the fallback
try:
    import pandas as pd
except ImportError as exc:  # pragma: no cover
    from portfolio_management.core.exceptions import DependencyNotInstalledError

    raise DependencyNotInstalledError(
        "pandas",
        context="pandas is required for all IO operations",
    ) from exc

Backend = Literal["pandas", "polars", "pyarrow", "auto"]


def get_available_backends() -> list[str]:
    """Return list of available IO backends.

    Returns:
        List of backend names: always includes 'pandas', optionally 'polars' and 'pyarrow'

    """
    backends = ["pandas"]
    if _POLARS_AVAILABLE:
        backends.append("polars")
    if _PYARROW_AVAILABLE:
        backends.append("pyarrow")
    return backends


def is_backend_available(backend: str) -> bool:
    """Check if a specific backend is available.

    Args:
        backend: Backend name ('pandas', 'polars', 'pyarrow')

    Returns:
        True if backend is available, False otherwise

    """
    if backend == "pandas":
        return True
    if backend == "polars":
        return _POLARS_AVAILABLE
    if backend == "pyarrow":
        return _PYARROW_AVAILABLE
    return False


def select_backend(requested: Backend) -> str:
    """Select the best available backend based on request.

    Args:
        requested: Requested backend ('auto', 'pandas', 'polars', 'pyarrow')

    Returns:
        Selected backend name

    Notes:
        - 'auto' selects polars > pyarrow > pandas (in order of preference)
        - If requested backend is not available, falls back to pandas with warning

    """
    if requested == "auto":
        # Auto-select best available backend
        if _POLARS_AVAILABLE:
            return "polars"
        if _PYARROW_AVAILABLE:
            return "pyarrow"
        return "pandas"

    if requested == "pandas":
        return "pandas"

    if requested == "polars":
        if _POLARS_AVAILABLE:
            return "polars"
        logger.warning(
            "Polars backend requested but not available - falling back to pandas. "
            "Install with: pip install polars",
        )
        return "pandas"

    if requested == "pyarrow":
        if _PYARROW_AVAILABLE:
            return "pyarrow"
        logger.warning(
            "PyArrow backend requested but not available - falling back to pandas. "
            "Install with: pip install pyarrow",
        )
        return "pandas"

    logger.warning(
        "Unknown backend '%s' requested - falling back to pandas",
        requested,
    )
    return "pandas"


def read_csv_fast(
    path: Path | str,
    backend: Backend = "auto",
    **kwargs,
) -> pd.DataFrame:
    """Read CSV file using fast IO backend if available.

    This function provides a unified interface for reading CSV files with
    optional fast backends (polars, pyarrow) while always returning a
    pandas DataFrame for compatibility.

    Args:
        path: Path to CSV file
        backend: IO backend to use ('auto', 'pandas', 'polars', 'pyarrow')
        **kwargs: Additional arguments passed to the underlying read function

    Returns:
        pandas DataFrame with the CSV contents

    Notes:
        - Result is always a pandas DataFrame regardless of backend
        - 'auto' selects the fastest available backend
        - Falls back to pandas if requested backend unavailable
        - Performance gains most significant for large files (100MB+)

    """
    path = Path(path)
    selected = select_backend(backend)

    if selected == "polars":
        return _read_csv_polars(path, **kwargs)

    if selected == "pyarrow":
        return _read_csv_pyarrow(path, **kwargs)

    return _read_csv_pandas(path, **kwargs)


def _read_csv_pandas(path: Path, **kwargs) -> pd.DataFrame:
    """Read CSV using pandas (default/fallback backend)."""
    return pd.read_csv(path, **kwargs)


def _read_csv_polars(path: Path, **kwargs) -> pd.DataFrame:
    """Read CSV using polars and convert to pandas.

    Polars provides significant speedups for CSV parsing, especially for
    large files with many columns. The result is converted to pandas for
    compatibility with the rest of the system.
    """
    import polars as pl

    # Read with polars
    df_pl = pl.read_csv(path, **kwargs)

    # Convert to pandas
    df_pd = df_pl.to_pandas()

    return df_pd


def _read_csv_pyarrow(path: Path, **kwargs) -> pd.DataFrame:
    """Read CSV using pyarrow and convert to pandas.

    PyArrow provides good CSV parsing performance and is often already
    installed as a pandas dependency for other operations.
    """
    import pyarrow.csv as pa_csv

    # Read with pyarrow
    table = pa_csv.read_csv(path, **kwargs)

    # Convert to pandas
    df_pd = table.to_pandas()

    return df_pd


def read_parquet_fast(
    path: Path | str,
    backend: Backend = "auto",
    **kwargs,
) -> pd.DataFrame:
    """Read Parquet file using fast IO backend if available.

    Parquet is a columnar storage format that can provide significant
    speedups over CSV for large datasets. This function provides a unified
    interface for reading Parquet files with optional fast backends.

    Args:
        path: Path to Parquet file
        backend: IO backend to use ('auto', 'pandas', 'polars', 'pyarrow')
        **kwargs: Additional arguments passed to the underlying read function

    Returns:
        pandas DataFrame with the Parquet contents

    Notes:
        - Result is always a pandas DataFrame regardless of backend
        - Parquet reading is typically 5-10x faster than CSV
        - PyArrow is the recommended backend for Parquet (often default in pandas)
        - Polars also provides excellent Parquet support

    """
    path = Path(path)
    selected = select_backend(backend)

    if selected == "polars":
        return _read_parquet_polars(path, **kwargs)

    if selected == "pyarrow":
        return _read_parquet_pyarrow(path, **kwargs)

    return _read_parquet_pandas(path, **kwargs)


def _read_parquet_pandas(path: Path, **kwargs) -> pd.DataFrame:
    """Read Parquet using pandas (uses pyarrow or fastparquet under the hood)."""
    return pd.read_parquet(path, **kwargs)


def _read_parquet_polars(path: Path, **kwargs) -> pd.DataFrame:
    """Read Parquet using polars and convert to pandas."""
    import polars as pl

    # Read with polars
    df_pl = pl.read_parquet(path, **kwargs)

    # Convert to pandas
    df_pd = df_pl.to_pandas()

    return df_pd


def _read_parquet_pyarrow(path: Path, **kwargs) -> pd.DataFrame:
    """Read Parquet using pyarrow and convert to pandas."""
    import pyarrow.parquet as pq

    # Read with pyarrow
    table = pq.read_table(path, **kwargs)

    # Convert to pandas
    df_pd = table.to_pandas()

    return df_pd
