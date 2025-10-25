"""Fast unit tests for backtesting engine logic using mocks."""

import pytest
import pandas as pd
from decimal import Decimal
from datetime import date
from unittest.mock import Mock

from portfolio_management.backtesting.engine.backtest import BacktestEngine
from portfolio_management.backtesting.models import RebalanceFrequency, RebalanceEvent


@pytest.mark.unit
def test_calculate_portfolio_value():
    """Test portfolio value calculation with mock holdings and prices."""
    # Mock a BacktestEngine instance to avoid its complex __init__
    engine = Mock(spec=BacktestEngine)
    engine.holdings = {"AAPL": 100, "GOOG": 50}
    engine.cash = Decimal("10000.00")

    # The method we want to test
    engine._calculate_portfolio_value = BacktestEngine._calculate_portfolio_value.__get__(engine)

    prices = pd.Series({"AAPL": 200.0, "GOOG": 1500.0, "MSFT": 300.0})

    # Expected value: (100 * 200) + (50 * 1500) + 10000 = 20000 + 75000 + 10000 = 105000
    expected_value = Decimal("105000.00")
    actual_value = engine._calculate_portfolio_value(prices)
    assert actual_value == expected_value


@pytest.mark.unit
def test_calculate_portfolio_value_with_missing_prices():
    """Test portfolio value calculation when a price is missing."""
    engine = Mock(spec=BacktestEngine)
    engine.holdings = {"AAPL": 100, "GOOG": 50}
    engine.cash = Decimal("10000.00")
    engine._calculate_portfolio_value = BacktestEngine._calculate_portfolio_value.__get__(engine)

    prices = pd.Series({"AAPL": 200.0, "MSFT": 300.0})  # GOOG is missing

    # Expected value: (100 * 200) + 10000 = 30000
    expected_value = Decimal("30000.00")
    actual_value = engine._calculate_portfolio_value(prices)
    assert actual_value == expected_value


@pytest.mark.unit
@pytest.mark.parametrize(
    "freq,last_date,current_date,expected",
    [
        (RebalanceFrequency.DAILY, date(2023, 1, 1), date(2023, 1, 2), True),
        (RebalanceFrequency.DAILY, date(2023, 1, 1), date(2023, 1, 1), False),
        (RebalanceFrequency.WEEKLY, date(2023, 1, 1), date(2023, 1, 8), True),
        (RebalanceFrequency.WEEKLY, date(2023, 1, 1), date(2023, 1, 7), False),
        (RebalanceFrequency.MONTHLY, date(2023, 1, 15), date(2023, 2, 1), True),
        (RebalanceFrequency.MONTHLY, date(2023, 1, 15), date(2023, 1, 28), False),
        (RebalanceFrequency.QUARTERLY, date(2023, 1, 15), date(2023, 4, 15), True),
        (RebalanceFrequency.QUARTERLY, date(2023, 1, 15), date(2023, 3, 28), False),
        (RebalanceFrequency.ANNUAL, date(2023, 1, 15), date(2024, 1, 1), True),
        (RebalanceFrequency.ANNUAL, date(2023, 1, 15), date(2023, 12, 31), False),
    ],
)
def test_should_rebalance_scheduled(freq, last_date, current_date, expected):
    """Test the logic for scheduled rebalancing triggers."""
    engine = Mock(spec=BacktestEngine)
    engine.config = Mock()
    engine.config.rebalance_frequency = freq
    engine.rebalance_events = [Mock(spec=RebalanceEvent, date=last_date)]
    engine._should_rebalance_scheduled = BacktestEngine._should_rebalance_scheduled.__get__(engine)

    assert engine._should_rebalance_scheduled(current_date) == expected


@pytest.mark.unit
def test_should_rebalance_scheduled_no_prior_rebalance():
    """Test that scheduled rebalancing is false if no rebalances have occurred."""
    engine = Mock(spec=BacktestEngine)
    engine.rebalance_events = []
    engine._should_rebalance_scheduled = BacktestEngine._should_rebalance_scheduled.__get__(engine)

    assert not engine._should_rebalance_scheduled(date(2023, 1, 1))
