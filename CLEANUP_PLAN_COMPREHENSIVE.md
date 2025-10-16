# Comprehensive Cleanup Plan - Option B

**Target:** Achieve 9.5+/10 code quality and pristine repository state
**Duration:** 8-10 hours
**Status:** Ready for execution
**Date:** October 16, 2025

______________________________________________________________________

## 📋 Overview

This plan addresses all remaining technical debt and organizational issues to prepare the codebase for Phase 4 (Portfolio Construction). Each task includes clear success criteria, validation steps, and rollback instructions.

______________________________________________________________________

## 🎯 Task List Summary

| # | Task | Priority | Effort | Status |
|---|------|----------|--------|--------|
| 1 | Documentation Organization | P1 | 1-2h | ⏳ Pending |
| 2 | Pytest Configuration | P2 | 30m | ⏳ Pending |
| 3 | Ruff Auto-fixes | P2 | 15m | ⏳ Pending |
| 4 | Fix Blanket ruff noqa | P2 | 30m | ⏳ Pending |
| 5 | Add Missing Docstrings | P3 | 30m | ⏳ Pending |
| 6 | Refactor Complex Function | P3 | 1-2h | ⏳ Pending |
| 7 | Move Imports to TYPE_CHECKING | P4 | 1h | ⏳ Pending |
| 8 | Custom Exception Classes | P4 | 1-2h | ⏳ Pending |
| 9 | Memory Bank Update | P1 | 30m | ⏳ Pending |
| 10 | Final Validation | P1 | 30m | ⏳ Pending |

**Total Estimated Time:** 8-10 hours

______________________________________________________________________

## Task 1: Documentation Organization (1-2 hours)

### Objective

Reduce root-level markdown files from 18 to ~6, organizing historical docs into `archive/` structure.

### Current State

```
Root directory has 18 .md files:
- AGENTS.md
- CODE_REVIEW.md
- CODE_REVIEW_PHASE3.md
- DOCUMENTATION_ORGANIZATION_PLAN.md
- GEMINI.md
- PHASE3_COMPLETION_PLAN.md
- PHASE3_IMPLEMENTATION_TASKS.md
- PHASE3_PORTFOLIO_SELECTION_PLAN.md
- PHASE3_QUICK_START.md
- PHASE3_QUICK_START_COMPLETION.md
- README.md
- RESOLUTION_P2_P4_TECHNICAL_DEBT.md
- SESSION_P2_P4_RESOLUTION_SUMMARY.md
- SESSION_PHASE3_PLANNING.md
- SESSION_SUMMARY_CODE_REVIEW_CLEANUP.md
- SESSION_TECHNICAL_DEBT_REVIEW_2025-10-15.md
- TECHNICAL_DEBT_RESOLUTION_SUMMARY.md
- TECHNICAL_DEBT_REVIEW_2025-10-15.md
```

### Actions

#### 1.1 Create Archive Directory Structure

```bash
mkdir -p archive/phase3
mkdir -p archive/sessions
mkdir -p archive/technical-debt  # Already exists, verify
```

#### 1.2 Move Phase 3 Planning Documents

```bash
# Move to archive/phase3/
git mv PHASE3_COMPLETION_PLAN.md archive/phase3/
git mv PHASE3_IMPLEMENTATION_TASKS.md archive/phase3/
git mv PHASE3_PORTFOLIO_SELECTION_PLAN.md archive/phase3/
git mv PHASE3_QUICK_START.md archive/phase3/
git mv PHASE3_QUICK_START_COMPLETION.md archive/phase3/
git mv SESSION_PHASE3_PLANNING.md archive/phase3/
# Check if exists first:
[ -f CODE_REVIEW_PHASE3.md ] && git mv CODE_REVIEW_PHASE3.md archive/phase3/
```

#### 1.3 Move Session Summaries

```bash
# Move to archive/sessions/
git mv SESSION_P2_P4_RESOLUTION_SUMMARY.md archive/sessions/
git mv SESSION_SUMMARY_CODE_REVIEW_CLEANUP.md archive/sessions/
git mv SESSION_TECHNICAL_DEBT_REVIEW_2025-10-15.md archive/sessions/
```

#### 1.4 Move Technical Debt Documents

```bash
# Move to archive/technical-debt/
git mv RESOLUTION_P2_P4_TECHNICAL_DEBT.md archive/technical-debt/
git mv TECHNICAL_DEBT_RESOLUTION_SUMMARY.md archive/technical-debt/
# Keep TECHNICAL_DEBT_REVIEW_2025-10-15.md at root for now (latest review)
```

