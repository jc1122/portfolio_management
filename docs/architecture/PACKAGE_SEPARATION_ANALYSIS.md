# Package Separation & Workflow Analysis

**Date:** October 25, 2025
**Purpose:** Analyze current architecture for separation of concerns and recommend package improvements

______________________________________________________________________

## Current Package Structure

```
src/portfolio_management/
├── core/              # Foundation (exceptions, config, types, utilities)
├── data/              # Data management (I/O, ingestion, matching, analysis)
├── assets/            # Asset universe (selection, classification, universes)
├── analytics/         # Financial analytics (returns, metrics, indicators)
├── macro/             # Macroeconomic signals & regime detection
├── portfolio/         # Portfolio construction (strategies, constraints, membership)
├── backtesting/       # Backtesting engine (simulation, transactions, performance)
├── reporting/         # Visualization & reporting
├── config/            # Configuration management
└── utils/             # General utilities
```

______________________________________________________________________

## Workflow Stages & Package Mapping

### Current State Analysis

| Workflow Stage | Current Package | Concerns | Coupling Issues |
|----------------|----------------|----------|-----------------|
| **Data Preparation** | `data.ingestion` | Data loading, matching, validation | ✅ Low coupling |
| **Asset Selection** | `assets.selection` | Filtering by liquidity, price, market cap | ⚠️ Depends on data, analytics |
| **Asset Classification** | `assets.classification` | Geographic & type classification | ✅ Low coupling |
| **Return Calculation** | `analytics.returns` | Log/simple returns, alignment | ⚠️ Depends on data |
| **Universe Management** | `assets.universes` | YAML config, orchestration | ⚠️ Orchestrates multiple packages |
| **Portfolio Construction** | `portfolio.strategies` | Optimization strategies | ⚠️ Depends on analytics, assets |
| **Backtesting** | `backtesting.engine` | Simulation, rebalancing | ⚠️ Depends on portfolio, analytics |
| **Performance Analytics** | `backtesting.performance` | Metrics calculation | ⚠️ Mixed with backtesting |
| **Visualization** | `reporting.visualization` | Chart generation | ✅ Low coupling |

______________________________________________________________________

## Separation of Concerns Issues

### Issue 1: Analytics Split Across Packages

**Problem:** Analytics functionality is divided between `analytics/` and `backtesting.performance/`

**Current State:**

- `analytics/returns/` - Return calculation
- `analytics/metrics/` - Some metrics
- `backtesting/performance/` - Performance metrics

**Recommendation:**

```
analytics/
├── returns/           # Return calculation
├── indicators/        # Technical indicators
├── metrics/           # ALL performance metrics (consolidated)
└── statistics/        # Statistical utilities
```

Move `backtesting.performance` metrics to `analytics.metrics` for cleaner separation.

______________________________________________________________________

### Issue 2: Universe Management Cross-Cutting Concerns

**Problem:** `assets.universes` orchestrates multiple packages (data, assets, analytics)

**Current State:**

- Universe manager calls: selection → classification → returns
- Tightly coupled to implementation details
- Difficult to test in isolation

**Recommendation:** Create orchestration layer

```
orchestration/
├── universe_loader.py      # Universe YAML loading & validation
├── pipeline_executor.py    # Executes data pipeline stages
└── workflow_manager.py     # Manages complete workflows
```

This separates:

1. **Configuration** (universe definitions) - stays in `assets.universes`
1. **Orchestration** (workflow execution) - new `orchestration` package
1. **Implementation** (actual processing) - existing packages

______________________________________________________________________

### Issue 3: Preselection & Membership Policy Location

**Problem:** These features span multiple concerns

**Current State:**

