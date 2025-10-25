"""Test configuration helpers."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

from tests.fixtures.mocks import (  # noqa: F401
    mock_covariance_matrix,
    mock_expected_returns,
    mock_price_data,
    mock_returns,
    mock_weights,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


@pytest.fixture
def selection_test_matches() -> pd.DataFrame:
    """Fixture for selection test data."""
    return pd.read_csv("tests/fixtures/selection_test_data.csv")
