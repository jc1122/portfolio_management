# Universe Configuration Guide (`universes.yaml`)

## Overview

The `config/universes.yaml` file is the central blueprint for the entire portfolio workflow. It allows you to define a named, reusable set of rules and parameters that orchestrate the entire data pipeline, from asset selection through to return calculation.

Instead of running each script manually with many command-line arguments, you can define a universe once in this file. Then, you can use the `scripts/manage_universes.py` script to `validate`, `load`, or `compare` your defined universes, making your workflow repeatable and easy to manage.

## Long-History Reference Universes

For large scale regression tests we maintain `config/universes_long_history.yaml`, which stores precomputed ticker rosters derived from the Stooq archive. The `long_history_1000` entry now covers 1,000 assets with continuous daily prices from 2005-02-25 onward, excluding the previously gap-prone tickers (`BT.A`, `SANM`, `SANM:US`, `AXGN`, `AXGN:US`). The corresponding price and return matrices live under `outputs/long_history_1000/` (with returns published as the compressed `long_history_1000_returns_daily.csv.gz`) and align with the metadata exported by the asset selection pipeline.

## Role in the Workflow

This configuration file is the heart of the **Managed Workflow**. The intended end-to-end process is as follows:

1. **Phase 1: Initial Data Preparation (Run Once)**
   You run the `scripts/prepare_tradeable_data.py` script once to scan all your raw data and generate the master `tradeable_matches.csv` file.

1. **Phase 2: Universe Definition (Manual Strategy Step)**
   You edit this `universes.yaml` file to define the rules and parameters for your investment strategies (universes).

1. **Phase 3: Pipeline Execution (Managed by `manage_universes.py`)**
   You use the `scripts/manage_universes.py` script with a command like `load <your_universe_name>` to automatically execute the full data pipeline (select, classify, calculate returns) based on the rules you defined here.

## Basic Structure

The file has a top-level `universes:` key. Underneath it, you can define one or more named universes. Each universe is a collection of settings that control the different stages of the pipeline.

```yaml
universes:
  my_first_universe:
    # ... configuration for this universe ...
  my_second_universe:
    # ... configuration for this universe ...
```

## Universe Definition

Each named universe has seven configuration blocks (four core blocks plus three optional advanced blocks):

### Core Configuration Blocks

### 1. `filter_criteria`

This block defines the rules for the **asset selection** step. The keys in this block correspond directly to the command-line arguments of the `scripts/select_assets.py` script.

**Example:**

```yaml
filter_criteria:
  data_status: ["ok"]
  min_history_days: 756
  markets: ["LSE", "NYSE"]
  currencies: ["GBP", "USD"]
  # ... and any other arguments from select_assets.py
```

*For a full list and detailed explanation of these criteria, see the `docs/asset_selection.md` documentation.*

### 2. `classification_requirements`

This block provides a way to **filter the asset list *after*** it has been selected and classified. This allows you to create universes with a specific thematic focus.

**Example:**

```yaml
classification_requirements:
  # Only keep assets that were classified as equity
  asset_class: ["equity"]
  # And only from these specific geographies
  geography: ["north_america", "united_kingdom"]
```

### 3. `return_config`

This block defines the parameters for the **return calculation** step. The keys in this block correspond directly to the command-line arguments of the `scripts/calculate_returns.py` script.

**Example:**

```yaml
return_config:
  method: "simple"
  frequency: "monthly"
  handle_missing: "forward_fill"
  align_method: "outer"
  min_coverage: 0.85
  # ... and any other arguments from calculate_returns.py
```

*For a full list and detailed explanation of these parameters, see the `docs/calculate_returns.md` documentation.*

### 4. `constraints`

This block sets high-level constraints on the final size of the universe itself, ensuring that the list of assets passing all the above filters is within an expected range.

**Example:**

```yaml
constraints:
  min_assets: 30
  max_assets: 50
```

This ensures that after all filtering and classification, the final asset list used for portfolio construction will have between 30 and 50 assets.

