# Performance Profiling Guide

This guide explains how to profile and measure performance in the portfolio management system.

## Overview

Profiling helps identify performance bottlenecks by measuring:
- **Time**: Where the code spends most time
- **Memory**: Which operations use most memory
- **Calls**: How many times functions are called
- **I/O**: Disk and network operations

## Quick Start

### Basic Time Profiling

```python
import time

start = time.perf_counter()
result = expensive_operation()
duration = time.perf_counter() - start

print(f"Operation took {duration:.3f} seconds")
```

### Context Manager for Timing

```python
from contextlib import contextmanager
import time

@contextmanager
def timer(operation_name: str):
    """Time a block of code."""
    start = time.perf_counter()
    yield
    duration = time.perf_counter() - start
    print(f"{operation_name}: {duration:.3f}s")

# Usage
with timer("Preselection"):
    result = preselection.select_assets(returns, date)
```

## Python Profiling Tools

### cProfile - Function-Level Profiling

**Purpose**: Identify which functions consume most time

```python
import cProfile
import pstats

# Profile a function
profiler = cProfile.Profile()
profiler.enable()

result = run_backtest(config, strategy, prices, returns)

profiler.disable()

# Print statistics
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)  # Top 20 functions
```

**Output Example**:
```
   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
     120    2.451    0.020   18.432    0.154 preselection.py:45(select_assets)
     120    1.837    0.015    6.892    0.057 strategies.py:78(compute_weights)
     240    0.892    0.004    0.892    0.004 {method 'cov' of 'pandas.core.frame.DataFrame'}
```

### line_profiler - Line-Level Profiling

**Purpose**: Identify slow lines within a function

**Installation**:
```bash
pip install line_profiler
```

**Usage**:
```python
from line_profiler import LineProfiler

def profile_function():
    profiler = LineProfiler()
    profiler.add_function(select_assets)
    profiler.enable()
    
    result = select_assets(config, returns, date)
    
    profiler.disable()
    profiler.print_stats()

profile_function()
```

**Output Example**:
```
Line #      Hits         Time  Per Hit   % Time  Line Contents
    45       120        245.1     2.0      1.3      def select_assets(config, returns, date):
    46       120       1834.2    15.3     10.0          factor_scores = compute_factors(returns)
    47       120      15234.8   126.  9     83.2          ranked = rank_by_factors(factor_scores)
    48       120       1015.3     8.5      5.5          return select_top_k(ranked, config.top_k)
```

### memory_profiler - Memory Usage Profiling

**Purpose**: Track memory allocation and identify leaks

**Installation**:
```bash
pip install memory_profiler
```

**Usage**:
```python
from memory_profiler import profile

@profile
def process_large_dataset():
    # Load data
    prices = pd.read_csv("large_file.csv")
    
    # Process
    returns = calculate_returns(prices)
    
    # Analyze
    result = run_analysis(returns)
    
    return result

process_large_dataset()
```

**Output Example**:
```
Line #    Mem usage    Increment   Line Contents
     5     45.2 MiB     45.2 MiB   @profile
     6                             def process_large_dataset():
     7     85.7 MiB     40.5 MiB       prices = pd.read_csv("large_file.csv")
     9    125.3 MiB     39.6 MiB       returns = calculate_returns(prices)
    11    127.8 MiB      2.5 MiB       result = run_analysis(returns)
    13    127.8 MiB      0.0 MiB       return result
```

### tracemalloc - Memory Tracking

**Purpose**: Track Python memory allocations

```python
import tracemalloc

# Start tracking
tracemalloc.start()

# Run code to profile
result = expensive_memory_operation()

# Get statistics
current, peak = tracemalloc.get_traced_memory()
tracemalloc.stop()

print(f"Current memory: {current / 1024 / 1024:.1f} MB")
print(f"Peak memory: {peak / 1024 / 1024:.1f} MB")

# Get top allocations
snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')

for stat in top_stats[:10]:
    print(stat)
```

## Benchmarking Best Practices

### 1. Warm-up Runs

Always include warm-up runs to account for caching:

```python
import time

def benchmark_with_warmup(func, n_warmup=1, n_runs=5):
    """Benchmark function with warm-up."""
    # Warm-up
    for _ in range(n_warmup):
        func()
    
    # Measure
    times = []
    for _ in range(n_runs):
        start = time.perf_counter()
        func()
        times.append(time.perf_counter() - start)
    
    return {
        "mean": sum(times) / len(times),
        "min": min(times),
        "max": max(times),
        "std": (sum((t - sum(times)/len(times))**2 for t in times) / len(times)) ** 0.5
    }
```

### 2. Statistical Significance

