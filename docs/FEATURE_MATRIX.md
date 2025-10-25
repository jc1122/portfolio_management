# Feature Matrix & Capability Reference

## Overview

This document provides a comprehensive reference of all features in the portfolio management toolkit, their implementation status, CLI access methods, and detailed capabilities.

**Status Legend:**

- ✅ **Production** - Fully implemented, tested, production-ready
- 🚧 **Stub/Interface** - Interface defined, ready for implementation
- 📋 **Planned** - Documented design, not yet implemented

______________________________________________________________________

## Core Features

### 1. Data Preparation & Ingestion

| Feature | Status | CLI Script | Documentation |
|---------|--------|------------|---------------|
| **Stooq CSV Ingestion** | ✅ Production | `prepare_tradeable_data.py` | [data_pipeline.md](data_pipeline.md) |
| **Instrument Matching** | ✅ Production | `prepare_tradeable_data.py` | [data_pipeline.md](data_pipeline.md) |
| **Quality Validation (9+ flags)** | ✅ Production | `prepare_tradeable_data.py` | [data_pipeline.md](data_pipeline.md) |
| **Multi-Venue Support** | ✅ Production | `prepare_tradeable_data.py` | [data_pipeline.md](data_pipeline.md) |
| **Incremental Resume** | ✅ Production | `--incremental` flag | [incremental_resume.md](incremental_resume.md) |
| **Fast I/O (Polars/PyArrow)** | ✅ Production | `--fast-io` flag | [fast_io.md](fast_io.md) |

#### Capabilities

**Stooq CSV Ingestion:**

- Reads daily OHLCV data from Stooq format
- Handles multiple exchanges (TSX, Xetra, Euronext, Swiss, Brussels)
- Validates data structure and completeness

**Instrument Matching:**

- Heuristic-based matching for venue-specific symbols
- TSX: `symbol.TSX` → `symbol.TO`
- Xetra: `symbol.DE` → `symbol.XETRA`
- Euronext: `symbol.FR`, `symbol.NL` → venue suffixes
- Swiss: `symbol.CH` → Swiss exchange
- Brussels: `symbol.BE` → Brussels exchange

**Quality Validation Flags:**

1. Duplicates in data
1. Non-positive prices
1. Zero volume days
1. Missing OHLC data
1. Inconsistent date ranges
1. Price spikes (>50% single-day moves)
1. Volume spikes (>10× average)
1. Suspicious zero returns
1. Data gaps >5 trading days

**Incremental Resume:**

- Cache-based workflow: 3-5 minutes → \<5 seconds
- Triggers: Input data unchanged
- Cache location: `.cache/` directory
- Invalidation: Automatic on input change

**Fast I/O:**

- Polars backend: 2-5× speedup for DataFrames >100MB
- PyArrow backend: 2-3× speedup for Parquet I/O
- Automatic fallback to pandas if backends unavailable

______________________________________________________________________

### 2. Asset Selection & Filtering

| Feature | Status | CLI Script | Documentation |
|---------|--------|------------|---------------|
| **Liquidity Filtering** | ✅ Production | `select_assets.py` | [asset_selection.md](asset_selection.md) |
| **Price Filtering** | ✅ Production | `select_assets.py` | [asset_selection.md](asset_selection.md) |
| **Market Cap Filtering** | ✅ Production | `select_assets.py` | [asset_selection.md](asset_selection.md) |
| **Allowlist/Blocklist** | ✅ Production | `select_assets.py` | [asset_selection.md](asset_selection.md) |
| **Factor Preselection** | ✅ Production | `--preselection` flag | [preselection.md](preselection.md) |

#### Capabilities

**Liquidity Filtering:**

- Minimum Average Daily Volume (ADV) in USD
- Configurable lookback period (default: 252 days)
- Handles currency conversion automatically
- Example: `--min-adv-usd 1000000` (minimum $1M daily volume)

**Price Filtering:**

- Minimum price threshold (avoids penny stocks)
- Currency-agnostic (applies after conversion)
- Example: `--min-price 5.0` (minimum $5)

**Market Cap Filtering:**

- Minimum market capitalization in USD
- Calculated from: `price × shares_outstanding`
- Example: `--min-market-cap-usd 100000000` (minimum $100M)

**Allowlist/Blocklist:**

- CSV file with symbols to include/exclude
- Format: Single column with header `symbol`
- Allowlist: Only include listed symbols
- Blocklist: Exclude listed symbols
- Example: `--allowlist config/sp500.csv`

**Factor Preselection:**

