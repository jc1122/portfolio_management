# Technical Indicator Filtering

## Overview

The technical indicator filtering framework provides a flexible, extensible system for incorporating technical analysis signals into the asset selection pipeline. The current implementation provides interfaces and stub implementations that prepare for future integration with technical analysis libraries like TA-Lib or ta.

## Current Status: Stub Implementation

The framework is currently implemented with **no-op (no-operation) stubs** that perform passthrough filtering. This means:

- Configuration is fully functional and validated
- All hooks and interfaces are in place
- No actual technical analysis is performed (all assets pass through)
- System is ready for future integration with real indicator libraries

## Architecture

### Core Components

1. **IndicatorProvider Interface** (`portfolio_management.analytics.indicators.IndicatorProvider`)

   - Abstract base class defining the contract for indicator computation
   - `compute(series, params) -> pd.Series` method returns indicator signals
   - Extensible for different indicator libraries

1. **NoOpIndicatorProvider** (`portfolio_management.analytics.indicators.NoOpIndicatorProvider`)

   - Stub implementation that returns all-True signals
   - Used for testing and preparation
   - Performs no actual filtering

1. **FilterHook** (`portfolio_management.analytics.indicators.FilterHook`)

   - Applies indicator-based filtering to asset lists
   - Integrates with universe configuration and backtest pipeline
   - Handles missing data and error cases gracefully

1. **IndicatorConfig** (`portfolio_management.analytics.indicators.IndicatorConfig`)

   - Configuration dataclass for indicator parameters
   - Validates provider types and parameter ranges
   - Supports enable/disable toggle

## Configuration

### Universe YAML

Technical indicators can be configured in universe definitions:

```yaml
universes:
  equity_with_indicators:
    description: "Equity sleeve with technical indicator filtering"
    filter_criteria:
      data_status: ["ok"]
      min_history_days: 756
      # ... other filter criteria ...

    # Technical indicators configuration (optional)
    technical_indicators:
      enabled: true           # Enable indicator filtering
      provider: "noop"        # Provider: 'noop', 'talib', 'ta'
      params:
        window: 20           # Rolling window for indicators
        threshold: 0.5       # Signal threshold for filtering
        # Additional provider-specific params can be added here
```

If the `technical_indicators` block is omitted, it defaults to disabled (no filtering).

### CLI Usage

The `run_backtest.py` script supports indicator configuration via command-line flags:

```bash
# Enable indicator filtering with default noop provider
python scripts/run_backtest.py equal_weight --enable-indicators

# Specify provider explicitly (currently only 'noop' supported)
python scripts/run_backtest.py risk_parity \
    --enable-indicators \
    --indicator-provider noop
```

## Extension Points

### Adding Real Indicator Implementations

To integrate actual technical analysis (e.g., RSI, MACD, moving averages):

1. **Create a new provider class**:

```python
from portfolio_management.analytics.indicators import IndicatorProvider
import talib  # or your preferred TA library

class TalibIndicatorProvider(IndicatorProvider):
    def compute(self, series: pd.Series, params: dict[str, Any]) -> pd.Series:
        """Compute RSI indicator using TA-Lib."""
        window = params.get("window", 14)
        threshold = params.get("threshold", 30.0)  # Oversold threshold

        # Compute RSI
        rsi = talib.RSI(series.values, timeperiod=window)
        rsi_series = pd.Series(rsi, index=series.index)

        # Return boolean signal: True if RSI < threshold (oversold = buy signal)
        return rsi_series < threshold
```

2. **Update configuration validation** in `config.py`:

```python
# Add 'talib' to supported providers
if self.enabled and self.provider not in ("noop", "talib", "ta"):
    raise ValueError(f"Unsupported indicator provider: {self.provider}")
```

3. **Update CLI to instantiate provider** in `run_backtest.py`:

```python
if args.indicator_provider == "noop":
    provider = NoOpIndicatorProvider()
elif args.indicator_provider == "talib":
    provider = TalibIndicatorProvider()
else:
    raise ValueError(f"Unknown provider: {args.indicator_provider}")
```

4. **Add tests** for the new provider implementation.

### Indicator Types

Future implementations can support various indicator types:

- **Trend indicators**: Moving averages (SMA, EMA), MACD, ADX
- **Momentum indicators**: RSI, Stochastic, Williams %R
- **Volatility indicators**: Bollinger Bands, ATR, Standard Deviation
- **Volume indicators**: OBV, Volume SMA, Volume Rate of Change

### Multiple Indicators

The framework can be extended to support multiple indicators:

```python
class CompositeIndicatorProvider(IndicatorProvider):
    def __init__(self, providers: list[IndicatorProvider], logic: str = "AND"):
        self.providers = providers
        self.logic = logic  # "AND" or "OR"

    def compute(self, series: pd.Series, params: dict[str, Any]) -> pd.Series:
        signals = [p.compute(series, params) for p in self.providers]

        if self.logic == "AND":
            return pd.concat(signals, axis=1).all(axis=1)
        else:  # OR
            return pd.concat(signals, axis=1).any(axis=1)
```

## Testing

### Running Tests

```bash
# Run all indicator tests
pytest tests/analytics/indicators/ -v

# Run specific test modules
pytest tests/analytics/indicators/test_providers.py -v
pytest tests/analytics/indicators/test_config.py -v
pytest tests/analytics/indicators/test_filter_hook.py -v
pytest tests/analytics/indicators/test_universe_integration.py -v
```

### Test Coverage

The test suite covers:

- NoOpIndicatorProvider behavior (passthrough signals)
- IndicatorConfig validation (providers, parameters)
- FilterHook filtering logic (inclusion/exclusion)
- Universe configuration roundtrip (YAML parsing)
- Integration with existing universe system

## API Reference

### IndicatorProvider

```python
class IndicatorProvider(ABC):
    @abstractmethod
    def compute(self, series: pd.Series, params: dict[str, Any]) -> pd.Series:
        """Compute indicator signal from price/volume series.

        Args:
            series: Price or volume time series
            params: Indicator-specific parameters

        Returns:
            Boolean or float series [0, 1] indicating signal strength
        """
```

### NoOpIndicatorProvider

```python
class NoOpIndicatorProvider(IndicatorProvider):
    def compute(self, series: pd.Series, params: dict[str, Any]) -> pd.Series:
        """Return all-True passthrough signal."""
```

### FilterHook

```python
class FilterHook:
    def __init__(self, config: IndicatorConfig, provider: IndicatorProvider):
        """Initialize filter hook."""

    def filter_assets(
        self,
        prices: pd.DataFrame,
        assets: list[str],
    ) -> list[str]:
        """Filter assets based on indicator signals.

        Returns list of assets that pass indicator filter.
        """
```

### IndicatorConfig

```python
@dataclass
class IndicatorConfig:
    enabled: bool = False
    provider: str = "noop"
    params: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        """Validate configuration."""

    @classmethod
    def disabled(cls) -> IndicatorConfig:
        """Create disabled configuration."""

    @classmethod
    def noop(cls, params: dict[str, Any] | None = None) -> IndicatorConfig:
        """Create no-op configuration."""
```

## Migration and Compatibility

### Backward Compatibility

- Existing universe configurations without `technical_indicators` continue to work
- Default behavior is disabled (no filtering)
- No breaking changes to existing APIs

### Forward Compatibility

The framework is designed to minimize changes when adding real indicators:

1. Configuration schema remains stable
1. Only provider implementations need to be swapped
1. Tests can be gradually migrated from stub to real indicators
1. CLI remains unchanged (just add more provider choices)

## Performance Considerations

### Current (Stub) Implementation

- Minimal overhead (simple boolean series creation)
- No impact on backtest performance

### Future Real Implementations

When integrating actual indicators:

1. **Caching**: Consider caching indicator computations across rebalances
1. **Vectorization**: Use vectorized TA library operations when possible
1. **Lazy Evaluation**: Compute indicators only when needed
1. **Parallelization**: Consider parallel computation for multiple assets

## Best Practices

1. **Start with no-op**: Test configuration and integration before adding real indicators
1. **Validate parameters**: Ensure indicator parameters are sensible for your data
1. **Handle missing data**: Providers should gracefully handle gaps in price data
1. **Document indicators**: Clearly document which indicators are used and why
1. **Backtest comparison**: Compare results with and without indicators to validate effectiveness

## Future Work

Potential enhancements:

- \[ \] Integration with TA-Lib for standard technical indicators
- \[ \] Support for custom indicator definitions via configuration
- \[ \] Multi-indicator composition and logic
- \[ \] Indicator signal strength (beyond binary include/exclude)
- \[ \] Rolling indicator re-evaluation during backtests
- \[ \] Indicator parameter optimization
- \[ \] Visualization of indicator signals alongside price charts

## References

- **TA-Lib**: Technical Analysis Library (https://ta-lib.org/)
- **ta (Python)**: Technical Analysis Library in Python (https://github.com/bukosabino/ta)
- **Pandas TA**: Pandas Technical Analysis (https://github.com/twopirllc/pandas-ta)
