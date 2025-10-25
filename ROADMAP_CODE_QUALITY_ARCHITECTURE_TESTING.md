# Roadmap: Code Quality, Architecture, and Testing Improvements

**Date:** October 25, 2025
**Status:** IN PROGRESS - Phase 2.2 Active (Phase 1 ✅, Phase 2.1 ✅)
**Context:** Pre-refactoring and new feature development preparation

______________________________________________________________________

## 🎉 Recent Progress (October 25, 2025)

### Phase 1: Test Infrastructure ✅ **COMPLETE**

- ✅ **Issue #118** - Test categorization & pytest configuration (PR #131)
- ✅ **Issue #119** - Extract unit tests (PR #133)
- ✅ **Issue #120** - Test isolation patterns (PRs #134 & #135)
- **Outcome:** 43x unit test speed improvement (0.57s vs 22-25s), 808 total tests (22 unit, 786 integration)

### Phase 2.1: Module Boundaries ✅ **COMPLETE**

- ✅ **Issue #121** - Import-linter implementation (PRs #134 & #135)
- **Outcome:** 8-layer architecture enforced, 7 contracts, 0 violations

### Phase 2.2: Service Layer Extraction 🔄 **IN PROGRESS - 25% Complete**

- 🔄 **Issue #122** - Extract service layer (1 of 4 scripts done)
- ✅ **PR #139 MERGED** - PortfolioConstructionService
  - Created `src/portfolio_management/services/` package
  - Implemented PortfolioConstructionService (200 lines)
  - Refactored `construct_portfolio.py` (69% orchestration logic reduction)
  - Added 3 unit tests (all passing)
  - Created stub services for future work
- **Remaining:** 3 more services (DataPreparationService, BacktestService, UniverseManagementService)

______________________________________________________________________

## Executive Summary

I'll review PR #135, check the codex remarks, make decisions on them, merge if appropriate, and update the roadmap, epic, and related issue.

Good! I can see that Jules has addressed all the codex remarks. Let me check the PR status to see if all tests are passing:

Perfect! All codex remarks have been addressed by Jules. The PR is ready to merge. Let me merge it and update everything:

Auto approved for this profile (Edit)

The portfolio management toolkit has grown significantly (16K+ lines of source, 17K+ lines of tests, 822 test cases, 130 integration tests). Before introducing new functionality, we need to address:

1. **Test Speed & Isolation** - Current test suite takes ~25 seconds; integration tests need better isolation
1. **Architecture Modularity** - Strengthen modular monolith boundaries and reduce coupling
1. **Code Quality** - Address remaining technical debt and improve maintainability
1. **Testing Infrastructure** - Implement fast unit tests, improve test organization

**Current State:**

- ✅ **Production-ready core** (Phases 1-9 complete)
- ✅ **Excellent test coverage** (822 tests, 75%+ coverage)
- ✅ **Clean codebase** (recent technical debt cleanup, October 2025)
- ⚠️ **Mixed test speeds** (some tests slow, no clear unit/integration separation)
- ⚠️ **Growing complexity** (some large modules, tight coupling in places)

______________________________________________________________________

## Phase 1: Test Infrastructure Overhaul (Priority: HIGH)

**Goal:** Achieve \<5 second unit test runs, clear test isolation, parallel-safe tests

### 1.1 Test Categorization & Pytest Configuration

**Current Issues:**

- No registered pytest marks (warnings in output: `pytest.mark.integration` and `pytest.mark.slow` not registered)
- No clear separation between unit, integration, and performance tests
- Unit tests take 22-25 seconds (should be \<5s)
- Integration tests mixed with unit tests

**Actions:**

1. **Register pytest marks in `pytest.ini`:**

```ini
[pytest]
testpaths = tests
pythonpath = src

markers =
    unit: Fast isolated unit tests (<100ms each)
    integration: Integration tests requiring multiple components
    slow: Slow tests (>1s runtime)
    performance: Performance benchmarks
    requires_data: Tests requiring large data files
```

2. **Create test organization guidelines:**

   - `tests/unit/` - Pure unit tests, \<100ms each, no I/O
   - `tests/integration/` - Multi-component tests, can use I/O
   - `tests/performance/` - Benchmarks (move from `benchmarks/`)
   - `tests/e2e/` - End-to-end CLI tests

