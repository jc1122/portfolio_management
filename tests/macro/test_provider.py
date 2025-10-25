"""Tests for MacroSignalProvider."""

from pathlib import Path

import pandas as pd
import pytest
pytestmark = pytest.mark.integration

from portfolio_management.core.exceptions import (
    DataDirectoryNotFoundError,
    DataValidationError,
)
from portfolio_management.macro.provider import MacroSignalProvider


class TestMacroSignalProviderInit:
    """Tests for MacroSignalProvider initialization."""

    def test_init_with_valid_directory(self, tmp_path: Path) -> None:
        """Test initialization with a valid data directory."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        provider = MacroSignalProvider(data_dir)

        assert provider.data_dir == data_dir

    def test_init_with_string_path(self, tmp_path: Path) -> None:
        """Test initialization with string path."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        provider = MacroSignalProvider(str(data_dir))

        assert provider.data_dir == data_dir

    def test_init_with_nonexistent_directory(self, tmp_path: Path) -> None:
        """Test initialization with nonexistent directory."""
        nonexistent = tmp_path / "nonexistent"

        with pytest.raises(DataDirectoryNotFoundError):
            MacroSignalProvider(nonexistent)


class TestLocateSeries:
    """Tests for locate_series method."""

    def test_locate_series_found(self, tmp_path: Path) -> None:
        """Test locating an existing series file."""
        # Create test directory structure
        data_dir = tmp_path / "data"
        series_dir = data_dir / "data" / "daily" / "us" / "economic"
        series_dir.mkdir(parents=True)

        # Create a test series file
        series_file = series_dir / "gdp.txt"
        series_file.write_text(
            "ticker,per,date,time,open,high,low,close,volume,openint\n"
        )

        provider = MacroSignalProvider(data_dir)
        series = provider.locate_series("gdp.us")

        assert series is not None
        assert series.ticker == "gdp.us"
        assert "gdp.txt" in series.rel_path
        assert series.region == "us"
        assert series.category == "economic"

    def test_locate_series_not_found(self, tmp_path: Path) -> None:
        """Test locating a nonexistent series."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        provider = MacroSignalProvider(data_dir)
        series = provider.locate_series("nonexistent.us")

        assert series is None

    def test_locate_series_alternative_path(self, tmp_path: Path) -> None:
        """Test locating series in alternative directory structure."""
        # Create test directory structure (simplified path)
        data_dir = tmp_path / "data"
        series_dir = data_dir / "us" / "indicators"
        series_dir.mkdir(parents=True)

        # Create a test series file
        series_file = series_dir / "pmi.txt"
        series_file.write_text(
            "ticker,per,date,time,open,high,low,close,volume,openint\n"
        )

        provider = MacroSignalProvider(data_dir)
        series = provider.locate_series("pmi.us")

        assert series is not None
        assert series.ticker == "pmi.us"
        assert "pmi.txt" in series.rel_path


class TestLocateMultipleSeries:
    """Tests for locate_multiple_series method."""

    def test_locate_multiple_all_found(self, tmp_path: Path) -> None:
        """Test locating multiple series when all exist."""
        # Create test directory structure
        data_dir = tmp_path / "data"
        series_dir = data_dir / "data" / "daily" / "us" / "economic"
        series_dir.mkdir(parents=True)

        # Create test series files
        (series_dir / "gdp.txt").write_text("data\n")
        (series_dir / "pmi.txt").write_text("data\n")

        provider = MacroSignalProvider(data_dir)
        series_dict = provider.locate_multiple_series(["gdp.us", "pmi.us"])

        assert len(series_dict) == 2
        assert "gdp.us" in series_dict
        assert "pmi.us" in series_dict
        assert series_dict["gdp.us"].ticker == "gdp.us"
        assert series_dict["pmi.us"].ticker == "pmi.us"

    def test_locate_multiple_partial_found(self, tmp_path: Path) -> None:
        """Test locating multiple series when only some exist."""
        # Create test directory structure
        data_dir = tmp_path / "data"
        series_dir = data_dir / "data" / "daily" / "us" / "economic"
        series_dir.mkdir(parents=True)

        # Create only one test series file
        (series_dir / "gdp.txt").write_text("data\n")

        provider = MacroSignalProvider(data_dir)
        series_dict = provider.locate_multiple_series(
            ["gdp.us", "pmi.us", "nonexistent.us"],
        )

        # Only found series should be in result
        assert len(series_dict) == 1
        assert "gdp.us" in series_dict
        assert "pmi.us" not in series_dict
        assert "nonexistent.us" not in series_dict

    def test_locate_multiple_none_found(self, tmp_path: Path) -> None:
        """Test locating multiple series when none exist."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        provider = MacroSignalProvider(data_dir)
        series_dict = provider.locate_multiple_series(
            ["nonexistent1.us", "nonexistent2.us"],
        )

        assert len(series_dict) == 0


