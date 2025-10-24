#!/usr/bin/env python3
"""Benchmark preselection factor computation performance.

This script profiles the performance characteristics of the preselection module,
measuring execution time, memory usage, and scaling behavior across different
universe sizes and configuration parameters.

Key profiling areas:
- Momentum factor computation
- Low-volatility factor computation
- Combined factor computation
- Ranking and selection operations
- Memory efficiency
- Scaling with universe size, lookback period, and rebalance frequency

Usage:
    python benchmarks/benchmark_preselection.py --all
    python benchmarks/benchmark_preselection.py --universe-sizes 100 500 1000
    python benchmarks/benchmark_preselection.py --profile-detail
"""

from __future__ import annotations

import argparse
import cProfile
import io
import pstats
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from portfolio_management.portfolio.preselection import (
    Preselection,
    PreselectionConfig,
    PreselectionMethod,
)


@dataclass
class BenchmarkResult:
    """Results from a single benchmark run."""

    scenario: str
    universe_size: int
    lookback: int
    method: str
    execution_time: float
    memory_mb: float | None = None
    compute_time: float | None = None
    rank_time: float | None = None
    select_time: float | None = None


class SyntheticDataGenerator:
    """Generate synthetic return data for benchmarking."""

    def __init__(self, seed: int = 42):
        """Initialize generator with random seed.

        Args:
            seed: Random seed for reproducibility
        """
        self.rng = np.random.default_rng(seed)

    def generate_returns(
        self,
        num_assets: int,
        num_days: int = 1260,  # ~5 years of daily data
        mean_return: float = 0.0005,
        volatility: float = 0.015,
    ) -> pd.DataFrame:
        """Generate synthetic return data.

        Creates realistic daily return series with:
        - Configurable mean and volatility
        - Cross-sectional dispersion in characteristics
        - Some assets with higher momentum
        - Some assets with lower volatility

        Args:
            num_assets: Number of assets to generate
            num_days: Number of trading days
            mean_return: Average daily return
            volatility: Average daily volatility

        Returns:
            DataFrame with returns (dates as index, assets as columns)
        """
        dates = pd.date_range("2020-01-01", periods=num_days, freq="B")
        returns_data = {}

        for i in range(num_assets):
            # Vary characteristics across assets
            asset_mean = mean_return * self.rng.uniform(0.5, 1.5)
            asset_vol = volatility * self.rng.uniform(0.5, 2.0)

            # Generate return series
            returns = self.rng.normal(asset_mean, asset_vol, num_days)
            returns_data[f"ASSET_{i:04d}"] = returns

        return pd.DataFrame(returns_data, index=dates)


