# Portfolio Management Toolkit

Offline-first Python command-line toolkit for constructing and backtesting long-horizon retirement portfolios for Polish investors trading via BOŚ Dom Maklerski and mBank's MDM. The project emphasizes diversified asset allocation, factor tilts, and disciplined risk overlays, with future plans to incorporate news- and sentiment-driven signals.

## Current Capabilities

- Offline-first data pipeline that ingests Stooq exports, validates quality, and produces tradeable match reports with diagnostics.
- Production-ready asset selection, classification, return preparation, and universe management CLIs with defensive validation and rich logging.
- Configurable universes defined in YAML, with scriptable validation, export, and comparison workflows.
- 200+ automated tests (unit, CLI, integration, performance smoke) covering the full data-to-portfolio stack.
- Portfolio construction module with equal-weight, risk-parity, and mean-variance strategies plus comparison tooling and CLI access.
- Backtesting engine with CLI orchestration, opportunistic rebalancing, transaction cost modelling, and performance analytics ready for production validation.

## Repository Structure

```
scripts/                             # CLI entry points
  ├── prepare_tradeable_data.py      # Data preparation orchestrator
  ├── select_assets.py               # Stage 1 filters (quality/history/lists)
  ├── classify_assets.py             # Stage 2 taxonomy + overrides
  ├── calculate_returns.py           # Stage 3 return alignment CLI
  ├── manage_universes.py            # Stage 4/5 universe tooling
  ├── construct_portfolio.py         # Phase 4 portfolio construction CLI
  └── run_backtest.py                # Phase 5 backtesting CLI
src/portfolio_management/
  ├── selection.py                   # FilterCriteria, SelectedAsset, AssetSelector
  ├── classification.py              # AssetClassifier, overrides, taxonomy enums
  ├── returns.py                     # ReturnConfig, ReturnCalculator, summaries
  ├── universes.py                   # Universe definitions & manager
  ├── backtest.py                    # Backtesting engine & analytics helpers
  ├── visualization.py               # Chart data preparation utilities
  ├── exceptions.py                  # Custom exception hierarchy
  ├── analysis.py / matching.py / io.py / utils.py / stooq.py / config.py
memory-bank/                         # Persistent cross-session context
tests/
  ├── integration/                   # End-to-end, performance, production smoke tests
  ├── fixtures/                      # Lightweight CSV fixtures
  ├── scripts/                       # CLI regression tests
  └── test_*.py                      # Unit coverage (selection/classification/etc.)
docs/                                # Living module guides (returns, universes)
archive/                             # Historical plans, reviews, session logs
```

## Getting Started

1. Ensure Python 3.10+ is available.

1. Create and activate a virtual environment.

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

   > **Note:** `prepare_tradeable_data.py` now requires pandas; there is no CSV fallback. Confirm the dependency installs cleanly in every execution environment before running the script.

1. Populate cached historical data from Stooq or other free sources.

1. Construct portfolios with:

   ```bash
   python scripts/construct_portfolio.py \
       --returns data/processed/universe_returns.csv \
       --strategy equal_weight \
       --max-weight 0.30 \
       --output outputs/portfolio_equal_weight.csv
   ```

1. Run historical backtests with:

   ```bash
   python scripts/run_backtest.py \
       --universe core_global \
       --strategy equal_weight \
       --start-date 2023-01-02 \
       --end-date 2023-12-31 \
       --returns data/processed/returns/core_global.csv \
       --output-dir output/backtests \
       --format both \
       --visualize
   ```

## Data Preparation Workflow

Once Stooq ZIP archives have been unpacked into `data/stooq/`, generate the tradeable dataset with:

```bash
python scripts/prepare_tradeable_data.py \
    --data-dir data/stooq \
    --tradeable-dir tradeable_instruments \
    --metadata-output data/metadata/stooq_index.csv \
    --match-report data/metadata/tradeable_matches.csv \
    --unmatched-report data/metadata/tradeable_unmatched.csv \
    --prices-output data/processed/tradeable_prices \
    --overwrite-prices --force-reindex
```

The first run builds a cached index (≈40 s for ~62k files); subsequent runs can omit `--force-reindex` for \<3 s incremental updates.

Optional flags: `--include-empty-prices` forces exports for tickers without usable data (normally skipped) and `--lse-currency-policy` lets you choose whether London listings keep the broker currency (`broker`, default), adopt Stooq's inferred currency (`stooq`), or raise an error when the currencies diverge (`strict`).

Worker pools default to `CPU cores - 1` for both matching/export and index scans; supply `--max-workers` or `--index-workers` to override.

