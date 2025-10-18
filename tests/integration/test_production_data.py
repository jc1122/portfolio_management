"""Integration tests that touch the production-sized configuration."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from portfolio_management.assets.universes import UniverseManager

pytestmark = pytest.mark.integration


def _require_path(path: Path) -> None:
    """Skip the current test if *path* does not exist."""
    if not path.exists():
        pytest.skip(f"Required test resource missing: {path}")


class TestProductionInputs:
    """Sanity checks that real data files remain consumable."""

    def test_real_match_report_loads(self) -> None:
        """The production match report should contain required columns."""
        path = Path("data/metadata/tradeable_matches.csv")
        _require_path(path)

        df = pd.read_csv(path)
        assert not df.empty
        required_columns = {
            "symbol",
            "isin",
            "name",
            "market",
            "region",
            "data_status",
            "stooq_path",
        }
        missing = required_columns - set(df.columns)
        assert not missing, f"Missing expected columns: {missing}"

    def test_predefined_universes_validate(self) -> None:
        """Universe definitions in the repo should validate successfully."""
        config_path = Path("config/universes.yaml")
        match_report = Path("data/metadata/tradeable_matches.csv")
        prices_dir = Path("data/processed/tradeable_prices")

        for required in (config_path, match_report, prices_dir):
            _require_path(required)

        matches_df = pd.read_csv(match_report)
        manager = UniverseManager(config_path, matches_df, prices_dir)

        universes = manager.list_universes()
        assert universes

        for universe_name in universes:
            definition = manager.get_definition(universe_name)
            definition.validate()

    @pytest.mark.slow
    def test_core_global_universe_loads(self) -> None:
        """The core_global sleeve should load end-to-end with production data."""
        config_path = Path("config/universes.yaml")
        match_report = Path("data/metadata/tradeable_matches.csv")
        prices_dir = Path("data/processed/tradeable_prices")

        for required in (config_path, match_report, prices_dir):
            _require_path(required)

        matches_df = pd.read_csv(match_report)
        manager = UniverseManager(config_path, matches_df, prices_dir)

        universe = manager.load_universe("core_global", use_cache=False)
        assert universe
        assert "returns" in universe
        assert not universe["returns"].empty