#### 1.5 Archive Documentation Plan (After This Cleanup)

```bash
# After this cleanup is complete:
git mv DOCUMENTATION_ORGANIZATION_PLAN.md archive/
```

### Expected Final State

**Root directory (6 active docs):**

- AGENTS.md
- README.md
- CODE_REVIEW.md
- TECHNICAL_DEBT_REVIEW_2025-10-15.md
- CLEANUP_PLAN_COMPREHENSIVE.md (this file)
- GEMINI.md (if actively used)

**Archive structure:**

```
archive/
├── phase3/
│   ├── PHASE3_COMPLETION_PLAN.md
│   ├── PHASE3_IMPLEMENTATION_TASKS.md
│   ├── PHASE3_PORTFOLIO_SELECTION_PLAN.md
│   ├── PHASE3_QUICK_START.md
│   ├── PHASE3_QUICK_START_COMPLETION.md
│   ├── SESSION_PHASE3_PLANNING.md
│   └── CODE_REVIEW_PHASE3.md (if exists)
├── sessions/
│   ├── SESSION_P2_P4_RESOLUTION_SUMMARY.md
│   ├── SESSION_SUMMARY_CODE_REVIEW_CLEANUP.md
│   ├── SESSION_TECHNICAL_DEBT_REVIEW_2025-10-15.md
│   ├── CLEANUP_SUMMARY.md (already exists)
│   ├── DOCUMENTATION_CLEANUP.md (already exists)
│   └── ... (other existing session files)
└── technical-debt/
    ├── RESOLUTION_P2_P4_TECHNICAL_DEBT.md
    ├── TECHNICAL_DEBT_RESOLUTION_SUMMARY.md
    ├── TECHNICAL_DEBT_PLAN.md (already exists)
    └── ... (other existing technical debt files)
```

### Validation

```bash
# Should show ~6 files
find . -maxdepth 1 -name "*.md" -type f | wc -l

# Verify archive structure
ls -la archive/phase3/
ls -la archive/sessions/
ls -la archive/technical-debt/

# Ensure all docs are tracked
git status
```

### Success Criteria

- ✅ Root directory has ≤6 markdown files
- ✅ All moved files are in appropriate archive subdirectories
- ✅ Git history preserved (using `git mv`)
- ✅ No broken links in active documentation

______________________________________________________________________

## Task 2: Pytest Configuration (30 minutes)

### Objective

Eliminate 5 pytest warnings about unknown marks (`integration`, `slow`).

### Current State

```
PytestUnknownMarkWarning: Unknown pytest.mark.integration
PytestUnknownMarkWarning: Unknown pytest.mark.slow
```

### Actions

#### 2.1 Add Markers to pyproject.toml

Open `pyproject.toml` and add pytest markers configuration.

**File:** `pyproject.toml`

**Find this section:**

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "-ra",
    "--strict-markers",
    "--strict-config",
    "--showlocals",
]
```

**Add after addopts:**

```toml
markers = [
    "integration: marks tests as integration tests (deselect with '-m \"not integration\"')",
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
]
```

### Validation

```bash
# Should show no warnings
python -m pytest tests/integration/test_full_pipeline.py -v

# List registered markers
python -m pytest --markers | grep -E "(integration|slow)"

# Run full suite - should have 0 warnings about marks
python -m pytest -v 2>&1 | grep -i "pytestunknownmarkwarning" | wc -l
# Expected: 0
```

### Success Criteria

- ✅ No PytestUnknownMarkWarning in test output
- ✅ Markers appear in `pytest --markers` output
- ✅ All 171 tests still pass

______________________________________________________________________

## Task 3: Ruff Auto-fixes (15 minutes)

### Objective

Apply automatic fixes for 8 auto-fixable ruff warnings.

### Current State

```
Found 47 errors.
8 fixable with the `--fix` option
```

**Auto-fixable issues:**

- F401: Unused imports (7 instances)
- Other formatting (1 instance)

### Actions

#### 3.1 Run Ruff Auto-fix

```bash
# Backup current state (optional)
git status
git diff

# Run auto-fix
ruff check --fix src/ scripts/ tests/

