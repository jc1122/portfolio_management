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
- **Cached Data Indexing**: Stooq file discovery is front-loaded into a reusable metadata index, with multicore directory traversal and export to keep subsequent runs fast and deterministic.

## Performance Optimization Patterns (Oct 22)

**Vectorization Pattern:** Replace row-wise pandas operations with vectorized operations

- **Problem:** `.apply()` and `.iterrows()` operations cause quadratic complexity
- **Solution:** Replace with pandas' native vectorized methods (`Series.str.extract()`, `Series.dt.*`, `Series.isin()`, `to_dict("records")`)
- **Example:** AssetSelector vectorization achieved **45-206x speedup** by replacing row-wise filtering with pandas boolean masks
- **Lesson:** Always prefer vectorized operations for numeric/string operations over row iteration

**Bounded Caching Pattern:** Prevent unbounded memory growth with LRU eviction

- **Problem:** Unbounded caches grow indefinitely during long runs
- **Solution:** Use `OrderedDict` with configurable size limit and LRU eviction
- **Implementation:** Track access order; remove least recently used when full
- **Example:** PriceLoader cache achieved **70-90% memory savings** with bounded size (default 1000 entries)
- **Lesson:** All caches must have size bounds; make them configurable

**Rolling Statistics Cache Pattern:** Cache intermediate calculations across overlapping windows

- **Problem:** Covariance/returns recalculated for overlapping data windows
- **Solution:** Cache statistics across rolling windows; invalidate only when data changes
- **Implementation:** Cache key is (start_date, end_date, asset_list); auto-invalidate on new data
- **Example:** Statistics caching eliminates redundant calculations during monthly rebalancing with overlapping data
- **Lesson:** For time-series operations, cache intermediate results when windows overlap

**Streaming Diagnostics Pattern:** Process large datasets incrementally

- **Problem:** Loading gigabyte-scale datasets into memory is inefficient
- **Solution:** Process data in chunks; maintain state across chunks for aggregation
- **Implementation:** Chunk-based iteration with context preservation between chunks
- **Lesson:** For large data volumes, stream processing prevents memory spikes

**Algorithmic Optimization Pattern:** Reduce unnecessary computation by changing algorithm structure

- **Problem:** Certain operations performed repeatedly when not necessary (e.g., slicing on every day)
- **Solution:** Restructure algorithm to only perform expensive operations when needed
- **Example:** BacktestEngine optimization reduced from O(n²) to O(rebalances) by only slicing on rebalance days
- **Lesson:** Profile first; look for operations that execute more often than necessary

**Incremental Computation Pattern:** Cache results of expensive operations and reuse when possible

- **Problem:** Reprocessing everything even when inputs unchanged
- **Solution:** Hash inputs; compare to cached state; skip processing if unchanged
- **Implementation:** SHA256 hashing for change detection; metadata cache for state
- **Example:** Incremental resume reduced prepare_tradeable_data runtime from 3-5 minutes to seconds
- **Lesson:** Always consider caching for expensive batch operations

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

## Pre-commit Hooks and Quality Gates

To ensure code quality and consistency, the project uses a pre-commit pipeline with the following tools. All checks must pass before a commit is accepted.

- **`pre-commit`**: The framework for managing and running the pre-commit hooks.
- **`black`**: An opinionated code formatter that ensures uniform style across the codebase (files: `^(scripts/|src/|tests/)`).
- **`isort`**: Automatically sorts and groups Python imports (files: `^(scripts/|src/|tests/)`).
- **`ruff`**: An extremely fast Python linter that checks for a wide range of errors and style issues (files: `^(scripts/|src/|tests/)`).
- **`mypy`**: A static type checker to help prevent type-related errors (files: `^(scripts/|src/|tests/)`).
- **`pytest`**: The testing framework used to run the automated test suite (~30 seconds with `-n auto`).
- **`mdformat`**: A tool to format and ensure consistency in Markdown files.
- **`gitlint`**: A tool to enforce a consistent and clean commit message style.

**Performance Note**: Pre-commit completes in ~50 seconds total with all hooks including pytest. The pytest hook configuration uses `pass_filenames: false` and `types: [python]` to run the full test suite only when Python files change, preventing redundant test runs for non-code changes.

## Follow-ups

- Decide on configuration format (YAML vs. CLI-only) and logging mechanism.
- Evaluate inclusion of hierarchical risk parity (via PyPortfolioOpt or Riskfolio-Lib) in early iterations.
- Design API contract for forthcoming sentiment/event overlay to ensure compatibility with existing modules.
