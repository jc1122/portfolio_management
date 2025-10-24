"""
Low-Volatility Defensive Strategy Example

This script demonstrates a defensive investment strategy that focuses on
selecting assets with low volatility. It's designed to be more stable
and produce lower drawdowns than a broad market index, especially during
turbulent periods.

This example showcases:
- Selecting assets based on a low-volatility factor.
- Using a tight membership policy to ensure low turnover and long holding periods.
- Running the backtest on a large universe of assets.
- Analyzing the results with a focus on risk metrics.
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
    """Main function to run the low-volatility strategy backtest."""
    print("Running Low-Volatility Defensive Strategy Example...")

    # 1. Define Paths and Configuration
    # ----------------------------------
    config_dir = Path("config")
    data_dir = Path("outputs/long_history_1000")
    output_dir = Path("outputs/examples/lowvol_strategy")
    universe_file = config_dir / "universes_long_history.yaml"
    prices_file = data_dir / "long_history_1000_prices_daily.csv"
    returns_file = data_dir / "long_history_1000_returns_daily.csv.gz"

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
    backtest_config = BacktestConfig(
        start_date=start_date,
        end_date=end_date,
        initial_capital=Decimal("100000"),
        rebalance_frequency=RebalanceFrequency.QUARTERLY, # Less frequent rebalancing for a defensive strategy
        use_pit_eligibility=True,
        min_history_days=252,
    )

    # 4. Configure Caching
    # ----------------------
    cache = FactorCache(cache_dir=Path(".cache/examples"), enabled=True)
    print(f"Caching enabled at: {cache.cache_dir}")

    # 5. Configure Preselection (Low-Volatility Strategy)
    # -------------------------------------------------
    # Select the top 20 assets with the lowest volatility over the past year.
    preselection_config = PreselectionConfig(
        method=PreselectionMethod.LOW_VOL,
        top_k=20,
        lookback=252,
    )
    preselection = Preselection(preselection_config, cache=cache)
    print("Low-volatility preselection configured: Top 20 assets with 12-month lookback.")

    # 6. Configure Membership Policy (Tight Turnover Control)
    # -------------------------------------------------------
    # Use a very tight membership policy to ensure low turnover, a hallmark of
    # defensive strategies.
    membership_policy = MembershipPolicy(
        min_holding_periods=4,  # Hold for at least 4 quarters (1 year)
        max_turnover=0.2,       # Allow a maximum of 20% turnover per rebalance
    )
    print("Membership policy configured: min_holding_periods=4, max_turnover=0.2.")

    # 7. Create and Run the Backtest Engine
    # ---------------------------------------
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
    output_dir.mkdir(parents=True, exist_ok=True)

    equity_curve_df = pd.DataFrame(equity_curve, columns=["date", "equity"]).set_index("date")
    equity_curve_df.to_csv(output_dir / "equity_curve.csv")

    report = create_summary_report(equity_curve_df, metrics, rebalance_events)
    with open(output_dir / "summary_report.yaml", "w") as f:
        yaml.dump(report, f, default_flow_style=False)

    print("\n----- Backtest Summary (Low-Volatility) -----")
    for key, value in report.items():
        if isinstance(value, dict):
            print(f"{key}:")
            for sub_key, sub_value in value.items():
                print(f"  {sub_key}: {sub_value}")
        else:
            print(f"{key}: {value}")

    print(f"\nResults saved to {output_dir}")
    print("Low-volatility strategy example finished successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
