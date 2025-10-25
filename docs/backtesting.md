# Backtesting Guide: `run_backtest.py`

## Overview

This script is the sixth and final step in the portfolio management toolkit's workflow. It is the ultimate test of an investment strategy, designed to provide a realistic simulation of how a portfolio would have performed over a specified historical period.

The script orchestrates the `BacktestEngine`, which processes historical data, executes a rebalancing strategy, models transaction costs, and generates a rich set of performance analytics with integrated preselection, membership policy, and point-in-time eligibility controls.

## Inputs (Prerequisites)

The backtest requires several key inputs to run a simulation:

1. **Strategy Name (Required)**: The portfolio construction strategy (e.g., `equal_weight`, `risk_parity`, `mean_variance`) that the backtest will use to determine target weights at each rebalancing point.

1. **Universe & Data Files**: The script needs to know which assets to trade and where to find their data.

   - `--universe-file`: A YAML file defining asset universes (default: `config/universes.yaml`)
   - `--prices-file`: The CSV file containing historical price data, needed for executing trades (default: `data/processed/prices.csv`)
   - `--returns-file`: The CSV file containing the historical returns matrix, used by the strategy logic (default: `data/processed/returns.csv`)

## The Backtesting Process

The backtesting engine simulates the life of a portfolio step-by-step with optional advanced features:

1. **Initialization**: The portfolio is created on the `--start-date` with the specified `--initial-capital`.

1. **Time Progression**: The engine advances day by day, updating the portfolio's market value based on the returns of the assets it holds.

1. **Rebalance Check**: At each time step, the engine checks if a rebalance is necessary. This is determined by the `--rebalance-frequency` (e.g., has a month passed?) or other triggers.

