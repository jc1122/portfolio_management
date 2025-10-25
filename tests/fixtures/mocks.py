"""Reusable mock fixtures for fast unit testing."""

from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def mock_price_data() -> pd.DataFrame:
    """Construct a small in-memory price DataFrame.

    The data covers 10 consecutive business days for three synthetic assets.
    Prices are generated deterministically so tests can rely on exact values.
    """

    start = datetime(2020, 1, 2)
    dates = pd.bdate_range(start=start, periods=10)
    base = np.linspace(100, 109, num=10)
    data = {
        "AAA": base,
        "BBB": base * 1.02,
        "CCC": base * 0.98,
    }
    return pd.DataFrame(data, index=dates)


@pytest.fixture
def mock_returns(mock_price_data: pd.DataFrame) -> pd.DataFrame:
    """Return deterministic percentage returns derived from ``mock_price_data``."""

    returns = mock_price_data.pct_change().dropna()
    returns.index.name = "date"
    return returns


@pytest.fixture
def mock_expected_returns(mock_returns: pd.DataFrame) -> pd.Series:
    """Provide average returns for each asset."""

    return mock_returns.mean()


@pytest.fixture
def mock_covariance_matrix(mock_returns: pd.DataFrame) -> pd.DataFrame:
    """Provide the covariance matrix of the mock returns."""

    return mock_returns.cov()


@pytest.fixture
def mock_weights() -> pd.Series:
    """Return a set of example portfolio weights that sum to one."""

    return pd.Series({"AAA": 0.4, "BBB": 0.35, "CCC": 0.25})