- **Momentum**: Top-K by 12-month trailing return

  - Formula: `(P_t / P_{t-252}) - 1`
  - Skips most recent month (de-trend)
  - Example: `--preselection momentum --top-k 30`

- **Low Volatility**: Top-K by lowest annualized volatility

  - Formula: `σ_daily × sqrt(252)`
  - Uses rolling 252-day window
  - Example: `--preselection low_volatility --top-k 30`

- **Universe Reduction**: 100-500 assets → 20-50 assets

- **Performance Impact**: 10-20× faster portfolio optimization

______________________________________________________________________

### 3. Asset Classification

| Feature | Status | CLI Script | Documentation |
|---------|--------|------------|---------------|
| **Geographic Classification** | ✅ Production | `classify_assets.py` | [asset_classification.md](asset_classification.md) |
| **Asset Type Classification** | ✅ Production | `classify_assets.py` | [asset_classification.md](asset_classification.md) |
| **Override Files** | ✅ Production | `--override-file` flag | [asset_classification.md](asset_classification.md) |
| **Export for Review** | ✅ Production | `--export-for-review` flag | [asset_classification.md](asset_classification.md) |

#### Capabilities

**Geographic Classification:**

- Derives country from exchange suffix
- Supported: US, Canada, Germany, France, Netherlands, Switzerland, Belgium
- Example: `AAPL.US` → United States, `SHOP.TO` → Canada

**Asset Type Classification:**

- Common Stock, Preferred Stock, ETF, ADR, REIT, etc.
- Heuristics: Symbol suffixes, name patterns
- Example: `QQQ.US` → ETF, `BRK-B.US` → Common Stock

**Override Files:**

- Manual corrections for misclassified assets
- CSV format: `symbol,country,asset_type`
- Example:
  ```csv
  symbol,country,asset_type
  SHOP.TO,Canada,Common Stock
  VTI.US,United States,ETF
  ```

**Export for Review:**

- Generate classification CSV for manual review
- Workflow: Export → Review → Override → Re-classify
- Example: `--export-for-review classifications_review.csv`

______________________________________________________________________

### 4. Return Calculation

| Feature | Status | CLI Script | Documentation |
|---------|--------|------------|---------------|
| **Log Returns** | ✅ Production | `calculate_returns.py` | [calculate_returns.md](calculate_returns.md) |
| **Simple Returns** | ✅ Production | `calculate_returns.py` | [calculate_returns.md](calculate_returns.md) |
| **Point-in-Time Integrity** | ✅ Production | `calculate_returns.py` | [calculate_returns.md](calculate_returns.md) |
| **Alignment Strategies** | ✅ Production | `--alignment` flag | [calculate_returns.md](calculate_returns.md) |
| **Missing Data Handling** | ✅ Production | `--fill-method` flag | [calculate_returns.md](calculate_returns.md) |

#### Capabilities

**Log Returns:**

- Formula: `ln(P_t / P_{t-1})`
- Advantages: Additive over time, symmetric
- Use case: Multi-period analysis, portfolio optimization
- Example: `--method log`

**Simple Returns:**

- Formula: `(P_t - P_{t-1}) / P_{t-1}`
- Advantages: Intuitive, matches reported returns
- Use case: Single-period reporting
- Example: `--method simple`

**Point-in-Time Integrity:**

- No lookahead bias in calculations
- Returns align with information available at time t
- Critical for realistic backtesting

**Alignment Strategies:**

- **Inner**: Only dates with all assets (most conservative)
- **Outer**: All dates, forward-fill missing (most complete)
- **Left**: Dates from first asset
- **Right**: Dates from last asset
- Example: `--alignment inner`

**Missing Data Handling:**

- **Forward Fill**: Use last known value
- **Zero Fill**: Assume zero return
- **Drop**: Remove asset
- Example: `--fill-method forward`

______________________________________________________________________

### 5. Portfolio Construction

| Feature | Status | CLI Script | Documentation |
|---------|--------|------------|---------------|
| **Equal Weight Strategy** | ✅ Production | `construct_portfolio.py` | [portfolio_construction.md](portfolio_construction.md) |
| **Risk Parity Strategy** | ✅ Production | `construct_portfolio.py` | [portfolio_construction.md](portfolio_construction.md) |
| **Mean-Variance Strategy** | ✅ Production | `construct_portfolio.py` | [portfolio_construction.md](portfolio_construction.md) |
| **Weight Constraints** | ✅ Production | `--min-weight`, `--max-weight` | [portfolio_construction.md](portfolio_construction.md) |
| **Membership Policy** | ✅ Production | `--membership-policy` flag | [membership_policy_guide.md](membership_policy_guide.md) |
| **Cardinality Constraints** | 🚧 Stub | Interface defined | [cardinality_constraints.md](cardinality_constraints.md) |