# Review changes
git diff
```

#### 3.2 Expected Fixes

**File:** `scripts/prepare_tradeable_data.py`

- Remove: `import re`
- Remove: `import pandas as pd` (in try block, unused)
- Remove: `infer_currency` import
- Remove: `resolve_currency` import
- Remove: `summarize_price_file` import
- Remove: `determine_unmatched_reason` import
- Remove: `StooqFile` import
- Remove: `TradeableInstrument` import
- Remove: `TradeableMatch` import

### Validation

```bash
# Check remaining warnings
ruff check src/ scripts/ tests/ --output-format=concise | grep -c "F401"
# Expected: 0 (or maybe 1-2 that couldn't be auto-fixed)

# Ensure tests still pass
python -m pytest -x -v

# Ensure mypy still passes
mypy src/ scripts/
```

### Success Criteria

- ✅ Ruff warning count reduced from 47 to ~39
- ✅ All tests still pass (171/171)
- ✅ Mypy shows 0 errors
- ✅ No unused imports remain

______________________________________________________________________

## Task 4: Fix Blanket ruff noqa (30 minutes)

### Objective

Replace 3 instances of blanket `# ruff: noqa` with specific rule codes.

### Current State

```python
# scripts/calculate_returns.py:1
# ruff: noqa

# scripts/classify_assets.py:1
# ruff: noqa

# scripts/manage_universes.py:1
# ruff: noqa
```

### Actions

#### 4.1 Analyze Each Script

For each script, determine which specific rules need suppression:

```bash
# Check what violations exist without noqa
ruff check scripts/calculate_returns.py --output-format=concise
ruff check scripts/classify_assets.py --output-format=concise
ruff check scripts/manage_universes.py --output-format=concise
```

#### 4.2 Fix calculate_returns.py

**File:** `scripts/calculate_returns.py`

**Current:**

```python
# ruff: noqa
"""Command-line interface for the return preparation pipeline."""
```

**Action:**

1. Comment out the noqa line
1. Run ruff to see actual violations
1. Add specific codes

**Expected violations:** E402 (module level imports not at top), possibly F401

**Replace with:**

```python
# ruff: noqa: E402, F401
"""Command-line interface for the return preparation pipeline."""
```

#### 4.3 Fix classify_assets.py

**File:** `scripts/classify_assets.py`

**Current:**

```python
# ruff: noqa
"""CLI script for asset classification.
```

**Replace with:**

```python
# ruff: noqa: E402, F401
"""CLI script for asset classification.
```

#### 4.4 Fix manage_universes.py

**File:** `scripts/manage_universes.py`

**Current:**

```python
# ruff: noqa
"""CLI script for universe management.
```

**Replace with:**

```python
# ruff: noqa: E402, F401
"""CLI script for universe management.
```

### Validation

```bash
# Should show specific suppressions instead of blanket noqa
ruff check scripts/ --output-format=concise | grep -i "PGH004"
# Expected: 0 results

# Ensure scripts still work
python scripts/calculate_returns.py --help
python scripts/classify_assets.py --help
python scripts/manage_universes.py --help
```

### Success Criteria

- ✅ No PGH004 warnings (blanket noqa)
- ✅ Specific rule codes documented
- ✅ Scripts execute without errors

______________________________________________________________________

## Task 5: Add Missing Docstrings (30 minutes)

### Objective

Add module-level docstrings to 2 modules with D100 warnings.

### Current State

```
2 × D100 Missing docstring in public module
```

### Actions

#### 5.1 Identify Missing Docstrings

```bash
ruff check src/ scripts/ tests/ --select D100 --output-format=concise
```

#### 5.2 Add Module Docstrings

For each file missing a docstring, add an appropriate module-level docstring at the top (after shebang and before imports).

**Template:**

```python
"""Brief one-line description.

Longer description if needed, explaining the module's purpose,
main classes/functions, and how it fits into the broader system.
"""
```

**Example for a hypothetical file:**

**Before:**

```python
from pathlib import Path
import pandas as pd
```

**After:**

```python
"""Data validation utilities for portfolio management pipeline.

This module provides functions for validating CSV data files,
checking data quality metrics, and ensuring consistency across
the data preparation workflow.
"""
from pathlib import Path
import pandas as pd
```

### Validation

```bash
# Should show 0 D100 warnings
ruff check src/ scripts/ tests/ --select D100

# Ensure docstrings are formatted correctly
ruff check src/ scripts/ tests/ --select D
```

### Success Criteria

- ✅ Zero D100 warnings
- ✅ All module docstrings follow project style
- ✅ Docstrings are meaningful and accurate

______________________________________________________________________

