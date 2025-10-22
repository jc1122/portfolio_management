# Memory Bank Update Priority Guide

## 🚨 URGENT (Do First – 2-3 hours)

### 1. Update `activeContext.md` – Complete Rewrite

**Why:** Directly contradicts current development state
**Time:** 1.5 hours
**Actions:**

- \[ \] Add comprehensive "Recent Optimization Work (Oct 22)" section
- \[ \] Document 6 major implementations:
  - AssetSelector vectorization (45-206x speedup)
  - PriceLoader bounded cache (70-90% memory)
  - Statistics caching for portfolio strategies
  - Streaming diagnostics implementation
  - BacktestEngine optimization (O(n²) → O(rebalances))
  - Incremental resume feature
- \[ \] Change status from "ALL WORK COMPLETE" to "Core production-ready; optimization ongoing"
- \[ \] Document current active branch as `refactoring`
- \[ \] Reorganize "Latest Update" sections chronologically
- \[ \] Link to summary documents (VECTORIZATION_SUMMARY.md, etc.)

**Result:** Accurate reflection of current development state

______________________________________________________________________

### 2. Update `progress.md` – Add Oct-22 Section

**Why:** Progress tracking is 4 days out of date
**Time:** 1.5 hours
**Actions:**

- \[ \] Add "2025-10-22 Update – Performance Optimization Sprint" section at top
- \[ \] Document each of 6 major implementations with:
  - What was done (brief description)
  - Performance metrics where applicable
  - Test results
  - Files changed
- \[ \] Update "Current Status" section:
  - Test count (check actual via pytest)
  - Performance improvements (speedups, memory savings)
  - Branch status (refactoring branch)
- \[ \] Fix branch information (should be `refactoring`, not `feature/modular-monolith`)
- \[ \] Update "Status" claim (ongoing optimization, not "complete")
- \[ \] Reference external summary documents

**Result:** Progress tracking catches up to actual development

______________________________________________________________________

### 3. Update `techContext.md` – Add Performance Patterns

**Why:** Critical patterns missing from architecture documentation
**Time:** 45 minutes
**Actions:**

- \[ \] Add "Performance Optimization Patterns" section covering:
  - Vectorization approach (replace .apply()/.iterrows() with pandas operations)
  - Caching strategies (LRU bounded cache, rolling statistics cache)
  - Streaming diagnostics pattern
  - Benchmarking infrastructure
- \[ \] Update "Dependencies" section if new packages added
- \[ \] Refresh file count metrics if significant changes
- \[ \] Update "Outstanding Questions" if any resolved by Oct-22 work

**Result:** Architecture documentation includes performance considerations

______________________________________________________________________

## ⚠️ IMPORTANT (Do Second – 1-2 hours)

### 4. Organize Root Directory Clutter

**Why:** Loose files create confusion and aren't navigable
**Time:** 1 hour
**Actions:**

- \[ \] Create `docs/performance/` directory
- \[ \] Move benchmark files:
  - `benchmark_backtest_optimization.py` → `docs/performance/`
  - `benchmark_data_loading.py` → `docs/performance/`
  - Summary docs already in root but should link from progress.md
- \[ \] Move utility scripts:
  - `profile_pre_commit.py` → `scripts/profiling/`
  - `create_test_fixtures.py` → `tests/fixtures/` or reference in tests
- \[ \] Move/archive experiments:
  - `corrected_backtest.py` → `archive/experiments/`
  - `example_optimized_loading.py` → `docs/examples/` or delete if obsolete
- \[ \] Move shell scripts:
  - `copy_fixtures.sh` → `scripts/utils/` or delete if obsolete

**Result:** Root directory focused on active documentation; experiments archived

______________________________________________________________________

### 5. Reference Oct-22 Summary Documents in Memory Bank

**Why:** New documents aren't discoverable through Memory Bank
**Time:** 30 minutes
**Actions:**

- \[ \] In `progress.md`, add references to:
  - VECTORIZATION_SUMMARY.md
  - OPTIMIZATION_SUMMARY.md
  - STATISTICS_CACHING_SUMMARY.md
  - STREAMING_DIAGNOSTICS_COMPLETE.md
  - INCREMENTAL_RESUME_SUMMARY.md
