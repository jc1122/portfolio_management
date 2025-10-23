"""Performance benchmarks for AssetSelector filtering pipeline.

This module provides benchmarks to measure the performance of the AssetSelector
filtering operations before and after vectorization optimizations.
"""

import time
from typing import Any

import numpy as np
import pandas as pd
import pytest

from portfolio_management.assets.selection import AssetSelector, FilterCriteria


def generate_large_match_report(n_rows: int = 10000, seed: int = 42) -> pd.DataFrame:
    """Generate a large synthetic match report for benchmarking.

    Args:
        n_rows: Number of rows to generate.
        seed: Random seed for reproducibility.

    Returns:
        DataFrame with columns matching the tradeable_matches.csv format.

    """
    rng = np.random.default_rng(seed)

    # Define value pools for categorical columns
    markets = ["UK", "US", "DE", "FR", "JP", "CA", "AU", "CH", "NL", "IT"]
    regions = ["Europe", "North America", "Asia", "Oceania"]
    currencies = ["GBP", "USD", "EUR", "JPY", "CAD", "AUD", "CHF"]
    categories = ["ETF", "Stock", "Bond", "REIT", "Commodity"]
    data_statuses = ["ok", "warning", "empty"]
    severities = ["low", "moderate", "high"]

    # Generate base data
    symbols = [f"SYM{i:05d}.{rng.choice(markets)}" for i in range(n_rows)]
    isins = [f"XX{i:010d}" for i in range(n_rows)]
    names = [f"Test Asset {i}" for i in range(n_rows)]

    # Generate date ranges (ensuring min_history_days variation)
    # 70% have good history (>252 days), 30% have short history
    price_starts = []
    price_ends = []
    price_rows_list = []

    base_end = pd.Timestamp("2025-01-01")
    for i in range(n_rows):
        if rng.random() < 0.7:
            # Good history: 252-1260 days
            days_back = rng.integers(252, 1260)
            rows = rng.integers(int(days_back * 0.8), days_back)
        else:
            # Short history: 50-250 days
            days_back = rng.integers(50, 250)
            rows = rng.integers(int(days_back * 0.7), days_back)

        start_date = base_end - pd.Timedelta(days=days_back)
        price_starts.append(start_date.strftime("%Y-%m-%d"))
        price_ends.append(base_end.strftime("%Y-%m-%d"))
        price_rows_list.append(rows)

    # Generate data_flags with zero_volume_severity
    # 60% have no severity, 40% have severity
    data_flags = []
    for i in range(n_rows):
        if rng.random() < 0.6:
            data_flags.append("")
        else:
            severity = rng.choice(severities)
            volume_count = rng.integers(1, 100)
            ratio = rng.random() * 0.1
            flags = f"zero_volume={volume_count};zero_volume_ratio={ratio:.3f};zero_volume_severity={severity}"
            data_flags.append(flags)

    # Create DataFrame
    df = pd.DataFrame(
        {
            "symbol": symbols,
            "isin": isins,
            "name": names,
            "market": rng.choice(markets, size=n_rows),
            "region": rng.choice(regions, size=n_rows),
            "currency": rng.choice(currencies, size=n_rows),
            "category": rng.choice(categories, size=n_rows),
            "price_start": price_starts,
            "price_end": price_ends,
            "price_rows": price_rows_list,
            "data_status": rng.choice(data_statuses, size=n_rows, p=[0.7, 0.25, 0.05]),
            "data_flags": data_flags,
            "stooq_path": [
                f"d_{m.lower()}_txt/data/daily/{m.lower()}/{s.lower()}.txt"
                for s, m in zip(symbols, rng.choice(markets, size=n_rows))
            ],
            "resolved_currency": rng.choice(currencies, size=n_rows),
            "currency_status": rng.choice(
                ["matched", "resolved", "unresolved"],
                size=n_rows,
                p=[0.8, 0.15, 0.05],
            ),
        },
    )

    return df


def benchmark_filter_operation(
    df: pd.DataFrame,
    criteria: FilterCriteria,
    operation_name: str,
    n_iterations: int = 10,
) -> dict[str, Any]:
    """Benchmark a single filtering operation.

    Args:
        df: Input DataFrame.
        criteria: FilterCriteria to apply.
        operation_name: Name of the operation being benchmarked.
        n_iterations: Number of iterations to average over.

    Returns:
        Dictionary with timing statistics.

    """
    selector = AssetSelector()

    times = []
    for _ in range(n_iterations):
        start = time.perf_counter()
        result = selector.select_assets(df, criteria)
        elapsed = time.perf_counter() - start
        times.append(elapsed)

    return {
        "operation": operation_name,
        "n_rows_input": len(df),
        "n_rows_output": len(result),
        "n_iterations": n_iterations,
        "mean_time": np.mean(times),
        "std_time": np.std(times),
        "min_time": np.min(times),
        "max_time": np.max(times),
    }


