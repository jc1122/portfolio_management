"""Tests for the visualization data preparation utilities."""

from datetime import date
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest

from portfolio_management.backtesting.models import (
    PerformanceMetrics,
    RebalanceEvent,
    RebalanceTrigger,
)
from portfolio_management.reporting.visualization import (
    create_summary_report,
    prepare_drawdown_series,
    prepare_equity_curve,
    prepare_metrics_comparison,
    prepare_monthly_returns_heatmap,
    prepare_returns_distribution,
    prepare_rolling_metrics,
    prepare_trade_analysis,
    prepare_transaction_costs_summary,
)


@pytest.fixture
def sample_equity_df() -> pd.DataFrame:
    """Create a sample equity DataFrame for testing."""
    dates = pd.to_datetime(pd.date_range("2020-01-01", periods=100, freq="D"))
    trend = 100000 + np.linspace(0, 20000, 100)
    oscillation = 2000 * np.sin(np.linspace(0, 10, 100))
    equity_values = trend + oscillation
    equity_df = pd.DataFrame({"equity": equity_values, "date": dates})
    # Introduce a pronounced drawdown that exceeds -100%.
    equity_df.loc[55:57, "equity"] = -500.0
    return equity_df


@pytest.fixture
def sample_rebalance_events() -> list[RebalanceEvent]:
    """Create a list of sample rebalance events."""
    return [
        RebalanceEvent(
            date=date(2020, 1, 1),
            trigger=RebalanceTrigger.SCHEDULED,
            pre_rebalance_value=Decimal(100000),
            post_rebalance_value=Decimal(100000),
            cash_before=Decimal(10000),
            cash_after=Decimal(5000),
            trades={"A": 10, "B": -5},
            costs=Decimal(50),
        ),
        RebalanceEvent(
            date=date(2020, 4, 1),
            trigger=RebalanceTrigger.SCHEDULED,
            pre_rebalance_value=Decimal(110000),
            post_rebalance_value=Decimal(110000),
            cash_before=Decimal(15000),
            cash_after=Decimal(8000),
            trades={"A": -10, "C": 20},
            costs=Decimal(75),
        ),
    ]


@pytest.fixture
def sample_metrics() -> PerformanceMetrics:
    """Create a sample PerformanceMetrics object."""
    return PerformanceMetrics(
        total_return=0.15,
        annualized_return=0.05,
        annualized_volatility=0.10,
        sharpe_ratio=0.5,
        sortino_ratio=0.7,
        max_drawdown=0.12,
        calmar_ratio=0.4,
        win_rate=0.6,
        avg_win=0.01,
        avg_loss=-0.008,
        expected_shortfall_95=0.02,
        turnover=0.5,
        total_costs=Decimal("1250.00"),
        num_rebalances=10,
    )


class TestEquityCurve:
    """Tests for prepare_equity_curve."""

    def test_prepare_equity_curve(self, sample_equity_df: pd.DataFrame) -> None:
        """Test that equity curve is prepared correctly."""
        result = prepare_equity_curve(sample_equity_df)
        assert "equity_normalized" in result.columns
        assert "equity_change_pct" in result.columns
        assert result["equity_normalized"].iloc[0] == 100.0
        assert result["equity_change_pct"].iloc[0] == 0.0
        assert result.shape[0] == sample_equity_df.shape[0]


class TestDrawdownSeries:
    """Tests for prepare_drawdown_series."""

    def test_prepare_drawdown_series(self, sample_equity_df: pd.DataFrame) -> None:
        """Test that drawdown series is calculated correctly."""
        result = prepare_drawdown_series(sample_equity_df)
        assert "drawdown_pct" in result.columns
        assert "running_max" in result.columns
        assert "underwater" in result.columns
        assert result["drawdown_pct"].max() <= 0.0
        assert not result["underwater"].iloc[0]
        assert result["drawdown_pct"].min() < -1.0  # Based on fixture


