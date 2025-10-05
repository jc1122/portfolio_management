# System Patterns

## Architecture Overview
- Modular Python CLI application composed of independent services for data acquisition, preprocessing, portfolio construction, backtesting, and reporting.
- Core workflow: fetch/cached prices → sanitize/align data → select eligible assets → compute strategy-specific weights → simulate/rebalance portfolio → report metrics and charts.
- Designed for offline execution with cached datasets and configuration-driven strategy selection.

## Key Patterns
- **Data Pipeline Modularization**: Each stage exposes a simple function/class interface, enabling substitution (e.g., switching Stooq reader with cached CSV loader) without impacting downstream modules.
- **Strategy Plug-ins**: Portfolio engines implemented as interchangeable adapters (equal weight baseline, risk parity via `riskparityportfolio`, mean-variance via `PyPortfolioOpt`). Future engines (HRP, Black–Litterman) can adhere to the same signature.
- **Configuration-Driven Orchestration**: CLI arguments or YAML/JSON config dictate assets, rebalance frequency, transaction costs, and strategy choice to avoid hard-coded logic.
- **Analytics Layer Separation**: Performance metrics (Empyrical/QuantStats) and visualization (Matplotlib) operate on standardized return series, decoupled from strategy implementation.
- **Extension Hooks**: Reserve interfaces for advanced overlays (trend filters, volatility targeting, sentiment-based views) to be layered on post-MVP without rewriting core modules.

## Component Relationships
- `DataFetcher` feeds `DataSanitizer`, which outputs aligned price frames consumed by `AssetSelector` and strategy modules.
- Strategy modules use cleaned returns/volatility estimates and hand weights to the `Backtester`, which enforces rebalance cadence and commission costs.
- `Reporter` consumes portfolio equity curves and metrics to produce textual summaries and plots.
- Future sentiment subsystem will inject additive views into the portfolio engine via Black–Litterman or satellite-tilt interfaces.

## Critical Paths
- Accurate data alignment and handling of missing observations prior to optimization.
- Reliable risk/return estimation feeding Mean-Variance or risk parity solvers; sensitivity to estimation error must be tracked.
- Rebalance engine must correctly apply transaction costs and opportunistic bands to avoid overstating performance.
- Reporting pipeline must persist logs/plots for each run to support auditability and behavioral discipline.

## Follow-ups
- Decide on configuration format (YAML vs. CLI-only) and logging mechanism.
- Evaluate inclusion of hierarchical risk parity (via PyPortfolioOpt or Riskfolio-Lib) in early iterations.
- Design API contract for forthcoming sentiment/event overlay to ensure compatibility with existing modules.
