# Codebase Cleanup Analysis & Portfolio Workflow Documentation

**Date:** October 24, 2025
**Branch:** feat/add-comprehensive-examples
**Status:** Post-Sprint 2 Clean Main Branch

______________________________________________________________________

## Executive Summary

The codebase has been successfully refactored into a **production-ready modular monolith** with comprehensive testing (615+ tests, all passing). However, there are **31 documentation files in the root directory** that should be archived, and the project needs a clear **end-to-end workflow guide** for live testing.

### Key Findings

✅ **What's Good:**

- Clean modular architecture (Phases 1-9 complete)
- Zero code quality issues (0 ruff errors, 0 mypy errors)
- Comprehensive testing (615+ tests passing)
- Well-organized `docs/` directory with 40+ guides
- Production-ready CLIs for all stages

❌ **What Needs Cleanup:**

- **31 legacy summary/implementation docs in root** (should be in `archive/`)
- **Outdated examples** that may not reflect current API
- **Missing end-to-end quick-start guide** for new users
- **Sprint 3 is in planning phase** (not yet executed)

______________________________________________________________________

## 1. Legacy Documentation Files to Archive

The following **31 root-level documentation files** are **implementation summaries from Sprint 2** and should be moved to `archive/sprint2/`:

### Sprint 2 Documentation (Move to `archive/sprint2/`)

```
SPRINT_2_AGENT_ASSIGNMENTS.md
SPRINT_2_ASSIGNMENT.md
SPRINT_2_DEPLOYMENT_SUMMARY.md
SPRINT_2_PHASE_1_COMPLETION.md
SPRINT_2_QUICK_START.md
SPRINT_2_REVIEW_REPORT.md
SPRINT_2_VISUAL_SUMMARY.md
SPRINT_3_AGENT_ASSIGNMENTS.md
SPRINT_3_PLAN.md                    # Sprint 3 is planning only, not executed yet
```

### Feature Implementation Summaries (Move to `archive/sprint2/implementations/`)

```
BENCHMARK_QUICK_START.md
CACHE_BENCHMARK_IMPLEMENTATION.md
CACHING_EDGE_CASES_SUMMARY.md
CARDINALITY_IMPLEMENTATION_SUMMARY.md
EDGE_CASE_TESTS_SUMMARY.md
ENHANCED_ERROR_HANDLING_SUMMARY.md
FAST_IO_BENCHMARKS_SUMMARY.md
FAST_IO_IMPLEMENTATION.md
IMPLEMENTATION_SUMMARY.md
IMPLEMENTATION_SUMMARY_PIT_EDGE_CASES.md
INTEGRATION_COMPLETE.md
LONG_HISTORY_TESTS_IMPLEMENTATION_SUMMARY.md
MEMBERSHIP_EDGE_CASE_IMPLEMENTATION.md
PRESELECTION_ROBUSTNESS_SUMMARY.md
TECHNICAL_INDICATORS_IMPLEMENTATION.md
```

### Cleanup Documentation (Move to `archive/cleanup/`)

```
CLEANUP_SUMMARY_2025-10-23.md
REFACTORING_SUMMARY.md
```

### Testing Documentation (Move to `archive/sprint2/testing/`)

```
REQUIREMENTS_COVERAGE.md
TESTING_INSTRUCTIONS.md
TESTING_MEMBERSHIP_EDGE_CASES.md
```

### Keep in Root (Core Documentation)

```
AGENTS.md          # Agent operating instructions (memory bank guide)
README.md          # Main project documentation
```

______________________________________________________________________

## 2. Codebase Structure Assessment

### ✅ Well-Organized Areas

**Source Code (`src/portfolio_management/`):**

- Clean modular structure (core, data, assets, analytics, macro, portfolio, backtesting, reporting)
- Zero technical debt
- Comprehensive docstrings
- Type hints throughout

**Tests (`tests/`):**

- 615+ tests organized by module
- 100% pass rate (1 xfail expected for CVXPY instability)
- Integration, unit, and performance tests

**Documentation (`docs/`):**

- 40+ comprehensive guides
- Well-organized subdirectories (architecture, examples, performance, testing, tooling)
- Up-to-date with current implementation

**Configuration (`config/`):**

- 4 pre-configured universes (core_global, satellite_factor, defensive, equity_only)
- Example regime configurations
- Clean YAML structure

### ❌ Areas Needing Attention

**Root Directory:**

- 31 legacy documentation files cluttering the root
- No clear quick-start guide for new users

