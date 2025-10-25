"""Test configuration helpers."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


# Re-export reusable mock fixtures for convenience across the suite.
from tests.fixtures.mocks import *  # noqa: F401,F403,E402


@pytest.fixture
def selection_test_matches() -> pd.DataFrame:
    """Fixture for selection test data."""
    return pd.read_csv("tests/fixtures/selection_test_data.csv")


INTEGRATION_PREFIXES: tuple[str, ...] = (
    "tests/data/",
    "tests/assets/",
    "tests/analytics/",
    "tests/portfolio/",
    "tests/backtesting/",
    "tests/scripts/",
    "tests/integration/",
    "tests/benchmarks/",
    "tests/macro/",
)


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Automatically tag integration tests based on their module path."""

    for item in items:
        node_path = item.nodeid.split("::", 1)[0]
        if any(node_path.startswith(prefix) for prefix in INTEGRATION_PREFIXES):
            item.add_marker(pytest.mark.integration)
