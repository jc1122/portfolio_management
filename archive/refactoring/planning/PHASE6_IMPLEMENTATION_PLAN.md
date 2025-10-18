# Phase 6: Reporting Package Refactoring - Implementation Plan

**Date:** October 18, 2025
**Status:** In Progress
**Previous Phase:** Phase 5 (Backtesting Package) ✅ Complete

## Objective

Refactor the monolithic `visualization.py` (400 lines) into a well-organized `reporting/` package with clear separation of concerns, maintainability, and backward compatibility.

## Current State

### Existing File Structure

```
src/portfolio_management/
├── visualization.py (400 lines - monolithic)
└── backtesting/ (Phase 5 complete)
```

### Functions in visualization.py

The file contains 10 functions organized by purpose:

**Equity & Performance (2 functions):**

- `prepare_equity_curve()` - Normalize equity curves for plotting
- `prepare_drawdown_series()` - Calculate drawdown percentages

**Allocation & Trading (3 functions):**

- `prepare_allocation_history()` - Stack area chart data for holdings
- `prepare_rolling_metrics()` - Rolling Sharpe, volatility, returns
- `prepare_transaction_costs_summary()` - Cost breakdown over time

**Distribution & Analysis (2 functions):**

- `prepare_returns_distribution()` - Histogram data
- `prepare_monthly_returns_heatmap()` - Monthly returns pivot table

**Comparison & Reports (3 functions):**

- `prepare_metrics_comparison()` - Multi-strategy comparison table
- `prepare_trade_analysis()` - Trade-level details
- `create_summary_report()` - Comprehensive report dictionary

### Dependencies

- `pandas` for data manipulation
- `portfolio_management.backtest` for `PerformanceMetrics`, `RebalanceEvent`

## Target Structure

### New Package Organization

```
src/portfolio_management/
├── reporting/
│   ├── __init__.py (clean public API)
│   └── visualization/
│       ├── __init__.py (exports all visualization functions)
│       ├── equity_curves.py (prepare_equity_curve)
│       ├── drawdowns.py (prepare_drawdown_series)
│       ├── allocations.py (prepare_allocation_history)
│       ├── metrics.py (prepare_rolling_metrics)
│       ├── costs.py (prepare_transaction_costs_summary)
│       ├── distributions.py (prepare_returns_distribution)
│       ├── heatmaps.py (prepare_monthly_returns_heatmap)
│       ├── comparison.py (prepare_metrics_comparison)
│       ├── trade_analysis.py (prepare_trade_analysis)
│       └── summary.py (create_summary_report)
└── visualization.py (37-line backward compatibility shim)
```

### Module Responsibilities

| Module | Lines | Functions | Responsibility |
|--------|-------|-----------|----------------|
| equity_curves.py | ~35 | 1 | Equity curve normalization |
| drawdowns.py | ~40 | 1 | Drawdown calculation |
| allocations.py | ~50 | 1 | Allocation history preparation |
| metrics.py | ~50 | 1 | Rolling performance metrics |
| costs.py | ~55 | 1 | Transaction cost summaries |
| distributions.py | ~35 | 1 | Returns distribution data |
| heatmaps.py | ~70 | 1 | Monthly returns heatmap |
| comparison.py | ~45 | 1 | Multi-strategy comparison |
| trade_analysis.py | ~50 | 1 | Trade-level analysis |
| summary.py | ~50 | 1 | Comprehensive reports |

**Total:** ~480 lines (vs. 400 original due to docstrings and structure)

## Implementation Steps

### Step 1: Create Directory Structure ✅

```bash
mkdir -p src/portfolio_management/reporting/visualization
touch src/portfolio_management/reporting/__init__.py
touch src/portfolio_management/reporting/visualization/__init__.py
```

### Step 2: Create Individual Visualization Modules

Split `visualization.py` into focused modules:

1. **equity_curves.py** - Extract `prepare_equity_curve()`
1. **drawdowns.py** - Extract `prepare_drawdown_series()`
1. **allocations.py** - Extract `prepare_allocation_history()`
1. **metrics.py** - Extract `prepare_rolling_metrics()`
1. **costs.py** - Extract `prepare_transaction_costs_summary()`
1. **distributions.py** - Extract `prepare_returns_distribution()`
1. **heatmaps.py** - Extract `prepare_monthly_returns_heatmap()`
1. **comparison.py** - Extract `prepare_metrics_comparison()`
1. **trade_analysis.py** - Extract `prepare_trade_analysis()`
1. **summary.py** - Extract `create_summary_report()`

Each module should:

- Have complete docstrings
- Import only what it needs
- Be independently testable
- Follow the same patterns as Phase 5

### Step 3: Create Public APIs

**reporting/visualization/__init__.py:**