### Advanced Configuration Blocks (Optional)

These optional blocks enable advanced portfolio features introduced in Sprint 2:

### 5. `preselection` (Optional)

Controls factor-based universe reduction before portfolio optimization. Applies momentum, low-volatility, or combined factor ranking to select top-K assets.

**Parameters:**
- `method`: Factor method (`momentum`, `low_vol`, or `combined`)
- `top_k`: Number of assets to select
- `lookback`: Lookback period in days (default: 252)
- `skip`: Skip N most recent days (default: 1)
- `momentum_weight`: Weight for momentum in combined method (default: 0.5)
- `low_vol_weight`: Weight for low-volatility in combined method (default: 0.5)
- `min_periods`: Minimum data periods required (default: 60)

**Example:**

```yaml
preselection:
  method: "combined"           # momentum, low_vol, or combined
  top_k: 30                    # Select top 30 assets
  lookback: 252                # 1 year lookback
  skip: 1                      # Skip most recent day
  momentum_weight: 0.6         # 60% momentum
  low_vol_weight: 0.4          # 40% low-volatility
  min_periods: 60              # Require at least 60 days
```

*See `docs/preselection.md` for detailed documentation.*

### 6. `membership_policy` (Optional)

Controls portfolio turnover and asset churn during rebalancing. Prevents excessive changes to portfolio composition.

**Parameters:**
- `buffer_rank`: Rank buffer to protect existing holdings (default: 5)
- `min_holding_periods`: Minimum rebalance periods to hold an asset (default: 3)
- `max_turnover`: Maximum portfolio turnover per rebalance (0-1)
- `max_new_assets`: Maximum new assets to add per rebalancing
- `max_removed_assets`: Maximum assets to remove per rebalancing

**Example:**

```yaml
membership_policy:
  buffer_rank: 10              # Protect holdings within top 40 if top_k=30
  min_holding_periods: 3       # Hold for at least 3 rebalances
  max_turnover: 0.30           # Maximum 30% turnover
  max_new_assets: 5            # Add maximum 5 new assets
  max_removed_assets: 3        # Remove maximum 3 assets
```

*See `docs/membership_policy.md` for detailed documentation.*

### 7. `pit_eligibility` (Optional)

Controls point-in-time eligibility filtering to prevent lookahead bias. Ensures assets have sufficient history at each rebalance date.

**Parameters:**
- `enabled`: Enable PIT eligibility filtering (boolean)
- `min_history_days`: Minimum days of history required (default: 252)
- `min_price_rows`: Minimum price observations required (default: 252)

**Example:**

```yaml
pit_eligibility:
  enabled: true                # Enable PIT filtering
  min_history_days: 252        # Require 1 year of history
  min_price_rows: 252          # Require 252 price observations
```

*See `docs/pit_eligibility_edge_cases.md` for edge case documentation.*

## Complete Examples

### Example 1: Basic Universe (Core Blocks Only)

Here is a basic universe definition using only the core configuration blocks. This is based on the `core_global` universe from the project's default configuration.

```yaml
universes:
  core_global:
    # A human-readable description of the universe's goal
    description: "Global core sleeve of diversified ETFs"

    # --- Asset Selection (filter_criteria) ---
    filter_criteria:
      # Only include assets with clean data quality
      data_status: ["ok"]
      # Assets must have at least 756 calendar days (~3 years) of history
      min_history_days: 756
      min_price_rows: 756
      # Restrict to assets trading on the London Stock Exchange
      markets: ["LSE", "GBR-LSE"]
      # Restrict to assets traded in Great British Pounds
      currencies: ["GBP"]
      # Custom filter specific to the project's data
      categories:
        - "lse etfs/1"
        - "lse etfs/2"

    # --- Post-Classification Filter (classification_requirements) ---
    classification_requirements:
      # Only keep assets that fall into these classes
      asset_class: ["equity", "commodity", "real_estate"]
      geography: ["united_kingdom", "north_america"]

    # --- Return Calculation (return_config) ---
    return_config:
      method: "simple"
      frequency: "monthly"
      handle_missing: "forward_fill"
      max_forward_fill_days: 5
      min_periods: 5
      align_method: "outer"
      min_coverage: 0.85

    # --- Universe Size Constraints (constraints) ---
    constraints:
      min_assets: 30
      max_assets: 50
```

