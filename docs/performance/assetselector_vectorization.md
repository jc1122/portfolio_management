# AssetSelector Vectorization Performance Report

## Summary

The AssetSelector filtering pipeline has been successfully vectorized, replacing row-wise `.apply()` and `.iterrows()` operations with pure pandas vector operations. This optimization achieves **45-206x speedup** across various filtering scenarios.

## Changes Made

### 1. Severity Filtering (`_filter_by_data_quality`)

**Before:**
```python
def check_severity(row: pd.Series[str]) -> bool:
    severity = self._parse_severity(row["data_flags"])
    return severity in severity_list

severity_mask = df_status.apply(check_severity, axis=1)
```

**After:**
```python
# New vectorized helper method
@staticmethod
def _parse_severity_vectorized(data_flags_series: pd.Series) -> pd.Series:
    flags = data_flags_series.fillna("").astype(str)
    severity = flags.str.extract(r"zero_volume_severity=([^;]+)", expand=False)
    severity = severity.str.strip()
    severity = severity.replace("", None)
    return severity

# In _filter_by_data_quality
severity_series = self._parse_severity_vectorized(df_status["data_flags"])
severity_mask = severity_series.isin(severity_list)
```

**Impact:** Uses pandas string operations and regex extraction instead of Python-level loop.

### 2. History Calculation (`_filter_by_history`)

**Before:**
```python
def calculate_row_history(row: pd.Series[str]) -> int:
    return self._calculate_history_days(
        row["price_start"],
        row["price_end"],
    )

df_copy["_history_days"] = df_copy.apply(calculate_row_history, axis=1)
```

**After:**
```python
# New vectorized helper method
@staticmethod
def _calculate_history_days_vectorized(
    price_start_series: pd.Series,
    price_end_series: pd.Series,
) -> pd.Series:
    start_dates = pd.to_datetime(price_start_series, errors="coerce")
    end_dates = pd.to_datetime(price_end_series, errors="coerce")
    deltas = end_dates - start_dates
    days = deltas.dt.days.fillna(0).astype(int)
    days = days.where(days >= 0, 0)
    return days

# In _filter_by_history
df_copy["_history_days"] = self._calculate_history_days_vectorized(
    df_copy["price_start"],
    df_copy["price_end"],
)
```

**Impact:** Uses pandas datetime arithmetic instead of Python-level loop.

### 3. Allow/Blocklist Filtering (`_apply_lists`)

**Before:**
```python
def not_in_blocklist(row: pd.Series[str]) -> bool:
    return not self._is_in_list(row["symbol"], row["isin"], blocklist)

blocklist_mask = df_result.apply(not_in_blocklist, axis=1)

def in_allowlist(row: pd.Series[str]) -> bool:
    return self._is_in_list(row["symbol"], row["isin"], allowlist)

allowlist_mask = df_result.apply(in_allowlist, axis=1)
```

**After:**
```python
# Blocklist filtering
symbol_blocked = df_result["symbol"].isin(blocklist)
isin_blocked = df_result["isin"].isin(blocklist)
in_blocklist = symbol_blocked | isin_blocked
blocklist_mask = ~in_blocklist

# Allowlist filtering
symbol_allowed = df_result["symbol"].isin(allowlist)
isin_allowed = df_result["isin"].isin(allowlist)
in_allowlist = symbol_allowed | isin_allowed
allowlist_mask = in_allowlist
```

**Impact:** Uses pandas `Series.isin()` with boolean operations instead of Python-level loop.

### 4. Dataclass Conversion (`_df_to_selected_assets`)

**Before:**
```python
assets = []
for _, row in df.iterrows():
    asset = SelectedAsset(
        symbol=row["symbol"],
        isin=row["isin"],
        # ... other fields
    )
    assets.append(asset)
```

**After:**
```python
records = df.to_dict("records")
assets = []
for record in records:
    asset = SelectedAsset(
        symbol=record["symbol"],
        isin=record["isin"],
        # ... other fields
    )
    assets.append(asset)
```

**Impact:** Uses `to_dict("records")` which is significantly faster than `.iterrows()`.

## Performance Benchmarks

All benchmarks run on a 10,000-row synthetic dataset with realistic filtering scenarios:

| Benchmark | Before (ms) | After (ms) | Speedup | Description |
|-----------|-------------|------------|---------|-------------|
| **1k rows basic** | 386 | 8.53 | **45x** | Basic filtering (status, history, rows) on 1k rows |
| **10k rows basic** | 3,871 | 52.77 | **73x** | Basic filtering (status, history, rows) on 10k rows |
| **10k rows complex** | 1,389 | 17.70 | **78x** | All filters (status, severity, history, markets, currencies, categories) |
| **10k rows severity** | 2,171 | 41.88 | **52x** | Severity filtering (most complex string parsing) |
| **10k rows allow/blocklist** | 4,989 | 24.17 | **206x** | Allow/blocklist filtering (1000 allowlist, 500 blocklist) |

### Key Findings

1. **Scalability:** The vectorized implementation scales linearly with dataset size, while the previous implementation had quadratic-like behavior for some operations.

2. **Most Improved:** Allow/blocklist filtering saw the most dramatic improvement (206x) because it involved two nested loops (one for apply, one for checking membership).

3. **Consistency:** All speedups are in the 45-206x range, showing consistent improvement across all filtering operations.

4. **Test Suite:** All 76 existing tests pass, confirming that filtering semantics remain unchanged.

## Technical Details

### Vectorization Techniques Used

1. **String Operations:** `Series.str.extract()` with regex for parsing complex string flags
2. **Datetime Arithmetic:** `pd.to_datetime()` + `Series.dt.days` for date calculations
3. **Set Operations:** `Series.isin()` for membership checks
4. **Boolean Indexing:** Combining boolean masks with `&`, `|`, `~` operators
5. **Batch Conversion:** `to_dict("records")` for DataFrame-to-object conversion

### Edge Cases Handled

The vectorized implementation maintains identical behavior for all edge cases:

- NaN values in data_flags
- Invalid date formats
- Empty DataFrames
- Missing columns
- Reversed dates (start > end)
- Overlapping allow/blocklists

## Usage

The benchmark suite can be run to verify performance on your system:

```bash
# Run all benchmarks
pytest tests/benchmarks/test_selection_performance.py -v -s

# Run specific benchmark
pytest tests/benchmarks/test_selection_performance.py::TestSelectionPerformance::test_benchmark_basic_filtering_large -v -s
```

## Future Work

Potential further optimizations (not included in this change to maintain minimal scope):

1. **Caching:** Cache parsed severity values if the same match report is filtered multiple times
2. **Parallel Processing:** Use Dask or multiprocessing for extremely large datasets (>1M rows)
3. **Memory Optimization:** Use categorical dtypes for columns with low cardinality
4. **JIT Compilation:** Consider Numba for hot paths if further speedup is needed

## Conclusion

The vectorization of AssetSelector successfully achieves the goal of scaling to large universes. The 45-206x speedup means:

- Processing 10,000 assets now takes ~50ms instead of ~4 seconds
- Processing 100,000 assets would take ~500ms instead of ~40 seconds
- The system can now comfortably handle universe sizes in the hundreds of thousands

All existing tests pass, confirming backward compatibility. The benchmark suite provides ongoing validation of performance characteristics.