1. **Point-in-Time (PIT) Eligibility** *(Optional)*: When `--use-pit-eligibility` is enabled, filters out assets that lack sufficient history at the rebalance date to prevent lookahead bias. See [PIT Eligibility](#point-in-time-pit-eligibility) section below.

1. **Preselection** *(Optional)*: When `--preselect-method` is specified, applies factor-based ranking (momentum, low-volatility, or combined) to reduce the universe to the top-K assets before optimization. See [Preselection Integration](#preselection-integration) section below.

1. **Strategy Execution**: The chosen portfolio construction **strategy** is executed using the historical data available up to that point to calculate the new target asset weights on the (optionally filtered) universe.

1. **Membership Policy** *(Optional)*: When `--membership-enabled` is set, applies rules to prevent excessive portfolio churn by protecting existing holdings and limiting turnover. See [Membership Policy Integration](#membership-policy-integration) section below.

1. **Order Generation & Execution**: The engine compares the new target weights to the current portfolio weights and generates the necessary buy and sell trades to align them. It simulates these trades using the historical price data and applies the transaction cost model (`--commission`, `--slippage`).

1. **Loop**: The process repeats until the simulation reaches the `--end-date`.

## Script Products

The script generates a comprehensive set of files in the specified `--output-dir`, allowing for a deep analysis of the strategy's performance.

### 1. Performance and Configuration Reports (JSON)

These files provide machine-readable summaries of the backtest.

- **`config.json`**: Saves the exact configuration of the backtest (dates, capital, costs, etc.) to ensure results are reproducible.
- **`metrics.json` / `summary_report.json`**: Contain the final quantitative performance metrics, such as **Annualized Return**, **Annualized Volatility**, **Sharpe Ratio**, and **Max Drawdown**.

### 2. Core Data Files (CSV)

These files provide the raw data from the simulation.

- **`equity_curve.csv`**: The most important file for visualization. It contains a `date` and `equity` column, tracking the portfolio's value over time.
- **`trades.csv`**: If `--save-trades` is enabled, this provides a detailed log of every simulated transaction, including the asset, shares, price, and costs.

### 3. Visualization-Ready Data (CSV)

If not disabled with `--no-visualize`, these files are generated for easy charting.

- **`viz_drawdown.csv`**: Tracks the percentage loss of the portfolio from its previous all-time high. Essential for understanding risk.
- **`viz_rolling_metrics.csv`**: Shows how key metrics like volatility and Sharpe ratio evolved over rolling time windows during the backtest.
- **`viz_transaction_costs.csv`**: Summarizes the commissions and slippage costs incurred over time.
- **`viz_equity_curve.csv`**: Normalised equity series suitable for plotting without additional data munging.

## Features in Detail

- **Strategy Selection**: Allows you to backtest any of the registered portfolio construction strategies (`equal_weight`, `risk_parity`, `mean_variance`).
- **Custom Date Range**: You can define the exact historical period for the simulation with `--start-date` and `--end-date`.
- **Transaction Cost Modeling**: Realistically models trading frictions by allowing you to specify a `--commission` rate, a `--slippage` rate, and a `--min-commission` per trade.
- **Flexible Rebalancing**: You can control *when* the portfolio is rebalanced using `--rebalance-frequency` (e.g., `monthly`, `quarterly`) and *how* it's triggered (e.g., on a fixed schedule or when the portfolio drifts too far from its targets).
- **Advanced Controls**: Optional features including preselection (factor-based universe reduction), membership policy (turnover control), point-in-time eligibility (lookahead bias prevention), and statistics caching (performance optimization).

### Preselection Integration

**Purpose**: Reduce computational cost and add factor tilt by filtering the investment universe before optimization.

The preselection feature applies deterministic, factor-based ranking to select top-K assets before portfolio construction:

- **Momentum**: Selects assets with highest cumulative returns over lookback period
- **Low-Volatility**: Selects assets with lowest realized volatility  
- **Combined**: Weighted combination of momentum and low-volatility Z-scores

**CLI Usage**:
```bash
# Use momentum preselection to select top 30 assets
python scripts/run_backtest.py risk_parity \
    --preselect-method momentum \
    --preselect-top-k 30 \
    --preselect-lookback 252

# Use combined factors with custom weights
python scripts/run_backtest.py equal_weight \
    --preselect-method combined \
    --preselect-top-k 50 \
    --preselect-momentum-weight 0.6 \
    --preselect-low-vol-weight 0.4
```

**Key Parameters**:
- `--preselect-method`: Factor method (`momentum`, `low_vol`, `combined`)
- `--preselect-top-k`: Number of assets to select (required when using preselection)
- `--preselect-lookback`: Lookback period in days (default: 252 = 1 year)
- `--preselect-skip`: Skip N most recent days (default: 1, avoids short-term noise)
- `--preselect-momentum-weight`: Momentum weight in combined method (default: 0.5)
- `--preselect-low-vol-weight`: Low-vol weight in combined method (default: 0.5)

**Impact**: Preselection is applied transparently before each rebalance. The portfolio strategy only sees the filtered universe, dramatically reducing optimization time for large universes (e.g., 500 assets → 50 assets = 1000× speedup for mean-variance).

See `docs/preselection.md` for detailed documentation.

### Membership Policy Integration

**Purpose**: Control portfolio turnover and reduce transaction costs by stabilizing holdings.

The membership policy prevents excessive churn by applying deterministic rules during rebalancing:

- **Buffer Rank**: Protects existing holdings by giving them a ranking advantage
- **Min Holding Periods**: Requires assets to be held for minimum number of rebalances
- **Max Turnover**: Limits total portfolio changes per rebalance
- **Entry/Exit Limits**: Controls number of new additions and removals

**CLI Usage**:
```bash
# Enable basic membership policy with defaults
python scripts/run_backtest.py risk_parity \
    --membership-enabled

# Custom policy with strict turnover control
python scripts/run_backtest.py equal_weight \
    --membership-enabled \
    --membership-buffer-rank 10 \
    --membership-min-hold 5 \
    --membership-max-turnover 0.25 \
    --membership-max-new 3 \
    --membership-max-removed 2
```

**Key Parameters**:
- `--membership-enabled`: Enable membership policy (default: disabled)
- `--membership-buffer-rank`: Rank buffer for holdings (default: 5)
- `--membership-min-hold`: Minimum rebalance periods to hold (default: 3)
- `--membership-max-turnover`: Maximum turnover per rebalance (0-1, e.g., 0.3 = 30%)
- `--membership-max-new`: Maximum new assets per rebalance
- `--membership-max-removed`: Maximum removals per rebalance

**Impact**: Membership policy is applied after preselection (if enabled) and before final weight optimization. It filters the candidate asset list to maintain portfolio stability.

See `docs/membership_policy.md` for detailed documentation.

### Point-in-Time (PIT) Eligibility

**Purpose**: Prevent lookahead bias by ensuring assets meet data quality requirements at each rebalance date.

PIT eligibility filters out assets that lack sufficient history or have been delisted:

- **Minimum History**: Requires specified days of price data before rebalance date
- **Delisting Detection**: Automatically removes assets with no future data
- **Data Quality**: Validates minimum number of price observations

**CLI Usage**:
```bash
# Enable PIT filtering with 1-year minimum history
python scripts/run_backtest.py mean_variance \
    --use-pit-eligibility \
    --min-history-days 252 \
    --min-price-rows 252
```

**Key Parameters**:
- `--use-pit-eligibility`: Enable PIT filtering (default: disabled)
- `--min-history-days`: Minimum days of history required (default: 252 = 1 year)
- `--min-price-rows`: Minimum price observations required (default: 252)

**Impact**: PIT eligibility is applied first in the rebalancing pipeline, before preselection or optimization. It ensures only assets with sufficient historical data are considered for investment.

See `docs/pit_eligibility_edge_cases.md` for edge case documentation.

### Statistics Caching

**Purpose**: Optimize performance by caching expensive covariance and return calculations across overlapping windows.

Statistics caching stores intermediate calculations during rebalancing with rolling windows:

- **Covariance Matrices**: Cached across rebalance periods with high data overlap
- **Expected Returns**: Cached mean return calculations
- **Automatic Invalidation**: Cache refreshed when data changes

**CLI Usage**:
```bash
# Enable caching with default settings
python scripts/run_backtest.py risk_parity \
    --enable-cache

# Custom cache directory and age limit
python scripts/run_backtest.py mean_variance \
    --enable-cache \
    --cache-dir .my_cache \
    --cache-max-age-days 7 \
    --verbose  # Shows cache hit/miss stats
```

**Key Parameters**:
- `--enable-cache`: Enable on-disk caching (default: disabled)
- `--cache-dir`: Cache storage directory (default: `.cache/backtest`)
- `--cache-max-age-days`: Maximum cache age in days (optional, no limit if not set)
- `--verbose`: Print cache statistics (hits, misses, puts)

**Performance Impact**: 
- Monthly rebalancing with 1-year window: ~92% data overlap → significant speedup
- Large universes (300+ assets): O(n²) covariance computation savings
- Typical cache hit rate: 70-90% after first rebalance

**Memory**: Cache stores full returns DataFrame + covariance matrix. For 300 assets × 252 days ≈ 1.5 MB per cache instance.

See `docs/statistics_caching.md` for detailed documentation.

### Hardened Output Exports

The CLI now guards against silent blank charts by coercing every equity curve into a sorted `DataFrame`, validating that the data is non-empty, and emitting normalised chart-ready CSVs (`viz_equity_curve.csv`, `viz_drawdown.csv`, `viz_rolling_metrics.csv`). These enhancements were exercised during the 1,000-asset (`long_history_1000`) regression runs, ensuring downstream notebooks receive consistent inputs even when risk parity optimisation falls back to a defensive solution.

## Usage Examples

### Basic Backtest

```bash
# Simple equal-weight backtest with default settings
python scripts/run_backtest.py equal_weight
```

### With Advanced Features

```bash
# Risk parity with all advanced features enabled
python scripts/run_backtest.py risk_parity \
    --start-date 2020-01-01 \
    --end-date 2023-12-31 \
    --commission 0.001 \
    --slippage 0.0005 \
    --preselect-method combined \
    --preselect-top-k 30 \
    --membership-enabled \
    --use-pit-eligibility \
    --enable-cache \
    --output-dir results/backtest_full_features
```

### Production Configuration

```bash
# Mean-variance with production-grade settings
python scripts/run_backtest.py mean_variance \
    --start-date 2015-01-01 \
    --end-date 2024-12-31 \
    --rebalance-frequency monthly \
    --lookback-periods 252 \
    --preselect-method momentum \
    --preselect-top-k 50 \
    --preselect-lookback 252 \
    --membership-enabled \
    --membership-buffer-rank 10 \
    --membership-min-hold 3 \
    --membership-max-turnover 0.30 \
    --use-pit-eligibility \
    --min-history-days 252 \
    --enable-cache \
    --cache-dir .cache/production \
    --save-trades \
    --verbose \
    --output-dir results/production_backtest
```

## Performance Optimization

### For Large Universes (300+ Assets)

When backtesting large universes, combine these optimizations:

1. **Enable Preselection**: Reduce universe size before optimization
   ```bash
   --preselect-method combined --preselect-top-k 50
   ```
   Impact: Reduces mean-variance from O(n³) to O(k³) where k << n

2. **Enable Caching**: Avoid redundant covariance calculations
   ```bash
   --enable-cache --cache-dir .cache/backtest
   ```
   Impact: 70-90% speedup on monthly rebalancing with 1-year windows

3. **Use PIT Eligibility**: Filter out ineligible assets early
   ```bash
   --use-pit-eligibility --min-history-days 252
   ```
   Impact: Reduces computation on assets with insufficient data

4. **Monthly Rebalancing**: Reduce number of optimizations
   ```bash
   --rebalance-frequency monthly
   ```
   Impact: ~12 optimizations/year vs. 252 for daily

**Combined Example**:
```bash
python scripts/run_backtest.py mean_variance \
    --preselect-method combined \
    --preselect-top-k 50 \
    --enable-cache \
    --use-pit-eligibility \
    --rebalance-frequency monthly \
    --verbose
```

### Memory Management

For very large backtests (1000+ assets, 10+ years):

- Use `--cache-max-age-days` to limit cache growth
- Enable `--verbose` to monitor cache statistics
- Consider running backtest in chunks (shorter date ranges)

### Computational Complexity

| Feature | Complexity | Notes |
|---------|-----------|-------|
| Equal Weight | O(n) | Minimal computation |
| Risk Parity | O(n²) | Covariance computation |
| Mean-Variance | O(n³) | Quadratic programming |
| Preselection | O(n × L) | L = lookback periods |
| PIT Eligibility | O(n) | Simple filtering |
| Caching | O(1) on hit | O(n²) on miss |

Where n = number of assets, L = lookback window

### Recommended Configurations

**Small Universe (<50 assets)**:
- Caching: Optional (overhead may dominate)
- Preselection: Not needed
- Strategy: Any (all are fast)

**Medium Universe (50-200 assets)**:
- Caching: Recommended
- Preselection: Optional for mean-variance
- Strategy: Equal-weight or risk-parity preferred

**Large Universe (200-1000+ assets)**:
- Caching: Required
- Preselection: Required (top-K = 30-50)
- Strategy: Equal-weight or risk-parity only (mean-variance too slow)
- PIT Eligibility: Recommended

## Command-Line Arguments

### Required

- `strategy`: The portfolio strategy to use
  - Choices: `equal_weight`, `risk_parity`, `mean_variance`

### Date Range & Capital

- `--start-date`: Backtest start date (YYYY-MM-DD). Default: 2020-01-01
- `--end-date`: Backtest end date (YYYY-MM-DD). Default: today
- `--initial-capital`: Starting capital for the portfolio. Default: 100000

### Transaction Costs

- `--commission`: Commission rate (e.g., 0.001 = 0.1%). Default: 0.001
- `--slippage`: Slippage rate (e.g., 0.0005 = 0.05%). Default: 0.0005
- `--min-commission`: Minimum commission per trade. Default: 1.0

### Rebalancing

- `--rebalance-frequency`: Rebalancing frequency. Default: monthly
  - Choices: `daily`, `weekly`, `monthly`, `quarterly`, `annual`
- `--drift-threshold`: Drift threshold for opportunistic rebalancing (0-1). Default: 0.05
- `--lookback-periods`: Rolling lookback window for parameter estimation (days). Default: 252

### Data Sources

- `--universe-file`: Path to universe configuration YAML. Default: config/universes.yaml
- `--universe-name`: Universe name in configuration file. Default: default
- `--prices-file`: Path to prices CSV. Default: data/processed/prices.csv
- `--returns-file`: Path to returns CSV. Default: data/processed/returns.csv

### Strategy Parameters

- `--max-position-size`: Maximum position size (0-1). Default: 0.25
- `--min-position-size`: Minimum position size (0-1). Default: 0.01
- `--target-return`: Target return for mean-variance (annualized, optional)
- `--risk-aversion`: Risk aversion parameter (higher = more conservative). Default: 1.0

### Preselection (Optional)

- `--preselect-method`: Preselection method
  - Choices: `momentum`, `low_vol`, `combined`
- `--preselect-top-k`: Number of assets to select (required when using preselection)
- `--preselect-lookback`: Lookback period in days. Default: 252
- `--preselect-skip`: Skip N most recent days. Default: 1
- `--preselect-momentum-weight`: Momentum weight in combined method (0-1). Default: 0.5
- `--preselect-low-vol-weight`: Low-vol weight in combined method (0-1). Default: 0.5

### Membership Policy (Optional)

- `--membership-enabled`: Enable membership policy (flag)
- `--membership-buffer-rank`: Rank buffer for existing holdings. Default: 5
- `--membership-min-hold`: Minimum rebalance periods to hold. Default: 3
- `--membership-max-turnover`: Maximum portfolio turnover per rebalance (0-1)
- `--membership-max-new`: Maximum new assets per rebalancing
- `--membership-max-removed`: Maximum removals per rebalancing

### Point-in-Time Eligibility (Optional)

- `--use-pit-eligibility`: Enable PIT eligibility filtering (flag)
- `--min-history-days`: Minimum days of history required. Default: 252
- `--min-price-rows`: Minimum price observations required. Default: 252

### Caching (Optional)

- `--enable-cache`: Enable on-disk caching (flag)
- `--cache-dir`: Directory for cache storage. Default: .cache/backtest
- `--cache-max-age-days`: Maximum cache age in days (optional)

### Output Options

- `--output-dir`: Output directory for results. Default: results/backtest_TIMESTAMP
- `--no-visualize`: Skip generating visualization data files (flag)
- `--save-trades`: Save detailed trade history to CSV (flag)
- `--verbose`: Print detailed progress information (flag)

### Validation Options

- `--strict`: Treat configuration warnings as errors (flag)
- `--ignore-warnings`: Suppress configuration warnings (flag)
- `--show-defaults`: Display sensible default values and exit (flag)

## See Also

- [Portfolio Construction](portfolio_construction.md) - Strategy details
- [Preselection](preselection.md) - Factor-based universe reduction
- [Membership Policy](membership_policy.md) - Turnover control
- [Statistics Caching](statistics_caching.md) - Performance optimization
- [Universes](universes.md) - Universe configuration with YAML
