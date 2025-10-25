"""Stooq data ingestion and indexing utilities.

This module provides functions to scan a directory of Stooq data files,
parse their metadata from file paths, and build a structured index. This
index is a critical first step in the data preparation pipeline, enabling
efficient lookup and processing of price data.

Key Functions:
    - build_stooq_index: The main entry point to create an index of all
      Stooq price files.
    - derive_region_and_category: A helper to infer metadata from file paths.

Usage Example:
    >>> from pathlib import Path
    >>>
    >>> # Create a dummy data directory
    >>> data_dir = Path("stooq_data")
    >>> data_dir.mkdir(exist_ok=True)
    >>> (data_dir / "daily").mkdir(exist_ok=True)
    >>> (data_dir / "daily" / "us").mkdir(exist_ok=True)
    >>> (data_dir / "daily" / "us" / "nasdaq").mkdir(exist_ok=True)
    >>> (data_dir / "daily" / "us" / "nasdaq" / "aapl.us.txt").write_text("...")
    3
    >>>
    >>> # Build the index
    >>> index = build_stooq_index(data_dir)
    >>> print(index[0].ticker)
    AAPL.US
    >>> print(index[0].region)
    us
    >>> print(index[0].category)
    nasdaq
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from portfolio_management.core.exceptions import DataDirectoryNotFoundError
from portfolio_management.core.utils import _run_in_parallel
from portfolio_management.data.models import StooqFile

LOGGER = logging.getLogger(__name__)

# Path structure for Stooq daily data:
#   {root}/data/daily/{region}/{category...}/{ticker}.txt
DAILY_INDEX_OFFSET = 1  # component immediately after "daily" gives the region
DAILY_CATEGORY_OFFSET = 2  # components between region and file describe category
MIN_PARTS_FOR_CATEGORY = 2


def _scan_directory(base_dir: Path, start_dir: Path) -> list[str]:
    """Scan a directory tree and return relative *.txt paths."""
    local_paths: list[str] = []
    try:
        for root, dirs, files in os.walk(start_dir, followlinks=False):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for file_name in files:
                if file_name.startswith(".") or not file_name.lower().endswith(".txt"):
                    continue
                full_path = Path(root) / file_name
                try:
                    relative = full_path.relative_to(base_dir)
                except ValueError:
                    continue
                if any(part.startswith(".") for part in relative.parts):
                    continue
                local_paths.append(relative.as_posix())
    except OSError as exc:
        LOGGER.warning("Unable to scan %s: %s", start_dir, exc)
    return local_paths


def _collect_relative_paths(base_dir: Path, max_workers: int) -> list[str]:
    """Collect relative *.txt paths within the Stooq tree."""
    try:
        entries = [
            entry for entry in base_dir.iterdir() if not entry.name.startswith(".")
        ]
    except OSError as exc:
        LOGGER.warning("Unable to iterate %s: %s", base_dir, exc)
        return []

    rel_paths = [
        entry.relative_to(base_dir).as_posix()
        for entry in entries
        if entry.is_file() and entry.suffix.lower() == ".txt"
    ]

    directories = [entry for entry in entries if entry.is_dir()]
    if directories:
        worker_count = max(1, max_workers)
        results = _run_in_parallel(
            _scan_directory,
            [(base_dir, directory) for directory in directories],
            worker_count,
            preserve_order=False,
        )
        for result in results:
            rel_paths.extend(result)

    rel_paths.sort()
    return rel_paths


def derive_region_and_category(rel_path: Path) -> tuple[str, str]:
    """Infer region and category from the relative path within the tree.

    Parses a file path to extract structured metadata based on conventions
    of the Stooq data layout.

    Args:
        rel_path: The relative path of a Stooq data file.

    Returns:
        A tuple containing the inferred region and category.

    Example:
        >>> from pathlib import Path
        >>> p = Path("daily/us/nasdaq stocks/aapl.us.txt")
        >>> derive_region_and_category(p)
        ('us', 'nasdaq stocks')
    """
    parts = list(rel_path.parts)
    region = ""
    category = ""
    if "daily" in parts:
        idx = parts.index("daily")
        if idx + DAILY_INDEX_OFFSET < len(parts):
            region = parts[idx + DAILY_INDEX_OFFSET]
        if idx + DAILY_CATEGORY_OFFSET < len(parts):
            category = "/".join(parts[idx + DAILY_CATEGORY_OFFSET : -1])
    else:
        if parts:
            region = parts[0]
        if len(parts) > MIN_PARTS_FOR_CATEGORY:
            category = "/".join(parts[1:-1])
    return region, category


def build_stooq_index(
    data_dir: Path,
    max_workers: int | None = None,
) -> list[StooqFile]:
    """Create an index describing all unpacked Stooq price files.

    Scans the data directory in parallel, collects all `.txt` files, and
    builds a list of `StooqFile` objects containing metadata for each file.

    Args:
        data_dir: The root directory of the unpacked Stooq data.
        max_workers: The maximum number of parallel workers to use for scanning.
                     Defaults to the number of CPU cores.

    Returns:
        A list of `StooqFile` objects, each representing a data file.

    Raises:
        DataDirectoryNotFoundError: If the specified `data_dir` does not exist.
    """
    if not data_dir.exists():
        raise DataDirectoryNotFoundError(data_dir)

    workers = max(1, max_workers or os.cpu_count() or 1)
    relative_paths = _collect_relative_paths(data_dir, workers)

    entries: list[StooqFile] = []
    for rel_path_str in relative_paths:
        rel_path = Path(rel_path_str)
        ticker = rel_path.stem.upper()
        region, category = derive_region_and_category(rel_path)
        entries.append(
            StooqFile(
                ticker=ticker,
                stem=rel_path.stem.upper(),
                rel_path=rel_path_str,
                region=region,
                category=category,
            ),
        )

    LOGGER.info("Indexed %s Stooq files from %s", len(entries), data_dir)
    return entries