### Example 2: Advanced Universe (All Features)

This example shows a universe definition with all optional advanced features enabled, suitable for production use with large universes and monthly rebalancing.

```yaml
universes:
  production_momentum_tilted:
    description: "Production momentum-tilted portfolio with turnover control"

    # --- Asset Selection ---
    filter_criteria:
      data_status: ["ok"]
      min_history_days: 1260  # 5 years for robust statistics
      min_price_rows: 1000
      markets: ["NYSE", "NASDAQ", "LSE"]
      currencies: ["USD", "GBP"]

    # --- Post-Classification Filter ---
    classification_requirements:
      asset_class: ["equity"]
      geography: ["united_states", "united_kingdom"]

    # --- Return Calculation ---
    return_config:
      method: "simple"
      frequency: "daily"
      handle_missing: "forward_fill"
      max_forward_fill_days: 3
      min_periods: 10
      align_method: "inner"
      min_coverage: 0.90

    # --- Universe Size ---
    constraints:
      min_assets: 40
      max_assets: 60

    # --- Preselection: Select top 50 by combined momentum/low-vol ---
    preselection:
      method: "combined"
      top_k: 50
      lookback: 252
      skip: 21                  # Skip most recent month
      momentum_weight: 0.7      # Heavy momentum tilt
      low_vol_weight: 0.3       # Light defensive tilt
      min_periods: 180          # 180 days minimum

    # --- Membership Policy: Strict turnover control ---
    membership_policy:
      buffer_rank: 15           # Large buffer for stability
      min_holding_periods: 5    # Hold for at least 5 rebalances
      max_turnover: 0.25        # Maximum 25% turnover
      max_new_assets: 3         # Add maximum 3 new assets
      max_removed_assets: 2     # Remove maximum 2 assets

    # --- PIT Eligibility: Prevent lookahead bias ---
    pit_eligibility:
      enabled: true
      min_history_days: 504     # Require 2 years
      min_price_rows: 400       # Require 400 observations
```

### Example 3: Defensive Universe (Low-Vol Focus)

A universe designed for defensive, low-volatility investing with monthly rebalancing.

```yaml
universes:
  defensive_low_vol:
    description: "Defensive low-volatility portfolio"

    filter_criteria:
      data_status: ["ok"]
      min_history_days: 756
      markets: ["NYSE", "NASDAQ"]
      currencies: ["USD"]

    classification_requirements:
      asset_class: ["equity", "fixed_income"]

    return_config:
      method: "simple"
      frequency: "daily"
      handle_missing: "forward_fill"
      min_coverage: 0.85

    constraints:
      min_assets: 25
      max_assets: 40

    # Preselection: Pure low-volatility
    preselection:
      method: "low_vol"
      top_k: 30
      lookback: 252
      min_periods: 120

    # Membership: Very stable (defensive strategy)
    membership_policy:
      buffer_rank: 20
      min_holding_periods: 6
      max_turnover: 0.15        # Very low turnover

    pit_eligibility:
      enabled: true
      min_history_days: 252
```

### Example 4: Large Universe with Aggressive Preselection

For backtesting very large universes (500+ assets), use aggressive preselection.

```yaml
universes:
  large_universe_momentum:
    description: "Large universe with aggressive momentum preselection"

    filter_criteria:
      data_status: ["ok"]
      min_history_days: 252
      # No market/currency filters - global universe

    return_config:
      method: "simple"
      frequency: "daily"

    constraints:
      min_assets: 100           # Start with 100+ assets
      max_assets: 1000          # Can handle up to 1000

    # Preselection: Reduce to manageable size
    preselection:
      method: "momentum"
      top_k: 50                 # Aggressive reduction: 1000 → 50
      lookback: 252
      skip: 1

    # Membership: Moderate control
    membership_policy:
      buffer_rank: 10
      min_holding_periods: 3
      max_turnover: 0.30

    pit_eligibility:
      enabled: true
      min_history_days: 252
```

