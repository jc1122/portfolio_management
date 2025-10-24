# Cache Reliability Guarantees and Failure Modes

## Overview

The FactorCache provides on-disk caching for expensive factor score calculations and point-in-time (PIT) eligibility determinations. This document describes the reliability guarantees, failure modes, and recovery strategies.

## Reliability Guarantees

### 1. **Correctness: Cached Results Equal Uncached Results**

**Guarantee**: When a cache hit occurs, the returned data is byte-for-byte identical to what would be computed without caching.

**Mechanism**:
- Hash-based invalidation ensures cache is invalidated when inputs change
- Pickle serialization preserves exact numerical precision
- No transformations applied to cached data during retrieval

**Validation**: See `tests/integration/test_caching_edge_cases.py::TestCacheCorrectness`

### 2. **Automatic Invalidation on Data Changes**

**Guarantee**: Cache automatically invalidates when:
- Returns dataset changes (any value modification)
- Configuration changes (lookback, skip, method parameters)
- Date range changes
- Data structure changes (column order, index order)

**Mechanism**:
- Dataset hash computed using `pd.util.hash_pandas_object()`
- Configuration hash computed using sorted JSON serialization
- Cache key includes dataset hash, config hash, and date range
- Mismatch on any component results in cache miss

**Validation**: See `tests/integration/test_caching_edge_cases.py::TestCacheInvalidation`

### 3. **Age-Based Expiration**

**Guarantee**: When `max_cache_age_days` is set, cache entries older than this limit are automatically invalidated.

**Mechanism**:
- Metadata stores creation timestamp (ISO 8601 format)
- On cache retrieval, age is computed: `(now - created_at).days`
- Entry invalidated if `age > max_cache_age_days`
- `max_cache_age_days=None` disables age-based expiration

**Validation**: See `tests/integration/test_caching_edge_cases.py::TestCacheAgeExpiration`

### 4. **Statistics Accuracy**

**Guarantee**: Cache statistics (hits, misses, puts) accurately reflect cache operations.

**Mechanism**:
- Counters updated atomically on each operation
- Thread-safe operations (no concurrent modification)
- `get_stats()` returns current snapshot
- `reset_stats()` allows resetting counters for testing

**Validation**: See `tests/integration/test_caching_edge_cases.py::TestCacheStatistics`

### 5. **No Silent Failures**

**Guarantee**: Cache errors result in either:
1. Explicit exception raised (documented failure mode)
2. Cache miss returned (graceful degradation)

**Never**: Silently return incorrect data or corrupt state.

**Mechanism**:
- Try-except blocks catch corruption errors
- Failed deserializations return None (cache miss)
- Logging captures all failure events
- No fallback to stale/corrupted data

**Validation**: See `tests/integration/test_caching_edge_cases.py::TestCacheCorrectness`

## Failure Modes and Recovery

### 1. Disk Space Exhausted

**Symptom**: Cache writes fail with `OSError: No space left on device`

**Behavior**:
- `put_factor_scores()` and `put_pit_eligibility()` may raise `OSError`
- Existing cache entries remain valid
- Subsequent cache gets still work for existing entries

**Recovery**:
1. Free disk space
2. Optionally call `cache.clear()` to remove old entries
3. Cache will resume normal operation

**Mitigation**:
- Set reasonable `max_cache_age_days` to limit growth
- Monitor cache directory size
- Implement cache size limits in application layer

### 2. Permission Denied

**Symptom**: Cannot write to cache directory (permission error)

**Behavior**:
- Cache initialization may fail if directory cannot be created
- `put_*()` operations may raise `PermissionError`
- Cache gets still work for existing entries (if readable)

**Recovery**:
1. Fix directory permissions: `chmod 755 $CACHE_DIR`
2. Or run with appropriate user permissions
3. Or disable caching: `FactorCache(dir, enabled=False)`

