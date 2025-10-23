# Backtest Integration Guide: PIT Eligibility, Preselection, and Membership Policy

This guide explains how to use the three integrated features in backtesting:
1. **Point-in-Time (PIT) Eligibility** - Avoid lookahead bias
2. **Preselection** - Factor-based asset filtering
3. **Membership Policy** - Control portfolio turnover

## Quick Start

### Using Universe Configuration (Recommended)

The easiest way is to define features in your universe YAML file:

```yaml
universes:
  my_universe:
    description: "Top-30 momentum strategy with turnover controls"
    assets:
      - AAPL
      - MSFT
      # ... more assets ...
    
    # Enable PIT eligibility filtering
    pit_eligibility:
      enabled: true
      min_history_days: 252  # Require 1 year of history
      min_price_rows: 252    # Require 252 valid observations
    
    # Enable preselection
    preselection:
      method: "momentum"     # Options: momentum, low_vol, combined
      top_k: 30             # Select top 30 assets
      lookback: 252         # 1 year lookback
      skip: 1               # Skip most recent day
      min_periods: 60       # Minimum data required
    
    # Enable membership policy
    membership_policy:
      enabled: true
      buffer_rank: 35               # Keep holdings ranked 31-35
      min_holding_periods: 3        # Hold for 3 rebalances minimum
      max_turnover: 0.30           # Max 30% turnover per rebalance
      max_new_assets: 5            # Add max 5 new assets
      max_removed_assets: 5        # Remove max 5 assets
```

Then run:

```bash
python scripts/run_backtest.py equal_weight \
  --universe-file config/universes.yaml \
  --universe-name my_universe \
  --prices-file data/prices.csv \
  --returns-file data/returns.csv
```

### Using CLI Flags

You can also configure features via command-line flags:

```bash
python scripts/run_backtest.py equal_weight \
  --universe-file config/universes.yaml \
  --universe-name my_universe \
  --use-pit-eligibility \
  --min-history-days 252 \
  --min-price-rows 252 \
  --preselect-method momentum \
  --preselect-top-k 30 \
  --membership-enabled \
  --membership-buffer-rank 35 \
  --membership-min-hold 3 \
  --membership-max-turnover 0.30
```

**Note:** CLI flags override universe configuration.

## Feature Details

### 1. Point-in-Time (PIT) Eligibility

**Purpose:** Ensure assets are only used when they have sufficient history, avoiding lookahead bias.

**How it works:**
- At each rebalance, computes which assets have enough history up to that date
- Excludes assets that don't meet the criteria
- Detects and liquidates delisted assets

**Parameters:**
- `enabled` (bool): Enable PIT filtering
- `min_history_days` (int): Minimum days from first valid observation (default: 252)
- `min_price_rows` (int): Minimum count of valid observations (default: 252)

**When to use:**
- When backtesting with assets that started trading at different times
- When you want to avoid using assets with insufficient history
- For more realistic historical simulations

### 2. Preselection

**Purpose:** Filter assets based on momentum and/or volatility factors before portfolio optimization.

**How it works:**
- Computes factor scores for all eligible assets
- Selects top-K assets by score
- Passes only selected assets to the portfolio optimizer

**Methods:**
- `momentum`: Cumulative return over lookback period
- `low_vol`: Inverse of realized volatility (lower vol = higher score)
- `combined`: Weighted combination of momentum and low-vol Z-scores

**Parameters:**
- `method` (str): Preselection method
- `top_k` (int): Number of assets to select
- `lookback` (int): Lookback period in days (default: 252)
- `skip` (int): Skip most recent N days (default: 1)
- `momentum_weight` (float): Weight for momentum in combined method (default: 0.5)
- `low_vol_weight` (float): Weight for low-vol in combined method (default: 0.5)
- `min_periods` (int): Minimum data required (default: 60)

**When to use:**
- When your universe is large (100+ assets) and optimizer is slow
- When you want factor-driven asset selection
- For momentum or low-volatility strategies

### 3. Membership Policy

**Purpose:** Control portfolio turnover and stability by limiting how many assets can be added/removed per rebalance.

**How it works:**
- After preselection (if enabled), applies policy rules to candidate set
- Keeps existing holdings that meet criteria (rank buffer, minimum hold period)
- Limits the number of additions and removals per rebalance
- Optionally enforces maximum turnover constraint

**Rules (applied in order):**
1. **Min holding periods**: Assets held for < N rebalances cannot be removed
2. **Rank buffer**: Existing holdings within buffer rank are kept (even if outside top-K)
3. **Max changes**: Limit additions and removals
4. **Turnover cap**: Limit total portfolio value that can change

**Parameters:**
- `enabled` (bool): Enable membership policy
- `buffer_rank` (int): Keep holdings ranked ≤ this value (e.g., 35 keeps top 35)
- `min_holding_periods` (int): Minimum rebalances to hold an asset (e.g., 3)
- `max_turnover` (float): Max portfolio turnover per rebalance (0-1, e.g., 0.30 = 30%)
- `max_new_assets` (int): Max new assets to add per rebalance
- `max_removed_assets` (int): Max assets to remove per rebalance

