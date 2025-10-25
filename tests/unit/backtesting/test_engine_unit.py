"""Unit tests for lightweight BacktestEngine helpers."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pandas as pd
import pytest

from portfolio_management.backtesting.engine.backtest import BacktestEngine
from portfolio_management.backtesting.models import (
    BacktestConfig,
    RebalanceEvent,
    RebalanceFrequency,
    RebalanceTrigger,
)
from portfolio_management.core.exceptions import InsufficientHistoryError


class _DummyStrategy:
    """Minimal strategy stub for engine construction."""

    min_history_periods = 1


def _make_engine() -> BacktestEngine:
    dates = pd.date_range("2020-01-01", periods=5, freq="D")
    prices = pd.DataFrame({"A": [100, 101, 102, 103, 104]}, index=dates)
    returns = prices.pct_change().fillna(0.0)

    config = BacktestConfig(
        start_date=dates[0].date(),
        end_date=dates[-1].date(),
        initial_capital=Decimal("100000"),
        rebalance_frequency=RebalanceFrequency.MONTHLY,
    )

    engine = BacktestEngine(config, _DummyStrategy(), prices, returns)
    engine.cash = Decimal("5000")
    engine.holdings = {"A": 10}
    return engine


@pytest.mark.unit
def test_calculate_portfolio_value_includes_holdings_and_cash() -> None:
    """Portfolio value is the sum of marked-to-market holdings and cash."""

    engine = _make_engine()
    latest_prices = pd.Series({"A": 110})

    value = engine._calculate_portfolio_value(latest_prices)

    assert value == Decimal("5000") + Decimal("10") * Decimal("110")


@pytest.mark.unit
def test_calculate_portfolio_value_ignores_missing_prices() -> None:
    """Holdings without available prices are skipped in the valuation."""

    engine = _make_engine()
    engine.holdings["B"] = 20
    latest_prices = pd.Series({"A": 110, "B": float("nan")})

    value = engine._calculate_portfolio_value(latest_prices)

    assert value == Decimal("5000") + Decimal("10") * Decimal("110")


@pytest.mark.unit
def test_should_rebalance_scheduled_returns_false_without_events() -> None:
    """No scheduled rebalance occurs until the first event is recorded."""

    engine = _make_engine()
    today = engine.config.start_date

    assert engine._should_rebalance_scheduled(today) is False


@pytest.mark.unit
def test_should_rebalance_scheduled_monthly_gap() -> None:
    """Monthly schedules trigger a rebalance when the calendar month advances."""

    engine = _make_engine()
    event = RebalanceEvent(
        date=engine.config.start_date,
        trigger=RebalanceTrigger.SCHEDULED,
        trades={},
        costs=Decimal("0"),
        pre_rebalance_value=Decimal("100000"),
        post_rebalance_value=Decimal("100000"),
        cash_before=Decimal("100000"),
        cash_after=Decimal("100000"),
    )
    engine.rebalance_events.append(event)

    next_month = engine.config.start_date + dt.timedelta(days=31)
    assert engine._should_rebalance_scheduled(next_month) is True


@pytest.mark.unit
def test_engine_requires_data_covering_period() -> None:
    """Engine initialisation raises when price data does not cover the range."""

    dates = pd.date_range("2020-01-02", periods=3, freq="D")
    prices = pd.DataFrame({"A": [100, 101, 102]}, index=dates)
    returns = prices.pct_change().fillna(0.0)

    config = BacktestConfig(
        start_date=dt.date(2020, 1, 1),
        end_date=dt.date(2020, 1, 4),
        initial_capital=Decimal("100000"),
    )

    with pytest.raises(InsufficientHistoryError):
        BacktestEngine(config, _DummyStrategy(), prices, returns)
