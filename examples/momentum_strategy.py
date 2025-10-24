"""
Momentum Strategy with Turnover Control Example

This script demonstrates how to run a backtest for a momentum-based investment
strategy with turnover controls. It showcases the following features:

- Loading a universe of assets from a YAML configuration file.
- Using a preselection step to filter assets based on a momentum factor.
- Applying a membership policy to control portfolio churn and reduce
  transaction costs.
- Enabling Point-in-Time (PIT) eligibility to avoid lookahead bias.
- Caching factor scores to speed up subsequent backtest runs.
- Running the backtest and saving the results for analysis.

This example is configured to run a momentum strategy on a universe of
1000 assets, selecting the top 30 based on their 12-month momentum.
The membership policy uses a buffer of 50 ranks to reduce asset turnover.
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


def load_universe(universe_file: Path, universe_name: str) -> tuple[list[str], dict]:
    """Load asset universe and configuration from YAML."""
    with open(universe_file) as f:
        config = yaml.safe_load(f)
    universe = config["universes"][universe_name]
    return universe["assets"], universe


def load_data(
    prices_file: Path, returns_file: Path, assets: list[str]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load prices and returns data for specified assets."""
    prices = pd.read_csv(prices_file, index_col=0, parse_dates=True, usecols=["date", *assets])
    returns = pd.read_csv(returns_file, index_col=0, parse_dates=True, usecols=["date", *assets])
    return prices, returns


def main():
    """Main function to run the momentum strategy backtest."""
    print("Running Momentum Strategy with Turnover Control Example...")

    # 1. Define Paths and Configuration
    # ----------------------------------
    # Define the paths to the configuration and data files.
    # These are expected to be in the standard project layout.
    config_dir = Path("config")
    data_dir = Path("outputs/long_history_1000")
    output_dir = Path("outputs/examples/momentum_strategy")
    universe_file = config_dir / "universes_long_history.yaml"
    prices_file = data_dir / "long_history_1000_prices_daily.csv"
    returns_file = data_dir / "long_history_1000_returns_daily.csv.gz"

    # Define the universe and strategy parameters.
    universe_name = "long_history_1000"
    strategy_name = "equal_weight"
    start_date = date(2010, 1, 1)
    end_date = date(2023, 12, 31)

    # 2. Load Universe and Data
    # -------------------------
    print(f"Loading universe '{universe_name}' from {universe_file}...")
    assets, universe_config = load_universe(universe_file, universe_name)
    print(f"Loading price and return data for {len(assets)} assets...")
    prices, returns = load_data(prices_file, returns_file, assets)
    print("Data loaded successfully.")

    # 3. Configure the Backtest
    # -------------------------
    # Create the main backtest configuration object.
    backtest_config = BacktestConfig(
        start_date=start_date,
        end_date=end_date,
        initial_capital=Decimal("100000"),
        rebalance_frequency=RebalanceFrequency.MONTHLY,
        use_pit_eligibility=True,
        min_history_days=252,
    )

    # 4. Configure Caching
    # ----------------------
    # Set up on-disk caching to speed up factor and eligibility calculations.
    # The cache is stored in the `.cache/examples` directory.
    cache = FactorCache(
        cache_dir=Path(".cache/examples"),
        enabled=True,
        max_cache_age_days=7,
    )
    print(f"Caching enabled at: {cache.cache_dir}")

    # 5. Configure Preselection (Momentum Strategy)
    # ---------------------------------------------
    # Configure the preselection step to select the top 30 assets based on
    # a 12-month momentum score.
    preselection_config = PreselectionConfig(
        method=PreselectionMethod.MOMENTUM,
        top_k=30,
        lookback=252,
        skip=21,  # Skip the most recent month to avoid short-term reversal
    )
    preselection = Preselection(preselection_config, cache=cache)
    print("Momentum preselection configured: Top 30 assets with 12-month lookback.")

    # 6. Configure Membership Policy (Turnover Control)
    # -------------------------------------------------
    # Configure the membership policy to reduce portfolio churn.
    # A buffer_rank of 50 means an asset will stay in the portfolio as long
    # as its rank does not drop below 30 + 50 = 80.
    membership_policy = MembershipPolicy(buffer_rank=50, min_holding_periods=3)
    print("Membership policy configured: buffer_rank=50, min_holding_periods=3.")

    # 7. Create and Run the Backtest Engine
    # ---------------------------------------
    # Instantiate the backtest engine with all the configured components.
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

    print("\nStarting backtest engine...")
    equity_curve, metrics, rebalance_events = engine.run()
    print("Backtest completed.")

    # 8. Save and Display Results
    # ---------------------------
    # Create the output directory if it doesn't exist.
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save the equity curve and performance metrics.
    equity_curve_df = pd.DataFrame(equity_curve, columns=["date", "equity"]).set_index("date")
    equity_curve_df.to_csv(output_dir / "equity_curve.csv")

    report = create_summary_report(equity_curve_df, metrics, rebalance_events)
    with open(output_dir / "summary_report.yaml", "w") as f:
        yaml.dump(report, f, default_flow_style=False)

    print("\n----- Backtest Summary -----")
    for key, value in report.items():
        if isinstance(value, dict):
            print(f"{key}:")
            for sub_key, sub_value in value.items():
                print(f"  {sub_key}: {sub_value}")
        else:
            print(f"{key}: {value}")

    print(f"\nResults saved to {output_dir}")
    print("Momentum strategy example finished successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
