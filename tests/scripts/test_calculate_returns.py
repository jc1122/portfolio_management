"""Tests for the calculate_returns CLI script."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from scripts.calculate_returns import parse_args, run_cli
from src.portfolio_management.selection import SelectedAsset


@pytest.fixture
def sample_asset() -> SelectedAsset:
    return SelectedAsset(
        symbol="TEST.US",
        isin="US0000000000",
        name="Test Equity Fund",
        market="US",
        region="North America",
        currency="USD",
        category="etf",
        price_start="2022-01-03",
        price_end="2022-01-07",
        price_rows=5,
        data_status="ok",
        data_flags="",
        stooq_path="test.us.txt",
        resolved_currency="USD",
        currency_status="matched",
    )


@pytest.fixture
def assets_csv(tmp_path: Path, sample_asset: SelectedAsset) -> Path:
    assets_path = tmp_path / "assets.csv"
    pd.DataFrame([sample_asset.__dict__]).to_csv(assets_path, index=False)
    return assets_path


@pytest.fixture
def prices_dir(tmp_path: Path) -> Path:
    prices_dir = tmp_path / "prices"
    prices_dir.mkdir()
    price_file = prices_dir / "test.us.txt"
    price_file.write_text(
        "date,open,high,low,close,volume\n"
        "2022-01-03,100,102,99,101,1000\n"
        "2022-01-04,101,103,100,102,1200\n"
        "2022-01-05,102,105,101,103,1100\n"
        "2022-01-06,103,106,102,104,900\n"
        "2022-01-07,104,107,103,105,850\n",
    )
    return prices_dir


def test_cli_summary_output(
    assets_csv: Path, prices_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    args = parse_args(
        [
            "--assets",
            str(assets_csv),
            "--prices-dir",
            str(prices_dir),
            "--summary",
        ],
    )
    exit_code = run_cli(args)
    assert exit_code == 0

    captured = capsys.readouterr().out
    assert "Return Statistics Summary" in captured
    assert "Assets with returns: 1" in captured


def test_cli_writes_output_file(
    tmp_path: Path, assets_csv: Path, prices_dir: Path
) -> None:
    output_path = tmp_path / "returns.csv"
    args = parse_args(
        [
            "--assets",
            str(assets_csv),
            "--prices-dir",
            str(prices_dir),
            "--output",
            str(output_path),
        ],
    )
    exit_code = run_cli(args)
    assert exit_code == 0
    assert output_path.exists()
    df = pd.read_csv(output_path)
    assert not df.empty
