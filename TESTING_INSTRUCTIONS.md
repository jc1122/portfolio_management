# Testing Instructions for Preselection Feature

This document describes how to test the preselection feature implementation.

## Prerequisites

Ensure all dependencies are installed:

```bash
pip install -e .
pip install -r requirements-dev.txt
```

## Running Tests

### Unit Tests

Run the preselection unit tests:

```bash
# Run all preselection tests
pytest tests/portfolio/test_preselection.py -v

# Run specific test classes
pytest tests/portfolio/test_preselection.py::TestMomentumPreselection -v
pytest tests/portfolio/test_preselection.py::TestLowVolatilityPreselection -v
pytest tests/portfolio/test_preselection.py::TestCombinedPreselection -v
pytest tests/portfolio/test_preselection.py::TestDeterminism -v
pytest tests/portfolio/test_preselection.py::TestEdgeCases -v
```

### Integration Tests

The preselection module should integrate seamlessly with existing backtests:

```bash
# Run backtest with preselection via CLI
python scripts/run_backtest.py equal_weight \
    --preselect-method momentum \
    --preselect-top-k 30 \
    --universe-name satellite_factor

# Run with combined method
python scripts/run_backtest.py mean_variance \
    --preselect-method combined \
    --preselect-top-k 25 \
    --preselect-momentum-weight 0.6 \
    --preselect-low-vol-weight 0.4
```

### Full Test Suite

Run all tests to ensure no regressions:

```bash
# Run all tests
pytest -v

# Run with coverage
pytest --cov=portfolio_management --cov-report=html

# Run only non-integration tests (faster)
pytest -m "not integration" -v
```

## Test Coverage

The test suite covers:

### Configuration & Validation
- [x] Default configuration values
- [x] Custom configuration
- [x] Invalid lookback validation
- [x] Invalid skip validation
- [x] Skip >= lookback validation
- [x] Invalid min_periods validation
- [x] Min_periods > lookback validation
- [x] Combined weights must sum to 1.0

### Momentum Preselection
- [x] Basic momentum selection
- [x] Momentum with skip period
- [x] No lookahead bias validation

### Low-Volatility Preselection
- [x] Basic low-vol selection
- [x] Preference for low volatility assets

### Combined Preselection
- [x] Basic combined selection
- [x] Different weight combinations

### Determinism
- [x] Deterministic repeated selection
- [x] Alphabetic tie-breaking

### Edge Cases
- [x] Insufficient data handling
- [x] Top-K > num assets
- [x] Top-K = None (disabled)
- [x] Top-K = 0 (disabled)
- [x] All NaN returns
- [x] Partial NaN returns

### Dictionary Configuration
- [x] Create from dict (momentum)
- [x] Create from dict (combined)
- [x] Disabled preselection (None/0)
- [x] Invalid method raises error
- [x] Defaults applied

### Integration
- [x] Reduces universe size before optimization
- [x] Works with BacktestEngine
- [x] Works with universe YAML configs

## Expected Test Results

All tests should pass. Specific validations:

1. **No Lookahead**: Verify preselection only uses data before rebalance date
2. **Determinism**: Same inputs produce same outputs every time
3. **Tie-Breaking**: Ties broken alphabetically by asset symbol
4. **Factor Computation**: Momentum and volatility computed correctly
5. **Edge Cases**: Graceful handling of insufficient data, NaN values, etc.

## Manual Verification

### 1. CLI Integration

Test that CLI flags work:

```bash
# Should show help with preselection options
python scripts/run_backtest.py --help | grep preselect
```

Expected output should include:
```
  --preselect-method {momentum,low_vol,combined}
  --preselect-top-k PRESELECT_TOP_K
  --preselect-lookback PRESELECT_LOOKBACK
  --preselect-skip PRESELECT_SKIP
  --preselect-momentum-weight PRESELECT_MOMENTUM_WEIGHT
  --preselect-low-vol-weight PRESELECT_LOW_VOL_WEIGHT
```

### 2. Universe YAML

Verify universe config loads preselection:

```python
from pathlib import Path
from portfolio_management.assets.universes import UniverseConfigLoader

loader = UniverseConfigLoader()
universes = loader.load_config(Path("config/universes.yaml"))

# Check satellite_factor has preselection
universe = universes["satellite_factor"]
assert universe.preselection is not None
assert universe.preselection["method"] == "combined"
assert universe.preselection["top_k"] == 25
print("✓ Universe YAML preselection config loaded correctly")
```

### 3. BacktestEngine Integration

Verify preselection integrates with backtesting:

```python
import datetime
import pandas as pd
from decimal import Decimal
from portfolio_management.backtesting import BacktestEngine, BacktestConfig, RebalanceFrequency
from portfolio_management.portfolio import (
    EqualWeightStrategy,
    Preselection,
    PreselectionConfig,
    PreselectionMethod,
)

# Create sample data
dates = pd.date_range("2020-01-01", "2020-12-31", freq="D")
assets = [f"ASSET_{i}" for i in range(50)]
prices = pd.DataFrame(
    100 + pd.np.random.randn(len(dates), len(assets)).cumsum(axis=0),
    index=dates,
    columns=assets,
)
returns = prices.pct_change().fillna(0)

# Configure preselection
preselection_config = PreselectionConfig(
    method=PreselectionMethod.MOMENTUM,
    top_k=10,
    lookback=60,
)
preselection = Preselection(preselection_config)

# Run backtest
config = BacktestConfig(
    start_date=datetime.date(2020, 6, 1),
    end_date=datetime.date(2020, 12, 31),
    initial_capital=Decimal(100000),
    rebalance_frequency=RebalanceFrequency.MONTHLY,
)

engine = BacktestEngine(
    config=config,
    strategy=EqualWeightStrategy(),
    prices=prices,
    returns=returns,
    preselection=preselection,
)

equity_curve, metrics, events = engine.run()
print("✓ BacktestEngine with preselection completed successfully")
print(f"  Final equity: {equity_curve['equity'].iloc[-1]:.2f}")
print(f"  Rebalances: {len(events)}")
```

## Troubleshooting

### Import Errors

If you see `ModuleNotFoundError: No module named 'portfolio_management'`:

```bash
# Install package in development mode
pip install -e .
```

### Test Failures

If tests fail:

1. Check that data fixtures are properly set up
2. Verify pandas/numpy versions are compatible
3. Run tests with `-vv` for verbose output
4. Check for random seed issues (tests use seed=42)

### Performance Issues

If tests are slow:

1. Reduce test data size in fixtures
2. Skip integration tests: `pytest -m "not integration"`
3. Use parallel execution: `pytest -n auto`

## Success Criteria

✅ All unit tests pass (100% pass rate)
✅ No regressions in existing tests
✅ CLI flags work as documented
✅ Universe YAML parsing works
✅ BacktestEngine integration works
✅ No lookahead bias confirmed
✅ Deterministic behavior confirmed
✅ Documentation is clear and accurate

## Next Steps After Testing

Once all tests pass:

1. Update memory bank with completion status
2. Create PR with test results
3. Request code review
4. Merge to main branch
