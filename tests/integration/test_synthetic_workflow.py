"""End-to-end workflow tests using synthetic market fixtures."""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from portfolio_management.assets.universes.universes import UniverseManager
from portfolio_management.backtesting.engine import (
    BacktestConfig,
    BacktestEngine,
    RebalanceFrequency,
)
from portfolio_management.core.exceptions import InsufficientDataError
from portfolio_management.data.analysis import collect_available_extensions
from portfolio_management.data.ingestion import build_stooq_index
from portfolio_management.data.io.io import (
    export_tradeable_prices,
    load_tradeable_instruments,
    write_match_report,
    write_stooq_index,
    write_unmatched_report,
)
from portfolio_management.data.matching import (
    annotate_unmatched_instruments,
    build_stooq_lookup,
    match_tradeables,
)
from portfolio_management.data.models import (
    ExportConfig,
    TradeableInstrument,
    TradeableMatch,
)
from portfolio_management.portfolio.builder import PortfolioConstructor
from portfolio_management.portfolio.constraints.models import PortfolioConstraints
from portfolio_management.portfolio.strategies import (
    EqualWeightStrategy,
    RiskParityStrategy,
)
from tests.synthetic_data import SyntheticDataset, generate_synthetic_market


@dataclass
class SyntheticWorkflowArtifacts:
    dataset: SyntheticDataset
    matches: list[TradeableMatch]
    unmatched: list[TradeableInstrument]
    match_df: pd.DataFrame
    unmatched_df: pd.DataFrame


@pytest.fixture(scope="module")
def synthetic_workflow(
    tmp_path_factory: pytest.TempPathFactory,
) -> SyntheticWorkflowArtifacts:
    """Generate synthetic data and execute the preparation pipeline."""
    root = tmp_path_factory.mktemp("synthetic_workflow")
    dataset = generate_synthetic_market(root)

    entries = build_stooq_index(dataset.stooq_dir, max_workers=4)
    write_stooq_index(entries, dataset.metadata_dir / "stooq_index.csv")

    tradeables = load_tradeable_instruments(dataset.tradeable_dir)
    by_ticker, by_stem, by_base = build_stooq_lookup(entries)
    matches, unmatched = match_tradeables(
        tradeables, by_ticker, by_stem, by_base, max_workers=4
    )

    diagnostics, _, _, _, _ = write_match_report(
        matches,
        dataset.metadata_dir / "tradeable_matches.csv",
        dataset.stooq_dir,
        lse_currency_policy="broker",
    )
    annotated_unmatched = annotate_unmatched_instruments(
        unmatched,
        by_base,
        collect_available_extensions(entries),
    )
    write_unmatched_report(
        annotated_unmatched,
        dataset.metadata_dir / "tradeable_unmatched.csv",
    )

    export_tradeable_prices(
        matches,
        ExportConfig(
            data_dir=dataset.stooq_dir,
            dest_dir=dataset.prices_output_dir,
            overwrite=True,
            max_workers=4,
            diagnostics=diagnostics,
        ),
    )

    match_df = pd.read_csv(dataset.metadata_dir / "tradeable_matches.csv")
    unmatched_df = pd.read_csv(dataset.metadata_dir / "tradeable_unmatched.csv")

    return SyntheticWorkflowArtifacts(
        dataset=dataset,
        matches=matches,
        unmatched=annotated_unmatched,
        match_df=match_df,
        unmatched_df=unmatched_df,
    )


def test_data_preparation_outputs(
    synthetic_workflow: SyntheticWorkflowArtifacts,
) -> None:
    """Validate match report contents and exported price coverage."""
    match_df = synthetic_workflow.match_df

    assert len(match_df) == len(synthetic_workflow.matches) == 36
    statuses = set(match_df["data_status"])
    assert {"ok", "warning", "sparse"}.issubset(statuses)

    exported_files = sorted(
        path.name for path in synthetic_workflow.dataset.prices_output_dir.glob("*.csv")
    )
    assert len(exported_files) == len(synthetic_workflow.matches)

    unmatched_symbols = set(synthetic_workflow.unmatched_df["symbol"])
    expected_unmatched = {
        "SYN_STOCKS_06:US",
        "SYN_BONDS_06:US",
        "SYN_REITS_06:US",
        "SYN_COMMODITIES_06:US",
        "SYN_UNKNOWN_01:US",
    }
    assert expected_unmatched.issubset(unmatched_symbols)