## Validation Process

The toolkit provides validation tools to check universe configurations before running backtests.

### Command-Line Validation

Use `manage_universes.py` to validate a universe definition:

```bash
# Validate a single universe
python scripts/manage_universes.py validate core_global

# Validate all universes in a file
python scripts/manage_universes.py validate-all
```

**Validation Checks**:

1. **YAML Syntax**: Verifies the file is valid YAML
2. **Required Blocks**: Ensures `filter_criteria`, `return_config`, and `constraints` are present
3. **Parameter Types**: Validates that parameters have correct types (int, float, string, list)
4. **Parameter Ranges**: Checks that numeric values are within valid ranges
5. **Block Dependencies**: Verifies optional blocks have required parameters
6. **Constraint Consistency**: Checks that `min_assets` ≤ `max_assets`

**Example Output**:

```
✓ Universe 'core_global' is valid
✓ All required blocks present
✓ Parameter types correct
✓ Constraints consistent
✓ Preselection configuration valid
✓ Membership policy configuration valid
✓ PIT eligibility configuration valid
```

### Validation Warnings

The validation process may emit warnings for non-fatal issues:

**Common Warnings**:

- **Large Top-K**: `preselection.top_k > 100` - May not provide sufficient universe reduction
- **Small Min-Hold**: `membership_policy.min_holding_periods < 3` - May lead to excessive turnover
- **High Turnover**: `membership_policy.max_turnover > 0.5` - May incur high transaction costs
- **Short History**: `pit_eligibility.min_history_days < 252` - May include immature assets

**Handling Warnings**:

```bash
# Run with strict validation (warnings become errors)
python scripts/run_backtest.py risk_parity --strict

# Suppress warnings (not recommended)
python scripts/run_backtest.py risk_parity --ignore-warnings
```

### Programmatic Validation

You can validate configurations programmatically:

```python
from portfolio_management.config.validation import (
    validate_preselection_config,
    validate_membership_config,
    validate_pit_config,
)

# Validate preselection
warnings = validate_preselection_config(preselection_dict)
for warning in warnings:
    print(f"Warning: {warning.message}")

# Validate membership policy
warnings = validate_membership_config(membership_dict)

# Validate PIT eligibility
warnings = validate_pit_config(pit_dict)
```

## Workflow: Export and Compare

### Load and Run a Universe

```bash
# Load universe and run full pipeline
python scripts/manage_universes.py load core_global

# This automatically executes:
# 1. select_assets.py (using filter_criteria)
# 2. classify_assets.py
# 3. calculate_returns.py (using return_config)
```

### Compare Multiple Universes

Compare asset selection across different universe definitions:

```bash
# Compare two universes
python scripts/manage_universes.py compare core_global defensive_low_vol

# Output shows:
# - Assets unique to each universe
# - Assets in common
# - Differences in universe size
```

**Example Output**:

```
Universe Comparison: core_global vs defensive_low_vol
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Core Stats:
  core_global:        42 assets
  defensive_low_vol:  28 assets
  In common:          18 assets

Unique to core_global (24 assets):
  AAPL, TSLA, GOOGL, ...

Unique to defensive_low_vol (10 assets):
  TLT, IEF, BND, ...

Overlap: 42.9%
```

### Export Universe

Export a processed universe to CSV for use in other tools:

```bash
# Export asset list
python scripts/manage_universes.py export core_global \
    --output universes/core_global_assets.csv

# Export with returns
python scripts/manage_universes.py export core_global \
    --include-returns \
    --output universes/core_global_full.csv
```

## Best Practices

