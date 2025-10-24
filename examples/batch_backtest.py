"""
Batch Backtest Execution Example

This script demonstrates how to run multiple backtest configurations in a batch,
a common requirement for production environments or for running experiments.
It programmatically invokes the backtesting engine with different configurations
and saves the results in a structured way.

This example showcases:
- How to loop through multiple strategy configurations.
- How to call the backtesting engine programmatically.
- How to organize the output from multiple backtest runs.
- A practical pattern for automated, large-scale backtesting.
"""
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd
import yaml

from portfolio_management.backtesting import (
    BacktestConfig,
    BacktestEngine,
    RebalanceFrequency,
)
from portfolio_management.data.factor_caching import FactorCache
from portfolio_management.portfolio import (
    EqualWeightStrategy,
    MembershipPolicy,
    Preselection,
    PreselectionConfig,
    PreselectionMethod,
)
from portfolio_management.reporting.visualization import create_summary_report


def load_universe(universe_file: Path, universe_name: str) -> list[str]:
    """Load asset universe from YAML."""
    with open(universe_file) as f:
        config = yaml.safe_load(f)
    return config["universes"][universe_name]["assets"]


def load_data(
    prices_file: Path, returns_file: Path, assets: list[str]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load prices and returns data for specified assets."""
    prices = pd.read_csv(prices_file, index_col=0, parse_dates=True, usecols=["date", *assets])
    returns = pd.read_csv(returns_file, index_col=0, parse_dates=True, usecols=["date", *assets])
    return prices, returns


def run_single_backtest(
    config_name: str,
    preselection_config: PreselectionConfig,
    membership_policy: MembershipPolicy | None,
    prices: pd.DataFrame,
    returns: pd.DataFrame,
    cache: FactorCache,
):
    """
    Runs a single backtest with a given configuration.
    """
    print(f"\n----- Running Batch Backtest for: {config_name} -----")

    output_dir = Path(f"outputs/examples/batch_backtest/{config_name}")
    output_dir.mkdir(parents=True, exist_ok=True)

    backtest_config = BacktestConfig(
        start_date=date(2010, 1, 1),
        end_date=date(2023, 12, 31),
        initial_capital=Decimal("100000"),
        rebalance_frequency=RebalanceFrequency.MONTHLY,
        use_pit_eligibility=True,
    )

    preselection = Preselection(preselection_config, cache=cache)
    strategy = EqualWeightStrategy()

    engine = BacktestEngine(
        config=backtest_config,
        strategy=strategy,
        prices=prices,
        returns=returns,
        preselection=preselection,
        membership_policy=membership_policy,
        cache=cache,
    )

    equity_curve, metrics, rebalance_events = engine.run()

    equity_curve_df = pd.DataFrame(equity_curve, columns=["date", "equity"]).set_index("date")
    equity_curve_df.to_csv(output_dir / "equity_curve.csv")

    report = create_summary_report(equity_curve_df, metrics, rebalance_events)
    with open(output_dir / "summary_report.yaml", "w") as f:
        yaml.dump(report, f, default_flow_style=False)

    print(f"Finished backtest for '{config_name}'. Results saved to {output_dir}")
    return report


def main():
    """Main function to run the batch backtest."""
    print("Running Batch Backtest Execution Example...")

    # 1. Define Paths and Load Data
    # -----------------------------
    config_dir = Path("config")
    data_dir = Path("outputs/long_history_1000")
    universe_file = config_dir / "universes_long_history.yaml"
    prices_file = data_dir / "long_history_1000_prices_daily.csv"
    returns_file = data_dir / "long_history_1000_returns_daily.csv.gz"

    universe_name = "long_history_1000"
    assets = load_universe(universe_file, universe_name)
    prices, returns = load_data(prices_file, returns_file, assets)
    print("Data loaded. This will be reused for all backtests.")

    # 2. Setup Shared Cache
    # ---------------------
    cache = FactorCache(cache_dir=Path(".cache/examples"), enabled=True)
    print(f"Shared cache enabled at: {cache.cache_dir}")

    # 3. Define Batch Configurations
    # ------------------------------
    # A list of configurations to run. Each entry is a dictionary
    # that defines the parameters for a single backtest.
    batch_configs = [
        {
            "name": "Momentum_Top30_Buffer50",
            "preselection": PreselectionConfig(
                method=PreselectionMethod.MOMENTUM, top_k=30, lookback=252, skip=21
            ),
            "membership": MembershipPolicy(buffer_rank=50, min_holding_periods=3),
        },
        {
            "name": "LowVol_Top20_MaxTurnover0.2",
            "preselection": PreselectionConfig(
                method=PreselectionMethod.LOW_VOL, top_k=20, lookback=252
            ),
            "membership": MembershipPolicy(min_holding_periods=4, max_turnover=0.2),
        },
        {
            "name": "MultiFactor_60Mom_40LV",
            "preselection": PreselectionConfig(
                method=PreselectionMethod.COMBINED,
                top_k=25,
                lookback=252,
                momentum_weight=0.6,
                low_vol_weight=0.4,
            ),
            "membership": None,
        },
    ]

    # 4. Run the Batch
    # ----------------
    all_reports = {}
    for config in batch_configs:
        report = run_single_backtest(
            config_name=config["name"],
            preselection_config=config["preselection"],
            membership_policy=config["membership"],
            prices=prices,
            returns=returns,
            cache=cache,
        )
        all_reports[config["name"]] = report

    # 5. Print Final Summary
    # ----------------------
    print("\n\n----- Batch Backtest Final Summary -----")
    summary_df = pd.DataFrame({name: r["performance"] for name, r in all_reports.items()}).T
    print(summary_df[["annualized_return_pct", "volatility_pct", "sharpe_ratio", "max_drawdown_pct"]])

    summary_df.to_csv("outputs/examples/batch_backtest/final_summary.csv")
    print("\nFull summary saved to outputs/examples/batch_backtest/final_summary.csv")
    print("Batch backtest example finished successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
