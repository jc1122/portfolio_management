"""Unit tests for lightweight BacktestEngine behaviours."""

from __future__ import annotations

import datetime
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
from portfolio_management.portfolio.models import Portfolio
from portfolio_management.portfolio.strategies.base import PortfolioStrategy

pytestmark = pytest.mark.unit


class DummyStrategy(PortfolioStrategy):
    """Simple deterministic strategy for testing."""

    def __init__(self, min_periods: int = 1) -> None:
        self._min_periods = min_periods

    @property
    def name(self) -> str:
        return "dummy"

    @property
    def min_history_periods(self) -> int:
        return self._min_periods

    def construct(
        self,
        returns: pd.DataFrame,
        constraints,
        asset_classes=None,
    ) -> Portfolio:
        weights = pd.Series(1 / len(returns.columns), index=returns.columns)
        return Portfolio(weights=weights, strategy=self.name, metadata={})


@pytest.fixture
def engine_config(mock_price_data: pd.DataFrame) -> BacktestConfig:
    start = mock_price_data.index[0].date()
    end = mock_price_data.index[-1].date()
    return BacktestConfig(start_date=start, end_date=end)


def create_engine(
    mock_price_data: pd.DataFrame,
    mock_returns: pd.DataFrame,
    config: BacktestConfig,
) -> BacktestEngine:
    strategy = DummyStrategy()
    return BacktestEngine(config, strategy, mock_price_data, mock_returns)


def test_engine_initializes_with_cash(mock_price_data, mock_returns, engine_config) -> None:
    """Cash should equal the configured initial capital and holdings empty."""

    engine = create_engine(mock_price_data, mock_returns, engine_config)

    assert engine.cash == engine_config.initial_capital
    assert engine.holdings == {}


def test_engine_raises_when_history_missing(mock_price_data, mock_returns, engine_config) -> None:
    """Constructor should guard against insufficient historical coverage."""

    bad_config = BacktestConfig(
        start_date=engine_config.start_date - datetime.timedelta(days=30),
        end_date=engine_config.end_date,
    )

    with pytest.raises(InsufficientHistoryError):
        create_engine(mock_price_data, mock_returns, bad_config)


def test_calculate_portfolio_value(mock_price_data, mock_returns, engine_config) -> None:
    """Portfolio value should include holdings and cash."""

    engine = create_engine(mock_price_data, mock_returns, engine_config)
    engine.cash = Decimal("1000")
    engine.holdings = {"AAA": 10, "BBB": 5}

    prices = mock_price_data.iloc[-1]
    value = engine._calculate_portfolio_value(prices)

    expected = (
        Decimal(str(10 * float(prices["AAA"])))
        + Decimal(str(5 * float(prices["BBB"])))
        + Decimal("1000")
    )
    assert float(value) == pytest.approx(float(expected))


def test_calculate_holdings_value_ignores_missing_prices(mock_price_data, mock_returns, engine_config) -> None:
    """Holdings without price data should be ignored."""

    engine = create_engine(mock_price_data, mock_returns, engine_config)
    engine.holdings = {"AAA": 10, "ZZZ": 5}

    prices = mock_price_data.iloc[-1]
    value = engine._calculate_holdings_value(prices)

    assert value == Decimal(str(10 * float(prices["AAA"])))


def test_should_rebalance_scheduled_monthly(mock_price_data, mock_returns, engine_config) -> None:
    """Scheduled rebalancing should trigger when month changes."""

    engine = create_engine(mock_price_data, mock_returns, engine_config)
    engine.rebalance_events.append(
        RebalanceEvent(
            date=engine_config.start_date,
            trigger=RebalanceTrigger.SCHEDULED,
            trades={},
            costs=Decimal("0"),
            pre_rebalance_value=engine_config.initial_capital,
            post_rebalance_value=engine_config.initial_capital,
            cash_before=engine_config.initial_capital,
            cash_after=engine_config.initial_capital,
        )
    )

    next_month = engine_config.start_date + datetime.timedelta(days=31)

    assert engine._should_rebalance_scheduled(next_month)
    assert not engine._should_rebalance_scheduled(engine_config.start_date)
