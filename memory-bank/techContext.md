# Tech Context

## Stack Summary

- Primary language: Python (>=3.10) executed via command-line scripts.
- Core libraries: `pandas`, `numpy`, `pandas-datareader` (Stooq connector), `PyPortfolioOpt`, `riskparityportfolio` (or `Riskfolio-Lib` as alternative), `empyrical`, `matplotlib`, optional `quantstats` for tear sheets.
- CLI tooling: `argparse` (baseline) or `click`; configuration optionally via `pyyaml` for YAML files.

## Development Environment

- Local workstation or container with offline capability; data directories for cached Stooq CSV files to avoid repeated downloads.
- Virtual environment/Poetry for dependency isolation; Git for version control.
- Recommend integrating basic logging (Python `logging`) and plotting backend compatible with headless runs (e.g., Agg).

## Key Patterns

- **Exception Hierarchy**: Custom exceptions derive from `PortfolioManagementError`, capturing missing dependencies and data directory issues with structured messages and context attributes.
- **Type-Checking Optimization**: Type-only imports now live behind `TYPE_CHECKING` guards, reducing runtime import overhead while preserving full static analysis coverage.

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