**When to use:**
- When transaction costs are significant
- When you want smoother portfolio transitions
- To reduce behavioral whiplash from frequent changes
- For long-term portfolios that should be stable

## Configuration Precedence

Features can be configured in three places with the following precedence:

1. **CLI flags** (highest) - Explicitly set on command line
2. **Universe YAML** (middle) - Defined in universe configuration
3. **Defaults** (lowest) - Built-in default values

### Examples

**Universe config with CLI override:**
```bash
# Universe has preselection: momentum, top 30
# CLI overrides to use low_vol, top 20
python scripts/run_backtest.py equal_weight \
  --universe-name my_universe \
  --preselect-method low_vol \
  --preselect-top-k 20
```

**Disable feature from universe:**
```bash
# Universe has membership policy enabled
# Can't disable via CLI - create a universe without it or set enabled: false in YAML
```

## Example Universes

### Conservative Portfolio (Low Turnover)

```yaml
conservative_equity:
  description: "Stable equity portfolio with minimal churn"
  assets: [...]
  
  pit_eligibility:
    enabled: true
    min_history_days: 504  # 2 years
    min_price_rows: 504
  
  preselection:
    method: "low_vol"      # Prefer low-volatility stocks
    top_k: 40
    lookback: 252
  
  membership_policy:
    enabled: true
    buffer_rank: 50        # Wide buffer
    min_holding_periods: 4 # Hold for 4 rebalances
    max_turnover: 0.20     # Low turnover
    max_new_assets: 3      # Few additions
    max_removed_assets: 3
```

### Aggressive Momentum Strategy

```yaml
aggressive_momentum:
  description: "High-turnover momentum strategy"
  assets: [...]
  
  pit_eligibility:
    enabled: true
    min_history_days: 252  # 1 year
    min_price_rows: 252
  
  preselection:
    method: "momentum"
    top_k: 30
    lookback: 126          # 6 months for faster signals
    skip: 1
  
  membership_policy:
    enabled: true
    buffer_rank: 35        # Narrow buffer
    min_holding_periods: 1 # Short hold period
    max_turnover: 0.50     # Higher turnover allowed
    max_new_assets: 10     # More flexibility
    max_removed_assets: 10
```

### Balanced Multi-Factor

```yaml
balanced_multifactor:
  description: "Balanced momentum and low-vol combination"
  assets: [...]
  
  pit_eligibility:
    enabled: true
    min_history_days: 252
    min_price_rows: 252
  
  preselection:
    method: "combined"
    top_k: 35
    lookback: 252
    momentum_weight: 0.6   # 60% momentum
    low_vol_weight: 0.4    # 40% low-vol
  
  membership_policy:
    enabled: true
    buffer_rank: 40
    min_holding_periods: 3
    max_turnover: 0.30
    max_new_assets: 5
    max_removed_assets: 5
```

## Backward Compatibility

All features are **opt-in**:
- Default behavior is unchanged when features are not configured
- Existing universes without these blocks work as before
- Existing strategies (equal weight, risk parity, mean-variance) work unchanged

To use the old behavior:
1. Don't add `pit_eligibility`, `preselection`, or `membership_policy` blocks to universe YAML
2. Don't set CLI flags for these features
3. All existing code continues to work

## Testing

Run integration tests:
```bash
# All integration tests (synthetic data)
pytest tests/integration/test_backtest_integration.py -v

# Smoke tests with real data (requires long_history datasets)
pytest tests/integration/test_smoke_integration.py -v
```

## Troubleshooting

### "No eligible assets" error

**Cause:** PIT eligibility filtered out all assets (not enough history).

**Solution:**
- Reduce `min_history_days` and `min_price_rows`
- Start backtest later when more assets have sufficient history
- Check that your data covers the backtest period

### Membership policy not having effect

**Possible causes:**
1. Policy is disabled: Check `enabled: true` in YAML or `--membership-enabled` in CLI
2. Preselection not providing ranks: Membership policy needs ranked candidates
3. Policy parameters too loose: Tighten constraints (lower buffer_rank, max_turnover, etc.)

**Debug:**
- Add `--verbose` flag to see what features are active
- Check rebalance events in output to see turnover levels

### Preselection returning no assets

**Cause:** Insufficient data for factor calculation.

**Solution:**
- Reduce `min_periods` in preselection config
- Increase `lookback` period to have more data
- Check that returns data covers the required period

## Performance Tips

1. **Large universes (500+ assets):**
   - Use preselection to reduce to 30-50 assets before optimization
   - Mean-variance and risk-parity are much faster with fewer assets

2. **High rebalance frequency:**
   - Enable membership policy to reduce turnover
   - Higher `min_holding_periods` reduces trades

3. **Long backtests (10+ years):**
   - Enable PIT eligibility to handle assets that started/stopped trading
   - Use larger `lookback` periods for more stable factors

## References

- **Preselection:** See `src/portfolio_management/portfolio/preselection.py`
- **Membership Policy:** See `src/portfolio_management/portfolio/membership.py`
- **PIT Eligibility:** See `src/portfolio_management/backtesting/eligibility.py`
- **Integration:** See `src/portfolio_management/backtesting/engine/backtest.py`