- Preselection in `portfolio/` (but it's also an asset selection concern)
- Membership policy in `portfolio/` (but it's a rebalancing concern)

**Analysis:**

- **Preselection** = Factor-based asset filtering → Could be in `assets.selection`
- **Membership Policy** = Turnover control during rebalancing → Could be in `backtesting`

**Recommendation:** Keep current location BUT clarify interfaces

- Preselection: Portfolio construction concern (uses financial factors)
- Membership: Portfolio management concern (applies to weights)

These are correctly placed because they use domain knowledge from portfolio theory.

______________________________________________________________________

### Issue 4: Caching Cross-Cutting

**Problem:** Caching is used in multiple packages

**Current State:**

- `data/factor_caching/` - Factor/statistics caching
- Incremental resume in data preparation
- Various ad-hoc caches

**Recommendation:** Create unified caching infrastructure

```
core/
├── exceptions.py
├── config.py
├── types.py
├── caching/              # NEW: Unified caching infrastructure
│   ├── cache_base.py     # Abstract cache interface
│   ├── disk_cache.py     # Disk-based cache
│   ├── memory_cache.py   # In-memory cache
│   └── cache_manager.py  # Cache lifecycle management
└── utils.py
```

Then refactor specific caches:

- `data/factor_caching/` → Use `core.caching`
- Data prep incremental resume → Use `core.caching`

______________________________________________________________________

## Proposed Package Structure

### Option A: Minimal Changes (Recommended)

**Rationale:** Current structure is good. Make targeted improvements.

```
src/portfolio_management/
├── core/                      # Foundation + unified caching
│   ├── caching/              # NEW: Unified cache infrastructure
│   ├── exceptions.py
│   ├── config.py
│   └── types.py
├── data/                      # Data management (no caching)
│   ├── ingestion/
│   ├── io/
│   └── matching/
├── assets/                    # Asset universe management
│   ├── selection/
│   ├── classification/
│   └── universes/           # Config only, no orchestration
├── analytics/                 # ALL analytics (consolidated)
│   ├── returns/
│   ├── metrics/             # MOVED: All performance metrics here
│   ├── indicators/
│   └── statistics/
├── portfolio/                 # Portfolio construction
│   ├── strategies/
│   ├── constraints/
│   ├── preselection/        # Keep here (portfolio concern)
│   └── membership/          # Keep here (portfolio concern)
├── backtesting/              # Backtesting engine only
│   ├── engine/
│   └── transactions/        # REMOVED: performance/ moved to analytics
├── orchestration/            # NEW: Workflow orchestration
│   ├── universe_loader.py
│   ├── pipeline_executor.py
│   └── workflow_manager.py
├── reporting/                # Visualization only
│   └── visualization/
└── macro/                    # Macro signals (stub)
```

**Changes:**

1. ✅ Add `core/caching/` - Unified cache infrastructure
1. ✅ Add `orchestration/` - Workflow management
1. ✅ Move `backtesting/performance/` → `analytics/metrics/`
1. ✅ Refactor `assets/universes/` to use `orchestration/`

______________________________________________________________________

### Option B: Full Separation (More Radical)

**Rationale:** Maximum decoupling, but requires significant refactoring.

```
src/portfolio_management/
├── core/                      # Shared infrastructure
├── data_pipeline/             # Data acquisition & preparation
│   ├── ingestion/
│   ├── matching/
│   └── validation/
├── asset_universe/            # Asset selection & classification
│   ├── selection/
│   ├── classification/
│   └── filtering/
├── analytics/                 # All analytical computations
│   ├── returns/
│   ├── metrics/
│   ├── indicators/
│   ├── statistics/
│   └── factors/             # Preselection factors
├── portfolio_construction/   # Portfolio optimization
│   ├── strategies/
│   ├── constraints/
│   └── rebalancing/         # Membership policy
├── backtesting/              # Simulation engine
│   ├── engine/
│   ├── transactions/
│   └── simulation/
├── orchestration/            # Workflow management
├── reporting/                # Visualization
└── macro/                    # Macro signals
```

**Pros:**

- Very clear boundaries
- Easy to extract packages as separate libraries
- Maximum testability

**Cons:**

- Major refactoring required
- Risk of breaking existing code
- Need to update all imports and tests

**Verdict:** Not recommended. Current structure is already good.

______________________________________________________________________

## Recommended Changes (Incremental)

### Phase 1: Unified Caching (Highest Priority)

**Goal:** Single cache infrastructure for all packages

**Tasks:**

1. Create `core/caching/` with abstract interfaces
1. Implement disk cache, memory cache, TTL support
1. Migrate `data/factor_caching/` to use new infrastructure
1. Migrate data prep incremental resume to use new infrastructure
1. Update documentation

**Benefit:** Reduces code duplication, improves maintainability

______________________________________________________________________

### Phase 2: Orchestration Layer (High Priority)

**Goal:** Separate workflow orchestration from business logic

**Tasks:**

1. Create `orchestration/` package
1. Extract orchestration logic from `assets/universes/`
1. Create `WorkflowManager` for managed/manual workflows
1. Update CLI scripts to use orchestration layer
1. Update tests

**Benefit:** Cleaner separation, easier to add new workflows

______________________________________________________________________

### Phase 3: Analytics Consolidation (Medium Priority)

**Goal:** All performance metrics in one place

**Tasks:**

1. Move `backtesting/performance/` to `analytics/metrics/`
1. Update imports in backtesting engine
1. Update tests
1. Update documentation

**Benefit:** Clearer responsibility, easier to find metrics

______________________________________________________________________

### Phase 4: Configuration Management (Low Priority)

**Goal:** Centralize configuration handling

**Tasks:**

1. Consolidate YAML loading/validation in `core/config/`
1. Create configuration schemas
1. Implement validation decorators
1. Update universe management to use centralized config

**Benefit:** Consistent config handling, better validation

______________________________________________________________________

## Package Coupling Analysis

### Current Coupling Matrix

```
Package Dependencies (→ means "depends on"):

core         → (no dependencies)
data         → core
assets       → core, data, analytics (returns)
analytics    → core, data
portfolio    → core, analytics, assets
backtesting  → core, portfolio, analytics, assets
reporting    → core, analytics, backtesting
macro        → core, data
orchestration → (NEW) → ALL packages
```

### Dependency Rules

**Good:**

- `core` has no dependencies (foundation)
- `reporting` only depends on data structures (loose coupling)
- `data` minimal dependencies

**Concerning:**

- `assets` depends on `analytics` (for returns)
  - **Fix:** Returns should be computed separately, not during selection
- `backtesting` depends on too many packages
  - **Fix:** Use dependency injection, interfaces

**Problematic:**

- Circular potential: `assets` ↔ `analytics`
  - **Status:** Currently avoided, but fragile

______________________________________________________________________

## Interface Definitions

### Recommended Clear Interfaces

```python
# core/interfaces.py
from abc import ABC, abstractmethod
from typing import Protocol

class DataProvider(Protocol):
    """Interface for providing price data"""
    def get_prices(self, symbols: list[str], start: date, end: date) -> pd.DataFrame:
        ...

class AssetFilter(Protocol):
    """Interface for filtering assets"""
    def filter(self, assets: pd.DataFrame) -> pd.DataFrame:
        ...

class PortfolioStrategy(ABC):
    """Abstract base for portfolio strategies"""
    @abstractmethod
    def optimize(self, returns: pd.DataFrame, **kwargs) -> pd.Series:
        ...

class RebalancingPolicy(Protocol):
    """Interface for rebalancing policies"""
    def should_rebalance(self, date: date, last_rebalance: date) -> bool:
        ...

class PerformanceMetric(Protocol):
    """Interface for performance metrics"""
    def calculate(self, returns: pd.Series) -> float:
        ...
```

**Usage:** All cross-package communication should use these interfaces.

______________________________________________________________________

## Testing Strategy for Package Separation

### Unit Testing

Each package should have:

1. **Unit tests** - Test individual functions/classes in isolation
1. **Mock dependencies** - Use mocks for other packages
1. **Interface tests** - Verify implementations match interfaces

### Integration Testing

Test package interactions:

1. **Pipeline tests** - Test data flow through packages
1. **Workflow tests** - Test complete workflows
1. **Contract tests** - Verify interfaces between packages

### Architecture Tests

Enforce separation:

```python
# tests/architecture/test_dependencies.py
def test_core_has_no_dependencies():
    """Core package should not import from other packages"""
    assert check_imports('portfolio_management.core') == []

def test_reporting_limited_dependencies():
    """Reporting should only depend on core and data structures"""
    allowed = ['portfolio_management.core']
    assert check_imports('portfolio_management.reporting') in allowed
```

______________________________________________________________________

## Migration Path

### Step 1: Current State (Oct 2025)

- ✅ Document current architecture
- ✅ Identify coupling issues
- ✅ Propose solutions

### Step 2: Phase 1 - Caching (1-2 days)

- Create `core/caching/`
- Migrate existing caches
- Tests + documentation

### Step 3: Phase 2 - Orchestration (2-3 days)

- Create `orchestration/` package
- Extract orchestration from `assets/universes/`
- Update CLIs
- Tests + documentation

### Step 4: Phase 3 - Analytics (1 day)

- Move performance metrics to `analytics/`
- Update imports
- Tests + documentation

### Step 5: Phase 4 - Config (1 day)

- Consolidate config handling
- Add validation
- Tests + documentation

### Step 6: Validation (1 day)

- Run all tests
- Update architecture documentation
- Create architecture tests

**Total Effort:** 6-8 days of development work

______________________________________________________________________

## Success Criteria

### Architectural Goals

1. **Low Coupling**

   - ✅ Each package has minimal dependencies
   - ✅ Changes in one package rarely require changes in others
   - ✅ Packages can be tested in isolation

1. **High Cohesion**

   - ✅ Related functionality grouped together
   - ✅ Clear single responsibility for each package
   - ✅ Intuitive package names and structure

1. **Clear Interfaces**

   - ✅ Well-defined contracts between packages
   - ✅ Type hints and protocols used throughout
   - ✅ Documentation of interfaces

1. **Testability**

   - ✅ Each package can be unit tested independently
   - ✅ Integration tests verify package interactions
   - ✅ Architecture tests enforce boundaries

1. **Maintainability**

   - ✅ Easy to locate functionality
   - ✅ Easy to add new features
   - ✅ Easy to modify existing features

______________________________________________________________________

## Recommendations Summary

### Immediate Actions (Do Now)

1. ✅ **Archive outdated documentation** (DONE)
1. ✅ **Create this analysis document** (DONE)
1. 📝 **Create architecture tests** - Enforce package boundaries
1. 📝 **Document interfaces** - Clarify contracts between packages

### Short-Term (Next Sprint)

1. **Phase 1: Unified Caching**

   - Create `core/caching/` infrastructure
   - Migrate existing caches
   - Reduces duplication, improves consistency

1. **Phase 2: Orchestration Layer**

   - Create `orchestration/` package
   - Extract workflow logic from `assets/universes/`
   - Clearer separation of concerns

### Medium-Term (Future)

1. **Phase 3: Analytics Consolidation**

   - Move all metrics to `analytics/`
   - Clearer responsibility

1. **Phase 4: Configuration Management**

   - Centralize config handling
   - Better validation

### Long-Term (Optional)

1. **Extract Packages as Libraries**
   - `portfolio-analytics` - Analytics package
   - `portfolio-construction` - Optimization strategies
   - `backtest-engine` - Simulation engine
   - Enables reuse across projects

______________________________________________________________________

## Conclusion

**Current State:** ⭐⭐⭐⭐ (Good architecture, minor improvements needed)

**Strengths:**

- Clear package boundaries
- Logical grouping of functionality
- Modular design

**Areas for Improvement:**

- Unified caching infrastructure
- Separate orchestration layer
- Consolidate analytics
- Clearer interfaces

**Recommendation:** Incremental improvements (Option A). The current architecture is solid and doesn't require radical changes. Focus on:

1. Unified caching (removes duplication)
1. Orchestration layer (better separation)
1. Analytics consolidation (clearer structure)

**Timeline:** 6-8 days of focused development work across 4 phases.

______________________________________________________________________

**Author:** Architecture Analysis
**Date:** October 25, 2025
**Status:** Proposal - Pending Review