class PreselectionBenchmark:
    """Benchmark suite for preselection performance."""

    def __init__(self, data_generator: SyntheticDataGenerator | None = None):
        """Initialize benchmark suite.

        Args:
            data_generator: Data generator (creates new one if None)
        """
        self.data_generator = data_generator or SyntheticDataGenerator()
        self.results: list[BenchmarkResult] = []

    def benchmark_factor_computation(
        self,
        method: PreselectionMethod,
        universe_sizes: list[int],
        lookback: int = 252,
        top_k: int = 30,
        iterations: int = 3,
    ) -> list[BenchmarkResult]:
        """Benchmark factor computation across universe sizes.

        Args:
            method: Preselection method to benchmark
            universe_sizes: List of universe sizes to test
            lookback: Lookback period for factor calculation
            top_k: Number of assets to select
            iterations: Number of iterations to average

        Returns:
            List of benchmark results
        """
        results = []

        for size in universe_sizes:
            print(f"\n{'='*60}")
            print(f"Benchmarking {method.value} with {size} assets")
            print(f"{'='*60}")

            # Generate data once per size
            returns = self.data_generator.generate_returns(size)
            rebalance_date = returns.index[-1].date()

            # Configure preselection
            config = PreselectionConfig(
                method=method,
                top_k=top_k,
                lookback=lookback,
                min_periods=min(60, lookback),
            )
            preselection = Preselection(config)

            # Run multiple iterations
            times = []
            for i in range(iterations):
                start = time.perf_counter()
                selected = preselection.select_assets(returns, rebalance_date)
                elapsed = time.perf_counter() - start
                times.append(elapsed)
                print(f"  Iteration {i+1}/{iterations}: {elapsed:.4f}s (selected {len(selected)} assets)")

            avg_time = np.mean(times)
            std_time = np.std(times)

            result = BenchmarkResult(
                scenario=f"{method.value}_size_{size}",
                universe_size=size,
                lookback=lookback,
                method=method.value,
                execution_time=avg_time,
            )
            results.append(result)

            print(f"  Average: {avg_time:.4f}s ± {std_time:.4f}s")
            print(f"  Speedup baseline (100 assets): {results[0].execution_time/avg_time:.2f}x" if len(results) > 1 else "")

        self.results.extend(results)
        return results

    def benchmark_time_breakdown(
        self,
        universe_size: int = 1000,
        lookback: int = 252,
        top_k: int = 30,
    ) -> BenchmarkResult:
        """Benchmark time breakdown into compute, rank, and select phases.

        Args:
            universe_size: Number of assets
            lookback: Lookback period
            top_k: Number of assets to select

        Returns:
            Benchmark result with time breakdown
        """
        print(f"\n{'='*60}")
        print(f"Time Breakdown Analysis ({universe_size} assets)")
        print(f"{'='*60}")

        returns = self.data_generator.generate_returns(universe_size)
        rebalance_date = returns.index[-1].date()

        # We'll manually time each phase
        config = PreselectionConfig(
            method=PreselectionMethod.COMBINED,
            top_k=top_k,
            lookback=lookback,
            min_periods=60,
        )
        preselection = Preselection(config)

        # Filter data (common to all)
        if isinstance(returns.index, pd.DatetimeIndex):
            date_mask = returns.index.date < rebalance_date
        else:
            date_mask = returns.index < rebalance_date
        available_returns = returns.loc[date_mask]
        
        # Get lookback window
        lookback_start = max(0, len(available_returns) - config.lookback)
        lookback_returns = available_returns.iloc[lookback_start:]

        # Time factor computation
        start = time.perf_counter()
        momentum = preselection._compute_momentum(lookback_returns)
        low_vol = preselection._compute_low_volatility(lookback_returns)
        momentum_z = preselection._standardize(momentum)
        low_vol_z = preselection._standardize(low_vol)
        combined = 0.5 * momentum_z + 0.5 * low_vol_z
        compute_time = time.perf_counter() - start

        # Time ranking (sorting)
        start = time.perf_counter()
        valid_scores = combined.dropna()
        sorted_scores = valid_scores.sort_values(ascending=False)
        rank_time = time.perf_counter() - start

        # Time selection (top-K with tie-breaking)
        start = time.perf_counter()
        k = min(top_k, len(sorted_scores))
        if k < len(sorted_scores):
            kth_score = sorted_scores.iloc[k - 1]
            candidates = sorted_scores[sorted_scores >= kth_score]
        else:
            candidates = sorted_scores
        
        if len(candidates) > k:
            candidates_df = pd.DataFrame(
                {"score": candidates, "symbol": candidates.index}
            )
            candidates_df = candidates_df.sort_values(
                by=["score", "symbol"], ascending=[False, True]
            )
            selected = candidates_df.head(k)["symbol"].tolist()
        else:
            selected = candidates.index.tolist()
        selected = sorted(selected)
        select_time = time.perf_counter() - start

        total_time = compute_time + rank_time + select_time

        print(f"  Compute factors: {compute_time:.4f}s ({100*compute_time/total_time:.1f}%)")
        print(f"  Rank assets:     {rank_time:.4f}s ({100*rank_time/total_time:.1f}%)")
        print(f"  Select top-K:    {select_time:.4f}s ({100*select_time/total_time:.1f}%)")
        print(f"  Total:           {total_time:.4f}s")

        result = BenchmarkResult(
            scenario="time_breakdown",
            universe_size=universe_size,
            lookback=lookback,
            method="combined",
            execution_time=total_time,
            compute_time=compute_time,
            rank_time=rank_time,
            select_time=select_time,
        )
        self.results.append(result)
        return result

    def benchmark_lookback_impact(
        self,
        universe_size: int = 1000,
        lookback_periods: list[int] | None = None,
        top_k: int = 30,
    ) -> list[BenchmarkResult]:
        """Benchmark impact of lookback period on performance.

        Args:
            universe_size: Number of assets
            lookback_periods: List of lookback periods to test
            top_k: Number of assets to select

        Returns:
            List of benchmark results
        """
        if lookback_periods is None:
            lookback_periods = [30, 63, 126, 252, 504]

        print(f"\n{'='*60}")
        print(f"Lookback Period Impact ({universe_size} assets)")
        print(f"{'='*60}")

        returns = self.data_generator.generate_returns(
            universe_size, num_days=max(lookback_periods) + 100
        )
        rebalance_date = returns.index[-1].date()

        results = []
        for lookback in lookback_periods:
            config = PreselectionConfig(
                method=PreselectionMethod.MOMENTUM,
                top_k=top_k,
                lookback=lookback,
                min_periods=min(30, lookback),
            )
            preselection = Preselection(config)

            start = time.perf_counter()
            selected = preselection.select_assets(returns, rebalance_date)
            elapsed = time.perf_counter() - start

            result = BenchmarkResult(
                scenario=f"lookback_{lookback}",
                universe_size=universe_size,
                lookback=lookback,
                method="momentum",
                execution_time=elapsed,
            )
            results.append(result)

            print(f"  Lookback {lookback:3d}: {elapsed:.4f}s")

        self.results.extend(results)
        return results

    def benchmark_rebalance_dates(
        self,
        universe_size: int = 1000,
        num_rebalances: int = 24,
        lookback: int = 252,
        top_k: int = 30,
    ) -> BenchmarkResult:
        """Benchmark performance with multiple rebalance dates.

        Simulates typical backtest scenario with monthly rebalancing.

        Args:
            universe_size: Number of assets
            num_rebalances: Number of rebalance dates
            lookback: Lookback period
            top_k: Number of assets to select

        Returns:
            Benchmark result
        """
        print(f"\n{'='*60}")
        print(f"Multiple Rebalance Dates ({num_rebalances} rebalances)")
        print(f"{'='*60}")

        # Generate data with extra history
        returns = self.data_generator.generate_returns(
            universe_size, num_days=lookback + num_rebalances * 21 + 100
        )

        # Create rebalance dates with sufficient history for min_periods
        all_dates = returns.index.tolist()
        min_periods = 60
        start_index = max(lookback, min_periods)  # Ensure enough history
        available_dates = len(all_dates) - start_index
        step = available_dates // num_rebalances
        
        # Generate rebalance dates starting after minimum history
        rebalance_dates = [
            all_dates[start_index + i * step].date() 
            for i in range(num_rebalances)
        ]

        config = PreselectionConfig(
            method=PreselectionMethod.MOMENTUM,
            top_k=top_k,
            lookback=lookback,
            min_periods=60,
        )
        preselection = Preselection(config)

        # Time all rebalances
        start = time.perf_counter()
        for rebal_date in rebalance_dates:
            selected = preselection.select_assets(returns, rebal_date)
        total_time = time.perf_counter() - start

        avg_per_rebalance = total_time / num_rebalances

        print(f"  Total time:     {total_time:.4f}s")
        print(f"  Per rebalance:  {avg_per_rebalance:.4f}s")
        print(f"  Rate:           {num_rebalances/total_time:.1f} rebalances/sec")

        result = BenchmarkResult(
            scenario="multiple_rebalances",
            universe_size=universe_size,
            lookback=lookback,
            method="momentum",
            execution_time=total_time,
        )
        self.results.append(result)
        return result

    def profile_detailed(
        self,
        universe_size: int = 1000,
        lookback: int = 252,
        top_k: int = 30,
    ) -> pstats.Stats:
        """Run detailed profiling with cProfile.

        Args:
            universe_size: Number of assets
            lookback: Lookback period
            top_k: Number of assets to select

        Returns:
            Profile statistics
        """
        print(f"\n{'='*60}")
        print(f"Detailed Profiling (cProfile)")
        print(f"{'='*60}")

        returns = self.data_generator.generate_returns(universe_size)
        rebalance_date = returns.index[-1].date()

        config = PreselectionConfig(
            method=PreselectionMethod.COMBINED,
            top_k=top_k,
            lookback=lookback,
            min_periods=60,
        )
        preselection = Preselection(config)

        # Profile the selection
        profiler = cProfile.Profile()
        profiler.enable()

        for _ in range(10):  # Run multiple times for better profiling
            selected = preselection.select_assets(returns, rebalance_date)

        profiler.disable()

        # Print top 20 functions by cumulative time
        s = io.StringIO()
        stats = pstats.Stats(profiler, stream=s).sort_stats("cumulative")
        stats.print_stats(20)
        
        print(s.getvalue())

        return stats

    def print_summary(self) -> None:
        """Print summary of all benchmark results."""
        if not self.results:
            print("\nNo benchmark results to display.")
            return

        print(f"\n{'='*60}")
        print("BENCHMARK SUMMARY")
        print(f"{'='*60}\n")

        # Group by scenario type
        by_universe = [r for r in self.results if "size_" in r.scenario]
        by_lookback = [r for r in self.results if "lookback_" in r.scenario]
        time_breakdown = [r for r in self.results if r.scenario == "time_breakdown"]
        rebalances = [r for r in self.results if r.scenario == "multiple_rebalances"]

        # Universe size scaling
        if by_universe:
            print("Universe Size Scaling:")
            print("-" * 60)
            for method in ["momentum", "low_vol", "combined"]:
                method_results = [r for r in by_universe if r.method == method]
                if method_results:
                    print(f"\n{method.upper()}:")
                    for r in method_results:
                        print(f"  {r.universe_size:5d} assets: {r.execution_time:.4f}s")

        # Lookback impact
        if by_lookback:
            print("\n\nLookback Period Impact:")
            print("-" * 60)
            for r in by_lookback:
                print(f"  Lookback {r.lookback:3d}: {r.execution_time:.4f}s")

        # Time breakdown
        if time_breakdown:
            print("\n\nTime Breakdown:")
            print("-" * 60)
            r = time_breakdown[0]
            if r.compute_time and r.rank_time and r.select_time:
                total = r.execution_time
                print(f"  Compute: {r.compute_time:.4f}s ({100*r.compute_time/total:.1f}%)")
                print(f"  Rank:    {r.rank_time:.4f}s ({100*r.rank_time/total:.1f}%)")
                print(f"  Select:  {r.select_time:.4f}s ({100*r.select_time/total:.1f}%)")

        # Rebalance performance
        if rebalances:
            print("\n\nMultiple Rebalance Performance:")
            print("-" * 60)
            for r in rebalances:
                print(f"  Total time: {r.execution_time:.4f}s")


