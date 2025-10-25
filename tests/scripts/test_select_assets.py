"""Tests for select_assets.py CLI script."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

# Add project root to path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# ruff: noqa: E402
from portfolio_management.assets.selection import FilterCriteria
from portfolio_management.core.exceptions import AssetSelectionError
from scripts.select_assets import process_chunked


@pytest.mark.integration
class TestProcessChunked:
    """Tests for process_chunked function."""

    @pytest.fixture
    def temp_match_report(self, tmp_path: Path) -> Path:
        """Create a temporary match report CSV for testing."""
        df = pd.DataFrame(
            {
                "symbol": [
                    "AAPL.US",
                    "MSFT.US",
                    "GOOGL.US",
                    "TSLA.US",
                    "META.US",
                    "AMZN.US",
                    "NVDA.US",
                    "AMD.US",
                ],
                "isin": [
                    "US0378331005",
                    "US5949181045",
                    "US02079K3059",
                    "US88160R1014",
                    "US30303M1027",
                    "US0231351067",
                    "US67066G1040",
                    "US0079031078",
                ],
                "name": [
                    "Apple Inc",
                    "Microsoft Corp",
                    "Alphabet Inc",
                    "Tesla Inc",
                    "Meta Platforms",
                    "Amazon.com Inc",
                    "NVIDIA Corp",
                    "Advanced Micro Devices",
                ],
                "market": ["US"] * 8,
                "region": ["Americas"] * 8,
                "currency": ["USD"] * 8,
                "category": ["Stock"] * 8,
                "price_start": ["2020-01-01"] * 8,
                "price_end": ["2025-10-15"] * 8,
                "price_rows": [1500] * 8,
                "data_status": ["ok"] * 8,
                "data_flags": [""] * 8,
                "stooq_path": ["d_us_txt/data/daily/us/aapl.txt"] * 8,
                "resolved_currency": ["USD"] * 8,
                "currency_status": ["matched"] * 8,
            },
        )
        csv_path = tmp_path / "test_matches.csv"
        df.to_csv(csv_path, index=False)
        return csv_path

    def test_chunked_processing_basic(self, temp_match_report: Path) -> None:
        """Test basic chunked processing with chunk_size=3."""
        criteria = FilterCriteria(data_status=["ok"], min_history_days=252)

        # Process in chunks of 3 rows
        selected_assets = process_chunked(temp_match_report, criteria, chunk_size=3)

        # All 8 assets should be selected
        assert len(selected_assets) == 8
        symbols = {asset.symbol for asset in selected_assets}
        assert "AAPL.US" in symbols
        assert "AMD.US" in symbols

    def test_chunked_same_as_eager(
        self,
        temp_match_report: Path,
    ) -> None:
        """Test that chunked processing produces same results as eager loading."""
        from portfolio_management.assets.selection import AssetSelector

        criteria = FilterCriteria(
            data_status=["ok"],
            min_history_days=252,
            markets=["US"],
        )

        # Eager loading
        eager_df = pd.read_csv(temp_match_report)
        selector = AssetSelector()
        eager_selected = selector.select_assets(eager_df, criteria)

        # Chunked loading
        chunked_selected = process_chunked(temp_match_report, criteria, chunk_size=3)

        # Should have same number of results
        assert len(eager_selected) == len(chunked_selected)

        # Should have same symbols
        eager_symbols = {asset.symbol for asset in eager_selected}
        chunked_symbols = {asset.symbol for asset in chunked_selected}
        assert eager_symbols == chunked_symbols

    def test_chunked_with_filters(self, temp_match_report: Path) -> None:
        """Test chunked processing with filtering criteria."""
        # Create criteria that filters out some assets
        criteria = FilterCriteria(
            data_status=["ok"],
            min_history_days=252,
            blocklist={"AAPL.US", "MSFT.US"},
        )

        selected_assets = process_chunked(temp_match_report, criteria, chunk_size=3)

        # Should have 6 assets (8 - 2 blocked)
        assert len(selected_assets) == 6
        symbols = {asset.symbol for asset in selected_assets}
        assert "AAPL.US" not in symbols
        assert "MSFT.US" not in symbols
        assert "GOOGL.US" in symbols

    def test_chunked_with_allowlist(self, temp_match_report: Path) -> None:
        """Test chunked processing with allowlist."""
        criteria = FilterCriteria(
            data_status=["ok"],
            min_history_days=252,
            allowlist={"AAPL.US", "GOOGL.US"},
        )

        selected_assets = process_chunked(temp_match_report, criteria, chunk_size=3)

        # Should have exactly 2 assets from allowlist
        assert len(selected_assets) == 2
        symbols = {asset.symbol for asset in selected_assets}
        assert symbols == {"AAPL.US", "GOOGL.US"}

    def test_chunked_allowlist_not_found(self, temp_match_report: Path) -> None:
        """Test that missing allowlist items raise an error."""
        criteria = FilterCriteria(
            data_status=["ok"],
            min_history_days=252,
            allowlist={"AAPL.US", "NOTFOUND.US"},
        )

        with pytest.raises(AssetSelectionError, match="Allowlist items not found"):
            process_chunked(temp_match_report, criteria, chunk_size=3)

    def test_chunked_allowlist_with_isin(self, temp_match_report: Path) -> None:
        """Test allowlist validation works with ISINs."""
        criteria = FilterCriteria(
            data_status=["ok"],
            min_history_days=252,
            allowlist={"US0378331005"},  # AAPL's ISIN
        )

        selected_assets = process_chunked(temp_match_report, criteria, chunk_size=3)

        assert len(selected_assets) == 1
        assert selected_assets[0].symbol == "AAPL.US"

    def test_chunked_with_blocklist(self, temp_match_report: Path) -> None:
        """Test chunked processing respects blocklist across chunks."""
        criteria = FilterCriteria(
            data_status=["ok"],
            min_history_days=252,
            blocklist={"AAPL.US", "US5949181045"},  # AAPL symbol, MSFT ISIN
        )

        selected_assets = process_chunked(temp_match_report, criteria, chunk_size=3)

        # Should have 6 assets (8 - 2 blocked)
        assert len(selected_assets) == 6
        symbols = {asset.symbol for asset in selected_assets}
        assert "AAPL.US" not in symbols
        assert "MSFT.US" not in symbols

    def test_chunked_chunk_size_one(self, temp_match_report: Path) -> None:
        """Test chunked processing with chunk_size=1."""
        criteria = FilterCriteria(data_status=["ok"], min_history_days=252)

        selected_assets = process_chunked(temp_match_report, criteria, chunk_size=1)

        # All 8 assets should be selected
        assert len(selected_assets) == 8

    def test_chunked_large_chunk_size(self, temp_match_report: Path) -> None:
        """Test chunked processing with chunk_size larger than file."""
        criteria = FilterCriteria(data_status=["ok"], min_history_days=252)

        selected_assets = process_chunked(temp_match_report, criteria, chunk_size=1000)

        # All 8 assets should be selected
        assert len(selected_assets) == 8

    def test_chunked_empty_result(self, temp_match_report: Path) -> None:
        """Test chunked processing when no assets match criteria."""
        criteria = FilterCriteria(
            data_status=["ok"],
            min_history_days=99999,  # Impossible requirement
        )

        selected_assets = process_chunked(temp_match_report, criteria, chunk_size=3)

        assert len(selected_assets) == 0

    def test_chunked_preserves_asset_properties(
        self,
        temp_match_report: Path,
    ) -> None:
        """Test that chunked processing preserves all asset properties."""
        criteria = FilterCriteria(data_status=["ok"], allowlist={"AAPL.US"})

        selected_assets = process_chunked(temp_match_report, criteria, chunk_size=3)

        assert len(selected_assets) == 1
        asset = selected_assets[0]
        assert asset.symbol == "AAPL.US"
        assert asset.isin == "US0378331005"
        assert asset.name == "Apple Inc"
        assert asset.market == "US"
        assert asset.region == "Americas"
        assert asset.currency == "USD"
        assert asset.category == "Stock"
        assert asset.data_status == "ok"
