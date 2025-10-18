# Modular Monolith Refactoring Plan

**Date:** October 18, 2025
**Version:** 1.0
**Status:** Planning Phase

## Executive Summary

This document outlines a comprehensive plan to refactor the portfolio management toolkit from a flat module structure into a **modular monolith architecture** with clear package boundaries, explicit dependencies, and separation of concerns. The refactoring aims to improve maintainability, testability, and scalability while preserving all existing functionality.

## Current State Analysis

### Existing Structure

```
src/portfolio_management/
├── __init__.py (empty)
├── analysis.py (price file analysis, currency inference)
├── backtest.py (backtesting engine)
├── classification.py (asset classification)
├── config.py (constants and configuration)
├── exceptions.py (custom exception hierarchy)
├── io.py (CSV I/O operations)
├── matching.py (symbol matching)
├── models.py (data models)
├── portfolio.py (portfolio construction)
├── returns.py (return calculation)
├── selection.py (asset selection)
├── stooq.py (Stooq data indexing)
├── universes.py (universe management)
├── utils.py (utilities)
├── visualization.py (chart data preparation)
├── core/ (empty)
├── data/ (empty)
├── backtesting/ (empty)
├── portfolio_construction/
│   ├── filters/ (empty)
│   └── strategies/ (empty)
├── universes_management/ (empty)
├── visualization_and_reporting/ (empty)
└── data_management/ (empty)
```

### Problems with Current Structure

1. **Flat organization** - All modules at the same level, no clear hierarchy
1. **Unclear boundaries** - Difficult to understand module relationships
1. **Hidden dependencies** - Import statements scattered throughout code
1. **Poor encapsulation** - No distinction between public API and implementation details
1. **Hard to navigate** - 15+ modules in a single directory
1. **Coupling issues** - Circular or unnecessary dependencies not immediately visible
1. **Testing challenges** - No clear test organization matching code structure

### Current Dependency Analysis

**Dependency Layers (simplified):**

- **Layer 0 (Foundation):** exceptions, config, utils, models
- **Layer 1 (Data):** stooq, io, matching, analysis
- **Layer 2 (Assets):** selection → classification → universes
- **Layer 3 (Analytics):** returns
- **Layer 4 (Portfolio):** portfolio → backtest
- **Layer 5 (Reporting):** visualization

## Target Architecture: Modular Monolith

### Design Principles

1. **Package Autonomy** - Each package has clear boundaries and responsibilities
1. **Explicit Dependencies** - Packages depend on well-defined interfaces
1. **Unidirectional Flow** - Dependencies flow in one direction (toward stable abstractions)
1. **High Cohesion** - Related functionality grouped together
1. **Low Coupling** - Minimal dependencies between packages
1. **Public APIs** - Each package exposes a clean API through `__init__.py`
1. **Information Hiding** - Implementation details remain internal

### Target Package Structure

