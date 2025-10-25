# Sprint 2 Assignment Plan

**Date:** October 23, 2025
**Status:** 3 Copilot agents assigned and ready to work in parallel
**Base Branch:** `main` (commit `4c332c8`)
**Epic:** #42 - Sprint 1 Follow-up Tasks

______________________________________________________________________

## Sprint Overview

**Previous Sprint (Sprint 1):** ✅ COMPLETE

- Issues #31-#36 merged and closed
- Features: preselection, clustering, technical indicators, macro signals, membership policy, PIT eligibility
- 519 tests passing, production-ready code

**Current Sprint (Sprint 2):** 📋 OPEN & ASSIGNED

- 5 open enhancement issues (#37-#41)
- 3 issues assigned to Copilot agents (can run in parallel)
- 1 issue queued for parallel secondary phase
- 1 issue deferred (documentation - requires code completion first)

______________________________________________________________________

## 🎯 Parallelization Strategy

The sprint is divided into two phases to maximize parallel development:

### Phase 1: Three Parallel Agent Tracks (Can Start Immediately)

These issues have **zero interdependencies** and can proceed in parallel from `main`.

#### ✅ TRACK 1: Issue #37 – Backtest Integration (PRIMARY)

**Branch:** `copilot/issue-37-backtest-integration`
**Assigned:** ✅ Copilot Agent
**Status:** Ready to start
**Priority:** PRIMARY - Unblocks other work

**Objective:**
Integrate the new preselection, membership policy, and PIT eligibility into the existing backtest and managed universe workflows.

**Scope:**

- Wire `scripts/run_backtest.py` flags for preselection, membership policy, PIT eligibility
- Update `manage_universes.py` to map universe YAML blocks to backtest arguments
- Add end-to-end smoke tests using long_history datasets
- Ensure backward compatibility (existing strategies work unchanged when features disabled)

**Acceptance Criteria:**

- Single command runs top-30 strategy with PIT eligibility and membership policy enabled
- Existing strategies (1/N, MV, risk parity) work unchanged when features disabled
- All tests pass

**Key Files to Modify:**

- `scripts/run_backtest.py` - add validation and flag handling
- `scripts/manage_universes.py` - YAML to backtest args mapping
- `src/portfolio_management/backtesting/models.py` - verify BacktestConfig
- Test files for integration validation

**Dependencies:**

- Requires Sprint 1 features (#31-#36) - ✅ ALREADY MERGED
- No blockers

______________________________________________________________________

#### ✅ TRACK 2: Issue #40 – Optional Fast IO (INDEPENDENT)

**Branch:** `copilot/issue-40-fast-io`
**Assigned:** ✅ Copilot Agent
**Status:** Ready to start
**Priority:** SECONDARY - Performance enhancement

**Objective:**
Offer optional faster IO paths for large datasets while preserving the pandas default.

**Scope:**

- Feature-flagged CSV/Parquet reading via polars or pyarrow (if installed)
- Benchmarks on long_history datasets; report indicative speedups
- Update docs to explain opt-in and compatibility

**Acceptance Criteria:**

- Enabling fast IO does not change results
- Shows measurable speed improvement on large inputs (long_history_1000+)
- Default behavior remains pandas (backward compatible)

**Key Decisions:**

- Polars/PyArrow are optional dependencies (graceful fallback)
- CSV and Parquet support both
- Results must be bitwise-identical to pandas version
- Configuration via CLI flag and YAML setting

**Key Files to Modify:**

- `src/portfolio_management/data/` - add IO abstraction layer
- `scripts/run_backtest.py` - add `--use-fast-io` flag
- `scripts/prepare_tradeable_data.py` - apply fast IO option
- Tests for correctness equivalence

**Dependencies:**

- No code dependencies (self-contained feature)
- Can develop independently

______________________________________________________________________

#### ✅ TRACK 3: Issue #41 – Advanced Cardinality Design (DESIGN-ONLY)

**Branch:** `copilot/issue-41-cardinality-design`
**Assigned:** ✅ Copilot Agent
**Status:** Ready to start
**Priority:** SECONDARY - Design groundwork

**Objective:**
Design and stub interfaces for future cardinality constraints inside the optimizer (no solver implementation).

**Scope:**

- Define interfaces/config for cardinality-constrained optimization
- Add NotImplemented paths behind feature flag
- Document trade-offs vs preselection approach
- Brief design notes comparing strategies

**Acceptance Criteria:**

- Codebase compiles with stubs
- Clear extension points documented
- Design document explains rationale and future extensions

**Design Decisions to Make:**

- Should cardinality be per-optimizer or universal?
- Configuration structure (max_nonzero, group constraints)?
- Integration point with existing optimizer classes?
- Error messages when NotImplemented is hit?

**Key Files to Modify:**

- `src/portfolio_management/portfolio/construction/` - add cardinality interfaces
- `src/portfolio_management/backtesting/models.py` - extend BacktestConfig
- `docs/` - design document
- Test stubs with NotImplemented checks

**Dependencies:**

- No code dependencies
- Pure design/interface work
- Can proceed in parallel

______________________________________________________________________

### Phase 2: Sequential Follow-up

#### ⏳ TRACK 4: Issue #38 – Caching (Can Start After #37)

**Branch:** Will be created after #37 PR review
**Status:** QUEUED for phase 2
**Priority:** TERTIARY - Optimization

**Objective:**
Reduce recomputation in backtests by caching per-asset, per-date factor scores and PIT eligibility.

**Scope:**

- Add simple on-disk cache (keyed by dataset hash + config hash + date range)
- Invalidation logic when inputs or params change
- Toggle via CLI/YAML; default on for backtests
- Tests: cache hits/misses and correctness equivalence

**Dependencies:**

- ✅ Sprint 1 features (#31-#36) - already available
- ⏳ #37 (Backtest Integration) - can start after #37 is merged
- Reason: Caching needs the integrated backtest pipeline to test against

**Timeline:**

- Start after #37 PR is approved and merged
- Estimated start: ~2-3 days into sprint (after #37 is reviewed)

______________________________________________________________________

#### 📚 TRACK 5: Issue #39 – Documentation (DEFERRED)

**Status:** DEFERRED until Phase 2 complete
**Priority:** LOWEST - Documentation (update after code)

**Objective:**
Update documentation and examples to cover new workflow pieces.

**Scope:**

- `docs/asset_selection.md` - clarify technical vs financial preselection
- `docs/universes.md` - add YAML blocks (preselection, membership_policy, eligibility)
- `docs/backtesting.md` - show top-K flow and policy interactions
- Add runnable example commands and expected outputs

**Dependencies:**

- ✅ #37 (Backtest Integration) - code must be complete
- ✅ #38 (Caching) - optional, but good to document
- ✅ #40 (Fast IO) - optional, but document if done
- ✅ #41 (Cardinality Design) - document design

**Rationale:**
Documentation should follow implementation to ensure accuracy and completeness. Write code first, document patterns second.

**Timeline:**

- Start after phases 1-2 are merged (~4-5 days into sprint)
- Writer can reference merged code and actual behavior

______________________________________________________________________

## 🚀 Execution Timeline

```
Day 1-3: Phase 1 (3 parallel tracks)
├─ Track 1: #37 (Backtest Integration) - PRIMARY
├─ Track 2: #40 (Fast IO) - PARALLEL
└─ Track 3: #41 (Cardinality Design) - PARALLEL
    ↓
Phase 1 PRs reviewed and merged (~day 3-4)
    ↓
Day 4-5: Phase 2a (Track 4)
├─ Track 4: #38 (Caching) - AFTER #37 merged
    ↓
Phase 2a merged (~day 5-6)
    ↓
Day 6-7: Phase 2b (Track 5)
└─ Track 5: #39 (Documentation) - AFTER all code
```

______________________________________________________________________

## 🔧 Technical Guidelines for Agents

### Branch Strategy

- **Base:** All branches start from `main` (commit `4c332c8`)
- **Naming:** `copilot/issue-{N}-{description}`
- **PR Target:** Back to `main` via Pull Request
- **Merge Strategy:** Squash or fast-forward (no merge commits)

### Code Quality Standards

- Follow existing project patterns (see `memory-bank/systemPatterns.md`)
- Maintain 100% test coverage for new code
- Run pre-commit hooks: `mypy`, `ruff`, `pylint`
- Update docstrings using existing style
- Run full test suite before PR: `pytest tests/`

### Configuration Management

- New features should default to **disabled** (backward compatible)
- Add CLI flags for new features to `run_backtest.py`
- Add YAML config blocks for universe-level settings
- Document all new config options in docstrings

### Testing Requirements

- Unit tests for all new functions
- Integration tests for backtest pipeline
- Parametrized tests for edge cases
- Mock external dependencies where appropriate

### Documentation Requirements

- Docstrings on all public functions (Google style)
- README updates if new CLI arguments added
- Inline comments for complex logic
- Type hints throughout (Python 3.12+)

______________________________________________________________________

## 📋 Key Contacts & References

**Project Context:**

- Memory Bank: `memory-bank/` directory
- System Patterns: `memory-bank/systemPatterns.md`
- Tech Context: `memory-bank/techContext.md`
- Active Progress: `memory-bank/activeContext.md`

**Codebase Landmarks:**

- Backtest engine: `src/portfolio_management/backtesting/`
- Portfolio construction: `src/portfolio_management/portfolio/`
- CLI scripts: `scripts/run_backtest.py`, `scripts/manage_universes.py`
- Test suite: `tests/`

**Dependencies Already Available:**

- Sprint 1 features: preselection, clustering, macro signals, technical indicators
- BacktestConfig: Extended with feature flags
- CLI framework: argparse setup in run_backtest.py

______________________________________________________________________

## ✅ Status Checklist

- \[x\] Sprint 1 complete (issues #31-#36 merged)
- \[x\] Sprint 2 issues identified and prioritized (#37-#41)
- \[x\] Parallelization strategy defined
- \[x\] Three branches created from `main`
- \[x\] Three Copilot agents assigned (Track 1, 2, 3)
- \[x\] Dependency analysis complete
- \[x\] Deferred items identified (Track 5)
- \[x\] Sequential phase planned (Track 4)
- \[x\] Technical guidelines prepared

______________________________________________________________________

**Next Steps:**

1. Copilot agents begin work on assigned issues (Tracks 1-3)
1. Monitor PR creation and test results
1. Review and approve PRs as they arrive
1. Assign Track 4 after Track 1 merges
1. Assign Track 5 after Track 2 merges
