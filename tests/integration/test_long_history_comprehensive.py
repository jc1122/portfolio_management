"""Comprehensive integration tests using 20 years of historical data (2005-2025).

This module tests all Sprint 2 features working together over long time periods:
- Strategy types: Equal weight, Mean-variance, Risk parity
- Feature combinations: Preselection, membership policy, PIT eligibility, caching, fast IO
- Factor combinations: Momentum, low volatility, combined factors
- Market regimes: 2007-2008 crisis, 2020 COVID crash, 2021-2022 bull/correction

Tests validate:
- Determinism: Multiple runs produce identical results
- Backward compatibility: Results without features match baseline
- Correctness: Preselection ranks, membership transitions, PIT dates correct
- Performance: Reasonable execution time (<20 min per test)
- No lookahead: PIT eligibility prevents future data usage
"""

from __future__ import annotations

import datetime
import tempfile
import time
from decimal import Decimal
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest

from portfolio_management.backtesting import (
    BacktestConfig,
    BacktestEngine,
    RebalanceFrequency,
)
from portfolio_management.data.factor_caching import FactorCache
from portfolio_management.portfolio import (
    EqualWeightStrategy,
    MeanVarianceStrategy,
    MembershipPolicy,
    Preselection,
    PreselectionConfig,
    PreselectionMethod,
    RiskParityStrategy,
)

# Mark all tests in this module as integration and slow
pytestmark = [pytest.mark.integration, pytest.mark.slow]

# Data file paths
LONG_HISTORY_DIR = Path("outputs/long_history_1000")
PRICES_FILE = LONG_HISTORY_DIR / "long_history_1000_prices_daily.csv"
RETURNS_FILE = LONG_HISTORY_DIR / "long_history_1000_returns_daily.csv"
SELECTION_FILE = LONG_HISTORY_DIR / "long_history_1000_selection.csv"


@pytest.fixture(scope="module")
def long_history_data():
    """Load 20-year historical price and return data.

    Returns:
        tuple: (prices DataFrame, returns DataFrame, selection metadata DataFrame)

    Skips if data not available.
    """
    if not PRICES_FILE.exists() or not RETURNS_FILE.exists():
        pytest.skip(
            "Long history data not available. "
            "Expected files in outputs/long_history_1000/"
        )

    # Load prices
    prices = pd.read_csv(PRICES_FILE, index_col=0, parse_dates=True)

    # Load returns
    returns = pd.read_csv(RETURNS_FILE, index_col=0, parse_dates=True)

    # Load selection metadata if available
    selection = None
    if SELECTION_FILE.exists():
        selection = pd.read_csv(SELECTION_FILE)

    # Verify data quality
    assert len(prices) > 4000, "Expected ~5000 days of data (20 years)"
    assert len(returns) > 4000, "Expected ~5000 days of returns"
    assert len(prices.columns) >= 100, "Expected at least 100 assets"

    # Verify date range covers 2005-2025
    assert prices.index.min().year <= 2006, "Data should start around 2005"
    assert prices.index.max().year >= 2024, "Data should extend to 2024+"

    return prices, returns, selection


