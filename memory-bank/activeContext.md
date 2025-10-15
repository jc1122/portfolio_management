# Active Context

## Current Focus

**Phase 1 Complete:** Data preparation pipeline successfully modularized and tested.
**Next Phase:** Address technical debt, then begin portfolio construction layer design.

## Recent Changes (Latest Session - All Technical Debt Tasks Complete)

- ✅ **Task 1: Type Annotations** - Installed pandas-stubs, added TypeVar generics, parameterized Counter/dict types throughout codebase
  * mypy errors: 40+ → 9 (78% reduction)
  * All 17 original tests remain passing, 75% coverage maintained
- ✅ **Task 2: Concurrency Implementation** - Enhanced `_run_in_parallel` with ordering, error handling, diagnostics
  * 18 new comprehensive tests, all passing
  * Total test suite: 35 tests passing (17 original + 18 new), zero regressions
- ✅ **Task 3: Matching Logic Simplification** - Reduced matching complexity by 55%
  * Extracted helper methods in all three strategy classes
  * Centralized extension validation logic
  * Module-level helper functions for extension computation
  * 17% reduction in strategy code lines
- ✅ **Task 4: Analysis Helpers Tightening** - Improved summarize_price_file pipeline
  * Extracted diagnostics initialization helper
  * Centralized status determination logic
  * Explicit 5-stage pipeline with comments
  * 26% reduction in summarize_price_file length

## Immediate Next Steps

### 1. Commit All Changes (Ready Now)
- All 4 technical debt tasks complete and tested
- 35/35 tests passing with zero regressions
- Branch: scripts/prepare_tradeable_data.py-refactor
- Commit message: "refactor: complete technical debt resolution (Tasks 1-4)"
- Create comprehensive PR summary documenting all improvements

### 2. Data Curation (2-3 days)
- Establish broker commission schedule
- Define FX policy for multi-currency assets
- Document unmatched instruments and remediation plan
- Identify empty Stooq histories and alternative sources

### 3. Portfolio Construction Design (3-5 days)
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
    ├── analysis.py    # Validation & diagnostics
    ├── matching.py    # Ticker matching heuristics
    ├── stooq.py       # Index building
    ├── utils.py       # Shared utilities
    └── config.py      # Configuration (existing)
```

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
2. **Document as you go** - Update Memory Bank after each session
3. **Modular design** - Keep clear boundaries between concerns
4. **Performance awareness** - Profile before optimizing, exclude `data/` from scans
5. **Incremental delivery** - Small, tested changes over large rewrites