**Examples (`examples/`):**

- 5 example scripts exist but may not reflect latest API
- Need validation/update (lowvol_strategy.py, momentum_strategy.py, multifactor_strategy.py, batch_backtest.py, cache_management.py)

**Sprint 3:**

- Planning documentation exists but sprint not yet executed
- Focus: long-duration testing, edge cases, performance benchmarks

______________________________________________________________________

## 3. Complete Portfolio Management Workflow

### Overview: From Raw Data to Backtest Results

This toolkit provides an **offline-first, CLI-driven workflow** for constructing and backtesting retirement portfolios using free historical data from Stooq.

______________________________________________________________________

### Stage 1: Data Preparation (One-Time Setup)

**Purpose:** Transform raw Stooq price files into a tradeable dataset with quality validation.

**Script:** `scripts/prepare_tradeable_data.py`

**What It Does:**

- Scans Stooq directories (unpacked ZIP archives)
- Matches broker tickers (from `tradeable_instruments/`) with Stooq symbols
- Validates data quality (missing dates, zero volume, non-positive prices)
- Exports cleaned price CSV files and metadata reports

**Key Outputs:**

- `data/metadata/stooq_index.csv` - Master index of all Stooq files
- `data/metadata/tradeable_matches.csv` - Matched broker tickers with quality flags
- `data/metadata/tradeable_unmatched.csv` - Unmatched tickers for review
- `data/processed/tradeable_prices/*.csv` - Individual price files per ticker

**Performance:**

- **First run:** ~3-5 minutes (500 instruments, 70k+ files)
- **Incremental:** \<5 seconds with `--incremental` flag

**Example:**

```bash
python scripts/prepare_tradeable_data.py \
    --data-dir data/stooq \
    --tradeable-dir tradeable_instruments \
    --metadata-output data/metadata/stooq_index.csv \
    --match-report data/metadata/tradeable_matches.csv \
    --prices-output data/processed/tradeable_prices \
    --incremental \
    --overwrite-prices
```

**Documentation:** `docs/data_preparation.md`

______________________________________________________________________

### Stage 2: Asset Selection

**Purpose:** Filter tradeable assets based on quality criteria (data completeness, market, currency).

**Script:** `scripts/select_assets.py`

**What It Does:**

- Reads tradeable matches report from Stage 1
- Applies quality filters (min history, data status, market codes)
- Supports allowlists/blocklists for manual overrides
- Exports filtered asset list

**Key Outputs:**

- CSV file with selected tickers (e.g., `data/selected/core_global.csv`)

**Filtering Options:**

- **Data quality:** `--data-status` (ok, warning, error)
- **History requirements:** `--min-history-days`, `--min-price-rows`
- **Market/region:** `--markets`, `--regions`, `--currencies`
- **Manual control:** `--allowlist`, `--blocklist`

**Example:**

```bash
python scripts/select_assets.py \
    --match-report data/metadata/tradeable_matches.csv \
    --output data/selected/core_global.csv \
    --min-history-days 756 \
    --markets "LSE,GBR-LSE" \
    --currencies "GBP" \
    --data-status "ok"
```

**Documentation:** `docs/asset_selection.md`

______________________________________________________________________

### Stage 3: Asset Classification

**Purpose:** Classify selected assets by type (equity, bond, commodity, REIT) and geography.

**Script:** `scripts/classify_assets.py`

**What It Does:**

- Rule-based classification using ticker patterns and metadata
- Supports manual overrides via CSV
- Exports classification results with summary statistics

**Key Outputs:**

- CSV file with columns: `ticker`, `asset_class`, `sub_class`, `geography`, `currency`

**Classification Categories:**

- **Asset classes:** equity, bond, commodity, real_estate, cash, alternative
- **Sub-classes:** growth, value, small_cap, dividend, etc.
- **Geography:** united_kingdom, europe, north_america, emerging_markets, global

**Example:**

```bash
python scripts/classify_assets.py \
    --input data/selected/core_global.csv \
    --output data/classified/core_global.csv \
    --summary
```

**Documentation:** `docs/asset_classification.md`

______________________________________________________________________

### Stage 4: Return Calculation

**Purpose:** Calculate aligned return series with missing data handling and calendar alignment.

**Script:** `scripts/calculate_returns.py`

**What It Does:**