def main():
    """Run preselection benchmarks."""
    parser = argparse.ArgumentParser(
        description="Benchmark preselection factor computation performance"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all benchmarks (default if no specific benchmark specified)",
    )
    parser.add_argument(
        "--universe-sizes",
        type=int,
        nargs="+",
        default=[100, 250, 500, 1000, 2500],
        help="Universe sizes to benchmark (default: 100 250 500 1000 2500)",
    )
    parser.add_argument(
        "--lookback-periods",
        type=int,
        nargs="+",
        default=[30, 63, 126, 252, 504],
        help="Lookback periods to benchmark (default: 30 63 126 252 504)",
    )
    parser.add_argument(
        "--rebalances",
        type=int,
        default=24,
        help="Number of rebalance dates to test (default: 24)",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=3,
        help="Iterations per benchmark (default: 3)",
    )
    parser.add_argument(
        "--profile-detail",
        action="store_true",
        help="Run detailed profiling with cProfile",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)",
    )

    args = parser.parse_args()

    # If no specific benchmark requested, run all
    run_all = args.all or not args.profile_detail

    print("="*60)
    print("PRESELECTION PERFORMANCE BENCHMARK")
    print("="*60)
    print(f"\nRandom seed: {args.seed}")
    print(f"Iterations per test: {args.iterations}")

    # Initialize benchmark suite
    generator = SyntheticDataGenerator(seed=args.seed)
    benchmark = PreselectionBenchmark(generator)

    # Run benchmarks
    if run_all:
        # Factor computation by universe size
        for method in [PreselectionMethod.MOMENTUM, PreselectionMethod.LOW_VOL, PreselectionMethod.COMBINED]:
            benchmark.benchmark_factor_computation(
                method=method,
                universe_sizes=args.universe_sizes,
                iterations=args.iterations,
            )

        # Time breakdown
        benchmark.benchmark_time_breakdown()

        # Lookback impact
        benchmark.benchmark_lookback_impact(lookback_periods=args.lookback_periods)

        # Multiple rebalances
        benchmark.benchmark_rebalance_dates(num_rebalances=args.rebalances)

    # Detailed profiling
    if args.profile_detail:
        benchmark.profile_detailed()

    # Print summary
    if run_all:
        benchmark.print_summary()

    print(f"\n{'='*60}")
    print("BENCHMARK COMPLETE")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
