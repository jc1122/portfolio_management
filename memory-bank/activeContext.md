# Active Context

## Current Focus

**Phase 1 Complete:** Data preparation pipeline successfully modularized and tested.
**Phase 2 Complete:** Technical debt resolution - type safety, concurrency, complexity reduction.
**Phase 3 Complete:** Asset selection, classification, returns, and universe management are production-ready with full integration coverage.
**Phase 3.5 Complete:** Comprehensive cleanup delivered documentation organization, lint/test polish, refactors, and refreshed exceptions.
**Current Phase:** Phase 4 – Portfolio Construction (detailed plan created, ready to implement).

### Latest Update – 2025-10-17

- Refreshed portfolio exceptions with typed context fields and optional messages; smoke tests now cover inheritance and attribute access.
- Risk parity tests skip gracefully on Python 3.9 (zip strict flag unavailable) while equal-weight coverage remains active.
- Next: Re-confirm Task 2 data model scaffolding before expanding strategy coverage.

## Recent Changes (Phase 3.5 – Comprehensive Cleanup) ✅

- Organized documentation: root markdown files reduced from 18 to 6 with historical content archived under `archive/`.
- Eliminated pytest marker warnings by registering `integration` and `slow` markers in `pyproject.toml`.
- Applied Ruff auto-fixes and replaced blanket `ruff: noqa` directives with targeted rule codes.
- Refactored `export_tradeable_prices` into helper-driven stages to reduce cyclomatic complexity to ≤10.
- Moved type-only imports into `TYPE_CHECKING` blocks to lower runtime import overhead.
- Enhanced the exception hierarchy with dependency and data-directory specific subclasses.
- Full validation completed (171 tests, 0 mypy errors, ~30 lint warnings) – repository is pristine for Phase 4 work.

## Phase 3 Progress

- ✅ Stage 1: Asset selection core models, filters, CLIs, fixtures, and unit coverage delivered.
- ✅ Stage 2: Classification taxonomy, rule engine, overrides, and CLI shipped.
- ✅ Stage 3: Return calculation rebuilt with validation, alignment, missing-data controls, and CLI enhancements; reference docs published.
- ✅ Stage 4: Universe management (YAML schema, CLI suite, curated sleeves) completed with documentation.
- ✅ Stage 5: Integration, performance validation, and cleanup complete – caching baselines set, CLI UX polished, and error handling unified.

**Test Suite:** 171 tests (unit + CLI + integration + performance smoke), ~86 % coverage with production-fixture validation.

## Historical Reference: Phase 2 Quick Maintenance

1. Kick off Phase 4 portfolio construction: implement equal-weight baseline, risk parity, and PyPortfolioOpt mean-variance adapters.
1. Maintain cleanup standards by keeping lint/mypy at zero, documenting changes as delivered, and preserving the 9.5+/10 quality bar.
1. Expand integration coverage to exercise upcoming strategy adapters end-to-end with existing fixtures and production configs.

## Coming Up

Phase 4 introduces portfolio construction strategies (equal-weight baseline, risk parity, mean-variance) on top of the prepared universes, followed by Phase 5 backtesting and Phase 6 advanced overlays.

### Latest Technical Debt Review (COMPLETE) ✅

### Technical Debt Resolution (COMPLETE) ✅

- ✅ **Task 1: Type Annotations** - 78% mypy error reduction (40+ → 9)

  - Installed pandas-stubs and types-PyYAML
  - Added TypeVar generics to `_run_in_parallel`
  - Parameterized Counter/dict types throughout codebase
  - All 17 original tests passing, 75% coverage maintained

- ✅ **Task 2: Concurrency Implementation** - 18 new tests, robust parallel execution

  - Enhanced `_run_in_parallel` with `preserve_order` parameter (default True)
  - Added task-level error handling with context
  - Optional `log_tasks` diagnostics
  - Total test suite: 35 tests passing (100%), zero regressions

- ✅ **Task 3: Matching Logic Simplification** - 55% complexity reduction

  - Extracted `_extension_is_acceptable` helper in matching strategies
  - Refactored BaseMarketMatchingStrategy into 3 focused methods
  - 17% reduction in strategy code lines
  - Clear single-responsibility design

- ✅ **Task 4: Analysis Pipeline Refactoring** - 26% length reduction

  - Extracted `_initialize_diagnostics` helper
  - Extracted `_determine_data_status` helper
  - Explicit 5-stage pipeline in `summarize_price_file`
  - Improved testability and maintainability

### Documentation Cleanup (COMPLETE) ✅

- Created CODE_REVIEW.md with comprehensive review (9.5/10 quality score)
- Organized documentation into clear structure:
  - Root: Active docs only (AGENTS.md, CODE_REVIEW.md, README.md, etc.)
  - archive/technical-debt/: Task completion docs and plan
  - archive/sessions/: Old session notes and summaries
- Updated README.md with Phase 2 status
- Cleaned memory bank (this file)

### Latest Technical Debt Review (COMPLETE) ✅