> **Heads-up:** The matching heuristics now cover common TSX, Xetra, Euronext, Swiss, and Brussels suffixes. If venues such as Xetra still appear in the unmatched report, confirm that the corresponding Stooq directory bundles (e.g., `d_de_txt/…`) have been unpacked—those files are absent from the current repository snapshot.
>
> The match report includes a `data_flags` column populated by additional validation checks (duplicate dates, non-positive closes, zero/missing volume, etc.) and the CLI emits summaries/warnings so suspect price files can be triaged immediately.
>
> The script now mandates pandas for all data access (indexing, tradeable ingestion, report writing, price exports). A 1,000-file benchmark shows identical outputs with roughly a 12 % runtime increase versus the previous hybrid implementation.

## Asset Selection Workflow

After generating the tradeable matches report, you can use the `select_assets.py` script to filter for high-quality assets that meet your investment criteria.

```bash
python scripts/select_assets.py \
    --match-report data/metadata/tradeable_matches.csv \
    --output /tmp/selected_assets.csv \
    --min-history-days 756 \
    --min-price-rows 756 \
    --markets "LSE,NYSE,NSQ" \
    --data-status "ok"
```

This command selects assets from the specified markets with at least 3 years of clean (`ok`) data and saves the result to `/tmp/selected_assets.csv`.

### CLI Arguments

- `--match-report` (required): Path to the `tradeable_matches.csv` file generated by the data preparation script.
- `--output` (optional): Path to save the output CSV file. If omitted, the results are printed to the console.
- `--data-status` (optional): Comma-separated list of allowed data quality statuses (e.g., "ok,warning"). Defaults to "ok".
- `--min-history-days` (optional): Minimum number of calendar days of price history. Defaults to 252.
- `--min-price-rows` (optional): Minimum number of data rows (trading days). Defaults to 252.
- `--markets` (optional): Comma-separated list of market codes to include (e.g., "LSE,NYSE").
- `--regions` (optional): Comma-separated list of regions to include (e.g., "Europe,North America").
- `--currencies` (optional): Comma-separated list of currencies to include (e.g., "GBP,USD").
- `--allowlist`: Path to a file containing a newline-separated list of symbols or ISINs to force-include.
- `--blocklist`: Path to a file containing a newline-separated list of symbols or ISINs to exclude.
- `--verbose`: Enable detailed logging output.
- `--dry-run`: Show a summary of what would be selected without writing any files.

## Asset Classification Workflow

Once you have a list of selected assets, you can classify them using the `classify_assets.py` script.

```bash
python scripts/classify_assets.py \
    --input /tmp/selected_assets.csv \
    --output /tmp/classified_assets.csv \
    --summary
```

This command takes the selected assets, classifies them based on a set of rules, and prints a summary of the classification.

### CLI Arguments

- `--input` (required): Path to the selected assets CSV file.
- `--output` (optional): Path to save the classified assets CSV file. If omitted, the results are printed to the console.
- `--overrides` (optional): Path to a CSV file with manual classification overrides.
- `--export-for-review` (optional): Path to export a CSV template for manual review.
- `--summary`: Print a summary of the classification results.
- `--verbose`: Enable detailed logging output.

## Return Calculation Workflow

After classifying your assets, calculate aligned return series using the
`calculate_returns.py` script. The CLI wraps the Stage 3 pipeline described in
[`docs/returns.md`](docs/returns.md), performs upfront validation, and raises
clear `PortfolioManagementError` subclasses if assets, price directories, or
configuration are invalid.

```bash
python scripts/calculate_returns.py \
    --assets /tmp/classified_assets.csv \
    --prices-dir data/processed/tradeable_prices \
    --method simple \
    --frequency monthly \
    --align-method inner \
    --business-days \
    --summary
```

This command prepares monthly simple returns, reindexed to the business-day
calendar, and prints an annualised performance summary. If the filters remove
every asset, the CLI exits with a non-zero status instead of silently emitting
an empty file.

## Portfolio Construction Workflow

Use the new Phase 4 CLI to convert prepared return matrices into allocation weights. The tool supports single-strategy runs and multi-strategy comparisons.

```bash
python scripts/construct_portfolio.py \
    --returns data/processed/universe_returns.csv \
    --classifications data/processed/asset_classes.csv \
    --strategy mean_variance_max_sharpe \
    --max-weight 0.25 \
    --max-equity 0.85 \
    --min-bond 0.15 \
    --output outputs/portfolio_mv.csv
```

To compare all registered strategies side by side:

```bash
python scripts/construct_portfolio.py \
    --returns data/processed/universe_returns.csv \
    --compare \
    --output outputs/portfolio_comparison.csv
```

Outputs are saved as CSV files (ticker-weight table for single portfolios, matrix for comparisons). Full details are documented in [`docs/portfolio_construction.md`](docs/portfolio_construction.md).

### CLI Arguments