class TestLoadSeriesData:
    """Tests for load_series_data method."""

    def test_load_series_data_success(self, tmp_path: Path) -> None:
        """Test successfully loading series data."""
        # Create test directory and file
        data_dir = tmp_path / "data"
        series_dir = data_dir / "data" / "daily" / "us" / "economic"
        series_dir.mkdir(parents=True)

        # Create test CSV with Stooq format
        series_file = series_dir / "gdp.txt"
        csv_content = """ticker,per,date,time,open,high,low,close,volume,openint
GDP.US,D,2020-01-01,0,100,105,98,102,1000,0
GDP.US,D,2020-01-02,0,102,107,100,105,1100,0
GDP.US,D,2020-01-03,0,105,110,103,108,1200,0
"""
        series_file.write_text(csv_content)

        provider = MacroSignalProvider(data_dir)
        df = provider.load_series_data("gdp.us")

        assert df is not None
        assert len(df) == 3
        assert "close" in df.columns
        assert df.index.name == "date"

    def test_load_series_data_with_date_filter(self, tmp_path: Path) -> None:
        """Test loading series data with date filtering."""
        # Create test directory and file
        data_dir = tmp_path / "data"
        series_dir = data_dir / "data" / "daily" / "us" / "economic"
        series_dir.mkdir(parents=True)

        # Create test CSV
        series_file = series_dir / "gdp.txt"
        csv_content = """ticker,per,date,time,open,high,low,close,volume,openint
GDP.US,D,2020-01-01,0,100,105,98,102,1000,0
GDP.US,D,2020-01-02,0,102,107,100,105,1100,0
GDP.US,D,2020-01-03,0,105,110,103,108,1200,0
GDP.US,D,2020-01-04,0,108,112,106,110,1300,0
"""
        series_file.write_text(csv_content)

        provider = MacroSignalProvider(data_dir)
        df = provider.load_series_data(
            "gdp.us",
            start_date="2020-01-02",
            end_date="2020-01-03",
        )

        assert df is not None
        assert len(df) == 2
        assert df.index.min() >= pd.Timestamp("2020-01-02")
        assert df.index.max() <= pd.Timestamp("2020-01-03")

    def test_load_series_data_not_found(self, tmp_path: Path) -> None:
        """Test loading data for nonexistent series."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        provider = MacroSignalProvider(data_dir)
        df = provider.load_series_data("nonexistent.us")

        assert df is None

    def test_load_series_data_invalid_file(self, tmp_path: Path) -> None:
        """Test loading data from an invalid file."""
        # Create test directory and file with invalid content
        data_dir = tmp_path / "data"
        series_dir = data_dir / "data" / "daily" / "us" / "economic"
        series_dir.mkdir(parents=True)

        series_file = series_dir / "gdp.txt"
        series_file.write_text("invalid,csv,content\n")

        provider = MacroSignalProvider(data_dir)

        with pytest.raises(DataValidationError):
            provider.load_series_data("gdp.us")


class TestGenerateSearchPaths:
    """Tests for _generate_search_paths method."""

    def test_generate_search_paths_with_region(self, tmp_path: Path) -> None:
        """Test generating search paths with explicit region."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        provider = MacroSignalProvider(data_dir)
        paths = provider._generate_search_paths("gdp.us")

        # Should contain multiple potential paths
        assert len(paths) > 0
        assert any("us" in p for p in paths)
        assert any("gdp.txt" in p for p in paths)

    def test_generate_search_paths_without_region(self, tmp_path: Path) -> None:
        """Test generating search paths without explicit region."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        provider = MacroSignalProvider(data_dir)
        paths = provider._generate_search_paths("gdp")

        # Should default to US and contain paths
        assert len(paths) > 0
        assert any("gdp.txt" in p for p in paths)


class TestParsePathMetadata:
    """Tests for _parse_path_metadata method."""

    def test_parse_path_metadata_full_path(self, tmp_path: Path) -> None:
        """Test parsing metadata from full Stooq path."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        provider = MacroSignalProvider(data_dir)
        region, category = provider._parse_path_metadata(
            "data/daily/us/economic/gdp.txt",
        )

        assert region == "us"
        assert category == "economic"

    def test_parse_path_metadata_simplified_path(self, tmp_path: Path) -> None:
        """Test parsing metadata from simplified path."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        provider = MacroSignalProvider(data_dir)
        region, category = provider._parse_path_metadata("us/indicators/pmi.txt")

        assert region == "us"
        assert category == "indicators"

    def test_parse_path_metadata_minimal_path(self, tmp_path: Path) -> None:
        """Test parsing metadata from minimal path."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        provider = MacroSignalProvider(data_dir)
        region, category = provider._parse_path_metadata("us/gdp.txt")

        assert region == "us"
        # Category might be empty or extracted differently
        assert isinstance(category, str)
