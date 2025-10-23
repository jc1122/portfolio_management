# 1000-Asset Backtest Results

## Summary

Successfully ran backtests on a 1000-asset universe with long history data (2021-01-04 to 2025-10-03) using the rolling 252-day lookback window implementation. All three portfolio strategies completed efficiently.

## Performance Summary

### Execution Times

| Strategy | Execution Time | Assets | Rebalances |
|----------|---------------|--------|------------|
| Equal Weight | 9.4s | 1000 | 58 |
| Risk Parity | 9.1s | 1000 | 47 |
| Mean Variance | 23.1s | 1000 | 47 |

### Strategy Performance Comparison

| Metric | Equal Weight | Risk Parity | Mean Variance |
|--------|--------------|-------------|---------------|
| **Total Return** | 35.0% | 2.8% | 15.5% |
| **Annualized Return** | 6.4% | 0.6% | 3.0% |
| **Annualized Volatility** | 12.8% | 8.9% | 13.8% |
| **Sharpe Ratio** | 0.498 | 0.063 | 0.219 |
| **Sortino Ratio** | 0.775 | 0.084 | 0.286 |
| **Max Drawdown** | -16.6% | -12.3% | -18.7% |
| **Calmar Ratio** | 0.383 | 0.046 | 0.162 |
| **Expected Shortfall (95%)** | -1.23% | -0.86% | -1.40% |
| **Win Rate** | 50.7% | 40.2% | 40.5% |
| **Total Costs** | $14,274 | $9,852 | $18,799 |

## Key Findings

### 1. Scaling Performance

The rolling lookback window implementation scales remarkably well:

- **Equal Weight**: Went from 5s (100 assets) to 9.4s (1000 assets) - only 1.9x slower for 10x assets
- **Risk Parity**: Went from 23s (100 assets) to 9.1s (1000 assets) - actually faster on larger universe
- **Mean Variance**: Went from 42s (100 assets) to 23.1s (1000 assets) - 1.8x faster on larger universe

### 2. Strategy Effectiveness

**Equal Weight** remains the best performer:

- Highest Sharpe ratio (0.498)
- Highest total return (35.0%)
- Best risk-adjusted returns

**Risk Parity** shows conservative characteristics:

- Lowest volatility (8.9%)
- Lowest drawdown (-12.3%)
- Very low returns (0.6% annualized)
- Poor Sharpe ratio (0.063)

**Mean Variance** shows moderate performance:

- Middle ground on returns (15.5% total)
- Moderate Sharpe ratio (0.219)
- Highest drawdown (-18.7%)

### 3. Data Period

Backtest period: 2021-01-04 to 2025-10-03 (4.75 years)

- Market conditions: Post-COVID recovery, inflation concerns, rate hikes
- Test universe: 1000 global stocks with 20+ years of history

## Charts Generated

All strategies have equity curve and drawdown visualizations:

- `outputs/backtests/long_history_1000_equal_weight/equity_curve.png`
- `outputs/backtests/long_history_1000_equal_weight/drawdown.png`
- `outputs/backtests/long_history_1000_risk_parity/equity_curve.png`
- `outputs/backtests/long_history_1000_risk_parity/drawdown.png`
- `outputs/backtests/long_history_1000_mean_variance/equity_curve.png`
- `outputs/backtests/long_history_1000_mean_variance/drawdown.png`

## Technical Notes

1. **Lookback Window**: 252 trading days (1 year) for parameter estimation
1. **Rebalancing**: Monthly frequency with 5% drift threshold
1. **Transaction Costs**:
   - Commission: 0.1% per trade
   - Minimum commission: $1.00
   - Slippage: 5 basis points
1. **Initial Capital**: $1,000,000

## Conclusion

The rolling lookback window implementation successfully addresses the computational challenges that caused optimization strategies to hang on large datasets. The system now processes 1000-asset backtests efficiently, with all strategies completing in under 25 seconds. Equal weight strategy remains the most effective for this universe and time period.