## Task 6: Refactor Complex Function (1-2 hours)

### Objective

Reduce cyclomatic complexity of `export_tradeable_prices` from 13 to ≤10.

### Current State

```
C901 `export_tradeable_prices` is too complex (13 > 10)
```

### Context

The function likely has multiple nested conditions and loops. We'll apply the same patterns used in Phase 2 Task 3 and Task 4.

### Actions

#### 6.1 Locate and Analyze Function

**File:** Find the file containing `export_tradeable_prices`

```bash
grep -rn "def export_tradeable_prices" src/
```

#### 6.2 Read Current Implementation

Read the function to understand its logic:

- What are the main stages?
- Which conditions can be extracted?
- What logic can be moved to helpers?

#### 6.3 Extract Helper Functions

Following Phase 2 patterns:

**Strategy 1: Extract condition checks**

```python
def _should_skip_file(file_path: Path, conditions: dict) -> bool:
    """Check if a file should be skipped based on conditions."""
    # Extract boolean logic here
    pass

def _is_valid_price_file(df: pd.DataFrame) -> bool:
    """Validate price file meets minimum requirements."""
    pass
```

**Strategy 2: Extract processing stages**

```python
def _initialize_export_state() -> dict:
    """Initialize state dictionary for export operation."""
    pass

def _process_price_file(file_path: Path, config: dict) -> pd.DataFrame:
    """Process a single price file for export."""
    pass

def _finalize_export(results: list, output_dir: Path) -> None:
    """Finalize export operation and write summary."""
    pass
```

**Strategy 3: Refactor main function**

```python
def export_tradeable_prices(...) -> ReturnType:
    """Export tradeable prices with quality filters.

    This is now a high-level orchestrator with clear stages.
    """
    # Stage 1: Initialize
    state = _initialize_export_state()

    # Stage 2: Process files
    for file_path in file_paths:
        if _should_skip_file(file_path, state):
            continue
        result = _process_price_file(file_path, config)
        state['results'].append(result)

    # Stage 3: Finalize
    _finalize_export(state['results'], output_dir)

    return state['summary']
```

#### 6.4 Maintain Test Coverage

After refactoring:

```bash
# Run tests for the modified module
python -m pytest tests/test_io.py -v  # or wherever tests are

# Check coverage didn't decrease
python -m pytest --cov=src/portfolio_management/io --cov-report=term-missing
```

### Validation

```bash
# Should show 0 C901 warnings
ruff check src/ --select C901

# All tests pass
python -m pytest -v

# Coverage maintained or improved
python -m pytest --cov=src/portfolio_management --cov-report=term-missing
```

### Success Criteria

- ✅ Cyclomatic complexity ≤10
- ✅ Helper functions have clear, single responsibilities
- ✅ All tests pass
- ✅ Code coverage maintained or improved
- ✅ Logic is more readable and maintainable

______________________________________________________________________

## Task 7: Move Imports to TYPE_CHECKING (1 hour)

### Objective

Move 7 imports into `TYPE_CHECKING` blocks to reduce runtime import overhead.

### Current State

```
3 × TC003 Move standard library import into a type-checking block
2 × TC003 Move standard library import into a type-checking block
1 × TC003 Move standard library import into a type-checking block
1 × TC001 Move application import into a type-checking block
1 × TC001 Move application import into a type-checking block
```

### Background

Imports only used for type annotations can be moved to `TYPE_CHECKING` blocks to avoid circular imports and reduce runtime overhead.

### Pattern

**Before:**

```python
from pathlib import Path
from collections.abc import Sequence

def process_files(files: Sequence[Path]) -> None:
    pass
```

**After:**

```python
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path
    from collections.abc import Sequence

def process_files(files: Sequence[Path]) -> None:
    pass
```

### Actions

#### 7.1 Identify All TC001/TC003 Warnings

```bash
ruff check src/ scripts/ --select TC001,TC003 --output-format=concise
```

#### 7.2 Fix Each File

For each file with TC001/TC003 warnings:

1. Add `from __future__ import annotations` at the top
1. Add `from typing import TYPE_CHECKING`
1. Move type-only imports into `if TYPE_CHECKING:` block
1. Keep imports needed at runtime outside the block

**Example file to fix:**

```bash
# Get full list
ruff check src/ --select TC001,TC003 --output-format=grouped
```

#### 7.3 Common Imports to Move

**Standard library (TC003):**

