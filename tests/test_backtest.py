"""Tests for the backtesting framework."""
from datetime import date
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest

from portfolio_management.backtest import (
    BacktestConfig,
    BacktestEngine,
    PerformanceMetrics,
    RebalanceEvent,
    RebalanceFrequency,
    RebalanceTrigger,
    TransactionCostModel,
)
from portfolio_management.exceptions import (
    InvalidBacktestConfigError,
    InsufficientHistoryError,
)
from portfolio_management.portfolio import (
    EqualWeightStrategy,
    RiskParityStrategy,
)


@pytest.fixture
def sample_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Create sample price and returns data with matching shapes."""
    # Create dates - use 1460 dates for 4 years of daily data
    dates = pd.date_range("2020-01-01", periods=1460, freq="D")
    
    np.random.seed(42)
    n = len(dates)
    
    # Generate returns for all dates
    returns = np.random.multivariate_normal(
        mean=[0.0001, 0.00015, 0.0001, 0.00005],
        cov=[[0.00025, 0.00015, 0.00010, 0.00005],
             [0.00015, 0.00030, 0.00012, 0.00008],
             [0.00010, 0.00012, 0.00020, 0.00006],
             [0.00005, 0.00008, 0.00006, 0.00015]],
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
                initial_capital=Decimal("-1000"),
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
        assert cost > Decimal("0")

    def test_zero_shares(self) -> None:
        """Test cost calculation with zero shares."""
        model = TransactionCostModel()
        cost = model.calculate_cost(
            ticker="A",
            shares=0,
            price=100.0,
            is_buy=True,
        )
        assert cost == Decimal("0")


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
            pre_rebalance_value=Decimal("100000"),
            post_rebalance_value=Decimal("100100"),
            cash_before=Decimal("5000"),
            cash_after=Decimal("4500"),
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

    def test_basic_run(
        self, sample_data: tuple[pd.DataFrame, pd.DataFrame]
    ) -> None:
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

        equity_curve, metrics, events = engine.run()
        assert len(equity_curve) > 0
        assert isinstance(metrics, PerformanceMetrics)
        assert metrics.num_rebalances >= 0

    def test_daily_rebalancing(
        self, sample_data: tuple[pd.DataFrame, pd.DataFrame]
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

        equity_curve, metrics, events = engine.run()
        # With daily rebalancing, we should have multiple rebalances
        assert metrics.num_rebalances > 0
        assert isinstance(metrics, PerformanceMetrics)

    def test_multiple_strategies(
        self, sample_data: tuple[pd.DataFrame, pd.DataFrame]
    ) -> None:
        """Test different strategies."""
        prices, returns = sample_data
        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2023, 12, 30),
        )

        for strategy in [EqualWeightStrategy(), RiskParityStrategy()]:
            engine = BacktestEngine(
                config=config,
                strategy=strategy,
                prices=prices,
                returns=returns,
            )

            equity_curve, metrics, events = engine.run()
            assert isinstance(metrics, PerformanceMetrics)
            assert metrics.total_return is not None
            assert len(equity_curve) > 0
