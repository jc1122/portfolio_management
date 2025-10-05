# Tech Context

## Stack Summary
- Primary language: Python (>=3.10) executed via command-line scripts.
- Core libraries: `pandas`, `numpy`, `pandas-datareader` (Stooq connector), `PyPortfolioOpt`, `riskparityportfolio` (or `Riskfolio-Lib` as alternative), `empyrical`, `matplotlib`, optional `quantstats` for tear sheets.
- CLI tooling: `argparse` (baseline) or `click`; configuration optionally via `pyyaml` for YAML files.

## Development Environment
- Local workstation or container with offline capability; data directories for cached Stooq CSV files to avoid repeated downloads.
- Virtual environment/Poetry for dependency isolation; Git for version control.
- Recommend integrating basic logging (Python `logging`) and plotting backend compatible with headless runs (e.g., Agg).

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
