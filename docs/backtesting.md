# Backtesting Script: `run_backtest.py`

## Overview

This script is the sixth and final step in the portfolio management toolkit's workflow. It is the ultimate test of an investment strategy, designed to provide a realistic simulation of how a portfolio would have performed over a specified historical period.

The script orchestrates the `BacktestEngine`, which processes historical data, executes a rebalancing strategy, models transaction costs, and generates a rich set of performance analytics.

## Inputs (Prerequisites)

The backtest requires several key inputs to run a simulation:

1. **Strategy Name (Required)**: The portfolio construction strategy (e.g., `equal_weight`, `risk_parity`) that the backtest will use to determine target weights at each rebalancing point.

1. **Universe & Data Files**: The script needs to know which assets to trade and where to find their data.

   - `--universe-file`: A YAML file defining asset universes.
   - `--prices-file`: The CSV file containing historical price data, needed for executing trades.
   - `--returns-file`: The CSV file containing the historical returns matrix, used by the strategy logic.

## The Backtesting Process

The backtesting engine simulates the life of a portfolio step-by-step:

1. **Initialization**: The portfolio is created on the `--start-date` with the specified `--initial-capital`.
1. **Time Progression**: The engine advances day by day, updating the portfolio's market value based on the returns of the assets it holds.
1. **Rebalance Check**: At each time step, the engine checks if a rebalance is necessary. This is determined by the `--rebalance-frequency` (e.g., has a month passed?) or other triggers.
1. **Strategy Execution**: When a rebalance is triggered, the chosen portfolio construction **strategy** is executed using the historical data available up to that point to calculate the new target asset weights.
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

- **Strategy Selection**: Allows you to backtest any of the registered portfolio construction strategies (`equal_weight`, `risk_parity`, etc.).
- **Custom Date Range**: You can define the exact historical period for the simulation with `--start-date` and `--end-date`.
- **Transaction Cost Modeling**: Realistically models trading frictions by allowing you to specify a `--commission` rate, a `--slippage` rate, and a `--min-commission` per trade.
- **Flexible Rebalancing**: You can control *when* the portfolio is rebalanced using `--rebalance-frequency` (e.g., `monthly`, `quarterly`) and *how* it's triggered (e.g., on a fixed schedule or when the portfolio drifts too far from its targets).

### Hardened Output Exports

The CLI now guards against silent blank charts by coercing every equity curve into a sorted `DataFrame`, validating that the data is non-empty, and emitting normalised chart-ready CSVs (`viz_equity_curve.csv`, `viz_drawdown.csv`, `viz_rolling_metrics.csv`). These enhancements were exercised during the 1,000-asset (`long_history_1000`) regression runs, ensuring downstream notebooks receive consistent inputs even when risk parity optimisation falls back to a defensive solution.

## Usage Example

```bash
# Backtest a risk parity strategy for the 2020-2023 period with specific costs
python scripts/run_backtest.py risk_parity \
    --start-date 2020-01-01 \
    --end-date 2023-12-31 \
    --commission 0.001 \
    --slippage 0.0005 \
    --output-dir results/backtest_risk_parity
```

## Command-Line Arguments

- `strategy`: **(Required)** The portfolio strategy to use (`equal_weight`, `risk_parity`, `mean_variance`).
- `--start-date` / `--end-date`: The simulation period.
- `--initial-capital`: The starting capital for the portfolio.
- `--commission` / `--slippage` / `--min-commission`: Parameters for the transaction cost model.
- `--rebalance-frequency`: How often to rebalance (`daily`, `weekly`, `monthly`, etc.).
- `--output-dir`: The directory where all result files will be saved.
- `--save-trades`: If specified, saves the detailed trade log.
- `--no-visualize`: If specified, skips generating the visualization-ready CSV files.
