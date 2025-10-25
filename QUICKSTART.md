# Quick Start Guide

**Portfolio Management Toolkit - 15-Minute Setup**

This guide will help you build and backtest your first portfolio in under 15 minutes using pre-configured sample data.

______________________________________________________________________

## Prerequisites

- Python 3.10 or higher
- pip package manager
- ~500 MB disk space for sample data

______________________________________________________________________

## Installation (5 minutes)

### 1. Clone the Repository

```bash
git clone https://github.com/jc1122/portfolio_management.git
cd portfolio_management
```

### 2. Install Dependencies

```bash
# Install core dependencies
pip install -r requirements.txt

# Optional: Install fast IO backends for 2-5x speedup
pip install polars pyarrow
```

### 3. Verify Installation

```bash
# Run a quick smoke test
pytest tests/ -m "not slow" -x
```

Expected: **600+ tests pass** (1 may xfail due to CVXPY solver instability)

______________________________________________________________________

## Quick Demo (10 minutes)

### Scenario: Build an Equal-Weight Portfolio

We'll use the **pre-configured `core_global` universe** (35 GBP-denominated ETFs) to:

1. Generate a return matrix
1. Construct an equal-weight portfolio
1. Backtest it from 2020-2023

### Step 1: Prepare Sample Data

**Option A: Use Existing Data (if available)**

If you already have Stooq data unpacked in `data/stooq/`, run:

```bash
python scripts/prepare_tradeable_data.py \
    --data-dir data/stooq \
    --tradeable-dir tradeable_instruments \
    --metadata-output data/metadata/stooq_index.csv \
    --match-report data/metadata/tradeable_matches.csv \
    --prices-output data/processed/tradeable_prices \
    --incremental
```

**First run:** ~3-5 minutes (indexes 70k+ files)
**Subsequent runs:** \<5 seconds with `--incremental`

**Option B: Use Pre-Processed Test Data (fastest)**

If test data exists in `outputs/long_history_1000/`, skip to Step 2.

### Step 2: Generate Universe Returns

```bash
python scripts/manage_universes.py load core_global \
    --output-dir outputs/quickstart
```

This single command:

- Selects assets (quality filters, market codes)
- Classifies assets (equity, bond, commodity)
- Calculates monthly returns
- Validates configuration

**Output:** `outputs/quickstart/core_global_returns.csv`

### Step 3: Construct Portfolio

```bash
python scripts/construct_portfolio.py \
    --returns outputs/quickstart/core_global_returns.csv \
    --strategy equal_weight \
    --max-weight 0.25 \
    --output outputs/quickstart/portfolio_weights.csv
```

**Output:** CSV with ticker-weight pairs (~35 assets, ~2.86% each)

### Step 4: Run Backtest

```bash
python scripts/run_backtest.py equal_weight \
    --start-date 2020-01-01 \
    --end-date 2023-12-31 \
    --returns outputs/quickstart/core_global_returns.csv \
    --output-dir outputs/quickstart/backtest \
    --rebalance-frequency quarterly \
    --visualize
```

**Outputs:**

- `equity_curve.csv` - Portfolio value over time
- `daily_returns.csv` - Daily return series
- `allocation_history.csv` - Weights over time
- `rebalance_log.csv` - Rebalance dates and changes
- `trade_log.csv` - Individual trades with costs
- `performance_metrics.json` - Summary statistics

### Step 5: Review Results

```bash
# View performance summary
cat outputs/quickstart/backtest/equal_weight/performance_metrics.json

# Key metrics (expected ranges):
# - Total Return: 15-30% (2020-2023 period)
# - Sharpe Ratio: 0.8-1.5
# - Max Drawdown: 15-25% (includes 2020 COVID crash)
# - Annual Volatility: 10-15%
```

______________________________________________________________________

## What Just Happened?

