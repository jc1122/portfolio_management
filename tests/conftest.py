"""Test configuration helpers."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

from tests.fixtures.mocks import (  # noqa: F401
    mock_backtest_config,
    mock_covariance_matrix,
    mock_expected_returns,
    mock_portfolio_constraints,
    mock_price_data,
    mock_returns,
    mock_selected_assets,
    mock_weights,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


@pytest.fixture
def selection_test_matches() -> pd.DataFrame:
    """Fixture for selection test data."""
    return pd.read_csv("tests/fixtures/selection_test_data.csv")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Automatically mark unit and integration tests based on their path."""

    root = Path(__file__).resolve().parent
    for item in items:
        try:
            relative = Path(item.fspath).resolve().relative_to(root)
        except ValueError:
            # Item outside repository tests directory; skip marking.
            continue

        if "unit" in relative.parts:
            item.add_marker("unit")
        else:
            item.add_marker("integration")
