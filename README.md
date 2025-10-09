# Portfolio Management Toolkit

Offline-first Python command-line toolkit for constructing and backtesting long-horizon retirement portfolios for Polish investors trading via BOŚ Dom Maklerski and mBank's MDM. The project emphasizes diversified asset allocation, factor tilts, and disciplined risk overlays, with future plans to incorporate news- and sentiment-driven signals.

## Key Features (Planned)
- Modular pipeline: data acquisition (e.g., Stooq), sanitation, asset selection, strategy engines, backtesting, and reporting.
- Multiple allocation methods: equal weight, risk parity, and mean-variance optimization via established libraries (`PyPortfolioOpt`, `riskparityportfolio`).
- Monthly/quarterly rebalancing with commission-aware opportunistic bands and risk guardrails.
- Performance analytics including Sharpe ratio, drawdowns, realized volatility, and Expected Shortfall.
- Extensible architecture prepared for sentiment/event overlays using NLP and LLM-driven factors.

## Repository Structure
- `memory-bank/`: Persistent project documentation (project brief, product context, system patterns, tech context, active context, progress log).
- `scripts/prepare_tradeable_data.py`: CLI utility that indexes unpacked Stooq price files, matches them against BOŚ/mBank tradeable universes, and exports curated price series.
- `AGENTS.md`: Operating instructions ensuring each session starts by reviewing the Memory Bank.

## Getting Started
1. Ensure Python 3.10+ is available.
2. Create and activate a virtual environment.
3. Install dependencies (list forthcoming as modules are implemented).
4. Populate cached historical data from Stooq or other free sources.
5. Run the CLI (to be added) to construct and evaluate portfolios.

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
    --max-workers 8 --index-workers 8 --overwrite-prices --force-reindex
```

The first run builds a cached index (≈40 s for ~62k files); subsequent runs can omit `--force-reindex` for <3 s incremental updates.

Optional flags: `--include-empty-prices` forces exports for tickers without usable data (normally skipped) and `--lse-currency-policy` lets you choose whether London listings keep the broker currency (`broker`, default), adopt Stooq’s inferred currency (`stooq`), or raise an error when the currencies diverge (`strict`).

> **Heads-up:** The matching heuristics now cover common TSX, Xetra, Euronext, Swiss, and Brussels suffixes. If venues such as Xetra still appear in the unmatched report, confirm that the corresponding Stooq directory bundles (e.g., `d_de_txt/…`) have been unpacked—those files are absent from the current repository snapshot.
>
> The match report now includes a `data_flags` column populated by additional validation checks (duplicate dates, non-positive closes, zero/missing volume, etc.) and the CLI emits summaries/warnings so suspect price files can be triaged immediately.

## Status
- Documentation and repository scaffolding complete.
- Stooq data preparation script now enriches match outputs with per-instrument price coverage, currency diagnostics, and zero-volume severity tagging while preventing cross-venue fallbacks; flagged listings remain available but carry warnings in `data/metadata/tradeable_data_flags.csv`.
- Latest data export matched 5,560 instruments (4,146 price files after dropping two empty histories) and clearly tags 1,262 unmatched assets by missing Stooq regions (`.TO`, `.DE`, `.FR/.PA`, `.CH`) or alias requirements.
- Next steps involve implementing the modular CLI, portfolio construction engines, and backtesting/reporting pipeline.

## Contributing
Pull requests are welcome once contribution guidelines and tests are established. Keep the Memory Bank current after every meaningful change to preserve context across sessions.
