# Preselection Tuning Guide

This guide provides practical advice on how to tune the parameters for the asset preselection feature.

## Key Parameters

The main parameters to tune in the `preselection` section of your `universes.yaml` are:

- `top_k`: The number of assets to select.
- `lookback`: The period over which to calculate the factor scores.
- `skip`: The number of recent periods to ignore (for momentum).
- `momentum_weight` & `low_vol_weight`: The weights for the combined factor.

## How to Choose `top_k`

The `top_k` parameter determines the size of your preselected universe.

- **Too small (e.g., `< 20`)**:
  - **Pros**: Very fast optimization.
  - **Cons**: High concentration risk, may be sensitive to single asset performance, may not be well-diversified.
- **Too large (e.g., `> 100`)**:
  - **Pros**: Better diversification.
  - **Cons**: Diminishes the performance benefits of preselection, as the optimizer still has a large number of assets to consider.
- **Sweet Spot (`20` to `50`)**:
  - For most strategies, selecting between 20 and 50 assets is a good balance. It provides a significant performance boost for the optimizer while still allowing for a reasonably diversified portfolio.

**Recommendation**: Start with `top_k: 30` and adjust based on your diversification needs.

## How to Choose `lookback`

The `lookback` period determines the timeframe for calculating factor scores. The optimal lookback period is strategy-dependent.

- **Shorter lookbacks (e.g., `63` days / 3 months)**:
  - **Pros**: More responsive to recent market changes, faster to compute.
  - **Cons**: Can be noisy and lead to higher turnover.
- **Longer lookbacks (e.g., `252` days / 1 year)**:
  - **Pros**: More stable, less sensitive to short-term noise.
  - **Cons**: Slower to react to new trends, slower to compute.

**Recommendation**:
- For **momentum** strategies, a `252`-day lookback is a standard choice in academic literature.
- For **low-volatility** strategies, a `252`-day lookback is also common.
- If you are rebalancing more frequently (e.g., monthly), consider a shorter lookback period like `63` or `126` days to better align with your rebalance frequency.

## How to Choose `skip` (for Momentum)

The `skip` parameter is used in momentum calculations to ignore the most recent data, which is often noisy and subject to short-term reversals.

- **`skip: 1`**: Skips the most recent day. This is a common practice.
- **`skip: 21` (approx. 1 month)**: This is the classic "12-1" momentum strategy, where you calculate the return over the past 12 months, excluding the most recent month.
- **`skip: 0`**: Not recommended for momentum, as it can be very sensitive to short-term noise.

**Recommendation**: Start with `skip: 21` for a standard monthly momentum strategy. For higher frequency strategies, a smaller `skip` like `5` (1 week) may be appropriate.

## How to Optimize Factor Weights (for Combined Method)

When using the `combined` method, you need to set the weights for the momentum and low-volatility factors.

- **`momentum_weight: 0.5`, `low_vol_weight: 0.5`**: A balanced, "all-weather" approach.
- **`momentum_weight: 0.7`, `low_vol_weight: 0.3`**: A more aggressive, growth-oriented approach that tilts towards momentum.
- **`momentum_weight: 0.3`, `low_vol_weight: 0.7`**: A more defensive approach that prioritizes stability.

**Recommendation**: Start with a balanced `0.5 / 0.5` split. If you have a strong view on the market environment (e.g., you expect a bull market), you might increase the weight on momentum. In a choppy or bear market, you might increase the weight on low-volatility.

## Performance Tradeoffs

- **Faster Backtests**:
  - Use a smaller `top_k`.
  - Use a shorter `lookback`.
- **More Stable Portfolios**:
  - Use a larger `top_k`.
  - Use a longer `lookback`.
  - Use a higher `low_vol_weight`.

## Decision Tree for Common Choices

1.  **What is your primary goal?**
    - **Growth/Aggressive**: Go to 2.
    - **Defensive/Stable**: Go to 3.
    - **Balanced**: Go to 4.

2.  **Growth/Aggressive (Momentum-focused)**
    - `method: "momentum"`
    - `top_k: 25` (for a concentrated portfolio)
    - `lookback: 252`
    - `skip: 21`

3.  **Defensive/Stable (Low-Volatility-focused)**
    - `method: "low_vol"`
    - `top_k: 40` (for better diversification)
    - `lookback: 252`

4.  **Balanced (Combined Factors)**
    - `method: "combined"`
    - `top_k: 30`
    - `lookback: 252`
    - `momentum_weight: 0.5`
    - `low_vol_weight: 0.5`

**Final Tip**: Always backtest your chosen parameters to see how they affect performance and turnover. There is no single "best" set of parameters; the optimal choice depends on your specific strategy and goals.