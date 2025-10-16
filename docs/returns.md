# Return Calculation Module

## Overview

The return calculation subsystem transforms cleaned Stooq price data into aligned
return series that portfolio construction engines can consume. The pipeline lives
in `src/portfolio_management/returns.py` and is composed of three main pieces:

- `ReturnConfig` – declarative configuration for all preparation steps
- `PriceLoader` – resilient readers for the cached Stooq CSV files
- `ReturnCalculator` – end-to-end orchestration with logging and summary metrics

Stage 3 of the portfolio selection effort formalised this module so that asset
selection, classification, and downstream portfolio construction share a common
return dataset.

## Return Methods

Supported return methods are configured via `ReturnConfig.method`:

- **Simple returns**: `r_t = (P_t / P_{t-1}) - 1`
- **Log returns**: `r_t = ln(P_t / P_{t-1})`
- **Excess returns**: `r_t^{ex} = r_t - r_f`, where `r_f` is the daily risk-free
  rate derived from the annual rate supplied in the config.

Weekly and monthly resampling compounds the prepared daily returns. Simple and
excess returns multiply `(1 + r_t)` across the window, while log returns sum.

## Missing Data Strategies

`ReturnConfig.handle_missing` controls how gaps are addressed:

- `forward_fill`: forward fill up to `max_forward_fill_days`
- `drop`: drop any row that contains null values
- `interpolate`: linear interpolation with the same day limit as forward fill

All strategies log the number of values filled or dropped and warn if null data
remains after processing.

## Alignment & Coverage

Alignment is managed by `ReturnConfig.align_method`:

- `outer`: keep the union of all available dates (default)
- `inner`: keep the intersection (drops any row with a null)

Set `ReturnConfig.reindex_to_business_days` to `True` to reindex onto the
business-day calendar before applying the coverage filter. Assets must retain at
least `min_coverage` of non-null returns to survive the filter.

## Summary Statistics

Each pipeline run stores a `ReturnSummary` object accessible via
`ReturnCalculator.latest_summary`. It contains:

- Annualised mean returns per asset
- Annualised volatility per asset
- Pairwise correlation matrix
- Non-null coverage ratio per asset

These metrics drive the CLI summary output and give immediate feedback on data
quality.

## CLI Quick Start

The `scripts/calculate_returns.py` entrypoint wraps the pipeline for ad-hoc use.
It delegates to `ReturnCalculator.load_and_prepare` and surfaces any
`PortfolioManagementError` exceptions as CLI failures:

```bash
python scripts/calculate_returns.py \
  --assets data/metadata/selected_assets.csv \
  --prices-dir data/processed/tradeable_prices \
  --method simple \
  --frequency monthly \
  --handle-missing interpolate \
  --max-forward-fill 3 \
  --align-method inner \
  --business-days \
  --summary
```

Key options:

- `--min-periods` – minimum number of price observations required per asset
- `--min-coverage` – drop series below the specified non-null percentage
- `--top` – number of assets displayed in the textual summary
- `--output` – file path for exporting the prepared return matrix

The CLI exits with a non-zero status if no returns are produced (e.g. because
filters were too restrictive or price files were missing) and logs a descriptive
message stating which validation stage failed.

## Integration Notes

- `UniverseManager` consumes the same `ReturnCalculator` instance to guarantee
  consistent behaviour across universes.
- When adding new strategies or frequencies, update `ReturnConfig` validation
  and extend the resampling map to keep the CLI and manager in sync.
- Always validate new Stooq price batches with the CLI before running costly
  portfolio optimisations.