**Mitigation**:
- Create cache directory with appropriate permissions during setup
- Use user-writable cache directories (e.g., `~/.cache/portfolio_management`)

### 3. Corrupted Pickle Data

**Symptom**: Cache hit returns `None` unexpectedly; warning logged

**Behavior**:
- `get_*()` catches `pickle.UnpicklingError` and other exceptions
- Logs warning: "Failed to load cached data: {error}"
- Returns `None` (cache miss)
- Increments miss counter

**Recovery**:
- Automatic: Next computation will recalculate and overwrite corrupted entry
- Manual: Call `cache.clear()` to remove all corrupted entries

**Causes**:
- Disk corruption
- Incomplete write (process killed during put)
- Pickle version incompatibility (rare)

**Mitigation**:
- Use `pickle.HIGHEST_PROTOCOL` (done by default)
- Ensure clean shutdown of processes
- Consider atomic writes for critical caching

### 4. Corrupted Metadata JSON

**Symptom**: Cache fails to load metadata; may raise `JSONDecodeError`

**Behavior**:
- Depends on corruption severity:
  - Minor: May successfully parse but with incorrect values → cache miss
  - Major: `json.JSONDecodeError` raised → cache miss
- Returns `None` for cache get
- Increments miss counter

**Recovery**:
- Automatic: Corrupted entry treated as missing
- Manual: Delete corrupted `.json` file or call `cache.clear()`

**Causes**:
- Incomplete write
- Concurrent write (if multiple processes writing)
- Disk corruption

**Mitigation**:
- Avoid concurrent writes to same cache key
- Use file locking for multi-process scenarios (not currently implemented)

### 5. Missing Metadata or Data File

**Symptom**: One file exists but corresponding pair is missing

**Behavior**:
- Both metadata (.json) and data (.pkl) required for valid entry
- Missing either file results in cache miss
- No error raised; transparent fallback

**Recovery**:
- Automatic: Next computation recreates both files
- Manual: Clean up orphaned files with `cache.clear()`

**Causes**:
- Incomplete write
- Manual file deletion
- Filesystem issues

**Mitigation**:
- Atomic writes (write to temp, then rename)
- Cleanup orphaned files periodically

### 6. Cache Directory is File

**Symptom**: `OSError` or `FileExistsError` during initialization

**Behavior**:
- `FactorCache` constructor raises exception
- Cache cannot be created or used

**Recovery**:
1. Remove file: `rm $CACHE_DIR`
2. Recreate cache: `FactorCache($CACHE_DIR, enabled=True)`

**Mitigation**:
- Validate cache directory path during configuration
- Use dedicated directory for cache (avoid naming conflicts)

### 7. Disabled Cache

**Symptom**: All cache operations return `None` or no-op

**Behavior**:
- `get_*()` always returns `None`
- `put_*()` is no-op
- Statistics remain zero
- Cache directories not created

**Recovery**:
- N/A (this is intentional behavior)
- Enable cache: `FactorCache($DIR, enabled=True)`

**Use Cases**:
- Testing uncached performance
- Debugging cache-related issues
- Environments where caching is not desired

## Error Handling Best Practices

### 1. Wrap Cache Operations in Try-Except

```python
try:
    cache = FactorCache(cache_dir, enabled=True)
    cached = cache.get_factor_scores(returns, config, start, end)
    if cached is None:
        # Cache miss - compute
        scores = compute_scores(returns, config)
        cache.put_factor_scores(scores, returns, config, start, end)
except OSError as e:
    logger.warning(f"Cache error: {e}. Continuing without cache.")
    # Compute without caching
    scores = compute_scores(returns, config)
```

### 2. Graceful Degradation

Always provide fallback to uncached computation:

```python
def get_scores_with_cache(returns, config, cache=None):
    """Get scores with optional caching."""
    if cache is not None:
        try:
            cached = cache.get_factor_scores(returns, config, start, end)
            if cached is not None:
                return cached
        except Exception as e:
            logger.warning(f"Cache error: {e}. Computing without cache.")
    
    # Fallback: compute without cache
    return compute_scores(returns, config)
```