- `collections.abc.Sequence`
- `collections.abc.Iterable`
- `collections.Counter`
- `pathlib.Path`

**Application imports (TC001):**

- `.models.TradeableInstrument`
- `.models.StooqFile`

### Validation

```bash
# Should show 0 TC001/TC003 warnings
ruff check src/ scripts/ --select TC001,TC003

# Mypy should still pass
mypy src/ scripts/

# All tests pass
python -m pytest -v

# Runtime behavior unchanged
python scripts/select_assets.py --help
```

### Success Criteria

- ✅ Zero TC001/TC003 warnings
- ✅ Mypy still shows 0 errors
- ✅ All tests pass
- ✅ No runtime import errors

______________________________________________________________________

## Task 8: Custom Exception Classes (1-2 hours)

### Objective

Replace 3 long exception messages with custom exception classes.

### Current State

```
3 × TRY003 Avoid specifying long messages outside the exception class
```

### Background

Long exception messages should be encapsulated in custom exception classes for:

- Better error categorization
- Consistent error messages
- Easier testing
- Better type hints

### Actions

#### 8.1 Identify Long Exception Messages

```bash
ruff check src/ scripts/ --select TRY003 --output-format=concise
```

#### 8.2 Review Existing Exception Hierarchy

**File:** `src/portfolio_management/exceptions.py`

Check what custom exceptions already exist:

```python
class PortfolioManagementError(Exception):
    """Base exception for portfolio management operations."""

class DataValidationError(PortfolioManagementError):
    """Raised when data validation fails."""

class ConfigurationError(PortfolioManagementError):
    """Raised when configuration is invalid."""

class InsufficientDataError(PortfolioManagementError):
    """Raised when insufficient data is available."""

class SelectionError(PortfolioManagementError):
    """Raised when asset selection fails."""

class ClassificationError(PortfolioManagementError):
    """Raised when asset classification fails."""

class ReturnCalculationError(PortfolioManagementError):
    """Raised when return calculation fails."""

class UniverseError(PortfolioManagementError):
    """Raised when universe management fails."""
```

#### 8.3 Pattern for Each TRY003 Violation

**Before (Bad):**

```python
if not data_dir.exists():
    raise FileNotFoundError(
        f"Data directory not found: {data_dir}. "
        "Please ensure the data directory exists and contains valid price files. "
        "Run prepare_tradeable_data.py first to generate the required data."
    )
```

**After (Good):**

```python
# In exceptions.py
class DataDirectoryNotFoundError(DataValidationError):
    """Raised when the data directory is not found.

    This typically means the data preparation pipeline has not been run yet.
    Run prepare_tradeable_data.py to generate the required data directory.
    """

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        super().__init__(
            f"Data directory not found: {data_dir}. "
            "Run prepare_tradeable_data.py to generate required data."
        )

# In the calling code
if not data_dir.exists():
    raise DataDirectoryNotFoundError(data_dir)
```

#### 8.4 Create Custom Exceptions for Each TRY003

For each long exception message:

1. Create a custom exception class in `exceptions.py`
1. Move the message to the class's `__init__` or docstring
1. Replace the raise statement with the custom exception
1. Add type hints for any exception attributes

### Validation

```bash
# Should show 0 TRY003 warnings
ruff check src/ scripts/ --select TRY003

# Ensure exceptions are importable
python -c "from src.portfolio_management.exceptions import *; print('OK')"

# All tests pass
python -m pytest -v

# Exception messages are still informative
python scripts/select_assets.py --match-report /nonexistent/file.csv 2>&1 | grep -i "error"
```

### Success Criteria

- ✅ Zero TRY003 warnings
- ✅ Custom exceptions are well-documented
- ✅ Exception hierarchy is logical
- ✅ All tests pass
- ✅ Error messages remain helpful

______________________________________________________________________

## Task 9: Memory Bank Update (30 minutes)

### Objective

Update Memory Bank files to reflect cleanup completion and current project state.

### Actions

#### 9.1 Update progress.md

**File:** `memory-bank/progress.md`

Add new section at the top of "Completed Milestones":

