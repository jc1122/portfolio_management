# Example: Multi-Factor Combined Strategy

This example demonstrates how to build a sophisticated strategy that combines multiple factors—in this case, momentum and low-volatility—to rank and select assets. The goal of a multi-factor model is to create a more robust portfolio by diversifying across different sources of return.

## Strategy Overview

This strategy blends the aggressive, return-chasing nature of momentum with the defensive, risk-reducing properties of low volatility.

1. **Universe**: Start with a broad universe of 1,000 liquid assets.
1. **Combined Factor Preselection**: At each rebalancing date, calculate both a momentum score and a low-volatility score for each asset. These scores are then combined into a single, weighted-average score. In this example, we use a 60% weight for momentum and a 40% weight for low-volatility. The top 25 assets with the highest combined score are selected.
1. **Portfolio Construction**: The 25 selected assets are weighted equally.
1. **Rebalancing**: The portfolio is rebalanced monthly to adapt to the latest factor scores.

By combining factors, we aim to create a strategy that can perform well in different market regimes—capturing upside during rallies (thanks to momentum) while offering some protection during downturns (thanks to low volatility).

## Key Features Demonstrated

- **Combined Preselection**: Using the `combined` method in the `Preselection` module.
- **Factor Weighting**: Assigning `momentum_weight` and `low_vol_weight` to control the influence of each factor.
- **Strategy Comparison**: This example provides a basis for comparing a multi-factor model against its single-factor components (the momentum and low-volatility strategies from the other examples).
- **Parameter Sensitivity**: Highlights how tuning the factor weights can be a powerful way to optimize a strategy.

## How to Run This Example

The example can be run directly from the `examples/multifactor_strategy.py` script.

```bash
python examples/multifactor_strategy.py
```

### Expected Output

The output will show the performance of the combined strategy. The interesting part is comparing these results to the single-factor examples.

```
Running Multi-Factor Combined Strategy Example...
Loading universe 'long_history_1000'...
Data loaded successfully.
Caching enabled at: .cache/examples
Multi-factor preselection configured: 60% Momentum, 40% Low-Volatility.

Starting backtest engine...
Backtest completed.

----- Backtest Summary (Multi-Factor) -----
initial_capital: 100000.0
end_capital: 320123.45
total_return: 2.2012
annualized_return: 0.0955
annualized_volatility: 0.1510  # <-- Hopefully lower than pure momentum
sharpe_ratio: 0.6325          # <-- Hopefully higher than both single factors
max_drawdown: -0.2980
calmar_ratio: 0.3205
...

Results saved to outputs/examples/multifactor_strategy
Multi-factor strategy example finished successfully.
```

## Performance Comparison (Single vs. Multi-Factor)

The real power of this example comes from comparing its output to the `momentum_turnover_control` and `lowvol_defensive` examples. You would typically analyze:

- **Returns**: Does the multi-factor model produce returns that are competitive with the pure momentum strategy?
- **Volatility and Drawdown**: Is the volatility lower than the momentum strategy, as intended? Is the max drawdown less severe?
- **Risk-Adjusted Return (Sharpe Ratio)**: The ultimate test. A successful multi-factor model should ideally have a higher Sharpe ratio than either of its single-factor components, indicating that the combination is more efficient.

## Factor Weight Optimization and Sensitivity Analysis

The factor weights (60% momentum, 40% low-vol) were chosen for this example, but they are critical parameters to optimize. You can perform a sensitivity analysis by running the backtest with different weight combinations:

- 70% Momentum / 30% Low-Vol
- 50% Momentum / 50% Low-Vol
- 30% Momentum / 70% Low-Vol

By plotting the performance metrics for each combination, you can find the optimal blend that best suits your risk-return objectives. This process of tuning factor weights is a cornerstone of quantitative strategy development.

## Configuration (`config/multifactor_strategy_config.yaml`)

The `config/multifactor_strategy_config.yaml` file shows how to set up the `combined` preselection method.

Key section:

```yaml
universes:
  multifactor_combined:
    # Preselection Configuration (Combined Factors)
    preselection:
      method: "combined"
      top_k: 25
      lookback: 252

      # Factor Weights
      momentum_weight: 0.6
      low_vol_weight: 0.4
```

To run with this configuration:

```bash
python scripts/run_backtest.py equal_weight \
  --universe-file config/multifactor_strategy_config.yaml \
  --universe-name multifactor_combined \
  --start-date 2010-01-01 \
  --end-date 2023-12-31
```

This example provides a launchpad for exploring the powerful and flexible world of multi-factor investing.