class TestRollingMetrics:
    """Tests for prepare_rolling_metrics."""

    def test_prepare_rolling_metrics(self, sample_equity_df: pd.DataFrame) -> None:
        """Test that rolling metrics are calculated correctly."""
        result = prepare_rolling_metrics(sample_equity_df, window=30)
        assert "rolling_return_annual" in result.columns
        assert "rolling_volatility_annual" in result.columns
        assert "rolling_sharpe" in result.columns
        assert "rolling_max_drawdown" in result.columns
        assert result.notna().sum().sum() > 0  # Check for non-NA values
        assert result.shape[0] == sample_equity_df.shape[0]


class TestTransactionCostsSummary:
    """Tests for prepare_transaction_costs_summary."""

    def test_prepare_transaction_costs_summary(
        self,
        sample_rebalance_events: list[RebalanceEvent],
    ) -> None:
        """Test that transaction costs summary is prepared correctly."""
        result = prepare_transaction_costs_summary(sample_rebalance_events)
        assert "costs" in result.columns
        assert "cumulative_costs" in result.columns
        assert "trigger" in result.columns
        assert "num_trades" in result.columns
        assert "portfolio_value" in result.columns
        assert "costs_bps" in result.columns
        assert result.shape[0] == 2
        assert result["cumulative_costs"].iloc[-1] == 125.0
        assert result["num_trades"].iloc[0] == 2


class TestReturnsDistribution:
    """Tests for prepare_returns_distribution."""

    def test_prepare_returns_distribution(
        self,
        sample_equity_df: pd.DataFrame,
    ) -> None:
        """Test that returns distribution is prepared correctly."""
        result = prepare_returns_distribution(sample_equity_df)
        assert "returns" in result.columns
        assert "returns_pct" in result.columns
        assert "positive" in result.columns
        assert "mean" in result.columns
        assert "std" in result.columns
        assert result.shape[0] == sample_equity_df.shape[0] - 1


class TestMonthlyReturnsHeatmap:
    """Tests for prepare_monthly_returns_heatmap."""

    def test_prepare_monthly_returns_heatmap(
        self,
        sample_equity_df: pd.DataFrame,
    ) -> None:
        """Test that monthly returns heatmap is prepared correctly."""
        # The function expects a datetime index, so we set it.
        df = sample_equity_df.set_index("date")
        result = prepare_monthly_returns_heatmap(df)
        assert "Jan" in result.columns
        assert "Feb" in result.columns
        assert "Mar" in result.columns
        assert "Apr" in result.columns
        assert result.shape[0] == 1
        assert result.shape[1] == 4


class TestMetricsComparison:
    """Tests for prepare_metrics_comparison."""

    def test_prepare_metrics_comparison(
        self,
        sample_metrics: PerformanceMetrics,
    ) -> None:
        """Test that metrics comparison table is prepared correctly."""
        metrics_list = [
            ("Strategy A", sample_metrics),
            ("Strategy B", sample_metrics),
        ]
        result = prepare_metrics_comparison(metrics_list)
        assert result.shape[0] == 2
        assert "Sharpe Ratio" in result.columns
        assert "Max Drawdown %" in result.columns
        assert result.loc["Strategy A"]["Sharpe Ratio"] == 0.5


class TestTradeAnalysis:
    """Tests for prepare_trade_analysis."""

    def test_prepare_trade_analysis(
        self,
        sample_rebalance_events: list[RebalanceEvent],
    ) -> None:
        """Test that trade analysis is prepared correctly."""
        result = prepare_trade_analysis(sample_rebalance_events)
        assert "ticker" in result.columns
        assert "shares" in result.columns
        assert "direction" in result.columns
        assert "trigger" in result.columns
        assert result.shape[0] == 4
        assert result["direction"].value_counts()["BUY"] == 2
        assert result["direction"].value_counts()["SELL"] == 2


class TestSummaryReport:
    """Tests for create_summary_report."""

    def test_create_summary_report(
        self,
        sample_equity_df: pd.DataFrame,
        sample_metrics: PerformanceMetrics,
        sample_rebalance_events: list[RebalanceEvent],
    ) -> None:
        """Test that summary report is created correctly."""
        report = create_summary_report(
            sample_equity_df,
            sample_metrics,
            sample_rebalance_events,
        )
        assert "performance" in report
        assert "risk" in report
        assert "trading" in report
        assert "portfolio" in report
        assert report["performance"]["sharpe_ratio"] == 0.5
        assert report["trading"]["num_rebalances"] == 10
