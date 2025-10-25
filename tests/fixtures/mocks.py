"""Reusable mock fixtures for fast unit testing."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest

from portfolio_management.assets.selection.selection import SelectedAsset
from portfolio_management.portfolio.constraints.models import PortfolioConstraints


@pytest.fixture
def mock_price_data() -> pd.DataFrame:
    """Return a small price DataFrame without touching disk."""
    dates = pd.date_range("2020-01-01", periods=10, freq="D")
    data = {
        "AAA": np.linspace(100, 110, num=10),
        "BBB": np.linspace(50, 55, num=10),
        "CCC": np.linspace(200, 210, num=10),
    }
    return pd.DataFrame(data, index=dates)


@pytest.fixture
def mock_returns(mock_price_data: pd.DataFrame) -> pd.DataFrame:
    """Compute simple returns from the in-memory price data."""
    return mock_price_data.pct_change().fillna(0.0)


@pytest.fixture
def mock_weights() -> pd.Series:
    """Provide a set of portfolio weights that sum to one."""
    return pd.Series({"AAA": 0.4, "BBB": 0.35, "CCC": 0.25})


@pytest.fixture
def mock_covariance_matrix(mock_returns: pd.DataFrame) -> pd.DataFrame:
    """Return a covariance matrix derived from the mock returns."""
    return mock_returns.cov()


@pytest.fixture
def mock_expected_returns(mock_returns: pd.DataFrame) -> pd.Series:
    """Return mean returns for each asset."""
    return mock_returns.mean()


@pytest.fixture
def mock_selected_assets() -> list[SelectedAsset]:
    """Create a small list of selected assets for testing."""
    return [
        SelectedAsset(
            symbol="AAA",
            isin="US000000AAA0",
            name="AAA Corp",
            market="US",
            region="North America",
            currency="USD",
            category="Stock",
            price_start="2019-01-01",
            price_end="2020-12-31",
            price_rows=500,
            data_status="ok",
            data_flags="",
            stooq_path="dummy/aaa.txt",
            resolved_currency="USD",
            currency_status="matched",
        ),
        SelectedAsset(
            symbol="BBB",
            isin="US000000BBB0",
            name="BBB Corp",
            market="US",
            region="North America",
            currency="USD",
            category="Stock",
            price_start="2019-01-01",
            price_end="2020-12-31",
            price_rows=500,
            data_status="ok",
            data_flags="",
            stooq_path="dummy/bbb.txt",
            resolved_currency="USD",
            currency_status="matched",
        ),
        SelectedAsset(
            symbol="CCC",
            isin="US000000CCC0",
            name="CCC Corp",
            market="US",
            region="North America",
            currency="USD",
            category="Stock",
            price_start="2019-01-01",
            price_end="2020-12-31",
            price_rows=500,
            data_status="ok",
            data_flags="",
            stooq_path="dummy/ccc.txt",
            resolved_currency="USD",
            currency_status="matched",
        ),
    ]


@pytest.fixture
def mock_portfolio_constraints() -> PortfolioConstraints:
    """Return permissive portfolio constraints for unit testing."""
    return PortfolioConstraints(max_weight=0.6, min_bond_exposure=0.0)


@pytest.fixture
def mock_backtest_config() -> tuple[date, date, Decimal]:
    """Provide reusable start/end dates and capital for backtest tests."""
    start = date(2020, 1, 1)
    end = start + timedelta(days=9)
    return start, end, Decimal("100000")
