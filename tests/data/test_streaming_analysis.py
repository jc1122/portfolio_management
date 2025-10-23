"""Tests for streaming diagnostics functionality in analysis module."""

import pathlib
import tempfile

from portfolio_management.data.analysis.analysis import (
    _stream_stooq_file_for_diagnostics,
    summarize_price_file,
)
from portfolio_management.data.models import StooqFile


def create_test_file(file_path: pathlib.Path, content: str) -> None:
    """Helper to create a test file with given content."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w") as f:
        f.write(content)


def test_stream_stooq_file_missing():
    """Test streaming with missing file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        non_existent = pathlib.Path(tmpdir) / "missing.txt"
        diagnostics, status = _stream_stooq_file_for_diagnostics(non_existent)

        assert status == "missing_file"
        assert diagnostics["data_status"] == "missing"
        assert diagnostics["price_rows"] == "0"


def test_stream_stooq_file_empty():
    """Test streaming with empty file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        empty_file = pathlib.Path(tmpdir) / "empty.txt"
        create_test_file(empty_file, "")

        diagnostics, status = _stream_stooq_file_for_diagnostics(empty_file)

        assert status == "empty"
        assert diagnostics["data_status"] == "empty"


def test_stream_stooq_file_clean_data():
    """Test streaming with clean data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = pathlib.Path(tmpdir) / "test.txt"
        content = """TEST,D,20200101,000000,100.0,105.0,95.0,102.0,10000,0
TEST,D,20200102,000000,102.0,108.0,100.0,106.0,12000,0
TEST,D,20200103,000000,106.0,110.0,104.0,108.0,15000,0"""
        create_test_file(test_file, content)

        diagnostics, status = _stream_stooq_file_for_diagnostics(test_file)

        assert status == "ok"
        assert diagnostics["data_status"] == "ok"
        assert diagnostics["price_start"] == "2020-01-01"
        assert diagnostics["price_end"] == "2020-01-03"
        assert diagnostics["price_rows"] == "3"
        assert diagnostics["data_flags"] == ""


def test_stream_stooq_file_with_header():
    """Test streaming handles header row correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = pathlib.Path(tmpdir) / "test.txt"
        # Use full Stooq format with header-like first row
        content = """date,close,volume,ticker,type,time,open,high,low,openint
TEST,D,20200101,000000,100.0,105.0,95.0,102.0,10000,0
TEST,D,20200102,000000,102.0,108.0,100.0,106.0,12000,0"""
        create_test_file(test_file, content)

        diagnostics, status = _stream_stooq_file_for_diagnostics(test_file)

        assert status == "ok"
        assert diagnostics["price_rows"] == "2"


def test_stream_stooq_file_zero_volume():
    """Test detection of zero volume."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = pathlib.Path(tmpdir) / "test.txt"
        content = """TEST,D,20200101,000000,100.0,105.0,95.0,102.0,0,0
TEST,D,20200102,000000,102.0,108.0,100.0,106.0,0,0
TEST,D,20200103,000000,106.0,110.0,104.0,108.0,0,0"""
        create_test_file(test_file, content)

        diagnostics, status = _stream_stooq_file_for_diagnostics(test_file)

        assert status == "ok"
        assert "zero_volume=3" in diagnostics["data_flags"]
        assert "zero_volume_ratio=1.0000" in diagnostics["data_flags"]
        assert "zero_volume_severity=critical" in diagnostics["data_flags"]


def test_stream_stooq_file_invalid_dates():
    """Test detection of invalid dates."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = pathlib.Path(tmpdir) / "test.txt"
        content = """TEST,D,20200101,000000,100.0,105.0,95.0,102.0,10000,0
TEST,D,invalid,000000,102.0,108.0,100.0,106.0,12000,0
TEST,D,20200103,000000,106.0,110.0,104.0,108.0,15000,0"""
        create_test_file(test_file, content)

        diagnostics, status = _stream_stooq_file_for_diagnostics(test_file)

        assert "invalid_rows=1" in diagnostics["data_flags"]


def test_stream_stooq_file_non_numeric_prices():
    """Test detection of non-numeric prices."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = pathlib.Path(tmpdir) / "test.txt"
        # Column order: ticker, per, date, time, open, high, low, close, volume, openint
        content = """TEST,D,20200101,000000,100.0,105.0,95.0,invalid,10000,0
TEST,D,20200102,000000,102.0,108.0,100.0,106.0,12000,0"""
        create_test_file(test_file, content)

        diagnostics, status = _stream_stooq_file_for_diagnostics(test_file)

        assert "non_numeric_prices=1" in diagnostics["data_flags"]


def test_stream_stooq_file_non_positive_close():
    """Test detection of non-positive close prices."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = pathlib.Path(tmpdir) / "test.txt"
        content = """TEST,D,20200101,000000,100.0,105.0,95.0,-5.0,10000,0
