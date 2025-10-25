"""Unit tests for the return calculator utilities."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from portfolio_management.analytics.returns.calculator import ReturnCalculator
from portfolio_management.analytics.returns.config import ReturnConfig

pytestmark = pytest.mark.unit


def test_handle_missing_forward_fill_respects_limit(mock_price_data: pd.DataFrame) -> None:
    """Forward fill should populate gaps up to the configured limit."""

    prices = mock_price_data.copy()
    prices.iloc[2, 0] = np.nan
    config = ReturnConfig(handle_missing="forward_fill", max_forward_fill_days=1)
    calculator = ReturnCalculator()

    filled = calculator.handle_missing_data(prices, config)

    assert not filled.iloc[2].isna().any()


def test_handle_missing_drop_removes_nan_rows(mock_price_data: pd.DataFrame) -> None:
    """Drop mode should remove rows containing missing data."""

    prices = mock_price_data.copy()
    prices.iloc[3, 1] = np.nan
    config = ReturnConfig(handle_missing="drop")
    calculator = ReturnCalculator()

    cleaned = calculator.handle_missing_data(prices, config)

    removed_index = prices.index[3]
    assert removed_index not in cleaned.index


def test_calculate_returns_simple(mock_price_data: pd.DataFrame) -> None:
    """Simple returns should match pct_change results."""

    config = ReturnConfig(method="simple", min_periods=2)
    calculator = ReturnCalculator()

    returns = calculator.calculate_returns(mock_price_data, config)

    expected = mock_price_data.pct_change().dropna()
    pd.testing.assert_frame_equal(returns, expected)


def test_align_dates_inner_drops_missing(mock_returns: pd.DataFrame) -> None:
    """Inner alignment should drop rows containing NaNs."""

    misaligned = mock_returns.copy()
    misaligned.iloc[0, 0] = np.nan
    config = ReturnConfig(align_method="inner", min_periods=2)
    calculator = ReturnCalculator()

    aligned = calculator._align_dates(misaligned, config)

    assert aligned.notna().all().all()
    assert len(aligned) == len(mock_returns) - 1


def test_resample_to_monthly_sums_returns(mock_returns: pd.DataFrame) -> None:
    """Monthly resampling should aggregate according to the configured rule."""

    config = ReturnConfig(frequency="monthly", method="simple", min_periods=2)
    calculator = ReturnCalculator()

    resampled = calculator._resample_to_frequency(mock_returns, "monthly", "simple")

    expected = (1 + mock_returns).resample("ME").prod() - 1
    pd.testing.assert_frame_equal(resampled, expected)
