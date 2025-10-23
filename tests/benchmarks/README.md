# Performance Benchmarks

This directory contains benchmark scripts for measuring performance improvements across the portfolio management toolkit.

## Fast IO Benchmarks

### benchmark_fast_io.py

Benchmarks the performance of optional fast IO backends (polars, pyarrow) compared to pandas for CSV reading operations.

**Purpose**: Demonstrate the speedup potential of using polars or pyarrow for loading large datasets.

**Requirements**:
```bash
# Install optional backends to see full comparison
pip install polars pyarrow

# Or install all at once
pip install -e ".[fast-io]"
```

**Usage**:
```bash
python tests/benchmarks/benchmark_fast_io.py
```

**What it tests**:
1. **Single Large File**: 5 years of daily data (~1260 trading days, ~3 MB CSV)
2. **Multiple Files (100 assets)**: Simulates loading a medium-sized portfolio
3. **Large Universe (500 assets)**: Simulates loading the long_history_1000 universe

**Expected Results**:
- Polars: ~4-5x faster than pandas
- PyArrow: ~2-3x faster than pandas
- Most significant gains for large files and multiple file operations

**Sample Output**:
```
================================================================================
Fast IO Backend Benchmark
================================================================================

Available backends: pandas, polars, pyarrow

================================================================================
Benchmark 1: Single Large File (5 years daily data)
================================================================================
Creating test file: /tmp/tmpdir/large.csv
File size: 2.89 MB

Backend         Mean (s)     Std (s)      Min (s)      Max (s)     
-----------------------------------------------------------------
pandas          0.0245       0.0012       0.0232       0.0261      
polars          0.0052       0.0003       0.0049       0.0056      
pyarrow         0.0089       0.0005       0.0084       0.0095      

Speedup vs pandas:
  polars          4.71x faster
  pyarrow         2.75x faster
```

## Running Benchmarks

### Prerequisites

Benchmarks can run with just pandas installed, but to see the full comparison you need the optional backends:

```bash
pip install polars pyarrow
```

### Single Benchmark

```bash
# Run fast IO benchmark
python tests/benchmarks/benchmark_fast_io.py
```

### All Benchmarks

```bash
# Run all benchmark scripts in this directory
for script in tests/benchmarks/*.py; do
    echo "Running $script..."
    python "$script"
done
```

## Benchmark Best Practices

1. **Warm-up**: First run may include module import time; run multiple iterations
2. **System Load**: Close other applications to get consistent results
3. **Disk Cache**: Results may vary based on OS disk caching; restart system for cold measurements
4. **Comparison**: Compare relative speedups, not absolute times (hardware-dependent)

## Adding New Benchmarks

To add a new benchmark:

1. Create a new file: `benchmark_<feature>.py`
2. Use the existing benchmarks as templates
3. Include:
   - Clear description of what's being measured
   - Synthetic data generation (don't rely on production data)
   - Multiple iterations to average results
   - Comparison table showing speedups
   - Summary with recommendations

4. Update this README with:
   - Purpose of the benchmark
   - How to run it
   - Expected results
   - Interpretation guidance

## Interpreting Results

### Speedup Factors

- **< 1.5x**: Minor improvement, might not be worth switching
- **1.5-2x**: Moderate improvement, consider for large workloads
- **2-5x**: Significant improvement, recommended for production
- **> 5x**: Major improvement, strongly recommended

### When Speedups Matter

Fast IO provides greatest benefit for:
- Large files (> 1 MB per file)
- Many files (> 100 files in a batch operation)
- Long histories (> 3 years of daily data)
- Repeated operations (backtests with many rebalances)

### When Speedups Don't Matter

Fast IO may not help for:
- Small files (< 100 KB)
- Few files (< 10 files)
- Short histories (< 1 year)
- One-time operations (occasional data loading)

In these cases, the overhead of converting between formats may negate benefits.

## Troubleshooting

### "Only pandas is available"

**Solution**: Install optional backends:
```bash
pip install polars pyarrow
```

### Unexpected Results

If benchmarks show unexpected results:

1. Check system load (close other applications)
2. Clear disk cache (restart system)
3. Run multiple times and average
4. Check Python version (should be 3.10+)
5. Verify package versions:
   ```bash
   pip list | grep -E "(pandas|polars|pyarrow)"
   ```

### Performance Regression

If a new version shows slower performance:

1. Check if the dataset changed
2. Verify package versions haven't regressed
3. Run benchmarks on multiple systems
4. Compare against previous benchmark results
5. File an issue with benchmark output

## References

- [Fast IO Documentation](../../docs/fast_io.md)
- [Polars Performance Guide](https://pola-rs.github.io/polars/user-guide/performance/)
- [PyArrow Performance Tips](https://arrow.apache.org/docs/python/performance.html)