```
src/portfolio_management/
├── __init__.py (root package exports)
│
├── core/ (Foundation Layer)
│   ├── __init__.py (exports: exceptions, config types, utilities)
│   ├── exceptions.py (custom exception hierarchy)
│   ├── config.py (constants, configuration)
│   ├── utils.py (parallel processing, timing)
│   └── types.py (common protocols, type aliases)
│
├── data/ (Data Management Layer)
│   ├── __init__.py (exports: public data API)
│   ├── models.py (StooqFile, TradeableInstrument, etc.)
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── stooq.py (index building)
│   │   └── loaders.py (price file loading)
│   ├── io/
│   │   ├── __init__.py
│   │   ├── readers.py (CSV reading)
│   │   ├── writers.py (CSV writing)
│   │   └── exporters.py (price export)
│   ├── matching/
│   │   ├── __init__.py
│   │   ├── matchers.py (symbol matching)
│   │   └── strategies.py (matching strategies)
│   └── analysis/
│       ├── __init__.py
│       ├── quality.py (data quality checks)
│       └── currency.py (currency inference)
│
├── assets/ (Asset Universe Layer)
│   ├── __init__.py (exports: selection, classification, universe APIs)
│   ├── selection/
│   │   ├── __init__.py
│   │   ├── criteria.py (FilterCriteria)
│   │   ├── selector.py (AssetSelector)
│   │   └── models.py (SelectedAsset)
│   ├── classification/
│   │   ├── __init__.py
│   │   ├── classifier.py (AssetClassifier)
│   │   ├── taxonomy.py (AssetClass, Geography, SubClass)
│   │   ├── overrides.py (ClassificationOverrides)
│   │   └── models.py (AssetClassification)
│   └── universes/
│       ├── __init__.py
│       ├── definition.py (UniverseDefinition)
│       ├── loader.py (UniverseConfigLoader)
│       └── manager.py (UniverseManager)
│
├── analytics/ (Financial Calculations Layer)
│   ├── __init__.py (exports: returns, metrics APIs)
│   ├── returns/
│   │   ├── __init__.py
│   │   ├── calculator.py (ReturnCalculator)
│   │   ├── config.py (ReturnConfig)
│   │   ├── loaders.py (PriceLoader)
│   │   └── models.py (ReturnSummary)
│   └── metrics/
│       ├── __init__.py
│       ├── performance.py (Sharpe, Sortino, etc.)
│       └── risk.py (volatility, drawdown)
│
├── portfolio/ (Portfolio Construction Layer)
│   ├── __init__.py (exports: Portfolio, strategies, constraints)
│   ├── models.py (Portfolio, StrategyType)
│   ├── builder.py (portfolio construction orchestration)
│   ├── strategies/
│   │   ├── __init__.py
│   │   ├── base.py (PortfolioStrategy ABC)
│   │   ├── equal_weight.py (EqualWeightStrategy)
│   │   ├── risk_parity.py (RiskParityStrategy)
│   │   └── mean_variance.py (MeanVarianceStrategy)
│   ├── constraints/
│   │   ├── __init__.py
│   │   ├── models.py (PortfolioConstraints)
│   │   └── validators.py (constraint validation)
│   └── rebalancing/
│       ├── __init__.py
│       ├── config.py (RebalanceConfig)
│       └── logic.py (rebalancing algorithms)
│
├── backtesting/ (Historical Simulation Layer)
│   ├── __init__.py (exports: BacktestEngine, config, results)
│   ├── models.py (BacktestConfig, BacktestResult)
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── backtest.py (BacktestEngine)
│   │   └── simulator.py (portfolio evolution)
│   ├── transactions/
│   │   ├── __init__.py
│   │   ├── costs.py (commission, slippage)
│   │   └── execution.py (trade execution)
│   ├── rebalancing/
│   │   ├── __init__.py
│   │   ├── triggers.py (RebalanceTrigger, frequency)
│   │   └── events.py (RebalanceEvent)
│   └── performance/
│       ├── __init__.py
│       ├── metrics.py (PerformanceMetrics)
│       └── analytics.py (analysis utilities)
│
└── reporting/ (Visualization & Reporting Layer)
    ├── __init__.py (exports: visualization, report APIs)
    ├── visualization/
    │   ├── __init__.py
    │   ├── equity_curves.py
    │   ├── drawdowns.py
    │   ├── allocations.py
    │   ├── distributions.py
    │   └── heatmaps.py
    ├── reports/
    │   ├── __init__.py
    │   ├── summary.py
    │   ├── comparison.py
    │   └── trade_analysis.py
    └── exporters/
        ├── __init__.py
        ├── csv.py
        ├── json.py
        └── html.py
```

### Package Dependency Rules

**Allowed Dependencies (packages can only depend on those listed):**

| Package      | Can Depend On                    |
|--------------|----------------------------------|
| core         | (none - foundation layer)        |
| data         | core                             |
| assets       | core, data                       |
| analytics    | core, assets                     |
| portfolio    | core, analytics                  |
| backtesting  | core, portfolio, analytics       |
| reporting    | core, backtesting, portfolio, analytics |

**Dependency Diagram:**

