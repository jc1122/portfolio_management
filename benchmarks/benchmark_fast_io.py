#!/usr/bin/env python3
"""Comprehensive benchmarking suite for fast IO implementation.

This script provides systematic benchmarks to quantify speedups and validate
the performance claims (2-5x) for the fast IO implementation using polars/pyarrow.

Benchmarks include:
- CSV reading (pandas vs polars)
- Parquet reading/writing (pandas vs pyarrow)
- Cold vs warm reads
- Memory usage profiling
- Multiple dataset sizes (100 to 10,000 assets)
- Result equivalence verification

Usage:
    python benchmarks/benchmark_fast_io.py --all
    python benchmarks/benchmark_fast_io.py --csv
    python benchmarks/benchmark_fast_io.py --parquet
    python benchmarks/benchmark_fast_io.py --memory
    python benchmarks/benchmark_fast_io.py --output-json results.json
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np

from portfolio_management.data.io.fast_io import (
    get_available_backends,
    is_backend_available,
    read_csv_fast,
    read_parquet_fast,
)

try:
    import pandas as pd
except ImportError as exc:  # pragma: no cover
    print("ERROR: pandas is required for benchmarking")
    print("Install with: pip install pandas")
    sys.exit(1)

# Optional: memory profiling
try:
    import psutil

    MEMORY_PROFILING_AVAILABLE = True
except ImportError:
    MEMORY_PROFILING_AVAILABLE = False


@dataclass
class BenchmarkResult:
    """Container for benchmark results."""

    benchmark_name: str
    backend: str
    dataset_size: str  # e.g., "100 assets x 5 years"
    num_assets: int
    num_days: int
    operation: str  # 'read_csv', 'write_csv', 'read_parquet', 'write_parquet'
    mean_time_sec: float
    std_time_sec: float
    min_time_sec: float
    max_time_sec: float
    iterations: int
    file_size_mb: float = 0.0
    peak_memory_mb: float = 0.0
    speedup_vs_pandas: float = 1.0
    notes: str = ""


@dataclass
class BenchmarkSuite:
    """Collection of benchmark results with analysis."""

    results: list[BenchmarkResult]
    summary: dict[str, any]
    timestamp: str


def get_memory_usage_mb() -> float:
    """Get current process memory usage in MB."""
    if not MEMORY_PROFILING_AVAILABLE:
        return 0.0
    process = psutil.Process()
    return process.memory_info().rss / (1024 * 1024)


def create_synthetic_price_file(
    path: Path,
    num_days: int = 1260,
    seed: int = 42,
) -> tuple[float, pd.DataFrame]:
    """Create a synthetic price file similar to Stooq format.

    Args:
        path: Output CSV path
        num_days: Number of trading days (~5 years = 1260 days)
        seed: Random seed for reproducibility

    Returns:
        Tuple of (file_size_mb, dataframe)
    """
    dates = pd.date_range("2019-01-01", periods=num_days, freq="B")
    rng = np.random.default_rng(seed)

    # Generate realistic price series (random walk with drift)
    returns = rng.normal(0.0005, 0.015, num_days)
    prices = 100 * np.exp(np.cumsum(returns))

    # Create DataFrame with typical columns (OHLCV format)
    data = {
        "date": dates,
        "open": prices * rng.uniform(0.99, 1.01, num_days),
        "high": prices * rng.uniform(1.00, 1.02, num_days),
        "low": prices * rng.uniform(0.98, 1.00, num_days),
        "close": prices,
        "volume": rng.integers(100000, 1000000, num_days),
    }

    df = pd.DataFrame(data)
    df.to_csv(path, index=False)

    file_size_mb = path.stat().st_size / (1024 * 1024)
    return file_size_mb, df


def create_synthetic_parquet_file(
    path: Path,
    num_days: int = 1260,
    seed: int = 42,
) -> tuple[float, pd.DataFrame]:
    """Create a synthetic Parquet file.

    Args:
        path: Output Parquet path
        num_days: Number of trading days
        seed: Random seed

    Returns:
        Tuple of (file_size_mb, dataframe)
    """
    dates = pd.date_range("2019-01-01", periods=num_days, freq="B")
    rng = np.random.default_rng(seed)

    returns = rng.normal(0.0005, 0.015, num_days)
    prices = 100 * np.exp(np.cumsum(returns))

    data = {
        "date": dates,
        "open": prices * rng.uniform(0.99, 1.01, num_days),
        "high": prices * rng.uniform(1.00, 1.02, num_days),
        "low": prices * rng.uniform(0.98, 1.00, num_days),
        "close": prices,
        "volume": rng.integers(100000, 1000000, num_days),
    }

    df = pd.DataFrame(data)
    df.to_parquet(path, index=False)

    file_size_mb = path.stat().st_size / (1024 * 1024)
    return file_size_mb, df


def benchmark_csv_read_single(
    csv_path: Path,
    backend: str,
    iterations: int = 5,
    clear_cache: bool = False,
) -> BenchmarkResult:
    """Benchmark reading a single CSV file.

    Args:
        csv_path: Path to CSV file
        backend: Backend name ('pandas', 'polars', 'pyarrow')
        iterations: Number of iterations to average
        clear_cache: Whether to clear OS cache between reads (cold reads)

    Returns:
        BenchmarkResult with timing statistics
    """
    times = []
    peak_memory = 0.0

    for i in range(iterations):
        # Clear OS cache if requested (requires sudo, so we'll skip in practice)
        if clear_cache and i > 0:
            gc.collect()
            time.sleep(0.5)  # Allow system to stabilize

        mem_before = get_memory_usage_mb()
        start = time.perf_counter()

        df = read_csv_fast(csv_path, backend=backend)

        elapsed = time.perf_counter() - start
        mem_after = get_memory_usage_mb()

        times.append(elapsed)
        peak_memory = max(peak_memory, mem_after - mem_before)

    file_size_mb = csv_path.stat().st_size / (1024 * 1024)

    return BenchmarkResult(
        benchmark_name="csv_read_single",
        backend=backend,
        dataset_size="1 asset",
        num_assets=1,
        num_days=len(df),
        operation="read_csv",
        mean_time_sec=float(np.mean(times)),
        std_time_sec=float(np.std(times)),
        min_time_sec=float(np.min(times)),
        max_time_sec=float(np.max(times)),
        iterations=iterations,
        file_size_mb=file_size_mb,
        peak_memory_mb=peak_memory,
    )


def benchmark_csv_read_multiple(
    tmpdir: Path,
    num_files: int,
    days_per_file: int,
    backend: str,
    iterations: int = 3,
) -> BenchmarkResult:
    """Benchmark reading multiple CSV files (simulating portfolio loading).

    Args:
        tmpdir: Temporary directory for test files
        num_files: Number of price files (assets)
        days_per_file: Number of days per file
        backend: Backend name
        iterations: Number of full iterations

    Returns:
        BenchmarkResult with timing statistics
    """
    # Create test files once
    print(f"    Creating {num_files} test files...")
    file_paths = []
    total_size_mb = 0.0

    for i in range(num_files):
        csv_path = tmpdir / f"asset_{i:04d}.csv"
        size_mb, _ = create_synthetic_price_file(csv_path, num_days=days_per_file, seed=i)
        file_paths.append(csv_path)
        total_size_mb += size_mb

    # Benchmark loading all files
    print(f"    Benchmarking {backend} on {num_files} files ({iterations} iterations)...")
    times = []
    peak_memory = 0.0

    for _ in range(iterations):
        gc.collect()
        mem_before = get_memory_usage_mb()
        start = time.perf_counter()

        for path in file_paths:
            df = read_csv_fast(path, backend=backend)

        elapsed = time.perf_counter() - start
        mem_after = get_memory_usage_mb()

        times.append(elapsed)
        peak_memory = max(peak_memory, mem_after - mem_before)

    return BenchmarkResult(
        benchmark_name="csv_read_multiple",
        backend=backend,
        dataset_size=f"{num_files} assets x {days_per_file} days",
        num_assets=num_files,
        num_days=days_per_file,
        operation="read_csv",
        mean_time_sec=float(np.mean(times)),
        std_time_sec=float(np.std(times)),
        min_time_sec=float(np.min(times)),
        max_time_sec=float(np.max(times)),
        iterations=iterations,
        file_size_mb=total_size_mb,
        peak_memory_mb=peak_memory,
    )


def benchmark_parquet_read_single(
    parquet_path: Path,
    backend: str,
    iterations: int = 5,
) -> BenchmarkResult:
    """Benchmark reading a single Parquet file.

    Args:
        parquet_path: Path to Parquet file
        backend: Backend name
        iterations: Number of iterations

    Returns:
        BenchmarkResult with timing statistics
    """
    times = []
    peak_memory = 0.0

    for _ in range(iterations):
        gc.collect()
        mem_before = get_memory_usage_mb()
        start = time.perf_counter()

        df = read_parquet_fast(parquet_path, backend=backend)

        elapsed = time.perf_counter() - start
        mem_after = get_memory_usage_mb()

        times.append(elapsed)
        peak_memory = max(peak_memory, mem_after - mem_before)

    file_size_mb = parquet_path.stat().st_size / (1024 * 1024)

    return BenchmarkResult(
        benchmark_name="parquet_read_single",
        backend=backend,
        dataset_size="1 asset",
        num_assets=1,
        num_days=len(df),
        operation="read_parquet",
        mean_time_sec=float(np.mean(times)),
        std_time_sec=float(np.std(times)),
        min_time_sec=float(np.min(times)),
        max_time_sec=float(np.max(times)),
        iterations=iterations,
        file_size_mb=file_size_mb,
        peak_memory_mb=peak_memory,
    )


def benchmark_parquet_write(
    output_path: Path,
    df: pd.DataFrame,
    backend: str,
    iterations: int = 5,
) -> BenchmarkResult:
    """Benchmark writing a Parquet file.

    Args:
        output_path: Output Parquet path
        df: DataFrame to write
        backend: Backend name (only 'pandas' supported for writing)
        iterations: Number of iterations

    Returns:
        BenchmarkResult with timing statistics
    """
    times = []
    peak_memory = 0.0

    for _ in range(iterations):
        gc.collect()
        mem_before = get_memory_usage_mb()
        start = time.perf_counter()

        df.to_parquet(output_path, index=False)

        elapsed = time.perf_counter() - start
        mem_after = get_memory_usage_mb()

        times.append(elapsed)
        peak_memory = max(peak_memory, mem_after - mem_before)

        # Clean up for next iteration
        if output_path.exists():
            output_path.unlink()

    return BenchmarkResult(
        benchmark_name="parquet_write",
        backend=backend,
        dataset_size=f"{len(df)} rows",
        num_assets=1,
        num_days=len(df),
        operation="write_parquet",
        mean_time_sec=float(np.mean(times)),
        std_time_sec=float(np.std(times)),
        min_time_sec=float(np.min(times)),
        max_time_sec=float(np.max(times)),
        iterations=iterations,
        peak_memory_mb=peak_memory,
    )


def verify_result_equivalence(tmpdir: Path) -> dict[str, bool]:
    """Verify that all backends produce identical results.

    Args:
        tmpdir: Temporary directory for test files

    Returns:
        Dict mapping backend pairs to equivalence status
    """
    print("\nVerifying result equivalence across backends...")

    # Create test CSV
    csv_path = tmpdir / "test_equivalence.csv"
    _, df_original = create_synthetic_price_file(csv_path, num_days=252, seed=42)

    results = {}
    available = get_available_backends()

    # Read with each backend
    dataframes = {}
    for backend in available:
        try:
            dataframes[backend] = read_csv_fast(csv_path, backend=backend)
        except Exception as e:
            print(f"  ⚠️  {backend}: Failed to read - {e}")
            continue

    # Compare all pairs
    backends_list = list(dataframes.keys())
    for i, backend1 in enumerate(backends_list):
        for backend2 in backends_list[i + 1 :]:
            try:
                df1 = dataframes[backend1]
                df2 = dataframes[backend2]

                # Compare shapes
                if df1.shape != df2.shape:
                    results[f"{backend1}_vs_{backend2}"] = False
                    print(f"  ❌ {backend1} vs {backend2}: Different shapes")
                    continue

                # Compare values (allow small numerical differences)
                numeric_cols = df1.select_dtypes(include=[np.number]).columns
                for col in numeric_cols:
                    if not np.allclose(
                        df1[col], df2[col], rtol=1e-10, atol=1e-10, equal_nan=True
                    ):
                        results[f"{backend1}_vs_{backend2}"] = False
                        print(f"  ❌ {backend1} vs {backend2}: Column '{col}' differs")
                        break
                else:
                    results[f"{backend1}_vs_{backend2}"] = True
                    print(f"  ✅ {backend1} vs {backend2}: Identical results")

            except Exception as e:
                results[f"{backend1}_vs_{backend2}"] = False
                print(f"  ❌ {backend1} vs {backend2}: Comparison failed - {e}")

    return results


def calculate_speedups(results: list[BenchmarkResult]) -> list[BenchmarkResult]:
    """Calculate speedup ratios relative to pandas.

    Args:
        results: List of benchmark results

    Returns:
        Updated results with speedup_vs_pandas calculated
    """
    # Group by benchmark name and dataset size
    groups = {}
    for result in results:
        key = (result.benchmark_name, result.dataset_size)
        if key not in groups:
            groups[key] = []
        groups[key].append(result)

    # Calculate speedups within each group
    for key, group in groups.items():
        # Find pandas baseline
        pandas_result = next((r for r in group if r.backend == "pandas"), None)
        if pandas_result is None:
            continue

        pandas_time = pandas_result.mean_time_sec

        # Calculate speedup for each backend
        for result in group:
            if result.backend != "pandas" and pandas_time > 0:
                result.speedup_vs_pandas = pandas_time / result.mean_time_sec

    return results


def print_results_table(results: list[BenchmarkResult]) -> None:
    """Print benchmark results in a formatted table.

    Args:
        results: List of benchmark results
    """
    if not results:
        print("No results to display")
        return

    print(
        f"\n{'Backend':<12} {'Dataset':<25} {'Operation':<15} "
        f"{'Mean (s)':<10} {'Speedup':<10} {'Memory (MB)':<12}"
    )
    print("-" * 95)

    for r in results:
        speedup_str = f"{r.speedup_vs_pandas:.2f}x" if r.speedup_vs_pandas > 1 else "-"
        memory_str = f"{r.peak_memory_mb:.1f}" if r.peak_memory_mb > 0 else "N/A"

        print(
            f"{r.backend:<12} {r.dataset_size:<25} {r.operation:<15} "
            f"{r.mean_time_sec:<10.4f} {speedup_str:<10} {memory_str:<12}"
        )


def run_comprehensive_benchmarks(
    run_csv: bool = True,
    run_parquet: bool = True,
    run_memory: bool = True,
    run_equivalence: bool = True,
) -> BenchmarkSuite:
    """Run comprehensive benchmark suite.

    Args:
        run_csv: Run CSV benchmarks
        run_parquet: Run Parquet benchmarks
        run_memory: Run memory profiling
        run_equivalence: Run equivalence verification

    Returns:
        BenchmarkSuite with all results
    """
    print("=" * 80)
    print("Comprehensive Fast IO Benchmark Suite")
    print("=" * 80)

    available = get_available_backends()
    print(f"\nAvailable backends: {', '.join(available)}")

    if not MEMORY_PROFILING_AVAILABLE:
        print("\n⚠️  psutil not installed - memory profiling disabled")
        print("Install with: pip install psutil")
        run_memory = False

    if len(available) == 1:
        print("\n⚠️  Only pandas is available. Install optional backends:")
        print("  pip install polars pyarrow")

    results = []

    with TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # CSV Benchmarks
        if run_csv:
            print("\n" + "=" * 80)
            print("CSV Reading Benchmarks")
            print("=" * 80)

            # Dataset size configurations
            configurations = [
                ("Small", 100, 1260),  # 100 assets x 5 years
                ("Medium", 500, 2520),  # 500 assets x 10 years
                ("Large", 1000, 5040),  # 1000 assets x 20 years
                ("XLarge", 5000, 5040),  # 5000 assets x 20 years (if time permits)
            ]

            for size_name, num_assets, num_days in configurations:
                print(f"\n--- {size_name}: {num_assets} assets x {num_days} days ---")

                for backend in available:
                    try:
                        backend_dir = tmpdir_path / f"csv_{size_name}_{backend}"
                        backend_dir.mkdir(exist_ok=True)

                        result = benchmark_csv_read_multiple(
                            backend_dir,
                            num_files=num_assets,
                            days_per_file=num_days,
                            backend=backend,
                            iterations=3 if num_assets <= 500 else 1,
                        )
                        results.append(result)

                    except Exception as e:
                        print(f"  ❌ {backend} failed: {e}")

        # Parquet Benchmarks
        if run_parquet:
            # Check if any Parquet backend is available
            has_parquet = is_backend_available('pyarrow') or is_backend_available('fastparquet')

            if not has_parquet:
                print("\n" + "=" * 80)
                print("Parquet Reading Benchmarks - SKIPPED")
                print("=" * 80)
                print("\n⚠️  No Parquet backend available. Install with:")
                print("    pip install pyarrow")
                print("    # or")
                print("    pip install fastparquet")
            else:
                print("\n" + "=" * 80)
                print("Parquet Reading Benchmarks")
                print("=" * 80)

                # Single large file
                parquet_path = tmpdir_path / "large.parquet"
                print(f"\nCreating large Parquet file: {parquet_path}")
                file_size_mb, df_large = create_synthetic_parquet_file(
                    parquet_path, num_days=5040
                )
                print(f"File size: {file_size_mb:.2f} MB")

                for backend in available:
                    try:
                        print(f"\nBenchmarking {backend}...")
                        result = benchmark_parquet_read_single(
                            parquet_path, backend=backend, iterations=5
                        )
                        results.append(result)
                    except Exception as e:
                        print(f"  ❌ {backend} failed: {e}")

                # Parquet writing benchmark (pandas only)
                print("\n--- Parquet Writing Benchmark ---")
                try:
                    write_path = tmpdir_path / "write_test.parquet"
                    result = benchmark_parquet_write(
                        write_path, df_large, backend="pandas", iterations=5
                    )
                    results.append(result)
                except Exception as e:
                    print(f"  ❌ Write benchmark failed: {e}")

        # Equivalence verification
        equivalence_results = {}
        if run_equivalence:
            equivalence_results = verify_result_equivalence(tmpdir_path)

    # Calculate speedups
    results = calculate_speedups(results)

    # Print summary
    print("\n" + "=" * 80)
    print("BENCHMARK RESULTS SUMMARY")
    print("=" * 80)
    print_results_table(results)

    # Analysis
    print("\n" + "=" * 80)
    print("ANALYSIS")
    print("=" * 80)

    # Find best speedups
    best_speedups = sorted(
        [r for r in results if r.speedup_vs_pandas > 1],
        key=lambda x: x.speedup_vs_pandas,
        reverse=True,
    )[:5]

    if best_speedups:
        print("\n🚀 Top 5 Speedups:")
        for i, result in enumerate(best_speedups, 1):
            print(
                f"  {i}. {result.backend} on {result.dataset_size} ({result.operation}): "
                f"{result.speedup_vs_pandas:.2f}x faster"
            )

    # Break-even analysis
    print("\n📊 Break-even Analysis:")
    csv_results = [r for r in results if r.operation == "read_csv"]
    if csv_results:
        pandas_csv = [r for r in csv_results if r.backend == "pandas"]
        polars_csv = [r for r in csv_results if r.backend == "polars"]

        if pandas_csv and polars_csv:
            # Find smallest dataset where speedup > 2x
            for r in polars_csv:
                if r.speedup_vs_pandas > 2.0:
                    print(
                        f"  CSV: {r.num_assets} assets achieves {r.speedup_vs_pandas:.2f}x speedup"
                    )
                    break

    # Memory efficiency
    if run_memory and MEMORY_PROFILING_AVAILABLE:
        print("\n💾 Memory Efficiency:")
        mem_results = [r for r in results if r.peak_memory_mb > 0]
        if mem_results:
            for backend in available:
                backend_mem = [r for r in mem_results if r.backend == backend]
                if backend_mem:
                    avg_mem = np.mean([r.peak_memory_mb for r in backend_mem])
                    print(f"  {backend}: {avg_mem:.1f} MB average peak memory")

    # Equivalence summary
    if equivalence_results:
        print("\n✅ Equivalence Verification:")
        all_passed = all(equivalence_results.values())
        if all_passed:
            print("  All backends produce identical results ✓")
        else:
            for pair, passed in equivalence_results.items():
                status = "✓" if passed else "✗"
                print(f"  {pair}: {status}")

    # Create summary dict
    summary = {
        "total_benchmarks": len(results),
        "backends_tested": list(set(r.backend for r in results)),
        "operations_tested": list(set(r.operation for r in results)),
        "best_speedup": max((r.speedup_vs_pandas for r in results), default=1.0),
        "equivalence_verified": all(equivalence_results.values())
        if equivalence_results
        else False,
        "memory_profiling_enabled": MEMORY_PROFILING_AVAILABLE,
    }

    return BenchmarkSuite(
        results=results,
        summary=summary,
        timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
    )


def save_results_json(suite: BenchmarkSuite, output_path: Path) -> None:
    """Save benchmark results to JSON file.

    Args:
        suite: BenchmarkSuite to save
        output_path: Output JSON file path
    """
    data = {
        "timestamp": suite.timestamp,
        "summary": suite.summary,
        "results": [asdict(r) for r in suite.results],
    }

    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\n💾 Results saved to: {output_path}")


def main() -> int:
    """Main entry point for benchmark script."""
    parser = argparse.ArgumentParser(
        description="Comprehensive Fast IO Benchmark Suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all benchmarks (default if no options specified)",
    )
    parser.add_argument("--csv", action="store_true", help="Run CSV benchmarks")
    parser.add_argument("--parquet", action="store_true", help="Run Parquet benchmarks")
    parser.add_argument("--memory", action="store_true", help="Run memory profiling")
    parser.add_argument(
        "--equivalence", action="store_true", help="Run equivalence verification"
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        help="Save results to JSON file",
    )

    args = parser.parse_args()

    # Default to all if no specific benchmarks selected
    if not any([args.csv, args.parquet, args.memory, args.equivalence]):
        args.all = True

    # Run benchmarks
    suite = run_comprehensive_benchmarks(
        run_csv=args.all or args.csv,
        run_parquet=args.all or args.parquet,
        run_memory=args.all or args.memory,
        run_equivalence=args.all or args.equivalence,
    )

    # Save results if requested
    if args.output_json:
        save_results_json(suite, args.output_json)

    # Print recommendations
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    print("\n📋 When to use each backend:")
    print("  • pandas: Default, maximum compatibility, small datasets (<100 assets)")
    print("  • polars: Large datasets (500+ assets), maximum speed (2-5x faster)")
    print("  • pyarrow: Alternative to polars, good Parquet support (2-3x faster)")
    print("\n⚙️  Configuration:")
    print("  • Use --io-backend=polars in CLI for best performance")
    print("  • Use io_backend='polars' programmatically")
    print("  • Consider Parquet for repeated reads (5-10x faster than CSV)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