#### Capabilities

**Equal Weight Strategy:**

- Simple: `w_i = 1 / N` for all assets
- No optimization required
- Rebalances to equal weights each period
- Use case: Benchmark, diversification
- Example: `--strategy equal_weight`

**Risk Parity Strategy:**

- Equal risk contribution from each asset
- Optimization: `w_i × σ_i = constant` for all i
- Inverse volatility weighting
- Use case: Risk-balanced portfolios
- Example: `--strategy risk_parity`

**Mean-Variance Strategy:**

- Markowitz optimization: `max(μ^T w - λ w^T Σ w)`
- Risk aversion parameter λ (default: 1.0)
- Efficient frontier optimization
- Use case: Return/risk optimization
- Example: `--strategy mean_variance --risk-aversion 2.0`

**Weight Constraints:**

- Minimum weight: Avoid tiny positions
- Maximum weight: Diversification enforcement
- Example: `--min-weight 0.01 --max-weight 0.20` (1%-20%)

**Membership Policy:**

- **Turnover Control**: Limit rebalancing frequency

  - Formula: `Σ|w_t - w_{t-1}| ≤ max_turnover`
  - Example: `--max-turnover 0.5` (max 50%)

- **Minimum Holding Periods**: Avoid rapid churn

  - Assets held for minimum N rebalances
  - Example: `--min-holding-periods 5`

- **Buffer Ranks**: Smooth entry/exit

  - Top-K eligible, but only top-(K-buffer) enter
  - Reduces boundary thrashing
  - Example: `--buffer-ranks 5`

**Cardinality Constraints (Stub):**

- Interface defined for MIQP/heuristic solvers
- Target: Limit portfolio to K positions
- Status: Stub implementation ready for solver integration
- Example (future): `--max-positions 30`

______________________________________________________________________

### 6. Backtesting & Simulation

| Feature | Status | CLI Script | Documentation |
|---------|--------|------------|---------------|
| **Full Simulation Engine** | ✅ Production | `run_backtest.py` | [backtesting.md](backtesting.md) |
| **Rebalancing Logic** | ✅ Production | `run_backtest.py` | [backtesting.md](backtesting.md) |
| **Transaction Costs** | ✅ Production | `--commission`, `--slippage` | [backtesting.md](backtesting.md) |
| **Performance Metrics** | ✅ Production | `run_backtest.py` | [backtesting.md](backtesting.md) |
| **Trade Log Export** | ✅ Production | `run_backtest.py` | [backtesting.md](backtesting.md) |

#### Capabilities

**Full Simulation Engine:**

- Date-by-date portfolio evolution
- Handles corporate actions (splits, dividends)
- Point-in-time weight application
- Cash management and tracking

**Rebalancing Logic:**

- Configurable frequency (daily, weekly, monthly, quarterly)
- Partial rebalancing support
- Drift monitoring
- Example: `--rebalance-frequency monthly`

**Transaction Costs:**

- **Commission**: Fixed percentage per trade

  - Formula: `cost = commission × trade_value`
  - Example: `--commission 0.001` (0.1% = 10 bps)

- **Slippage**: Market impact modeling

  - Formula: `slippage = slippage_bps × trade_value`
  - Example: `--slippage 0.0005` (0.05% = 5 bps)

**Performance Metrics:**

- Total Return, CAGR, Annualized Volatility
- Sharpe Ratio, Sortino Ratio, Calmar Ratio
- Maximum Drawdown, Maximum Drawdown Duration
- Win Rate, Profit Factor, Recovery Factor
- Skewness, Kurtosis, Value at Risk (VaR)
- Output: JSON file with all metrics

**Trade Log Export:**

- CSV with every trade executed
- Columns: `date`, `symbol`, `action`, `quantity`, `price`, `value`, `commission`, `slippage`
- Use case: Transaction cost analysis, execution audit

______________________________________________________________________

### 7. Visualization & Reporting

