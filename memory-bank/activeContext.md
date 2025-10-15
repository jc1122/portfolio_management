# Active Context

## Current Focus

**Phase 1 Complete:** Data preparation pipeline successfully modularized and tested.
**Phase 2 Complete:** Technical debt resolution - type safety, concurrency, complexity reduction.
**Next Phase:** Data curation, then begin portfolio construction layer design.

## Recent Changes (Latest Session - Technical Debt Complete + Documentation Cleanup)

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

## Immediate Next Steps

### 1. Data Curation (2-3 days) 🎯 NEXT

- Establish broker commission schedule
- Define FX policy for multi-currency assets
- Document unmatched instruments and remediation plan
- Identify empty Stooq histories and alternative sources

### 2. Portfolio Construction Design (3-5 days)

- Design strategy adapter interface
- Plan core allocation methods (equal-weight, risk-parity, mean-variance)
- Specify rebalance trigger logic and cadence
- Define portfolio constraint system

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
