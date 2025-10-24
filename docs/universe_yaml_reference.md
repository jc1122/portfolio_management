# Universe YAML Reference

This document provides a complete reference for all the configuration options available in the `universes.yaml` file.

## Top-Level Structure

The `universes.yaml` file has a single top-level key, `universes`. Under this key, you can define one or more named universe configurations.

```yaml
universes:
  my_first_universe:
    # ... configuration ...
  my_second_universe:
    # ... configuration ...
```

## Universe Configuration Sections

Each named universe configuration is divided into the following sections:

- `description`: A human-readable description of the universe.
- `filter_criteria`: Rules for the initial asset selection.
- `classification_requirements`: Filters based on asset classification.
- `return_config`: Parameters for return calculation.
- `constraints`: Constraints on the final universe size.
- `pit_eligibility`: Point-in-Time eligibility filters.
- `preselection`: Factor-based preselection of assets.
- `membership_policy`: Rules for asset turnover and portfolio stability.

---

### `description`

A string describing the purpose of the universe.

- **Type**: `string`
- **Required**: No

**Example:**
```yaml
description: "A core portfolio of global, diversified ETFs."
```

---

### `filter_criteria`

This section defines the rules for the initial asset selection, corresponding to the `select_assets.py` script.

| Parameter | Type | Description | Default |
|---|---|---|---|
| `data_status` | `list[string]` | Allowed data quality statuses. Options: `ok`, `warning`, `error`. | `["ok"]` |
| `min_history_days` | `integer` | Minimum number of calendar days of price history. | `252` |
| `min_price_rows` | `integer` | Minimum number of non-null price data points. | `252` |
| `max_gap_days` | `integer` | Maximum allowed gap in days between consecutive prices. | `10` |
| `markets` | `list[string]` | List of allowed market codes (e.g., "LSE", "NYSE"). | (all) |
| `regions` | `list[string]` | List of allowed geographic regions. | (all) |
| `currencies` | `list[string]` | List of allowed currencies (e.g., "USD", "GBP"). | (all) |
| `categories` | `list[string]` | List of allowed custom categories. | (all) |
| `allowlist` | `list[string]` | List of symbols/ISINs to force-include. | (none) |
| `blocklist` | `list[string]` | List of symbols/ISINs to always exclude. | (none) |

**Example:**
```yaml
filter_criteria:
  data_status: ["ok", "warning"]
  min_history_days: 756
  markets: ["LSE", "NYSE"]
  currencies: ["GBP", "USD"]
```

---

### `classification_requirements`

This section allows you to filter assets based on their classification, which is determined by the `classify_assets.py` script.

| Parameter | Type | Description |
|---|---|---|
| `asset_class` | `list[string]` | Allowed asset classes (e.g., "equity", "commodity"). |
| `sub_class` | `list[string]` | Allowed sub-classes (e.g., "growth", "value"). |
| `geography` | `list[string]` | Allowed geographies (e.g., "north_america", "europe"). |
| `sector` | `list[string]` | Allowed sectors (e.g., "Technology", "Healthcare"). |
| `tags` | `list[string]` | Allowed custom tags. |

**Example:**
```yaml
classification_requirements:
  asset_class: ["equity"]
  geography: ["north_america", "united_kingdom"]
```

---

### `return_config`

This section defines the parameters for the return calculation, corresponding to the `calculate_returns.py` script.

| Parameter | Type | Description | Default |
|---|---|---|---|
| `method` | `string` | Return calculation method. Options: `simple`, `log`, `excess`. | `simple` |
| `frequency` | `string` | Resampling frequency. Options: `daily`, `weekly`, `monthly`. | `daily` |
| `handle_missing` | `string` | How to handle missing data. Options: `forward_fill`, `interpolate`, `drop`. | `forward_fill` |
| `max_forward_fill_days` | `integer` | Maximum number of days to forward fill. | `5` |
| `min_periods` | `integer` | Minimum number of return periods required for an asset to be included. | `5` |
| `align_method` | `string` | How to align assets with different date ranges. Options: `outer`, `inner`. | `outer` |
| `min_coverage` | `float` | Minimum percentage (0.0 to 1.0) of non-null returns required. | `0.8` |

**Example:**
```yaml
return_config:
  method: "log"
  frequency: "monthly"
  handle_missing: "interpolate"
```

---

### `constraints`

This section sets high-level constraints on the final size of the universe.

| Parameter | Type | Description |
|---|---|---|
| `min_assets` | `integer` | The minimum number of assets the universe must have. |
| `max_assets` | `integer` | The maximum number of assets the universe can have. |

**Example:**
```yaml
constraints:
  min_assets: 30
  max_assets: 50
```

---

### `pit_eligibility`

This section enables Point-in-Time eligibility filtering to avoid lookahead bias in backtests.

| Parameter | Type | Description | Default |
|---|---|---|---|
| `enabled` | `boolean` | Enable or disable PIT eligibility. | `false` |
| `min_history_days` | `integer` | Minimum calendar days of history required at a point in time. | `252` |
| `min_price_rows` | `integer` | Minimum data points required at a point in time. | `252` |

**Example:**
```yaml
pit_eligibility:
  enabled: true
  min_history_days: 504
  min_price_rows: 480
```

---

### `preselection`

This section configures the factor-based preselection of assets to reduce the universe size before optimization.

| Parameter | Type | Description | Default |
|---|---|---|---|
| `method` | `string` | Preselection method. Options: `momentum`, `low_vol`, `combined`. | (disabled) |
| `top_k` | `integer` | The number of top assets to select. | (disabled) |
| `lookback` | `integer` | The lookback period in days for factor calculation. | `252` |
| `skip` | `integer` | Number of most recent days to skip for momentum calculation. | `1` |
| `min_periods` | `integer` | Minimum number of data points required for a valid factor score. | `60` |
| `momentum_weight` | `float` | Weight for the momentum factor (for `combined` method). | `0.5` |
| `low_vol_weight` | `float` | Weight for the low-volatility factor (for `combined` method). | `0.5` |

**Example:**
```yaml
preselection:
  method: "combined"
  top_k: 50
  lookback: 252
  momentum_weight: 0.6
  low_vol_weight: 0.4
```

---

### `membership_policy`

This section configures the rules for asset turnover and portfolio stability.

| Parameter | Type | Description | Default |
|---|---|---|---|
| `enabled` | `boolean` | Enable or disable the membership policy. | `false` |
| `min_holding_periods` | `integer` | Minimum number of rebalance periods to hold an asset. | `0` |
| `buffer_rank` | `integer` | A rank buffer to keep existing holdings even if they fall out of the `top_k`. | `0` |
| `max_turnover` | `float` | Maximum allowed portfolio turnover (0.0 to 1.0) per rebalance. | (none) |
| `max_new_assets` | `integer` | Maximum number of new assets to add per rebalance. | (none) |
| `max_removed_assets` | `integer` | Maximum number of assets to remove per rebalance. | (none) |

**Example:**
```yaml
membership_policy:
  enabled: true
  min_holding_periods: 3
  buffer_rank: 60
  max_turnover: 0.25
```