# Performance Optimization Guide

This comprehensive guide covers all performance optimizations and techniques used in the portfolio management system.

## Table of Contents

1. [Overview](#overview)
2. [Backtest Engine Optimization](#backtest-engine-optimization)
3. [Data Loading Optimization](#data-loading-optimization)
4. [Streaming Performance](#streaming-performance)
5. [Asset Selection Vectorization](#asset-selection-vectorization)
6. [Preselection Profiling](#preselection-profiling)
7. [Caching Strategies](#caching-strategies)
8. [Best Practices](#best-practices)

---

## Overview

### Performance Philosophy

The portfolio management system is optimized for:
- **Large universes**: Handle 1000+ assets efficiently
- **Long histories**: Process 20+ years of daily data
- **Frequent rebalancing**: Support monthly/quarterly rebalancing
- **Reasonable memory**: Operate within typical system constraints

### Key Optimizations

| Optimization | Impact | Complexity |
|--------------|--------|------------|
| Backtest lookback slicing | O(n²) → O(rebalances) | Low |
| Data loading column filtering | 60% memory reduction | Low |
| Streaming diagnostics | 44% memory reduction | Medium |
| Asset selector vectorization | 45-206x speedup | Medium |
| Factor caching | 80-100% hit rate | Medium |

---

## Backtest Engine Optimization

### Problem: Quadratic Lookback Slicing

The original implementation created full-history DataFrame slices on every trading day:

```python
# Original code - O(n²) complexity
for i in range(len(period_prices)):
    # ... portfolio value calculation ...
    
    if not self.rebalance_events and has_min_history:
        lookback_returns = period_returns.iloc[: i + 1]  # Slice every day
        lookback_prices = period_prices.iloc[: i + 1]    # Slice every day
        self._rebalance(...)
    
    if has_min_history and self._should_rebalance_scheduled(date):
        lookback_returns = period_returns.iloc[: i + 1]  # Slice every day
        lookback_prices = period_prices.iloc[: i + 1]    # Slice every day
        self._rebalance(...)
```

### Solution: Conditional Slicing

The optimized version only creates slices when actually rebalancing:

```python
# Optimized code - O(rebalances) complexity
for i in range(len(period_prices)):
    # ... portfolio value calculation ...
    
    should_rebalance_forced = not self.rebalance_events and has_min_history
    should_rebalance_scheduled = has_min_history and self._should_rebalance_scheduled(date)
    
    if should_rebalance_forced or should_rebalance_scheduled:
        # Only create slices when needed
        lookback_returns = period_returns.iloc[: i + 1]
        lookback_prices = period_prices.iloc[: i + 1]
        
        trigger = RebalanceTrigger.FORCED if should_rebalance_forced else RebalanceTrigger.SCHEDULED
        self._rebalance(date, lookback_returns, lookback_prices, trigger)
```

### Performance Results

**Dataset**: 10-year daily data (2,520 days), 50 assets

| Rebalance Frequency | Runtime (s) | Rebalances | Slice Operations Saved |
|---------------------|-------------|------------|------------------------|
| Monthly             | 2.40        | 116        | ~2,404 (95%)           |
| Quarterly           | 1.82        | 39         | ~2,481 (98%)           |
| Weekly              | 4.22        | 504        | ~2,016 (80%)           |

**Key Benefits**:
- Runtime scales linearly with rebalances, not total days
- Memory usage stable regardless of backtest length
- No behavioral changes - results identical

### When to Apply

This optimization is most beneficial for:
- Long backtests (5+ years)
- Lower rebalancing frequencies (monthly/quarterly)
- Large universes (100+ assets)

---

## Data Loading Optimization

### Problem: Loading Entire Datasets

Previously, `load_data()` would:
1. Load the **entire** prices and returns CSV files into memory
2. Then filter to only the columns needed for the requested universe
3. Ignore the `--start-date` and `--end-date` CLI arguments during loading

For a CSV with 1000 assets, even if you only needed 20 assets, pandas would parse all 1000 columns.

### Solution: Selective Loading

The optimized `load_data()` function now:

```python
def load_data(
    prices_file: Path,
    returns_file: Path,
    assets: list[str],
    start_date: date | None = None,
    end_date: date | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load price and return data with column and date filtering.
    
    Args:
        prices_file: Path to prices CSV
        returns_file: Path to returns CSV
        assets: List of asset symbols to load
        start_date: Optional start date for filtering
        end_date: Optional end date for filtering
    
    Returns:
        Tuple of (prices, returns) DataFrames
    """
    # 1. Validate columns first (peek at headers)
    prices_header = pd.read_csv(prices_file, nrows=0)
    missing = set(assets) - set(prices_header.columns)
    if missing:
        raise ValueError(f"Missing assets in prices file: {missing}")
    
    # 2. Load only needed columns
    usecols = ["Date"] + assets  # Index column + requested assets
    prices = pd.read_csv(prices_file, usecols=usecols, parse_dates=["Date"], index_col="Date")
    returns = pd.read_csv(returns_file, usecols=usecols, parse_dates=["Date"], index_col="Date")
    
    # 3. Filter date range
    if start_date:
        prices = prices[prices.index >= pd.Timestamp(start_date)]
        returns = returns[returns.index >= pd.Timestamp(start_date)]
    if end_date:
        prices = prices[prices.index <= pd.Timestamp(end_date)]
        returns = returns[returns.index <= pd.Timestamp(end_date)]
    
    return prices, returns
```

### Performance Results

**Benchmark**: Various universe sizes with 1-year data

| Scenario | Assets (Total/Requested) | Memory Reduction | Time Impact |
|----------|-------------------------|------------------|-------------|
| Small (100/10, 1 year) | 100 total, 10 requested | 60% | Neutral |
| Medium (500/20, 1 year) | 500 total, 20 requested | 60% | Neutral |
| Large (1000/50, 1 year) | 1000 total, 50 requested | 60% | Neutral |
| Large + Long (1000/50, 5 years) | 1000 total, 50 requested | 12% | 8.6% faster |

**Key Benefits**:
- Consistent 60% memory reduction when loading subset of columns
- Time improvements scale with data size
- Prevents multi-GB DataFrame allocation for wide universes

### When to Apply

Most beneficial when:
- CSV files contain 500+ assets
- You only need 10-100 assets for backtest
- CSV files span 5-10 years of daily data
- Running date-limited backtests (1-3 years)

**Example Scenarios**:

```python
# Maximum benefit scenario
# CSV: 1000 assets × 10 years = ~50 MB
# Universe: 30 assets
# Backtest: 2020-2023 (3 years)
# Reduction: ~97% memory (30/1000 assets × 3/10 years)

# Moderate benefit
# CSV: 200 assets × 5 years = ~10 MB
# Universe: 40 assets
# Backtest: 2021-2023 (2 years)
# Reduction: ~80% memory (40/200 assets × 2/5 years)
```

---

## Streaming Performance

### Problem: Loading Full Files for Diagnostics

The original `summarize_price_file()` loaded each complete Stooq TXT file into a pandas DataFrame before computing diagnostics. With 70,000+ files:

- **Memory usage**: ~40-45 GB peak
- **Processing time**: ~3 hours for full corpus
- **I/O overhead**: Loading all 9 columns when only 3 needed

### Solution: Streaming Approach

The new `_stream_stooq_file_for_diagnostics()` function:

```python
def _stream_stooq_file_for_diagnostics(
    file_path: Path,
    chunk_size: int = 10000
) -> DiagnosticResult:
    """Stream Stooq file for diagnostics without full load.
    
    Args:
        file_path: Path to Stooq TXT file
        chunk_size: Number of rows to process at once
    
    Returns:
        DiagnosticResult with quality metrics
    """
    # 1. Chunked reading
    usecols = ["<DATE>", "<CLOSE>", "<VOL>"]  # Only needed columns
    
    # Initialize accumulators
    total_rows = 0
    zero_volume_count = 0
    dates = []
    
    # 2. Process chunks incrementally
    for chunk in pd.read_csv(file_path, usecols=usecols, chunksize=chunk_size):
        # Process this chunk
        total_rows += len(chunk)
        zero_volume_count += (chunk["<VOL>"] == 0).sum()
        dates.extend(chunk["<DATE>"].tolist())
        
        # Chunk is discarded after processing
    
    # 3. Finalize statistics
    return DiagnosticResult(
        total_rows=total_rows,
        zero_volume_count=zero_volume_count,
        date_range=(min(dates), max(dates))
    )
```

### Key Features

1. **Chunked reading**: Process 10,000-row chunks using pandas' `chunksize` parameter
2. **Column filtering**: Only load 3 required columns (date, close, volume) instead of 9
3. **Incremental statistics**: Accumulate metrics across chunks without materialization
4. **Memory efficiency**: Each chunk is processed and discarded before loading next

### Performance Results

**Test Environment**: 36 synthetic Stooq files (~13,000 lines each, ~450 KB)

| Metric | Old (Full DataFrame) | New (Streaming) | Improvement |
|--------|---------------------|-----------------|-------------|
| **Peak Memory** | 23.76 MB | 13.38 MB | **43.7%** reduction |
| **Total Time** | 5.469 sec | 5.949 sec | 8.8% slower (acceptable) |
| **Per File** | 151.93 ms | 165.25 ms | Trade memory for speed |

**Extrapolation to 70,000 Files**:

| Metric | Old Approach | New Approach | Savings |
|--------|-------------|--------------|---------|
| **Peak Memory** | 45.1 GB | 25.4 GB | **19.7 GB** |
| **Processing Time** | 177 minutes | 193 minutes | -15.5 minutes |

### When to Apply

Use streaming approach when:
- Processing large batches of files (>100 files)
- Memory-constrained environments
- Production pipelines with 70k+ files
- Parallel processing with high concurrency

### Memory Breakdown

**Old approach per file**:
- DataFrame storage: ~660 KB (all columns)
- Processing overhead: ~50 KB
- Total: ~710 KB per file

**New approach per file**:
- Chunk buffer: ~130 KB (3 columns, 10k rows)
- Accumulator state: ~10 KB
- Total: ~140 KB per file
- **Reduction: 80%** per-file memory footprint

---

## Asset Selection Vectorization

### Problem: Row-wise Operations

The AssetSelector filtering pipeline used row-wise `.apply()` and `.iterrows()` operations:

```python
# Original - Slow row-wise operations
def check_severity(row: pd.Series[str]) -> bool:
    severity = self._parse_severity(row["data_flags"])
    return severity in severity_list

severity_mask = df_status.apply(check_severity, axis=1)  # Row-by-row iteration
```

### Solution: Vectorized Operations

Replace with pure pandas vector operations:

```python
# Optimized - Vectorized string operations
@staticmethod
def _parse_severity_vectorized(data_flags_series: pd.Series) -> pd.Series:
    """Extract severity using vectorized regex."""
    flags = data_flags_series.fillna("").astype(str)
    severity = flags.str.extract(r"zero_volume_severity=([^;]+)", expand=False)
    severity = severity.str.strip()
    severity = severity.replace("", None)
    return severity

# In _filter_by_data_quality
severity_series = self._parse_severity_vectorized(df_status["data_flags"])
severity_mask = severity_series.isin(severity_list)  # Vectorized comparison
```

### Optimization Categories

#### 1. Severity Filtering

**Before**: `.apply()` with string parsing
**After**: `.str.extract()` with regex

**Impact**: Uses pandas string operations instead of Python-level loop

#### 2. History Calculation

**Before**: `.apply()` with date arithmetic
**After**: `pd.to_datetime()` + `.dt.days`

```python
# Vectorized history calculation
start_dates = pd.to_datetime(df_status["price_start"])
end_dates = pd.to_datetime(df_status["price_end"])
history_days = (end_dates - start_dates).dt.days
history_mask = history_days >= min_history
```

#### 3. Allow/Blocklist Filtering

**Before**: `.apply()` with list membership check
**After**: `.isin()` boolean mask

```python
# Vectorized list filtering
if self.allow_list:
    allow_mask = df_status.index.isin(self.allow_list)
    df_status = df_status[allow_mask]

if self.block_list:
    block_mask = ~df_status.index.isin(self.block_list)
    df_status = df_status[block_mask]
```

#### 4. Dataclass Conversion

**Before**: `.iterrows()` with object construction
**After**: `.to_dict("records")` batch conversion

```python
# Vectorized dataclass construction
records = df_status.to_dict("records")
assets = [
    AssetInfo(
        symbol=record["symbol"],
        classification=record["classification"],
        # ... other fields
    )
    for record in records
]
```

### Performance Results

**Dataset**: 10,000 row selection DataFrame

| Scenario | Before (ms) | After (ms) | Speedup |
|----------|-------------|------------|---------|
| **Basic filtering** | 3871 | 52.77 | **73x** |
| **Complex filtering** | 1389 | 17.70 | **78x** |
| **Severity filtering** | 2171 | 41.88 | **52x** |
| **Allow/blocklist** | 4989 | 24.17 | **206x** |

**Key Benefits**:
- 45-206x speedup across scenarios
- Linear O(n) scaling maintained
- Zero regressions in functionality
- All 76 existing tests pass

---

## Preselection Profiling

### Performance Characteristics

**Key Findings**:
- ✅ Linear O(n) scaling with universe size
- ✅ Excellent performance: <0.1s for 1000 assets
- ✅ Memory efficient: <200MB for 5000 assets
- ✅ Factor computation is 70-80% of total time
- ✅ No significant bottlenecks requiring optimization

### Scalability by Universe Size

**Benchmark**: Momentum factor computation, 252-day lookback

| Universe Size | Time (ms) | Memory (MB) | Time/Asset (µs) |
|---------------|-----------|-------------|-----------------|
| 100           | 8.2       | 12          | 82              |
| 250           | 18.5      | 25          | 74              |
| 500           | 35.1      | 45          | 70              |
| 1000          | 68.3      | 85          | 68              |
| 2500          | 165.2     | 195         | 66              |
| 5000          | 327.8     | 380         | 66              |

**Observations**:
- Perfect linear scaling (constant time per asset)
- Memory scales linearly with data size
- Sub-millisecond per-asset performance

### Method Comparison

**Dataset**: 1000 assets, 252-day lookback

| Method | Time (ms) | Memory (MB) | Overhead vs Momentum |
|--------|-----------|-------------|----------------------|
| **Momentum** | 68.3 | 85 | - (baseline) |
| **Low Volatility** | 71.2 | 87 | +4% |
| **Combined** | 79.5 | 92 | +16% |

**Key Insight**: Combined factor method adds <20% overhead

### Lookback Period Impact

**Dataset**: 1000 assets, momentum method

| Lookback (days) | Time (ms) | Memory (MB) | Impact |
|-----------------|-----------|-------------|--------|
| 30              | 65.1      | 78          | Baseline |
| 63              | 66.8      | 82          | +2.6% |
| 126             | 67.9      | 85          | +4.3% |
| 252             | 68.3      | 85          | +4.9% |
| 504             | 71.2      | 92          | +9.4% |

**Key Insight**: Lookback period has minimal impact (<10% even at 2 years)

### Multiple Rebalancing

**Scenario**: 24 monthly rebalances over 2 years, 1000 assets

| Metric | Value |
|--------|-------|
| Total Time | 1.64 seconds |
| Time per Rebalance | 68.3 ms |
| Memory Peak | 85 MB |
| Throughput | 14.6 rebalances/sec |

**Key Insight**: Highly efficient for typical backtesting workflows

### Recommendations

Based on profiling results:

1. **Universe Size**: Safe to use with up to 5000 assets without caching
2. **Lookback Period**: Use any period up to 504 days with negligible impact
3. **Method Choice**: Combined factor adds acceptable <20% overhead
4. **Caching**: Consider for:
   - Multiple backtests with overlapping data
   - Universes >2500 assets
   - Real-time or interactive applications

---

## Caching Strategies

### Factor Caching

**Purpose**: Avoid redundant factor computations across rebalances

**Implementation**:
```python
from pathlib import Path
from portfolio_management.caching import FactorCache

# Create cache
cache = FactorCache(Path(".cache/factors"), enabled=True)

# Use with preselection
preselection = Preselection(config, cache=cache)
```

**Cache Key**: `(start_date, end_date, asset_list, config_hash)`

**Performance**:
- First run: 0% hits (cache empty)
- Second run (same config): 80-100% hits
- Different config: Varies based on overlap

### PriceLoader Bounded Cache

**Purpose**: Prevent unbounded memory growth during long CLI runs

**Implementation**:
```python
from portfolio_management.analytics.returns import PriceLoader

# Bounded cache (default: 1000 entries)
loader = PriceLoader(cache_size=1000)

# Disable caching
loader_no_cache = PriceLoader(cache_size=0)

# Clear cache
loader.clear_cache()

# Check cache info
info = loader.cache_info()
print(f"Hits: {info['hits']}, Misses: {info['misses']}")
```

**Memory Impact**:
- Before: Unbounded (could grow to thousands of entries)
- After: Bounded to 1000 entries (LRU eviction)
- Typical savings: **70-90% memory reduction** for wide-universe workflows

---

## Best Practices

### General Guidelines

1. **Profile first**: Measure before optimizing
2. **Target bottlenecks**: Focus on the slowest parts
3. **Maintain correctness**: Verify results match after optimization
4. **Document trade-offs**: Note any compromises made

### Memory Management

1. **Use streaming for large files**: Process incrementally when possible
2. **Filter data early**: Load only needed columns and rows
3. **Clear caches periodically**: Prevent unbounded growth
4. **Monitor peak usage**: Track memory in production

### Code Optimization

1. **Vectorize operations**: Use pandas/numpy operations over Python loops
2. **Avoid row-wise operations**: `.apply(axis=1)` and `.iterrows()` are slow
3. **Use appropriate data types**: Smaller dtypes reduce memory
4. **Minimize copies**: Use views and in-place operations when safe

### Caching Strategy

1. **Cache expensive computations**: Factor calculations, covariance matrices
2. **Use LRU eviction**: For bounded caches
3. **Invalidate on change**: Detect data/config changes
4. **Monitor hit rates**: Aim for >50% on repeated operations

### Benchmarking

1. **Use realistic data sizes**: Test with production-scale data
2. **Measure multiple runs**: Account for variance
3. **Test edge cases**: Small and large extremes
4. **Document results**: Record before/after metrics

### When to Optimize

**Optimize when**:
- Operation takes >1 second for typical use
- Memory usage >1 GB for typical dataset
- Users complain about performance
- Profiling shows clear bottleneck

**Don't optimize when**:
- Operation is fast enough (<100ms)
- Used infrequently (one-time setup)
- Complexity cost exceeds benefit
- No clear bottleneck identified

---

## Related Documentation

- [Benchmarks](benchmarks.md) - Detailed benchmark results
- [Profiling](profiling.md) - Profiling techniques and tools
- [Performance README](README.md) - Performance documentation index
- [Caching Reliability](../caching_reliability.md) - Cache behavior and guarantees
- [Best Practices](../best_practices.md) - General development guidelines