- `--assets` (required): Path to the selected/classified assets CSV file.
- `--prices-dir` (required): Directory containing the price files exported from Stooq.
- `--output`: Path to save the returns CSV file (parents created automatically).
- `--method`: Return calculation method (`simple`, `log`, `excess`). Defaults to `simple`.
- `--frequency`: Resampling cadence (`daily`, `weekly`, `monthly`). Defaults to `daily`.
- `--risk-free-rate`: Annual risk-free rate for excess returns.
- `--handle-missing`: Missing data strategy (`forward_fill`, `drop`, `interpolate`).
- `--max-forward-fill`: Maximum consecutive days to forward-fill or interpolate.
- `--min-periods`: Minimum number of price observations required per asset.
- `--align-method`: Date alignment strategy (`outer` union, `inner` intersection).
- `--business-days`: Reindex to the business-day calendar before coverage filtering.
- `--min-coverage`: Minimum non-null coverage threshold for keeping an asset.
- `--summary`: Print the textual performance summary instead of raw returns.
- `--top`: Number of top/bottom assets shown in the summary (default 5).
- `--verbose`: Enable detailed logging output.

## Backtesting Workflow

Use the Phase 5 CLI to simulate historical performance for any portfolio strategy registered with the constructor. The command accepts the universe name, strategy (or list of strategies for comparison), backtest window, and optional transaction cost overrides.

```bash
python scripts/run_backtest.py \
    --universe core_global \
    --strategy equal_weight \
    --start-date 2023-01-02 \
    --end-date 2023-12-31 \
    --returns data/processed/returns/core_global.csv \
    --output-dir output/backtests \
    --format both \
    --visualize
```

Key outputs include normalised equity curves, daily returns, allocation histories, rebalance logs, trade blotters, and JSON performance metrics. Comparison mode (`--compare --strategies equal_weight,mean_variance_min_vol`) aggregates results across strategies and stores summary tables alongside individual runs. When `--visualize` is supplied, chart-ready CSVs are exported for equity, drawdown, allocation, transaction-cost, and rolling Sharpe views.

For the full argument reference and detailed workflow notes see [`docs/backtesting.md`](docs/backtesting.md).

## Universe Management Workflow

Define repeatable investment universes via `config/universes.yaml` and control
them with `scripts/manage_universes.py`. The repository currently ships with
four calibrated universes:

| Universe | Focus | Assets Selected | Assets with Returns |
|----------|-------|-----------------|---------------------|
| `core_global` | GBP-denominated diversified ETFs | 41 | 35 |
| `satellite_factor` | Factor tilts (growth/value/dividend/small-cap) | 31 | 15 |
| `defensive` | REITs, dividend names, gold exposure | 10 | 9 |
| `equity_only` | Curated US/UK equity growth sleeve | 60 | 10 |

### CLI toolkit

```bash
# Discover configured universes
python scripts/manage_universes.py list

# Inspect a definition
python scripts/manage_universes.py show core_global

# Validate selection → classification → returns → constraints
python scripts/manage_universes.py validate satellite_factor --verbose

# Export assets/classifications/returns to CSVs
python scripts/manage_universes.py load defensive --output-dir /tmp/universe_exports

# Compare universes side-by-side
python scripts/manage_universes.py compare core_global defensive equity_only
```

Each universe pairs selection filters, classification requirements, return
calculation settings, and min/max asset constraints. Full schema details and
extension guidance live in [`docs/universes.md`](docs/universes.md).

## Status

**Phase 1 Complete: Data Preparation Pipeline** ✅

- Modular architecture with 6 focused modules extracted from monolithic script
- Initial Phase shipped 35 tests / 75 % coverage (overall suite now 170+ tests, ~86 % coverage)
- Pandas-based processing with comprehensive validation and diagnostics
- Zero-volume severity tagging and currency reconciliation
- Match/unmatched reports with data quality flags
- Performance optimized (pytest \<70s, pre-commit ~50s)
- Latest run: 5,560 matched instruments, 4,146 exported price files, 1,262 unmatched assets documented

**Phase 2 Complete: Technical Debt Resolution** ✅

- 78% reduction in mypy type errors (40+ → 9)
- 55% complexity reduction in matching logic
- Robust concurrency implementation with 18 new tests
- 26% analysis pipeline length reduction
- Zero regressions, zero breaking changes
- See: CODE_REVIEW.md, TECHNICAL_DEBT_RESOLUTION_SUMMARY.md

**Current Work:**

- Data curation (broker fees, FX policy, unmatched resolution)

**Next Phases:**

- Portfolio construction layer (strategy adapters, rebalancing logic)
- Backtesting framework (simulation, transaction costs, analytics)
- Advanced features (sentiment overlays, Black-Litterman, regime controls)

See `REFACTORING_SUMMARY.md` for detailed history and `memory-bank/progress.md` for complete roadmap.

## Contributing

Pull requests are welcome once contribution guidelines and tests are established. Keep the Memory Bank current after every meaningful change to preserve context across sessions.
