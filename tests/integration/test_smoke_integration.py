"""Smoke tests for end-to-end backtest integration with real data.

These tests verify that the integration works with actual long_history datasets
when available, but are skipped if data is not present.
"""

from __future__ import annotations

import datetime
from decimal import Decimal
from pathlib import Path

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

# Path to long history data
LONG_HISTORY_PRICES = Path(
    "outputs/long_history_1000/long_history_1000_prices_daily.csv"
)
LONG_HISTORY_RETURNS = Path(
    "outputs/long_history_1000/long_history_1000_returns_daily.csv.gz"
)


def data_available() -> bool:
    """Check if long_history data is available."""
    return LONG_HISTORY_PRICES.exists() and LONG_HISTORY_RETURNS.exists()


@pytest.mark.integration
@pytest.mark.skipif(not data_available(), reason="Long history data not available")
class TestSmokeIntegration:
    """Smoke tests with long_history datasets."""

    def test_long_history_baseline(self):
        """Test basic backtest with long_history data (no special features)."""
        # Load a subset of assets
        returns = pd.read_csv(LONG_HISTORY_RETURNS, index_col=0, parse_dates=True)
        prices = pd.read_csv(LONG_HISTORY_PRICES, index_col=0, parse_dates=True)

        # Use first 50 assets for faster testing
        assets = list(returns.columns[:50])
        returns = returns[assets]
        prices = prices[assets]

        config = BacktestConfig(
            start_date=datetime.date(2010, 1, 1),
            end_date=datetime.date(2012, 12, 31),
            initial_capital=Decimal(100000),
            rebalance_frequency=RebalanceFrequency.QUARTERLY,
            use_pit_eligibility=False,
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

    def test_long_history_with_all_features(self):
        """Test backtest with all features enabled on long_history data."""
        # Load a subset of assets
        returns = pd.read_csv(LONG_HISTORY_RETURNS, index_col=0, parse_dates=True)
        prices = pd.read_csv(LONG_HISTORY_PRICES, index_col=0, parse_dates=True)

        # Use first 50 assets for faster testing
        assets = list(returns.columns[:50])
        returns = returns[assets]
        prices = prices[assets]

        config = BacktestConfig(
            start_date=datetime.date(2010, 1, 1),
            end_date=datetime.date(2012, 12, 31),
            initial_capital=Decimal(100000),
            rebalance_frequency=RebalanceFrequency.QUARTERLY,
            use_pit_eligibility=True,
            min_history_days=252,
            min_price_rows=252,
        )

        # Preselection: top 30 by momentum
        preselection_config = PreselectionConfig(
            method=PreselectionMethod.MOMENTUM,
            top_k=30,
            lookback=252,
            skip=1,
        )
        preselection = Preselection(preselection_config)

        # Membership policy: conservative
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

        # Verify backtest completed
        assert len(equity_curve) > 0
        assert len(events) > 0
        assert metrics.total_return != 0

        # With PIT eligibility, some early dates might not have enough assets
        # Verify that the backtest handled this gracefully
        assert len(events) <= 15  # Should have quarterly rebalances over ~3 years
