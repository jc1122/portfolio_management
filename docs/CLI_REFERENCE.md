# CLI Reference Guide

**Complete command-line interface reference for portfolio management toolkit**

This document provides comprehensive documentation for all 7 CLI scripts in the `scripts/` directory.

______________________________________________________________________

## Table of Contents

1. [prepare_tradeable_data.py](#1-prepare_tradeable_datapy) - Data preparation & ingestion
1. [select_assets.py](#2-select_assetspy) - Asset filtering & selection
1. [classify_assets.py](#3-classify_assetspy) - Asset classification
1. [calculate_returns.py](#4-calculate_returnspy) - Return calculation
1. [manage_universes.py](#5-manage_universespy) - Universe management
1. [construct_portfolio.py](#6-construct_portfoliopy) - Portfolio weight generation
1. [run_backtest.py](#7-run_backtestpy) - Backtesting execution

______________________________________________________________________

## 1. prepare_tradeable_data.py

**Purpose**: Ingest Stooq CSV data, match instruments with broker lists, validate quality, and export tradeable price histories.

### Synopsis

```bash
python scripts/prepare_tradeable_data.py [OPTIONS]
```

### Description

This script orchestrates the complete data preparation pipeline:

1. **Index Stooq data** - Scan directories and build metadata index
1. **Match instruments** - Link broker symbols to Stooq data files
1. **Validate quality** - Check for data issues (gaps, duplicates, etc.)
1. **Export prices** - Write tradeable instrument price histories

### Required Arguments

None (all arguments have defaults)

### Optional Arguments

#### Data Sources

- `--data-dir PATH`

  - Root directory containing unpacked Stooq data
  - Default: `data/stooq`
  - Example: `--data-dir data/stooq`

- `--tradeable-dir PATH`

  - Directory containing broker tradeable instrument CSV files
  - Default: `tradeable_instruments`
  - Example: `--tradeable-dir tradeable_instruments`

#### Output Paths

- `--metadata-output PATH`

  - Path to write Stooq metadata index CSV
  - Default: `data/metadata/stooq_index.csv`
  - Example: `--metadata-output data/metadata/stooq_index.csv`

- `--match-report PATH`

  - Output CSV for matched tradeable instruments
  - Default: `data/metadata/tradeable_matches.csv`
  - Example: `--match-report data/metadata/tradeable_matches.csv`

- `--unmatched-report PATH`

  - Output CSV listing unmatched instruments
  - Default: `data/metadata/tradeable_unmatched.csv`
  - Example: `--unmatched-report data/metadata/tradeable_unmatched.csv`

- `--prices-output PATH`

  - Directory for exported tradeable price histories
  - Default: `data/processed/tradeable_prices`
  - Example: `--prices-output data/processed/tradeable_prices`

#### Performance & Caching

- `--incremental`

  - Enable incremental resume: skip processing if inputs unchanged
  - **Speedup**: 3-5 minutes → \<5 seconds when inputs unchanged
  - Example: `--incremental`

- `--cache-metadata PATH`

  - Path to cache metadata file for incremental resume
  - Default: `data/metadata/.prepare_cache.json`
  - Example: `--cache-metadata data/metadata/.prepare_cache.json`

- `--max-workers INT`

  - Maximum number of threads for matching and exporting
  - Default: CPU cores - 1
  - Example: `--max-workers 8`

- `--index-workers INT`

  - Number of threads for directory indexing
  - Default: 0 (uses --max-workers value)
  - Example: `--index-workers 4`

#### Processing Options

- `--force-reindex`

  - Rebuild Stooq metadata index even if CSV already exists
  - Use when Stooq data has changed
  - Example: `--force-reindex`

- `--overwrite-prices`

  - Rewrite price CSVs even if they already exist
  - Use when price data has been updated
  - Example: `--overwrite-prices`

- `--include-empty-prices`

  - Export price CSVs even when source file lacks usable data
  - Default: skip empty files
  - Example: `--include-empty-prices`

- `--lse-currency-policy {broker|stooq|strict}`

  - How to resolve LSE currency mismatches
  - `broker` (default): Keep broker currency
  - `stooq`: Force Stooq inferred currency
  - `strict`: Treat mismatches as errors
  - Example: `--lse-currency-policy broker`

#### Logging

- `--log-level {DEBUG|INFO|WARNING|ERROR}`
  - Logging verbosity
  - Default: `INFO`
  - Example: `--log-level DEBUG`

### Examples

#### Basic usage (first run)

```bash
python scripts/prepare_tradeable_data.py \
    --data-dir data/stooq \
    --tradeable-dir tradeable_instruments \
    --metadata-output data/metadata/stooq_index.csv \
    --match-report data/metadata/tradeable_matches.csv \
    --prices-output data/processed/tradeable_prices \
    --force-reindex
```

#### With incremental resume (subsequent runs)

```bash
python scripts/prepare_tradeable_data.py \
    --incremental \
    --overwrite-prices
```

**Result**: Completes in \<5 seconds if inputs unchanged

#### High-performance mode (large datasets)

```bash
python scripts/prepare_tradeable_data.py \
    --incremental \
    --max-workers 12 \
    --index-workers 8
```

#### Debug mode (troubleshooting)

```bash
python scripts/prepare_tradeable_data.py \
    --log-level DEBUG \
    --force-reindex
```

### Output Files

| File | Description |
|------|-------------|
| `data/metadata/stooq_index.csv` | Complete Stooq data catalog with file paths |
| `data/metadata/tradeable_matches.csv` | Matched instruments with quality flags |
| `data/metadata/tradeable_unmatched.csv` | Broker symbols not found in Stooq data |
| `data/processed/tradeable_prices/*.csv` | Individual price history files per ticker |
| `data/metadata/.prepare_cache.json` | Cache metadata for incremental resume |

### Performance Notes

- **First run**: 3-5 minutes for 500 instruments, 70k+ files
- **Incremental run**: \<5 seconds when inputs unchanged
- **Parallelization**: Scales linearly up to CPU core count
- **Memory usage**: ~100-200 MB typical, ~500 MB for very large datasets

### See Also

- [Data Pipeline Documentation](data_pipeline.md)
- [Incremental Resume Guide](incremental_resume.md)
- [Troubleshooting Guide](troubleshooting.md)

______________________________________________________________________

## 2. select_assets.py

**Purpose**: Filter assets based on liquidity, price thresholds, market cap, and other investment criteria.

### Synopsis

```bash
python scripts/select_assets.py --match-report PATH [OPTIONS]
```

### Description

Filters the matched instrument catalog to select high-quality tradeable assets meeting specified criteria:

- **Liquidity filtering** - Minimum volume, market cap
- **Price filtering** - Avoid penny stocks
- **History filtering** - Minimum data availability
- **Market/region filtering** - Geographic focus
- **Allowlist/blocklist** - Manual overrides

### Required Arguments

- `--match-report PATH`
  - Path to tradeable matches CSV from `prepare_tradeable_data.py`
  - Example: `--match-report data/metadata/tradeable_matches.csv`

### Optional Arguments

#### Output

- `--output PATH`
  - Path to save selected assets CSV
  - If omitted, prints to console
  - Example: `--output data/selected/my_universe.csv`

#### Data Quality Filters

- `--data-status STATUSES`

  - Comma-separated list of allowed quality statuses
  - Default: `ok`
  - Options: `ok`, `warning`, `error`
  - Example: `--data-status ok,warning`

- `--min-history-days INT`

  - Minimum calendar days of price history
  - Default: 252 (1 year)
  - Example: `--min-history-days 756` (3 years)

- `--min-price-rows INT`

  - Minimum number of trading days with data
  - Default: 252
  - Example: `--min-price-rows 500`

#### Geographic Filters

- `--markets MARKETS`

  - Comma-separated list of market codes
  - Example: `--markets LSE,NYSE,NSQ`
  - Common markets: NYSE, NSQ (NASDAQ), LSE, TSX, ETR (Xetra)

- `--regions REGIONS`

  - Comma-separated list of regions
  - Example: `--regions "Europe,North America"`

- `--currencies CURRENCIES`

  - Comma-separated list of currencies
  - Example: `--currencies GBP,USD,EUR`

#### Manual Overrides

- `--allowlist PATH`

  - File with symbols/ISINs to force-include (one per line)
  - Example: `--allowlist config/must_include.txt`

- `--blocklist PATH`

  - File with symbols/ISINs to exclude (one per line)
  - Example: `--blocklist config/excluded.txt`

#### Execution Options

- `--verbose`

  - Enable detailed logging
  - Example: `--verbose`

- `--dry-run`

  - Show selection summary without writing files
  - Example: `--dry-run`

### Examples

#### US large-cap stocks (3+ years history)

```bash
python scripts/select_assets.py \
    --match-report data/metadata/tradeable_matches.csv \
    --output data/selected/us_large_cap.csv \
    --markets "NYSE,NSQ" \
    --min-history-days 1095 \
    --min-price-rows 756 \
    --data-status ok
```

#### European stocks (clean data only)

```bash
python scripts/select_assets.py \
    --match-report data/metadata/tradeable_matches.csv \
    --output data/selected/european.csv \
    --regions Europe \
    --currencies "EUR,GBP" \
    --data-status ok \
    --min-history-days 756
```

#### With allowlist/blocklist

```bash
python scripts/select_assets.py \
    --match-report data/metadata/tradeable_matches.csv \
    --output data/selected/filtered.csv \
    --markets "NYSE,NSQ,LSE" \
    --allowlist config/must_have_stocks.txt \
    --blocklist config/exclude_stocks.txt
```

#### Dry run (check selection)

```bash
python scripts/select_assets.py \
    --match-report data/metadata/tradeable_matches.csv \
    --markets "NYSE,NSQ" \
    --min-history-days 1095 \
    --dry-run \
    --verbose
```

### Output Format

CSV with columns:

- `symbol` - Ticker symbol
- `isin` - ISIN code
- `name` - Security name
- `market` - Market code
- `currency` - Trading currency
- `region` - Geographic region
- `history_days` - Days of available data
- `price_rows` - Number of price observations
- `data_status` - Quality flag (ok/warning/error)

### See Also

- [Asset Selection Guide](asset_selection.md)
- [Data Pipeline Documentation](data_pipeline.md)

______________________________________________________________________

## 3. classify_assets.py

**Purpose**: Classify assets by geographic region, sector, and asset type for portfolio analysis.

### Synopsis

```bash
python scripts/classify_assets.py --input PATH [OPTIONS]
```

### Description

Applies classification rules to categorize selected assets:

- **Geographic classification** - Continent, region, country
- **Sector classification** - Industry groups
- **Asset type classification** - Equity, ETF, bond, etc.
- **Manual overrides** - User-defined classifications

### Required Arguments

- `--input PATH`
  - Path to selected assets CSV from `select_assets.py`
  - Example: `--input data/selected/my_universe.csv`

### Optional Arguments

#### Output

- `--output PATH`
  - Path to save classified assets CSV
  - If omitted, prints to console
  - Example: `--output data/classified/my_universe.csv`

#### Classification Options

- `--overrides PATH`

  - CSV file with manual classification overrides
  - Columns: `symbol`, `region`, `sector`, `asset_type`
  - Example: `--overrides config/classification_overrides.csv`

- `--export-for-review PATH`

  - Export CSV template for manual review/editing
  - Example: `--export-for-review review/classifications.csv`

#### Reporting

- `--summary`

  - Print classification summary statistics
  - Example: `--summary`

- `--verbose`

  - Enable detailed logging
  - Example: `--verbose`

### Examples

#### Basic classification

```bash
python scripts/classify_assets.py \
    --input data/selected/us_large_cap.csv \
    --output data/classified/us_large_cap.csv \
    --summary
```

#### With manual overrides

```bash
python scripts/classify_assets.py \
    --input data/selected/european.csv \
    --output data/classified/european.csv \
    --overrides config/manual_classifications.csv \
    --summary
```

#### Export for manual review

```bash
python scripts/classify_assets.py \
    --input data/selected/my_universe.csv \
    --export-for-review review/classify_review.csv
# Edit review/classify_review.csv manually
python scripts/classify_assets.py \
    --input data/selected/my_universe.csv \
    --overrides review/classify_review.csv \
    --output data/classified/my_universe.csv
```

### Output Format

CSV with additional classification columns:

- `continent` - Geographic continent
- `region` - Sub-region (e.g., Western Europe)
- `country` - Country code
- `sector` - Industry sector
- `industry` - Industry group
- `asset_type` - Asset class (equity/ETF/bond)

### Classification Rules

**Geographic**:

- Based on market code and ISIN prefix
- Fallback to manual overrides if ambiguous

**Sector**:

- Inferred from security name and market sector data
- Requires manual override for non-standard names

**Asset Type**:

- ETF: Name contains "ETF", "FUND", "INDEX"
- Bond: Name contains "BOND", "NOTE", "TREASURY"
- Equity: Default for stocks

### See Also

- [Asset Classification Guide](asset_classification.md)
- [Classification Best Practices](configuration_best_practices.md)

______________________________________________________________________

## 4. calculate_returns.py

**Purpose**: Calculate aligned return series with point-in-time integrity for backtesting.

### Synopsis

```bash
python scripts/calculate_returns.py --assets PATH --prices-dir PATH [OPTIONS]
```

### Description

Computes return series from price data with:

- **Return methods** - Simple, log, or excess returns
- **Frequency resampling** - Daily, weekly, monthly
- **Missing data handling** - Forward-fill, drop, interpolate
- **Alignment** - Ensure consistent date indices
- **Quality checks** - Coverage thresholds

### Required Arguments

- `--assets PATH`

  - Path to classified assets CSV
  - Example: `--assets data/classified/my_universe.csv`

- `--prices-dir PATH`

  - Directory containing individual price CSV files
  - Example: `--prices-dir data/processed/tradeable_prices`

### Optional Arguments

#### Output

- `--output PATH`
  - Path to save returns CSV (date × ticker matrix)
  - If omitted, prints to console
  - Example: `--output data/processed/returns/my_universe.csv`

#### Return Calculation

- `--method {simple|log|excess}`

  - Return calculation method
  - `simple`: (P1 - P0) / P0
  - `log`: log(P1 / P0)
  - `excess`: simple returns - risk-free rate
  - Default: `simple`
  - Example: `--method log`

- `--frequency {daily|weekly|monthly}`

  - Resampling frequency
  - Default: `daily`
  - Example: `--frequency monthly`

- `--risk-free-rate FLOAT`

  - Annual risk-free rate for excess returns
  - Required if `--method excess`
  - Example: `--risk-free-rate 0.02` (2% annually)

#### Missing Data Handling

- `--handle-missing {forward_fill|drop|interpolate}`

  - Strategy for missing values
  - `forward_fill`: Carry last known value forward
  - `drop`: Remove assets with missing data
  - `interpolate`: Linear interpolation
  - Default: `forward_fill`
  - Example: `--handle-missing forward_fill`

- `--max-forward-fill INT`

  - Maximum consecutive days to forward-fill
  - Default: 5
  - Example: `--max-forward-fill 10`

- `--min-periods INT`

  - Minimum price observations required per asset
  - Default: 252 (1 year daily)
  - Example: `--min-periods 500`

#### Alignment & Quality

- `--align-method {outer|inner}`

  - Date alignment strategy
  - `outer`: Union of all dates (more data, more NaN)
  - `inner`: Intersection of dates (less data, no NaN)
  - Default: `inner`
  - Example: `--align-method inner`

- `--business-days`

  - Reindex to business day calendar
  - Removes weekends/holidays
  - Example: `--business-days`

- `--min-coverage FLOAT`

  - Minimum non-null coverage threshold (0-1)
  - Assets below threshold are dropped
  - Default: 0.8 (80%)
  - Example: `--min-coverage 0.90`

#### Performance

- `--fast-io {pandas|polars|pyarrow|auto}`
  - I/O backend for large datasets
  - `auto`: Select best available
  - Default: `pandas`
  - Example: `--fast-io polars`

#### Reporting

- `--summary`

  - Print performance summary (annualized return, volatility, Sharpe)
  - Example: `--summary`

- `--top INT`

  - Number of top/bottom assets in summary
  - Default: 5
  - Example: `--top 10`

- `--verbose`

  - Enable detailed logging
  - Example: `--verbose`

### Examples

#### Daily simple returns

```bash
python scripts/calculate_returns.py \
    --assets data/classified/us_large_cap.csv \
    --prices-dir data/processed/tradeable_prices \
    --output data/processed/returns/us_large_cap.csv \
    --method simple \
    --frequency daily
```

#### Monthly log returns (business days)

```bash
python scripts/calculate_returns.py \
    --assets data/classified/my_universe.csv \
    --prices-dir data/processed/tradeable_prices \
    --output data/processed/returns/monthly_log.csv \
    --method log \
    --frequency monthly \
    --business-days \
    --summary
```

#### With fast I/O (large dataset)

```bash
python scripts/calculate_returns.py \
    --assets data/classified/large_universe.csv \
    --prices-dir data/processed/tradeable_prices \
    --output data/processed/returns/large_universe.csv \
    --fast-io polars \
    --min-coverage 0.90
```

#### Excess returns over risk-free rate

```bash
python scripts/calculate_returns.py \
    --assets data/classified/my_universe.csv \
    --prices-dir data/processed/tradeable_prices \
    --output data/processed/returns/excess.csv \
    --method excess \
    --risk-free-rate 0.025
```

### Output Format

CSV matrix:

- Rows: Dates (index)
- Columns: Ticker symbols
- Values: Returns (simple, log, or excess)

### Performance Notes

- **pandas**: Standard backend, ~60s for 1000 assets × 5 years
- **polars**: Fast backend, ~15s for 1000 assets × 5 years (4× speedup)
- **pyarrow**: Alternative fast backend, ~20s (3× speedup)

### See Also

- [Return Calculation Guide](calculate_returns.md)
- [Fast I/O Documentation](fast_io.md)
- [Point-in-Time Integrity](returns.md)

______________________________________________________________________

## 5. manage_universes.py

**Purpose**: Define, validate, and manage investment universes via YAML configuration.

### Synopsis

```bash
python scripts/manage_universes.py --config PATH ACTION [OPTIONS]
```

### Description

Manages universe definitions through YAML configuration:

- **Define** - Create universe specifications
- **Validate** - Check configuration syntax and references
- **Export** - Generate asset lists from universe definitions
- **Compare** - Analyze differences between universes

### Required Arguments

- `--config PATH`

  - Path to universe YAML configuration file
  - Example: `--config config/universes.yaml`

- `ACTION`

  - One of: `validate`, `export`, `compare`, `load`
  - Example: `validate`

### Optional Arguments

#### Universe Selection

- `--universe NAME`

  - Universe name within config file
  - Example: `--universe core_global`

- `--universes NAMES`

  - Comma-separated list for comparison
  - Example: `--universes "universe1,universe2"`

#### Output

- `--output PATH`

  - Output path for export action
  - Example: `--output data/universes/core_global.csv`

- `--format {csv|json}`

  - Output format for export
  - Default: `csv`
  - Example: `--format json`

#### Reporting

- `--verbose`
  - Enable detailed logging
  - Example: `--verbose`

### Examples

#### Validate configuration

```bash
python scripts/manage_universes.py \
    --config config/universes.yaml \
    validate
```

#### Export universe to CSV

```bash
python scripts/manage_universes.py \
    --config config/universes.yaml \
    --universe core_global \
    export \
    --output data/universes/core_global.csv
```

#### Compare two universes

```bash
python scripts/manage_universes.py \
    --config config/universes.yaml \
    compare \
    --universes "conservative,aggressive"
```

#### Load and process universe

```bash
python scripts/manage_universes.py \
    --config config/universes.yaml \
    --universe my_universe \
    load
```

**Note**: `load` action automatically executes selection + classification + returns

### Universe YAML Schema

```yaml
universes:
  universe_name:
    description: "Brief description"
    filters:
      markets:
        - NYSE
        - NSQ
      min_market_cap: 1000000000  # $1B
      min_volume: 100000
      max_position_count: 50
    classifications:
      regions:
        - "North America"
      asset_types:
        - equity
    rebalancing:
      frequency: monthly
      drift_threshold: 0.05
```

### See Also

- [Universe Management Guide](universes.md)
- [Universe YAML Reference](universe_yaml_reference.md)
- [Configuration Best Practices](configuration_best_practices.md)

______________________________________________________________________

## 6. construct_portfolio.py

**Purpose**: Generate portfolio weights using specified allocation strategy.

### Synopsis

```bash
python scripts/construct_portfolio.py --returns PATH --strategy STRATEGY [OPTIONS]
```

### Description

Constructs portfolio weights from return data using:

- **Equal Weight** - Simple 1/N allocation
- **Risk Parity** - Equal risk contribution
- **Mean-Variance** - Markowitz optimization

### Required Arguments

- `--returns PATH`

  - Path to returns CSV (date × ticker matrix)
  - Example: `--returns data/processed/returns/my_universe.csv`

- `--strategy {equal_weight|risk_parity|mean_variance}`

  - Portfolio construction strategy
  - Example: `--strategy risk_parity`

### Optional Arguments

#### Output

- `--output PATH`

  - Path to save portfolio weights CSV
  - Example: `--output outputs/portfolio_weights.csv`

- `--format {csv|json}`

  - Output format
  - Default: `csv`
  - Example: `--format json`

#### Weight Constraints

- `--max-weight FLOAT`

  - Maximum position size (0-1)
  - Default: 0.25 (25%)
  - Example: `--max-weight 0.10`

- `--min-weight FLOAT`

  - Minimum position size (0-1)
  - Default: 0.01 (1%)
  - Example: `--min-weight 0.02`

#### Risk Parity Options

- `--risk-tolerance FLOAT`
  - Risk tolerance parameter
  - Higher = more risk
  - Default: 1.0
  - Example: `--risk-tolerance 1.5`

#### Mean-Variance Options

- `--target-return FLOAT`

  - Target annualized return (required for mean-variance)
  - Example: `--target-return 0.12` (12% annually)

- `--risk-aversion FLOAT`

  - Risk aversion coefficient
  - Higher = more conservative
  - Default: 1.0
  - Example: `--risk-aversion 2.0`

#### Multi-Strategy Comparison

- `--compare`
  - Run all strategies and compare
  - Outputs comparison matrix
  - Example: `--compare`

#### Reporting

- `--summary`

  - Print allocation summary
  - Example: `--summary`

- `--verbose`

  - Enable detailed logging
  - Example: `--verbose`

### Examples

#### Equal-weight portfolio

```bash
python scripts/construct_portfolio.py \
    --returns data/processed/returns/my_universe.csv \
    --strategy equal_weight \
    --output outputs/portfolios/equal_weight.csv
```

#### Risk parity with constraints

```bash
python scripts/construct_portfolio.py \
    --returns data/processed/returns/my_universe.csv \
    --strategy risk_parity \
    --max-weight 0.15 \
    --min-weight 0.02 \
    --output outputs/portfolios/risk_parity.csv \
    --summary
```

#### Mean-variance optimization

```bash
python scripts/construct_portfolio.py \
    --returns data/processed/returns/my_universe.csv \
    --strategy mean_variance \
    --target-return 0.10 \
    --max-weight 0.20 \
    --output outputs/portfolios/mean_variance.csv
```

#### Compare all strategies

```bash
python scripts/construct_portfolio.py \
    --returns data/processed/returns/my_universe.csv \
    --compare \
    --output outputs/portfolios/comparison.csv
```

### Output Format

**Single Strategy CSV**:

```
ticker,weight
AAPL,0.15
MSFT,0.12
...
```

**Comparison CSV** (--compare):

```
ticker,equal_weight,risk_parity,mean_variance
AAPL,0.10,0.15,0.12
MSFT,0.10,0.08,0.14
...
```

### See Also

- [Portfolio Construction Guide](portfolio_construction.md)
- [Strategy Comparison](portfolio_construction.md#strategy-comparison)

______________________________________________________________________

## 7. run_backtest.py

**Purpose**: Execute full portfolio backtest with rebalancing, transaction costs, and performance analytics.

### Synopsis

```bash
python scripts/run_backtest.py STRATEGY [OPTIONS]
```

### Description

Runs complete backtesting simulation with:

- **Portfolio rebalancing** - Periodic or drift-triggered
- **Transaction costs** - Commissions and slippage
- **Performance metrics** - Sharpe, drawdown, turnover
- **Factor preselection** - Momentum/low-vol filtering
- **Membership policy** - Turnover control
- **Statistics caching** - Performance optimization
- **Visualization** - Auto-generate charts and dashboard

### Required Arguments

- `STRATEGY`
  - Portfolio construction strategy
  - Choices: `equal_weight`, `risk_parity`, `mean_variance`
  - Example: `risk_parity`

### Optional Arguments

#### Date Range

- `--start-date YYYY-MM-DD`

  - Backtest start date
  - Default: 2020-01-01
  - Example: `--start-date 2015-01-01`

- `--end-date YYYY-MM-DD`

  - Backtest end date
  - Default: today
  - Example: `--end-date 2024-12-31`

#### Capital & Costs

- `--initial-capital DECIMAL`

  - Initial portfolio capital
  - Default: 100000
  - Example: `--initial-capital 500000`

- `--commission DECIMAL`

  - Commission rate (e.g., 0.001 = 0.1%)
  - Default: 0.001
  - Example: `--commission 0.002`

- `--slippage DECIMAL`

  - Slippage rate (e.g., 0.0005 = 0.05%)
  - Default: 0.0005
  - Example: `--slippage 0.001`

- `--min-commission DECIMAL`

  - Minimum commission per trade
  - Default: 1.0
  - Example: `--min-commission 5.0`

#### Rebalancing

- `--rebalance-frequency {daily|weekly|monthly|quarterly|annual}`

  - Rebalancing frequency
  - Default: monthly
  - Example: `--rebalance-frequency quarterly`

- `--drift-threshold DECIMAL`

  - Drift threshold for opportunistic rebalancing (0-1)
  - Default: 0.05 (5%)
  - Example: `--drift-threshold 0.10`

- `--lookback-periods INT`

  - Rolling lookback window for parameter estimation (days)
  - Default: 252 (1 year)
  - Example: `--lookback-periods 504` (2 years)

#### Data Sources

- `--universe-file PATH`

  - Path to universe configuration YAML
  - Default: config/universes.yaml
  - Example: `--universe-file config/my_universes.yaml`

- `--universe-name NAME`

  - Universe name in configuration
  - Default: default
  - Example: `--universe-name core_global`

- `--prices-file PATH`

  - Path to prices CSV
  - Default: data/processed/prices.csv
  - Example: `--prices-file data/processed/tradeable_prices.csv`

- `--returns-file PATH`

  - Path to returns CSV
  - Default: data/processed/returns.csv
  - Example: `--returns-file data/processed/returns/my_universe.csv`

#### Strategy Parameters

- `--max-position-size DECIMAL`

  - Maximum position size (0-1)
  - Default: 0.25
  - Example: `--max-position-size 0.15`

- `--min-position-size DECIMAL`

  - Minimum position size (0-1)
  - Default: 0.01
  - Example: `--min-position-size 0.02`

#### Mean-Variance Specific

- `--target-return DECIMAL`

  - Target annualized return (required for mean-variance)
  - Example: `--target-return 0.12`

- `--risk-aversion DECIMAL`

  - Risk aversion parameter
  - Default: 1.0
  - Example: `--risk-aversion 1.5`

#### Preselection (Factor-Based Filtering)

- `--preselect-method {momentum|low_vol|combined}`

  - Preselection method
  - `momentum`: Cumulative returns
  - `low_vol`: Realized volatility
  - `combined`: Both factors
  - Example: `--preselect-method momentum`

- `--preselect-top-k INT`

  - Number of assets to select (e.g., 100→30)
  - Example: `--preselect-top-k 30`

- `--preselect-lookback INT`

  - Lookback period for factors (days)
  - Default: 252
  - Example: `--preselect-lookback 126` (6 months)

- `--preselect-skip-recent INT`

  - Days to skip at end (avoid short-term reversal)
  - Default: 21 (1 month)
  - Example: `--preselect-skip-recent 5`

#### Membership Policy (Turnover Control)

- `--membership-policy {none|turnover_control}`

  - Enable membership policy
  - `none` (default): No turnover control
  - `turnover_control`: Enforce constraints
  - Example: `--membership-policy turnover_control`

- `--max-turnover DECIMAL`

  - Maximum turnover per rebalance (0-1)
  - Example: `--max-turnover 0.20` (20%)

- `--min-hold-periods INT`

  - Minimum holding periods before selling
  - Example: `--min-hold-periods 2`

- `--buffer-rank INT`

  - Rank buffer for membership stability
  - Default: 5
  - Example: `--buffer-rank 10`

#### Output & Visualization

- `--output-dir PATH`

  - Directory for backtest results
  - Default: outputs/backtests
  - Example: `--output-dir outputs/my_backtest`

- `--format {csv|json|both}`

  - Output format
  - Default: csv
  - Example: `--format both`

- `--visualize`

  - Auto-generate charts and HTML dashboard
  - Creates: equity curve, drawdown, returns distribution, metrics
  - Example: `--visualize`

- `--plot-format {png|svg|pdf}`

  - Chart image format
  - Default: png
  - Example: `--plot-format svg`

#### Performance

- `--enable-caching`

  - Enable statistics caching (covariance, returns)
  - Recommended for 300+ assets, monthly rebalancing
  - **Speedup**: ~50% for eligible scenarios
  - Example: `--enable-caching`

- `--cache-dir PATH`

  - Cache directory
  - Default: .cache/statistics
  - Example: `--cache-dir /tmp/backtest_cache`

#### Execution Options

- `--verbose`

  - Enable detailed logging
  - Example: `--verbose`

- `--debug`

  - Enable debug mode (very detailed)
  - Example: `--debug`

### Examples

#### Basic equal-weight backtest

```bash
python scripts/run_backtest.py equal_weight \
    --start-date 2020-01-01 \
    --end-date 2024-12-31 \
    --returns-file data/processed/returns/my_universe.csv \
    --output-dir outputs/equal_weight \
    --visualize
```

#### Risk parity with transaction costs

```bash
python scripts/run_backtest.py risk_parity \
    --start-date 2015-01-01 \
    --initial-capital 500000 \
    --commission 0.002 \
    --slippage 0.001 \
    --rebalance-frequency monthly \
    --returns-file data/processed/returns/my_universe.csv \
    --output-dir outputs/risk_parity \
    --visualize
```

#### Momentum strategy with preselection

```bash
python scripts/run_backtest.py equal_weight \
    --preselect-method momentum \
    --preselect-top-k 30 \
    --preselect-lookback 252 \
    --returns-file data/processed/returns/large_universe.csv \
    --output-dir outputs/momentum_30 \
    --visualize
```

#### Low-turnover risk parity

```bash
python scripts/run_backtest.py risk_parity \
    --membership-policy turnover_control \
    --max-turnover 0.15 \
    --min-hold-periods 2 \
    --rebalance-frequency monthly \
    --returns-file data/processed/returns/my_universe.csv \
    --output-dir outputs/low_turnover \
    --visualize
```

#### Mean-variance with all features

```bash
python scripts/run_backtest.py mean_variance \
    --target-return 0.12 \
    --risk-aversion 1.5 \
    --preselect-method combined \
    --preselect-top-k 40 \
    --membership-policy turnover_control \
    --max-turnover 0.20 \
    --enable-caching \
    --returns-file data/processed/returns/large_universe.csv \
    --output-dir outputs/mean_var_optimized \
    --visualize
```

#### Production backtest (300+ assets)

```bash
python scripts/run_backtest.py risk_parity \
    --start-date 2010-01-01 \
    --rebalance-frequency monthly \
    --lookback-periods 504 \
    --enable-caching \
    --returns-file data/processed/returns/large_universe.csv \
    --output-dir outputs/production_backtest \
    --format both \
    --visualize
```

### Output Files

| File | Description |
|------|-------------|
| `equity.csv` | Equity curve over time |
| `returns.csv` | Daily portfolio returns |
| `allocations.csv` | Portfolio weights at each rebalance |
| `trades.csv` | Trade blotter (all transactions) |
| `rebalances.csv` | Rebalance events log |
| `metrics.json` | Performance metrics (Sharpe, drawdown, turnover) |
| `index.html` | HTML dashboard (if --visualize) |
| `equity_curve.png` | Equity curve chart (if --visualize) |
| `drawdown.png` | Drawdown chart (if --visualize) |
| `returns_dist.png` | Returns distribution (if --visualize) |
| `performance_metrics.png` | Metrics table (if --visualize) |

### Performance Metrics

The `metrics.json` file includes:

- **Total Return**: Cumulative return over backtest period
- **Annualized Return**: Geometric mean return
- **Volatility**: Annualized standard deviation
- **Sharpe Ratio**: Risk-adjusted return
- **Sortino Ratio**: Downside risk-adjusted return
- **Maximum Drawdown**: Largest peak-to-trough decline
- **Calmar Ratio**: Return / max drawdown
- **Turnover**: Average turnover per rebalance
- **Win Rate**: Percentage of positive return days
- **Transaction Costs**: Total costs paid

### Performance Notes

- **Statistics caching**: 50-80% speedup for 300+ assets with monthly rebalancing
- **Preselection**: Reduces optimization time proportional to universe size reduction
- **Membership policy**: Slight overhead (\<5%) for turnover tracking

### See Also

- [Backtesting Guide](backtesting.md)
- [Preselection Guide](preselection.md)
- [Membership Policy Guide](membership_policy_guide.md)
- [Statistics Caching Guide](statistics_caching.md)
- [Performance Optimization](backtest_optimization.md)

______________________________________________________________________

## Common Workflows

### Workflow 1: Complete Pipeline (Manual)

```bash
# 1. Prepare data
python scripts/prepare_tradeable_data.py \
    --data-dir data/stooq \
    --incremental

# 2. Select assets
python scripts/select_assets.py \
    --match-report data/metadata/tradeable_matches.csv \
    --output data/selected/my_universe.csv \
    --markets "NYSE,NSQ" \
    --min-history-days 756

# 3. Classify assets
python scripts/classify_assets.py \
    --input data/selected/my_universe.csv \
    --output data/classified/my_universe.csv

# 4. Calculate returns
python scripts/calculate_returns.py \
    --assets data/classified/my_universe.csv \
    --prices-dir data/processed/tradeable_prices \
    --output data/processed/returns/my_universe.csv

# 5. Construct portfolio
python scripts/construct_portfolio.py \
    --returns data/processed/returns/my_universe.csv \
    --strategy risk_parity \
    --output outputs/portfolios/risk_parity.csv

# 6. Run backtest
python scripts/run_backtest.py risk_parity \
    --returns-file data/processed/returns/my_universe.csv \
    --output-dir outputs/backtest \
    --visualize
```

### Workflow 2: Universe-Driven (Recommended)

```bash
# 1. Prepare data
python scripts/prepare_tradeable_data.py --incremental

# 2. Define universe in config/universes.yaml

# 3. Load universe (auto-executes steps 2-4)
python scripts/manage_universes.py \
    --config config/universes.yaml \
    --universe my_universe \
    load

# 4. Run backtest
python scripts/run_backtest.py risk_parity \
    --universe-file config/universes.yaml \
    --universe-name my_universe \
    --output-dir outputs/backtest \
    --visualize
```

### Workflow 3: Daily Production Update

```bash
# Daily update script
#!/bin/bash

# Update data (incremental - fast)
python scripts/prepare_tradeable_data.py \
    --incremental \
    --overwrite-prices

# Recalculate returns
python scripts/calculate_returns.py \
    --assets data/classified/production_universe.csv \
    --prices-dir data/processed/tradeable_prices \
    --output data/processed/returns/production_universe.csv \
    --fast-io polars

# Run backtest with latest data
python scripts/run_backtest.py risk_parity \
    --returns-file data/processed/returns/production_universe.csv \
    --output-dir outputs/production/$(date +%Y%m%d) \
    --visualize
```

______________________________________________________________________

## Troubleshooting

### Common Issues

#### "No such file or directory"

- **Cause**: Missing input files
- **Solution**: Check file paths, run prerequisite scripts

#### "Insufficient data for calculations"

- **Cause**: Not enough price history
- **Solution**: Reduce `--min-history-days` or add more assets

#### "Optimization failed to converge"

- **Cause**: Unstable covariance matrix or infeasible constraints
- **Solution**:
  - Increase `--lookback-periods`
  - Relax position constraints
  - Try different strategy

#### "Memory error" or "Out of memory"

- **Cause**: Dataset too large for available RAM
- **Solution**:
  - Use `--fast-io polars` (more memory efficient)
  - Reduce universe size
  - Increase system RAM

#### "Import error: module not found"

- **Cause**: Missing dependencies
- **Solution**: `pip install -r requirements.txt`

### Performance Tips

1. **Use incremental resume**: `--incremental` flag saves minutes
1. **Enable fast I/O**: `--fast-io polars` for large datasets
1. **Cache statistics**: `--enable-caching` for monthly rebalancing
1. **Parallel processing**: Adjust `--max-workers` for CPU utilization
1. **Reduce lookback**: Shorter `--lookback-periods` = faster optimization

### Getting Help

```bash
# Get help for any script
python scripts/SCRIPT_NAME.py --help

# Example
python scripts/run_backtest.py --help
```

### See Also

- [Troubleshooting Guide](troubleshooting.md)
- [Best Practices](best_practices.md)
- [Performance Optimization](backtest_optimization.md)

______________________________________________________________________

## Appendix: Argument Quick Reference

### prepare_tradeable_data.py

```
--data-dir, --tradeable-dir, --metadata-output, --match-report,
--unmatched-report, --prices-output, --incremental, --force-reindex,
--overwrite-prices, --include-empty-prices, --lse-currency-policy,
--max-workers, --index-workers, --cache-metadata, --log-level
```

### select_assets.py

```
--match-report*, --output, --data-status, --min-history-days,
--min-price-rows, --markets, --regions, --currencies,
--allowlist, --blocklist, --verbose, --dry-run
```

### classify_assets.py

```
--input*, --output, --overrides, --export-for-review,
--summary, --verbose
```

### calculate_returns.py

```
--assets*, --prices-dir*, --output, --method, --frequency,
--risk-free-rate, --handle-missing, --max-forward-fill,
--min-periods, --align-method, --business-days, --min-coverage,
--fast-io, --summary, --top, --verbose
```

### manage_universes.py

```
--config*, ACTION*, --universe, --universes, --output,
--format, --verbose
```

### construct_portfolio.py

```
--returns*, --strategy*, --output, --format, --max-weight,
--min-weight, --risk-tolerance, --target-return, --risk-aversion,
--compare, --summary, --verbose
```

### run_backtest.py

```
STRATEGY*, --start-date, --end-date, --initial-capital,
--commission, --slippage, --min-commission, --rebalance-frequency,
--drift-threshold, --lookback-periods, --universe-file,
--universe-name, --prices-file, --returns-file,
--max-position-size, --min-position-size, --target-return,
--risk-aversion, --preselect-method, --preselect-top-k,
--preselect-lookback, --preselect-skip-recent,
--membership-policy, --max-turnover, --min-hold-periods,
--buffer-rank, --output-dir, --format, --visualize,
--plot-format, --enable-caching, --cache-dir, --verbose, --debug
```

**Note**: * = Required argument

______________________________________________________________________

**Last Updated**: October 25, 2025
**Version**: 1.0.0
**For**: Portfolio Management Toolkit
