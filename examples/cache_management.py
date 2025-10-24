"""
Cache Management and Performance Example

This script provides a hands-on demonstration of the factor caching system.
The caching system is designed to dramatically speed up backtests by storing
the results of expensive calculations (like factor scores and PIT eligibility)
on disk.

This example will:
1.  Configure and run a backtest with caching enabled.
2.  Run the *exact same backtest* a second time to show the performance gain
    when the results are read from the cache.
3.  Demonstrate how to access and print cache statistics (hits, misses, etc.).
4.  Show how to clear the cache for a specific backtest.
"""
import sys
import time
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


def run_backtest_with_timing(
    engine: BacktestEngine, run_name: str
):
    """Runs the backtest and prints the execution time."""
    print(f"\n--- Running backtest: {run_name} ---")
    start_time = time.time()
    engine.run()
    end_time = time.time()
    print(f"Execution time: {end_time - start_time:.2f} seconds")


def main():
    """Main function to demonstrate cache management."""
    print("Running Cache Management and Performance Example...")

    # 1. Setup: Load data and configure the backtest
    # -----------------------------------------------
    config_dir = Path("config")
    data_dir = Path("outputs/long_history_1000")
    universe_file = config_dir / "universes_long_history.yaml"
    prices_file = data_dir / "long_history_1000_prices_daily.csv"
    returns_file = data_dir / "long_history_1000_returns_daily.csv.gz"
    universe_name = "long_history_1000"

    assets = load_universe(universe_file, universe_name)
    prices, returns = load_data(prices_file, returns_file, assets)

    backtest_config = BacktestConfig(
        start_date=date(2018, 1, 1),
        end_date=date(2023, 12, 31), # Shorter period for quicker demonstration
        initial_capital=Decimal("100000"),
        rebalance_frequency=RebalanceFrequency.MONTHLY,
        use_pit_eligibility=True,
    )

    preselection_config = PreselectionConfig(
        method=PreselectionMethod.MOMENTUM, top_k=50, lookback=252
    )

    # 2. Initialize the Cache
    # -----------------------
    # We create a dedicated cache directory for this example.
    cache = FactorCache(cache_dir=Path(".cache/cache_demo"), enabled=True)
    print(f"Cache initialized at: {cache.cache_dir}")
    print("Clearing any previous cache entries for a clean run...")
    cache.clear()
    cache.reset_stats()

    # 3. Create the Backtest Engine
    # -----------------------------
    preselection = Preselection(preselection_config, cache=cache)
    strategy = EqualWeightStrategy()
    engine = BacktestEngine(
        config=backtest_config,
        strategy=strategy,
        prices=prices,
        returns=returns,
        preselection=preselection,
        membership_policy=None,
        cache=cache,
    )

    # 4. First Run (Populating the Cache)
    # -----------------------------------
    # The first time the backtest is run, the cache is empty. All factor
    # scores will be calculated from scratch and then saved to the cache.
    run_backtest_with_timing(engine, "First Run (Cache Misses)")

    print("\nCache statistics after first run:")
    cache.print_stats() # Should show all misses

    # 5. Second Run (Reading from the Cache)
    # --------------------------------------
    # Now, we run the exact same backtest again. This time, the engine will
    # find the pre-calculated results in the cache, leading to a significant
    # speedup.
    cache.reset_stats() # Reset stats for a clean measurement
    run_backtest_with_timing(engine, "Second Run (Cache Hits)")

    print("\nCache statistics after second run:")
    cache.print_stats() # Should show all hits

    print("\nCache management example finished successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
