# Data Loading Optimization for run_backtest

## Overview

The `run_backtest.py` script has been optimized to significantly reduce memory usage and improve startup time when working with large universes.

## Problem

Previously, the `load_data` function in `scripts/run_backtest.py` would:
1. Load the **entire** prices and returns CSV files into memory
2. Then filter to only the columns needed for the requested universe
3. Ignore the `--start-date` and `--end-date` CLI arguments during data loading

This meant that for a CSV file with 1000 assets, even if you only needed 20 assets for your backtest, pandas would parse all 1000 columns and keep them in memory before filtering.

## Solution

The optimized `load_data` function now:
1. **Validates columns first**: Peeks at CSV headers to check if requested assets exist (fail-fast)
2. **Loads only needed columns**: Uses pandas `usecols` parameter to only parse required asset columns
3. **Filters date range during load**: Applies date range filtering immediately after loading
4. **Provides clear errors**: Reports missing assets with detailed error messages

## Performance Impact

Benchmark results (see `benchmark_data_loading.py`):

| Scenario | Assets (Total/Requested) | Memory Reduction | Time Impact |
|----------|-------------------------|------------------|-------------|
| Small (100/10, 1 year) | 100 total, 10 requested | 60% | Neutral |
| Medium (500/20, 1 year) | 500 total, 20 requested | 60% | Neutral |
| Large (1000/50, 1 year) | 1000 total, 50 requested | 60% | Neutral |
| Large + Long (1000/50, 5 years) | 1000 total, 50 requested | 12% | 8.6% faster |

**Key Findings:**
- **Memory**: Consistent 60% reduction when loading subset of columns
- **Time**: Improvements scale with data size; most beneficial for 10+ MB files
- **Scalability**: Prevents multi-GB DataFrame allocation for wide universes

## Usage

### Automatic (Recommended)

Simply use the existing CLI flags:

```bash
python scripts/run_backtest.py equal_weight \
  --universe-file config/universes.yaml \
  --universe-name my_portfolio \
  --start-date 2020-01-01 \
  --end-date 2023-12-31
```

The optimization is **automatic** - no code changes needed!

### API Changes

The `load_data` function signature has been updated:

**Before:**
```python
def load_data(
    prices_file: Path,
    returns_file: Path,
    assets: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
```

**After:**
```python
def load_data(
    prices_file: Path,
    returns_file: Path,
    assets: list[str],
    start_date: date | None = None,  # NEW
    end_date: date | None = None,    # NEW
) -> tuple[pd.DataFrame, pd.DataFrame]:
```

**Backwards Compatibility:** The new parameters are optional (default `None`), so existing code continues to work without changes.

## Testing

The optimization is covered by 12 comprehensive unit tests in `tests/scripts/test_run_backtest.py`:

- ✅ Column filtering (only requested assets loaded)
- ✅ Date range filtering (start, end, both, neither)
- ✅ Error handling (missing files, missing columns)
- ✅ Empty results (non-overlapping date ranges)
- ✅ Data integrity (values match original data)
- ✅ Performance (1000 asset universe)

Run tests:
```bash
pytest tests/scripts/test_run_backtest.py -v
```

## When to Use

This optimization is most beneficial when:

1. **Wide universes**: CSV files contain 500+ assets
2. **Small selection**: You only need 10-100 assets for your backtest
3. **Long histories**: CSV files span 5-10 years of daily data
4. **Date-limited backtests**: You only need 1-3 years for the backtest period

## Example Scenarios

### Maximum Benefit
```bash
# CSV: 1000 assets × 10 years = ~50 MB
# Universe: 30 assets
# Backtest period: 2020-2023 (3 years)
# Reduction: ~97% memory usage (30/1000 assets × 3/10 years)
```

### Moderate Benefit
```bash
# CSV: 200 assets × 5 years = ~10 MB  
# Universe: 40 assets
# Backtest period: 2021-2023 (2 years)
# Reduction: ~80% memory usage (40/200 assets × 2/5 years)
```

### Minimal Benefit
```bash
# CSV: 50 assets × 1 year = ~2 MB
# Universe: 30 assets
# Backtest period: full year
# Reduction: ~40% memory usage (30/50 assets × 1/1 year)
```

## Implementation Details

The optimization works in three stages:

1. **Header validation** (pandas `nrows=0`):
   - Reads only the CSV header row
   - Validates all requested assets exist
   - Fails fast with clear error message if assets missing

2. **Column filtering** (pandas `usecols`):
   - Constructs list of columns to load: `[index_column, *requested_assets]`
   - Pandas parser only processes specified columns
   - Significantly reduces memory allocation

3. **Date filtering** (boolean indexing):
   - Applies `>= start_date` and `<= end_date` filters
   - Removes rows outside backtest period
   - Further reduces memory footprint

## Benchmark Script

Run the included benchmark to see performance on your system:

```bash
python benchmark_data_loading.py
```

This will:
- Create test data of various sizes
- Compare old vs. new loading approaches
- Report time and memory improvements
- Show summary across different scenarios

## Future Enhancements

Potential further optimizations:
- Chunk-based reading for very large files (>1 GB)
- Parallel CSV parsing for multiple universe backtests
- Compression support for `.csv.gz` files
- Memory-mapped file access for repeated reads

## See Also

- Issue: [Optimize run_backtest data loading for large universes](#)
- Tests: `tests/scripts/test_run_backtest.py`
- Benchmark: `benchmark_data_loading.py`
- Example: `example_optimized_loading.py`
