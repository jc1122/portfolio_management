# Tech Context

## Stack Summary

- Primary language: **Python 3.12** (minimum 3.10) executed via command-line scripts.
- Core libraries: `pandas>=2.3`, `numpy>=2.0`, `jax>=0.4.0`, `jaxlib>=0.4.0`, `PyPortfolioOpt>=1.5.0`, `riskparityportfolio>=0.2`, `empyrical-reloaded>=0.5.0`, `cvxpy>=1.1.19`, `scipy>=1.3`, `PyYAML>=6.0`, `plotly>=5.0.0`.
- CLI tooling: `argparse` for argument parsing; `pyyaml` for YAML configuration files.
- Development tools: `black==25.9.0`, `ruff==0.14.1`, `mypy==1.18.2`, `pytest==8.4.2`, `pre-commit`.

## Development Environment

- **System Python 3.12.11** (no virtual environments) with user site-packages (`--user` installations)
- Dev container: Debian GNU/Linux 11 (bullseye) with Docker-outside-of-Docker support
- VS Code configuration: Python 3.12 as default interpreter, auto-formatting with black, linting with ruff
- Git for version control with pre-commit hooks
- Data directories: `data/stooq/`, `data/processed/`, `data/metadata/` (gitignored but present locally)

## Key Patterns

- **Exception Hierarchy**: Custom exceptions derive from `PortfolioManagementError`, capturing missing dependencies and data directory issues with structured messages and context attributes.
- **Type-Checking Optimization**: Type-only imports now live behind `TYPE_CHECKING` guards, reducing runtime import overhead while preserving full static analysis coverage.

## Performance Optimization Strategies (Oct 22)

### Vectorization Approach

**Objective:** Replace pandas `.apply()` and `.iterrows()` with native vectorized operations

**Techniques:**

- String operations: `Series.str.extract()` for regex, `Series.str.contains()` for filtering
- Date/time: `pd.to_datetime()` + `Series.dt.*` properties for date arithmetic
- Filtering: `Series.isin()` for membership checks, boolean masks for complex conditions
- Conversion: `to_dict("records")` for batch dataclass creation instead of `.iterrows()`

**Results:** AssetSelector achieved **45-206x speedup** on 10k-row datasets

**Guidance:** For any loop over DataFrame rows, consider whether a vectorized operation exists

### Caching Strategies

**LRU Cache (PriceLoader):**

- Bounded cache using `OrderedDict` with configurable size (default 1000 entries)
- Automatic eviction of least recently used entry when full
- Memory savings: **70-90%** for wide-universe workflows
- Implementation: `src/portfolio_management/analytics/returns/loaders.py`
- CLI integration: `--cache-size` argument in `calculate_returns.py`

**Rolling Statistics Cache:**

- Cache covariance matrices and expected returns across overlapping windows
- Automatic invalidation when new data loaded
- Eliminates redundant calculations during monthly rebalancing
- Implementation: `src/portfolio_management/portfolio/statistics/`
- Integration: Optional parameter injection in `RiskParityStrategy` and `MeanVarianceStrategy`

**Incremental Resume (Hash-Based):**

- SHA256 hashing for input file state tracking
- Metadata cache for comparison across runs
- Skip processing when inputs unchanged
- Performance: 3-5 minutes → 2-3 seconds for unchanged inputs
- Implementation: `scripts/prepare_tradeable_data.py`

### Streaming Processing

**Objective:** Process gigabyte-scale datasets incrementally

**Approach:** Chunk-based iteration with state preservation

- Process one chunk at a time (memory efficient)
- Maintain aggregation state across chunks
- Real-time issue detection during processing

**Benefits:** Prevents memory spikes; enables real-time diagnostics

### Algorithmic Optimization

**BacktestEngine:** O(n²) → O(rebalances) reduction

- Problem: Creating DataFrame slices on every trading day
- Solution: Only create slices when actually rebalancing
- Impact: 95-98% reduction in unnecessary operations
- Complexity: Code simplified from 30 lines to 18 lines
- Implementation: `src/portfolio_management/backtesting/engine/backtest.py`

## Repository Structure Constraints

**CRITICAL**: This repository contains **71,379+ files**, with **70,420+ data files** in the `data/` directory (primarily CSV price files from Stooq). The `data/` directory is gitignored but present in the working directory.

**Configuration Requirements**:

- All scanning/search tools MUST be configured to exclude the `data/` directory to prevent performance issues
- Tools that scan the filesystem (pytest, pre-commit, linters, etc.) can hang or take minutes if not properly configured
- The `data/` directory structure: `data/stooq/`, `data/processed/tradeable_prices/`, and test fixtures under `tests/fixtures/`

**Current Tool Configurations**:

- `pyproject.toml` → pytest: `testpaths = ["tests"]` and `norecursedirs = ["data", ...]` to prevent test collection from scanning data files
- `.gitignore` → already excludes `data/` directory
- Future tools (IDEs, search tools, etc.) must be configured similarly to avoid the data directory

## Dependencies

- Data: Stooq daily OHLCV (via direct CSV download or `pandas_datareader.DataReader`). Optional expansion to other free APIs if licensing permits.
- Optimization: `cvxopt`/`cvxpy` backends as required by PyPortfolioOpt; `jax` if using `riskparityportfolio`.
- Analytics: `empyrical` for Sharpe, drawdown, volatility, Expected Shortfall; `matplotlib`/`seaborn` for visualization.
- Testing/reporting: `pytest` for unit coverage (future), `quantstats` for extended performance reports.

## Constraints

- Must function without persistent internet access after initial data retrieval; ensure graceful degradation when APIs are unreachable.
- Need transaction cost modeling aligned with broker fee schedules.
- Library choices should favor active maintenance and permissive licenses (MIT/BSD) for long-term viability.

## Outstanding Questions

- Confirm Python version compatibility with target deployment environment (e.g., broker-supplied workstations?).
- Determine preferred packaging strategy (single CLI script vs. installable package).
- Validate whether GPU acceleration is required/desirable for future NLP/sentiment module.
- Specify data storage format/retention policy for cached price histories and generated reports.
