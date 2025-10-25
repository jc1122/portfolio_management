"""Tests for :class:`portfolio_management.services.backtest.BacktestService`."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import pandas as pd

from portfolio_management.backtesting import BacktestConfig, PerformanceMetrics, RebalanceEvent, RebalanceTrigger
from portfolio_management.portfolio import EqualWeightStrategy
from portfolio_management.services import BacktestResult, BacktestService


@dataclass
class _StubEngine:
    """Simple stand-in for :class:`BacktestEngine` used in tests."""

    config: BacktestConfig
    strategy: EqualWeightStrategy
    prices: pd.DataFrame
    returns: pd.DataFrame
    classifications: dict[str, str] | None = None
    preselection: object | None = None
    membership_policy: object | None = None
    cache: object | None = None

    def run(self) -> tuple[pd.DataFrame, PerformanceMetrics, list[RebalanceEvent]]:
        equity_curve = pd.DataFrame({"equity": [1.0, 1.01]})
        metrics = PerformanceMetrics(
            total_return=0.01,
            annualized_return=0.02,
            annualized_volatility=0.01,
            sharpe_ratio=1.0,
            sortino_ratio=1.0,
            max_drawdown=0.001,
            calmar_ratio=1.0,
            expected_shortfall_95=-0.001,
            win_rate=0.6,
            avg_win=0.002,
            avg_loss=-0.001,
            turnover=0.1,
            total_costs=Decimal("0"),
            num_rebalances=1,
        )
        events = [
            RebalanceEvent(
                date=self.config.start_date,
                trigger=RebalanceTrigger.SCHEDULED,
                trades={"A": 10},
                costs=Decimal("0"),
                pre_rebalance_value=self.config.initial_capital,
                post_rebalance_value=self.config.initial_capital,
                cash_before=self.config.initial_capital,
                cash_after=self.config.initial_capital,
            )
        ]
        return equity_curve, metrics, events


def _sample_config() -> BacktestConfig:
    return BacktestConfig(
        start_date=date(2020, 1, 1),
        end_date=date(2020, 6, 1),
        initial_capital=Decimal("100000"),
    )


def _sample_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    index = pd.date_range("2020-01-01", periods=5, freq="D")
    prices = pd.DataFrame({"A": [100, 101, 102, 103, 104]}, index=index)
    returns = prices.pct_change().fillna(0.0)
    return prices, returns


def test_run_backtest_with_registered_strategy() -> None:
    config = _sample_config()
    prices, returns = _sample_data()
    registry = {"equal_weight": EqualWeightStrategy()}
    service = BacktestService(engine_cls=_StubEngine, strategy_registry=registry)

    result = service.run_backtest(
        config=config,
        strategy="equal_weight",
        prices=prices,
        returns=returns,
    )

    assert isinstance(result, BacktestResult)
    assert result.strategy_name == "equal_weight"
    assert len(result.rebalance_events) == 1


def test_run_backtest_with_strategy_instance() -> None:
    config = _sample_config()
    prices, returns = _sample_data()
    strategy = EqualWeightStrategy()
    service = BacktestService(engine_cls=_StubEngine)

    result = service.run_backtest(
        config=config,
        strategy=strategy,
        prices=prices,
        returns=returns,
    )

    assert result.strategy_name == strategy.__class__.__name__