```
         reporting
            ↓
      backtesting
            ↓
        portfolio
            ↓
       analytics
            ↓
         assets
            ↓
          data
            ↓
          core
```

### Public API Design

Each package exposes a clean public API through its `__init__.py`:

#### Example: `assets/__init__.py`

```python
"""Asset selection, classification, and universe management."""

from .selection import FilterCriteria, SelectedAsset, AssetSelector
from .classification import (
    AssetClass,
    Geography,
    SubClass,
    AssetClassification,
    AssetClassifier,
)
from .universes import UniverseDefinition, UniverseConfigLoader, UniverseManager

__all__ = [
    # Selection
    "FilterCriteria",
    "SelectedAsset",
    "AssetSelector",
    # Classification
    "AssetClass",
    "Geography",
    "SubClass",
    "AssetClassification",
    "AssetClassifier",
    # Universes
    "UniverseDefinition",
    "UniverseConfigLoader",
    "UniverseManager",
]
```

#### Example: Script Import Pattern

```python
# Before (flat structure)
from src.portfolio_management.selection import FilterCriteria, AssetSelector
from src.portfolio_management.classification import AssetClassifier

# After (modular structure)
from portfolio_management.assets import FilterCriteria, AssetSelector, AssetClassifier
```

## Migration Strategy

### Phase-by-Phase Approach

#### Phase 0: Preparation (1-2 hours)

- ✅ Analyze current structure and dependencies
- ✅ Create this refactoring plan document
- ✅ Get stakeholder approval
- Create feature branch: `refactor/modular-monolith`
- Ensure all tests pass before starting
- Create backup/tag of current state

#### Phase 1: Core Package (2-3 hours)

**Goal:** Establish foundation layer

**Tasks:**

1. Create `core/` package structure
1. Move `exceptions.py` → `core/exceptions.py`
1. Move `config.py` → `core/config.py`
1. Move `utils.py` → `core/utils.py`
1. Create `core/types.py` for common protocols
1. Create `core/__init__.py` with public API
1. Update all imports to use `portfolio_management.core`
1. Run tests, fix any issues

**Testing:**

- All exception imports work correctly
- Config constants accessible
- Utility functions operate as before
- No broken imports in any module

#### Phase 2: Data Package (4-6 hours)

**Goal:** Organize data management layer

**Tasks:**

1. Create `data/` package with subpackages
1. Keep `models.py` in `data/` (StooqFile, TradeableInstrument, etc.)
1. Move `stooq.py` → `data/ingestion/stooq.py`
1. Split `io.py`:
   - Readers → `data/io/readers.py`
   - Writers → `data/io/writers.py`
   - Exporters → `data/io/exporters.py`
1. Move `matching.py` → `data/matching/matchers.py`
1. Split `analysis.py`:
   - Quality checks → `data/analysis/quality.py`
   - Currency logic → `data/analysis/currency.py`
1. Create `__init__.py` files with public APIs
1. Update imports in other modules
1. Run tests, fix any issues

**Testing:**

- Data loading works correctly
- Stooq indexing functional
- Symbol matching operational
- I/O operations unchanged
- Integration test: `test_prepare_tradeable_data.py`

#### Phase 3: Assets Package (4-6 hours)

**Goal:** Organize asset universe layer

**Tasks:**

1. Create `assets/` package with subpackages
1. Reorganize `selection.py`:
   - FilterCriteria → `assets/selection/criteria.py`
   - SelectedAsset → `assets/selection/models.py`
   - AssetSelector → `assets/selection/selector.py`
1. Reorganize `classification.py`:
   - Enums → `assets/classification/taxonomy.py`
   - AssetClassification → `assets/classification/models.py`
   - AssetClassifier → `assets/classification/classifier.py`
   - ClassificationOverrides → `assets/classification/overrides.py`
1. Reorganize `universes.py`:
   - UniverseDefinition → `assets/universes/definition.py`
   - UniverseConfigLoader → `assets/universes/loader.py`
   - UniverseManager → `assets/universes/manager.py` (if exists)