### 3. Monitor Cache Health

```python
def check_cache_health(cache):
    """Check cache statistics and health."""
    stats = cache.get_stats()
    hit_rate = stats["hits"] / (stats["hits"] + stats["misses"]) if stats["hits"] + stats["misses"] > 0 else 0
    
    if hit_rate < 0.5:
        logger.warning(f"Low cache hit rate: {hit_rate:.2%}")
    
    # Check cache directory size
    cache_size = sum(f.stat().st_size for f in cache.data_dir.glob("*.pkl"))
    if cache_size > 1e9:  # 1 GB
        logger.warning(f"Cache size large: {cache_size / 1e9:.2f} GB")
```

## Configuration Recommendations

### Development Environment

```python
# Aggressive caching for fast iteration
cache = FactorCache(
    cache_dir=Path(".cache/dev"),
    enabled=True,
    max_cache_age_days=None,  # Never expire
)
```

### Production Environment

```python
# Conservative caching with age limits
cache = FactorCache(
    cache_dir=Path("/var/cache/portfolio_management"),
    enabled=True,
    max_cache_age_days=7,  # Expire after 1 week
)
```

### Testing Environment

```python
# Disable caching for deterministic tests
cache = FactorCache(
    cache_dir=Path("/tmp/test_cache"),
    enabled=False,  # No caching
)
```

### Benchmarking

```python
# Enable caching but reset stats
cache = FactorCache(cache_dir, enabled=True)
cache.reset_stats()

# Run benchmark
# ...

# Report statistics
stats = cache.get_stats()
print(f"Hit rate: {stats['hits']/(stats['hits']+stats['misses']):.2%}")
```

## Testing Cache Reliability

See `tests/integration/test_caching_edge_cases.py` for comprehensive edge case tests:

- **Invalidation correctness**: Data/config/date changes
- **Disk I/O errors**: Full disk, permissions, corruption
- **Age expiration**: Boundary conditions, TTL=0, no TTL
- **Statistics accuracy**: 100+ operations, mixed patterns
- **Correctness**: Cached = uncached results
- **Edge configs**: Disabled cache, empty directory
- **Hit/miss patterns**: First run, second run, partial changes

## Monitoring and Observability

### Log Levels

- `DEBUG`: Cache miss details (verbose)
- `INFO`: Cache hits, cache puts (normal)
- `WARNING`: Cache errors, corruption detected (actionable)
- `ERROR`: Critical cache failures (requires attention)

### Metrics to Track

1. **Hit Rate**: `hits / (hits + misses)`
2. **Cache Size**: Total bytes in cache directory
3. **Entry Count**: Number of cached entries
4. **Error Rate**: Cache errors per operation
5. **Age Distribution**: Distribution of entry ages

## Limitations and Known Issues

### 1. No Concurrency Control

**Issue**: Multiple processes writing to same cache key can cause corruption.

**Mitigation**: Avoid concurrent writes or implement file locking.

### 2. No Cache Size Limit

**Issue**: Cache can grow unbounded if `max_cache_age_days=None`.

**Mitigation**: Set reasonable TTL or implement application-level size limits.

### 3. Pickle Version Compatibility

**Issue**: Pickles created with newer Python may not load in older Python.

**Mitigation**: Use same Python version for all cache operations.

### 4. Hash Collisions (Theoretical)

**Issue**: SHA256 is truncated to 16 chars, increasing collision probability.

**Probability**: ~1 in 10^19 (negligible for practical use)

**Mitigation**: Full hash comparison in metadata (already done).

## Changelog

- **2025-10-24**: Initial documentation
  - Documented reliability guarantees
  - Documented failure modes and recovery
  - Added best practices and configuration examples
  - Added monitoring and testing guidance