| Feature | Status | CLI Script | Documentation |
|---------|--------|------------|---------------|
| **Equity Curve Plot** | ✅ Production | `run_backtest.py --visualize` | [visualization.md](visualization.md) |
| **Drawdown Chart** | ✅ Production | `run_backtest.py --visualize` | [visualization.md](visualization.md) |
| **Return Distribution** | ✅ Production | `run_backtest.py --visualize` | [visualization.md](visualization.md) |
| **Performance Metrics Table** | ✅ Production | `run_backtest.py --visualize` | [visualization.md](visualization.md) |
| **HTML Dashboard** | ✅ Production | `run_backtest.py --visualize` | [visualization.md](visualization.md) |

#### Capabilities

**Equity Curve Plot:**

- Portfolio value evolution over time
- Benchmark comparison (if provided)
- Log scale option for long-term views
- Export: PNG, SVG formats

**Drawdown Chart:**

- Underwater equity curve
- Highlights maximum drawdown periods
- Recovery periods visualization
- Export: PNG, SVG formats

**Return Distribution:**

- Histogram of daily/monthly returns
- Normal distribution overlay
- Skewness and kurtosis annotations
- Export: PNG, SVG formats

**Performance Metrics Table:**

- All key metrics in formatted table
- Risk/return decomposition
- Comparison to benchmark (if provided)
- Export: CSV, Markdown formats

**HTML Dashboard:**

- Interactive dashboard with all charts
- Tabbed interface for different views
- Responsive design
- Self-contained HTML file

______________________________________________________________________

### 8. Universe Management

| Feature | Status | CLI Script | Documentation |
|---------|--------|------------|---------------|
| **YAML Configuration** | ✅ Production | `manage_universes.py` | [universes.md](universes.md) |
| **Load Universe** | ✅ Production | `manage_universes.py load` | [universes.md](universes.md) |
| **Export Universe** | ✅ Production | `manage_universes.py export` | [universes.md](universes.md) |
| **Compare Universes** | ✅ Production | `manage_universes.py compare` | [universes.md](universes.md) |
| **Validate Config** | ✅ Production | `manage_universes.py validate` | [universes.md](universes.md) |

#### Capabilities

**YAML Configuration:**

- Centralized strategy definition
- Version control friendly
- Self-documenting format
- Schema validation
- Example structure:
  ```yaml
  my_strategy:
    asset_selection:
      min_price: 5.0
      min_adv_usd: 1000000
      preselection: "momentum"
    asset_classification:
      mode: "geographic"
    returns:
      alignment: "inner"
      method: "log"
  ```

**Load Universe:**

- Single command pipeline orchestration
- Runs: selection → classification → returns
- Output: `data/processed/{universe_name}/returns.csv`
- Example: `python scripts/manage_universes.py load my_strategy`

**Export Universe:**

- Export to CSV, JSON, or Parquet
- Includes metadata (creation date, config hash)
- Use case: Sharing, archiving, external analysis
- Example: `python scripts/manage_universes.py export my_strategy --format csv`

**Compare Universes:**

- Side-by-side asset list comparison
- Highlights additions, removals, changes
- Classification difference detection
- Example: `python scripts/manage_universes.py compare universe_a universe_b`

**Validate Config:**

- Schema validation before execution
- Catches typos, invalid parameters
- Prevents runtime errors
- Example: `python scripts/manage_universes.py validate my_strategy`

______________________________________________________________________

### 9. Performance Optimization

| Feature | Status | CLI Flag | Speedup | Documentation |
|---------|--------|----------|---------|---------------|
| **Incremental Resume** | ✅ Production | `--incremental` | 3-5 min → \<5 sec | [incremental_resume.md](incremental_resume.md) |
| **Fast I/O (Polars)** | ✅ Production | `--fast-io` | 2-5× | [fast_io.md](fast_io.md) |
| **Statistics Caching** | ✅ Production | Automatic | 4-60× | [statistics_caching.md](statistics_caching.md) |
| **Factor Preselection** | ✅ Production | `--preselection` | 10-20× | [preselection.md](preselection.md) |

#### Detailed Performance Impact

**Incremental Resume:**

- **Use Case**: Repeated runs with same inputs
- **Trigger**: Input files unchanged (hash-based detection)
- **Benefit**: Skip expensive I/O and computation
- **Benchmark**: 3-5 minutes → \<5 seconds (60-100×)

**Fast I/O:**

- **Use Case**: Large datasets (500-1000+ assets)
- **Backends**: Polars (default), PyArrow (optional)
- **Benefit**: Faster DataFrame operations, I/O
- **Benchmark**: 2-5× speedup on 1000-asset universe

**Statistics Caching:**

- **Use Case**: Backtests with overlapping windows
- **Automatic**: Enabled when conditions met
- **Benefit**: Reuse covariance/return calculations
- **Benchmark**: 4-60× speedup (depends on overlap)

