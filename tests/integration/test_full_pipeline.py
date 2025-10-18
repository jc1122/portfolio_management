"""End-to-end integration tests for the Phase 3 asset selection pipeline."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pandas as pd
import pytest

from src.portfolio_management.classification import AssetClassifier
from src.portfolio_management.exceptions import (
    ConfigurationError,
    ReturnCalculationError,
)
from src.portfolio_management.returns import ReturnCalculator, ReturnConfig
from src.portfolio_management.selection import AssetSelector, FilterCriteria
from src.portfolio_management.universes import UniverseManager

pytestmark = pytest.mark.integration


def _assets_with_price_files(
    assets: list,
    prices_dir: Path,
) -> list:
    """Return only assets with an associated price file on disk."""
    available: list = []
    for asset in assets:
        primary = prices_dir / asset.stooq_path
        fallback = prices_dir / f"{Path(asset.stooq_path).stem.lower()}.csv"
        if primary.exists() or fallback.exists():
            available.append(asset)
    return available


class TestEndToEndPipeline:
    """Smoke tests covering the selection → classification → returns pipeline."""

    def test_selection_to_classification_flow(
        self,
        integration_match_report: pd.DataFrame,
    ) -> None:
        """Selection and classification should produce aligned results."""
        criteria = FilterCriteria(
            data_status=["ok"],
            min_history_days=180,
            min_price_rows=180,
        )
        selector = AssetSelector()
        selected = selector.select_assets(integration_match_report, criteria)

        assert selected, "Expected at least one asset after selection stage."

        classifier = AssetClassifier()
        classified_df = classifier.classify_universe(selected)

        assert not classified_df.empty
        assert len(classified_df) == len(selected)
        assert "asset_class" in classified_df.columns
        assert list(classified_df["symbol"]) == [asset.symbol for asset in selected]

    def test_selection_to_returns_flow(
        self,
        integration_match_report: pd.DataFrame,
        integration_test_data_dir: Path,
    ) -> None:
        """Selected assets should yield return series when price files exist."""
        criteria = FilterCriteria(
            data_status=["ok"],
            min_history_days=252,
            min_price_rows=200,
        )
        selector = AssetSelector()
        selected = selector.select_assets(integration_match_report, criteria)
        available = _assets_with_price_files(selected, integration_test_data_dir)

        assert available, "Test dataset must contain assets with price files."

        config = ReturnConfig(
            method="simple",
            frequency="daily",
            handle_missing="forward_fill",
            min_coverage=0.3,
        )
        calculator = ReturnCalculator()
        returns = calculator.load_and_prepare(
            available[:20],
            integration_test_data_dir,
            config,
        )

        assert isinstance(returns, pd.DataFrame)
        assert not returns.empty
        assert returns.columns.any()

    def test_complete_universe_loading(
        self,
        integration_match_report: pd.DataFrame,
        integration_test_data_dir: Path,
        integration_config_path: Path,
    ) -> None:
        """UniverseManager should stitch the whole pipeline together."""
        manager = UniverseManager(
            integration_config_path,
            integration_match_report,
            integration_test_data_dir,
        )

        universes = manager.list_universes()
        assert "test_integration" in universes

        universe_data = manager.load_universe("test_integration", use_cache=False)
        assert universe_data
        assert "assets" in universe_data
        assert "classifications" in universe_data
        assert "returns" in universe_data
        assert universe_data["returns"].shape[1] <= 25


class TestMultiUniverseIntegration:
    """Validate that multiple universes can be handled in isolation."""

    def test_load_multiple_universes(
        self,
        integration_match_report: pd.DataFrame,
        integration_test_data_dir: Path,
        tmp_path: Path,
    ) -> None:
        """Loading distinct universes should not interfere with one another."""
        config_path = tmp_path / "multi_universes.yaml"
        config_path.write_text(
            textwrap.dedent(
                """
                universes:
                  universe_a:
                    description: "Universe A"
                    filter_criteria:
                      data_status: ['ok']
                      min_history_days: 200
                    return_config:
                      method: 'simple'
                    constraints:
                      max_assets: 10
                  universe_b:
                    description: "Universe B"
                    filter_criteria:
                      data_status: ['ok', 'warning']
                      min_history_days: 120
                    return_config:
                      method: 'log'
                    constraints:
                      max_assets: 15
                """,
            ).strip(),
            encoding="utf-8",
        )

        manager = UniverseManager(
            config_path,
            integration_match_report,
            integration_test_data_dir,
        )

        universe_a = manager.load_universe("universe_a", use_cache=False)
        universe_b = manager.load_universe("universe_b", use_cache=False)

        assert universe_a and universe_b
        assert universe_a["returns"].shape[1] <= 10
        assert universe_b["returns"].shape[1] <= 15


class TestErrorScenarios:
    """Ensure error scenarios degrade gracefully."""

    def test_empty_selection_result(
        self,
        integration_match_report: pd.DataFrame,
    ) -> None:
        """Impossibly strict filters should yield no assets without crashing."""
        criteria = FilterCriteria(
            data_status=["__nonexistent__"],
            min_history_days=10_000,
        )
        selector = AssetSelector()
        selected = selector.select_assets(integration_match_report, criteria)
        assert selected == []

    def test_missing_price_files(
        self,
        integration_match_report: pd.DataFrame,
        tmp_path: Path,
    ) -> None:
        """Missing price directory should trigger a handled error."""
        criteria = FilterCriteria(data_status=["ok"])
        selector = AssetSelector()
        selected = selector.select_assets(integration_match_report, criteria)[:5]

        calculator = ReturnCalculator()
        with pytest.raises(ReturnCalculationError):
            calculator.load_and_prepare(selected, tmp_path / "missing", ReturnConfig())

    def test_invalid_universe_config(
        self,
        integration_match_report: pd.DataFrame,
        integration_test_data_dir: Path,
        tmp_path: Path,
    ) -> None:
        """Invalid universe configuration should raise an error."""
        bad_config = tmp_path / "invalid_config.yaml"
        bad_config.write_text(
            textwrap.dedent(
                """
                universes:
                  invalid:
                    description: "Bad configuration"
                    filter_criteria:
                      min_history_days: -100
                """,
            ).strip(),
            encoding="utf-8",
        )

        with pytest.raises(ConfigurationError):
            UniverseManager(
                bad_config, integration_match_report, integration_test_data_dir
            )
