"""Optional fast IO backends using Polars or PyArrow.

This module provides faster alternatives for reading CSV and Parquet files by
leveraging high-performance libraries like Polars and PyArrow. It gracefully
falls back to pandas if these dependencies are not installed, ensuring
compatibility while offering significant performance gains when available.

Key Functions:
    - read_csv_fast: Reads a CSV file, auto-selecting the best available backend.
    - read_parquet_fast: Reads a Parquet file, auto-selecting the best backend.
    - get_available_backends: Lists the currently installed and available IO backends.

Performance:
    - Polars: Typically the fastest backend for both CSV and Parquet parsing.
    - PyArrow: A strong alternative, especially for Parquet. Often installed
      as a dependency for other data science libraries.
    - Pandas: The reliable default, but slower for large files.

Usage:
    >>> import tempfile
    >>> from pathlib import Path
    >>> from portfolio_management.data.io.fast_io import read_csv_fast, get_available_backends
    >>>
    >>> # Check available backends
    >>> backends = get_available_backends()
    >>> print(f"Available backends: {backends}") # doctest: +SKIP
    >>>
    >>> with tempfile.NamedTemporaryFile(mode='w+', suffix='.csv') as tmp:
    ...     _ = tmp.write('a,b\\n1,2')
    ...     _ = tmp.seek(0)
    ...     df = read_csv_fast(tmp.name)
    >>> print(df.shape)
    (1, 2)

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
    import polars as pl

    _POLARS_AVAILABLE = True
    logger.debug("Polars backend available for fast IO.")
except ImportError:
    logger.debug("Polars not installed; falling back to pandas for IO.")

try:
    import pyarrow as pa
    import pyarrow.csv as pa_csv

    _PYARROW_AVAILABLE = True
    logger.debug("PyArrow backend available for fast IO.")
except ImportError:
    logger.debug("PyArrow not installed; falling back to pandas for IO.")

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
    """Return a list of available IO backends.

    The list always includes 'pandas' and will also contain 'polars' and/or
    'pyarrow' if they are installed in the environment.

    Returns:
        A list of backend names.

    Example:
        >>> isinstance(get_available_backends(), list)
        True
    """
    backends = ["pandas"]
    if _POLARS_AVAILABLE:
        backends.append("polars")
    if _PYARROW_AVAILABLE:
        backends.append("pyarrow")
    return backends


def is_backend_available(backend: str) -> bool:
    """Check if a specific IO backend is available.

    Args:
        backend: The name of the backend ('pandas', 'polars', 'pyarrow').

    Returns:
        True if the backend is available, False otherwise.
    """
    if backend == "pandas":
        return True
    if backend == "polars":
        return _POLARS_AVAILABLE
    if backend == "pyarrow":
        return _PYARROW_AVAILABLE
    return False


def select_backend(requested: Backend) -> str:
    """Select the best available backend based on the user's request.

    If 'auto' is requested, it selects the best available backend in the
    order of preference: Polars, PyArrow, then Pandas. If a specific
    backend is requested but unavailable, it falls back to pandas.

    Args:
        requested: The desired backend ('auto', 'pandas', 'polars', 'pyarrow').

    Returns:
        The name of the selected backend.
    """
    if requested == "auto":
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
    """Read a CSV file using the fastest available IO backend.

    This function provides a unified interface that delegates to the best
    available parsing engine (Polars, PyArrow, or pandas) while always
    returning a pandas DataFrame for API consistency.

    Args:
        path: The path to the CSV file.
        backend: The IO backend to use. Defaults to 'auto', which selects the
                 fastest available option.
        **kwargs: Additional arguments passed to the underlying read function.

    Returns:
        A pandas DataFrame with the CSV contents.

    Raises:
        FileNotFoundError: If the specified path does not exist.
        Exception: Can raise exceptions from the underlying parser if the
                   file is malformed.
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
    """Read CSV using Polars and convert to a pandas DataFrame."""
    df_pl = pl.read_csv(path, **kwargs)
    return df_pl.to_pandas()


def _read_csv_pyarrow(path: Path, **kwargs) -> pd.DataFrame:
    """Read CSV using PyArrow and convert to a pandas DataFrame."""
    table = pa_csv.read_csv(path, **kwargs)
    return table.to_pandas()


def read_parquet_fast(
    path: Path | str,
    backend: Backend = "auto",
    **kwargs,
) -> pd.DataFrame:
    """Read a Parquet file using the fastest available IO backend.

    This function provides a unified interface for reading Parquet files,
    which is a highly efficient columnar storage format. It delegates to the
    best available engine while always returning a pandas DataFrame.

    Args:
        path: The path to the Parquet file.
        backend: The IO backend to use. Defaults to 'auto'.
        **kwargs: Additional arguments passed to the underlying read function.

    Returns:
        A pandas DataFrame with the Parquet file contents.

    Raises:
        FileNotFoundError: If the specified path does not exist.
    """
    path = Path(path)
    selected = select_backend(backend)

    if selected == "polars":
        return _read_parquet_polars(path, **kwargs)

    if selected == "pyarrow":
        return _read_parquet_pyarrow(path, **kwargs)

    return _read_parquet_pandas(path, **kwargs)


def _read_parquet_pandas(path: Path, **kwargs) -> pd.DataFrame:
    """Read Parquet using pandas, which internally uses PyArrow or FastParquet."""
    return pd.read_parquet(path, **kwargs)


def _read_parquet_polars(path: Path, **kwargs) -> pd.DataFrame:
    """Read Parquet using Polars and convert to a pandas DataFrame."""
    df_pl = pl.read_parquet(path, **kwargs)
    return df_pl.to_pandas()


def _read_parquet_pyarrow(path: Path, **kwargs) -> pd.DataFrame:
    """Read Parquet using PyArrow and convert to a pandas DataFrame."""
    table = pa.parquet.read_table(path, **kwargs)
    return table.to_pandas()