- \[ \] Consider consolidating these into single "PERFORMANCE_OPTIMIZATION_SUMMARY.md"
- \[ \] Or move to `docs/performance/` directory with cross-references

**Result:** Oct-22 work is properly tracked and discoverable

______________________________________________________________________

### 6. Update `systemPatterns.md` – Add Optimization Patterns

**Why:** New patterns introduced but not documented in architecture
**Time:** 45 minutes
**Actions:**

- \[ \] Add "Performance Optimization Patterns" section:
  - Vectorization (replace row-wise operations with pandas)
  - Caching (LRU with bounds, rolling statistics)
  - Streaming diagnostics (chunk-based processing)
- \[ \] Link to performance documentation
- \[ \] Update "Critical Paths" if performance optimization affected them
- \[ \] Consider new "Follow-ups" for next optimization phase

**Result:** Architecture documentation reflects current implementation patterns

______________________________________________________________________

## 📋 NICE-TO-HAVE (Do Third – 1-2 hours)

### 7. Consolidate Archive

**Why:** Archive contains redundant completed work
**Time:** 1 hour
**Actions:**

- \[ \] Create `archive/REFACTORING_PHASES_1-9_COMPLETED.md` consolidating:
  - Summary of all 9 phases
  - Key metrics from each phase
  - Final completion date (Oct-18)
  - Link to individual completion reports (in appendix or separate directory)
- \[ \] Consolidate cleanup documents into single `TECHNICAL_DEBT_RESOLUTION_SUMMARY.md`
- \[ \] Move/delete obsolete planning documents
- \[ \] Reorganize archive structure:
  ```
  archive/
  ├── REFACTORING_PHASES_1-9_COMPLETED.md
  ├── TECHNICAL_DEBT_RESOLUTION_SUMMARY.md
  ├── sessions/          (old session notes for reference)
  ├── experiments/       (experiments and benchmarks)
  ├── phase-details/     (if keeping detailed per-phase docs)
  └── deprecated/        (clearly obsolete documents)
  ```

**Result:** Archive is cleaner and more navigable; easier to find historical context

______________________________________________________________________

### 8. Create Documentation Index

**Why:** Users need navigation through growing documentation
**Time:** 1 hour
**Actions:**

- \[ \] Create `docs/INDEX.md` (or update README.md section) with:
  - Quick links to all major documentation
  - Performance optimization docs
  - Architecture docs
  - Testing guides
  - Examples and tutorials
- \[ \] Add "Start Here" section for new developers
- \[ \] Link Memory Bank files from appropriate places
- \[ \] Add "Last Updated" timestamps

**Result:** Documentation is discoverable; easier navigation

______________________________________________________________________

## Quick Action Checklist

### This Session (2-3 hours)

- \[ \] Update activeContext.md (1.5 hr)
- \[ \] Update progress.md (1.5 hr)
- \[ \] Quick pass on techContext.md (0.5 hr)

### Follow-up Session (1-2 hours)

- \[ \] Organize root directory (1 hr)
- \[ \] Consolidate archive (1 hr)

### Optional (1-2 hours)

- \[ \] Create documentation index (1 hr)
- \[ \] Create performance optimization summary document (0.5 hr)

______________________________________________________________________

## Verification Checklist

After updates, verify:

- \[ \] All Oct-22 work is documented in progress.md
- \[ \] activeContext.md accurately reflects current branch and status
- \[ \] No false claims about "work complete" when optimization ongoing
- \[ \] systemPatterns.md includes performance optimization patterns
- \[ \] External summary documents are referenced from Memory Bank
- \[ \] Root directory doesn't contain loose benchmark/utility files
- \[ \] Archive structure is logical and not redundant
- \[ \] All changes are coherent and non-contradictory across Memory Bank files

______________________________________________________________________

## Expected Outcome

After completing URGENT and IMPORTANT sections:

✅ **activeContext.md** – Accurately describes current development state
✅ **progress.md** – Tracks all work through Oct-22
✅ **techContext.md** – Documents performance optimization patterns
✅ **systemPatterns.md** – Includes caching/vectorization/streaming patterns
✅ **Root directory** – Clean and organized
✅ **Archive** – Coherent and non-redundant
✅ **Navigation** – External docs properly referenced

**Result:** Memory Bank is current, coherent, and reliable for next development phase