1. **Add pytest-timeout for safety:**

```toml
[project.optional-dependencies]
dev = [
    # ... existing ...
    "pytest-timeout",
]
```

4. **Update CI/CD to run test tiers separately:**

```bash
# Fast feedback (CI on every commit)
pytest tests/unit -v --timeout=10

# Full validation (CI on PR)
pytest tests/integration -v --timeout=60
pytest tests/e2e -v --timeout=120
```

**Effort:** 1-2 days
**Impact:** Fast feedback loop for development

______________________________________________________________________

### 1.2 Extract True Unit Tests from Current Test Suite

**Current Issues:**

- Many "unit" tests actually do integration (file I/O, multiple components)
- No clear distinction between unit and integration tests
- Test fixtures create real files/data (slow)

**Actions:**

1. **Audit current tests and categorize:**

```bash
# Scan for I/O operations in tests
grep -r "tmp_path\|tmpdir\|Path\|open\|read_csv\|to_csv" tests/ --include="*.py"

# Identify integration patterns
grep -r "BacktestEngine\|construct_portfolio\|run_backtest" tests/ --include="*.py"
```

2. **Create mock-based unit tests for core modules:**

   - `src/portfolio_management/portfolio/strategies/` - Mock data loaders
   - `src/portfolio_management/assets/selection/` - Mock price data
   - `src/portfolio_management/backtesting/engine/` - Mock returns data

1. **Move I/O-heavy tests to integration:**

   - `tests/scripts/test_*.py` → `tests/e2e/`
   - Multi-component tests → `tests/integration/`

1. **Create fixture library for common mocks:**

```python
# tests/fixtures/mocks.py
@pytest.fixture
def mock_price_data():
    """Fast in-memory price DataFrame for unit tests."""
    return pd.DataFrame(...)

@pytest.fixture
def mock_returns():
    """Fast in-memory returns for strategy tests."""
    return pd.DataFrame(...)
```

**Effort:** 3-5 days
**Impact:** Sub-second unit test runs, parallel test execution

______________________________________________________________________

### 1.3 Implement Test Isolation Patterns

**Current Issues:**

- Some tests may share state (caches, global variables)
- No explicit test isolation guarantees
- Caching code could affect test reproducibility

**Actions:**

1. **Add test isolation fixtures:**

```python
# tests/conftest.py
@pytest.fixture(autouse=True)
def reset_caches():
    """Clear all module-level caches before each test."""
    # Clear PriceLoader cache
    # Clear StatisticsCache
    # Clear FactorCache
    yield
    # Cleanup after test
```

2. **Make caches testable:**

```python
# Add to cache classes
class PriceLoader:
    def clear_cache(self) -> None:
        """Clear cache (primarily for testing)."""
        self._cache.clear()
```

3. **Add pytest-randomly for test independence validation:**

```toml
[project.optional-dependencies]
dev = [
    # ... existing ...
    "pytest-randomly",
]
```

4. **Run tests in random order to detect dependencies:**

```bash
pytest tests/ --randomly --randomly-dont-reorganise
```

**Effort:** 2-3 days
**Impact:** Reliable parallel test execution, no flaky tests

______________________________________________________________________

## Phase 2: Architecture Strengthening (Priority: HIGH)

**Goal:** Strengthen modular monolith, reduce coupling, improve testability

### 2.1 Define Clear Module Boundaries

**Current State:**

- Good module structure already in place
- Some coupling between modules (backtesting ↔ portfolio, data ↔ assets)
- No explicit dependency diagram

**Actions:**

1. **Document module dependencies:**

```python
# Create docs/architecture/MODULE_DEPENDENCIES.md
"""
Module Dependency Graph:

core (exceptions, types, utils)
  ↑
data (ingestion, io, matching, analysis)
  ↑
assets (selection, classification, universes)
  ↑
analytics (returns, metrics, indicators)
  ↑
portfolio (strategies, constraints, preselection, membership)
  ↑
backtesting (engine, transactions, performance)
  ↑
reporting (visualization, exporters)
  ↑
scripts (CLI entry points)
"""
```

2. **Add dependency enforcement with import-linter:**

```toml
[project.optional-dependencies]
dev = [
    # ... existing ...
    "import-linter",
]
```

3. **Create import contract (`.importlinter` config):**

