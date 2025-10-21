# Incremental Resume Feature for `prepare_tradeable_data.py`

## Overview

The incremental resume feature dramatically speeds up repeated executions of `prepare_tradeable_data.py` when inputs haven't changed, reducing runtime from minutes to seconds by intelligently caching results and detecting changes.

## Problem Solved

Previously, `scripts/prepare_tradeable_data.py` would always:
- Rebuild the Stooq index (scanning 70k+ files)
- Re-match every instrument
- Re-generate all exports and reports

This took several minutes even when nothing had changed, making iterative development and testing slow.

## Solution

The incremental resume system:
1. **Tracks input state** via cryptographic hashes of:
   - Tradeable instrument CSVs (directory-level hash based on filenames and mtimes)
   - Stooq index file (content hash)

2. **Detects changes** by comparing current state to cached metadata

3. **Skips processing** when:
   - Input hashes match previous run
   - Output files exist (match report, unmatched report)

4. **Logs clearly** what action is taken and why

## Usage

### Enable Incremental Resume

Add the `--incremental` flag to any invocation:

```bash
python scripts/prepare_tradeable_data.py \
    --data-dir data/stooq \
    --tradeable-dir tradeable_instruments \
    --incremental
```

### First Run (Builds Everything)

```bash
$ python scripts/prepare_tradeable_data.py --incremental
INFO: Worker configuration: match/export=7, index=7 (cpu=8)
INFO: Incremental resume: inputs changed or outputs missing - running full pipeline
# ... normal processing logs ...
INFO: Exported 500 price files to data/processed/tradeable_prices
DEBUG: Saved cache metadata for future incremental resumes
```

**Result**: Full processing, cache metadata saved

### Second Run (Inputs Unchanged)

```bash
$ python scripts/prepare_tradeable_data.py --incremental
INFO: Worker configuration: match/export=7, index=7 (cpu=8)
INFO: Input files unchanged since last run - incremental resume possible
INFO: Incremental resume: inputs unchanged and outputs exist - skipping processing
INFO: Match report: data/metadata/tradeable_matches.csv
INFO: Unmatched report: data/metadata/tradeable_unmatched.csv
INFO: To force full rebuild, use --force-reindex or omit --incremental
```

**Result**: Completes in seconds, reuses cached outputs

### When Inputs Change

```bash
# Add new tradeable instrument CSV or modify existing one
$ echo "TSLA,US88160R1014,NASDAQ,Tesla,USD" >> tradeable_instruments/new.csv

$ python scripts/prepare_tradeable_data.py --incremental
INFO: Worker configuration: match/export=7, index=7 (cpu=8)
DEBUG: Tradeable directory changed (hash a1b2c3d4 -> e5f6g7h8)
INFO: Incremental resume: inputs changed or outputs missing - running full pipeline
# ... normal processing logs ...
```

**Result**: Detects change, runs full pipeline, updates cache

## Configuration

### Cache Metadata Location

By default, cache metadata is stored in `data/metadata/.prepare_cache.json`.

Customize with `--cache-metadata`:

```bash
python scripts/prepare_tradeable_data.py \
    --incremental \
    --cache-metadata /custom/path/cache.json
```

### Cache Metadata Format

The cache file is JSON with this structure:

```json
{
  "tradeable_hash": "abc123...",
  "stooq_index_hash": "def456..."
}
```

## Force Full Rebuild

Three ways to bypass the cache:

1. **Omit --incremental flag**:
   ```bash
   python scripts/prepare_tradeable_data.py  # no --incremental
   ```

2. **Use --force-reindex**:
   ```bash
   python scripts/prepare_tradeable_data.py --incremental --force-reindex
   ```

3. **Delete cache file**:
   ```bash
   rm data/metadata/.prepare_cache.json
   python scripts/prepare_tradeable_data.py --incremental
   ```

## Change Detection Details

### Tradeable CSVs

Hash computed from:
- Sorted list of `.csv` filenames in tradeable directory
- Modification time (`st_mtime`) of each file

**Triggers rebuild**:
- New CSV added
- CSV deleted
- CSV content modified (changes mtime)
- CSV renamed

### Stooq Index

Hash computed from:
- Full content of `metadata_output` CSV file (default: `data/metadata/stooq_index.csv`)

**Triggers rebuild**:
- Stooq index regenerated
- Stooq data directory changed (when using `--force-reindex`)

### Output Files

Existence check for:
- Match report (default: `data/metadata/tradeable_matches.csv`)
- Unmatched report (default: `data/metadata/tradeable_unmatched.csv`)

