"""Shared fixtures for integration tests."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest


@pytest.fixture(scope="session")
def integration_test_data_dir() -> Path:
    """Return the path to the lightweight price directory used for integration tests."""
    path = Path("data/processed/tradeable_prices_test")
    if not path.exists():
        pytest.skip("Test price directory not available; integration tests skipped.")
    return path


@pytest.fixture(scope="session")
def integration_match_report() -> pd.DataFrame:
    """Provide a trimmed match report for integration scenarios."""
    path = Path("data/metadata/tradeable_matches_test.csv")
    if not path.exists():
        pytest.skip("Integration match report not available.")
    df = pd.read_csv(path)
    # Use a manageable slice to keep tests fast.
    return df.head(100).copy()


@pytest.fixture(scope="session")
def integration_config_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Create a temporary universe configuration for integration tests."""
    tmp_dir = tmp_path_factory.mktemp("integration_config")
    config_path = tmp_dir / "test_universes.yaml"
    config_path.write_text(
        "\n".join(
            [
                "universes:",
                "  test_integration:",
                '    description: "Integration test universe"',
                "    filter_criteria:",
                "      data_status: ['ok']",
                "      min_history_days: 126",
                "      min_price_rows: 100",
                "    return_config:",
                "      method: 'simple'",
                "      frequency: 'daily'",
                "      handle_missing: 'forward_fill'",
                "      min_coverage: 0.3",
                "    constraints:",
                "      min_assets: 3",
                "      max_assets: 25",
            ],
        ),
        encoding="utf-8",
    )
    return config_path
