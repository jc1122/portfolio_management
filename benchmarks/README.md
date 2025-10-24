# Benchmarks

This directory contains performance benchmarks for the portfolio management system.

## Available Benchmarks

### `benchmark_cache_performance.py`

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

### `benchmark_fast_io.py`

Fast I/O benchmarks comparing CSV vs Parquet performance (existing benchmark).

### `test_selection_performance.py`

Asset selector vectorization performance tests (existing benchmark).

## Running Benchmarks

Benchmarks can be run directly as Python scripts:

```bash
# Navigate to repository root
cd /path/to/portfolio_management

# Run cache performance benchmarks
python benchmarks/benchmark_cache_performance.py

# Run fast I/O benchmarks
python benchmarks/benchmark_fast_io.py
```

## Interpreting Results

Benchmark results include:

- **Hit Rate (%):** Percentage of cache hits vs total requests
- **Memory (MB):** Memory usage in megabytes
- **Time (s):** Wall clock time in seconds
- **Speedup (x):** Performance multiplier (uncached_time / cached_time)
- **Break-Even (runs):** Number of runs where caching becomes beneficial

### Example Output Structure

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

## Adding New Benchmarks

To add a new benchmark:

1. Create a new Python script in this directory
2. Follow the naming convention: `benchmark_<feature>.py`
3. Include docstring with description, usage, requirements
4. Output results to `docs/performance/` directory
5. Update this README with benchmark description

## Notes

- Benchmarks generate synthetic data for reproducibility
- Results may vary based on hardware and system load
- Run benchmarks on a quiet system for consistent results
- Some benchmarks may take several minutes to complete
