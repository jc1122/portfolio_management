# Architecture Documentation

This directory contains comprehensive architecture and workflow documentation for the Portfolio Management Toolkit.

## 📊 Core Documents

### [COMPLETE_WORKFLOW.md](COMPLETE_WORKFLOW.md)

**The definitive reference for understanding the entire system.**

This document contains:

- Complete Mermaid workflow diagram showing all data flows
- Detailed descriptions of every component
- All feature integrations and data paths
- CLI command reference
- Examples and use cases
- Troubleshooting guide

**👉 Start here for comprehensive system understanding.**

## Architecture Overview

### System Type

**Modular Monolith** - Single codebase with clear module boundaries

### Design Principles

1. **Offline-First**

   - Works with cached data
   - No external API dependencies during execution
   - Reproducible workflows

1. **Modular Pipeline**

   - Each stage is independent and composable
   - Clear input/output contracts
   - Can be run individually or orchestrated

1. **Configuration-Driven**

   - YAML-based universe definitions
   - CLI flags for runtime parameters
   - Version-controlled configurations

1. **Production-Ready**

   - 200+ automated tests
   - Comprehensive error handling
   - Performance optimized (caching, vectorization)
   - Defensive validation

### Core Workflow Stages

```
CSV Files → Data Prep → Selection → Classification → Returns → Portfolio → Backtest → Visualization
```

**Detailed Breakdown:**

1. **Data Preparation** (`prepare_tradeable_data.py`)

   - Ingest Stooq CSV files
   - Match instruments across venues
   - Validate data quality (9+ flags)
   - Features: Incremental resume, fast I/O

1. **Asset Selection** (`select_assets.py`)

   - Filter by liquidity, price, market cap
   - Apply allow/block lists
   - Optional: Factor preselection

1. **Asset Classification** (`classify_assets.py`)

   - Geographic classification
   - Asset type classification
   - Override support for corrections

1. **Return Calculation** (`calculate_returns.py`)

   - Compute log or simple returns
   - Handle missing data
   - Ensure point-in-time integrity

1. **Universe Management** (`manage_universes.py`)

   - Define universes in YAML
   - Orchestrate pipeline stages
   - Validate configurations

1. **Portfolio Construction** (`construct_portfolio.py`)

   - Three strategies: Equal Weight, Risk Parity, Mean-Variance
   - Apply constraints (weights, asset classes)
   - Optional: Statistics caching

1. **Backtesting** (`run_backtest.py`)

   - Simulate historical performance
   - Model transaction costs
   - Optional: PIT eligibility, preselection, membership policy
   - Generate comprehensive results

1. **Visualization & Reporting**

   - Equity curves, drawdowns, distributions
   - Performance metrics
   - Interactive HTML dashboards

### Advanced Features

**Performance Optimization:**

- Incremental resume (3-5 min → 2-3 sec)
- Fast I/O with Polars/PyArrow (2-5× speedup)
- Statistics caching (5-10× speedup for rebalancing)
- Vectorization (45-206× speedup for selection)

**Risk Management:**

- Point-in-time eligibility (prevent lookahead bias)
- Membership policy (control turnover)
- Weight constraints (enforce diversification)
- Asset class limits (allocation guardrails)
- Transaction cost modeling

**Factor & Signal Features:**

- Momentum preselection (top-K by returns)
- Low-volatility preselection (top-K by volatility)
- Combined factor scoring
- Technical indicators (stub - future)
- Macro signals (stub - future)

### Module Structure

```
src/portfolio_management/
├── core/           # Exceptions, config, types, utilities
├── data/           # Ingestion, I/O, matching, analysis
├── assets/         # Selection, classification, universes
├── analytics/      # Returns, metrics, indicators
├── macro/          # Macro signals, regime detection
├── portfolio/      # Strategies, constraints, membership
├── backtesting/    # Engine, transactions, performance
└── reporting/      # Visualization, exporters
```

### Data Flow Patterns

**Managed Workflow (Recommended):**

```
1. prepare_tradeable_data.py → tradeable_matches.csv
2. Edit config/universes.yaml
3. manage_universes.py load <universe> → Auto-pipeline
4. construct_portfolio.py → weights.csv
5. run_backtest.py → Results + visualizations
```

**Manual Workflow (Debug/Experiment):**

```
1. prepare_tradeable_data.py
2. select_assets.py
3. classify_assets.py
4. calculate_returns.py
5. construct_portfolio.py
6. run_backtest.py
```

### Technology Stack

**Core:**

- Python 3.12 (minimum 3.10)
- pandas 2.3+, numpy 2.0+, scipy 1.3+
- JAX 0.4+ (for numerical computations)

**Portfolio Optimization:**

- PyPortfolioOpt 1.5+ (mean-variance)
- riskparityportfolio 0.2+ (risk parity)
- cvxpy 1.1+ (convex optimization)

**Performance:**

- Polars (optional fast I/O)
- PyArrow (optional fast I/O)

**Analytics:**

- empyrical-reloaded 0.5+ (performance metrics)
- Plotly 5.0+ (interactive visualization)

**Development:**

- pytest 8.4+ (testing)
- black 25.9 (formatting)
- ruff 0.14 (linting)
- mypy 1.18 (type checking)

### Testing Strategy

**200+ Tests covering:**

- Unit tests for all modules
- Integration tests for pipeline stages
- CLI tests for scripts
- Performance smoke tests
- Edge case handling
- Caching correctness

**Test Organization:**

