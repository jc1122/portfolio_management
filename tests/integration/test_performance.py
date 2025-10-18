"""Lightweight performance benchmarks for the Phase 3 pipeline."""

from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
import pytest

from portfolio_management.analytics.returns import ReturnCalculator, ReturnConfig
from portfolio_management.assets.classification import AssetClassifier
from portfolio_management.assets.selection import AssetSelector, FilterCriteria

pytestmark = [pytest.mark.integration]


def _available_assets(
    matches: pd.DataFrame,
    prices_dir: Path,
    limit: int,
) -> list:
    """Return up to *limit* assets that have price files present."""
    selector = AssetSelector()
    criteria = FilterCriteria(
        data_status=["ok"],
        min_history_days=180,
        min_price_rows=150,
    )
    selected = selector.select_assets(matches, criteria)
    assets = []
    for asset in selected:
        primary = prices_dir / asset.stooq_path
        fallback = prices_dir / f"{Path(asset.stooq_path).stem.lower()}.csv"
        if primary.exists() or fallback.exists():
            assets.append(asset)
        if len(assets) >= limit:
            break
    return assets


class TestPerformance:
    """Measure approximate runtime for key pipeline stages."""

    def test_selection_performance_100_assets(
        self,
        integration_match_report: pd.DataFrame,
    ) -> None:
        """Selecting 100 assets should be fast on the trimmed dataset."""
        df = integration_match_report.head(200)
        criteria = FilterCriteria(
            data_status=["ok", "warning"],
            min_history_days=120,
            min_price_rows=120,
        )
        selector = AssetSelector()

        start = time.perf_counter()
        result = selector.select_assets(df, criteria)
        elapsed = time.perf_counter() - start

        assert result
        # Allow generous threshold to avoid flaky CI while still flagging regressions.
        assert elapsed < 5.0, f"Selection took too long: {elapsed:.2f}s"

    def test_classification_performance_100_assets(
        self,
        integration_match_report: pd.DataFrame,
    ) -> None:
        """Classifying 100 assets should complete quickly."""
        df = integration_match_report.head(150)
        criteria = FilterCriteria(data_status=["ok"], min_history_days=100)
        selector = AssetSelector()
        assets = selector.select_assets(df, criteria)[:100]

        start = time.perf_counter()
        classified = AssetClassifier().classify_universe(assets)
        elapsed = time.perf_counter() - start

        assert not classified.empty
        assert elapsed < 5.0, f"Classification exceeded time budget: {elapsed:.2f}s"

    def test_returns_performance_40_assets(
        self,
        integration_match_report: pd.DataFrame,
        integration_test_data_dir: Path,
    ) -> None:
        """Return calculation for ~40 assets should fit within a reasonable budget."""
        assets = _available_assets(
            integration_match_report, integration_test_data_dir, limit=40
        )
        assert assets, "Expected at least one asset with price data."

        config = ReturnConfig(method="simple", frequency="daily", min_coverage=0.3)
        calculator = ReturnCalculator()

        start = time.perf_counter()
        returns = calculator.load_and_prepare(assets, integration_test_data_dir, config)
        elapsed = time.perf_counter() - start

        assert not returns.empty
        assert (
            elapsed < 12.0
        ), f"Return calculation exceeded time budget: {elapsed:.2f}s"

    @pytest.mark.slow
    def test_full_pipeline_performance(
        self,
        integration_match_report: pd.DataFrame,
        integration_test_data_dir: Path,
    ) -> None:
        """Full selection → returns pipeline should complete without regressions."""
        assets = _available_assets(
            integration_match_report, integration_test_data_dir, limit=80
        )
        config = ReturnConfig(min_coverage=0.3)
        calculator = ReturnCalculator()

        start = time.perf_counter()
        returns = calculator.load_and_prepare(assets, integration_test_data_dir, config)
        elapsed = time.perf_counter() - start

        assert elapsed < 60.0, f"Full pipeline took too long: {elapsed:.2f}s"
        assert returns.shape[1] <= 80