1. Create `__init__.py` files with public APIs
1. Update imports throughout codebase
1. Run tests, fix any issues

**Testing:**

- Asset selection works
- Classification operational
- Universe loading functional
- Test files: `test_selection.py`, `test_classification.py`, `test_universes.py`

#### Phase 4: Analytics Package (3-4 hours)

**Goal:** Organize financial calculations

**Tasks:**

1. Create `analytics/` package with subpackages
1. Reorganize `returns.py`:
   - ReturnConfig → `analytics/returns/config.py`
   - PriceLoader → `analytics/returns/loaders.py`
   - ReturnCalculator → `analytics/returns/calculator.py`
   - ReturnSummary → `analytics/returns/models.py`
1. Extract metrics from `backtest.py` if applicable:
   - Performance metrics → `analytics/metrics/performance.py`
   - Risk metrics → `analytics/metrics/risk.py`
1. Create `__init__.py` files with public APIs
1. Update imports
1. Run tests, fix any issues

**Testing:**

- Return calculation works
- Metrics computation correct
- Test file: `test_returns.py`
- Script test: `test_calculate_returns.py`

#### Phase 5: Portfolio Package (4-6 hours)

**Goal:** Organize portfolio construction layer

**Tasks:**

1. Create `portfolio/` package with subpackages
1. Reorganize `portfolio.py`:
   - Portfolio, StrategyType → `portfolio/models.py`
   - PortfolioStrategy ABC → `portfolio/strategies/base.py`
   - Specific strategies → `portfolio/strategies/equal_weight.py`, etc.
   - PortfolioConstraints → `portfolio/constraints/models.py`
   - RebalanceConfig → `portfolio/rebalancing/config.py`
   - Orchestration → `portfolio/builder.py`
1. Move existing `filters/` and `strategies/` content if any
1. Create `__init__.py` files with public APIs
1. Update imports
1. Run tests, fix any issues

**Testing:**

- Portfolio construction works
- All strategies operational
- Constraint validation works
- Test file: `test_portfolio.py`
- Script test: `test_construct_portfolio.py`

#### Phase 6: Backtesting Package (4-6 hours)

**Goal:** Organize historical simulation layer

**Tasks:**

1. Create `backtesting/` package with subpackages
1. Reorganize `backtest.py`:
   - BacktestConfig → `backtesting/models.py`
   - BacktestEngine → `backtesting/engine/backtest.py`
   - Transaction costs → `backtesting/transactions/costs.py`
   - Rebalancing events → `backtesting/rebalancing/events.py`
   - Performance metrics → `backtesting/performance/metrics.py`
1. Create `__init__.py` files with public APIs
1. Update imports
1. Run tests, fix any issues

**Testing:**

- Backtest engine works
- Transaction costs calculated correctly
- Performance metrics accurate
- Test file: `test_backtest.py`
- Integration test: `test_full_pipeline.py`

#### Phase 7: Reporting Package (3-4 hours)

**Goal:** Organize visualization and reporting layer

**Tasks:**

1. Create `reporting/` package with subpackages
1. Reorganize `visualization.py`:
   - Equity curves → `reporting/visualization/equity_curves.py`
   - Drawdowns → `reporting/visualization/drawdowns.py`
   - Allocations → `reporting/visualization/allocations.py`
   - Distributions → `reporting/visualization/distributions.py`
   - Heatmaps → `reporting/visualization/heatmaps.py`
1. Add report generation if needed:
   - Summary → `reporting/reports/summary.py`
   - Comparison → `reporting/reports/comparison.py`
   - Trade analysis → `reporting/reports/trade_analysis.py`
1. Create `__init__.py` files with public APIs
1. Update imports
1. Run tests, fix any issues

**Testing:**

- All visualization functions work
- Chart data prepared correctly
- Test file: `test_visualization.py`

#### Phase 8: Scripts Update (2-3 hours)

**Goal:** Update all CLI scripts to use new structure

**Tasks:**

