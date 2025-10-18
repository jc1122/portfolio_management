# Universe Management Guide

## Overview

Phase 3 introduces a configurable universe system that layers on top of the
asset-selection and classification pipeline. Each universe definition combines:

- **Selection filters** (`FilterCriteria`) describing quality, history, and
  market constraints.
- **Classification requirements** that prune the universe by asset class,
  geography, or factor sub-class.
- **Return preparation settings** (`ReturnConfig`) that determine how prices are
  transformed into aligned return series.
- **Constraints** that define expected universe cardinality and data coverage.

Universes are stored in `config/universes.yaml` and consumed by
`scripts/manage_universes.py`. The CLI can list, validate, load, compare, or
export any configured universe.

## Configuration Schema

```yaml
universes:
  <universe_name>:
    description: "Human readable description"
    filter_criteria:
      data_status: ["ok", "warning"]      # optional; defaults to ["ok"]
      min_history_days: 756                  # calendar days of history required
      min_price_rows: 756                    # minimum observations
      max_gap_days: 10                       # optional; currently unused in filters
      zero_volume_severity: ["low"]         # optional; limits to specified severities
      markets: ["LSE"]                      # optional inclusion list
      regions: ["uk"]
      currencies: ["GBP"]
      categories: ["lse etfs/1"]
      allowlist: ["SPY4", "SWDA"]          # optional forced inclusions
      blocklist: ["UNWANTED"]               # optional forced exclusions
    classification_requirements:
      asset_class: ["equity"]
      sub_class: ["growth", "value"]
      geography: ["north_america"]
    return_config:
      method: "simple"                      # simple, log, excess
      frequency: "monthly"                  # daily, weekly, monthly
      handle_missing: "forward_fill"        # forward_fill, drop, interpolate
      max_forward_fill_days: 5
      min_periods: 5                         # minimum price observations required
      align_method: "outer"                 # outer union, inner intersection
      reindex_to_business_days: false
      min_coverage: 0.8                      # minimum percentage of non-null returns
    constraints:
      min_assets: 30
      max_assets: 50
```

Only the keys that differ from defaults must be specified. `FilterCriteria` and
`ReturnConfig` fields that are omitted fall back to their respective
`default()` values.

## Predefined Universes

The repository ships with four curated universes calibrated to the regenerated
tradeable dataset (October 2025):

| Universe | Purpose | Selected Assets | Assets with Returns | Return Periods |
|----------|---------|-----------------|---------------------|----------------|
| `core_global` | GBP-denominated diversified core ETF sleeve | 41 | 35 | 128 monthly periods |
| `satellite_factor` | Factor tilts (value, growth, dividend, small-cap) | 31 | 15 | 1,075 weekly periods |
| `defensive` | Income / precious metals / REIT defensive sleeve | 10 | 9 | 128 monthly periods |
| `equity_only` | Pure US/UK equity growth sleeve (curated blue chips) | 60 | 10 | 550 monthly periods |

> **Note:** Asset counts reflect the October 2025 static dataset. Future data
> curation may change availability or price coverage.

### `core_global`

- **Filters:** `data_status = ok`, ≥3 years of history, GBP-denominated LSE ETFs.
- **Classification:** Retain equity, commodity (gold), and real estate exposures
  with UK or US residence.
- **Returns:** Monthly simple returns with forward-fill (5 days) and 85%
  coverage threshold.
- **Constraints:** 30–50 assets target; actual output = 41 symbols, 35 with
  sufficient coverage after filtering.

Typical holdings: broad market equity ETFs (`SWDA`, `VUKE`), bond sleeves
(`IGLT`, `IGLS`), and commodity hedges (`SGLN`).

### `satellite_factor`

- **Filters:** Allow OK and warning data status, ≥600 days of history, curated
  allowlist of GBP-listed factor ETFs and a small set of US ADRs.
- **Classification:** Must be equity with sub-class in {growth, value,
  small_cap, dividend}.
- **Returns:** Weekly log returns using interpolation (10-day window) and 40%
  minimum coverage. This keeps 15 assets with usable return series.