```markdown
### Phase 3.5: Comprehensive Cleanup (✓ Complete)

**Date:** October 16, 2025
**Duration:** 8-10 hours
**Status:** ✅ COMPLETE

Comprehensive cleanup of technical debt and documentation organization to achieve pristine codebase state before Phase 4.

**Accomplishments:**

1. **Documentation Organization** (✓)
   - Reduced root markdown files from 18 to 6
   - Organized historical docs into `archive/phase3/`, `archive/sessions/`
   - Clear separation between active and archived documentation

2. **Pytest Configuration** (✓)
   - Added markers for `integration` and `slow` tests
   - Eliminated 5 pytest warnings
   - Improved test organization and selective execution

3. **Ruff Auto-fixes** (✓)
   - Applied 8 automatic fixes
   - Removed unused imports and variables
   - Reduced warnings from 47 to ~35

4. **Specific noqa Directives** (✓)
   - Replaced 3 blanket `# ruff: noqa` with specific rule codes
   - Improved code transparency and maintainability

5. **Module Docstrings** (✓)
   - Added missing D100 docstrings to 2 modules
   - Ensured all public modules are documented

6. **Complexity Refactoring** (✓)
   - Refactored `export_tradeable_prices` from CC=13 to CC≤10
   - Extracted helper functions following Phase 2 patterns
   - Improved readability and testability

7. **TYPE_CHECKING Blocks** (✓)
   - Moved 7 type-only imports to TYPE_CHECKING
   - Reduced runtime import overhead
   - Eliminated TC001/TC003 warnings

8. **Custom Exception Classes** (✓)
   - Created 3 new custom exceptions
   - Eliminated TRY003 warnings
   - Improved error categorization and testing

**Results:**
- ✅ 171 tests passing (100%)
- ✅ 0 mypy errors
- ✅ ~30 ruff warnings remaining (down from 47, all P4)
- ✅ Code quality: 9.5+/10
- ✅ Technical debt: VERY LOW → MINIMAL
- ✅ Repository organization: Excellent
```

#### 9.2 Update activeContext.md

**File:** `memory-bank/activeContext.md`

Update "Current Focus" section:

```markdown
## Current Focus

**Phase 1 Complete:** Data preparation pipeline successfully modularized and tested.
**Phase 2 Complete:** Technical debt resolution - type safety, concurrency, complexity reduction.
**Phase 3 Complete:** Asset selection, classification, returns, universe management - production ready.
**Phase 3.5 Complete:** Comprehensive cleanup - documentation organization, remaining technical debt.
**Current Phase:** Ready for Phase 4 - Portfolio Construction

## Recent Changes (Phase 3.5 – Comprehensive Cleanup) ✅

- Organized documentation: 18 root MD files → 6, with logical archive structure
- Eliminated all pytest warnings through proper marker configuration
- Applied ruff auto-fixes and replaced blanket noqa directives with specific codes
- Refactored complex functions to improve maintainability
- Moved type-only imports to TYPE_CHECKING blocks for cleaner runtime
- Enhanced exception hierarchy with custom exception classes
- **Repository is now in pristine state for Phase 4 work**

## Immediate Next Steps

1. Begin Phase 4: Portfolio Construction
   - Equal weight baseline implementation
   - Risk parity strategy
   - Mean-variance optimization via PyPortfolioOpt
2. Maintain code quality standards established in Phases 2-3.5
3. Continue test-driven development approach
```

#### 9.3 Update techContext.md

**File:** `memory-bank/techContext.md`

Add to "Key Patterns" section:

```markdown
- **Exception Hierarchy**: Custom exception classes derived from `PortfolioManagementError` provide clear error categorization and context. Exceptions include specific attributes and helpful messages for debugging and user feedback.
- **Type-Checking Optimization**: Type-only imports are moved to `TYPE_CHECKING` blocks to reduce runtime overhead and avoid circular imports while maintaining full type safety.
```

#### 9.4 Create Cleanup Summary Document

**File:** `archive/sessions/CLEANUP_COMPREHENSIVE_SUMMARY.md`

Create a summary document:

```markdown
# Comprehensive Cleanup Summary

**Date:** October 16, 2025
**Branch:** portfolio-construction
**Duration:** 8-10 hours
**Status:** ✅ COMPLETE

## Overview

Executed comprehensive cleanup plan (Option B) to bring codebase from 9.0/10 to 9.5+/10 quality before Phase 4 portfolio construction work.

## Achievements

[... detailed summary of all 8 tasks ...]

## Metrics

**Before:**
- Root markdown files: 18
- Ruff warnings: 47
- Pytest warnings: 5
- Code quality: 9.0/10
- Technical debt: LOW

**After:**
- Root markdown files: 6
- Ruff warnings: ~30
- Pytest warnings: 0
- Code quality: 9.5+/10
- Technical debt: MINIMAL