**Triggers rebuild**:
- Either file missing
- Either file deleted

## Performance Impact

### Typical Dataset (500 instruments, 70k+ Stooq files)

| Scenario | Without --incremental | With --incremental |
|----------|----------------------|-------------------|
| First run | 3-5 minutes | 3-5 minutes |
| No changes | 3-5 minutes | **< 5 seconds** |
| 1 CSV changed | 3-5 minutes | 3-5 minutes |
| Force reindex | 3-5 minutes | 3-5 minutes |

**Speedup**: ~60x faster for unchanged inputs

## Testing

The feature includes comprehensive test coverage:

### Unit Tests (18 tests)

Tests for `data/cache.py` functions:
```bash
pytest tests/data/test_cache.py -v
```

Covers:
- Hash computation (directories, files)
- Change detection logic
- Metadata persistence
- Edge cases (missing files, invalid JSON, etc.)

### Integration Tests (3 tests)

Tests for end-to-end behavior:
```bash
pytest tests/scripts/test_prepare_tradeable_incremental.py -v
```

Covers:
- Skipping when inputs unchanged
- Rerunning when inputs change
- CLI flag presence

## Implementation Details

### Architecture

```
prepare_tradeable_data.py
    ↓
prepare_tradeable_data(args)
    ↓
[--incremental?] → Yes → cache.inputs_unchanged() ?
                          ↓                    ↓
                         Yes                  No
                          ↓                    ↓
                    Skip & Exit          Run Full Pipeline
                                              ↓
                                      cache.save_cache_metadata()
```

### Key Functions (data/cache.py)

- `compute_directory_hash(dir, pattern)` - Hash directory state
- `compute_stooq_index_hash(path)` - Hash index file
- `inputs_unchanged(tradeable_dir, index_path, cache)` - Compare to cache
- `outputs_exist(match_report, unmatched_report)` - Check outputs
- `create_cache_metadata(tradeable_dir, index_path)` - Create new cache
- `save_cache_metadata(path, metadata)` - Persist cache
- `load_cache_metadata(path)` - Load cache

## Limitations & Caveats

1. **Hash-based, not content-aware**
   - Changing a file triggers rebuild even if change is inconsequential
   - E.g., adding a comment or whitespace to CSV

2. **Directory-level granularity**
   - Cannot detect which specific tradeable CSV changed
   - Always rebuilds entire dataset when any CSV changes

3. **No partial exports**
   - Even if only one instrument changed, all exports regenerated
   - Future enhancement could add symbol-level granularity

4. **Manual cache invalidation**
   - If you modify Stooq data files directly, you must use `--force-reindex`
   - Cache doesn't track raw Stooq directory (only the built index)

5. **Single-machine only**
   - Cache metadata is local to the machine
   - Shared/distributed builds would need cache synchronization

## Future Enhancements

Potential improvements for future iterations:

1. **Symbol-level caching**
   - Track which instruments changed
   - Only re-export affected price files

2. **Partial matching**
   - Re-match only new/changed instruments
   - Merge with previous match report

3. **Stooq directory tracking**
   - Hash Stooq data directory directly
   - Auto-invalidate when new files appear

4. **Cache versioning**
   - Invalidate cache when script logic changes
   - Prevent stale results from old algorithm

5. **Cache statistics**
   - Track hit/miss rate
   - Show time saved

## Troubleshooting

### Cache Not Working

**Symptom**: Always rebuilds even with `--incremental`

**Checks**:
1. Verify cache file exists: `ls -la data/metadata/.prepare_cache.json`
2. Check logs for "DEBUG: Tradeable directory changed" or "DEBUG: Stooq index changed"
3. Ensure output files exist (match_report, unmatched_report)
4. Try with `--log-level DEBUG` for detailed diagnostics

### Stale Results

**Symptom**: Outputs don't reflect recent changes

**Solution**:
Force rebuild with `--force-reindex` or delete cache file

### Cache File Errors

**Symptom**: "Failed to load cache metadata" warning

**Cause**: Corrupted JSON or file permissions

**Solution**:
Delete cache file - it will be recreated on next run

## See Also

- Issue: [Add incremental resume to prepare_tradeable_data](https://github.com/jc1122/portfolio_management/issues/XXX)
- Code: `src/portfolio_management/data/cache.py`
- Tests: `tests/data/test_cache.py`, `tests/scripts/test_prepare_tradeable_incremental.py`
