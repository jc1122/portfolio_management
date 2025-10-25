"""Incremental resume support for data preparation pipeline.

This module provides caching and change detection to avoid redundant processing
when inputs haven't changed. It computes hashes of input data directories and
files to determine if downstream processing steps can be skipped.

Key Functions:
    - compute_directory_hash: Creates a hash for a directory's contents.
    - load_cache_metadata: Loads pipeline metadata from a previous run.
    - save_cache_metadata: Saves metadata for the current run.
    - inputs_unchanged: Compares current input hashes with cached ones.
    - create_cache_metadata: Generates new metadata for the current inputs.

Usage Example:
    >>> import tempfile
    >>> from pathlib import Path
    >>>
    >>> with tempfile.TemporaryDirectory() as tmpdir:
    ...     # Setup paths
    ...     tradeable_dir = Path(tmpdir) / "tradeable"
    ...     tradeable_dir.mkdir()
    ...     _ = (tradeable_dir / "a.csv").write_text("1")
    ...     stooq_index_path = Path(tmpdir) / "stooq_index.csv"
    ...     _ = stooq_index_path.write_text("2")
    ...     cache_meta_path = Path(tmpdir) / "pipeline_meta.json"
    ...
    ...     # On a subsequent run, load previous metadata
    ...     cached_meta = load_cache_metadata(cache_meta_path)
    ...
    ...     # Check if inputs have changed
    ...     if not inputs_unchanged(tradeable_dir, stooq_index_path, cached_meta):
    ...         print("Inputs have changed, re-running pipeline...")
    ...         # Create new metadata for the current run
    ...         new_meta = create_cache_metadata(tradeable_dir, stooq_index_path)
    ...         save_cache_metadata(cache_meta_path, new_meta)
    ...     else:
    ...         print("Inputs are unchanged, skipping pipeline.")
    Inputs have changed, re-running pipeline...

"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger(__name__)


def compute_directory_hash(directory: Path, pattern: str = "*.csv") -> str:
    """Compute a hash representing the state of files in a directory.

    The hash is derived from the names and modification times of all files
    matching the specified pattern. This provides a reliable way to detect
    if any file has been added, removed, or changed.

    Args:
        directory: The directory to hash.
        pattern: A glob pattern to select which files to include in the hash.

    Returns:
        A hex digest of the combined file hashes.

    Example:
        >>> import tempfile
        >>> from pathlib import Path
        >>>
        >>> with tempfile.TemporaryDirectory() as tmpdir:
        ...     p = Path(tmpdir)
        ...     _ = (p / "file1.csv").write_text("a")
        ...     _ = (p / "file2.csv").write_text("b")
        ...     print(len(compute_directory_hash(p)))
        64
    """
    hasher = hashlib.sha256()

    # Sort files for deterministic ordering
    files = sorted(directory.glob(pattern))

    for file_path in files:
        # Include file name and mtime in hash
        hasher.update(file_path.name.encode())
        hasher.update(str(file_path.stat().st_mtime).encode())

    return hasher.hexdigest()


def compute_stooq_index_hash(index_path: Path) -> str:
    """Compute the hash of the Stooq index file.

    Args:
        index_path: The path to the Stooq index CSV file.

    Returns:
        A hex digest of the file's contents, or an empty string if the
        file does not exist.
    """
    if not index_path.exists():
        return ""

    hasher = hashlib.sha256()
    hasher.update(index_path.read_bytes())
    return hasher.hexdigest()


def load_cache_metadata(cache_path: Path) -> dict[str, Any]:
    """Load cache metadata from a JSON file.

    If the file doesn't exist or is corrupted, it returns an empty dictionary.

    Args:
        cache_path: The path to the cache metadata JSON file.

    Returns:
        A dictionary of cached metadata, or an empty dict if not found or invalid.

    Raises:
        OSError: If there is an issue reading the file.
    """
    if not cache_path.exists():
        return {}

    try:
        with cache_path.open() as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        LOGGER.warning("Failed to load cache metadata from %s: %s", cache_path, e)
        return {}


def save_cache_metadata(cache_path: Path, metadata: dict[str, Any]) -> None:
    """Save cache metadata to a JSON file.

    This function will create the parent directory if it does not exist.

    Args:
        cache_path: The path to the cache metadata JSON file.
        metadata: A dictionary of metadata to save.

    Raises:
        OSError: If the file cannot be written to the specified path.

    Example:
        >>> import tempfile
        >>> from pathlib import Path
        >>>
        >>> with tempfile.TemporaryDirectory() as tmpdir:
        ...     meta = {"key": "value"}
        ...     path = Path(tmpdir) / "meta.json"
        ...     save_cache_metadata(path, meta)
        ...     assert path.exists()
    """
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with cache_path.open("w") as f:
            json.dump(metadata, f, indent=2)
        LOGGER.debug("Saved cache metadata to %s", cache_path)
    except OSError as e:
        LOGGER.warning("Failed to save cache metadata to %s: %s", cache_path, e)


def inputs_unchanged(
    tradeable_dir: Path,
    stooq_index_path: Path,
    cache_metadata: dict[str, Any],
) -> bool:
    """Check if input files have changed since the last run.

    This compares the hash of the current tradeable instruments directory and
    Stooq index with the hashes stored in the cached metadata.

    Args:
        tradeable_dir: The directory containing tradeable CSVs.
        stooq_index_path: The path to the Stooq index CSV.
        cache_metadata: Previously saved cache metadata.

    Returns:
        True if inputs are unchanged, False otherwise.
    """
    if not cache_metadata:
        LOGGER.debug("No cache metadata found - inputs considered changed")
        return False

    # Check tradeable directory hash
    current_tradeable_hash = compute_directory_hash(tradeable_dir, "*.csv")
    cached_tradeable_hash = cache_metadata.get("tradeable_hash", "")

    if current_tradeable_hash != cached_tradeable_hash:
        LOGGER.debug(
            "Tradeable directory changed (hash %s -> %s)",
            cached_tradeable_hash[:8] if cached_tradeable_hash else "N/A",
            current_tradeable_hash[:8],
        )
        return False

    # Check stooq index hash
    current_index_hash = compute_stooq_index_hash(stooq_index_path)
    cached_index_hash = cache_metadata.get("stooq_index_hash", "")

    if current_index_hash != cached_index_hash:
        LOGGER.debug(
            "Stooq index changed (hash %s -> %s)",
            cached_index_hash[:8] if cached_index_hash else "N/A",
            current_index_hash[:8],
        )
        return False

    LOGGER.info("Input files unchanged since last run - incremental resume possible")
    return True


def outputs_exist(match_report: Path, unmatched_report: Path) -> bool:
    """Check if output files exist from a previous run.

    Args:
        match_report: The path to the match report CSV.
        unmatched_report: The path to the unmatched report CSV.

    Returns:
        True if both output files exist, False otherwise.
    """
    if not match_report.exists():
        LOGGER.debug("Match report %s does not exist", match_report)
        return False

    if not unmatched_report.exists():
        LOGGER.debug("Unmatched report %s does not exist", unmatched_report)
        return False

    return True


def create_cache_metadata(
    tradeable_dir: Path,
    stooq_index_path: Path,
) -> dict[str, Any]:
    """Create cache metadata for the current run.

    This generates a dictionary containing the hashes of the input data,
    which can be saved for comparison in future runs.

    Args:
        tradeable_dir: The directory containing tradeable CSVs.
        stooq_index_path: The path to the Stooq index CSV.

    Returns:
        A dictionary of cache metadata.
    """
    return {
        "tradeable_hash": compute_directory_hash(tradeable_dir, "*.csv"),
        "stooq_index_hash": compute_stooq_index_hash(stooq_index_path),
    }