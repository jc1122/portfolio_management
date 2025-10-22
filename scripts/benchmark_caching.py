"""Benchmark script to measure performance improvement from statistics caching.

This script profiles the performance of portfolio construction strategies with and
without statistics caching on a large universe (300+ assets).
"""

import time
from typing import Any

import numpy as np
import pandas as pd

from portfolio_management.portfolio.constraints.models import PortfolioConstraints
from portfolio_management.portfolio.statistics import RollingStatistics


def generate_large_universe(n_assets: int = 300, n_periods: int = 504) -> pd.DataFrame:
    """Generate synthetic returns for a large universe.

    Args:
        n_assets: Number of assets in the universe
        n_periods: Number of periods (default: 504 = ~2 years of daily data)

    Returns:
        DataFrame of returns

    """
    np.random.seed(42)
    dates = pd.date_range("2020-01-01", periods=n_periods, freq="D")
    tickers = [f"ASSET_{i:03d}" for i in range(n_assets)]

    # Generate correlated returns using a factor model
    n_factors = 5
    factor_returns = np.random.randn(n_periods, n_factors) * 0.01
    factor_loadings = np.random.randn(n_assets, n_factors) * 0.5
    idiosyncratic = np.random.randn(n_periods, n_assets) * 0.01

    returns = factor_returns @ factor_loadings.T + idiosyncratic

    return pd.DataFrame(returns, index=dates, columns=tickers)


def benchmark_risk_parity(
    returns: pd.DataFrame,
    n_rebalances: int = 12,
    use_cache: bool = False,
) -> tuple[float, list[Any]]:
    """Benchmark RiskParityStrategy performance.

    Args:
        returns: Full returns DataFrame
        n_rebalances: Number of rebalancing periods to simulate
        use_cache: Whether to use statistics caching

    Returns:
        Tuple of (total_time, portfolios)

    """
    try:
        from portfolio_management.portfolio.strategies.risk_parity import (
            RiskParityStrategy,
        )
    except ImportError:
        print("RiskParityStrategy not available, skipping benchmark")
        return 0.0, []

    constraints = PortfolioConstraints(max_weight=0.25, min_weight=0.0)

    # Create strategy with or without cache
    if use_cache:
        cache = RollingStatistics(window_size=252)
        strategy = RiskParityStrategy(min_periods=252, statistics_cache=cache)
    else:
        strategy = RiskParityStrategy(min_periods=252)

    portfolios = []
    start_time = time.time()

    # Simulate monthly rebalances (rolling window)
    window_size = 252
    step_size = 21  # ~1 month

    for i in range(n_rebalances):
        start_idx = i * step_size
        end_idx = start_idx + window_size

        if end_idx > len(returns):
            break

        returns_window = returns.iloc[start_idx:end_idx]

        # Skip if universe is too large (falls back to inverse volatility)
        if len(returns_window.columns) <= 300:
            try:
                portfolio = strategy.construct(returns_window, constraints)
                portfolios.append(portfolio)
            except Exception as e:
                print(f"Rebalance {i} failed: {e}")
                continue

    end_time = time.time()
    total_time = end_time - start_time

    return total_time, portfolios


def benchmark_mean_variance(
    returns: pd.DataFrame,
    n_rebalances: int = 12,
    use_cache: bool = False,
) -> tuple[float, list[Any]]:
    """Benchmark MeanVarianceStrategy performance.

    Args:
        returns: Full returns DataFrame
        n_rebalances: Number of rebalancing periods to simulate
        use_cache: Whether to use statistics caching

    Returns:
        Tuple of (total_time, portfolios)

    """
    try:
        from portfolio_management.portfolio.strategies.mean_variance import (
            MeanVarianceStrategy,
        )
    except ImportError:
        print("MeanVarianceStrategy not available, skipping benchmark")
        return 0.0, []

    constraints = PortfolioConstraints(max_weight=0.25, min_weight=0.0)

    # Create strategy with or without cache
    if use_cache:
        cache = RollingStatistics(window_size=252)
        strategy = MeanVarianceStrategy(
            objective="min_volatility",
            min_periods=252,
            statistics_cache=cache,
        )
    else:
        strategy = MeanVarianceStrategy(objective="min_volatility", min_periods=252)

    portfolios = []
    start_time = time.time()

    # Simulate monthly rebalances (rolling window)
    window_size = 252
    step_size = 21  # ~1 month

    for i in range(n_rebalances):
        start_idx = i * step_size
        end_idx = start_idx + window_size

        if end_idx > len(returns):
            break

        returns_window = returns.iloc[start_idx:end_idx]

        try:
            portfolio = strategy.construct(returns_window, constraints)
            portfolios.append(portfolio)
        except Exception as e:
            print(f"Rebalance {i} failed: {e}")
            continue

    end_time = time.time()
    total_time = end_time - start_time

    return total_time, portfolios


