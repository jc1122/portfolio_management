"""Fast unit tests for returns calculation using mocks."""

import pytest
import pandas as pd
import numpy as np
from portfolio_management.analytics.returns import calculator
from portfolio_management.analytics.returns.calculator import ReturnConfig


@pytest.mark.unit
def test_simple_returns_calculation():
    """Test simple returns with known values."""
    prices = pd.DataFrame({'TEST': [100, 110, 121]}, index=pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03']))
    calc = calculator.ReturnCalculator()

    returns = calc.calculate_returns(prices, ReturnConfig(method="simple"))

    expected_index = pd.to_datetime(['2023-01-02', '2023-01-03'])
    expected_values = [0.10, 0.10]
    expected = pd.DataFrame({'TEST': expected_values}, index=expected_index)

    pd.testing.assert_frame_equal(returns, expected, check_names=False)


@pytest.mark.unit
def test_log_returns_calculation():
    """Test log returns with known values."""
    prices = pd.DataFrame({'TEST': [100, 110, 121]}, index=pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03']))
    calc = calculator.ReturnCalculator()

    returns = calc.calculate_returns(prices, ReturnConfig(method="log"))

    expected_index = pd.to_datetime(['2023-01-02', '2023-01-03'])
    expected_values = [np.log(110/100), np.log(121/110)]
    expected = pd.DataFrame({'TEST': expected_values}, index=expected_index)

    pd.testing.assert_frame_equal(returns, expected, check_names=False)


@pytest.mark.unit
def test_returns_properties(mock_returns):
    """Test mathematical properties of returns."""
    calc = calculator.ReturnCalculator()

    # Returns should maintain time series properties
    assert not mock_returns.isna().all().any()
    assert len(mock_returns) == 252
    assert mock_returns.shape[1] == 5
