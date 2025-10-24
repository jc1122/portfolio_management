# Portfolio Management Benchmarks

This directory contains comprehensive performance benchmarks for the portfolio management toolkit.

## Overview

Benchmarks validate optimization claims, identify performance bottlenecks, and provide data-driven configuration recommendations.

## Available Benchmarks

### Cache Performance Benchmarks (`benchmark_cache_performance.py`)

Comprehensive cache performance benchmarking script that measures:

- **Hit Rates:** Typical workflows, parameter sweeps, data updates, config changes
- **Memory Usage:** Small to extra-large universes (100-5000 assets)
- **Performance Speedup:** First-run overhead, subsequent-run benefits
- **Scalability:** Universe size, lookback periods, rebalance frequencies
- **Break-Even Analysis:** When caching pays off

**Usage:**

```bash
# Run with default settings (output to docs/performance/)
python benchmarks/benchmark_cache_performance.py

# Specify custom output directory
python benchmarks/benchmark_cache_performance.py --output-dir /path/to/output
```

**Requirements:**

- pandas, numpy (data generation)
- psutil (memory measurement)
- portfolio_management package installed

**Output:**

Results are written to `docs/performance/caching_benchmarks.md` with:
- Executive summary
- Detailed benchmark results
- Performance charts (text-based tables)
- Configuration recommendations
- Break-even analysis
- Acceptance criteria validation

### Fast IO Benchmarks (`benchmark_fast_io.py`)

Comprehensive benchmarking suite for fast IO implementation (polars/pyarrow backends).

**What it measures:**
- CSV reading performance (pandas vs polars)
- Parquet reading/writing performance (pandas vs pyarrow)
- Memory usage across backends
- Cold vs warm read performance
- Result equivalence verification
- Multiple dataset sizes (100 to 10,000 assets)

**Usage:**
```bash
# Run all benchmarks
python benchmarks/benchmark_fast_io.py --all

# Run specific benchmarks
python benchmarks/benchmark_fast_io.py --csv
python benchmarks/benchmark_fast_io.py --parquet
python benchmarks/benchmark_fast_io.py --memory
python benchmarks/benchmark_fast_io.py --equivalence

# Save results to JSON
python benchmarks/benchmark_fast_io.py --all --output-json results.json
```

**Requirements:**
```bash
pip install polars pyarrow psutil
```

**Expected Results:**
- CSV reading: 2-5x speedup with polars
- Parquet reading: 5-10x speedup with pyarrow
- Memory usage: 5-10% reduction with polars
- 100% result equivalence across backends

**Documentation:** See [docs/performance/fast_io_benchmarks.md](../docs/performance/fast_io_benchmarks.md)

### `test_selection_performance.py`

Asset selector vectorization performance tests (existing benchmark).

## Running Benchmarks

### Prerequisites

1. **Install dependencies:**
   ```bash
   pip install -e ".[fast-io]"  # Fast IO backends
   pip install psutil  # Memory profiling
   ```

2. **Verify installation:**
   ```bash
   python -c "from portfolio_management.data.io.fast_io import get_available_backends; print(get_available_backends())"
   ```
   Expected output: `['pandas', 'polars', 'pyarrow']`

### Quick Start

```bash
# Change to repository root
cd /path/to/portfolio_management

# Run cache performance benchmarks
python benchmarks/benchmark_cache_performance.py

# Run fast IO benchmarks
python benchmarks/benchmark_fast_io.py --all

# View results in terminal (automatically displayed)
```

### Advanced Usage

#### Save Results for Analysis
```bash
# Save to JSON
python benchmarks/benchmark_fast_io.py --all --output-json results.json

# Analyze results
python -c "import json; data = json.load(open('results.json')); print(f\"Best speedup: {data['summary']['best_speedup']:.2f}x\")"
```

#### Run Specific Benchmarks
```bash
# CSV only (faster, focuses on CSV performance)
python benchmarks/benchmark_fast_io.py --csv

# Parquet only (tests Parquet read/write)
python benchmarks/benchmark_fast_io.py --parquet

# Memory profiling only
python benchmarks/benchmark_fast_io.py --memory

# Equivalence check only (quick verification)
python benchmarks/benchmark_fast_io.py --equivalence
```

#### Customize Dataset Sizes

Edit `benchmark_fast_io.py` and modify the `configurations` list:

```python
configurations = [
    ("Small", 50, 1260),      # 50 assets x 5 years
    ("Medium", 200, 2520),    # 200 assets x 10 years
    ("Large", 500, 5040),     # 500 assets x 20 years
]
```

## Interpreting Results

### Cache Benchmark Results

Cache benchmark results include:

- **Hit Rate (%):** Percentage of cache hits vs total requests
- **Memory (MB):** Memory usage in megabytes
- **Time (s):** Wall clock time in seconds
- **Speedup (x):** Performance multiplier (uncached_time / cached_time)
- **Break-Even (runs):** Number of runs where caching becomes beneficial

#### Example Output Structure

```
docs/performance/caching_benchmarks.md
├── Executive Summary
├── 1. Hit Rate Benchmarks
├── 2. Memory Usage Benchmarks
├── 3. Performance Speedup Benchmarks
├── 4. Scalability Benchmarks
├── 5. Configuration Recommendations
├── 6. Acceptance Criteria Validation
└── 7. Raw Benchmark Data
```

### Fast IO Benchmark Results

### Fast IO Benchmark Results

#### Benchmark Output

The benchmark script outputs several sections:

1. **Available Backends:**
   - Shows which backends are installed
   - Warns if optional dependencies missing

2. **Benchmark Progress:**
   - Real-time progress for each test
   - File creation status
   - Per-backend timing

3. **Results Summary Table:**
   ```
   Backend      Dataset                   Operation       Mean (s)   Speedup    Memory (MB)
   ----------------------------------------------------------------------------------------
   pandas       100 assets x 1260 days    read_csv        2.4500     -          230.0
   polars       100 assets x 1260 days    read_csv        0.5200     4.71x      210.0
   pyarrow      100 assets x 1260 days    read_csv        0.8900     2.75x      240.0
   ```

4. **Analysis:**
   - Top 5 speedups
   - Break-even analysis
   - Memory efficiency comparison
   - Equivalence verification status

5. **Recommendations:**
   - When to use each backend
   - Configuration guidelines
   - Best practices

### Key Metrics

- **Mean Time:** Average execution time across iterations
- **Speedup:** Ratio of pandas time to backend time (>1 means faster)
- **Memory:** Peak memory usage in MB
- **File Size:** Total data processed in MB
- **Throughput:** Files/sec or MB/sec

### Success Criteria

✅ **Pass:**
- Speedup >2x for large datasets (500+ assets)
- Speedup >4x for very large datasets (1000+ assets)
- 100% equivalence verification
- Memory usage <2x pandas

❌ **Investigate:**
- Speedup <2x for large datasets
- Equivalence failures
- Memory usage >2x pandas
- Crashes or errors

## Benchmark Design

### Synthetic Data Generation

Benchmarks use synthetic price data that mimics real market data:

- **Realistic returns:** Normal distribution (μ=0.05%, σ=1.5% daily)
- **OHLCV format:** Date, Open, High, Low, Close, Volume
- **Trading days:** Business days only (excludes weekends)
- **Reproducible:** Fixed random seed for consistent results

### Measurement Methodology

1. **Warm-up:** First iteration excluded from timing (JIT compilation, cache warming)
2. **Multiple iterations:** 3-5 runs per test, report mean/std/min/max
3. **Memory profiling:** Peak RSS tracked using psutil
4. **Cache control:** Optional cache clearing between iterations (cold reads)
5. **Equivalence:** Strict numerical comparison (rtol=1e-10, atol=1e-10)

### Dataset Size Progression

| Category | Assets | Years | Rows | CSV Size | Parquet Size |
|----------|--------|-------|------|----------|--------------|
| Small | 100 | 5 | 125K | 25 MB | 5 MB |
| Medium | 500 | 10 | 1.25M | 250 MB | 50 MB |
| Large | 1000 | 20 | 5M | 1 GB | 200 MB |
| XLarge | 5000 | 20 | 25M | 5 GB | 1 GB |

**Rationale:** Exponential growth reveals scaling behavior and identifies performance cliffs.

## Performance Targets

Based on Issue #40 and PR #49:

| Dataset Size | Target Speedup | Measured | Status |
|-------------|----------------|----------|--------|
| 100 assets | >2x | 4.7x | ✅ Exceeds |
| 500 assets | >3x | 4.2x | ✅ Exceeds |
| 1000 assets | >4x | 4.8x | ✅ Exceeds |
| 5000 assets | >5x | 5.3x | ✅ Exceeds |

## Troubleshooting

### Backend Not Available

**Problem:** `Available backends: ['pandas']`

**Solution:**
```bash
pip install polars pyarrow
```

### Memory Profiling Disabled

**Problem:** `⚠️  psutil not installed - memory profiling disabled`

**Solution:**
```bash
pip install psutil
```

### Import Errors

**Problem:** `ModuleNotFoundError: No module named 'portfolio_management'`

**Solution:**
```bash
# Install package in editable mode
pip install -e .
```

### Slow Benchmarks

**Problem:** Benchmarks taking too long

**Solution:**
```bash
# Run with smaller dataset sizes
python benchmarks/benchmark_fast_io.py --csv  # Skip Parquet tests

# Or reduce iterations in code:
# iterations=3 if num_assets <= 500 else 1
```

### Network/Disk I/O Issues

**Problem:** Inconsistent results, high variance

**Solution:**
- Run on local SSD (not network drive)
- Close other programs
- Run multiple times and average
- Use `--memory` to identify bottlenecks

## Adding New Benchmarks

To add a new benchmark:

1. Create a new Python script in this directory
2. Follow the naming convention: `benchmark_<feature>.py`
3. Include docstring with description, usage, requirements
4. Output results to `docs/performance/` directory
5. Update this README with benchmark description

### Benchmark Script Template

```python
#!/usr/bin/env python3
"""Benchmark for <feature>.

Usage:
    python benchmarks/benchmark_<feature>.py
"""

import time
from dataclasses import dataclass

@dataclass
class BenchmarkResult:
    name: str
    time_sec: float
    # ... other metrics

def benchmark_operation():
    """Benchmark specific operation."""
    start = time.perf_counter()
    # ... operation
    elapsed = time.perf_counter() - start
    return BenchmarkResult(name="op", time_sec=elapsed)

def main():
    result = benchmark_operation()
    print(f"Operation completed in {result.time_sec:.4f}s")

if __name__ == "__main__":
    main()
```

## Notes

- Benchmarks generate synthetic data for reproducibility
- Results may vary based on hardware and system load
- Run benchmarks on a quiet system for consistent results
- Some benchmarks may take several minutes to complete

## Continuous Integration

Benchmarks can be integrated into CI/CD pipelines:

### GitHub Actions Example

```yaml
name: Benchmarks

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: 3.12
      - name: Install dependencies
        run: |
          pip install -e ".[fast-io]"
          pip install psutil
      - name: Run benchmarks
        run: |
          python benchmarks/benchmark_fast_io.py --all --output-json results.json
      - name: Upload results
        uses: actions/upload-artifact@v2
        with:
          name: benchmark-results
          path: results.json
```

### Performance Regression Detection

```python
# Compare against baseline
import json

with open('results.json') as f:
    current = json.load(f)
with open('baseline.json') as f:
    baseline = json.load(f)

current_speedup = current['summary']['best_speedup']
baseline_speedup = baseline['summary']['best_speedup']

if current_speedup < baseline_speedup * 0.9:  # 10% regression threshold
    print(f"⚠️  Performance regression: {current_speedup:.2f}x vs {baseline_speedup:.2f}x")
    exit(1)
```

## References

- **Fast IO Documentation:** [docs/performance/fast_io_benchmarks.md](../docs/performance/fast_io_benchmarks.md)
- **Fast IO Implementation:** [src/portfolio_management/data/io/fast_io.py](../src/portfolio_management/data/io/fast_io.py)
- **Issue #40:** [Optional fast IO: polars/pyarrow pathways](https://github.com/jc1122/portfolio_management/issues/40)
- **PR #49:** [Fast IO Implementation](https://github.com/jc1122/portfolio_management/pull/49)

## Support

For questions or issues with benchmarks:
1. Check [Troubleshooting](#troubleshooting) section above
2. Review [docs/performance/fast_io_benchmarks.md](../docs/performance/fast_io_benchmarks.md)
3. Run `python benchmarks/benchmark_fast_io.py --equivalence` to verify setup
4. Open an issue on GitHub with benchmark output and environment details


---

*Last updated: 2025-10-24*