Run multiple iterations and report statistics:

```python
import statistics

def benchmark_statistical(func, n_runs=10):
    """Benchmark with statistical analysis."""
    times = []
    for i in range(n_runs):
        start = time.perf_counter()
        func()
        times.append(time.perf_counter() - start)
    
    mean = statistics.mean(times)
    stdev = statistics.stdev(times) if len(times) > 1 else 0
    
    # Remove outliers (>2 std dev)
    filtered = [t for t in times if abs(t - mean) < 2 * stdev]
    
    return {
        "mean": statistics.mean(filtered),
        "median": statistics.median(filtered),
        "stdev": statistics.stdev(filtered) if len(filtered) > 1 else 0,
        "min": min(filtered),
        "max": max(filtered),
        "n_outliers": len(times) - len(filtered)
    }
```

### 3. Reproducibility

Control random seeds for reproducible benchmarks:

```python
import numpy as np
import random

def reproducible_benchmark():
    """Benchmark with controlled randomness."""
    # Set seeds
    np.random.seed(42)
    random.seed(42)
    
    # Generate test data
    data = np.random.randn(1000, 100)
    
    # Benchmark
    start = time.perf_counter()
    result = process_data(data)
    duration = time.perf_counter() - start
    
    return duration
```

## Profiling Specific Components

### Backtest Engine

```python
import cProfile
from portfolio_management.backtesting import BacktestEngine

def profile_backtest():
    """Profile backtest engine."""
    profiler = cProfile.Profile()
    
    # Setup
    config = BacktestConfig(...)
    strategy = EqualWeightStrategy()
    prices, returns = load_data()
    
    # Profile
    profiler.enable()
    engine = BacktestEngine(config, strategy, prices, returns)
    result = engine.run()
    profiler.disable()
    
    # Analyze
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(30)
```

### Preselection

```python
from memory_profiler import profile

@profile
def profile_preselection():
    """Profile preselection memory usage."""
    config = PreselectionConfig(top_k=50, lookback=252)
    returns = create_test_returns(n_assets=1000, n_periods=2000)
    
    preselection = Preselection(config)
    result = preselection.select_assets(returns, date.today())
    
    return result
```

### Data Loading

```python
import time
import psutil
import os

def profile_data_loading(file_path):
    """Profile data loading with system metrics."""
    process = psutil.Process(os.getpid())
    
    # Before loading
    mem_before = process.memory_info().rss / 1024 / 1024
    
    # Load data
    start = time.perf_counter()
    data = pd.read_csv(file_path)
    load_time = time.perf_counter() - start
    
    # After loading
    mem_after = process.memory_info().rss / 1024 / 1024
    
    print(f"Load time: {load_time:.3f}s")
    print(f"Memory increase: {mem_after - mem_before:.1f} MB")
    print(f"Data shape: {data.shape}")
    print(f"MB per 1000 rows: {(mem_after - mem_before) / len(data) * 1000:.2f}")
```

## Automated Profiling Scripts

### Benchmark Suite

Create reusable benchmark scripts:

```python
# benchmarks/benchmark_preselection.py
import time
import pandas as pd
import numpy as np

def create_test_data(n_assets, n_periods):
    """Create test data for benchmarking."""
    dates = pd.date_range("2020-01-01", periods=n_periods, freq="D")
    assets = [f"ASSET_{i:03d}" for i in range(n_assets)]
    data = np.random.randn(n_periods, n_assets) * 0.01
    return pd.DataFrame(data, index=dates, columns=assets)

def benchmark_preselection_scalability():
    """Benchmark preselection across universe sizes."""
    results = []
    
    for n_assets in [100, 250, 500, 1000, 2500, 5000]:
        print(f"Benchmarking {n_assets} assets...")
        
        # Create data
        returns = create_test_data(n_assets, 1000)
        config = PreselectionConfig(top_k=min(50, n_assets // 2))
        preselection = Preselection(config)
        
        # Warm-up
        preselection.select_assets(returns, returns.index[-1].date())
        
        # Measure
        times = []
        for _ in range(5):
            start = time.perf_counter()
            preselection.select_assets(returns, returns.index[-1].date())
            times.append(time.perf_counter() - start)
        
        results.append({
            "assets": n_assets,
            "time_ms": sum(times) / len(times) * 1000,
            "time_per_asset_us": sum(times) / len(times) / n_assets * 1e6
        })
    
    # Print results
    print("\nResults:")
    print(f"{'Assets':>8} {'Time (ms)':>12} {'µs/asset':>12}")
    print("-" * 35)
    for r in results:
        print(f"{r['assets']:>8} {r['time_ms']:>12.2f} {r['time_per_asset_us']:>12.2f}")

if __name__ == "__main__":
    benchmark_preselection_scalability()
```

