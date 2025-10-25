"""Unit tests for backtesting engine helpers."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import pandas as pd
import pytest

from portfolio_management.backtesting.engine.backtest import BacktestEngine
from portfolio_management.backtesting.models import (
    BacktestConfig,
    RebalanceEvent,
    RebalanceTrigger,
)
from portfolio_management.core.exceptions import InsufficientHistoryError
from portfolio_management.portfolio.constraints.models import PortfolioConstraints
from portfolio_management.portfolio.models import Portfolio
from portfolio_management.portfolio.strategies.base import PortfolioStrategy

pytestmark = pytest.mark.unit


@dataclass
class DummyStrategy(PortfolioStrategy):
    """Simple strategy returning equal weights without external dependencies."""

    min_periods: int = 11

    def construct(
        self,
        returns: pd.DataFrame,
        constraints: PortfolioConstraints,
        asset_classes: pd.Series | None = None,
    ) -> Portfolio:
        weights = pd.Series(
            1 / len(returns.columns),
            index=returns.columns,
        )
        return Portfolio(weights=weights, strategy="dummy")

    @property
    def name(self) -> str:
        return "dummy"

    @property
    def min_history_periods(self) -> int:
        return self.min_periods


@pytest.fixture
def engine(mock_price_data: pd.DataFrame, mock_returns: pd.DataFrame) -> BacktestEngine:
    """Instantiate the engine with in-memory data and a dummy strategy."""
    start_date = mock_price_data.index.min().date()
    end_date = mock_price_data.index.max().date()
    config = BacktestConfig(start_date=start_date, end_date=end_date, initial_capital=Decimal("100000"))
    strategy = DummyStrategy()
    return BacktestEngine(config, strategy, mock_price_data, mock_returns)


def test_initial_cash_equals_initial_capital(engine: BacktestEngine) -> None:
    """Engine should set cash balance to the configured starting capital."""
    assert engine.cash == Decimal("100000")


def test_calculate_portfolio_value(engine: BacktestEngine) -> None:
    """Portfolio value calculation should include holdings and cash."""
    engine.cash = Decimal("50000")
    engine.holdings = {"AAA": 10, "BBB": 5}
    prices = engine.prices.iloc[0]

    value = engine._calculate_portfolio_value(prices)

    expected = Decimal(str(float(prices["AAA"]))) * 10 + Decimal(str(float(prices["BBB"]))) * 5 + Decimal("50000")
    assert value == expected


def test_should_rebalance_scheduled_monthly(engine: BacktestEngine) -> None:
    """Monthly schedules should trigger when the month changes."""
    event = RebalanceEvent(
        date=engine.config.start_date,
        trigger=RebalanceTrigger.SCHEDULED,
        trades={},
        costs=Decimal("0"),
        pre_rebalance_value=Decimal("0"),
        post_rebalance_value=Decimal("0"),
        cash_before=Decimal("0"),
        cash_after=Decimal("0"),
    )
    engine.rebalance_events.append(event)

    next_month = (engine.config.start_date.replace(day=1) + pd.offsets.MonthBegin(1)).date()
    assert engine._should_rebalance_scheduled(next_month) is True


def test_run_raises_when_period_empty(engine: BacktestEngine) -> None:
    """If no data exists in the requested period, the engine should raise."""
    engine.prices = engine.prices.iloc[0:0]
    engine.returns = engine.returns.iloc[0:0]

    with pytest.raises(InsufficientHistoryError):
        engine.run()


def test_run_generates_equity_curve(engine: BacktestEngine) -> None:
    """Even without rebalances the engine should record equity values."""
    equity_df, metrics, events = engine.run()

    assert not equity_df.empty
    assert metrics.num_rebalances == 0
    assert events == []
