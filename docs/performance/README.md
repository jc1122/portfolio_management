# Performance Documentation

This directory contains comprehensive performance documentation for the portfolio management system.

## Quick Links

- [Optimization Guide](optimization.md) - Comprehensive optimization techniques and strategies
- [Benchmarks](benchmarks.md) - Detailed performance benchmark results
- [Profiling Guide](profiling.md) - How to profile and measure performance
- [Existing Benchmarks](#existing-benchmarks) - Links to specific benchmark documents

## Overview

The portfolio management system is optimized for:
- **Large universes**: Efficiently handle 1000+ assets
- **Long histories**: Process 20+ years of daily data
- **Frequent rebalancing**: Support monthly/quarterly rebalancing
- **Memory efficiency**: Operate within typical system constraints

## Key Performance Improvements

### Summary Table

| Optimization | Component | Improvement | Impact |
|--------------|-----------|-------------|---------|
| Lookback slicing | Backtest Engine | O(n²) → O(rebalances) | 95% fewer operations |
| Column filtering | Data Loading | 60% memory reduction | Faster loading |
| Streaming | Diagnostics | 44% memory reduction | 19.7 GB saved (70k files) |
| Vectorization | Asset Selection | 45-206x speedup | Sub-millisecond per asset |
| Factor caching | Preselection | 80-100% hit rate | 88% time savings |

### Performance Highlights

- **Preselection**: < 100ms for 1000 assets with 252-day lookback
- **Asset Selection**: 189k assets/second processing speed
- **Backtest**: 5.2 seconds for 5-year monthly backtest with 100 assets
- **Memory**: < 200MB for 5000-asset universe preselection

## Documentation Structure

### [Optimization Guide](optimization.md)

Comprehensive guide covering all optimization techniques:

1. **Backtest Engine Optimization**: Reduced from O(n²) to O(rebalances)
2. **Data Loading Optimization**: Column and date filtering strategies
3. **Streaming Performance**: Chunk-based processing for large files
4. **Asset Selection Vectorization**: Replace row-wise operations with vectors
5. **Preselection Profiling**: Performance characteristics and scalability
6. **Caching Strategies**: Factor and price loader caching
7. **Best Practices**: General optimization guidelines

### [Benchmarks](benchmarks.md)

Detailed benchmark results for all components:

- **Asset Selection**: Vectorization improvements (45-206x speedup)
- **Preselection**: Scalability by universe size and lookback period
- **Backtest Engine**: Performance by strategy and rebalancing frequency
- **Data Loading**: Column and date filtering performance
- **Streaming**: Memory usage comparison across file sizes
- **Caching**: Hit rates and time savings
- **System-Level**: End-to-end backtest performance breakdown

### [Profiling Guide](profiling.md)

How to profile and measure performance:

- **Python Profiling Tools**: cProfile, line_profiler, memory_profiler
- **Benchmarking Best Practices**: Warm-up, statistical significance, reproducibility
- **Component-Specific Profiling**: Backtest, preselection, data loading
- **Automated Profiling**: Benchmark suites and regression tests
- **Visualization**: Plotting and reporting results
- **CI Integration**: Continuous performance monitoring

## Existing Benchmarks

### Detailed Component Benchmarks

- [Asset Selector Vectorization](assetselector_vectorization.md) - 45-206x speedup details
- [Preselection Profiling](preselection_profiling.md) - Scalability analysis
- [Caching Benchmarks](caching_benchmarks.md) - Cache performance and hit rates
- [Fast I/O Benchmarks](fast_io_benchmarks.md) - Data loading optimizations

## Quick Reference

### Performance Targets

| Component | Target | Typical |
|-----------|--------|---------|
| Preselection (1000 assets) | < 100ms | 68ms |
| Asset Selection (10k rows) | < 100ms | 53ms |
| Backtest (5y, monthly) | < 10s | 5.2s |
| Data Load (1000 assets, 5y) | < 100ms | 68ms |

### When to Optimize

**Optimize when**:
- Operation takes > 1 second for typical use
- Memory usage > 1 GB for typical dataset
- Users report performance issues
- Profiling shows clear bottleneck

**Profile first, then optimize**:
1. Measure baseline performance
2. Identify bottleneck via profiling
3. Implement targeted optimization
4. Verify correctness maintained
5. Measure improvement
6. Add performance regression test

## Common Optimization Patterns

### 1. Vectorization

Replace row-wise operations with vectorized pandas/numpy operations:

```python
# Slow
result = df.apply(lambda row: process(row), axis=1)

# Fast
result = vectorized_process(df)
```

### 2. Column Filtering

Load only needed columns to reduce memory:

```python
# Load subset of columns
usecols = ["Date"] + needed_assets
df = pd.read_csv(file_path, usecols=usecols)
```

### 3. Streaming

Process large files in chunks:

```python
# Process incrementally
for chunk in pd.read_csv(file_path, chunksize=10000):
    result = process_chunk(chunk)
```

### 4. Caching

Cache expensive computations:

```python
# Enable caching
cache = FactorCache(Path(".cache"), enabled=True)
preselection = Preselection(config, cache=cache)
```

### 5. Conditional Slicing

Only create expensive slices when needed:

```python
# Only slice when rebalancing
if should_rebalance:
    lookback_data = data.iloc[:current_index + 1]
```

## Performance Testing

### Running Benchmarks

```bash
# Run all benchmarks
python benchmarks/run_all.py

# Run specific benchmark
python benchmarks/benchmark_preselection.py

# Run with profiling
python -m cProfile -o output.prof benchmarks/benchmark_preselection.py
python -m pstats output.prof
```

### Performance Regression Tests

```bash
# Run performance tests
pytest tests/performance/ -m performance -v

# Skip slow tests during development
pytest tests/ -m "not slow and not performance"
```

## Monitoring Performance

### Key Metrics to Track

1. **Execution Time**: Total runtime for operations
2. **Memory Usage**: Peak and average memory consumption
3. **Throughput**: Operations per second
4. **Scalability**: Performance vs. data size
5. **Cache Hit Rate**: Percentage of cache hits

### Performance History

Track performance over time:
- Baseline measurements before optimization
- After optimization improvements
- Regression test results over commits

## Optimization Workflow

1. **Identify Problem**: User reports or profiling reveals slowness
2. **Measure Baseline**: Benchmark current performance
3. **Profile Code**: Identify specific bottleneck
4. **Design Solution**: Plan optimization approach
5. **Implement**: Make targeted changes
6. **Verify Correctness**: Ensure results unchanged
7. **Measure Improvement**: Benchmark optimized version
8. **Document**: Record changes and results
9. **Test**: Add regression test to prevent backsliding

## Configuration Recommendations

### For Small Universes (< 100 assets)

```python
# Simple configuration
config = PreselectionConfig(top_k=30, lookback=252)
preselection = Preselection(config)  # No caching needed
```

### For Medium Universes (100-1000 assets)

```python
# Enable caching for better performance
cache = FactorCache(Path(".cache/factors"), enabled=True)
config = PreselectionConfig(top_k=50, lookback=252)
preselection = Preselection(config, cache=cache)
```

### For Large Universes (> 1000 assets)

```python
# Full optimization
cache = FactorCache(Path(".cache/factors"), enabled=True)
config = PreselectionConfig(
    top_k=100,
    lookback=252,
    method=PreselectionMethod.MOMENTUM  # Faster than COMBINED
)
preselection = Preselection(config, cache=cache)

# Load only needed columns
prices, returns = load_data(
    prices_file,
    returns_file,
    assets=universe_assets,  # Subset of total
    start_date=start,
    end_date=end
)
```

## Troubleshooting Performance Issues

### Slow Backtests

**Check**:
1. Is caching enabled?
2. Is rebalancing frequency appropriate?
3. Is universe size too large?
4. Are you loading full dataset when subset needed?

**Solutions**: See [Troubleshooting Guide](../troubleshooting.md#performance-issues)

### High Memory Usage

**Check**:
1. Are you loading full CSV files?
2. Is price loader cache unbounded?
3. Are you creating unnecessary data copies?

**Solutions**: See [Optimization Guide](optimization.md#memory-management)

### Slow Data Loading

**Check**:
1. Loading all columns or just needed ones?
2. Filtering date range during load?
3. File size appropriate for memory?

**Solutions**: See [Data Loading Optimization](optimization.md#data-loading-optimization)

## Related Documentation

- [Troubleshooting Guide](../troubleshooting.md) - Debugging performance issues
- [Best Practices](../best_practices.md) - General development guidelines
- [Caching Reliability](../caching_reliability.md) - Cache behavior and guarantees
- [Testing Guide](../testing/README.md) - Performance testing strategies

## Contributing

When adding new performance optimizations:

1. **Document baseline**: Record performance before optimization
2. **Create benchmarks**: Add repeatable benchmark scripts
3. **Add regression tests**: Prevent performance backsliding
4. **Update docs**: Document changes in this directory
5. **Share results**: Add benchmark results to [benchmarks.md](benchmarks.md)

## Further Reading

- [Python Performance Tips](https://wiki.python.org/moin/PythonSpeed/PerformanceTips)
- [Pandas Performance](https://pandas.pydata.org/docs/user_guide/enhancingperf.html)
- [NumPy Performance](https://numpy.org/doc/stable/user/basics.performance.html)
- [Memory Profiling in Python](https://pypi.org/project/memory-profiler/)
