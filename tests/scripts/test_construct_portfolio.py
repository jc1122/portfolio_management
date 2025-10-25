"""Tests for the portfolio construction CLI."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts.construct_portfolio import parse_args, run_cli


@pytest.fixture
def returns_csv(tmp_path: Path) -> Path:
    """Create a small returns CSV for testing."""
    rng = np.random.default_rng(1)
    dates = pd.date_range("2020-01-01", periods=10, freq="D")
    df = pd.DataFrame(
        rng.normal(scale=0.01, size=(10, 3)),
        index=dates,
        columns=["AAPL", "MSFT", "BND"],
    )
    path = Path(tmp_path) / "returns.csv"
    df.to_csv(path)
    return path


@pytest.mark.integration
def test_cli_constructs_equal_weight(tmp_path: Path, returns_csv: Path) -> None:
    """CLI writes portfolio weights for equal weight strategy."""
    output_path = Path(tmp_path) / "weights.csv"
    args = parse_args(
        [
            "--returns",
            str(returns_csv),
            "--strategy",
            "equal_weight",
            "--output",
            str(output_path),
            "--max-weight",
            "1.0",
        ],
    )

    exit_code = run_cli(args)

    assert exit_code == 0
    assert output_path.exists()
    weights = pd.read_csv(output_path, index_col=0)
    assert np.isclose(weights["weight"].sum(), 1.0)


def test_cli_compare_mode(
    tmp_path: Path,
    returns_csv: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CLI comparison writes table of strategies."""
    # Limit strategies to equal-weight to avoid optional dependency requirements.
    from portfolio_management.portfolio import PortfolioConstructor

    def list_strategies_stub(self):
        return ["equal_weight"]

    monkeypatch.setattr(
        PortfolioConstructor,
        "list_strategies",
        list_strategies_stub,
        raising=False,
    )

    output_path = Path(tmp_path) / "comparison.csv"
    args = parse_args(
        [
            "--returns",
            str(returns_csv),
            "--output",
            str(output_path),
            "--compare",
            "--max-weight",
            "1.0",
        ],
    )

    exit_code = run_cli(args)

    assert exit_code == 0
    comparison = pd.read_csv(output_path, index_col=0)
    assert "equal_weight" in comparison.columns


@pytest.mark.integration
def test_cli_invalid_strategy_returns_error(tmp_path: Path, returns_csv: Path) -> None:
    """Invalid strategy name returns a non-zero exit code."""
    output_path = Path(tmp_path) / "invalid.csv"
    args = parse_args(
        [
            "--returns",
            str(returns_csv),
            "--strategy",
            "does_not_exist",
            "--output",
            str(output_path),
        ],
    )

    exit_code = run_cli(args)

    assert exit_code == 1
    assert not output_path.exists()
