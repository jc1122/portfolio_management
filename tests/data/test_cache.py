"""Tests for incremental resume caching functionality."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from portfolio_management.data import cache


def test_compute_directory_hash_empty_dir(tmp_path: Path) -> None:
    """Test hash computation for empty directory."""
    hash1 = cache.compute_directory_hash(tmp_path)
    hash2 = cache.compute_directory_hash(tmp_path)
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA256 hex digest


def test_compute_directory_hash_with_files(tmp_path: Path) -> None:
    """Test hash changes when files are added."""
    initial_hash = cache.compute_directory_hash(tmp_path, "*.csv")
    
    # Add a file
    (tmp_path / "test.csv").write_text("data")
    hash_after_add = cache.compute_directory_hash(tmp_path, "*.csv")
    
    assert hash_after_add != initial_hash


def test_compute_directory_hash_file_modification(tmp_path: Path) -> None:
    """Test hash changes when file is modified."""
    test_file = tmp_path / "test.csv"
    test_file.write_text("data")
    
    hash1 = cache.compute_directory_hash(tmp_path, "*.csv")
    
    # Modify file (mtime will change)
    time.sleep(0.01)  # Ensure mtime changes
    test_file.write_text("different data")
    
    hash2 = cache.compute_directory_hash(tmp_path, "*.csv")
    
    assert hash1 != hash2


def test_compute_directory_hash_deterministic(tmp_path: Path) -> None:
    """Test hash is deterministic for same directory state."""
    (tmp_path / "a.csv").write_text("data1")
    (tmp_path / "b.csv").write_text("data2")
    
    hash1 = cache.compute_directory_hash(tmp_path, "*.csv")
    hash2 = cache.compute_directory_hash(tmp_path, "*.csv")
    
    assert hash1 == hash2


def test_compute_stooq_index_hash_nonexistent(tmp_path: Path) -> None:
    """Test hash for nonexistent file returns empty string."""
    hash_result = cache.compute_stooq_index_hash(tmp_path / "nonexistent.csv")
    assert hash_result == ""


def test_compute_stooq_index_hash_file_exists(tmp_path: Path) -> None:
    """Test hash computation for existing file."""
    index_file = tmp_path / "index.csv"
    index_file.write_text("ticker,stem,path\nAAA.US,AAA,daily/us/aaa.us.txt")
    
    hash1 = cache.compute_stooq_index_hash(index_file)
    hash2 = cache.compute_stooq_index_hash(index_file)
    
    assert hash1 == hash2
    assert len(hash1) == 64


def test_compute_stooq_index_hash_file_changes(tmp_path: Path) -> None:
    """Test hash changes when file content changes."""
    index_file = tmp_path / "index.csv"
    index_file.write_text("ticker,stem,path\nAAA.US,AAA,daily/us/aaa.us.txt")
    
    hash1 = cache.compute_stooq_index_hash(index_file)
    
    index_file.write_text("ticker,stem,path\nBBB.US,BBB,daily/us/bbb.us.txt")
    hash2 = cache.compute_stooq_index_hash(index_file)
    
    assert hash1 != hash2


def test_load_cache_metadata_nonexistent(tmp_path: Path) -> None:
    """Test loading metadata from nonexistent file returns empty dict."""
    metadata = cache.load_cache_metadata(tmp_path / "nonexistent.json")
    assert metadata == {}


def test_load_cache_metadata_invalid_json(tmp_path: Path) -> None:
    """Test loading invalid JSON returns empty dict."""
    cache_file = tmp_path / "cache.json"
    cache_file.write_text("not valid json{}")
    
    metadata = cache.load_cache_metadata(cache_file)
    assert metadata == {}


def test_save_and_load_cache_metadata(tmp_path: Path) -> None:
    """Test saving and loading cache metadata."""
    cache_file = tmp_path / "metadata" / "cache.json"
    test_metadata = {
        "tradeable_hash": "abc123",
        "stooq_index_hash": "def456",
    }
    
    cache.save_cache_metadata(cache_file, test_metadata)
    loaded = cache.load_cache_metadata(cache_file)
    
    assert loaded == test_metadata


def test_inputs_unchanged_no_cache() -> None:
    """Test inputs considered changed when no cache exists."""
    result = cache.inputs_unchanged(
        Path("/fake/tradeable"),
        Path("/fake/index.csv"),
        {},
    )
    assert result is False


def test_inputs_unchanged_tradeable_dir_changed(tmp_path: Path) -> None:
    """Test inputs marked as changed when tradeable directory changes."""
    tradeable_dir = tmp_path / "tradeable"
    tradeable_dir.mkdir()
    index_path = tmp_path / "index.csv"
    index_path.write_text("data")
    
    # Create initial cache
    cache_metadata = cache.create_cache_metadata(tradeable_dir, index_path)
    
    # Modify tradeable directory
    (tradeable_dir / "new.csv").write_text("data")
    
    result = cache.inputs_unchanged(tradeable_dir, index_path, cache_metadata)
    assert result is False


def test_inputs_unchanged_index_changed(tmp_path: Path) -> None:
    """Test inputs marked as changed when index changes."""
    tradeable_dir = tmp_path / "tradeable"
    tradeable_dir.mkdir()
    index_path = tmp_path / "index.csv"
    index_path.write_text("original data")
    
    # Create initial cache
    cache_metadata = cache.create_cache_metadata(tradeable_dir, index_path)
    
    # Modify index
    index_path.write_text("modified data")
    
    result = cache.inputs_unchanged(tradeable_dir, index_path, cache_metadata)
    assert result is False


def test_inputs_unchanged_nothing_changed(tmp_path: Path) -> None:
    """Test inputs marked as unchanged when nothing changes."""
    tradeable_dir = tmp_path / "tradeable"
    tradeable_dir.mkdir()
    (tradeable_dir / "test.csv").write_text("data")
    
    index_path = tmp_path / "index.csv"
    index_path.write_text("index data")
    
    # Create cache based on current state
    cache_metadata = cache.create_cache_metadata(tradeable_dir, index_path)
    
    # Nothing changed
    result = cache.inputs_unchanged(tradeable_dir, index_path, cache_metadata)
    assert result is True


def test_outputs_exist_both_missing(tmp_path: Path) -> None:
    """Test outputs_exist returns False when both files missing."""
    result = cache.outputs_exist(
        tmp_path / "match.csv",
        tmp_path / "unmatched.csv",
    )
    assert result is False


def test_outputs_exist_one_missing(tmp_path: Path) -> None:
    """Test outputs_exist returns False when one file missing."""
    (tmp_path / "match.csv").write_text("data")
    
    result = cache.outputs_exist(
        tmp_path / "match.csv",
        tmp_path / "unmatched.csv",
    )
    assert result is False


def test_outputs_exist_both_present(tmp_path: Path) -> None:
    """Test outputs_exist returns True when both files present."""
    (tmp_path / "match.csv").write_text("data")
    (tmp_path / "unmatched.csv").write_text("data")
    
    result = cache.outputs_exist(
        tmp_path / "match.csv",
        tmp_path / "unmatched.csv",
    )
    assert result is True


def test_create_cache_metadata(tmp_path: Path) -> None:
    """Test creating cache metadata."""
    tradeable_dir = tmp_path / "tradeable"
    tradeable_dir.mkdir()
    (tradeable_dir / "test.csv").write_text("data")
    
    index_path = tmp_path / "index.csv"
    index_path.write_text("index data")
    
    metadata = cache.create_cache_metadata(tradeable_dir, index_path)
    
    assert "tradeable_hash" in metadata
    assert "stooq_index_hash" in metadata
    assert len(metadata["tradeable_hash"]) == 64
    assert len(metadata["stooq_index_hash"]) == 64
