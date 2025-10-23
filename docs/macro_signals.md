# Macroeconomic Signal Provider and Regime Gating

## Overview

The macro module provides infrastructure for loading macroeconomic time series from Stooq data directories and defining regime configurations that can influence asset selection decisions. This feature enables future integration of macroeconomic context into portfolio construction workflows.

## Current Implementation Status

**Status: Infrastructure Complete, Logic is NoOp (Stubbed)**

The current implementation provides:
- ✅ Complete data models and provider infrastructure
- ✅ Configuration system for regime rules
- ✅ Integration hooks in asset selection
- ⚠️ **NoOp regime logic** - all gating returns neutral signals and passes selections through unchanged

This documented NoOp behavior ensures the system is ready for future regime detection logic without affecting current selection workflows.

## Components

### Data Models (`portfolio_management.macro.models`)

#### MacroSeries
Represents a macroeconomic time series with metadata:
- `ticker`: Series identifier (e.g., "gdp.us", "pmi.us")
- `rel_path`: Relative path to series file in Stooq directory
- `start_date`, `end_date`: Available date range
- `region`, `category`: Classification metadata

#### RegimeConfig
Configuration for regime detection rules:
- `recession_indicator`: Optional ticker for recession indicator
- `risk_off_threshold`: Optional threshold for risk-off detection
- `enable_gating`: Whether to apply gating (default: False)
- `custom_rules`: Extensible dict for custom rules

**Validation**: Validates threshold is non-negative

### Provider (`portfolio_management.macro.provider.MacroSignalProvider`)

Loads macroeconomic series from Stooq data directories.

#### Initialization
```python
from pathlib import Path
from portfolio_management.macro import MacroSignalProvider

provider = MacroSignalProvider(Path("data/stooq"))
```

#### Locating Series
```python
# Locate single series
series = provider.locate_series("gdp.us")
if series:
    print(f"Found: {series.rel_path}")

# Locate multiple series
series_dict = provider.locate_multiple_series(["gdp.us", "pmi.us", "yield_10y.us"])
print(f"Found {len(series_dict)} series")
```

#### Loading Data
```python
# Load series data with optional date filtering
df = provider.load_series_data(
    "gdp.us",
    start_date="2020-01-01",
    end_date="2025-10-23"
)
if df is not None:
    print(f"Loaded {len(df)} rows")
```

**Path Search**: Provider searches multiple potential paths in Stooq structure:
- `data/daily/{region}/economic/{ticker}.txt`
- `data/daily/{region}/indicators/{ticker}.txt`
- `data/daily/{region}/macro/{ticker}.txt`
- Simplified variations: `{region}/economic/{ticker}.txt`, etc.

### Regime Gating (`portfolio_management.macro.regime.RegimeGate`)

Applies regime-based gating to asset selection (currently NoOp).

#### Initialization
```python
from portfolio_management.macro import RegimeConfig, RegimeGate

config = RegimeConfig(
    enable_gating=False,  # NoOp mode (default)
    recession_indicator="recession_indicator.us",
    risk_off_threshold=0.5
)

gate = RegimeGate(config)
```

#### Methods (All Currently NoOp)

**apply_gating**: Filter assets by regime (returns all assets unchanged)
```python
filtered_assets = gate.apply_gating(selected_assets, date="2025-10-23")
# Returns: same as input (NoOp)
```

**get_current_regime**: Get regime classification (returns neutral)
```python
regime = gate.get_current_regime(date="2025-10-23")
# Returns: {'recession': 'neutral', 'risk_sentiment': 'neutral', 'mode': 'noop'}
```

**filter_by_asset_class**: Filter by asset class (returns all assets unchanged)
```python
filtered = gate.filter_by_asset_class(assets, allowed_classes=["equity"])
# Returns: same as input (NoOp)
```

**adjust_selection_scores**: Adjust scores by regime (returns all scores as 1.0)
```python
scored = gate.adjust_selection_scores(assets, date="2025-10-23")
# Returns: [(asset, 1.0) for asset in assets] (neutral scores)
```

