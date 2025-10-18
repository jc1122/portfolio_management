# Cleanup Quick Reference Card

**For:** Coding agents executing CLEANUP_PLAN_COMPREHENSIVE.md
**Date:** October 16, 2025

______________________________________________________________________

## 🎯 Mission

Transform codebase from **9.0/10 → 9.5+/10** quality through systematic cleanup.

______________________________________________________________________

## 📋 Task Overview (8-10 hours)

| # | Task | Time | Command |
|---|------|------|---------|
| 1 | Documentation | 1-2h | `git mv` files to archive/ |
| 2 | Pytest markers | 30m | Edit `pyproject.toml` |
| 3 | Ruff auto-fix | 15m | `ruff check --fix` |
| 4 | Specific noqa | 30m | Replace `# ruff: noqa` |
| 5 | Docstrings | 30m | Add module docstrings |
| 6 | Refactor complex | 1-2h | Extract helpers |
| 7 | TYPE_CHECKING | 1h | Move type imports |
| 8 | Custom exceptions | 1-2h | Add exception classes |
| 9 | Memory bank | 30m | Update documentation |
| 10 | Final validation | 30m | Run full test suite |

______________________________________________________________________

## ⚡ Quick Commands

### Test & Validate

```bash
# Run all tests
python -m pytest -v

# Quick test run
python -m pytest -x  # Stop at first failure

# Type check
mypy src/ scripts/

# Lint check
ruff check src/ scripts/ tests/

# Coverage
python -m pytest --cov=src/portfolio_management --cov-report=term-missing

# Pre-commit
pre-commit run --all-files
```

### Find Issues

```bash
# Find specific ruff warnings
ruff check src/ --select F401  # Unused imports
ruff check src/ --select D100  # Missing docstrings
ruff check src/ --select C901  # Complexity
ruff check src/ --select TC001,TC003  # TYPE_CHECKING
ruff check src/ --select TRY003  # Long exception messages
ruff check src/ --select PGH004  # Blanket noqa

# Count warnings
ruff check src/ scripts/ tests/ | grep "Found"

# Find function complexity
ruff check src/ --select C901 --output-format=concise
```

### Git Operations

```bash
# Move files to archive
git mv FILENAME.md archive/phase3/

# Check status
git status

# Create checkpoint
git add .
git commit -m "cleanup(task-N): description"

# View changes
git diff
git diff --cached
```

______________________________________________________________________

## 🎨 Code Patterns

### Pattern 1: Module Docstring

```python
"""Brief one-line description of module.

Longer explanation of module purpose, main classes/functions,
and how it fits into the system architecture.
"""
```

### Pattern 2: TYPE_CHECKING Block

```python
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path
    from collections.abc import Sequence

def process(items: Sequence[Path]) -> None:
    pass
```

### Pattern 3: Custom Exception

```python
# In exceptions.py
class SpecificError(PortfolioManagementError):
    """Raised when specific condition occurs.

    This typically means... [explanation]
    """

    def __init__(self, context: str) -> None:
        self.context = context
        super().__init__(f"Error with {context}: detailed message")

# In calling code
raise SpecificError(problematic_value)
```

### Pattern 4: Specific noqa

```python
# Instead of:
# ruff: noqa

# Use:
# ruff: noqa: E402, F401  # Module imports, unused imports
```

### Pattern 5: Complexity Reduction

```python
# Before: One large function (CC=13)
def complex_function(args):
    # 50+ lines with nested conditions
    pass

# After: Orchestrator + helpers (CC≤10)
def main_function(args):
    """High-level orchestrator with clear stages."""
    state = _initialize_state()
    for item in items:
        if _should_skip(item, state):
            continue
        result = _process_item(item, state)
        state.update(result)
    return _finalize(state)

def _initialize_state() -> dict:
    """Initialize processing state."""
    pass

def _should_skip(item, state) -> bool:
    """Check if item should be skipped."""
    pass

def _process_item(item, state):
    """Process a single item."""
    pass

def _finalize(state):
    """Finalize processing and return results."""
    pass
```

______________________________________________________________________

