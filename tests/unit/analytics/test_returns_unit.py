"""Unit tests for return calculation helpers."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from portfolio_management.analytics.returns.calculator import ReturnCalculator
from portfolio_management.analytics.returns.config import ReturnConfig

pytestmark = pytest.mark.unit


@pytest.fixture
def calculator() -> ReturnCalculator:
    """Return a calculator instance for direct method testing."""
    return ReturnCalculator()


def test_handle_missing_data_forward_fill(calculator: ReturnCalculator) -> None:
    """Forward filling should backfill a single gap using prior values."""
    prices = pd.DataFrame(
        {
            "AAA": [100.0, np.nan, 102.0],
            "BBB": [50.0, 51.0, 52.0],
        },
        index=pd.date_range("2020-01-01", periods=3, freq="D"),
    )
    config = ReturnConfig(handle_missing="forward_fill", min_periods=3)

    filled = calculator.handle_missing_data(prices, config)

    assert filled.loc[pd.Timestamp("2020-01-02"), "AAA"] == pytest.approx(100.0)
    assert filled.isna().sum().sum() == 0


def test_handle_missing_data_drop(calculator: ReturnCalculator) -> None:
    """Drop strategy removes rows containing NaNs."""
    prices = pd.DataFrame(
        {
            "AAA": [100.0, np.nan, 103.0],
            "BBB": [50.0, 51.0, 52.0],
        },
        index=pd.date_range("2020-01-01", periods=3, freq="D"),
    )
    config = ReturnConfig(handle_missing="drop", min_periods=3)

    handled = calculator.handle_missing_data(prices, config)

    assert len(handled) == 2
    assert handled.index.tolist() == [pd.Timestamp("2020-01-01"), pd.Timestamp("2020-01-03")]


def test_calculate_simple_returns(calculator: ReturnCalculator) -> None:
    """Simple returns should match the pct_change calculation."""
    prices = pd.DataFrame(
        {
            "AAA": [100.0, 110.0, 121.0],
            "BBB": [50.0, 60.0, 66.0],
        },
        index=pd.date_range("2020-01-01", periods=3, freq="D"),
    )
    config = ReturnConfig(method="simple", min_periods=3)

    returns = calculator.calculate_returns(prices, config)

    expected = prices.pct_change().dropna()
    pd.testing.assert_frame_equal(returns, expected)


def test_calculate_log_returns(calculator: ReturnCalculator) -> None:
    """Log returns should equal log(price/price.shift(1))."""
    prices = pd.DataFrame(
        {
            "AAA": [100.0, 105.0, 110.25],
            "BBB": [200.0, 210.0, 220.5],
        },
        index=pd.date_range("2020-01-01", periods=3, freq="D"),
    )
    config = ReturnConfig(method="log", min_periods=3)

    returns = calculator.calculate_returns(prices, config)

    expected = np.log(prices / prices.shift(1)).dropna()
    pd.testing.assert_frame_equal(returns, expected)


def test_apply_coverage_filter(calculator: ReturnCalculator) -> None:
    """Assets falling below the coverage threshold are removed."""
    returns = pd.DataFrame(
        {
            "AAA": [0.01, 0.02, 0.03, 0.04],
            "BBB": [0.01, np.nan, np.nan, 0.02],
            "CCC": [0.0, 0.0, 0.0, 0.0],
        },
        index=pd.date_range("2020-01-01", periods=4, freq="D"),
    )

    filtered = calculator._apply_coverage_filter(returns, min_coverage=0.75)

    assert list(filtered.columns) == ["AAA", "CCC"]
    assert "BBB" not in filtered.columns