### Performance Regression Tests

Add performance tests to catch regressions:

```python
# tests/performance/test_preselection_performance.py
import pytest
import time

@pytest.mark.performance
def test_preselection_performance_1000_assets():
    """Verify preselection completes within time limit for 1000 assets."""
    returns = create_test_returns(n_assets=1000, n_periods=1000)
    config = PreselectionConfig(top_k=50)
    preselection = Preselection(config)
    
    start = time.perf_counter()
    result = preselection.select_assets(returns, returns.index[-1].date())
    duration = time.perf_counter() - start
    
    # Should complete in <100ms
    assert duration < 0.100, f"Preselection took {duration*1000:.1f}ms (expected <100ms)"
    assert len(result) == 50
```

## Visualization

### Plotting Performance Results

```python
import matplotlib.pyplot as plt

def plot_scalability(results):
    """Plot scalability results."""
    assets = [r["assets"] for r in results]
    times = [r["time_ms"] for r in results]
    
    plt.figure(figsize=(10, 6))
    plt.plot(assets, times, marker='o', linewidth=2, markersize=8)
    plt.xlabel("Number of Assets", fontsize=12)
    plt.ylabel("Time (ms)", fontsize=12)
    plt.title("Preselection Scalability", fontsize=14)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig("scalability.png", dpi=150)
    plt.close()
```

### Performance Dashboard

Create comprehensive performance reports:

```python
import json

def generate_performance_report(results, output_file="performance_report.json"):
    """Generate JSON performance report."""
    report = {
        "timestamp": datetime.now().isoformat(),
        "system": {
            "python": sys.version,
            "platform": platform.platform(),
            "cpu_count": os.cpu_count()
        },
        "results": results
    }
    
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"Report saved to {output_file}")
```

## Continuous Performance Monitoring

### CI Integration

Add performance tests to CI pipeline:

```yaml
# .github/workflows/performance.yml
name: Performance Tests

on:
  schedule:
    - cron: '0 0 * * 0'  # Weekly
  workflow_dispatch:

jobs:
  performance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Run performance benchmarks
        run: python benchmarks/run_all.py
      
      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: performance-results
          path: benchmarks/results/
```

### Performance History Tracking

Track performance over time:

```python
import sqlite3
from datetime import datetime

def record_performance(metric_name, value, commit_hash):
    """Record performance metric to database."""
    conn = sqlite3.connect('performance_history.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS metrics (
            timestamp TEXT,
            commit_hash TEXT,
            metric_name TEXT,
            value REAL
        )
    ''')
    
    cursor.execute(
        'INSERT INTO metrics VALUES (?, ?, ?, ?)',
        (datetime.now().isoformat(), commit_hash, metric_name, value)
    )
    
    conn.commit()
    conn.close()
```

## Profiling Checklist

Before optimizing, complete this checklist:

- [ ] Profile to identify bottleneck (don't guess!)
- [ ] Measure baseline performance (time + memory)
- [ ] Create reproducible benchmark
- [ ] Document test conditions (data size, config)
- [ ] Run multiple iterations for statistical validity
- [ ] Record results before optimization
- [ ] Implement optimization
- [ ] Verify correctness (results unchanged)
- [ ] Measure improved performance
- [ ] Document improvement and trade-offs
- [ ] Add performance regression test

## Common Performance Patterns

### Pattern: Vectorization

**Before**:
```python
# Slow: Row-wise iteration
result = df.apply(lambda row: expensive_function(row), axis=1)
```

**After**:
```python
# Fast: Vectorized operation
result = vectorized_function(df)
```

### Pattern: Caching

**Before**:
```python
# Recompute every time
def get_factors(returns, date):
    return expensive_computation(returns, date)
```

**After**:
```python
# Cache results
from functools import lru_cache

@lru_cache(maxsize=128)
def get_factors(returns_hash, date):
    returns = unhash(returns_hash)
    return expensive_computation(returns, date)
```

### Pattern: Streaming

**Before**:
```python
# Load entire file
df = pd.read_csv("huge_file.csv")
result = process(df)
```

**After**:
```python
# Stream in chunks
result = initialize_result()
for chunk in pd.read_csv("huge_file.csv", chunksize=10000):
    result = update_result(result, process_chunk(chunk))
```

## Related Documentation

- [Optimization Guide](optimization.md) - Optimization techniques
- [Benchmarks](benchmarks.md) - Benchmark results
- [Performance README](README.md) - Performance documentation index
- [Best Practices](../best_practices.md) - Development guidelines