1. Update `scripts/prepare_tradeable_data.py`
1. Update `scripts/select_assets.py`
1. Update `scripts/classify_assets.py`
1. Update `scripts/calculate_returns.py`
1. Update `scripts/manage_universes.py`
1. Update `scripts/construct_portfolio.py`
1. Update `scripts/run_backtest.py`
1. Run all script tests
1. Test scripts manually end-to-end

**Testing:**

- All script imports work
- CLI functionality unchanged
- Integration tests pass
- Test directory: `tests/scripts/`

#### Phase 9: Test Reorganization (3-4 hours)

**Goal:** Align test structure with new package structure

**Tasks:**

1. Create new test structure:
   ```
   tests/
   ├── unit/
   │   ├── core/
   │   ├── data/
   │   ├── assets/
   │   ├── analytics/
   │   ├── portfolio/
   │   ├── backtesting/
   │   └── reporting/
   ├── integration/
   ├── scripts/
   └── fixtures/
   ```
1. Move existing tests to appropriate locations
1. Update test imports
1. Add package-level `conftest.py` files
1. Run full test suite
1. Ensure 100% test pass rate

#### Phase 10: Documentation & Cleanup (2-3 hours)

**Goal:** Update documentation and clean up old files

**Tasks:**

1. Update `README.md` with new structure
1. Create `docs/architecture/modular_monolith.md`
1. Update `docs/` with new import patterns
1. Create migration guide: `MIGRATION_GUIDE.md`
1. Update `pyproject.toml` linting rules
1. Remove old empty directories
1. Update developer documentation
1. Create architecture diagram
1. Final code review
1. Merge to main branch

### Backward Compatibility Strategy

To maintain backward compatibility during transition, we can add compatibility shims:

#### Root `__init__.py` Compatibility Layer

```python
"""Portfolio management toolkit package.

Modern modular structure with backward compatibility.
"""

import warnings

# Modern exports (new structure)
from .core import *  # noqa: F401, F403
from .data import *  # noqa: F401, F403
from .assets import *  # noqa: F401, F403
from .analytics import *  # noqa: F401, F403
from .portfolio import *  # noqa: F401, F403
from .backtesting import *  # noqa: F401, F403
from .reporting import *  # noqa: F401, F403

# Backward compatibility (deprecated)
def _create_backward_compatibility_warning(old_import: str, new_import: str):
    def deprecated_import(*args, **kwargs):
        warnings.warn(
            f"Importing from '{old_import}' is deprecated. "
            f"Use '{new_import}' instead.",
            DeprecationWarning,
            stacklevel=2
        )
    return deprecated_import

# This can be expanded as needed during migration
```

**Deprecation Timeline:**

- **Version 1.0** (current): Old imports work, deprecation warnings
- **Version 2.0** (3 months): Old imports still work, louder warnings
- **Version 3.0** (6 months): Remove backward compatibility, new structure only

## Testing Strategy

### Test Coverage Requirements

- Maintain current test coverage (>80%)
- Each phase must pass all existing tests before proceeding
- Add new tests for package boundaries and APIs
- Integration tests must pass after each major phase

### Test Organization

**New test structure mirrors package structure:**

```
tests/
├── unit/
│   ├── core/
│   │   ├── test_exceptions.py
│   │   ├── test_config.py
│   │   └── test_utils.py
│   ├── data/
│   │   ├── ingestion/
│   │   │   └── test_stooq.py
│   │   ├── io/
│   │   │   ├── test_readers.py
│   │   │   ├── test_writers.py
│   │   │   └── test_exporters.py
│   │   ├── matching/
│   │   │   └── test_matchers.py
│   │   └── analysis/
│   │       ├── test_quality.py
│   │       └── test_currency.py
│   ├── assets/
│   │   ├── selection/
│   │   │   └── test_selector.py
│   │   ├── classification/
│   │   │   └── test_classifier.py
│   │   └── universes/
│   │       └── test_loader.py
│   ├── analytics/
│   │   └── returns/
│   │       └── test_calculator.py
│   ├── portfolio/
│   │   ├── strategies/
│   │   │   ├── test_equal_weight.py
│   │   │   ├── test_risk_parity.py
│   │   │   └── test_mean_variance.py
│   │   └── test_builder.py
│   ├── backtesting/
│   │   ├── engine/
│   │   │   └── test_backtest.py
│   │   └── performance/
│   │       └── test_metrics.py
│   └── reporting/
│       └── visualization/
│           └── test_visualizations.py
├── integration/
│   ├── test_full_pipeline.py
│   ├── test_data_to_portfolio.py
│   ├── test_portfolio_to_backtest.py
│   └── test_production_data.py
├── scripts/
│   ├── test_prepare_tradeable_data.py
│   ├── test_calculate_returns.py
│   └── test_construct_portfolio.py
├── conftest.py
└── fixtures/
```