### Configuration Organization

**File Structure**:
```
config/
├── universes.yaml              # Main production universes
├── universes_test.yaml         # Test/development universes
├── universes_long_history.yaml # Historical regression test universes
└── universes_experimental.yaml # Experimental configurations
```

**Naming Conventions**:
- `core_*`: Core portfolio sleeves (main allocations)
- `satellite_*`: Satellite sleeves (tactical tilts)
- `defensive_*`: Defensive/low-volatility strategies
- `momentum_*`: Momentum-tilted strategies
- `test_*`: Testing configurations

### Parameter Selection

**Universe Size**:
- Small portfolios (20-30 assets): Better for concentrated strategies
- Medium portfolios (30-50 assets): Good balance of diversification and simplicity
- Large portfolios (50-100+ assets): Maximum diversification but higher complexity

**Preselection Top-K**:
- Conservative: `top_k = 0.5 × starting_universe` (select half)
- Moderate: `top_k = 0.2 × starting_universe` (select 20%)
- Aggressive: `top_k = 30-50` (fixed target regardless of starting size)

**Membership Policy**:
- Stable portfolios: High `buffer_rank` (10-20), high `min_holding_periods` (5-8)
- Balanced portfolios: Medium `buffer_rank` (5-10), medium `min_holding_periods` (3-5)
- Active portfolios: Low `buffer_rank` (2-5), low `min_holding_periods` (1-2)

**PIT Eligibility**:
- Always enable for production backtests (prevents lookahead bias)
- `min_history_days = rebalance_lookback`: Ensure enough data for first rebalance
- Typical: `min_history_days = 252` (1 year) or `504` (2 years)

### Version Control

**Track Universe Changes**:
```bash
# Tag universe configurations with versions
git tag -a universes-v1.0 -m "Initial production universe configurations"
git push origin universes-v1.0

# Document changes in commit messages
git commit -m "Update core_global: Increase min_history to 1260 days (5 years)"
```

**Review Process**:
1. Create new universe in experimental file
2. Validate configuration
3. Run backtest on historical data
4. Compare with existing universes
5. Move to production file after approval

## Troubleshooting

### Issue: Universe Too Small After Filtering

**Symptom**: Universe has fewer assets than `min_assets`

**Solutions**:
1. Relax `filter_criteria` (reduce `min_history_days`, add more markets)
2. Reduce `min_assets` constraint
3. Remove or relax `classification_requirements`
4. Check data availability (may need more data sources)

### Issue: Preselection Reduces Universe Too Much

**Symptom**: Preselection selects fewer than expected assets

**Causes**:
- Many assets have insufficient data for factor calculation
- `min_periods` is too strict
- `lookback` period exceeds available history

**Solutions**:
1. Reduce `preselection.min_periods`
2. Reduce `preselection.lookback`
3. Enable PIT eligibility to filter before preselection

### Issue: Membership Policy Too Restrictive

**Symptom**: Portfolio never rebalances or adds new assets

**Solutions**:
1. Reduce `buffer_rank` (less protective)
2. Reduce `min_holding_periods` (allow earlier exits)
3. Increase `max_turnover` (allow more changes)
4. Increase `max_new_assets` and `max_removed_assets`

### Issue: Validation Warnings

**Common Fixes**:

| Warning | Fix |
|---------|-----|
| Large top-K | Reduce `preselection.top_k` to 30-50 |
| Small min-hold | Increase `membership_policy.min_holding_periods` to 3+ |
| High turnover | Reduce `membership_policy.max_turnover` to ≤0.30 |
| Short history | Increase `pit_eligibility.min_history_days` to 252+ |

## See Also

- [Asset Selection](asset_selection.md) - Filter criteria details
- [Preselection](preselection.md) - Factor-based universe reduction
- [Membership Policy](membership_policy.md) - Turnover control
- [Backtesting](backtesting.md) - Running backtests with universes
- [Portfolio Construction](portfolio_construction.md) - Strategy selection