def print_results(
    strategy_name: str,
    time_no_cache: float,
    time_with_cache: float,
    n_portfolios_no_cache: int,
    n_portfolios_with_cache: int,
) -> None:
    """Print benchmark results.

    Args:
        strategy_name: Name of the strategy
        time_no_cache: Time without caching
        time_with_cache: Time with caching
        n_portfolios_no_cache: Number of portfolios constructed without cache
        n_portfolios_with_cache: Number of portfolios constructed with cache

    """
    if time_no_cache == 0 or n_portfolios_no_cache == 0:
        print(f"\n{strategy_name}: Benchmark skipped (strategy not available)")
        return

    speedup = time_no_cache / time_with_cache if time_with_cache > 0 else 0
    time_reduction_pct = (
        (time_no_cache - time_with_cache) / time_no_cache * 100
        if time_no_cache > 0
        else 0
    )

    print(f"\n{strategy_name} Benchmark Results:")
    print(f"  Portfolios constructed (no cache): {n_portfolios_no_cache}")
    print(f"  Portfolios constructed (with cache): {n_portfolios_with_cache}")
    print(f"  Time without cache: {time_no_cache:.2f}s")
    print(f"  Time with cache: {time_with_cache:.2f}s")
    print(f"  Speedup: {speedup:.2f}x")
    print(f"  Time reduction: {time_reduction_pct:.1f}%")


def main():
    """Run benchmarks and print results."""
    print("=" * 80)
    print("Portfolio Statistics Caching Benchmark")
    print("=" * 80)

    # Generate test data
    print("\nGenerating large universe (300 assets, 504 periods)...")
    returns = generate_large_universe(n_assets=300, n_periods=504)
    print(f"Generated returns: {returns.shape}")

    n_rebalances = 12  # Simulate 12 monthly rebalances

    # Benchmark RiskParityStrategy
    print("\n" + "-" * 80)
    print("Benchmarking RiskParityStrategy...")
    print("-" * 80)

    print("\nRunning WITHOUT cache...")
    time_rp_no_cache, portfolios_rp_no_cache = benchmark_risk_parity(
        returns,
        n_rebalances=n_rebalances,
        use_cache=False,
    )

    print("\nRunning WITH cache...")
    time_rp_with_cache, portfolios_rp_with_cache = benchmark_risk_parity(
        returns,
        n_rebalances=n_rebalances,
        use_cache=True,
    )

    print_results(
        "RiskParityStrategy",
        time_rp_no_cache,
        time_rp_with_cache,
        len(portfolios_rp_no_cache),
        len(portfolios_rp_with_cache),
    )

    # Benchmark MeanVarianceStrategy
    print("\n" + "-" * 80)
    print("Benchmarking MeanVarianceStrategy...")
    print("-" * 80)

    print("\nRunning WITHOUT cache...")
    time_mv_no_cache, portfolios_mv_no_cache = benchmark_mean_variance(
        returns,
        n_rebalances=n_rebalances,
        use_cache=False,
    )

    print("\nRunning WITH cache...")
    time_mv_with_cache, portfolios_mv_with_cache = benchmark_mean_variance(
        returns,
        n_rebalances=n_rebalances,
        use_cache=True,
    )

    print_results(
        "MeanVarianceStrategy",
        time_mv_no_cache,
        time_mv_with_cache,
        len(portfolios_mv_no_cache),
        len(portfolios_mv_with_cache),
    )

    # Summary
    print("\n" + "=" * 80)
    print("Summary")
    print("=" * 80)
    print(f"\nBenchmark configuration:")
    print(f"  Universe size: 300 assets")
    print(f"  Window size: 252 periods")
    print(f"  Number of rebalances: {n_rebalances}")
    print(f"  Overlap between rebalances: ~96% (21/252 periods shift)")
    print(
        "\nNote: The performance improvement is most significant for strategies",
    )
    print("      that compute covariance matrices, especially with large universes.")


if __name__ == "__main__":
    main()