### Testing Checkpoints

After each phase:

1. Run unit tests: `pytest tests/unit/`
1. Run integration tests: `pytest tests/integration/`
1. Run script tests: `pytest tests/scripts/`
1. Check coverage: `pytest --cov=portfolio_management --cov-report=html`
1. Manual smoke tests of key workflows

## Risk Mitigation

### Potential Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Breaking existing functionality | High | Medium | Phased approach, test after each phase |
| Circular dependencies | Medium | Low | Clear dependency rules, detect early |
| Performance degradation | Low | Low | Benchmark before/after |
| Test failures | High | Medium | Fix immediately, don't proceed |
| Import confusion | Medium | Medium | Clear documentation, backward compatibility |
| Developer friction | Medium | Low | Good documentation, training session |

### Rollback Plan

If critical issues arise:

1. Revert to feature branch checkpoint
1. Fix issues in isolated branch
1. Re-run full test suite
1. Restart from last successful phase

### Success Criteria

- ✅ All tests pass (100% of previous passing tests)
- ✅ Test coverage maintained or improved
- ✅ All scripts functional
- ✅ No performance degradation (benchmark key operations)
- ✅ Documentation updated
- ✅ Code review approved
- ✅ Integration tests pass
- ✅ Manual end-to-end testing successful

## Benefits & Expected Outcomes

### Immediate Benefits

1. **Clearer Architecture** - Package structure immediately communicates system design
1. **Better Navigation** - Developers can find code faster
1. **Improved Testing** - Tests organized by package
1. **Explicit Dependencies** - Import statements show relationships clearly
1. **Better Encapsulation** - Internal details hidden from external packages

### Long-term Benefits

1. **Easier Onboarding** - New developers understand structure faster
1. **Reduced Coupling** - Packages can evolve independently
1. **Better Maintainability** - Changes localized to specific packages
1. **Facilitates Growth** - Easy to add new packages/features
1. **Testing Improvements** - Mock boundaries more easily
1. **Potential Microservices** - Could extract packages as services if needed
1. **Code Quality** - Enforced boundaries prevent shortcuts
1. **Documentation** - Package-level docs more natural

### Metrics to Track

**Before Refactoring:**

- Number of modules: 15+
- Average module size: ~500 lines
- Import depth: varies
- Circular dependencies: TBD
- Test organization: flat

**After Refactoring:**

- Number of packages: 7
- Average package size: 3-5 modules
- Import depth: clear hierarchy
- Circular dependencies: 0 (enforced)
- Test organization: mirrors code

## Configuration Updates

### pyproject.toml

Update paths for linting exclusions:

```toml
[tool.ruff.lint.per-file-ignores]
"src/portfolio_management/core/*.py" = [...]
"src/portfolio_management/data/**/*.py" = [...]
"src/portfolio_management/assets/**/*.py" = [...]
# ... etc
```

### pytest.ini

Already configured correctly:

```ini
[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

### mypy.ini

May need package-specific configurations:

```ini
[mypy]
python_version = 3.10
warn_return_any = True
warn_unused_configs = True

[mypy-portfolio_management.core.*]
# Core-specific settings

