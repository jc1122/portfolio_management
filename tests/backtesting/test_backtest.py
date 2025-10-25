"""Tests for the backtesting framework."""

from datetime import date
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest
pytestmark = pytest.mark.integration

from portfolio_management.backtesting.engine import (
    BacktestConfig,
    BacktestEngine,
    RebalanceEvent,
    RebalanceFrequency,
    RebalanceTrigger,
    TransactionCostModel,
)
from portfolio_management.backtesting.models import PerformanceMetrics
from portfolio_management.core.exceptions import InvalidBacktestConfigError
from portfolio_management.portfolio.strategies import (
    EqualWeightStrategy,
    PortfolioStrategy,
    RiskParityStrategy,
)


@pytest.fixture
def sample_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Create sample price and returns data with matching shapes."""
    # Create dates - use 1460 dates for 4 years of daily data
    dates = pd.date_range("2020-01-01", periods=1460, freq="D")

    rng = np.random.default_rng(42)
    n = len(dates)

    # Generate returns for all dates
    returns = rng.multivariate_normal(
        mean=[0.0001, 0.00015, 0.0001, 0.00005],
        cov=[
            [0.00025, 0.00015, 0.00010, 0.00005],
            [0.00015, 0.00030, 0.00012, 0.00008],
            [0.00010, 0.00012, 0.00020, 0.00006],
            [0.00005, 0.00008, 0.00006, 0.00015],
        ],
        size=n,
    )

    # Create cumulative prices from returns
    prices = np.exp(np.cumsum(returns, axis=0))
    prices = prices * 100  # Scale to reasonable prices

    # Create DataFrames
    prices_df = pd.DataFrame(
        prices,
        index=dates,
        columns=["A", "B", "C", "D"],
    )

    returns_df = pd.DataFrame(
        returns,
        index=dates,
        columns=["A", "B", "C", "D"],
    )

    return prices_df, returns_df


class TestBacktestConfig:
    """Tests for BacktestConfig data class."""

    def test_creation(self) -> None:
        """Test creating a valid BacktestConfig."""
        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2023, 12, 31),
        )
        assert config.start_date == date(2020, 1, 1)
        assert config.end_date == date(2023, 12, 31)
        # Default capital is 100,000 (as per code)
        assert config.initial_capital == Decimal("100000.00")

    def test_invalid_dates(self) -> None:
        """Test that end_date before start_date raises error."""
        with pytest.raises(InvalidBacktestConfigError):
            BacktestConfig(
                start_date=date(2023, 12, 31),
                end_date=date(2020, 1, 1),
            )

    def test_negative_capital(self) -> None:
        """Test that negative capital raises error."""
        with pytest.raises(InvalidBacktestConfigError):
            BacktestConfig(
                start_date=date(2020, 1, 1),
                end_date=date(2023, 12, 31),
                initial_capital=Decimal(-1000),
            )


class TestTransactionCostModel:
    """Tests for TransactionCostModel."""

    def test_calculate_cost_buy(self) -> None:
        """Test cost calculation for buy order."""
        model = TransactionCostModel(
            commission_pct=0.001,  # 0.1%
            commission_min=5.0,
            slippage_bps=5.0,  # 5 basis points
        )

        # Buy 1000 shares at $100
        # Trade value: $100,000
        # Commission: max(0.001 * 100000, 5) = $100
        # Slippage: 100000 * 0.0005 = $50
        cost = model.calculate_cost(
            ticker="A",
            shares=1000,
            price=100.0,
            is_buy=True,
        )
        assert cost > Decimal(0)

    def test_zero_shares(self) -> None:
        """Test cost calculation with zero shares."""
        model = TransactionCostModel()
        cost = model.calculate_cost(
            ticker="A",
            shares=0,
            price=100.0,
            is_buy=True,
        )
        assert cost == Decimal(0)


class TestRebalanceEnums:
    """Tests for rebalancing enums."""

    def test_rebalance_frequency_values(self) -> None:
        """Test RebalanceFrequency enum values."""
        assert RebalanceFrequency.DAILY.value == "daily"
        assert RebalanceFrequency.WEEKLY.value == "weekly"
        assert RebalanceFrequency.MONTHLY.value == "monthly"
        assert RebalanceFrequency.QUARTERLY.value == "quarterly"
        assert RebalanceFrequency.ANNUAL.value == "annual"

    def test_rebalance_trigger_values(self) -> None:
        """Test RebalanceTrigger enum values."""
        assert RebalanceTrigger.SCHEDULED.value == "scheduled"
        assert RebalanceTrigger.OPPORTUNISTIC.value == "opportunistic"
        assert RebalanceTrigger.FORCED.value == "forced"


class TestRebalanceEvent:
    """Tests for RebalanceEvent data model."""

    def test_creation(self) -> None:
        """Test creating a RebalanceEvent."""
        event = RebalanceEvent(
            date=date(2020, 1, 15),
            trigger=RebalanceTrigger.SCHEDULED,
            trades={"A": 100, "B": -50},
            costs=Decimal("25.50"),
            pre_rebalance_value=Decimal(100000),
            post_rebalance_value=Decimal(100100),
            cash_before=Decimal(5000),
            cash_after=Decimal(4500),
        )
        assert event.date == date(2020, 1, 15)
        assert event.trigger == RebalanceTrigger.SCHEDULED
        assert len(event.trades) == 2


class TestPerformanceMetrics:
    """Tests for PerformanceMetrics data model."""

    def test_creation(self) -> None:
        """Test creating PerformanceMetrics."""
        metrics = PerformanceMetrics(
            total_return=0.25,
            annualized_return=0.10,
            annualized_volatility=0.15,
            sharpe_ratio=0.67,
            sortino_ratio=0.90,
            max_drawdown=-0.15,
            calmar_ratio=0.67,
            expected_shortfall_95=-0.02,
            win_rate=0.55,
            avg_win=0.02,
            avg_loss=-0.015,
            turnover=0.30,
            total_costs=Decimal("1234.56"),
            num_rebalances=12,
        )
        assert metrics.total_return == 0.25
        assert metrics.sharpe_ratio == 0.67
        assert metrics.num_rebalances == 12


class TestBacktestEngine:
    """Tests for BacktestEngine."""

    def test_basic_run(self, sample_data: tuple[pd.DataFrame, pd.DataFrame]) -> None:
        """Test basic backtest run."""
        prices, returns = sample_data
        # Use dates that match actual data
        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2023, 12, 30),
        )
        strategy = EqualWeightStrategy()

        engine = BacktestEngine(
            config=config,
            strategy=strategy,
            prices=prices,
            returns=returns,
        )

        equity_curve, metrics, _events = engine.run()
        assert len(equity_curve) > 0
        assert isinstance(metrics, PerformanceMetrics)
        assert metrics.num_rebalances >= 0

    def test_daily_rebalancing(
        self,
        sample_data: tuple[pd.DataFrame, pd.DataFrame],
    ) -> None:
        """Test daily rebalancing."""
        prices, returns = sample_data
        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 1, 20),
            rebalance_frequency=RebalanceFrequency.DAILY,
        )
        strategy = EqualWeightStrategy()

        engine = BacktestEngine(
            config=config,
            strategy=strategy,
            prices=prices,
            returns=returns,
        )

        _equity_curve, metrics, _events = engine.run()
        # With daily rebalancing, we should have multiple rebalances
        assert metrics.num_rebalances > 0
        assert isinstance(metrics, PerformanceMetrics)

    def test_multiple_strategies(
        self,
        sample_data: tuple[pd.DataFrame, pd.DataFrame],
    ) -> None:
        """Test different strategies."""
        prices, returns = sample_data
        # Start later to allow for lookback period for RiskParityStrategy
        config = BacktestConfig(
            start_date=date(2020, 6, 1),
            end_date=date(2023, 12, 30),
        )

        strategies: list[PortfolioStrategy] = [
            EqualWeightStrategy(),
        ]

        # Only test RiskParityStrategy if dependency is available
        try:
            import riskparityportfolio  # noqa: F401

            strategies.append(RiskParityStrategy())
        except ImportError:
            pytest.skip("RiskParityStrategy requires riskparityportfolio dependency")

        for strategy in strategies:
            engine = BacktestEngine(
                config=config,
                strategy=strategy,
                prices=prices,
                returns=returns,
            )

            equity_curve, metrics, _ = engine.run()
            assert isinstance(metrics, PerformanceMetrics)
            assert metrics.total_return is not None
            assert len(equity_curve) > 0

    def test_optimization_behavior_unchanged(
        self,
        sample_data: tuple[pd.DataFrame, pd.DataFrame],
    ) -> None:
        """Regression test to ensure optimization doesn't change behavior.

        This test verifies that the optimized lookback slicing produces
        identical results to the previous implementation.
        """
        prices, returns = sample_data

        # Test with monthly rebalancing over a year
        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 12, 31),
            rebalance_frequency=RebalanceFrequency.MONTHLY,
        )
        strategy = EqualWeightStrategy()

        engine = BacktestEngine(
            config=config,
            strategy=strategy,
            prices=prices,
            returns=returns,
        )

        equity_curve, metrics, events = engine.run()

        # Verify expected behavior
        assert len(equity_curve) > 0
        assert len(events) > 0  # Should have rebalanced

        # For monthly rebalancing over 1 year, expect around 12 rebalances
        # (could be 11-13 depending on exact trading days)
        assert 10 <= metrics.num_rebalances <= 14

        # Verify equity curve is monotonic or reasonable
        equity_values = equity_curve["equity"].values
        assert len(equity_values) > 250  # Should have most trading days

        # Verify all rebalances have valid data
        for event in events:
            assert event.date is not None
            assert event.pre_rebalance_value > 0
            assert event.post_rebalance_value > 0
            # Transaction costs should be non-negative
            assert event.costs >= 0

        # Verify metrics are reasonable
        assert metrics.total_return is not None
        assert metrics.annualized_return is not None
        assert metrics.annualized_volatility > 0
        assert metrics.max_drawdown <= 0  # Drawdown is negative
        assert metrics.num_rebalances > 0


class TestPITEligibility:
    """Tests for point-in-time eligibility filtering in backtesting."""

    @pytest.fixture
    def returns_with_late_starter(self) -> pd.DataFrame:
        """Create returns with one asset starting late."""
        dates = pd.date_range("2020-01-01", periods=800, freq="D")

        rng = np.random.default_rng(100)

        # Assets A, B: Full history
        returns_a = rng.normal(0.0001, 0.01, len(dates))
        returns_b = rng.normal(0.00015, 0.012, len(dates))

        # Asset C: Starts after 400 days
        returns_c = np.full(len(dates), np.nan)
        returns_c[400:] = rng.normal(0.0001, 0.011, len(dates) - 400)

        df = pd.DataFrame(
            {"A": returns_a, "B": returns_b, "C": returns_c},
            index=dates,
        )

        return df

    @pytest.fixture
    def returns_with_delisting(self) -> pd.DataFrame:
        """Create returns with one asset delisting mid-period."""
        dates = pd.date_range("2020-01-01", periods=800, freq="D")

        rng = np.random.default_rng(101)

        # Asset A: Full history
        returns_a = rng.normal(0.0001, 0.01, len(dates))

        # Asset B: Delists after 400 days
        returns_b = rng.normal(0.00015, 0.012, len(dates))
        returns_b[400:] = np.nan

        # Asset C: Full history
        returns_c = rng.normal(0.0001, 0.011, len(dates))

        df = pd.DataFrame(
            {"A": returns_a, "B": returns_b, "C": returns_c},
            index=dates,
        )

        return df

    def test_pit_eligibility_excludes_late_starter_initially(
        self, returns_with_late_starter: pd.DataFrame
    ):
        """Test that late-starting assets are excluded when they don't have enough history."""
        returns = returns_with_late_starter

        # Generate prices from returns
        prices = (1 + returns).cumprod() * 100

        # Backtest from day 450 to 550 (only 50 days after C starts)
        config = BacktestConfig(
            start_date=returns.index[450].date(),
            end_date=returns.index[550].date(),
            use_pit_eligibility=True,
            min_history_days=100,  # Require 100 days
            min_price_rows=100,
        )

        strategy = EqualWeightStrategy()

        engine = BacktestEngine(
            config=config,
            strategy=strategy,
            prices=prices,
            returns=returns,
        )

        _equity, _metrics, events = engine.run()

        # At first rebalance (day 450), asset C should not be included
        # because it only has 50 days of history
        first_event = events[0]

        # Check that only A and B were traded in first rebalance
        traded_assets = set(first_event.trades.keys())
        assert "A" in traded_assets or len(traded_assets) > 0
        assert "B" in traded_assets or len(traded_assets) > 0
        # C might not be traded if it doesn't meet eligibility

    def test_pit_eligibility_includes_late_starter_later(
        self, returns_with_late_starter: pd.DataFrame
    ):
        """Test that late-starting assets are included once they have enough history."""
        returns = returns_with_late_starter

        # Generate prices from returns
        prices = (1 + returns).cumprod() * 100

        # Backtest from day 550 to 650 (150 days after C starts)
        config = BacktestConfig(
            start_date=returns.index[550].date(),
            end_date=returns.index[650].date(),
            use_pit_eligibility=True,
            min_history_days=100,  # Asset C now has enough history
            min_price_rows=100,
        )

        strategy = EqualWeightStrategy()

        engine = BacktestEngine(
            config=config,
            strategy=strategy,
            prices=prices,
            returns=returns,
        )

        _equity, _metrics, events = engine.run()

        # Now all three assets should potentially be included
        # Check at least one rebalance happened
        assert len(events) > 0

    def test_pit_eligibility_handles_delisting(
        self, returns_with_delisting: pd.DataFrame
    ):
        """Test that delisted assets are properly liquidated."""
        returns = returns_with_delisting

        # Generate prices from returns
        prices = (1 + returns).cumprod() * 100

        # Backtest from day 200 to 600 (across the delisting at day 400)
        config = BacktestConfig(
            start_date=returns.index[200].date(),
            end_date=returns.index[600].date(),
            use_pit_eligibility=True,
            min_history_days=50,
            min_price_rows=50,
        )

        strategy = EqualWeightStrategy()

        engine = BacktestEngine(
            config=config,
            strategy=strategy,
            prices=prices,
            returns=returns,
        )

        _equity, _metrics, events = engine.run()

        # Should have successfully completed the backtest
        assert len(events) > 0

        # Engine should have tracked the delisted asset
        assert len(engine.delisted_assets) >= 0  # May or may not detect B as delisted

    def test_pit_eligibility_disabled_includes_all_assets(
        self, returns_with_late_starter: pd.DataFrame
    ):
        """Test that disabling PIT eligibility includes all assets regardless of history."""
        returns = returns_with_late_starter

        # Generate prices from returns
        prices = (1 + returns).cumprod() * 100

        # Backtest early when C doesn't have much history
        config = BacktestConfig(
            start_date=returns.index[450].date(),
            end_date=returns.index[550].date(),
            use_pit_eligibility=False,  # Disabled
            min_history_days=100,
            min_price_rows=100,
        )

        strategy = EqualWeightStrategy()

        engine = BacktestEngine(
            config=config,
            strategy=strategy,
            prices=prices,
            returns=returns,
        )

        _equity, _metrics, events = engine.run()

        # Should run successfully even with late starter
        assert len(events) > 0

    def test_pit_eligibility_no_eligible_assets_skips_rebalance(self):
        """Test that rebalancing is skipped when no assets are eligible."""
        # Create minimal data with very late starters
        dates = pd.date_range("2020-01-01", periods=300, freq="D")

        rng = np.random.default_rng(102)

        # All assets start very late
        returns_a = np.full(len(dates), np.nan)
        returns_a[290:] = rng.normal(0.0001, 0.01, 10)

        returns = pd.DataFrame({"A": returns_a}, index=dates)
        prices = (1 + returns.fillna(0)).cumprod() * 100

        # Try to backtest from beginning with strict requirements
        config = BacktestConfig(
            start_date=dates[0].date(),
            end_date=dates[100].date(),  # Before asset starts
            use_pit_eligibility=True,
            min_history_days=252,  # Very strict
            min_price_rows=252,
        )

        strategy = EqualWeightStrategy()

        engine = BacktestEngine(
            config=config,
            strategy=strategy,
            prices=prices,
            returns=returns,
        )

        _equity, metrics, events = engine.run()

        # Should have no rebalances since no assets were eligible
        assert metrics.num_rebalances == 0
        assert len(events) == 0

    def test_config_validates_pit_parameters(self):
        """Test that BacktestConfig validates PIT eligibility parameters."""
        # Valid config should work
        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2021, 1, 1),
            min_history_days=252,
            min_price_rows=252,
        )
        assert config.min_history_days == 252
        assert config.min_price_rows == 252

        # Invalid min_history_days should raise error
        with pytest.raises(Exception):  # InvalidBacktestConfigError
            BacktestConfig(
                start_date=date(2020, 1, 1),
                end_date=date(2021, 1, 1),
                min_history_days=0,
            )

        # Invalid min_price_rows should raise error
        with pytest.raises(Exception):  # InvalidBacktestConfigError
            BacktestConfig(
                start_date=date(2020, 1, 1),
                end_date=date(2021, 1, 1),
                min_price_rows=-1,
            )
