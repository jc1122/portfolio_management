"""Tests for the classify_assets CLI script."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import pandas as pd
import pytest

from portfolio_management.assets.selection import SelectedAsset
from scripts.classify_assets import parse_args, run_cli


@pytest.fixture
def sample_assets() -> list[SelectedAsset]:
    base_kwargs = dict(
        market="NYSE",
        region="us",
        currency="usd",
        price_start="2020-01-01",
        price_end="2020-12-31",
        price_rows=252,
        data_status="ok",
        data_flags="",
        stooq_path="sample.txt",
        resolved_currency="USD",
        currency_status="matched",
    )
    equity = SelectedAsset(
        symbol="EQTY",
        isin="US0000000001",
        name="Global Equity Fund",
        category="etf",
        **base_kwargs,
    )
    bond = SelectedAsset(
        symbol="BOND",
        isin="US0000000002",
        name="US Treasury Bond",
        category="bond fund",
        **base_kwargs,
    )
    return [equity, bond]


@pytest.fixture
def assets_csv(tmp_path: Path, sample_assets: list[SelectedAsset]) -> Path:
    assets_path = tmp_path / "selected_assets.csv"
    pd.DataFrame([asdict(asset) for asset in sample_assets]).to_csv(
        assets_path,
        index=False,
    )
    return assets_path


def test_cli_summary_output(
    assets_csv: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    args = parse_args(
        [
            "--input",
            str(assets_csv),
            "--summary",
        ],
    )
    exit_code = run_cli(args)
    assert exit_code == 0

    captured = capsys.readouterr().out
    assert "Classification Summary" in captured
    assert "Asset Class Breakdown" in captured


@pytest.mark.integration
def test_cli_writes_output_file(tmp_path: Path, assets_csv: Path) -> None:
    output_path = tmp_path / "classified.csv"
    args = parse_args(
        [
            "--input",
            str(assets_csv),
            "--output",
            str(output_path),
        ],
    )
    exit_code = run_cli(args)
    assert exit_code == 0
    assert output_path.exists()
    df = pd.read_csv(output_path)
    assert "asset_class" in df.columns
    assert not df.empty