@pytest.fixture(scope="module")
def universe_manager(synthetic_workflow: SyntheticWorkflowArtifacts) -> UniverseManager:
    """Instantiate UniverseManager using synthetic match data."""
    return UniverseManager(
        synthetic_workflow.dataset.universe_config,
        synthetic_workflow.match_df,
        synthetic_workflow.dataset.prices_output_dir,
    )


def test_universe_loading(universe_manager: UniverseManager) -> None:
    """Ensure both strict and balanced universes load successfully."""
    strict_payload = universe_manager.load_universe("synthetic_strict", use_cache=False)
    balanced_payload = universe_manager.load_universe(
        "synthetic_balanced", use_cache=False
    )

    assert strict_payload is not None
    assert balanced_payload is not None

    assert strict_payload["returns"].shape[1] == 16
    assert balanced_payload["returns"].shape[1] > strict_payload["returns"].shape[1]

    strict_assets_frame = strict_payload["assets"]
    assert isinstance(strict_assets_frame, pd.DataFrame)
    assert set(strict_assets_frame["data_status"].unique()) == {"ok"}


def _prepare_returns_for_portfolio(
    universe_payload: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    returns = universe_payload["returns"].copy()
    return returns.dropna(how="all", axis=0)


def test_return_pipeline_balanced(universe_manager: UniverseManager) -> None:
    """Check the balanced universe return matrix handles gaps and warnings."""
    balanced = universe_manager.load_universe("synthetic_balanced", use_cache=False)
    returns = balanced["returns"]

    # Weekly frequency expected; ensure alignment and finite coverage.
    assert returns.index.inferred_type in {"datetime64", "datetime64tz"}
    assert returns.notna().mean().mean() > 0.7

    coverage = universe_manager.return_calculator.latest_summary.coverage
    assert (coverage >= 0.7).all()


def _strategy_names(constructor: PortfolioConstructor) -> list[str]:
    return constructor.list_strategies()


def _build_constructor() -> PortfolioConstructor:
    return PortfolioConstructor(
        constraints=PortfolioConstraints(
            max_equity_exposure=0.8,
            min_weight=0.0,
            max_weight=0.25,
            min_bond_exposure=0.0,
        ),
    )


def _required_strategies(constructor: PortfolioConstructor) -> list[str]:
    names = _strategy_names(constructor)
    required = ["equal_weight"]
    if (
        importlib.util.find_spec("riskparityportfolio") is not None
        and "risk_parity" in names
    ):
        required.append("risk_parity")
    if importlib.util.find_spec("pypfopt") is not None:
        required.extend(
            candidate
            for candidate in ("mean_variance_max_sharpe", "mean_variance_min_vol")
            if candidate in names
        )
    return required


def _synthetic_strategy_dataset(periods: int) -> tuple[pd.DataFrame, pd.Series]:
    rng = np.random.default_rng(123)
    columns = [f"EQ{i}" for i in range(3)] + [f"BD{i}" for i in range(3)]
    means = np.array([0.0006, 0.0005, 0.0007, 0.0003, 0.00025, 0.00035])
    base = np.array(
        [
            [0.015, 0.012, 0.010, 0.002, 0.0015, 0.001],
            [0.012, 0.014, 0.009, 0.0015, 0.0012, 0.0008],
            [0.010, 0.009, 0.016, 0.001, 0.0011, 0.0009],
            [0.002, 0.0015, 0.001, 0.006, 0.004, 0.003],
            [0.0015, 0.0012, 0.0011, 0.004, 0.0055, 0.0035],
            [0.001, 0.0008, 0.0009, 0.003, 0.0035, 0.0065],
        ],
    )
    cov = base @ base.T
    data = rng.multivariate_normal(mean=means, cov=cov, size=periods)
    returns = pd.DataFrame(data, columns=columns)
    asset_classes = pd.Series(
        ["equity", "equity", "equity", "fixed_income", "fixed_income", "fixed_income"],
        index=columns,
    )
    return returns, asset_classes


def test_portfolio_construction_success() -> None:
    """All optional strategies should succeed on a well-behaved dataset."""
    returns, asset_classes = _synthetic_strategy_dataset(periods=400)

    constructor = _build_constructor()
    successful: dict[str, pd.Series] = {}
    for strategy in _required_strategies(constructor):
        portfolio = constructor.construct(
            strategy, returns, asset_classes=asset_classes
        )
        successful[strategy] = portfolio.weights

    assert successful, "Expected at least one strategy to succeed."
    for name, weights in successful.items():
        assert np.isclose(weights.sum(), 1.0), f"{name} weights do not sum to 1.0"
        assert (weights >= -1e-6).all(), f"{name} produced negative weights."


def test_portfolio_construction_insufficient_history() -> None:
    """Risk parity and mean-variance should reject when history is too short."""
    short_returns, asset_classes = _synthetic_strategy_dataset(periods=100)

    constructor = _build_constructor()

    # Equal weight still succeeds even with short histories.
    eq_portfolio = constructor.construct(
        "equal_weight", short_returns, asset_classes=asset_classes
    )
    assert np.isclose(eq_portfolio.weights.sum(), 1.0)

    needs_long_history = (
        ["risk_parity"]
        if importlib.util.find_spec("riskparityportfolio") is not None
        else []
    )
    if importlib.util.find_spec("pypfopt") is not None:
        names = _strategy_names(constructor)
        needs_long_history.extend(
            candidate
            for candidate in ("mean_variance_max_sharpe", "mean_variance_min_vol")
            if candidate in names
        )

    for strategy in needs_long_history:
        with pytest.raises(InsufficientDataError):
            constructor.construct(strategy, short_returns, asset_classes=asset_classes)


def test_backtesting_strategies(universe_manager: UniverseManager) -> None:
    """Validate backtest engine across available strategies."""
    balanced = universe_manager.load_universe("synthetic_balanced", use_cache=False)
    returns = _prepare_returns_for_portfolio(balanced)
    prices = (1 + returns).cumprod() * 100.0

    config = BacktestConfig(
        start_date=returns.index[0].date(),
        end_date=returns.index[-1].date(),
        rebalance_frequency=RebalanceFrequency.MONTHLY,
    )

    strategies: dict[str, EqualWeightStrategy | RiskParityStrategy] = {
        "equal_weight": EqualWeightStrategy(),
    }
    if importlib.util.find_spec("riskparityportfolio") is not None:
        strategies["risk_parity"] = RiskParityStrategy()

    engine_results = {}
    for name, strategy in strategies.items():
        engine = BacktestEngine(
            config=config, strategy=strategy, prices=prices, returns=returns
        )
        equity_curve, metrics, events = engine.run()
        assert not equity_curve.empty
        assert metrics.total_return is not None
        assert isinstance(events, list)
        engine_results[name] = metrics

    assert engine_results


def test_cli_smoke_workflow(
    synthetic_workflow: SyntheticWorkflowArtifacts,
    tmp_path: Path,
) -> None:
    """Smoke test CLI components using the synthetic dataset."""
    from scripts.calculate_returns import parse_args as parse_returns_args
    from scripts.calculate_returns import run_cli as run_returns_cli
    from scripts.construct_portfolio import parse_args as parse_portfolio_args
    from scripts.construct_portfolio import run_cli as run_portfolio_cli

    dataset = synthetic_workflow.dataset
    assets_df = synthetic_workflow.match_df[
        synthetic_workflow.match_df["data_status"] == "ok"
    ].head(12)
    assets_csv = tmp_path / "selected_assets.csv"
    assets_df[
        [
            "symbol",
            "isin",
            "name",
            "market",
            "region",
            "currency",
            "category",
            "price_start",
            "price_end",
            "price_rows",
            "data_status",
            "data_flags",
            "stooq_path",
            "resolved_currency",
            "currency_status",
        ]
    ].to_csv(assets_csv, index=False)

    returns_csv = tmp_path / "synthetic_returns.csv"
    returns_args = parse_returns_args(
        [
            "--assets",
            str(assets_csv),
            "--prices-dir",
            str(dataset.prices_output_dir),
            "--output",
            str(returns_csv),
            "--frequency",
            "weekly",
            "--method",
            "simple",
        ]
    )
    assert run_returns_cli(returns_args) == 0
    returns = pd.read_csv(returns_csv, index_col=0, parse_dates=True)
    assert not returns.empty

    weights_csv = tmp_path / "synthetic_weights.csv"
    portfolio_args = parse_portfolio_args(
        [
            "--returns",
            str(returns_csv),
            "--strategy",
            "equal_weight",
            "--output",
            str(weights_csv),
        ]
    )
    assert run_portfolio_cli(portfolio_args) == 0
    weights = pd.read_csv(weights_csv, index_col=0)
    assert not weights.empty