TEST,D,20200102,000000,102.0,108.0,100.0,0,12000,0
TEST,D,20200103,000000,106.0,110.0,104.0,108.0,15000,0"""
        create_test_file(test_file, content)

        diagnostics, status = _stream_stooq_file_for_diagnostics(test_file)

        assert "non_positive_close=2" in diagnostics["data_flags"]


def test_stream_stooq_file_duplicate_dates():
    """Test detection of duplicate dates."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = pathlib.Path(tmpdir) / "test.txt"
        content = """TEST,D,20200101,000000,100.0,105.0,95.0,102.0,10000,0
TEST,D,20200101,000000,102.0,108.0,100.0,106.0,12000,0
TEST,D,20200102,000000,106.0,110.0,104.0,108.0,15000,0"""
        create_test_file(test_file, content)

        diagnostics, status = _stream_stooq_file_for_diagnostics(test_file)

        assert "duplicate_dates" in diagnostics["data_flags"]


def test_stream_stooq_file_duplicate_dates_across_chunks():
    """Ensure duplicate dates are detected when they span chunk boundaries."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = pathlib.Path(tmpdir) / "chunk_duplicate.txt"

        lines = []
        import datetime

        start_date = datetime.date(2000, 1, 1)
        # Generate 10,001 rows so the chunk boundary falls between index 9999 and 10000
        for i in range(10001):
            current_date = start_date + datetime.timedelta(days=i)
            date_str = current_date.strftime("%Y%m%d")
            lines.append(f"TEST,D,{date_str},000000,100.0,105.0,95.0,102.0,10000,0")

        # Make the first row of the second chunk share a date with the last row of the first chunk
        duplicate_date = start_date + datetime.timedelta(days=9999)
        duplicate_date_str = duplicate_date.strftime("%Y%m%d")
        lines[10000] = (
            f"TEST,D,{duplicate_date_str},000000,101.0,106.0,96.0,103.0,11000,0"
        )

        create_test_file(test_file, "\n".join(lines))

        diagnostics, status = _stream_stooq_file_for_diagnostics(test_file)

        assert status == "ok"
        assert "duplicate_dates" in diagnostics["data_flags"]


def test_stream_stooq_file_non_monotonic_dates():
    """Test detection of non-monotonic dates."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = pathlib.Path(tmpdir) / "test.txt"
        content = """TEST,D,20200103,000000,100.0,105.0,95.0,102.0,10000,0
TEST,D,20200102,000000,102.0,108.0,100.0,106.0,12000,0
TEST,D,20200101,000000,106.0,110.0,104.0,108.0,15000,0"""
        create_test_file(test_file, content)

        diagnostics, status = _stream_stooq_file_for_diagnostics(test_file)

        assert "non_monotonic_dates" in diagnostics["data_flags"]


def test_stream_stooq_file_large_file():
    """Test streaming with a large file (multiple chunks)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = pathlib.Path(tmpdir) / "large.txt"

        # Create a file with >10000 rows (exceeds chunk size)
        # Use proper date format
        lines = []
        import datetime

        start_date = datetime.date(2000, 1, 1)
        for i in range(15000):
            current_date = start_date + datetime.timedelta(days=i)
            date_str = current_date.strftime("%Y%m%d")
            lines.append(f"TEST,D,{date_str},000000,100.0,105.0,95.0,102.0,10000,0")

        create_test_file(test_file, "\n".join(lines))

        diagnostics, status = _stream_stooq_file_for_diagnostics(test_file)

        assert status == "ok"
        assert diagnostics["price_rows"] == "15000"


def test_summarize_price_file_integration():
    """Test the public summarize_price_file function."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = pathlib.Path(tmpdir)
        test_file = base_dir / "test.us.txt"
        content = """TEST,D,20200101,000000,100.0,105.0,95.0,102.0,10000,0
TEST,D,20200102,000000,102.0,108.0,100.0,106.0,12000,0
TEST,D,20200103,000000,106.0,110.0,104.0,108.0,15000,0"""
        create_test_file(test_file, content)

        stooq_file = StooqFile(
            ticker="TEST.US",
            stem="TEST",
            rel_path="test.us.txt",
            region="us",
            category="stocks",
        )

        diagnostics = summarize_price_file(base_dir, stooq_file)

        assert diagnostics["data_status"] == "ok"
        assert diagnostics["price_start"] == "2020-01-01"
        assert diagnostics["price_end"] == "2020-01-03"
        assert diagnostics["price_rows"] == "3"


def test_stream_stooq_file_whitespace_handling():
    """Test that whitespace is properly stripped."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = pathlib.Path(tmpdir) / "test.txt"
        content = """TEST,D, 20200101 ,000000, 100.0 ,105.0,95.0, 102.0 , 10000 ,0
TEST,D,20200102,000000,102.0,108.0,100.0,106.0,12000,0"""
        create_test_file(test_file, content)

        diagnostics, status = _stream_stooq_file_for_diagnostics(test_file)

        assert status == "ok"
        assert diagnostics["price_rows"] == "2"