- **Constraints:** 20–35 assets target; 31 selected, 15 retained after coverage
  filtering.

Allows tilting the core exposure toward style premia without overwhelming the
portfolio.

### `defensive`

- **Filters:** High-quality UK listings with long history; mix of REITs,
  dividend payers, and gold-related securities.
- **Classification:** Sub-class must be one of {gold, reit, dividend}.
- **Returns:** Monthly simple returns, drop rows with NaNs, 90% coverage.
- **Constraints:** 10–20 assets; produces 10 defensive holdings (9 with returns
  after coverage filter).

### `equity_only`

- **Filters:** 60-symbol allowlist of seasoned US large/mid-cap equities and one
  UK listing, all with ≥5,000 price observations. Only equity asset class is
  retained.
- **Returns:** Monthly simple returns, 70% coverage threshold.
- **Constraints:** 40–60 assets; 60 selected, 10 retain sufficient coverage for
  return analysis (many fail the 70% coverage rule due to delistings or sparse
  data – noted as a limitation below).

This sleeve is intended as the high-beta growth leg of the allocation, with the
option to tighten the allowlist as data curation improves.

## CLI Usage

`scripts/manage_universes.py` exposes five subcommands:

```bash
# List configured universes
python scripts/manage_universes.py list

# Show a definition
python scripts/manage_universes.py show core_global

# Validate (selection + classification + return prep + constraints)
python scripts/manage_universes.py validate satellite_factor

# Compare several universes side-by-side
python scripts/manage_universes.py compare core_global satellite_factor equity_only

# Load and export assets/classifications/returns as CSVs
python scripts/manage_universes.py load defensive --output-dir /tmp/universe_exports
```

Flags:

- `--config` to point at an alternative YAML file (defaults to
  `config/universes.yaml`).
- `--matches` to override the tradeable matches report path.
- `--prices-dir` to switch between `data/processed/tradeable_prices` (flattened
  CSVs) and `data/stooq` (raw directories).
- `--verbose` for detailed logging (especially useful to trace price gaps or
  coverage drops).

## Implementation Notes

- The `PriceLoader` automatically falls back from raw Stooq `.txt` files to the
  flattened `.csv` outputs in `data/processed/tradeable_prices`, so either
  directory can be used in `--prices-dir`.
- Coverage filters can be tuned per universe. For example, the factor sleeve
  uses a 40% threshold due to gaps in LSE factor ETF histories, whereas the core
  sleeve requires 85% coverage.
- Allowlists are provided for `satellite_factor` and `equity_only` to keep
  results deterministic until broader metadata (e.g., reliable factor tags) is
  available.
- Validation warnings about “extreme returns” surface suspected data jumps.
  These should be reviewed during data curation; they currently do not block
  universe load/validation.
- `UniverseManager.load_universe(name, use_cache=True, strict=False)` is a
  recovery-friendly mode: instead of raising, the manager logs the failure and
  returns `None`. Integration and comparison utilities rely on this behaviour
  so that a single bad universe does not abort multi-universe workflows.

## Extending the System

1. Duplicate an existing universe block in `config/universes.yaml`.
1. Adjust `filter_criteria` and `classification_requirements` as needed.
1. Run `python scripts/manage_universes.py validate <name>` to verify the new
   configuration.
1. Commit both the YAML change and any supporting documentation.

Future improvements (tracked for later phases):

- Additional classification heuristics to recognise more factor exposures.
- Automated allowlist generation based on liquidity and price coverage.
- Per-universe metadata exports summarising holdings, turnover, and coverage.

## Known Limitations

- Some LSE tickers still exhibit multi-week gaps; the loader logs each case to
  aid curation.
- Legacy delistings in the `equity_only` allowlist currently fail the 70%
  coverage rule, reducing return-ready assets to 10. Tightening the allowlist or
  lowering `min_coverage` are potential mitigations.
- Factor detection relies on keyword searches within the asset name; expanding
  classification rules (or adding metadata overrides) will enrich the satellite
  sleeve over time.
