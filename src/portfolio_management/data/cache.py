"""Incremental resume support for data preparation pipeline.

This module provides caching and change detection to avoid redundant processing
when inputs haven't changed.
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
    
    Args:
        directory: Directory to hash
        pattern: Glob pattern for files to include
        
    Returns:
        Hex digest of combined file hashes
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
    """Compute hash of Stooq index file.
    
    Args:
        index_path: Path to stooq index CSV
        
    Returns:
        Hex digest of file contents
    """
    if not index_path.exists():
        return ""
        
    hasher = hashlib.sha256()
    hasher.update(index_path.read_bytes())
    return hasher.hexdigest()


def load_cache_metadata(cache_path: Path) -> dict[str, Any]:
    """Load cache metadata from JSON file.
    
    Args:
        cache_path: Path to cache metadata JSON
        
    Returns:
        Dictionary of cached metadata, or empty dict if not found
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
    """Save cache metadata to JSON file.
    
    Args:
        cache_path: Path to cache metadata JSON  
        metadata: Dictionary of metadata to save
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
    """Check if input files have changed since last run.
    
    Args:
        tradeable_dir: Directory containing tradeable CSVs
        stooq_index_path: Path to stooq index CSV
        cache_metadata: Previously saved cache metadata
        
    Returns:
        True if inputs are unchanged, False otherwise
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
            cached_tradeable_hash[:8],
            current_tradeable_hash[:8],
        )
        return False
        
    # Check stooq index hash
    current_index_hash = compute_stooq_index_hash(stooq_index_path)
    cached_index_hash = cache_metadata.get("stooq_index_hash", "")
    
    if current_index_hash != cached_index_hash:
        LOGGER.debug(
            "Stooq index changed (hash %s -> %s)",
            cached_index_hash[:8],
            current_index_hash[:8],
        )
        return False
        
    LOGGER.info("Input files unchanged since last run - incremental resume possible")
    return True


def outputs_exist(match_report: Path, unmatched_report: Path) -> bool:
    """Check if output files exist from previous run.
    
    Args:
        match_report: Path to match report CSV
        unmatched_report: Path to unmatched report CSV
        
    Returns:
        True if both outputs exist, False otherwise
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
    """Create cache metadata for current run.
    
    Args:
        tradeable_dir: Directory containing tradeable CSVs
        stooq_index_path: Path to stooq index CSV
        
    Returns:
        Dictionary of cache metadata
    """
    return {
        "tradeable_hash": compute_directory_hash(tradeable_dir, "*.csv"),
        "stooq_index_hash": compute_stooq_index_hash(stooq_index_path),
    }
