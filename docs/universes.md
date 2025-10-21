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

Each named universe has four main configuration blocks:

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

## Complete Example

Here is a complete, annotated example of a universe definition. This is based on the `core_global` universe from the project's default configuration.

```yaml
  # The name of the universe, used with manage_universes.py
  core_global:
    # A human-readable description of the universe's goal.
    description: "Global core sleeve of diversified ETFs"

    # --- Corresponds to the `select_assets.py` script ---
    filter_criteria:
      # Only include assets with a clean data quality status.
      data_status: ["ok"]
      # Assets must have at least 756 calendar days (~3 years) of history.
      min_history_days: 756
      min_price_rows: 756
      # Restrict to assets trading on the London Stock Exchange.
      markets: ["LSE", "GBR-LSE"]
      # Restrict to assets traded in Great British Pounds.
      currencies: ["GBP"]
      # A custom filter that might be specific to the project's data.
      categories:
        - "lse etfs/1"
        - "lse etfs/2"

    # --- A post-classification filter ---
    classification_requirements:
      # After classification, only keep assets that fall into these classes.
      asset_class: ["equity", "commodity", "real_estate"]
      geography: ["united_kingdom", "north_america"]

    # --- Corresponds to the `calculate_returns.py` script ---
    return_config:
      method: "simple"
      frequency: "monthly"
      handle_missing: "forward_fill"
      max_forward_fill_days: 5
      min_periods: 5
      align_method: "outer"
      min_coverage: 0.85

    # --- A final check on the size of the resulting asset list ---
    constraints:
      min_assets: 30
      max_assets: 50
```