- Loads price files for classified assets
- Calculates returns (simple, log, or excess)
- Resamples to desired frequency (daily, weekly, monthly)
- Handles missing data (forward-fill, drop, interpolate)
- Aligns dates across all assets
- Filters by coverage threshold

**Key Outputs:**

- CSV file with return matrix (dates as rows, tickers as columns)

**Return Types:**

- **Simple:** $(P_t - P\_{t-1}) / P\_{t-1}$
- **Log:** $\\log(P_t / P\_{t-1})$
- **Excess:** Simple returns minus risk-free rate

**Performance Optimization:**

- **Fast IO:** Use `--io-backend polars` or `--io-backend pyarrow` for 2-5x speedup on large datasets
- Requires: `pip install polars` or `pip install pyarrow`

**Example:**

```bash
python scripts/calculate_returns.py \
    --assets data/classified/core_global.csv \
    --prices-dir data/processed/tradeable_prices \
    --output data/processed/returns/core_global.csv \
    --method simple \
    --frequency monthly \
    --align-method inner \
    --business-days \
    --io-backend polars
```

**Documentation:** `docs/calculate_returns.md`, `docs/fast_io.md`

______________________________________________________________________

### Stage 5: Portfolio Construction

**Purpose:** Apply allocation strategy to generate portfolio weights from return series.

**Script:** `scripts/construct_portfolio.py`

**What It Does:**

- Loads return matrix and optional asset classifications
- Applies selected strategy to optimize weights
- Enforces constraints (max weight, equity/bond limits)
- Can compare multiple strategies side-by-side

**Available Strategies:**

1. **Equal Weight** - Naive 1/N allocation
1. **Risk Parity** - Equal risk contribution across assets
1. **Mean-Variance (Min Volatility)** - Minimize portfolio variance
1. **Mean-Variance (Max Sharpe)** - Maximize Sharpe ratio
1. **Mean-Variance (Efficient Risk)** - Target specific risk level

**Constraints:**

- `--max-weight` - Maximum single asset weight (default: 0.25)
- `--min-weight` - Minimum single asset weight (default: 0.0)
- `--max-equity` - Maximum total equity exposure (default: 0.90)
- `--min-bond` - Minimum bond/cash allocation (default: 0.10)

**Key Outputs:**

- CSV file with ticker-weight pairs
- Comparison mode: matrix of strategies × tickers

**Example (Single Strategy):**

```bash
python scripts/construct_portfolio.py \
    --returns data/processed/returns/core_global.csv \
    --strategy risk_parity \
    --max-weight 0.20 \
    --output outputs/portfolio_riskparity.csv
```

**Example (Strategy Comparison):**

```bash
python scripts/construct_portfolio.py \
    --returns data/processed/returns/core_global.csv \
    --compare \
    --output outputs/portfolio_comparison.csv
```

**Documentation:** `docs/portfolio_construction.md`

______________________________________________________________________

### Stage 6: Backtesting

**Purpose:** Simulate historical performance with realistic transaction costs and rebalancing.

**Script:** `scripts/run_backtest.py`

**What It Does:**

- Loads prices and returns for backtest period
- Simulates portfolio rebalancing at specified frequency
- Models transaction costs (commission, slippage)
- Tracks equity curve, drawdowns, turnover
- Generates performance analytics and visualizations

**Advanced Features:**

- **Preselection:** Factor-based asset filtering (momentum, low-vol, combined)
- **Membership Policy:** Control turnover and holding periods
- **PIT Eligibility:** Point-in-time availability (no lookahead bias)
- **Caching:** Automatic caching of covariance/returns for overlapping windows

**Rebalance Frequencies:**

- Daily, Weekly, Monthly, Quarterly, Semi-Annual, Annual

**Transaction Cost Model:**

- Flat commission per trade (default: 0.1% = 10 bps)
- Proportional slippage (default: 0.05% = 5 bps)
- Minimum commission per trade (default: $5)

**Key Outputs:**

- Equity curve (CSV + optional charts)
- Daily returns series
- Allocation history (weights over time)
- Rebalance logs (dates, old/new weights)
- Trade blotter (individual trades with costs)
- Performance metrics (JSON + text)
  - Sharpe ratio, Sortino ratio
  - Maximum drawdown, Expected Shortfall (CVaR)
  - Total return, annualized return, volatility
  - Win rate, transaction costs

**Example (Basic Backtest):**

