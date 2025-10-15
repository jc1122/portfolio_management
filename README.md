# Portfolio Management Toolkit

Offline-first Python command-line toolkit for constructing and backtesting long-horizon retirement portfolios for Polish investors trading via BOŚ Dom Maklerski and mBank's MDM. The project emphasizes diversified asset allocation, factor tilts, and disciplined risk overlays, with future plans to incorporate news- and sentiment-driven signals.

## Key Features (Planned)

- Modular pipeline: data acquisition (e.g., Stooq), sanitation, asset selection, strategy engines, backtesting, and reporting.
- Multiple allocation methods: equal weight, risk parity, and mean-variance optimization via established libraries (`PyPortfolioOpt`, `riskparityportfolio`).
- Monthly/quarterly rebalancing with commission-aware opportunistic bands and risk guardrails.
- Performance analytics including Sharpe ratio, drawdowns, realized volatility, and Expected Shortfall.
- Extensible architecture prepared for sentiment/event overlays using NLP and LLM-driven factors.

## Repository Structure

```
scripts/prepare_tradeable_data.py    # CLI orchestrator for data preparation
src/portfolio_management/            # Core library modules
  ├── models.py                      # Shared dataclasses
  ├── io.py                          # File I/O operations
  ├── analysis.py                    # Validation & diagnostics
  ├── matching.py                    # Ticker matching heuristics
  ├── stooq.py                       # Index building
  ├── utils.py                       # Shared utilities
  └── config.py                      # Configuration
memory-bank/                         # Persistent documentation
  ├── projectbrief.md
  ├── productContext.md
  ├── systemPatterns.md
  ├── techContext.md
  ├── activeContext.md
  └── progress.md
tests/                               # Test suite (17 tests, 75% coverage)
AGENTS.md                            # Session boot instructions
REFACTORING_SUMMARY.md               # Refactoring history
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

1. Run the CLI (to be added) to construct and evaluate portfolios.

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

## Status

**Phase 1 Complete: Data Preparation Pipeline** ✅

- Modular architecture with 6 focused modules extracted from monolithic script
- 17 passing tests with 75% coverage, CI/CD pipeline configured
- Pandas-based processing with comprehensive validation and diagnostics
- Zero-volume severity tagging and currency reconciliation
- Match/unmatched reports with data quality flags
- Performance optimized (pytest \<3s, pre-commit ~50s)
- Latest run: 5,560 matched instruments, 4,146 exported price files, 1,262 unmatched assets documented

**Current Work:**

- Addressing technical debt in matching and concurrency implementations
- Data curation (broker fees, FX policy, unmatched resolution)

**Next Phases:**

- Portfolio construction layer (strategy adapters, rebalancing logic)
- Backtesting framework (simulation, transaction costs, analytics)
- Advanced features (sentiment overlays, Black-Litterman, regime controls)

See `REFACTORING_SUMMARY.md` for detailed history and `memory-bank/progress.md` for complete roadmap.

## Contributing

Pull requests are welcome once contribution guidelines and tests are established. Keep the Memory Bank current after every meaningful change to preserve context across sessions.