```ini
[importlinter]
root_package = portfolio_management

[importlinter:contract:1]
name = Core has no dependencies on other modules
type = forbidden
source_modules =
    portfolio_management.core
forbidden_modules =
    portfolio_management.data
    portfolio_management.assets
    portfolio_management.analytics
    portfolio_management.portfolio
    portfolio_management.backtesting
    portfolio_management.reporting

[importlinter:contract:2]
name = Data layer doesn't depend on portfolio
type = forbidden
source_modules =
    portfolio_management.data
forbidden_modules =
    portfolio_management.portfolio
    portfolio_management.backtesting
```

4. **Run in CI:**

```bash
lint-imports
```

**Effort:** 2-3 days
**Impact:** Clear architecture boundaries, easier refactoring

______________________________________________________________________

### 2.2 Extract Service Layer for Complex Operations

**Current Issues:**

- Some scripts have complex orchestration logic
- Business logic mixed with CLI parsing
- Hard to test orchestration without CLI

**Actions:**

1. **Create service layer for orchestration:**

```python
# src/portfolio_management/services/portfolio_service.py
class PortfolioService:
    """High-level orchestration for portfolio operations."""

    def construct_portfolio(
        self,
        returns: pd.DataFrame,
        strategy: StrategyType,
        constraints: ConstraintSet,
    ) -> PortfolioWeights:
        """Construct portfolio with business logic."""
        # Orchestrate: preselection → construction → validation
        pass

# src/portfolio_management/services/backtest_service.py
class BacktestService:
    """High-level orchestration for backtesting."""

    def run_backtest(
        self,
        universe: Universe,
        strategy: Strategy,
        config: BacktestConfig,
    ) -> BacktestResults:
        """Run complete backtest workflow."""
        pass
```

2. **Refactor scripts to use services:**

```python
# scripts/construct_portfolio.py (simplified)
def main():
    args = parse_args()
    service = PortfolioService()
    result = service.construct_portfolio(...)
    export_results(result)
```

3. **Add service-layer tests:**

```python
# tests/services/test_portfolio_service.py
def test_portfolio_service_orchestration(mock_data):
    """Test service orchestrates correctly."""
    service = PortfolioService()
    result = service.construct_portfolio(...)
    assert ...
```

**Effort:** 5-7 days
**Impact:** Better testability, clearer separation of concerns

______________________________________________________________________

### 2.3 Reduce Large Module Complexity

**Current Issues:**

- Some modules have high complexity (matching.py, universes.py, etc.)
- Long files (200-500+ lines)
- Multiple responsibilities in single files

**Actions:**

1. **Identify large/complex modules:**

```bash
# Find files >300 lines
find src/ -name "*.py" -exec wc -l {} + | awk '$1 > 300' | sort -n

# Find high cyclomatic complexity
radon cc src/ -s -n C
```

2. **Refactor large modules into submodules:**

```
# Example: universes.py → universes/ package
src/portfolio_management/assets/universes/
  ├── __init__.py
  ├── universe.py          # Universe dataclass
  ├── loader.py            # YAML loading
  ├── validator.py         # Validation logic
  ├── exporter.py          # Export functionality
  └── comparison.py        # Comparison tools
```

3. **Extract helper functions to utils:**

```python
# src/portfolio_management/assets/universes/utils.py
def parse_date_range(...):
    """Parse date range from config."""

def resolve_asset_list(...):
    """Resolve asset list from various sources."""
```

4. **Create focused classes with single responsibility:**

```python
# Before: UniverseManager does everything
# After:
class UniverseLoader:
    """Load universes from YAML."""

class UniverseValidator:
    """Validate universe configuration."""

class UniverseExporter:
    """Export universes to various formats."""
```

**Effort:** 7-10 days (spread across multiple PRs)
**Impact:** Better maintainability, easier testing, clearer code

______________________________________________________________________

## Phase 3: Code Quality Improvements (Priority: MEDIUM)

**Goal:** Address remaining technical debt, improve code consistency

### 3.1 Address Remaining Type Errors

**Current State:**

- 9 mypy errors (acceptable but improvable)
- Some generic types not fully specified
- Pandas type stubs still have limitations

**Actions:**

1. **Fix remaining mypy errors:**

```bash
mypy src/ --show-error-codes --pretty
```

2. **Add generic type parameters where missing:**