[mypy-portfolio_management.data.*]
# Data-specific settings
```

## Timeline Estimate

| Phase | Estimated Time | Dependencies |
|-------|----------------|--------------|
| Phase 0: Preparation | 1-2 hours | - |
| Phase 1: Core | 2-3 hours | Phase 0 |
| Phase 2: Data | 4-6 hours | Phase 1 |
| Phase 3: Assets | 4-6 hours | Phases 1-2 |
| Phase 4: Analytics | 3-4 hours | Phases 1-3 |
| Phase 5: Portfolio | 4-6 hours | Phases 1-4 |
| Phase 6: Backtesting | 4-6 hours | Phases 1-5 |
| Phase 7: Reporting | 3-4 hours | Phases 1-6 |
| Phase 8: Scripts | 2-3 hours | Phases 1-7 |
| Phase 9: Tests | 3-4 hours | Phases 1-8 |
| Phase 10: Documentation | 2-3 hours | Phases 1-9 |
| **Total** | **32-47 hours** | **(4-6 working days)** |

**Recommended Approach:**

- Work in focused 3-4 hour blocks
- Complete 1-2 phases per day
- Run full test suite between phases
- Don't rush - quality over speed

## Next Steps

1. **Review & Approval** - Get team approval for this plan
1. **Create Feature Branch** - `git checkout -b refactor/modular-monolith`
1. **Baseline Tests** - Ensure all tests pass before starting
1. **Begin Phase 1** - Start with core package migration
1. **Track Progress** - Update this document as phases complete
1. **Regular Check-ins** - Review progress daily
1. **Final Review** - Code review before merge

## References

### Related Documents

- `README.md` - Current project documentation
- `PHASE5_IMPLEMENTATION_PLAN.md` - Previous implementation plans
- `CODE_REVIEW.md` - Existing code review notes
- `TECHNICAL_DEBT_REVIEW_2025-10-15.md` - Technical debt analysis

### Architecture Patterns

- **Modular Monolith**: Single deployment, multiple modules with clear boundaries
- **Layered Architecture**: Dependencies flow from top (UI/reporting) to bottom (core/data)
- **Package by Feature**: Related functionality grouped by domain
- **Clean Architecture**: Dependency inversion, stable abstractions

### Inspiration

- Domain-Driven Design (DDD) - Bounded contexts as packages
- Hexagonal Architecture - Clear boundaries and adapters
- Package Principles (Robert C. Martin) - REP, CCP, CRP

______________________________________________________________________

## Appendix A: Module Mapping

### Complete File Mapping

| Current File | New Location | Notes |
|--------------|--------------|-------|
| `exceptions.py` | `core/exceptions.py` | No changes to content |
| `config.py` | `core/config.py` | No changes to content |
| `utils.py` | `core/utils.py` | No changes to content |
| `models.py` | `data/models.py` | Data-specific models only |
| `stooq.py` | `data/ingestion/stooq.py` | Index building logic |
| `io.py` | `data/io/readers.py`<br>`data/io/writers.py`<br>`data/io/exporters.py` | Split by responsibility |
| `matching.py` | `data/matching/matchers.py` | Symbol matching logic |
| `analysis.py` | `data/analysis/quality.py`<br>`data/analysis/currency.py` | Split by domain |
| `selection.py` | `assets/selection/criteria.py`<br>`assets/selection/selector.py`<br>`assets/selection/models.py` | Split by concern |
| `classification.py` | `assets/classification/classifier.py`<br>`assets/classification/taxonomy.py`<br>`assets/classification/overrides.py`<br>`assets/classification/models.py` | Split by concern |
| `universes.py` | `assets/universes/definition.py`<br>`assets/universes/loader.py`<br>`assets/universes/manager.py` | Split by concern |
| `returns.py` | `analytics/returns/calculator.py`<br>`analytics/returns/config.py`<br>`analytics/returns/loaders.py`<br>`analytics/returns/models.py` | Split by concern |
| `portfolio.py` | `portfolio/models.py`<br>`portfolio/builder.py`<br>`portfolio/strategies/base.py`<br>`portfolio/strategies/equal_weight.py`<br>`portfolio/strategies/risk_parity.py`<br>`portfolio/strategies/mean_variance.py`<br>`portfolio/constraints/models.py`<br>`portfolio/rebalancing/config.py` | Split by strategy and concern |
| `backtest.py` | `backtesting/models.py`<br>`backtesting/engine/backtest.py`<br>`backtesting/transactions/costs.py`<br>`backtesting/rebalancing/events.py`<br>`backtesting/performance/metrics.py` | Split by component |
| `visualization.py` | `reporting/visualization/equity_curves.py`<br>`reporting/visualization/drawdowns.py`<br>`reporting/visualization/allocations.py`<br>`reporting/visualization/distributions.py`<br>`reporting/visualization/heatmaps.py` | Split by chart type |

### Import Transformation Examples

#### Before: Flat Structure

```python
from src.portfolio_management.selection import FilterCriteria, AssetSelector
from src.portfolio_management.classification import AssetClassifier
from src.portfolio_management.returns import ReturnCalculator
from src.portfolio_management.portfolio import Portfolio
from src.portfolio_management.backtest import BacktestEngine
```

#### After: Modular Structure

```python
from portfolio_management.assets import FilterCriteria, AssetSelector, AssetClassifier
from portfolio_management.analytics import ReturnCalculator
from portfolio_management.portfolio import Portfolio
from portfolio_management.backtesting import BacktestEngine
```

## Appendix B: Example Package Implementation

### Example: assets/selection/__init__.py

```python
"""Asset selection and filtering functionality.

This subpackage provides tools for selecting assets from the tradeable
universe based on quality, history, and user-defined criteria.

Public API:
    - FilterCriteria: Configuration for asset filtering
    - SelectedAsset: Data model for selected assets
    - AssetSelector: Main selection engine

Example:
    >>> from portfolio_management.assets import FilterCriteria, AssetSelector
    >>> criteria = FilterCriteria.default()
    >>> selector = AssetSelector()
    >>> selected = selector.filter(assets, criteria)
"""

