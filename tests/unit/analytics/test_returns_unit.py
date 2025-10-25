"""Unit tests for return calculation utilities."""

from __future__ import annotations

import pandas as pd
import pytest

from portfolio_management.analytics.returns.calculator import ReturnCalculator
from portfolio_management.analytics.returns.config import ReturnConfig


@pytest.mark.unit
def test_simple_returns_known_values() -> None:
    """Simple returns use percentage change between observations."""

    calculator = ReturnCalculator()
    prices = pd.Series([100, 110, 121], index=pd.date_range("2020-01-01", periods=3))

    result = calculator._calculate_simple_returns(prices)

    expected = pd.Series(
        [0.10, 0.10],
        index=pd.date_range("2020-01-02", periods=2),
    )
    pd.testing.assert_series_equal(result, expected)


@pytest.mark.unit
def test_log_returns_known_values() -> None:
    """Log returns match the natural logarithm of price ratios."""

    calculator = ReturnCalculator()
    prices = pd.Series([100, 110, 121], index=pd.date_range("2020-01-01", periods=3))

    result = calculator._calculate_log_returns(prices)

    assert pytest.approx(result.iloc[0], rel=1e-5) == pytest.approx(0.0953102, rel=1e-5)
    assert pytest.approx(result.iloc[1], rel=1e-5) == pytest.approx(0.0953102, rel=1e-5)


@pytest.mark.unit
def test_excess_returns_subtracts_risk_free() -> None:
    """Excess returns subtract the daily risk-free rate from simple returns."""

    calculator = ReturnCalculator()
    prices = pd.Series([100, 110, 121], index=pd.date_range("2020-01-01", periods=3))

    result = calculator._calculate_excess_returns(prices, risk_free_rate=0.05)

    daily_rf = (1 + 0.05) ** (1 / 252) - 1
    assert pytest.approx(result.iloc[0]) == pytest.approx(0.10 - daily_rf)


@pytest.mark.unit
def test_calculate_returns_filters_insufficient_history() -> None:
    """Assets with fewer than ``min_periods`` observations are removed."""

    calculator = ReturnCalculator()
    prices = pd.DataFrame(
        {
            "A": [100, 101, 102],
            "B": [50, 51, None],
        },
        index=pd.date_range("2020-01-01", periods=3),
    )
    config = ReturnConfig(method="simple", min_periods=3)

    returns = calculator.calculate_returns(prices, config)

    assert list(returns.columns) == ["A"]
    assert returns.shape[0] == 2


@pytest.mark.unit
def test_calculate_returns_log_method(mock_returns: pd.DataFrame) -> None:
    """Log return calculation preserves the input shape for eligible assets."""

    calculator = ReturnCalculator()
    config = ReturnConfig(method="log", min_periods=5)

    returns = calculator.calculate_returns(mock_returns.iloc[:6], config)

    assert returns.shape[1] == mock_returns.shape[1]
    assert returns.index.min() == mock_returns.index[1]
