# Example: Momentum Strategy with Turnover Control

This example demonstrates a classic quantitative strategy: selecting assets based on momentum and applying rules to control portfolio turnover. It's a powerful showcase of combining preselection, membership policies, and point-in-time (PIT) eligibility to build a robust backtest.

## Strategy Overview

The core of the strategy is as follows:

1. **Universe**: Start with a broad universe of 1,000 liquid assets.
1. **Momentum Preselection**: At each rebalancing date, calculate the 12-month momentum for all eligible assets. Select the top 30 assets with the highest momentum scores.
1. **Turnover Control**: To prevent excessive trading costs and churn, apply a membership policy. An asset currently in the portfolio will remain as long as its momentum rank does not fall below 80 (30 `top_k` + 50 `buffer_rank`). This creates a "hysteresis" effect, favoring assets that are already held.
1. **Portfolio Construction**: The 30 selected assets are then weighted equally in the portfolio.
1. **Rebalancing**: The portfolio is rebalanced on a monthly basis to reflect the new momentum rankings.

This strategy aims to capture the momentum premium while mitigating the high turnover that often plagues such strategies.

## Key Features Demonstrated

- **Preselection**: Using the `Preselection` module to filter a large universe down to a manageable number of assets based on a factor (momentum).
- **Membership Policy**: Using the `MembershipPolicy` module to control portfolio churn, reduce transaction costs, and improve stability.
- **PIT Eligibility**: Enabling `use_pit_eligibility` to ensure that assets are only included in the backtest if they have sufficient historical data at each rebalancing point, thus avoiding lookahead bias.
- **Factor Caching**: Using the `FactorCache` to store the results of expensive calculations (like momentum scores and PIT eligibility), making subsequent runs significantly faster.
- **Workflow Integration**: Showing how these components are wired together in a clean, readable script.

## How to Run This Example

The example can be run directly from the `examples/momentum_strategy.py` script. This script is self-contained and hardcodes the configuration for clarity.

```bash
python examples/momentum_strategy.py
```

### Expected Output

When you run the script, you will see output similar to the following:

```
Running Momentum Strategy with Turnover Control Example...
Loading universe 'long_history_1000' from config/universes.yaml...
Loading price and return data for 1000 assets...
Data loaded successfully.
Caching enabled at: .cache/examples
Momentum preselection configured: Top 30 assets with 12-month lookback.
Membership policy configured: buffer_rank=50, min_holding_periods=3.

Starting backtest engine...
Backtest completed.

----- Backtest Summary -----
initial_capital: 100000.0
end_capital: 350123.45
total_return: 2.5012
annualized_return: 0.1056
annualized_volatility: 0.1854
sharpe_ratio: 0.5698
max_drawdown: -0.3521
calmar_ratio: 0.3000
total_trades: 512
average_turnover: 0.1534
total_costs: 12345.67

Results saved to outputs/examples/momentum_strategy
Momentum strategy example finished successfully.
```

The script will generate two files in the `outputs/examples/momentum_strategy/` directory:

- `equity_curve.csv`: The daily equity value of the portfolio.
- `summary_report.yaml`: A detailed report of performance metrics.

You can use this data to plot the performance of the strategy and analyze its characteristics.

## Code Walkthrough (`examples/momentum_strategy.py`)

The example script is broken down into 8 clear steps:

1. **Define Paths and Configuration**: Sets up the file paths and basic parameters like the date range.
1. **Load Universe and Data**: Loads the asset list and the corresponding price/return data.
1. **Configure the Backtest**: Creates the main `BacktestConfig` object, enabling PIT eligibility.
1. **Configure Caching**: Initializes the `FactorCache` to speed up repeated runs.
1. **Configure Preselection**: This is the core of the momentum strategy. It creates a `Preselection` object to select the top 30 assets based on momentum.
1. **Configure Membership Policy**: Creates a `MembershipPolicy` object to control turnover.
1. **Create and Run the Backtest Engine**: Instantiates the `BacktestEngine` with all the components and runs the simulation.
1. **Save and Display Results**: Saves the results and prints a summary to the console.

## Configuration (`config/momentum_strategy_config.yaml`)

While the example script hardcodes the configuration, we have also provided a YAML file that demonstrates how you would configure this strategy for use with the general-purpose `run_backtest.py` script. This promotes the best practice of separating configuration from code.

Here are the key sections of `config/momentum_strategy_config.yaml`:

```yaml
universes:
  momentum_turnover_control:
    # Point-in-Time (PIT) Eligibility Configuration
    pit_eligibility:
      enabled: true
      min_history_days: 252

    # Preselection Configuration (The Momentum Factor)
    preselection:
      method: "momentum"
      top_k: 30
      lookback: 252
      skip: 21
      min_periods: 126

    # Membership Policy (Turnover Control)
    membership_policy:
      enabled: true
      buffer_rank: 50
      min_holding_periods: 3
```

To run the backtest using this configuration file, you would use the following command:

```bash
python scripts/run_backtest.py equal_weight \
  --universe-file config/momentum_strategy_config.yaml \
  --universe-name momentum_turnover_control \
  --start-date 2010-01-01 \
  --end-date 2023-12-31 \
  --enable-cache
```

This command would produce the same results as the example script, but in a more flexible and configurable way.

## Parameter Tuning Guide

The parameters in this example were chosen for demonstration purposes. In a real-world scenario, you would want to experiment with these settings to optimize the strategy. Here are some ideas for parameter tuning:

- **`top_k`**: A smaller `top_k` might lead to a more concentrated, higher-conviction portfolio, but potentially with higher risk. A larger `top_k` would be more diversified.
- **`lookback`**: The lookback period for momentum is a classic parameter to test. Common values range from 3 to 12 months.
- **`buffer_rank`**: A smaller buffer will make the portfolio track the top momentum names more closely but will increase turnover. A larger buffer will reduce turnover but may lead to holding onto assets that are losing momentum.
- **`min_holding_periods`**: This parameter can be used to enforce a longer-term holding discipline, which can be beneficial for tax purposes and reducing the impact of short-term noise.

By experimenting with these parameters, you can gain a deeper understanding of the trade-offs between momentum exposure, turnover, and overall performance.
