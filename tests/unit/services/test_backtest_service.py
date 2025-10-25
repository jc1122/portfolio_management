from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any

import pandas as pd
from portfolio_management.backtesting import BacktestConfig, PerformanceMetrics, RebalanceFrequency
from portfolio_management.services import BacktestRequest, BacktestResult, BacktestService


def _dummy_config() -> BacktestConfig:
    return BacktestConfig(
        start_date=pd.Timestamp("2023-01-01").date(),
        end_date=pd.Timestamp("2023-01-05").date(),
        initial_capital=Decimal("100000"),
        rebalance_frequency=RebalanceFrequency.DAILY,
        rebalance_threshold=0.0,
        commission_pct=0.0,
        commission_min=0.0,
        slippage_bps=0.0,
        lookback_periods=5,
        use_pit_eligibility=False,
        min_history_days=1,
        min_price_rows=1,
    )


def test_run_backtest_invokes_dependencies(tmp_path: Path) -> None:
    prices = pd.DataFrame({"AAA": [10, 11, 12]}, index=pd.date_range("2023-01-01", periods=3))
    returns = prices.pct_change().fillna(0.0)
    metrics = PerformanceMetrics(
        total_return=0.1,
        annualized_return=0.1,
        annualized_volatility=0.2,
        sharpe_ratio=1.0,
        sortino_ratio=1.0,
        max_drawdown=0.1,
        calmar_ratio=1.0,
        expected_shortfall_95=0.0,
        win_rate=0.5,
        avg_win=0.01,
        avg_loss=-0.01,
        turnover=0.1,
        total_costs=Decimal("0"),
        num_rebalances=1,
        final_value=Decimal("110000"),
    )

    class StubEngine:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs

        def run(self):
            equity_curve = pd.DataFrame({"equity": [100000, 110000]}, index=pd.date_range("2023-01-01", periods=2))
            events = [object()]
            return equity_curve, metrics, events

    captured = {
        "printed": False,
        "saved": False,
        "cache_reported": False,
    }

    def printer(metric_obj: PerformanceMetrics, verbose: bool) -> None:
        captured["printed"] = True
        assert metric_obj is metrics
        assert verbose is True

    def saver(output_dir: Path, config: BacktestConfig, equity_curve: pd.DataFrame, events, metric_obj, save_trades, visualize, verbose):
        captured["saved"] = True
        assert output_dir == tmp_path
        assert config == _dummy_config()
        assert isinstance(equity_curve, pd.DataFrame)
        assert metric_obj is metrics
        assert save_trades is True
        assert visualize is True
        assert verbose is True

    def cache_reporter(cache_obj: Any) -> None:
        captured["cache_reported"] = True
        assert cache_obj == "cache"

    service = BacktestService(
        engine_factory=lambda **kwargs: StubEngine(**kwargs),
        results_printer=printer,
        results_saver=saver,
        cache_reporter=cache_reporter,
    )

    request = BacktestRequest(
        config=_dummy_config(),
        strategy=object(),  # type: ignore[arg-type]
        prices=prices,
        returns=returns,
        preselection=None,
        membership_policy=None,
        cache="cache",
        output_dir=tmp_path,
        save_trades=True,
        visualize=True,
        verbose=True,
    )

    result = service.run(request)

    assert isinstance(result, BacktestResult)
    assert captured["printed"]
    assert captured["saved"]
    assert captured["cache_reported"]


def test_run_backtest_omits_cache_reporting_when_not_verbose(tmp_path: Path) -> None:
    prices = pd.DataFrame({"AAA": [10, 11]}, index=pd.date_range("2023-01-01", periods=2))
    returns = prices.pct_change().fillna(0.0)
    metrics = PerformanceMetrics(
        total_return=0.1,
        annualized_return=0.1,
        annualized_volatility=0.2,
        sharpe_ratio=1.0,
        sortino_ratio=1.0,
        max_drawdown=0.1,
        calmar_ratio=1.0,
        expected_shortfall_95=0.0,
        win_rate=0.5,
        avg_win=0.01,
        avg_loss=-0.01,
        turnover=0.1,
        total_costs=Decimal("0"),
        num_rebalances=1,
        final_value=Decimal("110000"),
    )

    class StubEngine:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs

        def run(self):
            equity_curve = pd.DataFrame({"equity": [100000, 110000]}, index=pd.date_range("2023-01-01", periods=2))
            events = [object()]
            return equity_curve, metrics, events

    cache_called = False

    def cache_reporter(_cache: Any) -> None:
        nonlocal cache_called
        cache_called = True

    service = BacktestService(
        engine_factory=lambda **kwargs: StubEngine(**kwargs),
        results_printer=lambda *args, **kwargs: None,
        results_saver=lambda *args, **kwargs: None,
        cache_reporter=cache_reporter,
    )

    request = BacktestRequest(
        config=_dummy_config(),
        strategy=object(),  # type: ignore[arg-type]
        prices=prices,
        returns=returns,
        cache="cache",
        output_dir=tmp_path,
        save_trades=False,
        visualize=False,
        verbose=False,
    )

    service.run(request)

    assert cache_called is False
