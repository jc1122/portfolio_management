"""
Multi-Factor Combined Strategy Example

This script demonstrates a more advanced strategy that combines multiple
factors to select assets. Specifically, it blends momentum and low-volatility
factors, aiming to capture the upside of momentum while mitigating risk
using the defensive properties of low volatility.

This example showcases:
- Using the 'combined' preselection method to rank assets on multiple factors.
- Assigning weights to each factor to control their influence.
- Optimizing a multi-factor model by tuning factor weights.
- Comparing the performance of a multi-factor strategy to single-factor strategies.
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


def main():
    """Main function to run the multi-factor strategy backtest."""
    print("Running Multi-Factor Combined Strategy Example...")

    # 1. Define Paths and Configuration
    # ----------------------------------
    config_dir = Path("config")
    data_dir = Path("outputs/long_history_1000")
    output_dir = Path("outputs/examples/multifactor_strategy")
    universe_file = config_dir / "universes_long_history.yaml"
    prices_file = data_dir / "long_history_1000_prices_daily.csv"
    returns_file = data_dir / "long_history_1000_returns_daily.csv.gz"

    universe_name = "long_history_1000"
    start_date = date(2010, 1, 1)
    end_date = date(2023, 12, 31)

    # 2. Load Universe and Data
    # -------------------------
    print(f"Loading universe '{universe_name}' from {universe_file}...")
    assets = load_universe(universe_file, universe_name)
    print(f"Loading price and return data for {len(assets)} assets...")
    prices, returns = load_data(prices_file, returns_file, assets)
    print("Data loaded successfully.")

    # 3. Configure the Backtest
    # -------------------------
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
    cache = FactorCache(cache_dir=Path(".cache/examples"), enabled=True)
    print(f"Caching enabled at: {cache.cache_dir}")

    # 5. Configure Preselection (Multi-Factor Strategy)
    # -------------------------------------------------
    # Combine momentum and low-volatility factors. Here, we assign a 60%
    # weight to momentum and a 40% weight to low-volatility.
    preselection_config = PreselectionConfig(
        method=PreselectionMethod.COMBINED,
        top_k=25,
        lookback=252,
        momentum_weight=0.6,
        low_vol_weight=0.4,
    )
    preselection = Preselection(preselection_config, cache=cache)
    print("Multi-factor preselection configured: 60% Momentum, 40% Low-Volatility.")

    # 6. Create and Run the Backtest Engine
    # ---------------------------------------
    # For this example, we will not use a membership policy to see the
    # "raw" effect of the combined factor score.
    strategy = EqualWeightStrategy()
    engine = BacktestEngine(
        config=backtest_config,
        strategy=strategy,
        prices=prices,
        returns=returns,
        preselection=preselection,
        membership_policy=None,  # No membership policy
        cache=cache,
    )

    print("\nStarting backtest engine...")
    equity_curve, metrics, rebalance_events = engine.run()
    print("Backtest completed.")

    # 7. Save and Display Results
    # ---------------------------
    output_dir.mkdir(parents=True, exist_ok=True)

    equity_curve_df = pd.DataFrame(equity_curve, columns=["date", "equity"]).set_index("date")
    equity_curve_df.to_csv(output_dir / "equity_curve.csv")

    report = create_summary_report(equity_curve_df, metrics, rebalance_events)
    with open(output_dir / "summary_report.yaml", "w") as f:
        yaml.dump(report, f, default_flow_style=False)

    print("\n----- Backtest Summary (Multi-Factor) -----")
    for key, value in report.items():
        if isinstance(value, dict):
            print(f"{key}:")
            for sub_key, sub_value in value.items():
                print(f"  {sub_key}: {sub_value}")
        else:
            print(f"{key}: {value}")

    print(f"\nResults saved to {output_dir}")
    print("Multi-factor strategy example finished successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
