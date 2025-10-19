# Return Calculation Module

## Overview

The return calculation subsystem transforms cleaned price data into aligned return series that portfolio construction engines can consume. The pipeline lives in the `src/portfolio_management/analytics/returns/` package and is composed of two main pieces:

- `ReturnConfig` – A declarative configuration for all preparation steps.
- `ReturnCalculator` – The engine that orchestrates the end-to-end process, from loading prices to calculating and aligning returns.

This module is a critical part of the workflow, providing the foundational data required for all quantitative analysis and portfolio optimization.

## Return Methods

Supported return methods are configured via `ReturnConfig.method`:

- **Simple returns**: `r_t = (P_t / P_{t-1}) - 1`
- **Log returns**: `r_t = ln(P_t / P_{t-1})`
- **Excess returns**: `r_t^{ex} = r_t - r_f`, where `r_f` is the daily risk-free rate derived from the annual rate supplied in the config.

Weekly and monthly resampling compounds the prepared daily returns. Simple and excess returns multiply `(1 + r_t)` across the window, while log returns are summed.

## Missing Data Strategies

`ReturnConfig.handle_missing` controls how gaps in the data are addressed:

- `forward_fill` (default): Forward fill up to `max_forward_fill_days`.
- `drop`: Drop any row that contains null values.
- `interpolate`: Linear interpolation up to `max_forward_fill_days`.

## Alignment & Coverage

Alignment is managed by `ReturnConfig.align_method`:

- `outer` (default): Keep the union of all available dates, filling gaps for assets with shorter histories.
- `inner`: Keep only the intersection of available dates (i.e., dates where all assets have data).

Set `ReturnConfig.reindex_to_business_days` to `True` to reindex the series onto the business-day calendar before applying the coverage filter. Assets must retain at least `min_coverage` of non-null returns to survive the filter.

## Summary Statistics

Each pipeline run stores a `ReturnSummary` object accessible via `ReturnCalculator.latest_summary`. It contains:

- Annualised mean returns per asset
- Annualised volatility per asset
- Pairwise correlation matrix
- Non-null coverage ratio per asset

These metrics drive the CLI summary output and give immediate feedback on data quality.

## CLI Quick Start

The `scripts/calculate_returns.py` entrypoint wraps the pipeline for ad-hoc use. It delegates to the `ReturnCalculator` and surfaces any `PortfolioManagementError` exceptions as CLI failures.

### Example

```bash
# Calculate monthly simple returns, handling missing data by interpolation
python scripts/calculate_returns.py \
  --assets data/processed/classified_assets.csv \
  --prices-dir data/processed/tradeable_prices \
  --method simple \
  --frequency monthly \
  --handle-missing interpolate \
  --max-forward-fill 5 \
  --align-method inner \
  --business-days \
  --summary \
  --output data/processed/returns.csv
```

### Key Arguments

The CLI offers a rich set of configuration options:

- `--assets`: **(Required)** Path to the classified assets CSV file.
- `--prices-dir`: **(Required)** Directory containing the cleaned price history files.
- `--output`: Path to save the final returns matrix CSV.
- `--method`: The calculation method (`simple`, `log`, `excess`). Default: `simple`.
- `--frequency`: The resampling frequency (`daily`, `weekly`, `monthly`). Default: `daily`.
- `--handle-missing`: Strategy for handling gaps (`forward_fill`, `drop`, `interpolate`). Default: `forward_fill`.
- `--max-forward-fill`: The maximum number of consecutive days to fill. Default: `5`.
- `--align-method`: How to align assets with different date ranges (`outer` or `inner`). Default: `outer`.
- `--min-coverage`: The minimum percentage (0.0 to 1.0) of non-null returns required to keep an asset. Default: `0.8`.
- `--summary`: If specified, prints a summary of return statistics instead of the full matrix.
- `--top`: The number of top/bottom assets to show in the summary. Default: `5`.

## Integration Notes

- `UniverseManager` consumes the same `ReturnCalculator` instance to guarantee consistent behaviour across universes.
- When adding new strategies or frequencies, update `ReturnConfig` validation and extend the resampling logic to keep the CLI and manager in sync.
- Always validate new price data batches with the CLI before running costly portfolio optimisations.