1. **Universe Management** (`manage_universes.py`)

   - Read configuration from `config/universes.yaml`
   - Selected 35 high-quality GBP ETFs from LSE
   - Classified assets (equity, commodity, REIT)
   - Calculated monthly returns (2015-2024)

1. **Portfolio Construction** (`construct_portfolio.py`)

   - Applied equal-weight strategy (1/N allocation)
   - Enforced constraints (max 25% per asset)
   - Generated initial weights

1. **Backtesting** (`run_backtest.py`)

   - Simulated quarterly rebalancing (2020-2023)
   - Applied transaction costs (0.1% commission, 0.05% slippage)
   - Tracked equity curve and drawdowns
   - Calculated performance metrics

______________________________________________________________________

## Next Steps

### Explore Different Strategies

```bash
# Risk Parity (equal risk contribution)
python scripts/construct_portfolio.py \
    --returns outputs/quickstart/core_global_returns.csv \
    --strategy risk_parity \
    --output outputs/quickstart/portfolio_riskparity.csv

# Mean-Variance (maximize Sharpe ratio)
python scripts/construct_portfolio.py \
    --returns outputs/quickstart/core_global_returns.csv \
    --strategy mean_variance_max_sharpe \
    --max-equity 0.85 \
    --min-bond 0.15 \
    --output outputs/quickstart/portfolio_mv.csv

# Compare all strategies
python scripts/construct_portfolio.py \
    --returns outputs/quickstart/core_global_returns.csv \
    --compare \
    --output outputs/quickstart/comparison.csv
```

### Add Factor-Based Preselection

```bash
# Select top 20 assets by momentum before optimization
python scripts/run_backtest.py risk_parity \
    --returns outputs/quickstart/core_global_returns.csv \
    --start-date 2020-01-01 \
    --end-date 2023-12-31 \
    --preselection-method momentum \
    --preselection-top-k 20 \
    --output-dir outputs/quickstart/momentum
```

### Control Portfolio Turnover

```bash
# Add membership policy to reduce churn
python scripts/run_backtest.py equal_weight \
    --returns outputs/quickstart/core_global_returns.csv \
    --start-date 2020-01-01 \
    --end-date 2023-12-31 \
    --membership-enabled \
    --membership-buffer-rank 5 \
    --membership-min-hold 3 \
    --membership-max-turnover 0.25 \
    --output-dir outputs/quickstart/stable
```

### Explore Other Universes

```bash
# List available universes
python scripts/manage_universes.py list

# Load different universes
python scripts/manage_universes.py load satellite_factor --output-dir outputs/satellite
python scripts/manage_universes.py load defensive --output-dir outputs/defensive

# Compare universes
python scripts/manage_universes.py compare core_global satellite_factor defensive
```

______________________________________________________________________

## Advanced Usage

### Custom Universe Configuration

Edit `config/universes.yaml` to define your own universe:

```yaml
universes:
  my_custom_universe:
    description: "Custom high-dividend portfolio"
    filter_criteria:
      data_status: ["ok"]
      min_history_days: 756
      markets: ["LSE", "NYSE"]
      currencies: ["GBP", "USD"]
    classification_requirements:
      asset_class: ["equity"]
      sub_class: ["dividend"]
    return_config:
      method: "simple"
      frequency: "monthly"
      min_coverage: 0.80
    constraints:
      min_assets: 20
      max_assets: 40
```

Then load it:

```bash
python scripts/manage_universes.py load my_custom_universe
```

### Manual Workflow (Advanced)

For full control, run each stage individually:

```bash
# Stage 1: Data Preparation
python scripts/prepare_tradeable_data.py [options]

# Stage 2: Asset Selection
python scripts/select_assets.py \
    --match-report data/metadata/tradeable_matches.csv \
    --output data/selected/custom.csv \
    --min-history-days 756

# Stage 3: Asset Classification
python scripts/classify_assets.py \
    --input data/selected/custom.csv \
    --output data/classified/custom.csv

# Stage 4: Return Calculation
python scripts/calculate_returns.py \
    --assets data/classified/custom.csv \
    --prices-dir data/processed/tradeable_prices \
    --output data/returns/custom.csv \
    --frequency monthly

# Stage 5: Portfolio Construction
python scripts/construct_portfolio.py [options]

# Stage 6: Backtesting
python scripts/run_backtest.py [options]
```

