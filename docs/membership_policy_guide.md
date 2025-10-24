# Membership Policy Tuning Guide

This guide provides practical advice on how to tune the parameters for the `membership_policy` feature to control portfolio turnover and stability.

## Key Parameters

The main parameters to tune in the `membership_policy` section are:

- `min_holding_periods`: The minimum time to hold an asset.
- `buffer_rank`: A "grace zone" for existing holdings.
- `max_turnover`: A hard cap on portfolio churn.
- `max_new_assets` & `max_removed_assets`: Limits on the number of trades.

## How to Choose `min_holding_periods`

This parameter forces an asset to be held for a minimum number of rebalancing periods, which helps prevent "whipsaw" trades where an asset is bought and sold in quick succession.

- **Use Case**: To enforce a long-term holding discipline and reduce tax impacts.
- **Value**: If you rebalance monthly, `min_holding_periods: 3` means an asset is held for at least 3 months. For quarterly rebalancing, `min_holding_periods: 4` would mean holding for at least a year.
- **Tradeoff**: A high value can prevent you from selling a poorly performing asset quickly.

**Recommendation**: Start with `min_holding_periods: 3` for monthly rebalancing.

## How to Choose `buffer_rank`

This is one of the most effective parameters for reducing turnover. It gives existing holdings a "grace zone" if their rank drops slightly.

- **How it works**: If `top_k` is 50 and `buffer_rank` is 60, an existing holding will be kept as long as its rank is 60 or better. A new asset would need to be ranked 50 or better to be considered.
- **Value**: A common approach is to set the buffer to be 10-20% of the `top_k`. For `top_k: 50`, a `buffer_rank` of `60` would be a 20% buffer.
- **Tradeoff**: A large buffer reduces turnover but makes the portfolio slower to respond to new, high-ranked assets. A small buffer increases responsiveness at the cost of higher turnover.

**Recommendation**: Set `buffer_rank` to be `top_k + 10`. For `top_k: 50`, use `buffer_rank: 60`.

## How to Choose `max_turnover`

This parameter provides a hard cap on the percentage of the portfolio that can be changed in a single rebalance.

- **Use Case**: For strategies with very high transaction costs or strict institutional constraints.
- **Value**: `max_turnover: 0.25` means that no more than 25% of the portfolio's assets can be changed at a rebalance.
- **Tradeoff**: This is a very blunt instrument. It can prevent the strategy from taking advantage of new opportunities if the cap is hit. It can also lead to unintended consequences, as the system will have to decide which trades *not* to make.

**Recommendation**: Use this parameter sparingly. It's often better to control turnover with `min_holding_periods` and `buffer_rank`. If you do use it, start with a relatively high value like `max_turnover: 0.40`.

## How to Choose `max_new_assets` and `max_removed_assets`

These parameters limit the number of assets that can be bought or sold at a rebalance.

- **Use Case**: To smooth out portfolio changes over time.
- **Value**: For a 50-asset portfolio, `max_new_assets: 5` and `max_removed_assets: 5` would mean that at most 10% of the portfolio is turned over.
- **Tradeoff**: Like `max_turnover`, these can be blunt instruments. They can prevent the portfolio from adapting quickly to market changes.

**Recommendation**: Use these in combination with other parameters. For example, you can set a `buffer_rank` and also a `max_new_assets` to ensure that even if many new assets are highly ranked, you only onboard a few at a time.

## Balancing Stability vs. Responsiveness

- **For more stability (lower turnover)**:
  - Increase `min_holding_periods`.
  - Increase `buffer_rank`.
  - Set `max_turnover`, `max_new_assets`, or `max_removed_assets`.
- **For more responsiveness (higher turnover)**:
  - Decrease `min_holding_periods`.
  - Decrease `buffer_rank`.
  - Do not set the `max_` constraints.

## Decision Tree for Common Choices

1.  **What is your primary goal?**
    - **Reduce whipsaw trades and taxes**: Go to 2.
    - **Reduce turnover from rank fluctuations**: Go to 3.
    - **Strictly cap churn**: Go to 4.

2.  **To reduce whipsaw trades**:
    - Set `min_holding_periods` to a value that reflects your desired holding time (e.g., 3 for monthly rebalancing).

3.  **To reduce turnover from rank fluctuations**:
    - Set `buffer_rank` to be `top_k + 10` or `top_k + 20`.

4.  **To strictly cap churn**:
    - Start by using `min_holding_periods` and `buffer_rank`.
    - If turnover is still too high, cautiously add `max_turnover` or `max_new_assets`.

**Final Tip**: Membership policy works best when used to gently guide the portfolio, not to force it into a straitjacket. Start with a simple policy (e.g., just `min_holding_periods` and `buffer_rank`) and only add more constraints if necessary. Always backtest to see the impact on performance and turnover.