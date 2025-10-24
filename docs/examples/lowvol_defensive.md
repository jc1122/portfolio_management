# Example: Low-Volatility Defensive Strategy

This example illustrates how to construct a low-volatility, defensive equity strategy. The primary goal of such a strategy is not necessarily to maximize returns, but to provide a smoother ride by reducing drawdowns and overall portfolio volatility, especially during market downturns.

## Strategy Overview

The strategy is built on the "low-volatility anomaly," the observation that stocks with lower historical volatility have often provided higher risk-adjusted returns than their more volatile counterparts.

1. **Universe**: Start with a universe of 500 liquid assets.
1. **Low-Volatility Preselection**: At each rebalancing date, calculate the 12-month volatility for all eligible assets. Select the top 20 assets with the *lowest* volatility.
1. **Tight Turnover Control**: A key feature of defensive strategies is low turnover. We enforce this with a strict membership policy:
   - Assets must be held for at least one year (`min_holding_periods: 4` on a quarterly rebalance).
   - Maximum turnover is capped at 20% per rebalance.
1. **Portfolio Construction**: The 20 selected assets are weighted equally.
1. **Rebalancing**: The portfolio is rebalanced quarterly. A lower rebalancing frequency is typical for defensive strategies to further reduce costs and unnecessary trades.

This strategy is designed for investors who are more risk-averse and prioritize capital preservation.

## Key Features Demonstrated

- **Factor Preselection**: Using the `low_vol` method in the `Preselection` module to build a portfolio based on a defensive factor.
- **Strict Membership Policy**: Configuring a `MembershipPolicy` with `min_holding_periods` and `max_turnover` to enforce a low-churn, long-term holding discipline.
- **Quarterly Rebalancing**: Demonstrating a different rebalancing frequency suitable for less active strategies.
- **Risk Analysis**: The interpretation of this strategy's results will focus more on risk metrics like `annualized_volatility`, `max_drawdown`, and the `sharpe_ratio`.

## How to Run This Example

The example can be run directly from the `examples/lowvol_strategy.py` script.

```bash
python examples/lowvol_strategy.py
```

### Expected Output

The output will summarize the backtest results, with a focus on risk metrics.

```
Running Low-Volatility Defensive Strategy Example...
Loading universe 'long_history_1000'...
Data loaded successfully.
Caching enabled at: .cache/examples
Low-volatility preselection configured: Top 20 assets with 12-month lookback.
Membership policy configured: min_holding_periods=4, max_turnover=0.2.

Starting backtest engine...
Backtest completed.

----- Backtest Summary (Low-Volatility) -----
initial_capital: 100000.0
end_capital: 280123.45
total_return: 1.8012
annualized_return: 0.0811
annualized_volatility: 0.1234  # <-- Noticeably lower than a typical equity strategy
sharpe_ratio: 0.6572          # <-- Potentially higher due to lower volatility
max_drawdown: -0.2510          # <-- Expected to be lower (better)
calmar_ratio: 0.3231
average_turnover: 0.0812       # <-- Very low due to the tight membership policy
total_costs: 4321.98

Results saved to outputs/examples/lowvol_strategy
Low-volatility strategy example finished successfully.
```

The script will generate results in `outputs/examples/lowvol_strategy/`.

## Risk Analysis Interpretation

When evaluating a low-volatility strategy, the key metrics to watch are:

- **Annualized Volatility**: This should be significantly lower than that of a broad market index or a more aggressive strategy like momentum. This is the primary goal of the strategy.
- **Max Drawdown**: This measures the largest peak-to-trough decline in the portfolio's value. A successful low-volatility strategy will have a smaller (less negative) max drawdown, indicating better capital preservation during market crashes.
- **Sharpe Ratio**: This measures risk-adjusted return. Even if the total return is lower, a low-volatility strategy can have a higher Sharpe ratio if the volatility is reduced sufficiently.
- **Average Turnover**: This should be very low, confirming that the membership policy is working as intended to minimize transaction costs.

## Configuration (`config/lowvol_strategy_config.yaml`)

The `config/lowvol_strategy_config.yaml` file shows how to configure this strategy for the `run_backtest.py` script.

Key sections:

```yaml
universes:
  lowvol_defensive:
    # Preselection Configuration (Low-Volatility Factor)
    preselection:
      method: "low_vol"
      top_k: 20
      lookback: 252

    # Membership Policy (Tight Turnover Control)
    membership_policy:
      enabled: true
      min_holding_periods: 4
      max_turnover: 0.20
```

To run with this configuration:

```bash
python scripts/run_backtest.py equal_weight \
  --universe-file config/lowvol_strategy_config.yaml \
  --universe-name lowvol_defensive \
  --start-date 2010-01-01 \
  --end-date 2023-12-31 \
  --rebalance-frequency quarterly
```

## When to Use This Strategy

A low-volatility strategy is suitable for:

- **Risk-averse investors**: Those who prioritize capital preservation over maximizing returns.
- **Retirees or those nearing retirement**: Who cannot afford large drawdowns.
- **A core holding in a diversified portfolio**: It can act as a stabilizing element to complement more aggressive satellite strategies.

This example provides a solid foundation for building and testing defensive, factor-based investment strategies.