## Next Steps

Repository is ready for Phase 4: Portfolio Construction implementation.
```

### Validation

```bash
# Ensure all memory bank files are valid markdown
mdformat --check memory-bank/*.md

# Verify content is accurate
cat memory-bank/progress.md | grep -i "phase 3.5"
cat memory-bank/activeContext.md | grep -i "pristine"
```

### Success Criteria

- ✅ All Memory Bank files updated
- ✅ Documentation reflects current state
- ✅ Historical record is accurate
- ✅ Next steps are clear

______________________________________________________________________

## Task 10: Final Validation (30 minutes)

### Objective

Comprehensive validation that all tasks completed successfully and system is healthy.

### Actions

#### 10.1 Run Full Test Suite

```bash
# All tests pass
python -m pytest -v --tb=short

# Expected: 171 passed, 0 warnings
```

#### 10.2 Check Code Quality Metrics

```bash
# Mypy - should show 0 errors
mypy src/ scripts/

# Ruff - should show ~30 warnings (all P4)
ruff check src/ scripts/ tests/ | tail -1

# Coverage - should be ~86%
python -m pytest --cov=src/portfolio_management --cov-report=term | tail -5
```

#### 10.3 Verify Pre-commit Hooks

```bash
# Run all hooks
pre-commit run --all-files

# Should pass with no errors (warnings are OK)
```

#### 10.4 Test CLI Scripts

```bash
# All scripts should execute
python scripts/prepare_tradeable_data.py --help
python scripts/select_assets.py --help
python scripts/classify_assets.py --help
python scripts/calculate_returns.py --help
python scripts/manage_universes.py --help
```

#### 10.5 Verify Documentation Structure

```bash
# Root should have ~6 files
ls -1 *.md | wc -l
# Expected: 6

# Archive should have organized structure
tree -d archive/
```

#### 10.6 Create Validation Report

**File:** `CLEANUP_VALIDATION_REPORT.md`

```markdown
# Cleanup Validation Report

**Date:** October 16, 2025
**Validator:** [Agent Name]

## Test Results

- ✅ All 171 tests passing
- ✅ Zero pytest warnings
- ✅ 86% code coverage maintained

## Code Quality

- ✅ Mypy: 0 errors
- ✅ Ruff: 30 warnings (all P4)
- ✅ Pre-commit: All hooks passing

## Repository Structure

- ✅ 6 root markdown files
- ✅ Organized archive structure
- ✅ All git history preserved

## Functionality

- ✅ All CLI scripts operational
- ✅ Exception handling working
- ✅ Type checking functioning

## Final Status

**Code Quality:** 9.5+/10
**Technical Debt:** MINIMAL
**Ready for Phase 4:** YES ✅

## Metrics Summary

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Test Pass Rate | 100% | 100% | ✅ Maintained |
| Test Count | 171 | 171 | ✅ Maintained |
| Coverage | 86% | 86% | ✅ Maintained |
| Mypy Errors | 0 | 0 | ✅ Maintained |
| Ruff Warnings | 47 | 30 | ✅ -36% |
| Pytest Warnings | 5 | 0 | ✅ -100% |
| Root MD Files | 18 | 6 | ✅ -67% |
| Code Quality | 9.0/10 | 9.5+/10 | ✅ +5% |

**Status:** READY FOR PHASE 4 🚀
```

### Validation Commands Summary

```bash
# Complete validation script
cat << 'EOF' > validate_cleanup.sh
#!/bin/bash
set -e

echo "=== Running Full Validation ==="

echo "1. Testing..."
python -m pytest -v --tb=short

echo "2. Type checking..."
mypy src/ scripts/

echo "3. Linting..."
ruff check src/ scripts/ tests/

echo "4. Coverage..."
python -m pytest --cov=src/portfolio_management --cov-report=term

echo "5. Pre-commit..."
pre-commit run --all-files

echo "6. CLI functionality..."
python scripts/select_assets.py --help
python scripts/classify_assets.py --help
python scripts/calculate_returns.py --help
python scripts/manage_universes.py --help

echo "7. Documentation structure..."
echo "Root MD files: $(ls -1 *.md 2>/dev/null | wc -l)"
echo "Archive structure:"
tree -d archive/ -L 2

echo "=== Validation Complete ==="
EOF

chmod +x validate_cleanup.sh
./validate_cleanup.sh
```

### Success Criteria

- ✅ All tests pass (171/171)
- ✅ Zero mypy errors
- ✅ Ruff warnings ≤35
- ✅ Zero pytest warnings
- ✅ All CLI scripts functional
- ✅ Documentation properly organized
- ✅ Git history intact
- ✅ Pre-commit hooks pass

______________________________________________________________________

## 🎯 Rollback Plan

If any task fails critically, use these rollback procedures:

### Git-based Rollback

```bash
# View recent commits
git log --oneline -10

# Rollback to before cleanup (soft - keeps changes)
git reset --soft HEAD~N  # N = number of commits

# Rollback to before cleanup (hard - discards changes)
git reset --hard HEAD~N  # Use with caution!

# Rollback specific file
git checkout HEAD~1 -- path/to/file
```

### Task-specific Rollback

**Task 1 (Documentation):**

```bash
# Move files back
git mv archive/phase3/*.md .
git mv archive/sessions/*.md .
```

**Task 3 (Ruff auto-fixes):**

```bash
# Revert changes
git checkout -- src/ scripts/ tests/
```

**Task 6 (Refactoring):**

```bash
# Revert specific file
git checkout HEAD -- src/portfolio_management/io.py
```

______________________________________________________________________

## 📊 Success Metrics

### Before Cleanup

- Root markdown files: 18
- Test pass rate: 100% (171/171)
- Test warnings: 5
- Mypy errors: 0
- Ruff warnings: 47
- Code quality: 9.0/10
- Technical debt: LOW

### After Cleanup (Target)

- Root markdown files: ≤6
- Test pass rate: 100% (171/171)
- Test warnings: 0
- Mypy errors: 0
- Ruff warnings: ≤35
- Code quality: 9.5+/10
- Technical debt: MINIMAL

### Key Improvements

- 67% reduction in root documentation clutter
- 100% elimination of pytest warnings
- 36% reduction in ruff warnings
- 5% improvement in code quality score
- Enhanced maintainability and readability

______________________________________________________________________

## 🚀 Post-Cleanup: Phase 4 Readiness

Upon completion, the repository will be ready for Phase 4 work:

### Phase 4: Portfolio Construction

1. **Equal Weight Baseline**

   - Simple equal-weighted portfolio construction
   - Baseline for performance comparison

1. **Risk Parity Implementation**

   - Using `riskparityportfolio` library
   - Volatility-based weighting

1. **Mean-Variance Optimization**

   - Using `PyPortfolioOpt` library
   - Efficient frontier computation

### Development Standards

- Maintain 9.5+/10 code quality
- Keep test coverage ≥85%
- Zero mypy errors policy
- Address ruff warnings promptly
- Update documentation continuously

______________________________________________________________________

## 📝 Notes for Executing Agent

### General Guidelines

1. **Work sequentially** through tasks 1-10
1. **Validate after each task** before proceeding
1. **Commit after each major task** with descriptive messages
1. **Run tests frequently** to catch regressions early
1. **Update this plan** if you encounter unexpected issues
1. **Ask for clarification** if task requirements are unclear

### Commit Message Template

```
cleanup(task-N): <brief description>

- <detail 1>
- <detail 2>
- <detail 3>

Status: Task N/10 complete
Remaining tasks: <list>
```

### Time Management

- Tasks 1-5: Quick wins (3-4 hours)
- Tasks 6-8: Deep work (4-5 hours)
- Tasks 9-10: Documentation (1 hour)

### If Stuck

1. Review task's "Validation" section
1. Check git diff to see what changed
1. Run subset of tests to isolate issue
1. Consult relevant Phase 2 documentation for patterns
1. Create issue report with details

______________________________________________________________________

## ✅ Completion Checklist

Mark each task as complete:

- \[ \] Task 1: Documentation Organization
- \[ \] Task 2: Pytest Configuration
- \[ \] Task 3: Ruff Auto-fixes
- \[ \] Task 4: Fix Blanket ruff noqa
- \[ \] Task 5: Add Missing Docstrings
- \[ \] Task 6: Refactor Complex Function
- \[ \] Task 7: Move Imports to TYPE_CHECKING
- \[ \] Task 8: Custom Exception Classes
- \[ \] Task 9: Memory Bank Update
- \[ \] Task 10: Final Validation

**Final Status:** ⏳ PENDING

______________________________________________________________________

**END OF PLAN**

This plan is ready for execution by a coding agent. Each task has clear objectives, actions, validation steps, and success criteria. The agent can work independently through this plan to achieve pristine codebase state.