@pytest.fixture
def temp_cache_dir():
    """Create temporary cache directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestEqualWeightLongHistory:
    """Test equal weight strategy with 20-year history."""

    def test_equal_weight_momentum_preselection_20_years(self, long_history_data):
        """Test equal weight + momentum preselection over 20 years."""
        prices, returns, _ = long_history_data

        config = BacktestConfig(
            start_date=datetime.date(2006, 1, 1),
            end_date=datetime.date(2024, 12, 31),
            initial_capital=Decimal(100000),
            rebalance_frequency=RebalanceFrequency.MONTHLY,
        )

        preselection_config = PreselectionConfig(
            method=PreselectionMethod.MOMENTUM,
            top_k=30,
            lookback=252,  # 1 year
            skip=21,  # 1 month
        )
        preselection = Preselection(preselection_config)

        strategy = EqualWeightStrategy()

        start_time = time.time()
        engine = BacktestEngine(
            config=config,
            strategy=strategy,
            prices=prices,
            returns=returns,
            preselection=preselection,
        )

        equity_curve, metrics, events = engine.run()
        elapsed_time = time.time() - start_time

        # Validation
        assert len(equity_curve) > 0, "Should have equity curve data"
        assert len(events) > 0, "Should have rebalance events"
        assert len(events) >= 200, "Should have ~228 monthly rebalances over 19 years"

        # Performance characteristics
        assert metrics.total_return != 0, "Should have non-zero total return"
        assert metrics.sharpe_ratio is not None, "Should calculate Sharpe ratio"

        # Execution time should be reasonable (<20 minutes)
        assert elapsed_time < 1200, f"Test took {elapsed_time:.1f}s, expected <1200s"

        # Verify preselection worked (should have ~30 assets per rebalance)
        for event in events[:10]:  # Check first 10 rebalances
            assert len(event.new_weights) <= 30, "Should respect top_k constraint"
            assert len(event.new_weights) > 0, "Should have selected some assets"

    def test_equal_weight_membership_policy_20_years(self, long_history_data):
        """Test equal weight + membership policy over 20 years."""
        prices, returns, _ = long_history_data

        config = BacktestConfig(
            start_date=datetime.date(2006, 1, 1),
            end_date=datetime.date(2024, 12, 31),
            initial_capital=Decimal(100000),
            rebalance_frequency=RebalanceFrequency.QUARTERLY,
        )

        preselection_config = PreselectionConfig(
            method=PreselectionMethod.MOMENTUM,
            top_k=50,
            lookback=252,
            skip=21,
        )
        preselection = Preselection(preselection_config)

        membership_policy = MembershipPolicy(
            buffer_rank=60,  # 10 asset buffer
            min_holding_periods=3,  # Hold for at least 3 quarters
            max_turnover=0.30,  # Max 30% turnover per rebalance
            max_new_assets=10,
            max_removed_assets=10,
            enabled=True,
        )

        strategy = EqualWeightStrategy()

        engine = BacktestEngine(
            config=config,
            strategy=strategy,
            prices=prices,
            returns=returns,
            preselection=preselection,
            membership_policy=membership_policy,
        )

        equity_curve, metrics, events = engine.run()

        # Validation
        assert len(equity_curve) > 0
        assert len(events) >= 70, "Should have ~76 quarterly rebalances"

        # Verify membership policy constraints are honored
        for i, event in enumerate(events[1:], start=1):
            prev_assets = set(events[i - 1].new_weights.keys())
            curr_assets = set(event.new_weights.keys())

            added = curr_assets - prev_assets
            removed = prev_assets - curr_assets

            # Check max turnover constraints
            assert len(added) <= 10, f"Event {i}: Too many assets added ({len(added)})"
            assert (
                len(removed) <= 10
            ), f"Event {i}: Too many assets removed ({len(removed)})"

    def test_equal_weight_all_features_20_years(self, long_history_data, temp_cache_dir):
        """Test equal weight with ALL features enabled over 20 years."""
        prices, returns, _ = long_history_data

        config = BacktestConfig(
            start_date=datetime.date(2006, 1, 1),
            end_date=datetime.date(2024, 12, 31),
            initial_capital=Decimal(100000),
            rebalance_frequency=RebalanceFrequency.QUARTERLY,
            use_pit_eligibility=True,
            min_history_days=252,  # 1 year minimum history
            min_price_rows=200,
        )

        preselection_config = PreselectionConfig(
            method=PreselectionMethod.MOMENTUM,
            top_k=30,
            lookback=252,
            skip=21,
        )

        factor_cache = FactorCache(temp_cache_dir, enabled=True)
        preselection = Preselection(preselection_config, cache=factor_cache)

        membership_policy = MembershipPolicy(
            buffer_rank=35,
            min_holding_periods=2,
            max_turnover=0.40,
            max_new_assets=8,
            max_removed_assets=8,
            enabled=True,
        )

        strategy = EqualWeightStrategy()

        engine = BacktestEngine(
            config=config,
            strategy=strategy,
            prices=prices,
            returns=returns,
            preselection=preselection,
            membership_policy=membership_policy,
        )

        equity_curve, metrics, events = engine.run()

        # Validation
        assert len(equity_curve) > 0
        assert len(events) > 0

        # Check cache was used
        cache_stats = factor_cache.get_stats()
        assert (
            cache_stats["puts"] > 0
        ), "Cache should have stored factor computations"
        assert cache_stats["hits"] + cache_stats["misses"] > 0, "Cache should be queried"


class TestMeanVarianceLongHistory:
    """Test mean-variance optimization with 20-year history."""

    def test_mean_variance_low_vol_preselection_20_years(self, long_history_data):
        """Test mean-variance + low volatility preselection over 20 years."""
        prices, returns, _ = long_history_data

        config = BacktestConfig(
            start_date=datetime.date(2006, 1, 1),
            end_date=datetime.date(2024, 12, 31),
            initial_capital=Decimal(100000),
            rebalance_frequency=RebalanceFrequency.QUARTERLY,
        )

        preselection_config = PreselectionConfig(
            method=PreselectionMethod.LOW_VOL,
            top_k=30,
            lookback=252,
        )
        preselection = Preselection(preselection_config)

        strategy = MeanVarianceStrategy()

        start_time = time.time()
        engine = BacktestEngine(
            config=config,
            strategy=strategy,
            prices=prices,
            returns=returns,
            preselection=preselection,
        )

        equity_curve, metrics, events = engine.run()
        elapsed_time = time.time() - start_time

        # Validation
        assert len(equity_curve) > 0
        assert len(events) > 0

        # Mean-variance should produce concentrated portfolios
        avg_portfolio_size = sum(len(e.new_weights) for e in events) / len(events)
        assert (
            avg_portfolio_size <= 30
        ), "Mean-variance should respect top_k preselection"

        # Execution time
        assert elapsed_time < 1200, f"Test took {elapsed_time:.1f}s, expected <1200s"

    def test_mean_variance_membership_20_years(self, long_history_data):
        """Test mean-variance + membership policy over 20 years."""
        prices, returns, _ = long_history_data

        config = BacktestConfig(
            start_date=datetime.date(2006, 1, 1),
            end_date=datetime.date(2024, 12, 31),
            initial_capital=Decimal(100000),
            rebalance_frequency=RebalanceFrequency.QUARTERLY,
        )

        preselection_config = PreselectionConfig(
            method=PreselectionMethod.LOW_VOL,
            top_k=40,
            lookback=252,
        )
        preselection = Preselection(preselection_config)

        membership_policy = MembershipPolicy(
            buffer_rank=45,
            min_holding_periods=2,
            max_turnover=0.35,
            max_new_assets=10,
            max_removed_assets=10,
            enabled=True,
        )

        strategy = MeanVarianceStrategy()

        engine = BacktestEngine(
            config=config,
            strategy=strategy,
            prices=prices,
            returns=returns,
            preselection=preselection,
            membership_policy=membership_policy,
        )

        equity_curve, metrics, events = engine.run()

        # Validation
        assert len(equity_curve) > 0
        assert len(events) > 0


class TestRiskParityLongHistory:
    """Test risk parity strategy with 20-year history."""

    def test_risk_parity_combined_factors_20_years(self, long_history_data):
        """Test risk parity + combined factors (momentum + low vol) over 20 years."""
        prices, returns, _ = long_history_data

        config = BacktestConfig(
            start_date=datetime.date(2006, 1, 1),
            end_date=datetime.date(2024, 12, 31),
            initial_capital=Decimal(100000),
            rebalance_frequency=RebalanceFrequency.QUARTERLY,
        )

        preselection_config = PreselectionConfig(
            method=PreselectionMethod.COMBINED,
            top_k=30,
            lookback=252,
            skip=21,
            momentum_weight=0.5,
            low_vol_weight=0.5,
        )
        preselection = Preselection(preselection_config)

        strategy = RiskParityStrategy()

        start_time = time.time()
        engine = BacktestEngine(
            config=config,
            strategy=strategy,
            prices=prices,
            returns=returns,
            preselection=preselection,
        )

        equity_curve, metrics, events = engine.run()
        elapsed_time = time.time() - start_time

        # Validation
        assert len(equity_curve) > 0
        assert len(events) > 0

        # Risk parity should produce more balanced portfolios
        for event in events[:5]:  # Check first 5 rebalances
            weights = list(event.new_weights.values())
            # Risk parity aims for equal risk contribution, so weights should be relatively balanced
            if len(weights) > 0:
                max_weight = max(weights)
                min_weight = min(weights)
                # No single asset should dominate (max < 20% ideally)
                assert max_weight < 0.30, "Risk parity should avoid concentration"

        # Execution time
        assert elapsed_time < 1200, f"Test took {elapsed_time:.1f}s, expected <1200s"

    def test_risk_parity_all_features_20_years(
        self, long_history_data, temp_cache_dir
    ):
        """Test risk parity with all features enabled over 20 years."""
        prices, returns, _ = long_history_data

        config = BacktestConfig(
            start_date=datetime.date(2006, 1, 1),
            end_date=datetime.date(2024, 12, 31),
            initial_capital=Decimal(100000),
            rebalance_frequency=RebalanceFrequency.QUARTERLY,
            use_pit_eligibility=True,
            min_history_days=252,
            min_price_rows=200,
        )

        preselection_config = PreselectionConfig(
            method=PreselectionMethod.COMBINED,
            top_k=25,
            lookback=252,
            skip=21,
            momentum_weight=0.6,
            low_vol_weight=0.4,
        )

        factor_cache = FactorCache(temp_cache_dir, enabled=True)
        preselection = Preselection(preselection_config, cache=factor_cache)

        membership_policy = MembershipPolicy(
            buffer_rank=30,
            min_holding_periods=3,
            max_turnover=0.30,
            max_new_assets=5,
            max_removed_assets=5,
            enabled=True,
        )

        strategy = RiskParityStrategy()

        engine = BacktestEngine(
            config=config,
            strategy=strategy,
            prices=prices,
            returns=returns,
            preselection=preselection,
            membership_policy=membership_policy,
        )

        equity_curve, metrics, events = engine.run()

        # Validation
        assert len(equity_curve) > 0
        assert len(events) > 0


class TestDeterminismAndBackwardCompatibility:
    """Test determinism and backward compatibility."""

    def test_determinism_multiple_runs(self, long_history_data):
        """Test that running the same configuration 3 times produces identical results."""
        prices, returns, _ = long_history_data

        config = BacktestConfig(
            start_date=datetime.date(2010, 1, 1),
            end_date=datetime.date(2015, 12, 31),
            initial_capital=Decimal(100000),
            rebalance_frequency=RebalanceFrequency.QUARTERLY,
        )

        preselection_config = PreselectionConfig(
            method=PreselectionMethod.MOMENTUM,
            top_k=30,
            lookback=252,
            skip=21,
        )

        strategy = EqualWeightStrategy()

        results = []
        for i in range(3):
            preselection = Preselection(preselection_config)
            engine = BacktestEngine(
                config=config,
                strategy=strategy,
                prices=prices,
                returns=returns,
                preselection=preselection,
            )

            equity_curve, metrics, events = engine.run()
            results.append(
                {
                    "equity_curve": equity_curve,
                    "total_return": metrics.total_return,
                    "sharpe_ratio": metrics.sharpe_ratio,
                    "max_drawdown": metrics.max_drawdown,
                    "num_events": len(events),
                }
            )

        # All runs should produce identical results
        assert (
            results[0]["total_return"] == results[1]["total_return"]
        ), "Run 1 and 2 should match"
        assert (
            results[0]["total_return"] == results[2]["total_return"]
        ), "Run 1 and 3 should match"
        assert (
            results[0]["sharpe_ratio"] == results[1]["sharpe_ratio"]
        ), "Sharpe ratios should match"
        assert results[0]["num_events"] == results[1]["num_events"], "Event counts should match"

        # Equity curves should be identical
        pd.testing.assert_series_equal(
            results[0]["equity_curve"],
            results[1]["equity_curve"],
            check_names=False,
        )
        pd.testing.assert_series_equal(
            results[0]["equity_curve"],
            results[2]["equity_curve"],
            check_names=False,
        )

    def test_backward_compatibility_features_disabled(self, long_history_data):
        """Test that results without features match baseline behavior."""
        prices, returns, _ = long_history_data

        config = BacktestConfig(
            start_date=datetime.date(2010, 1, 1),
            end_date=datetime.date(2015, 12, 31),
            initial_capital=Decimal(100000),
            rebalance_frequency=RebalanceFrequency.QUARTERLY,
            use_pit_eligibility=False,  # Disabled
        )

        strategy = EqualWeightStrategy()

        # Run 1: Completely baseline (no features)
        engine1 = BacktestEngine(
            config=config,
            strategy=strategy,
            prices=prices,
            returns=returns,
        )
        equity_curve1, metrics1, events1 = engine1.run()

        # Run 2: Features explicitly passed but disabled
        disabled_policy = MembershipPolicy(enabled=False)
        engine2 = BacktestEngine(
            config=config,
            strategy=strategy,
            prices=prices,
            returns=returns,
            membership_policy=disabled_policy,
        )
        equity_curve2, metrics2, events2 = engine2.run()

        # Results should be identical
        assert metrics1.total_return == metrics2.total_return
        assert len(events1) == len(events2)
        pd.testing.assert_series_equal(equity_curve1, equity_curve2, check_names=False)

    def test_cached_vs_uncached_equivalence(self, long_history_data, temp_cache_dir):
        """Test that cached and uncached runs produce identical results."""
        prices, returns, _ = long_history_data

        config = BacktestConfig(
            start_date=datetime.date(2010, 1, 1),
            end_date=datetime.date(2015, 12, 31),
            initial_capital=Decimal(100000),
            rebalance_frequency=RebalanceFrequency.QUARTERLY,
        )

        preselection_config = PreselectionConfig(
            method=PreselectionMethod.MOMENTUM,
            top_k=30,
            lookback=252,
            skip=21,
        )

        strategy = EqualWeightStrategy()

        # Run without cache
        preselection_no_cache = Preselection(preselection_config, cache=None)
        engine_no_cache = BacktestEngine(
            config=config,
            strategy=strategy,
            prices=prices,
            returns=returns,
            preselection=preselection_no_cache,
        )
        equity_curve_no_cache, metrics_no_cache, events_no_cache = engine_no_cache.run()

        # Run with cache (first run will populate cache)
        factor_cache = FactorCache(temp_cache_dir, enabled=True)
        preselection_cached = Preselection(preselection_config, cache=factor_cache)
        engine_cached = BacktestEngine(
            config=config,
            strategy=strategy,
            prices=prices,
            returns=returns,
            preselection=preselection_cached,
        )
        equity_curve_cached, metrics_cached, events_cached = engine_cached.run()

        # Results should be identical
        assert metrics_no_cache.total_return == metrics_cached.total_return
        assert metrics_no_cache.sharpe_ratio == metrics_cached.sharpe_ratio
        assert len(events_no_cache) == len(events_cached)
        pd.testing.assert_series_equal(
            equity_curve_no_cache, equity_curve_cached, check_names=False
        )

        # Verify cache was actually used
        cache_stats = factor_cache.get_stats()
        assert cache_stats["puts"] > 0, "Cache should have stored results"


class TestMarketRegimes:
    """Test behavior across different market regimes."""

    def test_financial_crisis_2007_2008(self, long_history_data):
        """Test backtest during 2007-2008 financial crisis."""
        prices, returns, _ = long_history_data

        config = BacktestConfig(
            start_date=datetime.date(2007, 1, 1),
            end_date=datetime.date(2009, 12, 31),
            initial_capital=Decimal(100000),
            rebalance_frequency=RebalanceFrequency.QUARTERLY,
        )

        preselection_config = PreselectionConfig(
            method=PreselectionMethod.LOW_VOL,  # Low vol should help in crisis
            top_k=30,
            lookback=252,
        )
        preselection = Preselection(preselection_config)

        strategy = EqualWeightStrategy()

        engine = BacktestEngine(
            config=config,
            strategy=strategy,
            prices=prices,
            returns=returns,
            preselection=preselection,
        )

        equity_curve, metrics, events = engine.run()

        # Validation
        assert len(equity_curve) > 0
        assert len(events) > 0

        # During crisis, expect negative returns but valid metrics
        assert metrics.total_return is not None
        assert metrics.max_drawdown is not None
        assert metrics.max_drawdown < 0, "Should have drawdown during crisis"

    def test_covid_crash_2020(self, long_history_data):
        """Test backtest during 2020 COVID crash and recovery."""
        prices, returns, _ = long_history_data

        config = BacktestConfig(
            start_date=datetime.date(2019, 1, 1),
            end_date=datetime.date(2021, 12, 31),
            initial_capital=Decimal(100000),
            rebalance_frequency=RebalanceFrequency.MONTHLY,
        )

        preselection_config = PreselectionConfig(
            method=PreselectionMethod.COMBINED,
            top_k=30,
            lookback=252,
            skip=21,
            momentum_weight=0.5,
            low_vol_weight=0.5,
        )
        preselection = Preselection(preselection_config)

        strategy = RiskParityStrategy()

        engine = BacktestEngine(
            config=config,
            strategy=strategy,
            prices=prices,
            returns=returns,
            preselection=preselection,
        )

        equity_curve, metrics, events = engine.run()

        # Validation
        assert len(equity_curve) > 0
        assert len(events) > 0

        # Should have captured crash and recovery
        assert metrics.max_drawdown < 0, "Should show drawdown during March 2020"

    def test_bull_market_2021_2022(self, long_history_data):
        """Test backtest during 2021-2022 bull market and correction."""
        prices, returns, _ = long_history_data

        config = BacktestConfig(
            start_date=datetime.date(2021, 1, 1),
            end_date=datetime.date(2023, 12, 31),
            initial_capital=Decimal(100000),
            rebalance_frequency=RebalanceFrequency.MONTHLY,
        )

        preselection_config = PreselectionConfig(
            method=PreselectionMethod.MOMENTUM,
            top_k=30,
            lookback=252,
            skip=21,
        )
        preselection = Preselection(preselection_config)

        strategy = MeanVarianceStrategy()

        engine = BacktestEngine(
            config=config,
            strategy=strategy,
            prices=prices,
            returns=returns,
            preselection=preselection,
        )

        equity_curve, metrics, events = engine.run()

        # Validation
        assert len(equity_curve) > 0
        assert len(events) > 0


class TestValidationChecks:
    """Validation tests for correctness."""

    def test_pit_eligibility_no_lookahead(self, long_history_data):
        """Test that PIT eligibility prevents lookahead bias."""
        prices, returns, _ = long_history_data

        config = BacktestConfig(
            start_date=datetime.date(2010, 1, 1),
            end_date=datetime.date(2015, 12, 31),
            initial_capital=Decimal(100000),
            rebalance_frequency=RebalanceFrequency.QUARTERLY,
            use_pit_eligibility=True,
            min_history_days=252,  # Require 1 year of history
            min_price_rows=200,
        )

        strategy = EqualWeightStrategy()

        engine = BacktestEngine(
            config=config,
            strategy=strategy,
            prices=prices,
            returns=returns,
        )

        equity_curve, metrics, events = engine.run()

        # Validation: Check that early events have fewer eligible assets
        # (because not all assets will have 252 days of history yet)
        first_event = events[0]
        last_event = events[-1]

        # First event should have fewer assets than last (as more become eligible over time)
        # This validates PIT filtering is working
        assert len(first_event.new_weights) <= len(
            last_event.new_weights
        ), "Early rebalances should have fewer eligible assets"

    def test_preselection_top_k_honored(self, long_history_data):
        """Test that preselection top_k constraint is honored."""
        prices, returns, _ = long_history_data

        config = BacktestConfig(
            start_date=datetime.date(2010, 1, 1),
            end_date=datetime.date(2015, 12, 31),
            initial_capital=Decimal(100000),
            rebalance_frequency=RebalanceFrequency.QUARTERLY,
        )

        top_k = 25
        preselection_config = PreselectionConfig(
            method=PreselectionMethod.MOMENTUM,
            top_k=top_k,
            lookback=252,
            skip=21,
        )
        preselection = Preselection(preselection_config)

        strategy = EqualWeightStrategy()

        engine = BacktestEngine(
            config=config,
            strategy=strategy,
            prices=prices,
            returns=returns,
            preselection=preselection,
        )

        equity_curve, metrics, events = engine.run()

        # Verify all events respect top_k
        for event in events:
            assert (
                len(event.new_weights) <= top_k
            ), f"Event has {len(event.new_weights)} assets, expected <= {top_k}"

    def test_membership_policy_constraints(self, long_history_data):
        """Test that membership policy constraints are honored."""
        prices, returns, _ = long_history_data

        config = BacktestConfig(
            start_date=datetime.date(2010, 1, 1),
            end_date=datetime.date(2015, 12, 31),
            initial_capital=Decimal(100000),
            rebalance_frequency=RebalanceFrequency.QUARTERLY,
        )

        preselection_config = PreselectionConfig(
            method=PreselectionMethod.MOMENTUM,
            top_k=40,
            lookback=252,
            skip=21,
        )
        preselection = Preselection(preselection_config)

        max_new = 8
        max_removed = 8
        membership_policy = MembershipPolicy(
            buffer_rank=45,
            min_holding_periods=2,
            max_turnover=0.30,
            max_new_assets=max_new,
            max_removed_assets=max_removed,
            enabled=True,
        )

        strategy = EqualWeightStrategy()

        engine = BacktestEngine(
            config=config,
            strategy=strategy,
            prices=prices,
            returns=returns,
            preselection=preselection,
            membership_policy=membership_policy,
        )

        equity_curve, metrics, events = engine.run()

        # Verify membership constraints
        for i in range(1, len(events)):
            prev_assets = set(events[i - 1].new_weights.keys())
            curr_assets = set(events[i].new_weights.keys())

            added = curr_assets - prev_assets
            removed = prev_assets - curr_assets

            assert (
                len(added) <= max_new
            ), f"Event {i}: Added {len(added)} assets, max allowed {max_new}"
            assert (
                len(removed) <= max_removed
            ), f"Event {i}: Removed {len(removed)} assets, max allowed {max_removed}"

    def test_cache_hit_rates(self, long_history_data, temp_cache_dir):
        """Test that caching provides good hit rates on repeated runs."""
        prices, returns, _ = long_history_data

        config = BacktestConfig(
            start_date=datetime.date(2010, 1, 1),
            end_date=datetime.date(2015, 12, 31),
            initial_capital=Decimal(100000),
            rebalance_frequency=RebalanceFrequency.QUARTERLY,
        )

        preselection_config = PreselectionConfig(
            method=PreselectionMethod.MOMENTUM,
            top_k=30,
            lookback=252,
            skip=21,
        )

        factor_cache = FactorCache(temp_cache_dir, enabled=True)
        preselection = Preselection(preselection_config, cache=factor_cache)

        strategy = EqualWeightStrategy()

        # First run - populate cache
        engine1 = BacktestEngine(
            config=config,
            strategy=strategy,
            prices=prices,
            returns=returns,
            preselection=preselection,
        )
        engine1.run()

        stats_after_first = factor_cache.get_stats()
        assert stats_after_first["puts"] > 0, "Should have cached results"

        # Second run - should hit cache
        factor_cache.reset_stats()
        preselection2 = Preselection(preselection_config, cache=factor_cache)
        engine2 = BacktestEngine(
            config=config,
            strategy=strategy,
            prices=prices,
            returns=returns,
            preselection=preselection2,
        )
        engine2.run()

        stats_after_second = factor_cache.get_stats()
        assert stats_after_second["hits"] > 0, "Should have cache hits on second run"

        # Hit rate should be high (>50%)
        total_queries = stats_after_second["hits"] + stats_after_second["misses"]
        hit_rate = (
            stats_after_second["hits"] / total_queries if total_queries > 0 else 0
        )
        assert hit_rate > 0.5, f"Hit rate {hit_rate:.1%} should be >50%"


class TestPerformanceMetrics:
    """Test performance monitoring."""

    def test_execution_time_tracking(self, long_history_data):
        """Test that execution times are reasonable for long-history backtests."""
        prices, returns, _ = long_history_data

        test_cases = [
            {
                "name": "Equal Weight + Momentum",
                "strategy": EqualWeightStrategy(),
                "preselection": PreselectionConfig(
                    method=PreselectionMethod.MOMENTUM, top_k=30, lookback=252, skip=21
                ),
            },
            {
                "name": "Risk Parity + Low Vol",
                "strategy": RiskParityStrategy(),
                "preselection": PreselectionConfig(
                    method=PreselectionMethod.LOW_VOL, top_k=25, lookback=252
                ),
            },
        ]

        config = BacktestConfig(
            start_date=datetime.date(2010, 1, 1),
            end_date=datetime.date(2020, 12, 31),
            initial_capital=Decimal(100000),
            rebalance_frequency=RebalanceFrequency.QUARTERLY,
        )

        results = []

        for test_case in test_cases:
            preselection = Preselection(test_case["preselection"])

            start_time = time.time()
            engine = BacktestEngine(
                config=config,
                strategy=test_case["strategy"],
                prices=prices,
                returns=returns,
                preselection=preselection,
            )
            engine.run()
            elapsed_time = time.time() - start_time

            results.append(
                {
                    "name": test_case["name"],
                    "time": elapsed_time,
                }
            )

            # Each test should complete in reasonable time
            assert (
                elapsed_time < 600
            ), f"{test_case['name']} took {elapsed_time:.1f}s, expected <600s"

        # Print performance summary for documentation
        print("\n=== Performance Summary ===")
        for result in results:
            print(f"{result['name']}: {result['time']:.2f}s")
