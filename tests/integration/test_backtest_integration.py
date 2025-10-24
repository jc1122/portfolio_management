"""Integration tests for preselection, membership policy, and PIT eligibility."""

from __future__ import annotations

import datetime
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest

from portfolio_management.backtesting import (
    BacktestConfig,
    BacktestEngine,
    RebalanceFrequency,
)
from portfolio_management.portfolio import (
    EqualWeightStrategy,
    MembershipPolicy,
    Preselection,
    PreselectionConfig,
    PreselectionMethod,
)


@pytest.fixture
def sample_data():
    """Create sample price and return data for testing."""
    dates = pd.date_range("2020-01-01", "2023-12-31", freq="D")
    assets = [f"ASSET{i:02d}" for i in range(50)]

    # Create synthetic prices with some variation
    np.random.seed(42)
    base_prices = 100.0
    returns_data = np.random.randn(len(dates), len(assets)) * 0.01

    # Convert to prices
    prices_data = base_prices * (1 + returns_data).cumprod(axis=0)

    prices = pd.DataFrame(prices_data, index=dates, columns=assets)
    returns = pd.DataFrame(returns_data, index=dates, columns=assets)

    return prices, returns


@pytest.mark.integration
class TestBacktestIntegration:
    """Test suite for integrated backtest features."""

    def test_backtest_with_pit_eligibility(self, sample_data):
        """Test backtest with PIT eligibility enabled."""
        prices, returns = sample_data

        config = BacktestConfig(
            start_date=datetime.date(2021, 1, 1),
            end_date=datetime.date(2022, 12, 31),
            initial_capital=Decimal(100000),
            rebalance_frequency=RebalanceFrequency.QUARTERLY,
            use_pit_eligibility=True,
            min_history_days=180,  # ~6 months
            min_price_rows=180,
        )

        strategy = EqualWeightStrategy()

        engine = BacktestEngine(
            config=config,
            strategy=strategy,
            prices=prices,
            returns=returns,
        )

        equity_curve, metrics, events = engine.run()

        # Verify backtest completed
        assert len(equity_curve) > 0
        assert len(events) > 0
        assert metrics.total_return != 0

    def test_backtest_with_preselection(self, sample_data):
        """Test backtest with preselection enabled."""
        prices, returns = sample_data

        config = BacktestConfig(
            start_date=datetime.date(2021, 1, 1),
            end_date=datetime.date(2022, 12, 31),
            initial_capital=Decimal(100000),
            rebalance_frequency=RebalanceFrequency.QUARTERLY,
        )

        preselection_config = PreselectionConfig(
            method=PreselectionMethod.MOMENTUM,
            top_k=20,
            lookback=126,  # 6 months
            skip=1,
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

        # Verify backtest completed
        assert len(equity_curve) > 0
        assert len(events) > 0

    def test_backtest_with_membership_policy(self, sample_data):
        """Test backtest with membership policy enabled."""
        prices, returns = sample_data

        config = BacktestConfig(
            start_date=datetime.date(2021, 1, 1),
            end_date=datetime.date(2022, 12, 31),
            initial_capital=Decimal(100000),
            rebalance_frequency=RebalanceFrequency.QUARTERLY,
        )

        policy = MembershipPolicy(
            buffer_rank=25,
            min_holding_periods=2,
            max_turnover=0.40,
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
            membership_policy=policy,
        )

        equity_curve, metrics, events = engine.run()

        # Verify backtest completed
        assert len(equity_curve) > 0
        assert len(events) > 0

    def test_backtest_all_features_integrated(self, sample_data):
        """Test backtest with all features enabled: PIT, preselection, membership."""
        prices, returns = sample_data

        config = BacktestConfig(
            start_date=datetime.date(2021, 1, 1),
            end_date=datetime.date(2022, 12, 31),
            initial_capital=Decimal(100000),
            rebalance_frequency=RebalanceFrequency.QUARTERLY,
            use_pit_eligibility=True,
            min_history_days=180,  # ~6 months
            min_price_rows=180,
        )

        preselection_config = PreselectionConfig(
            method=PreselectionMethod.COMBINED,
            top_k=30,
            lookback=126,  # ~6 months
            skip=1,
            momentum_weight=0.6,
            low_vol_weight=0.4,
        )
        preselection = Preselection(preselection_config)

        policy = MembershipPolicy(
            buffer_rank=35,
            min_holding_periods=3,
            max_turnover=0.30,
            max_new_assets=5,
            max_removed_assets=5,
            enabled=True,
        )

        strategy = EqualWeightStrategy()

        engine = BacktestEngine(
            config=config,
            strategy=strategy,
            prices=prices,
            returns=returns,
            preselection=preselection,
            membership_policy=policy,
        )

        equity_curve, metrics, events = engine.run()

        # Verify backtest completed successfully
        assert len(equity_curve) > 0
        assert len(events) > 0
        assert metrics.total_return != 0

        # Verify membership policy had effect (should have fewer rebalances due to policy)
        # This is indirect verification - exact behavior depends on data
        assert len(events) <= 10  # Should have quarterly rebalances over 2 years

    def test_backtest_features_disabled(self, sample_data):
        """Test that backtest works with all features explicitly disabled."""
        prices, returns = sample_data

        config = BacktestConfig(
            start_date=datetime.date(2021, 1, 1),
            end_date=datetime.date(2022, 12, 31),
            initial_capital=Decimal(100000),
            rebalance_frequency=RebalanceFrequency.QUARTERLY,
            use_pit_eligibility=False,  # Disabled
        )

        # No preselection
        # No membership policy

        strategy = EqualWeightStrategy()

        engine = BacktestEngine(
            config=config,
            strategy=strategy,
            prices=prices,
            returns=returns,
        )

        equity_curve, metrics, events = engine.run()

        # Verify backtest completed
        assert len(equity_curve) > 0
        assert len(events) > 0

    def test_membership_policy_disabled(self, sample_data):
        """Test that disabled membership policy doesn't affect backtest."""
        prices, returns = sample_data

        config = BacktestConfig(
            start_date=datetime.date(2021, 1, 1),
            end_date=datetime.date(2022, 12, 31),
            initial_capital=Decimal(100000),
            rebalance_frequency=RebalanceFrequency.QUARTERLY,
        )

        policy = MembershipPolicy(
            enabled=False,  # Disabled
        )

        strategy = EqualWeightStrategy()

        engine = BacktestEngine(
            config=config,
            strategy=strategy,
            prices=prices,
            returns=returns,
            membership_policy=policy,
        )

        equity_curve, metrics, events = engine.run()

        # Verify backtest completed
        assert len(equity_curve) > 0
        assert len(events) > 0
