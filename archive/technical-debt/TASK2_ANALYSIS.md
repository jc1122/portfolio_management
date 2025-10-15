# Task 2: Concurrency Implementation Review

**Date:** October 15, 2025
**Status:** In Progress

## Current Implementation Analysis

### `_run_in_parallel` Function

**Current Code:**

```python
def _run_in_parallel(
    func: Callable[..., T],
    args_list: list[tuple[Any, ...]],
    max_workers: int,
) -> list[T]:
    """Run a function in parallel with a list of arguments.

    Returns:
        List of results from func calls. Note: Results may be unordered
        when max_workers > 1 due to as_completed iteration.
    """
    if max_workers <= 1:
        return [func(*args) for args in args_list]

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(func, *args) for args in args_list]
        return [future.result() for future in as_completed(futures)]
```

### Issues Identified

#### 1. **Result Ordering** 🔴 (HIGH PRIORITY)

- Uses `as_completed(futures)` which returns results **out of order**
- Current usages don't appear to depend on order, but this is fragile
- Future code changes could break silently

**Evidence:**

- `stooq.py:58` - Extends results to list (order matters for reproducibility)
- `io.py:347` - Sums boolean results (order doesn't matter functionally, but matters for debugging)
- `matching.py:375` - Processes tuples sequentially (order-dependent logic)

#### 2. **No Error Handling** 🟡 (MEDIUM PRIORITY)

- If any worker raises exception, `future.result()` re-raises it
- Entire operation fails; no partial results returned
- No context about which task failed
- No way to distinguish between task errors and executor errors

#### 3. **No Logging/Diagnostics** 🟡 (MEDIUM PRIORITY)

- No way to know which tasks completed, which failed, when
- No performance metrics per task
- Difficult to debug parallel execution issues
- Makes monitoring and optimization hard

#### 4. **Thread Pool Appropriateness** 🟢 (LOW PRIORITY)

- All three usages are **I/O-bound** (file system operations):
  - `stooq.py`: Directory scanning (`os.walk`)
  - `io.py`: File reading/writing
  - `matching.py`: Python object comparisons (CPU-bound, but small operations)
- ThreadPoolExecutor **is appropriate** for I/O-bound work (GIL released during I/O)
- No need to switch to ProcessPoolExecutor

#### 5. **Type Annotation Could Be Better** 🟢 (LOW PRIORITY)

- Current: `args_list: list[tuple[Any, ...]]`
- Could be more flexible: `Sequence[tuple[Any, ...]]`
- Could accept different argument structures if needed

## Usage Patterns

### Pattern 1: Directory Scanning (`stooq.py`)

```python
results = _run_in_parallel(_scan_directory, [(d,) for d in top_level_dirs], max_workers)
for result in results:
    rel_paths.extend(result)
```

**Issue:** Order-independent, but order would help with reproducibility

### Pattern 2: File Export (`io.py`)

```python
results = _run_in_parallel(_export_single, [(m,) for m in unique_matches.values()], config.max_workers)
exported = sum(1 for r in results if r)
```

**Issue:** Order-independent, sums boolean results

### Pattern 3: Instrument Matching (`matching.py`)

```python
results = _run_in_parallel(_match_instrument, [(instrument, ...) for instrument in instruments], max_workers)
for match, missing in results:
    # Process results in order
```

**Issue:** Appears to process results sequentially after parallel execution; order-independent

## Recommendations

### High Priority (Must Fix)

1. **Preserve Result Order** - Use `map` from executor instead of `as_completed`

   - Better for reproducibility and debugging
   - Makes result matching easier
   - Minimal performance impact

1. **Add Error Handling** - Wrap in try-except with context

   - Catch exceptions from individual tasks
   - Log failures with task identity
   - Decide: fail-fast vs. collect-all-errors approach

### Medium Priority (Should Fix)

3. **Add Diagnostics** - Log task execution with timing

   - Per-task timing would help identify bottlenecks
   - Task start/completion logging for debugging

1. **Better Type Hints** - Accept `Sequence` instead of `list`

   - More flexible API
   - Matches actual usage patterns

### Low Priority (Nice to Have)

5. **Configuration Options**
   - Option to preserve order (default True)
   - Option for error handling strategy
   - Option for logging level

## Implementation Plan

**Phase 1: Preserve Order** (Quick win, 20 min)

- Switch from `as_completed` to `map` or manual ordering
- Verify all tests still pass
- No API changes needed

**Phase 2: Add Error Handling** (Medium effort, 30 min)

- Wrap task execution in try-except
- Log failures with context
- Decide error strategy (fail-fast by default)

**Phase 3: Add Diagnostics** (Nice to have, 20 min)

- Add timing per task
- Log task start/completion events
- Make logging level configurable

**Phase 4: Tests** (30-45 min)

- Test with various worker counts
- Test error scenarios
- Test performance characteristics

## Files to Modify

- `src/portfolio_management/utils.py` - Core implementation
- `tests/` - Add new tests (to be created)

## Notes

- All changes are backward compatible at API level
- Focus on robustness and debuggability
- Minimal performance overhead expected
