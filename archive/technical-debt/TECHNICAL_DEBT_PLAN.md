# Technical Debt Resolution Plan

**Date:** October 15, 2025
**Branch:** `scripts/prepare_tradeable_data.py-refactor`

## Current Issues Summary

### Type Checking Issues (mypy)

1. Missing pandas-stubs library
1. Missing type annotations in `utils._run_in_parallel`
1. Generic type parameters missing (dict, Counter)
1. Dataclass typing issues in `io.py`

### Code Quality Issues

1. **Matching complexity** - `_match_instrument` function (not yet reviewed fully)
1. **Concurrency implementation** - `_collect_relative_paths` and `_run_in_parallel`
1. **Analysis helpers** - Already well-decomposed but could tighten boundaries

## Resolution Tasks

### Task 1: Fix Type Annotations (High Priority)

**Estimated time:** 30-45 minutes

#### 1.1 Install pandas-stubs

```bash
pip install pandas-stubs types-PyYAML
```

#### 1.2 Add type hints to `utils.py`

- Add proper type annotations to `_run_in_parallel`
- Add return type to `log_duration`

#### 1.3 Fix generic types

- Add type parameters to `dict` declarations
- Add type parameters to `Counter` declarations

#### 1.4 Fix io.py dataclass issues

- Fix asdict call type issues
- Fix list type assignment issues

**Files affected:**

- `requirements-dev.txt` (add pandas-stubs)
- `src/portfolio_management/utils.py`
- `src/portfolio_management/io.py`
- `src/portfolio_management/analysis.py`
- `src/portfolio_management/matching.py`

### Task 2: Review and Improve Concurrency (Medium Priority)

**Estimated time:** 45-60 minutes

#### 2.1 Review `_run_in_parallel`

Current issues:

- No type hints
- Returns unordered results (uses `as_completed`)
- No error handling/logging

Improvements needed:

- Add proper type hints with TypeVar for return type
- Document ordering behavior
- Add error handling option
- Consider preserving order if needed

#### 2.2 Review `_collect_relative_paths`

Current implementation uses `_run_in_parallel` with `os.walk`.

Questions to answer:

- Is the threading model appropriate for I/O-bound directory scanning?
- Should we preserve order of results?
- Do we need better error aggregation?

**Files affected:**

- `src/portfolio_management/utils.py`
- `src/portfolio_management/stooq.py`

### Task 3: Review Matching Logic (Medium Priority)

**Estimated time:** 60-90 minutes

Need to examine:

- `_match_instrument` function complexity
- Strategy pattern implementation
- Can we simplify branching logic?

**Files affected:**

- `src/portfolio_management/matching.py`

### Task 4: Add Tests for Concurrency (Low Priority)

**Estimated time:** 30-45 minutes

Add targeted tests for:

- `_run_in_parallel` with various worker counts
- Error handling in parallel execution
- `_collect_relative_paths` behavior

**Files affected:**

- `tests/test_utils.py` (new)
- `tests/test_stooq.py` (expand)

## Recommended Order

1. **Start with Task 1 (Type Annotations)** - Quick wins, improves code quality immediately
1. **Then Task 2 (Concurrency)** - Core infrastructure that affects multiple modules
1. **Then Task 3 (Matching)** - More complex, requires careful refactoring
1. **Finally Task 4 (Tests)** - Validate the improvements

## Success Criteria

- \[ \] All mypy errors resolved (except acceptable pandas import warnings)
- \[ \] `_run_in_parallel` properly typed and documented
- \[ \] Code passes ruff complexity checks (or suppressions are justified)
- \[ \] Test coverage maintained at 75%+
- \[ \] All 17+ tests passing
- \[ \] Pre-commit hooks pass (\<50s runtime)

## Notes

- Keep changes incremental - commit after each task
- Run tests after each change
- Update docstrings as you improve code
- Don't break existing functionality