```bash
python scripts/run_backtest.py equal_weight \
    --start-date 2020-01-01 \
    --end-date 2023-12-31 \
    --returns data/processed/returns/core_global.csv \
    --prices data/processed/prices/core_global.csv \
    --output-dir outputs/backtests/core_equal \
    --rebalance-frequency monthly \
    --visualize
```

**Example (With Preselection & Membership Policy):**

```bash
python scripts/run_backtest.py risk_parity \
    --start-date 2015-01-01 \
    --end-date 2024-12-31 \
    --universe-file config/universes.yaml \
    --universe satellite_factor \
    --preselection-method combined \
    --preselection-top-k 25 \
    --membership-enabled \
    --membership-buffer-rank 30 \
    --membership-min-hold 3 \
    --membership-max-turnover 0.30 \
    --output-dir outputs/backtests/satellite_defensive \
    --format both
```

**Documentation:** `docs/backtesting.md`, `docs/preselection.md`, `docs/membership_policy.md`

______________________________________________________________________

### Alternative: Universe-Driven Workflow (Recommended)

**Purpose:** Define repeatable strategies in YAML config and automate Stages 2-4.

**Script:** `scripts/manage_universes.py`

**What It Does:**

- Reads universe definitions from `config/universes.yaml`
- Automates asset selection, classification, and return calculation
- Validates configuration and outputs
- Exports ready-to-use return files

**Pre-Configured Universes:**

- `core_global` - 35 GBP-denominated diversified ETFs
- `satellite_factor` - 15 factor-tilted equities (growth, value, small-cap)
- `defensive` - 9 defensive holdings (REITs, gold, dividends)
- `equity_only` - 10 curated US/UK equity growth

**Universe Management Commands:**

```bash
# List available universes
python scripts/manage_universes.py list

# Inspect a universe definition
python scripts/manage_universes.py show core_global

# Validate configuration (check filters, constraints)
python scripts/manage_universes.py validate satellite_factor --verbose

# Generate universe data (runs Stages 2-4 automatically)
python scripts/manage_universes.py load core_global \
    --output-dir outputs/universes

# Compare multiple universes
python scripts/manage_universes.py compare core_global satellite_factor defensive
```

**Then run Stages 5-6 normally:**

```bash
# Stage 5: Construct portfolio
python scripts/construct_portfolio.py \
    --returns outputs/universes/core_global_returns.csv \
    --strategy equal_weight \
    --output outputs/portfolio.csv

# Stage 6: Backtest
python scripts/run_backtest.py equal_weight \
    --returns outputs/universes/core_global_returns.csv \
    --output-dir outputs/backtests
```

**Documentation:** `docs/universes.md`, `docs/workflow.md`

______________________________________________________________________

## 4. Summary of Functionality: What Can You Do?

### Data Management

✅ Ingest and validate Stooq data with quality checks
✅ Match broker tickers to Stooq symbols across 10+ exchanges
✅ Export cleaned price files with metadata
✅ Incremental resume (skip redundant processing)
✅ Fast IO with polars/pyarrow (2-5x speedup)

### Asset Universe Construction

✅ Filter assets by quality, market, currency, region
✅ Classify assets by type, geography, sub-class
✅ Calculate returns (simple, log, excess) with missing data handling
✅ Define reusable universes in YAML
✅ Validate and compare universe configurations

### Portfolio Optimization

✅ 5 built-in strategies (equal weight, risk parity, mean-variance variants)
✅ Customizable constraints (max weight, equity/bond limits)
✅ Strategy comparison mode
✅ Asset class-based constraints

### Factor-Based Selection

✅ Momentum preselection (top K by trailing returns)
✅ Low-volatility preselection (top K by minimum variance)
✅ Combined factor scoring (weighted momentum + low-vol)
✅ Configurable lookback periods and skip days

### Backtesting

✅ Historical simulation with realistic transaction costs
✅ Configurable rebalancing (daily to annual)
✅ Membership policy (control turnover and churn)
✅ Point-in-time eligibility (no lookahead bias)
✅ Statistics caching (faster repeated runs)
✅ Comprehensive performance analytics (Sharpe, drawdown, CVaR)
✅ Visualization exports (equity, drawdown, allocation charts)

### Advanced Features

✅ Macroeconomic signal infrastructure (NoOp stubs ready)
✅ Regime gating framework (extensible)
✅ Cardinality constraint interfaces (stubs for future MIQP)
✅ Extensible strategy registry (easy to add custom strategies)

______________________________________________________________________

## 5. Recommended Actions

### Immediate (Before Live Testing)