```
tests/
├── core/           # Core utilities
├── data/           # Data pipeline
├── assets/         # Selection & classification
├── analytics/      # Returns & metrics
├── portfolio/      # Strategies & constraints
├── backtesting/    # Engine & performance
├── reporting/      # Visualization
├── integration/    # End-to-end tests
└── scripts/        # CLI tests
```

### Configuration Management

**Primary Configuration:**

- `config/universes.yaml`: Universe definitions
- `config/*.yaml`: Strategy-specific configurations
- `pyproject.toml`: Project metadata & tool configs
- `pytest.ini`: Test configuration
- `mypy.ini`: Type checking configuration

**Runtime Configuration:**

- CLI flags for all scripts
- Environment variables for system paths
- `.cache/`: Incremental resume metadata

### Error Handling

**Exception Hierarchy:**

```
PortfolioManagementError (base)
├── DataError
│   ├── FileNotFoundError
│   ├── DataValidationError
│   └── DataQualityError
├── ConfigError
│   ├── ConfigValidationError
│   └── MissingConfigError
├── OptimizationError
│   ├── InfeasibleConstraintsError
│   └── SolverFailureError
└── BacktestError
    ├── InsufficientDataError
    └── RebalanceError
```

**Error Handling Strategy:**

- Validate early (fail fast)
- Provide actionable error messages
- Include context (file paths, parameter values)
- Log warnings for non-critical issues
- Raise exceptions for critical failures

### Performance Characteristics

**Data Preparation:**

- First run: 3-5 minutes (10,000 files)
- Subsequent runs: 2-3 seconds (with incremental resume)
- Fast I/O: 2-5× speedup for large datasets

**Asset Selection:**

- Vectorized: 45-206× faster than iterative
- 10,000 assets: \<1 second

**Portfolio Construction:**

- Equal Weight: O(n) - instant
- Risk Parity: O(n²) - seconds to minutes
- Mean-Variance: O(n³) - minutes for large universes
- With caching: 5-10× speedup for rebalancing

**Backtesting:**

- 10-year backtest, 50 assets, monthly rebalancing: \<10 seconds
- 10-year backtest, 300 assets, monthly rebalancing: \<60 seconds
- With preselection: 10-20× faster for large universes

### Memory Management

**Constraints:**

- Repository: 71,379+ files (70,420+ data files)
- All tools configured to exclude `data/` directory
- Bounded caches with LRU eviction

**Memory Optimization:**

- Streaming processing for large datasets
- Bounded caches (default 1000 entries)
- 70-90% memory savings vs. unbounded caching

### Future Roadmap

**Stub Features (Infrastructure Complete):**

1. **Cardinality Constraints**

   - MIQP solver integration
   - Heuristic approximations
   - Limit portfolio to K positions

1. **Technical Indicators**

   - TA-Lib integration
   - Configurable indicators (RSI, MACD, MA)
   - Signal combination logic

1. **Macro Signals**

   - Regime detection (recession, risk-off)
   - Asset class gating by regime
   - Score adjustments

**Planned Enhancements:**

- Black-Litterman views integration
- News/sentiment factor overlays
- Multi-period optimization
- Risk budgeting constraints
- ESG filtering

### Documentation Map

**Getting Started:**

- [README.md](../../README.md) - Project overview
- [QUICKSTART.md](../../QUICKSTART.md) - 5-minute setup
- [workflow.md](../workflow.md) - Workflow overview

**Module Guides:**

- [data_preparation.md](../data_preparation.md)
- [asset_selection.md](../asset_selection.md)
- [asset_classification.md](../asset_classification.md)
- [calculate_returns.md](../calculate_returns.md)
- [universes.md](../universes.md)
- [portfolio_construction.md](../portfolio_construction.md)
- [backtesting.md](../backtesting.md)

**Advanced Features:**

- [preselection.md](../preselection.md)
- [membership_policy_guide.md](../membership_policy_guide.md)
- [statistics_caching.md](../statistics_caching.md)
- [fast_io.md](../fast_io.md)
- [incremental_resume.md](../incremental_resume.md)

**Reference:**

- [CLI_REFERENCE.md](../CLI_REFERENCE.md)
- [FEATURE_MATRIX.md](../FEATURE_MATRIX.md)
- [troubleshooting.md](../troubleshooting.md)
- [best_practices.md](../best_practices.md)

**Architecture:**

- [COMPLETE_WORKFLOW.md](COMPLETE_WORKFLOW.md) ⭐ **Complete system diagram**

### Memory Bank (Agent Context)

For AI agents working on this project:

- [AGENTS.md](../../AGENTS.md) - Agent operating instructions
- [memory-bank/](../../memory-bank/) - Persistent context
  - `projectbrief.md` - Project overview
  - `productContext.md` - User needs & use cases
  - `systemPatterns.md` - Architecture patterns
  - `techContext.md` - Technical stack
  - `activeContext.md` - Current development status
  - `progress.md` - Development history

______________________________________________________________________

## Contributing

When adding new features:

1. **Follow Module Boundaries**: Keep concerns separated
1. **Add Tests**: Maintain >80% coverage
1. **Update Documentation**: Especially COMPLETE_WORKFLOW.md
1. **Validate Configuration**: Add YAML schema validation
1. **Handle Errors**: Use exception hierarchy
1. **Optimize Performance**: Profile before optimizing
1. **Cache Wisely**: Use bounded caches with LRU

## Support

For questions or issues:

1. Check [troubleshooting.md](../troubleshooting.md)
1. Review [COMPLETE_WORKFLOW.md](COMPLETE_WORKFLOW.md)
1. Consult module-specific documentation
1. Check test cases for usage examples

______________________________________________________________________

**Last Updated:** October 25, 2025