## Integration with Asset Selection

Regime configuration can be specified in `FilterCriteria`:

```python
from portfolio_management.assets.selection import FilterCriteria
from portfolio_management.macro import RegimeConfig

# Create regime config
regime_config = RegimeConfig(
    enable_gating=False,  # NoOp for now
    recession_indicator="recession_indicator.us"
)

# Include in filter criteria
criteria = FilterCriteria(
    data_status=["ok"],
    min_history_days=252,
    markets=["UK", "US"],
    regime_config=regime_config  # Ready for future logic
)
```

**Current Behavior**: Even when `regime_config` is provided, selection proceeds unchanged. This is the documented NoOp behavior.

**Future Behavior**: When regime logic is implemented, `AssetSelector` will use `RegimeGate` to:
- Filter assets by regime-appropriate asset classes
- Adjust selection scores based on macro conditions
- Apply custom gating rules defined in configuration

## Testing

Comprehensive test suite in `tests/macro/`:
- `test_models.py`: Data model validation and behavior
- `test_provider.py`: Series location and data loading
- `test_regime.py`: Regime gate NoOp behavior
- `test_selection_integration.py`: FilterCriteria integration

All tests verify NoOp behavior and document future integration points.

## Future Enhancements

When implementing actual regime logic:

1. **Regime Detection**
   - Load macro indicators via `MacroSignalProvider`
   - Implement detection rules in `RegimeGate.get_current_regime()`
   - Return actual regime classifications

2. **Asset Class Filtering**
   - Implement `filter_by_asset_class()` to exclude asset classes in risk-off regimes
   - Example: exclude equities during recession, favor bonds/cash

3. **Score Adjustment**
   - Implement `adjust_selection_scores()` to modify asset attractiveness
   - Example: reduce equity scores in risk-off, increase defensive asset scores

4. **Custom Rules**
   - Support user-defined regime rules via `custom_rules` dict
   - Allow flexible regime definitions beyond built-in indicators

5. **Integration with AssetSelector**
   - Check `criteria.regime_config` in `AssetSelector.select_assets()`
   - Apply `RegimeGate` if `config.is_enabled()` returns True
   - Log regime state and gating decisions

## Example: Future Complete Workflow

```python
from pathlib import Path
from portfolio_management.macro import MacroSignalProvider, RegimeConfig, RegimeGate
from portfolio_management.assets.selection import FilterCriteria, AssetSelector

# Initialize macro provider
provider = MacroSignalProvider(Path("data/stooq"))

# Verify macro series are available
series = provider.locate_multiple_series(["recession_indicator.us", "vix.us"])
print(f"Available macro series: {list(series.keys())}")

# Configure regime detection
regime_config = RegimeConfig(
    enable_gating=True,  # Will be active when logic is implemented
    recession_indicator="recession_indicator.us",
    risk_off_threshold=30.0  # VIX threshold
)

# Create filter criteria with regime config
criteria = FilterCriteria(
    data_status=["ok"],
    min_history_days=252,
    markets=["UK", "US"],
    regime_config=regime_config
)

# Future: AssetSelector will check regime_config and apply gating
selector = AssetSelector()
# selected = selector.select_assets(matches_df, criteria)
# ^ Will apply regime gating once implemented
```

## Notes

- **NoOp Status**: This is the documented and tested current behavior
- **Data Location**: Series must exist in Stooq data directory structure
- **Validation**: Always validate `RegimeConfig` before use
- **Performance**: Provider caches nothing currently; consider adding caching when implementing actual logic
- **Thread Safety**: Not currently thread-safe; add locking if needed for concurrent access

## See Also

- [Asset Selection](asset_selection.md) - Main selection workflow
- [Data Preparation](data_preparation.md) - Stooq data ingestion
- [Portfolio Construction](portfolio_construction.md) - How selection feeds into optimization