from .criteria import FilterCriteria
from .models import SelectedAsset
from .selector import AssetSelector

__all__ = [
    "FilterCriteria",
    "SelectedAsset",
    "AssetSelector",
]
```

### Example: assets/__init__.py

```python
"""Asset universe management package.

This package provides comprehensive tools for asset selection, classification,
and universe management for portfolio construction.

Subpackages:
    - selection: Asset filtering and selection
    - classification: Asset taxonomy and classification
    - universes: Universe definition and management

Public API:
    Selection:
        - FilterCriteria
        - SelectedAsset
        - AssetSelector

    Classification:
        - AssetClass, Geography, SubClass (enums)
        - AssetClassification
        - AssetClassifier

    Universes:
        - UniverseDefinition
        - UniverseConfigLoader
        - UniverseManager

Example:
    >>> from portfolio_management.assets import (
    ...     FilterCriteria,
    ...     AssetSelector,
    ...     AssetClassifier,
    ...     UniverseConfigLoader
    ... )
    >>> criteria = FilterCriteria.default()
    >>> selector = AssetSelector()
    >>> classifier = AssetClassifier()
"""

# Selection API
from .selection import (
    FilterCriteria,
    SelectedAsset,
    AssetSelector,
)

# Classification API
from .classification import (
    AssetClass,
    Geography,
    SubClass,
    AssetClassification,
    AssetClassifier,
)

# Universes API
from .universes import (
    UniverseDefinition,
    UniverseConfigLoader,
    UniverseManager,
)

__all__ = [
    # Selection
    "FilterCriteria",
    "SelectedAsset",
    "AssetSelector",
    # Classification
    "AssetClass",
    "Geography",
    "SubClass",
    "AssetClassification",
    "AssetClassifier",
    # Universes
    "UniverseDefinition",
    "UniverseConfigLoader",
    "UniverseManager",
]
```

______________________________________________________________________

**Document Prepared By:** GitHub Copilot
**Date:** October 18, 2025
**Status:** Ready for Review and Implementation