```python
# Before
def process_data(df: pd.DataFrame) -> pd.Series:

# After
def process_data(df: pd.DataFrame) -> pd.Series[float]:
```

3. **Update to latest pandas-stubs:**

```toml
[project.optional-dependencies]
dev = [
    "pandas-stubs>=2.2.0",  # Update to latest
]
```

4. **Create type aliases for complex types:**

```python
# src/portfolio_management/core/types.py
PriceFrame = pd.DataFrame  # Columns: Date, Asset, Price
ReturnSeries = pd.Series[float]  # Index: Date
WeightDict = dict[str, float]  # Asset -> Weight
```

**Effort:** 2-3 days
**Impact:** Better IDE support, catch more bugs at development time

______________________________________________________________________

### 3.2 Standardize Error Handling

**Current State:**

- Good exception hierarchy already exists
- Some inconsistency in error handling patterns
- Mix of bare exceptions and custom exceptions

**Actions:**

1. **Audit error handling patterns:**

```bash
# Find bare exceptions
grep -r "except:" src/ --include="*.py"
grep -r "except Exception:" src/ --include="*.py"
```

2. **Create error handling guidelines:**

```python
# docs/best_practices/ERROR_HANDLING.md
"""
Error Handling Patterns:

1. Always catch specific exceptions
2. Re-raise with context using custom exceptions
3. Log at appropriate level
4. Include context in error messages
"""
```

3. **Add error context to all exceptions:**

```python
# Before
raise ValueError("Invalid weight")

# After
raise ValidationError(
    "Invalid weight for asset",
    context={"asset": asset, "weight": weight, "constraint": constraint}
)
```

4. **Create error handling decorators:**

```python
# src/portfolio_management/core/decorators.py
def handle_data_errors(func):
    """Convert data errors to DataError."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (KeyError, ValueError, pd.errors.ParserError) as e:
            raise DataError(...) from e
    return wrapper
```

**Effort:** 3-4 days
**Impact:** More consistent error handling, better debugging

______________________________________________________________________

### 3.3 Improve Logging Consistency

**Current State:**

- Logging in place but inconsistent levels
- Some debug logging, some info
- No structured logging

**Actions:**

1. **Define logging standards:**

```python
# docs/best_practices/LOGGING.md
"""
Logging Levels:

- DEBUG: Detailed diagnostic info (cache hits, internal state)
- INFO: Key milestones (file loaded, portfolio constructed)
- WARNING: Recoverable issues (missing data, fallback used)
- ERROR: Errors that prevent operation
- CRITICAL: System-level failures
"""
```

2. **Add structured logging context:**

```python
# Before
logger.info(f"Processed {count} assets")

# After
logger.info("Processed assets", extra={
    "asset_count": count,
    "strategy": strategy_name,
    "elapsed_time": elapsed,
})
```

3. **Create logging configuration template:**

```yaml
# config/logging.yaml
version: 1
formatters:
  detailed:
    format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
handlers:
  console:
    class: logging.StreamHandler
    formatter: detailed
    level: INFO
  file:
    class: logging.FileHandler
    filename: portfolio_management.log
    formatter: detailed
    level: DEBUG
loggers:
  portfolio_management:
    level: DEBUG
    handlers: [console, file]
```

4. **Add logging to key operations:**

```python
# Add performance logging
with log_performance("portfolio_construction"):
    weights = strategy.construct(...)
```

**Effort:** 2-3 days
**Impact:** Better observability, easier debugging

______________________________________________________________________

## Phase 4: Testing Enhancements (Priority: MEDIUM)

**Goal:** Improve test quality, coverage, and maintainability

### 4.1 Add Property-Based Testing for Core Logic

**Current State:**

- Good parametric testing with pytest
- No property-based testing (Hypothesis)
- Some edge cases may be missed

**Actions:**

1. **Add Hypothesis for property-based tests:**

```toml
[project.optional-dependencies]
dev = [
    # ... existing ...
    "hypothesis",
]
```

2. **Create property tests for mathematical operations:**

