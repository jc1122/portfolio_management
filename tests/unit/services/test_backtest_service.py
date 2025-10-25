from __future__ import annotations

from datetime import date
from decimal import Decimal

import pandas as pd
import pytest

from portfolio_management.backtesting import BacktestConfig, PerformanceMetrics
from portfolio_management.core.exceptions import BacktestError
from portfolio_management.portfolio import EqualWeightStrategy
from portfolio_management.services import BacktestRequest, BacktestResult, BacktestService


class DummyEngine:
    def __init__(self, config, strategy, prices, returns, **kwargs):
        self.config = config
        self.strategy = strategy
        self.prices = prices
        self.returns = returns
        self.kwargs = kwargs

    def run(self) -> tuple[pd.DataFrame, PerformanceMetrics, list]:
        equity_curve = pd.DataFrame(
            {"equity": [100.0, 101.0]},
            index=pd.date_range(self.config.start_date, periods=2, freq="D"),
        )
        metrics = PerformanceMetrics(
            total_return=0.01,
            annualized_return=0.01,
            annualized_volatility=0.01,
            sharpe_ratio=1.0,
            sortino_ratio=1.0,
            max_drawdown=0.0,
            calmar_ratio=0.0,
            expected_shortfall_95=0.0,
            win_rate=0.5,
            avg_win=0.01,
            avg_loss=-0.01,
            turnover=0.0,
            total_costs=Decimal("0"),
            num_rebalances=0,
        )
        return equity_curve, metrics, []


class FailingEngine(DummyEngine):
    def run(self, *args, **kwargs):
        raise BacktestError("boom")


def _build_request() -> BacktestRequest:
    config = BacktestConfig(start_date=date(2020, 1, 1), end_date=date(2020, 1, 5))
    strategy = EqualWeightStrategy()
    prices = pd.DataFrame(
        {"AAA": [100, 101, 102, 103, 104]},
        index=pd.date_range("2020-01-01", periods=5, freq="D"),
    )
    returns = prices.pct_change().fillna(0.0)
    return BacktestRequest(
        config=config,
        strategy=strategy,
        prices=prices,
        returns=returns,
    )


def test_backtest_service_runs_engine() -> None:
    service = BacktestService(engine_cls=DummyEngine)
    request = _build_request()

    result = service.run(request)

    assert isinstance(result, BacktestResult)
    assert isinstance(result.metrics.total_costs, Decimal)
    assert result.events == ()


def test_backtest_service_propagates_errors() -> None:
    service = BacktestService(engine_cls=FailingEngine)
    request = _build_request()

    with pytest.raises(BacktestError):
        service.run(request)
