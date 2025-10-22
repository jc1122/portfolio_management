"""Benchmark script to measure BacktestEngine optimization improvements.

This script measures runtime and memory usage improvements from optimizing
the lookback slicing in BacktestEngine.run().
"""

import time
import tracemalloc
from datetime import date
from decimal import Decimal

import numpy as np
import pandas as pd

from portfolio_management.backtesting.engine import BacktestConfig, BacktestEngine
from portfolio_management.backtesting.models import RebalanceFrequency
from portfolio_management.portfolio.strategies import EqualWeightStrategy


def create_large_dataset(years: int = 10, num_assets: int = 50) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Create a large synthetic dataset for benchmarking.
    
    Args:
        years: Number of years of daily data
        num_assets: Number of assets in the universe
        
    Returns:
        Tuple of (prices_df, returns_df)
    """
    # Create ~252 trading days per year
    num_days = years * 252
    dates = pd.date_range("2010-01-01", periods=num_days, freq="B")
    
    # Generate correlated returns
    rng = np.random.default_rng(42)
    
    # Create correlation structure
    mean_returns = rng.uniform(0.00005, 0.0003, num_assets)
    volatilities = rng.uniform(0.01, 0.03, num_assets)
    
    # Generate returns with some correlation
    base_returns = rng.normal(0, 1, size=(len(dates), num_assets))
    market_factor = rng.normal(0, 1, size=(len(dates), 1))
    
    # Add market correlation
    returns = (base_returns * 0.7 + market_factor * 0.3) * volatilities + mean_returns
    
    # Create prices from cumulative returns
    prices = np.exp(np.cumsum(returns, axis=0)) * 100
    
    # Create DataFrames
    tickers = [f"ASSET_{i:03d}" for i in range(num_assets)]
    prices_df = pd.DataFrame(prices, index=dates, columns=tickers)
    returns_df = pd.DataFrame(returns, index=dates, columns=tickers)
    
    return prices_df, returns_df


def run_benchmark(
    prices: pd.DataFrame,
    returns: pd.DataFrame,
    rebalance_freq: RebalanceFrequency,
    description: str,
) -> dict[str, float]:
    """Run a single benchmark test.
    
    Args:
        prices: Price data
        returns: Return data
        rebalance_freq: Rebalancing frequency to test
        description: Description of this test
        
    Returns:
        Dictionary with timing and memory metrics
    """
    # Use actual data range
    start_date = prices.index[0].date()
    end_date = prices.index[-1].date()
    
    config = BacktestConfig(
        start_date=start_date,
        end_date=end_date,
        initial_capital=Decimal("100000"),
        rebalance_frequency=rebalance_freq,
    )
    
    strategy = EqualWeightStrategy()
    
    # Start memory tracking
    tracemalloc.start()
    start_time = time.perf_counter()
    
    # Run backtest
    engine = BacktestEngine(
        config=config,
        strategy=strategy,
        prices=prices,
        returns=returns,
    )
    equity_curve, metrics, events = engine.run()
    
    # Stop timing and memory tracking
    end_time = time.perf_counter()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    runtime = end_time - start_time
    peak_mb = peak / 1024 / 1024
    
    print(f"\n{description}")
    print(f"  Runtime: {runtime:.2f}s")
    print(f"  Peak Memory: {peak_mb:.1f} MB")
    print(f"  Num Rebalances: {metrics.num_rebalances}")
    print(f"  Total Return: {metrics.total_return:.2%}")
    print(f"  Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
    
    return {
        "runtime": runtime,
        "peak_memory_mb": peak_mb,
        "num_rebalances": metrics.num_rebalances,
        "total_return": metrics.total_return,
        "sharpe_ratio": metrics.sharpe_ratio,
    }


def main() -> None:
    """Run benchmark suite."""
    print("=" * 70)
    print("BacktestEngine Optimization Benchmark")
    print("=" * 70)
    
    # Create large dataset
    print("\nGenerating 10-year daily dataset with 50 assets...")
    prices, returns = create_large_dataset(years=10, num_assets=50)
    print(f"Dataset shape: {prices.shape}")
    print(f"Date range: {prices.index[0].date()} to {prices.index[-1].date()}")
    
    # Run benchmarks for different rebalancing frequencies
    results = {}
    
    results["monthly"] = run_benchmark(
        prices,
        returns,
        RebalanceFrequency.MONTHLY,
        "Monthly Rebalancing (realistic use case)",
    )
    
    results["quarterly"] = run_benchmark(
        prices,
        returns,
        RebalanceFrequency.QUARTERLY,
        "Quarterly Rebalancing (lower frequency)",
    )
    
    results["weekly"] = run_benchmark(
        prices,
        returns,
        RebalanceFrequency.WEEKLY,
        "Weekly Rebalancing (higher frequency)",
    )
    
    # Print summary
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"{'Frequency':<12} {'Runtime (s)':<12} {'Memory (MB)':<12} {'Rebalances':<12}")
    print("-" * 70)
    for freq, res in results.items():
        print(
            f"{freq.capitalize():<12} "
            f"{res['runtime']:<12.2f} "
            f"{res['peak_memory_mb']:<12.1f} "
            f"{res['num_rebalances']:<12}"
        )
    
    print("\n" + "=" * 70)
    print("Notes:")
    print("  - The optimization reduces slice creation from O(n²) to O(rebalances)")
    print("  - For monthly rebalancing over 10 years: ~120 rebalances vs ~2,520 days")
    print("  - Memory savings: Avoiding ~2,400 unnecessary DataFrame copies")
    print("=" * 70)


if __name__ == "__main__":
    main()