```python
# tests/portfolio/test_strategies_properties.py
from hypothesis import given, strategies as st

@given(
    returns=st.data_frames(...),
    weights=st.dictionaries(...)
)
def test_portfolio_weights_sum_to_one(returns, weights):
    """Portfolio weights always sum to 1.0."""
    result = normalize_weights(weights)
    assert abs(sum(result.values()) - 1.0) < 1e-6

@given(prices=st.data_frames(...))
def test_returns_calculation_invertible(prices):
    """Returns can be inverted to recover prices."""
    returns = calculate_returns(prices)
    recovered = reconstruct_prices(returns, prices.iloc[0])
    assert_frame_equal(prices, recovered, atol=1e-6)
```

3. **Add property tests for constraints:**

```python
@given(weights=st.dictionaries(...))
def test_weight_constraints_always_satisfied(weights):
    """Constraints are always satisfied after enforcement."""
    constrained = apply_constraints(weights, min_weight=0.01, max_weight=0.25)
    assert all(0.01 <= w <= 0.25 for w in constrained.values())
```

**Effort:** 3-5 days
**Impact:** Find edge cases automatically, higher confidence in correctness

______________________________________________________________________

### 4.2 Add Mutation Testing

**Current State:**

- Good line coverage (75%+)
- Unknown mutation coverage
- May have tests that don't actually test behavior

**Actions:**

1. **Add mutmut for mutation testing:**

```toml
[project.optional-dependencies]
dev = [
    # ... existing ...
    "mutmut",
]
```

2. **Run mutation testing on core modules:**

```bash
# Start with small module
mutmut run --paths-to-mutate=src/portfolio_management/portfolio/strategies/equal_weight.py

# Check results
mutmut results
mutmut show
```

3. **Fix weak tests identified:**

```python
# Example: test that doesn't catch mutation
def test_sum_weights():
    weights = {"A": 0.5, "B": 0.5}
    result = sum(weights.values())
    assert result == 1.0  # Would pass even if code changed

# Better test
def test_normalize_weights():
    weights = {"A": 2.0, "B": 3.0}
    result = normalize_weights(weights)
    assert result == {"A": 0.4, "B": 0.6}  # Catches implementation bugs
```

4. **Set mutation coverage target:**

```bash
# Aim for 80% mutation coverage on core modules
```

**Effort:** 5-7 days
**Impact:** Find tests that don't actually verify behavior

______________________________________________________________________

### 4.3 Add Performance Regression Tests

**Current State:**

- Some performance benchmarks exist
- No automated regression detection
- Performance changes not tracked

**Actions:**

1. **Add pytest-benchmark:**

```toml
[project.optional-dependencies]
dev = [
    # ... existing ...
    "pytest-benchmark",
]
```

2. **Create performance test suite:**

```python
# tests/performance/test_performance_benchmarks.py
def test_backtest_performance(benchmark):
    """Backtest should complete in reasonable time."""
    result = benchmark(run_backtest, universe, strategy, config)
    # benchmark automatically tracks timing and regressions
```

3. **Set performance budgets:**

```python
@pytest.mark.performance
def test_asset_selection_budget():
    """Asset selection should be <1s for 1000 assets."""
    start = time.perf_counter()
    select_assets(large_universe)
    elapsed = time.perf_counter() - start
    assert elapsed < 1.0, f"Too slow: {elapsed:.2f}s"
```

4. **Add CI performance tracking:**

```yaml
# .github/workflows/performance.yml
- name: Run performance tests
  run: |
    pytest tests/performance --benchmark-only \
      --benchmark-save=baseline \
      --benchmark-compare
```

**Effort:** 3-4 days
**Impact:** Catch performance regressions early

______________________________________________________________________

## Phase 5: Documentation & Tooling (Priority: LOW)

**Goal:** Improve developer experience and onboarding

### 5.1 Create Developer Guide

**Actions:**

1. **Create comprehensive developer guide:**

```markdown
# docs/CONTRIBUTING.md

## Getting Started
## Running Tests
## Code Style
## Architecture Overview
## Adding New Features
## Debugging Tips
```

2. **Add architecture decision records (ADRs):**

```markdown
# docs/architecture/decisions/001-modular-monolith.md
# 1. Use Modular Monolith Architecture

Date: 2025-10-25

## Status: Accepted

## Context
...

## Decision
...

## Consequences
...
```

**Effort:** 2-3 days
**Impact:** Easier onboarding, better architecture communication

______________________________________________________________________

### 5.2 Improve Pre-commit Hooks

**Actions:**