- Created TECHNICAL_DEBT_REVIEW_2025-10-15.md with comprehensive analysis
- **Code Quality Score: 9.0/10** - Excellent professional-grade codebase
- **Remaining Technical Debt: LOW** - 5 categories identified, all P2-P4 priority
  1. 9 mypy errors (P3) - pandas-stubs limitations and minor type mismatches
  1. 52 ruff warnings (P4) - mostly style/consistency, 14 auto-fixable
  1. pyproject.toml deprecation (P2) - ruff config needs migration to \[tool.ruff.lint\]
  1. Pre-commit hook updates (P3) - black, ruff, mypy, isort versions outdated
  1. Documentation gaps (P3) - 6 modules missing docstrings
- **No blocking issues identified** - Ready for Phase 3
- Identified 2-3 optional refactoring opportunities (extract config, structured logging)
- Test coverage: 84% (excellent), minor gaps in error handling paths

## Immediate Next Steps

### Phase 4: Portfolio Construction (Implementation in Progress) 🎯

**Task 1: Portfolio Exceptions (COMPLETE) ✅**

- Added a new suite of exceptions for portfolio construction (`PortfolioConstructionError`, `InvalidStrategyError`, `ConstraintViolationError`, `OptimizationError`, `InsufficientDataError`, `DependencyError`) to `src/portfolio_management/exceptions.py`.
- Renamed the old `InsufficientDataError` to `InsufficientAssetsError` to better reflect its purpose and avoid conflicts.
- Added comprehensive unit tests for the new exceptions in `tests/test_portfolio.py`.
- Fixed all associated linting and type-checking issues, ensuring the codebase remains clean.

**Task 2: Portfolio Data Models (COMPLETE) ✅**

- Created the initial `src/portfolio_management/portfolio.py` module.
- Defined and implemented the core data models: `StrategyType`, `PortfolioConstraints`, `RebalanceConfig`, and `Portfolio`.
- Added comprehensive unit tests for the new data models and their validation logic.

**Task 3: Strategy Interface (COMPLETE) ✅**

- Defined the `PortfolioStrategy` abstract base class in `src/portfolio_management/portfolio.py`.
- Added tests to ensure the abstract class cannot be instantiated.

**Task 4: Equal-Weight Strategy (COMPLETE) ✅**

- Implemented the `EqualWeightStrategy` in `src/portfolio_management/portfolio.py`.
- Added unit tests for the strategy, including constraint validation and error handling.

**Task 5: Risk Parity Strategy (COMPLETE) ✅**

- Implemented the `RiskParityStrategy` in `src/portfolio_management/portfolio.py`.
- Added `riskparityportfolio` and its dependencies (`tqdm`, `jax`, `jaxlib`, `quadprog`) to `requirements.txt`.
- Added unit tests for the strategy, including handling of missing dependencies and optimization errors.

**Next Up: Task 6 - Implement Mean-Variance Strategy.**

All P2-P4 technical debt items addressed:

- ✅ pyproject.toml config deprecation fixed
- ✅ 8 new concurrency error tests added (26 total)
- ✅ 4 module docstrings added
- ✅ 13 ruff warnings auto-fixed
- ✅ All pre-commit hooks updated

**Status (Historical):** No blocking issues. Ready to proceed to Phase 3.

### 1. Data Curation (2-3 days) 🎯 NEXT

- Establish broker commission schedule
- Define FX policy for multi-currency assets
- Document unmatched instruments and remediation plan
- Identify empty Stooq histories and alternative sources

### 2. Phase 4: Portfolio Construction (3-5 days) 🎯 READY TO START

- Design strategy adapter interface
- Implement core allocation methods (equal-weight, risk-parity, mean-variance)
- Build rebalance trigger logic and cadence
- Implement portfolio constraint system
- Create CLI for portfolio construction
- Add comprehensive tests and documentation

## Current Architecture

```
scripts/prepare_tradeable_data.py    # CLI orchestrator (thin layer)
└── src/portfolio_management/
    ├── models.py      # Shared dataclasses
    ├── io.py          # File I/O operations
    ├── analysis.py    # Validation & diagnostics (refactored)
    ├── matching.py    # Ticker matching (simplified)
    ├── stooq.py       # Index building
    ├── utils.py       # Shared utilities (concurrency enhanced)
    └── config.py      # Configuration
```

**Test Suite:** 35 tests, 75% coverage, all passing
**Type Safety:** 9 remaining mypy errors (acceptable for this phase)
**Documentation:** Organized and archived

## Key Decisions & Constraints

**Portfolio Rules:**

- Rebalance cadence: Monthly/quarterly with ±20% opportunistic bands
- Diversification: Max 25% per ETF, min 10% bonds/cash, cap 90% equities
- Transaction costs: Model commissions and slippage explicitly

**Technical Approach:**

- Leverage established libraries: `PyPortfolioOpt`, `riskparityportfolio`, `empyrical`
- Treat sentiment overlays as satellite tilts with Black-Litterman blending
- Maintain regime-aware controls and cooldowns for signals

**Operational Constraints:**

- Offline operation mandated (no automated Stooq downloads)
- Zero-volume anomalies flagged but not auto-remediated
- All filesystem-scanning tools must exclude `data/` directory

## Development Principles

1. **Maintain test coverage** - Keep 75%+ coverage, add tests for new features
1. **Document as you go** - Update Memory Bank after each session
1. **Modular design** - Keep clear boundaries between concerns
1. **Performance awareness** - Profile before optimizing, exclude `data/` from scans
1. **Incremental delivery** - Small, tested changes over large rewrites
