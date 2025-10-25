"""Test configuration helpers."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


# Import mock fixtures for unit tests
from tests.fixtures.mocks import (  # noqa: E402, F401
    mock_price_data,
    mock_returns,
    mock_weights,
    mock_covariance_matrix,
    mock_expected_returns,
)


@pytest.fixture(autouse=True)
def reset_all_caches(tmp_path):
    """Clear all module-level caches before each test.

    This ensures test isolation and prevents state leakage between tests.
    Applied automatically to all tests via autouse=True.
    """
    # Import cache classes
    from portfolio_management.analytics.returns.loaders import PriceLoader
    from portfolio_management.portfolio.statistics.rolling_statistics import StatisticsCache
    from portfolio_management.data.factor_caching.factor_cache import FactorCache

    # For singleton-like caches, we need to clear them if they exist
    # This is a best-effort approach since we don't control instantiation

    # Note: If caches are instantiated as module-level singletons,
    # we'd need to import and clear them. Otherwise, this fixture
    # documents the pattern for test authors to follow.

    # Clear PriceLoader cache
    PriceLoader().clear_cache()

    yield  # Run the test

    # Cleanup after test (belt-and-suspenders approach)
    PriceLoader().clear_cache()


@pytest.fixture(autouse=True)
def reset_random_seed():
    """Reset random seed for reproducible tests.

    Some tests may use random number generation. This ensures
    they produce consistent results across runs.
    """
    import random
    import numpy as np

    random.seed(42)
    np.random.seed(42)

    yield


@pytest.fixture
def selection_test_matches() -> pd.DataFrame:
    """Fixture for selection test data."""
    return pd.read_csv("tests/fixtures/selection_test_data.csv")
