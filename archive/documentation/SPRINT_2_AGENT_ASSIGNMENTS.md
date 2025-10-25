# Sprint 2 – Agent Assignments Summary

**Date:** October 23, 2025
**Status:** ✅ ALL AGENTS ASSIGNED & READY
**Base Branch:** `main` (commit 4c332c8)
**Total Issues:** 5 (#37-#41)
**Parallel Tracks:** 3 (Phase 1) + 1 (Phase 2) + 1 (Final)

______________________________________________________________________

## 🎯 IMMEDIATE ASSIGNMENTS (Start Now – Oct 23)

### ✅ AGENT 1: Issue #37 – Backtest Integration

```
Branch:     copilot/issue-37-backtest-integration
Priority:   PRIMARY (unblocks #38)
Duration:   2-3 days
Status:     ASSIGNED ✅ Ready to work

Goal: Wire preselection, membership policy, and PIT eligibility into run_backtest.py
      and manage_universes.py for end-to-end integration testing.

Quick Start:
1. Review issue #37 on GitHub
2. Check out: git checkout copilot/issue-37-backtest-integration
3. Read: SPRINT_2_ASSIGNMENT.md (section "Issue #37")
4. Modify:
   - scripts/run_backtest.py (add CLI flags)
   - scripts/manage_universes.py (YAML mapping)
   - Add integration tests
5. Ensure backward compatibility (existing features work unchanged)

Success = Single command runs top-30 strategy with all new features enabled
```

### ✅ AGENT 2: Issue #40 – Optional Fast IO

```
Branch:     copilot/issue-40-fast-io
Priority:   SECONDARY (independent)
Duration:   2-3 days
Status:     ASSIGNED ✅ Ready to work

Goal: Implement optional polars/pyarrow CSV/Parquet reading while keeping
      pandas as default. Include benchmarks showing speedup.

Quick Start:
1. Review issue #40 on GitHub
2. Check out: git checkout copilot/issue-40-fast-io
3. Read: SPRINT_2_ASSIGNMENT.md (section "Issue #40")
4. Create:
   - src/portfolio_management/data/io.py (abstraction layer)
   - Implement backends: pandas (default), polars (if installed), pyarrow (if installed)
5. Add CLI flag: --use-fast-io
6. Add benchmarks & correctness tests

Success = Results identical to pandas + 30-50% speedup on long_history_1000
```

### ✅ AGENT 3: Issue #41 – Advanced Cardinality Design

```
Branch:     copilot/issue-41-cardinality-design
Priority:   SECONDARY (independent)
Duration:   1-2 days
Status:     ASSIGNED ✅ Ready to work

Goal: Design and stub interfaces for future cardinality-constrained optimization.
      (Design only – no solver implementation.)

Quick Start:
1. Review issue #41 on GitHub
2. Check out: git checkout copilot/issue-41-cardinality-design
3. Read: SPRINT_2_ASSIGNMENT.md (section "Issue #41")
4. Create:
   - src/portfolio_management/portfolio/construction/cardinality.py (interfaces)
   - docs/cardinality_design.md (design rationale)
5. Extend BacktestConfig with cardinality flags (feature-flagged)
6. Add stubs that raise NotImplementedError with guidance

Success = Code compiles, interfaces clear, design document explains future work
```

______________________________________________________________________

## ⏳ QUEUED ASSIGNMENTS (Start After Phase 1 Merges – ~Oct 26)

### ⏳ AGENT 4: Issue #38 – Caching

```
Branch:     copilot/issue-38-caching (create after #37 merges)
Priority:   TERTIARY (enhances Phase 1)
Duration:   2-3 days
Status:     QUEUED – Assign after #37 PR approved & merged
Start Date: ~October 26-27

Goal: Implement on-disk caching for factor scores and PIT eligibility masks
      to reduce recomputation in backtests.

Waiting For:
- Issue #37 to merge (provides integration point to cache against)
- Will be assigned when #37 is in final review

Quick Start (when assigned):
1. Review issue #38 on GitHub
2. Check out: git checkout copilot/issue-38-caching
3. Read: SPRINT_2_ASSIGNMENT.md (section "Issue #38")
4. Create:
   - src/portfolio_management/caching/factor_cache.py
   - Implement cache key: hash(dataset) + hash(config) + date_range
   - Implement invalidation logic
5. Integrate with preselection & PIT eligibility modules
6. Add correctness tests (cached == uncached)

Success = 50%+ speedup on 2nd run with same config, zero correctness issues
```

______________________________________________________________________

## 📚 DEFERRED ASSIGNMENT (Start After All Code – ~Oct 28)

### 📚 ISSUE #39 – Documentation

```
Branch:     copilot/issue-39-documentation (create after #38 merges)
Priority:   LOWEST (documentation after code)
Duration:   1-2 days
Status:     DEFERRED – Assign after phases 1-2a complete
Start Date: ~October 28-29

Goal: Update documentation with new workflow pieces and examples.

Waiting For:
- All code to be merged and tested
- Will be assigned after #37, #40, #41, #38 are merged to main

Scope:
- docs/asset_selection.md (preselection)
- docs/universes.md (YAML config examples)
- docs/backtesting.md (workflow & feature interactions)
- docs/cardinality_design.md (from #41)
- Add fast IO docs (from #40)
- Add caching docs (from #38)
- Runnable examples for all new features

Success = Readers can configure and run features from documentation alone
```

______________________________________________________________________

## 🔄 Execution Flow

```
NOW (Oct 23):
┌─────────────────────────────────────────────┐
│ START:                                      │
│ ├─ Agent 1 → #37 (Backtest Integration)    │
│ ├─ Agent 2 → #40 (Fast IO)                 │
│ └─ Agent 3 → #41 (Cardinality Design)      │
└─────────────────────────────────────────────┘
    ↓ (2-3 days)
Oct 25-26:
┌─────────────────────────────────────────────┐
│ PR REVIEW & MERGE:                          │
│ ├─ #37 approved & merged                    │
│ ├─ #40 approved & merged                    │
│ └─ #41 approved & merged                    │
└─────────────────────────────────────────────┘
    ↓ (assign Agent 4)
Oct 26-27:
┌─────────────────────────────────────────────┐
│ START:                                      │
│ └─ Agent 4 → #38 (Caching)                 │
└─────────────────────────────────────────────┘
    ↓ (2-3 days)
Oct 27-28:
┌─────────────────────────────────────────────┐
│ PR REVIEW & MERGE:                          │
│ └─ #38 approved & merged                    │
└─────────────────────────────────────────────┘
    ↓ (assign writer)
Oct 28-29:
┌─────────────────────────────────────────────┐
│ START:                                      │
│ └─ Writer → #39 (Documentation)            │
└─────────────────────────────────────────────┘
    ↓ (1-2 days)
Oct 29:
┌─────────────────────────────────────────────┐
│ COMPLETE:                                   │
│ ├─ #39 approved & merged                    │
│ └─ Sprint 2: ✅ ALL DONE                    │
└─────────────────────────────────────────────┘
```

______________________________________________________________________

## 📋 What Each Agent Should Do First

### All Agents (Same Steps)

1. **Read the context:**

   ```bash
   # Understand the project
   cat SPRINT_2_ASSIGNMENT.md      # Detailed scope
   cat SPRINT_2_QUICK_START.md     # FAQ & quick ref
   cat SPRINT_2_REVIEW_REPORT.md   # Full analysis

   # Understand the codebase
   cat memory-bank/systemPatterns.md    # Code patterns
   cat memory-bank/techContext.md       # Tech stack
   cat memory-bank/activeContext.md     # Current state
   ```

1. **Check out your branch:**

   ```bash
   git fetch origin
   git checkout copilot/issue-{N}-{description}
   git status
   ```

1. **Read your GitHub issue:**

   - Go to https://github.com/jc1122/portfolio_management/issues/{N}
   - Read the full description
   - Understand acceptance criteria

1. **Run tests to establish baseline:**

   ```bash
   pytest tests/ -v
   # Expected: 519 tests passing
   ```

1. **Start coding:**

   - Follow code patterns from systemPatterns.md
   - Write tests as you go
   - Run mypy & ruff frequently
   - Commit early & often

______________________________________________________________________

## 🎯 Key Files to Know

### Config & Models

- `src/portfolio_management/backtesting/models.py` – BacktestConfig (extend for new features)
- `src/portfolio_management/backtesting/engine/backtest.py` – Main backtest logic
- `config/universes_long_history.yaml` – Example universe config

### Scripts

- `scripts/run_backtest.py` – CLI entry point (add flags here)
- `scripts/manage_universes.py` – Universe management
- `scripts/prepare_tradeable_data.py` – Data preparation

### Portfolio Construction

- `src/portfolio_management/portfolio/` – All portfolio-related modules
  - `preselection.py` – Factor-based selection (Sprint 1)
  - `membership.py` – Turnover management (Sprint 1)

### Testing

- `tests/backtesting/` – Backtest integration tests
- `tests/portfolio/` – Portfolio module tests
- `pytest.ini` – Test configuration

______________________________________________________________________

## 💡 Tips for Success

### Code Quality

- Run `mypy --config-file mypy.ini src/` before pushing
- Run `ruff check src/` before pushing
- Aim for 100% coverage on new code

### Testing

- Write unit tests for all new functions
- Write integration tests for CLI changes
- Test edge cases and error handling
- Run full suite before PR: `pytest tests/`

### Git Workflow

- Commit frequently with clear messages
- Push early & often
- Create PR with description matching issue
- Ask for review when ready

### Documentation

- Add docstrings (Google style) to all public functions
- Add type hints (Python 3.12+)
- Update README if adding new CLI flags
- Add examples in docstrings

### Backward Compatibility

- New features should default to DISABLED
- Existing tests should still pass
- CLI flags should be optional
- No breaking changes to existing APIs

______________________________________________________________________

## ✅ Before You Submit a PR

- \[ \] All tests pass locally: `pytest tests/`
- \[ \] Mypy clean: `mypy --config-file mypy.ini src/`
- \[ \] Ruff clean: `ruff check src/`
- \[ \] Code follows project patterns
- \[ \] New functions have docstrings & type hints
- \[ \] New code has unit tests
- \[ \] Integration tests added if needed
- \[ \] Backward compatibility preserved
- \[ \] Feature defaults to disabled (if applicable)
- \[ \] PR description references issue #N
- \[ \] Acceptance criteria from issue are met

______________________________________________________________________

## 🚨 If You Get Stuck

1. **Check memory bank:** `memory-bank/activeContext.md` – current system state
1. **Check system patterns:** `memory-bank/systemPatterns.md` – how we do things
1. **Check tech context:** `memory-bank/techContext.md` – dependencies & tools
1. **Review Sprint 1 code:** Issues #31-#36 already merged; look at their implementations
1. **Run tests:** See if existing tests give hints
1. **Ask in PR:** Create draft PR early, ask questions in comments

______________________________________________________________________

## 📞 Communication

- **GitHub Issues:** Reference issue #N in commits and PRs
- **PR Descriptions:** Explain what changed and why
- **Code Comments:** Document complex logic inline
- **Test Names:** Make test names describe what's being tested

______________________________________________________________________

## 🎖️ Sprint Success Criteria

**Sprint 2 is complete when:**

- \[ \] All 5 issues closed (#37-#41)
- \[ \] All PRs merged to main
- \[ \] 520+ tests passing
- \[ \] Zero mypy errors
- \[ \] Zero ruff errors
- \[ \] Documentation updated
- \[ \] Benchmarks available (where applicable)

**Current Status:** ✅ Ready to launch

______________________________________________________________________

## 📚 Quick Links

- **Sprint 2 Assignment Plan:** `SPRINT_2_ASSIGNMENT.md`
- **Quick Start & FAQ:** `SPRINT_2_QUICK_START.md`
- **Full Review Report:** `SPRINT_2_REVIEW_REPORT.md` ← Start here for context
- **Memory Bank:** `memory-bank/` ← Everything about project state
- **GitHub Issues:** https://github.com/jc1122/portfolio_management/issues?q=is%3Aopen+is%3Aissue
- **Main Branch:** https://github.com/jc1122/portfolio_management/tree/main

______________________________________________________________________

**Generated:** October 23, 2025
**Status:** ✅ ALL SYSTEMS GO
**Next Step:** Agents begin work immediately