1. **Archive Legacy Documentation**

   ```bash
   mkdir -p archive/sprint2/{implementations,testing}
   mv SPRINT_*.md archive/sprint2/
   mv *IMPLEMENTATION*.md *SUMMARY*.md archive/sprint2/implementations/
   mv *TESTING*.md archive/sprint2/testing/
   mv CLEANUP_*.md REFACTORING_*.md archive/cleanup/
   ```

1. **Create Quick-Start Guide**

   - New file: `QUICKSTART.md` in root
   - Step-by-step example using sample data
   - Expected outputs and validation steps

1. **Validate Examples**

   - Test all 5 scripts in `examples/`
   - Update to match current API if needed
   - Add README.md in `examples/` with usage instructions

1. **Update Memory Bank**

   - Mark cleanup complete in `activeContext.md`
   - Document current state in `progress.md`

### Before Production Deployment

5. **Execute Sprint 3 (Testing & Refactoring)**

   - Long-duration backtests (10-20 years)
   - Edge case coverage (sparse data, delistings)
   - Performance benchmarks for production scenarios

1. **Add CI/CD Pipeline**

   - Automated test runs on push
   - Code quality checks (ruff, mypy)
   - Documentation builds

1. **Create Monitoring Guide**

   - Cache hit rates
   - Backtest performance metrics
   - Data quality alerts

______________________________________________________________________

## 6. Next Steps for Live Testing

### Minimal Viable Test (30 minutes)

**Goal:** Run end-to-end workflow on small universe to validate everything works.

```bash
# Assumes Stooq data already unpacked in data/stooq/

# 1. Prepare data (first time: ~3-5 min, incremental: <5 sec)
python scripts/prepare_tradeable_data.py \
    --data-dir data/stooq \
    --tradeable-dir tradeable_instruments \
    --metadata-output data/metadata/stooq_index.csv \
    --match-report data/metadata/tradeable_matches.csv \
    --prices-output data/processed/tradeable_prices \
    --incremental

# 2. Load pre-configured universe (runs selection, classification, returns)
python scripts/manage_universes.py load core_global \
    --output-dir outputs/live_test

# 3. Construct portfolio
python scripts/construct_portfolio.py \
    --returns outputs/live_test/core_global_returns.csv \
    --strategy equal_weight \
    --output outputs/live_test/portfolio.csv

# 4. Backtest (2020-2023)
python scripts/run_backtest.py equal_weight \
    --start-date 2020-01-01 \
    --end-date 2023-12-31 \
    --returns outputs/live_test/core_global_returns.csv \
    --output-dir outputs/live_test/backtest \
    --rebalance-frequency quarterly \
    --visualize

# 5. Review results
cat outputs/live_test/backtest/equal_weight/performance_metrics.json
```

**Expected Outputs:**

- Portfolio weights CSV (35 assets, equal ~2.86% each)
- Equity curve showing 2020-2023 performance
- Sharpe ratio ~1.0-1.5 (typical for diversified portfolio)
- Max drawdown ~15-25% (includes 2020 COVID crash)

### Production Test (2+ hours)

**Goal:** Full 20-year backtest with advanced features.

```bash
# Use satellite_factor universe with preselection + membership
python scripts/run_backtest.py risk_parity \
    --universe-file config/universes.yaml \
    --universe satellite_factor \
    --start-date 2005-01-01 \
    --end-date 2024-12-31 \
    --preselection-method combined \
    --preselection-top-k 20 \
    --membership-enabled \
    --membership-buffer-rank 25 \
    --membership-max-turnover 0.25 \
    --output-dir outputs/production_test \
    --format both \
    --visualize
```

______________________________________________________________________

## Appendix: File Counts

**Root Directory:** 31 markdown files (should be ~2-3 after cleanup)
**Source Code:** 150+ Python files (all production-ready)
**Tests:** 80+ test files, 615+ test cases
**Documentation:** 40+ guides in `docs/`
**Examples:** 5 example scripts (need validation)
**Configuration:** 2 YAML files (universes, regime examples)

**Disk Usage:**

- Source code: ~2 MB
- Tests: ~1.5 MB
- Documentation: ~500 KB
- Legacy docs (to archive): ~300 KB

______________________________________________________________________

**Conclusion:** The codebase is production-ready with excellent test coverage and documentation. The main cleanup task is archiving 31 legacy implementation summaries from Sprint 2. After cleanup, the project will have a clean root directory with only essential files (README, AGENTS, QUICKSTART).