```python
"""Visualization data preparation utilities for reporting."""

from .allocations import prepare_allocation_history
from .comparison import prepare_metrics_comparison
from .costs import prepare_transaction_costs_summary
from .distributions import prepare_returns_distribution
from .drawdowns import prepare_drawdown_series
from .equity_curves import prepare_equity_curve
from .heatmaps import prepare_monthly_returns_heatmap
from .metrics import prepare_rolling_metrics
from .summary import create_summary_report
from .trade_analysis import prepare_trade_analysis

__all__ = [
    "prepare_equity_curve",
    "prepare_drawdown_series",
    "prepare_allocation_history",
    "prepare_rolling_metrics",
    "prepare_transaction_costs_summary",
    "prepare_returns_distribution",
    "prepare_monthly_returns_heatmap",
    "prepare_metrics_comparison",
    "prepare_trade_analysis",
    "create_summary_report",
]
```

**reporting/__init__.py:**

```python
"""Reporting and visualization package."""

from .visualization import (
    create_summary_report,
    prepare_allocation_history,
    prepare_drawdown_series,
    prepare_equity_curve,
    prepare_metrics_comparison,
    prepare_monthly_returns_heatmap,
    prepare_returns_distribution,
    prepare_rolling_metrics,
    prepare_trade_analysis,
    prepare_transaction_costs_summary,
)

__all__ = [
    "prepare_equity_curve",
    "prepare_drawdown_series",
    "prepare_allocation_history",
    "prepare_rolling_metrics",
    "prepare_transaction_costs_summary",
    "prepare_returns_distribution",
    "prepare_monthly_returns_heatmap",
    "prepare_metrics_comparison",
    "prepare_trade_analysis",
    "create_summary_report",
]
```

### Step 4: Create Backward Compatibility Shim

**visualization.py (new):**

```python
"""Backward compatibility shim for visualization module.

This module has been refactored into portfolio_management.reporting.visualization.
All imports are forwarded to the new location for backward compatibility.

Deprecated: Import from portfolio_management.reporting.visualization instead.
"""

from portfolio_management.reporting.visualization import (
    create_summary_report,
    prepare_allocation_history,
    prepare_drawdown_series,
    prepare_equity_curve,
    prepare_metrics_comparison,
    prepare_monthly_returns_heatmap,
    prepare_returns_distribution,
    prepare_rolling_metrics,
    prepare_trade_analysis,
    prepare_transaction_costs_summary,
)

__all__ = [
    "prepare_equity_curve",
    "prepare_drawdown_series",
    "prepare_allocation_history",
    "prepare_rolling_metrics",
    "prepare_transaction_costs_summary",
    "prepare_returns_distribution",
    "prepare_monthly_returns_heatmap",
    "prepare_metrics_comparison",
    "prepare_trade_analysis",
    "create_summary_report",
]
```

### Step 5: Validation

**Tests to Run:**

```bash
# All tests should pass
pytest tests/reporting/test_visualization.py -v

# Full test suite
pytest tests/ -v

# Type checking
mypy src/portfolio_management/reporting/
```

**Expected Results:**

- ✅ All 231 tests pass (100%)
- ✅ Zero mypy errors
- ✅ Backward compatibility preserved
- ✅ Old imports work: `from portfolio_management.visualization import prepare_equity_curve`
- ✅ New imports work: `from portfolio_management.reporting.visualization import prepare_equity_curve`

## Quality Gates

| Metric | Target | Status |
|--------|--------|--------|
| Tests Passing | 231 (100%) | ⏳ Pending |
| Mypy Errors | 0 | ⏳ Pending |
| Backward Compatibility | 100% | ⏳ Pending |
| Code Organization | Excellent | ⏳ Pending |
| Module Count | 10 modules + 2 __init__.py | ⏳ Pending |

## Benefits

1. **Clear Organization** - Each function in its own focused module
1. **Easy Navigation** - Find visualization code by purpose
1. **Better Testability** - Test modules independently
1. **Maintainability** - Update one module without affecting others
1. **Scalability** - Easy to add new visualization types
1. **Backward Compatible** - No breaking changes for existing code

## Timeline

**Estimated Duration:** 2-3 hours

- **Step 1:** Directory structure - 5 minutes
- **Step 2:** Create 10 modules - 60-90 minutes
- **Step 3:** Create public APIs - 15 minutes
- **Step 4:** Backward compatibility shim - 10 minutes
- **Step 5:** Testing and validation - 30-45 minutes

## Next Steps After Phase 6

**Phase 7:** Scripts update (if needed)

- Update any scripts that use visualization
- Ensure all CLI tools work with new structure

**Phase 8:** Documentation cleanup

- Update README
- Create reporting documentation
- Archive old docs if needed

## Success Criteria

✅ All 10 visualization functions moved to separate modules
✅ Clean public API through `__init__.py` files
✅ Backward compatibility maintained (old imports work)
✅ All 231 tests pass (100%)
✅ Zero mypy errors
✅ Code organization improved
✅ Ready for Phase 7

______________________________________________________________________

**Status:** Ready to begin implementation
**Next Action:** Create directory structure and start module extraction