**Factor Preselection:**

- **Use Case**: Large universes (100-500 assets)
- **Reduction**: 100-500 → 20-50 assets
- **Benefit**: Faster portfolio optimization (quadratic complexity)
- **Benchmark**: 10-20× speedup in construct_portfolio.py

______________________________________________________________________

### 10. Advanced Features (Stubs & Future)

| Feature | Status | Interface | Documentation |
|---------|--------|-----------|---------------|
| **Macro Signals** | 🚧 Stub | Provider interface | [macro_signals.md](macro_signals.md) |
| **Regime Gating** | 🚧 Stub | Regime detector interface | [macro_signals.md](macro_signals.md) |
| **Cardinality Constraints (MIQP)** | 🚧 Stub | MIQP solver interface | [cardinality_constraints.md](cardinality_constraints.md) |
| **Cardinality Constraints (Heuristic)** | 🚧 Stub | Greedy/iterative interface | [cardinality_constraints.md](cardinality_constraints.md) |

#### Future Capabilities

**Macro Signals:**

- Interface: `MacroSignalProvider` abstract class
- Purpose: Integrate economic data (GDP, inflation, rates)
- Use case: Strategy gating based on regime
- Status: Stub ready, no implementation

**Regime Gating:**

- Interface: `RegimeDetector` abstract class
- Purpose: Detect bull/bear/sideways markets
- Use case: Enable/disable strategies by regime
- Status: Stub ready, no implementation

**Cardinality Constraints (MIQP):**

- Interface: `MIQPSolver` abstract class
- Purpose: Exact position limits (e.g., max 30 positions)
- Method: Mixed-Integer Quadratic Programming
- Status: Stub ready, solver integration pending

**Cardinality Constraints (Heuristic):**

- Interface: `HeuristicCardinalitySolver` abstract class
- Purpose: Approximate position limits (fast)
- Method: Greedy selection, iterative pruning
- Status: Stub ready, algorithm implementation pending

______________________________________________________________________

## Feature Roadmap

### Phase 1: Core Foundation ✅

- \[x\] Data ingestion pipeline
- \[x\] Asset selection & classification
- \[x\] Return calculation
- \[x\] Portfolio construction (3 strategies)
- \[x\] Backtesting engine
- \[x\] Visualization

### Phase 2: Performance ✅

- \[x\] Incremental resume
- \[x\] Fast I/O backends
- \[x\] Statistics caching
- \[x\] Factor preselection
- \[x\] Membership policy

### Phase 3: Quality & Documentation 🔄

- \[x\] 200+ automated tests
- \[x\] Long-history test coverage
- \[x\] Edge case validation
- \[ \] Code documentation audit (Phase 4)
- \[ \] Test suite audit (Phase 5)
- \[ \] Architecture audit (Phase 6)
- \[ \] Examples creation (Phase 7)

### Phase 4: Advanced Features 📋

- \[ \] Macro signals integration
- \[ \] Regime gating implementation
- \[ \] Cardinality constraints (MIQP)
- \[ \] Cardinality constraints (Heuristic)
- \[ \] Multi-currency support
- \[ \] Alternative data integration

______________________________________________________________________

## Quick Reference Table

### By Use Case

| Use Case | Recommended Features | CLI Flags | Documentation |
|----------|---------------------|-----------|---------------|
| **Quick Start** | Default settings | None | [workflow.md](workflow.md) |
| **Large Universe (300+)** | Fast I/O, Preselection, Caching | `--fast-io --preselection momentum` | [workflow.md](workflow.md#workflow-3-production-optimized-) |
| **Low Turnover** | Membership Policy | `--membership-policy --max-turnover 0.5` | [membership_policy_guide.md](membership_policy_guide.md) |
| **Factor-Based** | Preselection (momentum or low-vol) | `--preselection momentum --top-k 30` | [preselection.md](preselection.md) |
| **Repeated Runs** | Incremental Resume | `--incremental` | [incremental_resume.md](incremental_resume.md) |
| **Comparison Study** | Universe Management | `manage_universes.py compare` | [universes.md](universes.md) |

______________________________________________________________________

## See Also

- **[README.md](../README.md)** - Project overview and quick start
- **[workflow.md](workflow.md)** - Complete workflow guide with examples
- **[CLI_REFERENCE.md](CLI_REFERENCE.md)** - Detailed CLI command reference
- **[best_practices.md](best_practices.md)** - Configuration and usage best practices
- **[../examples/README.md](../examples/README.md)** - Working code examples
