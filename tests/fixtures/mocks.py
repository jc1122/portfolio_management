"""Reusable mock fixtures for fast unit testing."""

from __future__ import annotations

import pandas as pd
import pytest


@pytest.fixture
def mock_price_data() -> pd.DataFrame:
    """Fast in-memory price DataFrame for unit tests.

    Returns 3 assets, 10 trading days.
    No I/O, constructed in-memory.
    """
    dates = pd.date_range(start="2020-01-01", periods=10, freq="D")
    data = {
        "Date": dates.tolist() * 3,
        "Symbol": ["AAPL"] * 10 + ["GOOGL"] * 10 + ["MSFT"] * 10,
        "Close": [100 + i for i in range(10)] * 3,
        "Volume": [1000000] * 30,
    }
    return pd.DataFrame(data)


@pytest.fixture
def mock_returns() -> pd.DataFrame:
    """Fast in-memory returns DataFrame for strategy tests.

    Returns 5 assets, 252 trading days (1 year).
    Normally distributed returns for realistic testing.
    """
    import numpy as np

    dates = pd.date_range(start="2020-01-01", periods=252, freq="D")
    assets = ["A", "B", "C", "D", "E"]

    # Generate realistic returns
    np.random.seed(42)  # Reproducible
    returns = pd.DataFrame(
        np.random.normal(0.0005, 0.01, size=(252, 5)),
        index=dates,
        columns=assets,
    )
    return returns


@pytest.fixture
def mock_weights() -> dict[str, float]:
    """Fast mock portfolio weights."""
    return {
        "AAPL": 0.2,
        "GOOGL": 0.2,
        "MSFT": 0.2,
        "AMZN": 0.2,
        "TSLA": 0.2,
    }


@pytest.fixture
def mock_covariance_matrix(mock_returns: pd.DataFrame) -> pd.DataFrame:
    """Fast mock covariance matrix matching mock_returns."""
    return mock_returns.cov()


@pytest.fixture
def mock_expected_returns(mock_returns: pd.DataFrame) -> pd.Series:
    """Fast mock expected returns matching mock_returns."""
    return mock_returns.mean() * 252  # Annualized