## 🔍 Validation Checklist

After each task:

```bash
# 1. Tests still pass?
python -m pytest -v
# Expected: 171 passed

# 2. Mypy clean?
mypy src/ scripts/
# Expected: Success: no issues found

# 3. Progress on ruff?
ruff check src/ scripts/ tests/ | tail -1
# Expected: Decreasing error count

# 4. Git status clean?
git status
# Expected: Changes ready to commit
```

______________________________________________________________________

## 🎯 Success Metrics

| Metric | Before | Target | Check Command |
|--------|--------|--------|---------------|
| Root MD files | 18 | ≤6 | `ls -1 *.md \| wc -l` |
| Tests passing | 171 | 171 | `pytest -v` |
| Mypy errors | 0 | 0 | `mypy src/ scripts/` |
| Ruff warnings | 47 | ≤35 | `ruff check ... \| tail -1` |
| Pytest warnings | 5 | 0 | `pytest -v 2>&1 \| grep Warning` |
| Coverage | 86% | ≥85% | `pytest --cov=...` |

______________________________________________________________________

## 🚨 If Something Breaks

### Quick Rollback

```bash
# See what changed
git diff

# Undo unstaged changes
git checkout -- path/to/file

# Undo last commit (keep changes)
git reset --soft HEAD~1

# Undo last commit (discard changes)
git reset --hard HEAD~1  # CAREFUL!
```

### Debug Test Failure

```bash
# Run single test
python -m pytest tests/test_file.py::test_name -v

# Run with output
python -m pytest -v -s

# Run with debugger
python -m pytest --pdb
```

### Find What Broke

```bash
# Run tests until failure
python -m pytest -x

# Show local variables
python -m pytest --showlocals

# Increase verbosity
python -m pytest -vv
```

______________________________________________________________________

## 📁 Key File Locations

### Core Files

- `pyproject.toml` - Python project config
- `mypy.ini` - Type checker config
- `.pre-commit-config.yaml` - Pre-commit hooks

### Source Code

- `src/portfolio_management/` - Main package
- `scripts/` - CLI entry points
- `tests/` - Test suite

### Documentation

- `memory-bank/` - Persistent context
- `docs/` - Module documentation
- `archive/` - Historical documents

### Test Fixtures

- `tests/fixtures/` - Test data
- `config/` - Configuration files

______________________________________________________________________

## 💡 Pro Tips

1. **Commit often** - After each task or subtask
1. **Test early** - Don't accumulate untested changes
1. **Read the error** - Error messages are usually accurate
1. **Use git diff** - Review changes before committing
1. **Keep notes** - Document any deviations from plan
1. **Stay sequential** - Don't skip tasks (dependencies exist)
1. **Validate incrementally** - Run quick tests during work
1. **Check coverage** - Ensure refactoring doesn't lose tests

______________________________________________________________________

## 🔗 Related Documents

- `CLEANUP_PLAN_COMPREHENSIVE.md` - Full detailed plan
- `TECHNICAL_DEBT_REVIEW_2025-10-15.md` - Original assessment
- `CODE_REVIEW.md` - Code quality review
- `memory-bank/progress.md` - Project history
- `memory-bank/systemPatterns.md` - Architecture patterns

______________________________________________________________________

## ✅ Daily Checklist

**Morning:**

- \[ \] Read CLEANUP_PLAN_COMPREHENSIVE.md Task N
- \[ \] Review validation criteria
- \[ \] Check current git status
- \[ \] Run baseline tests

**During Work:**

- \[ \] Follow task actions step-by-step
- \[ \] Run validation after each subtask
- \[ \] Commit logical units of work
- \[ \] Update this checklist

**End of Session:**

- \[ \] Run full validation suite
- \[ \] Update task status in plan
- \[ \] Commit all work
- \[ \] Update memory bank if major milestone
- \[ \] Note any blockers or questions

______________________________________________________________________

**Quick Start:** Open `CLEANUP_PLAN_COMPREHENSIVE.md` and begin with Task 1.

**Questions?** Review the full plan's "Notes for Executing Agent" section.

**Good luck! 🚀**