See `docs/workflow.md` for detailed documentation.

______________________________________________________________________

## Performance Optimization

### Fast IO for Large Datasets

For 500+ assets or 5+ years of daily data, use fast IO backends:

```bash
# Install optional backends
pip install polars pyarrow

# Use in return calculation
python scripts/calculate_returns.py \
    --assets data/classified/large_universe.csv \
    --prices-dir data/processed/tradeable_prices \
    --output data/returns/large_universe.csv \
    --io-backend polars  # 2-5x faster than pandas
```

### Caching for Repeated Backtests

Statistics caching automatically speeds up repeated backtests with overlapping windows:

```bash
# First run: calculates covariance matrices
python scripts/run_backtest.py risk_parity [options]

# Subsequent runs: uses cached statistics (much faster)
python scripts/run_backtest.py risk_parity [options]
```

Cache is stored in `.cache/` and automatically invalidated when data changes.

______________________________________________________________________

## Troubleshooting

### "No module named 'pandas'"

**Solution:** Install dependencies:

```bash
pip install -r requirements.txt
```

### "No matching price file for ticker XYZ"

**Solution:** Ensure data preparation completed:

```bash
python scripts/prepare_tradeable_data.py --incremental
```

### "Insufficient history for asset ABC"

**Solution:** Lower history requirements:

```bash
python scripts/select_assets.py --min-history-days 252  # 1 year instead of 3
```

### "CVXPY solver failed"

**Solution:** This is expected for some mean-variance problems. Use equal-weight or risk-parity instead:

```bash
python scripts/construct_portfolio.py --strategy equal_weight
```

### Performance Issues with Large Datasets

**Solution:** Enable fast IO and caching:

```bash
pip install polars
python scripts/calculate_returns.py --io-backend polars
```

______________________________________________________________________

## Documentation

**Core Guides:**

- `README.md` - Project overview and architecture
- `docs/workflow.md` - Detailed workflow documentation
- `docs/universes.md` - Universe configuration guide
- `docs/portfolio_construction.md` - Strategy documentation
- `docs/backtesting.md` - Backtest configuration reference

**Feature Guides:**

- `docs/preselection.md` - Factor-based asset selection
- `docs/membership_policy.md` - Turnover control
- `docs/statistics_caching.md` - Performance optimization
- `docs/fast_io.md` - Fast IO backends

**API Reference:**

- `docs/architecture/` - System architecture diagrams
- `docs/error_reference.md` - Error codes and solutions
- `docs/troubleshooting.md` - Common issues

______________________________________________________________________

## Getting Help

1. **Check Documentation:** Browse `docs/` for comprehensive guides
1. **Review Examples:** See `examples/` for complete working scripts
1. **Run Tests:** `pytest tests/ -v` to verify installation
1. **Open Issue:** Report bugs on GitHub

______________________________________________________________________

## What's Next?

**For Production Use:**

1. Execute Sprint 3 testing (long-duration backtests, edge cases)
1. Set up CI/CD pipeline for automated testing
1. Configure monitoring for cache hit rates and data quality

**For Development:**

1. Add custom strategies (extend `PortfolioStrategy` ABC)
1. Implement regime-gating logic (NoOp stubs ready)
1. Integrate news/sentiment factors (future roadmap)

See `CODEBASE_CLEANUP_ANALYSIS.md` for detailed next steps.

______________________________________________________________________

**Need more help?** See `docs/workflow.md` for the complete manual workflow or `examples/` for advanced usage patterns.
