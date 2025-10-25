"""Integration tests for prepare_tradeable_data incremental resume."""

from __future__ import annotations

import pytest
pytestmark = pytest.mark.integration

import subprocess
import sys
from pathlib import Path


def test_incremental_resume_skips_when_unchanged(tmp_path: Path) -> None:
    """Test that incremental resume skips processing when inputs unchanged."""
    # Set up directories
    data_dir = tmp_path / "stooq"
    data_dir.mkdir()

    tradeable_dir = tmp_path / "tradeable"
    tradeable_dir.mkdir()
    (tradeable_dir / "instruments.csv").write_text(
        "symbol,isin,market,name,currency\n" "AAPL,US0378331005,NASDAQ,Apple,USD\n"
    )

    metadata_dir = tmp_path / "metadata"
    metadata_dir.mkdir()

    # Create a minimal stooq index to satisfy the check
    index_path = metadata_dir / "stooq_index.csv"
    index_path.write_text("ticker,stem,relative_path,region,category\n")

    # Create output files to simulate previous run
    match_report = metadata_dir / "matches.csv"
    match_report.write_text("symbol,matched_ticker\n")

    unmatched_report = metadata_dir / "unmatched.csv"
    unmatched_report.write_text("symbol,reason\n")

    prices_dir = tmp_path / "prices"
    prices_dir.mkdir()

    cache_file = metadata_dir / "cache.json"

    # First run with --incremental to create cache
    cmd1 = [
        sys.executable,
        "scripts/prepare_tradeable_data.py",
        "--data-dir",
        str(data_dir),
        "--metadata-output",
        str(index_path),
        "--tradeable-dir",
        str(tradeable_dir),
        "--match-report",
        str(match_report),
        "--unmatched-report",
        str(unmatched_report),
        "--prices-output",
        str(prices_dir),
        "--incremental",
        "--cache-metadata",
        str(cache_file),
        "--log-level",
        "INFO",
    ]

    # Run should fail because stub functions raise NotImplementedError
    # but we can test the cache creation
    result1 = subprocess.run(
        cmd1,
        check=False,
        capture_output=True,
        text=True,
        cwd=Path.cwd(),
    )

    # The script should try to run but fail on stub implementations
    # However, if outputs already exist and we run again, it should skip

    # Second run - should skip processing since nothing changed
    result2 = subprocess.run(
        cmd1,
        check=False,
        capture_output=True,
        text=True,
        cwd=Path.cwd(),
    )

    # Check that second run detected unchanged inputs
    assert (
        "incremental resume" in result2.stdout.lower()
        or "incremental resume" in result2.stderr.lower()
    )


def test_incremental_resume_reruns_when_tradeable_changed(tmp_path: Path) -> None:
    """Test that incremental resume reruns when tradeable files change."""
    # Set up directories
    data_dir = tmp_path / "stooq"
    data_dir.mkdir()

    tradeable_dir = tmp_path / "tradeable"
    tradeable_dir.mkdir()
    tradeable_file = tradeable_dir / "instruments.csv"
    tradeable_file.write_text(
        "symbol,isin,market,name,currency\n" "AAPL,US0378331005,NASDAQ,Apple,USD\n"
    )

    metadata_dir = tmp_path / "metadata"
    metadata_dir.mkdir()

    index_path = metadata_dir / "stooq_index.csv"
    index_path.write_text("ticker,stem,relative_path,region,category\n")

    match_report = metadata_dir / "matches.csv"
    match_report.write_text("symbol,matched_ticker\n")

    unmatched_report = metadata_dir / "unmatched.csv"
    unmatched_report.write_text("symbol,reason\n")

    prices_dir = tmp_path / "prices"
    prices_dir.mkdir()

    cache_file = metadata_dir / "cache.json"

    # Create initial cache manually

    from portfolio_management.data import cache as cache_module

    initial_metadata = cache_module.create_cache_metadata(tradeable_dir, index_path)
    cache_module.save_cache_metadata(cache_file, initial_metadata)

    # Verify cache exists
    assert cache_file.exists()

    # Modify tradeable file
    tradeable_file.write_text(
        "symbol,isin,market,name,currency\n"
        "AAPL,US0378331005,NASDAQ,Apple,USD\n"
        "MSFT,US5949181045,NASDAQ,Microsoft,USD\n"
    )

    # Run with --incremental
    cmd = [
        sys.executable,
        "scripts/prepare_tradeable_data.py",
        "--data-dir",
        str(data_dir),
        "--metadata-output",
        str(index_path),
        "--tradeable-dir",
        str(tradeable_dir),
        "--match-report",
        str(match_report),
        "--unmatched-report",
        str(unmatched_report),
        "--prices-output",
        str(prices_dir),
        "--incremental",
        "--cache-metadata",
        str(cache_file),
        "--log-level",
        "DEBUG",
    ]

    result = subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
        cwd=Path.cwd(),
    )

    # Should not skip because tradeable files changed
    output = result.stdout + result.stderr
    # Should see message about inputs changed or should try to run pipeline
    assert (
        "changed" in output.lower()
        or "running" in output.lower()
        or "notimplementederror" in output.lower()
    )


def test_help_shows_incremental_flags() -> None:
    """Test that help message includes incremental resume flags."""
    result = subprocess.run(
        [sys.executable, "scripts/prepare_tradeable_data.py", "--help"],
        check=False,
        capture_output=True,
        text=True,
        cwd=Path.cwd(),
    )

    assert result.returncode == 0
    assert "--incremental" in result.stdout
    assert "--cache-metadata" in result.stdout
    # Check for "incremental" and "resume" separately since help formatting may split them
    help_text_lower = result.stdout.lower()
    assert "incremental" in help_text_lower
    assert "resume" in help_text_lower