1. **Update pre-commit versions (already noted in technical debt):**

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 24.10.0  # Update from 22.10.0
  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.6.8  # Update from v0.0.289
```

2. **Add additional hooks:**

```yaml
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.11.2  # Update from v0.982

  # New hooks
  - repo: https://github.com/pre-commit/pygrep-hooks
    rev: v1.10.0
    hooks:
      - id: python-check-blanket-noqa
      - id: python-check-blanket-type-ignore

  - repo: https://github.com/asottile/pyupgrade
    rev: v3.15.0
    hooks:
      - id: pyupgrade
        args: [--py310-plus]
```

**Effort:** 1 day
**Impact:** Catch more issues before commit

______________________________________________________________________

## Summary & Prioritization

### Immediate Actions (Weeks 1-2)

**Priority 1: Test Speed & Organization**

- \[ \] 1.1 Test Categorization & Pytest Configuration (1-2 days)
- \[ \] 1.2 Extract True Unit Tests (3-5 days)
- \[ \] 1.3 Implement Test Isolation (2-3 days)

**Expected Outcome:** \<5 second unit test runs, reliable parallel execution

______________________________________________________________________

### Short-term Actions (Weeks 3-6)

**Priority 2: Architecture Boundaries**

- \[ \] 2.1 Define Clear Module Boundaries (2-3 days)
- \[ \] 2.2 Extract Service Layer (5-7 days)
- \[ \] 2.3 Reduce Large Module Complexity (7-10 days, spread over time)

**Expected Outcome:** Clearer architecture, easier refactoring, better testability

______________________________________________________________________

### Medium-term Actions (Weeks 7-10)

**Priority 3: Code Quality**

- \[ \] 3.1 Address Remaining Type Errors (2-3 days)
- \[ \] 3.2 Standardize Error Handling (3-4 days)
- \[ \] 3.3 Improve Logging Consistency (2-3 days)

**Priority 4: Testing Enhancements**

- \[ \] 4.1 Add Property-Based Testing (3-5 days)
- \[ \] 4.2 Add Mutation Testing (5-7 days)
- \[ \] 4.3 Add Performance Regression Tests (3-4 days)

**Expected Outcome:** Higher code quality, better test coverage, performance tracking

______________________________________________________________________

### Long-term Actions (Ongoing)

**Priority 5: Documentation & Tooling**

- \[ \] 5.1 Create Developer Guide (2-3 days)
- \[ \] 5.2 Improve Pre-commit Hooks (1 day)

**Expected Outcome:** Better developer experience, easier onboarding

______________________________________________________________________

## Success Metrics

**Test Speed:**

- Unit tests: \<5 seconds (currently ~25s)
- Integration tests: \<30 seconds
- Full suite with parallel: \<60 seconds

**Test Quality:**

- 100% of unit tests isolated (no I/O)
- 80%+ mutation coverage on core modules
- Zero flaky tests

**Architecture:**

- All modules have explicit dependency contracts
- No circular dependencies
- Service layer covers all CLI orchestration

**Code Quality:**

- Zero mypy errors on strict mode
- Zero ruff errors
- 100% of exceptions are custom exceptions with context

______________________________________________________________________

## Risk Assessment

**Low Risk:**

- Test reorganization (backwards compatible)
- Documentation improvements
- Pre-commit updates

**Medium Risk:**

- Service layer extraction (requires refactoring scripts)
- Module splitting (could break imports if not careful)

**High Risk:**

- None identified (all changes are incremental and testable)

______________________________________________________________________

## Next Steps

1. **Review this roadmap** with stakeholders
1. **Create GitHub issues** for Phase 1 items
1. **Start with test categorization** (quick win, high impact)
1. **Track progress** in `memory-bank/progress.md`
1. **Regular checkpoints** every 2 weeks

______________________________________________________________________

## Related Documents

- [ARCHITECTURE_AUDIT_SUMMARY.md](ARCHITECTURE_AUDIT_SUMMARY.md)
- [archive/technical-debt/TECHNICAL_DEBT_REVIEW_2025-10-15.md](archive/technical-debt/TECHNICAL_DEBT_REVIEW_2025-10-15.md)
- [memory-bank/systemPatterns.md](memory-bank/systemPatterns.md)
- [docs/architecture/COMPLETE_WORKFLOW.md](docs/architecture/COMPLETE_WORKFLOW.md)