class TestSelectionPerformance:
    """Performance benchmarks for AssetSelector operations."""

    @pytest.fixture
    def small_dataset(self) -> pd.DataFrame:
        """Generate a small dataset (1000 rows) for quick tests."""
        return generate_large_match_report(n_rows=1000)

    @pytest.fixture
    def large_dataset(self) -> pd.DataFrame:
        """Generate a large dataset (10000 rows) for realistic benchmarks."""
        return generate_large_match_report(n_rows=10000)

    @pytest.fixture
    def basic_criteria(self) -> FilterCriteria:
        """Create basic filtering criteria."""
        return FilterCriteria(
            data_status=["ok"],
            min_history_days=252,
            min_price_rows=200,
        )

    @pytest.fixture
    def complex_criteria(self) -> FilterCriteria:
        """Create complex filtering criteria with all filters."""
        return FilterCriteria(
            data_status=["ok", "warning"],
            min_history_days=504,
            min_price_rows=400,
            zero_volume_severity=["low", "moderate"],
            markets=["UK", "US", "DE"],
            currencies=["GBP", "USD", "EUR"],
            categories=["ETF", "Stock"],
        )

    def test_benchmark_basic_filtering_small(
        self,
        small_dataset: pd.DataFrame,
        basic_criteria: FilterCriteria,
    ) -> None:
        """Benchmark basic filtering on small dataset (1k rows)."""
        result = benchmark_filter_operation(
            small_dataset,
            basic_criteria,
            "basic_filtering_1k",
            n_iterations=20,
        )

        print(f"\n{'='*60}")
        print(f"Benchmark: {result['operation']}")
        print(f"Input rows: {result['n_rows_input']}")
        print(f"Output rows: {result['n_rows_output']}")
        print(f"Mean time: {result['mean_time']*1000:.2f}ms")
        print(f"Std time: {result['std_time']*1000:.2f}ms")
        print(f"Min time: {result['min_time']*1000:.2f}ms")
        print(f"Max time: {result['max_time']*1000:.2f}ms")
        print(f"{'='*60}")

        # Assert reasonable performance (adjust threshold as needed)
        assert (
            result["mean_time"] < 0.5
        ), "Basic filtering on 1k rows should complete in <500ms"

    def test_benchmark_basic_filtering_large(
        self,
        large_dataset: pd.DataFrame,
        basic_criteria: FilterCriteria,
    ) -> None:
        """Benchmark basic filtering on large dataset (10k rows)."""
        result = benchmark_filter_operation(
            large_dataset,
            basic_criteria,
            "basic_filtering_10k",
            n_iterations=10,
        )

        print(f"\n{'='*60}")
        print(f"Benchmark: {result['operation']}")
        print(f"Input rows: {result['n_rows_input']}")
        print(f"Output rows: {result['n_rows_output']}")
        print(f"Mean time: {result['mean_time']*1000:.2f}ms")
        print(f"Std time: {result['std_time']*1000:.2f}ms")
        print(f"Min time: {result['min_time']*1000:.2f}ms")
        print(f"Max time: {result['max_time']*1000:.2f}ms")
        print(f"{'='*60}")

        # Store baseline for comparison after vectorization
        # Current implementation uses .apply(), so expect slower performance

    def test_benchmark_complex_filtering_large(
        self,
        large_dataset: pd.DataFrame,
        complex_criteria: FilterCriteria,
    ) -> None:
        """Benchmark complex filtering (all filters) on large dataset (10k rows)."""
        result = benchmark_filter_operation(
            large_dataset,
            complex_criteria,
            "complex_filtering_10k",
            n_iterations=10,
        )

        print(f"\n{'='*60}")
        print(f"Benchmark: {result['operation']}")
        print(f"Input rows: {result['n_rows_input']}")
        print(f"Output rows: {result['n_rows_output']}")
        print(f"Mean time: {result['mean_time']*1000:.2f}ms")
        print(f"Std time: {result['std_time']*1000:.2f}ms")
        print(f"Min time: {result['min_time']*1000:.2f}ms")
        print(f"Max time: {result['max_time']*1000:.2f}ms")
        print(f"{'='*60}")

    def test_benchmark_severity_filtering(
        self,
        large_dataset: pd.DataFrame,
    ) -> None:
        """Benchmark severity filtering specifically (most complex apply operation)."""
        criteria = FilterCriteria(
            data_status=["ok", "warning"],
            zero_volume_severity=["low", "moderate", "high"],
        )

        result = benchmark_filter_operation(
            large_dataset,
            criteria,
            "severity_filtering_10k",
            n_iterations=10,
        )

        print(f"\n{'='*60}")
        print(f"Benchmark: {result['operation']}")
        print(f"Input rows: {result['n_rows_input']}")
        print(f"Output rows: {result['n_rows_output']}")
        print(f"Mean time: {result['mean_time']*1000:.2f}ms")
        print(f"Std time: {result['std_time']*1000:.2f}ms")
        print(f"Min time: {result['min_time']*1000:.2f}ms")
        print(f"Max time: {result['max_time']*1000:.2f}ms")
        print(f"{'='*60}")

    def test_benchmark_allowlist_blocklist(
        self,
        large_dataset: pd.DataFrame,
    ) -> None:
        """Benchmark allow/blocklist filtering."""
        # Create allowlist with ~10% of symbols
        all_symbols = large_dataset["symbol"].unique()
        allowlist_size = len(all_symbols) // 10
        allowlist = set(all_symbols[:allowlist_size])

        # Create blocklist with ~5% of symbols (different from allowlist)
        blocklist_size = len(all_symbols) // 20
        blocklist = set(all_symbols[-blocklist_size:])

        criteria = FilterCriteria(
            data_status=["ok", "warning"],
            allowlist=allowlist,
            blocklist=blocklist,
        )

        result = benchmark_filter_operation(
            large_dataset,
            criteria,
            "allowlist_blocklist_10k",
            n_iterations=10,
        )

        print(f"\n{'='*60}")
        print(f"Benchmark: {result['operation']}")
        print(f"Input rows: {result['n_rows_input']}")
        print(f"Output rows: {result['n_rows_output']}")
        print(f"Allowlist size: {len(allowlist)}")
        print(f"Blocklist size: {len(blocklist)}")
        print(f"Mean time: {result['mean_time']*1000:.2f}ms")
        print(f"Std time: {result['std_time']*1000:.2f}ms")
        print(f"Min time: {result['min_time']*1000:.2f}ms")
        print(f"Max time: {result['max_time']*1000:.2f}ms")
        print(f"{'='*60}")
