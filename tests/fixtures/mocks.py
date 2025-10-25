"""Reusable mock fixtures for fast unit testing."""

from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def mock_price_data() -> pd.DataFrame:
    """Return an in-memory price table for three assets across ten days."""

    start = datetime(2020, 1, 1)
    dates = [start + timedelta(days=idx) for idx in range(10)]
    symbols = ["AAPL", "GOOGL", "MSFT"]

    records: list[dict[str, object]] = []
    for symbol in symbols:
        for offset, date in enumerate(dates):
            records.append(
                {
                    "date": date,
                    "symbol": symbol,
                    "close": 100 + offset,
                    "volume": 1_000_000 + (offset * 10_000),
                }
            )

    return pd.DataFrame.from_records(records)


@pytest.fixture
def mock_returns() -> pd.DataFrame:
    """Return a deterministic returns matrix for five assets over one year."""

    np.random.seed(42)
    dates = pd.date_range(start="2020-01-01", periods=252, freq="B")
    assets = ["A", "B", "C", "D", "E"]

    data = np.random.normal(0.0005, 0.01, size=(len(dates), len(assets)))
    return pd.DataFrame(data, index=dates, columns=assets)


@pytest.fixture
def mock_weights() -> dict[str, float]:
    """Return evenly split mock portfolio weights."""

    return {"AAPL": 0.2, "GOOGL": 0.2, "MSFT": 0.2, "AMZN": 0.2, "TSLA": 0.2}


@pytest.fixture
def mock_covariance_matrix(mock_returns: pd.DataFrame) -> pd.DataFrame:
    """Return the covariance matrix corresponding to ``mock_returns``."""

    return mock_returns.cov()


@pytest.fixture
def mock_expected_returns(mock_returns: pd.DataFrame) -> pd.Series:
    """Return annualised expected returns derived from ``mock_returns``."""

    return mock_returns.mean() * 252

