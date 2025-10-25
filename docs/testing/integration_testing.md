# Integration Testing Guidelines

This document provides guidelines for writing effective integration tests that validate multiple components working together.

## What is an Integration Test?

Integration tests validate that multiple components work correctly together as a system. They differ from unit tests in that they:

- Test interactions between components
- Use real or realistic data
- May involve actual I/O operations
- Take longer to execute (seconds to minutes)
- Validate end-to-end workflows

## When to Write Integration Tests

Write integration tests when you need to:

1. **Validate component interactions**: Test that modules communicate correctly
2. **Test end-to-end workflows**: Verify complete user scenarios work
3. **Catch integration bugs**: Find issues that unit tests miss
4. **Test with real data**: Validate behavior with production-like data
5. **Verify system contracts**: Ensure APIs between components are stable

## Structure

### Test Organization

Integration tests are in `tests/integration/`:

```
tests/integration/
├── test_workflow.py                    # End-to-end workflow tests
├── test_backtest_integration.py        # Backtest component integration
├── test_portfolio_integration.py       # Portfolio construction integration
├── test_caching_edge_cases.py          # Cache system integration
└── test_long_history_comprehensive.py  # Long-term validation tests
```

### Test File Template

```python
"""Integration tests for <feature/workflow>.

Tests:
- Workflow 1: Description
- Workflow 2: Description
- Edge case: Description
"""

import pytest
from pathlib import Path


@pytest.mark.integration
class Test<Feature>Integration:
    """Integration tests for <feature>."""
    
    def test_<workflow>_end_to_end(self, tmp_path):
        """Verify <workflow> works end-to-end."""
        # Setup: Create realistic test environment
        data = create_realistic_data()
        config = create_config()
        
        # Execute: Run complete workflow
        result = execute_workflow(data, config)
        
        # Validate: Check key outcomes
        assert result.success
        assert len(result.outputs) > 0
```

## Writing Effective Integration Tests

### Test Complete Workflows

Integration tests should cover complete user scenarios:

```python
@pytest.mark.integration
def test_full_backtest_workflow(tmp_path):
    """Test complete backtest from data to results."""
    # 1. Load data
    prices = load_prices("tests/fixtures/prices.csv")
    returns = calculate_returns(prices)
    
    # 2. Configure strategy
    config = BacktestConfig(
        start_date=date(2020, 1, 1),
        end_date=date(2023, 12, 31),
        rebalance_frequency=RebalanceFrequency.MONTHLY,
        initial_capital=Decimal(100000)
    )
    
    # 3. Setup components
    preselection = Preselection(PreselectionConfig(top_k=30))
    strategy = EqualWeightStrategy()
    
    # 4. Run backtest
    engine = BacktestEngine(config, strategy, prices, returns)
    result = engine.run()
    
    # 5. Validate results
    assert result.total_return is not None
    assert len(result.rebalance_events) > 0
    assert result.sharpe_ratio > 0
    
    # 6. Generate report
    report_file = tmp_path / "backtest_report.html"
    generate_report(result, report_file)
    assert report_file.exists()
```

### Test Component Interactions

Verify that components communicate correctly:

```python
@pytest.mark.integration
def test_preselection_with_membership_policy():
    """Verify preselection and membership policy work together."""
    # Setup components
    preselection_config = PreselectionConfig(
        method=PreselectionMethod.MOMENTUM,
        top_k=30,
        lookback=252
    )
    membership_policy = MembershipPolicy(
        buffer_rank=40,
        min_holding_periods=2,
        max_turnover=0.30
    )
    
    # Generate test data
    returns = create_test_returns(n_assets=100, n_periods=1000)
    
    # First rebalance - no current holdings
    date1 = returns.index[500].date()
    selected1 = preselection.select_assets(returns[:500], date1)
    holdings1 = apply_membership_policy(
        current_holdings=[],
        preselected_ranks={asset: i for i, asset in enumerate(selected1)},
        policy=membership_policy,
        top_k=30
    )
    
    # Second rebalance - with current holdings
    date2 = returns.index[600].date()
    selected2 = preselection.select_assets(returns[:600], date2)
    holdings2 = apply_membership_policy(
        current_holdings=holdings1,
        preselected_ranks={asset: i for i, asset in enumerate(selected2)},
        policy=membership_policy,
        top_k=30,
        holding_periods={asset: 1 for asset in holdings1}
    )
    
    # Validate interactions
    assert len(holdings1) <= 30
    assert len(holdings2) <= 30
    
    # Membership policy should limit turnover
    added = set(holdings2) - set(holdings1)
    removed = set(holdings1) - set(holdings2)
    turnover = (len(added) + len(removed)) / len(holdings1)
    assert turnover <= membership_policy.max_turnover
```

### Test with Realistic Data

Use production-like data for validation:

```python
@pytest.mark.integration
def test_backtest_with_real_data_patterns():
    """Test backtest with realistic data patterns."""
    # Create data with realistic characteristics
    returns = generate_realistic_returns(
        n_assets=100,
        n_periods=1000,
        mean_return=0.0003,  # 7.5% annualized
        volatility=0.01,      # 16% annualized
        correlation=0.3       # Moderate correlation
    )
    
    # Add realistic gaps and missing data
    returns = add_random_gaps(returns, gap_probability=0.02)
    
    # Run backtest
    config = BacktestConfig(
        start_date=returns.index[0].date(),
        end_date=returns.index[-1].date(),
        rebalance_frequency=RebalanceFrequency.MONTHLY,
        use_pit_eligibility=True,
        min_history_days=252
    )
    
    strategy = RiskParityStrategy()
    prices = returns_to_prices(returns, initial_price=100)
    
    engine = BacktestEngine(config, strategy, prices, returns)
    result = engine.run()
    
    # Validate realistic outcomes
    assert -0.5 < result.total_return < 2.0  # Reasonable range
    assert 0 < result.sharpe_ratio < 3.0     # Reasonable Sharpe
    assert result.max_drawdown < 0.6          # Not catastrophic
```

### Test Error Handling

Integration tests should verify error handling across components:

```python
@pytest.mark.integration
def test_backtest_handles_insufficient_data_gracefully():
    """Verify backtest handles data issues appropriately."""
    # Create dataset with insufficient history
    returns = create_test_returns(n_assets=50, n_periods=100)
    prices = returns_to_prices(returns, initial_price=100)
    
    # Configure backtest with requirements that can't be met
    config = BacktestConfig(
        start_date=returns.index[0].date(),
        end_date=returns.index[-1].date(),
        use_pit_eligibility=True,
        min_history_days=365,  # More than available
    )
    
    strategy = EqualWeightStrategy()
    engine = BacktestEngine(config, strategy, prices, returns)
    
    # Should raise appropriate error
    with pytest.raises(InsufficientHistoryError):
        engine.run()
```

## Using Fixtures

Integration tests often need complex setup. Use fixtures:

```python
@pytest.fixture
def realistic_market_data():
    """Create realistic market data for integration tests."""
    # Load or generate comprehensive test data
    dates = pd.date_range("2015-01-01", "2023-12-31", freq="D")
    assets = [f"ASSET_{i:03d}" for i in range(200)]
    
    # Generate with realistic properties
    returns = generate_correlated_returns(
        dates=dates,
        assets=assets,
        mean=0.0003,
        vol=0.01,
        correlation_matrix=create_block_correlation_matrix(200, 0.3)
    )
    
    return {
        "returns": returns,
        "prices": returns_to_prices(returns, 100),
        "dates": dates,
        "assets": assets
    }

@pytest.fixture
def backtest_config():
    """Create standard backtest configuration."""
    return BacktestConfig(
        start_date=date(2020, 1, 1),
        end_date=date(2023, 12, 31),
        rebalance_frequency=RebalanceFrequency.MONTHLY,
        initial_capital=Decimal(100000),
        use_pit_eligibility=True,
        min_history_days=252
    )

@pytest.mark.integration
def test_with_fixtures(realistic_market_data, backtest_config):
    """Test using integration fixtures."""
    strategy = EqualWeightStrategy()
    engine = BacktestEngine(
        backtest_config,
        strategy,
        realistic_market_data["prices"],
        realistic_market_data["returns"]
    )
    
    result = engine.run()
    assert result.total_return is not None
```

## Testing Across Multiple Components

### Data Pipeline Integration

```python
@pytest.mark.integration
def test_data_pipeline_end_to_end(tmp_path):
    """Test complete data pipeline from raw to processed."""
    # 1. Setup: Create raw data files
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    create_raw_stooq_files(raw_dir, n_assets=50)
    
    # 2. Index building
    index_file = tmp_path / "index.csv"
    build_index(raw_dir, index_file)
    assert index_file.exists()
    
    # 3. Matching with brokers
    broker_files = create_broker_files(tmp_path)
    matches = match_tickers(index_file, broker_files)
    assert len(matches) > 0
    
    # 4. Data validation
    diagnostics = validate_data(raw_dir, matches)
    assert diagnostics["total_files"] == 50
    
    # 5. Export processed data
    processed_dir = tmp_path / "processed"
    export_processed_data(raw_dir, matches, processed_dir)
    assert (processed_dir / "prices.csv").exists()
    assert (processed_dir / "returns.csv").exists()
```

### Strategy Pipeline Integration

```python
@pytest.mark.integration
def test_strategy_pipeline_with_all_features():
    """Test strategy with preselection, membership, and optimization."""
    # Setup data
    returns = create_test_returns(n_assets=200, n_periods=2000)
    prices = returns_to_prices(returns, 100)
    
    # Configure all components
    preselection_config = PreselectionConfig(
        method=PreselectionMethod.COMBINED,
        top_k=50,
        momentum_weight=0.6,
        low_vol_weight=0.4
    )
    
    membership_policy = MembershipPolicy(
        buffer_rank=60,
        min_holding_periods=3,
        max_turnover=0.25
    )
    
    strategy = MeanVarianceStrategy(
        risk_aversion=1.0,
        weight_bounds=(0.01, 0.10)
    )
    
    config = BacktestConfig(
        start_date=returns.index[500].date(),
        end_date=returns.index[-1].date(),
        rebalance_frequency=RebalanceFrequency.QUARTERLY,
        use_pit_eligibility=True,
        min_history_days=252
    )
    
    # Execute full pipeline
    cache = FactorCache(Path(".cache/test"), enabled=True)
    preselection = Preselection(preselection_config, cache=cache)
    
    engine = BacktestEngine(config, strategy, prices, returns)
    engine.set_preselection(preselection)
    engine.set_membership_policy(membership_policy)
    
    result = engine.run()
    
    # Validate all features worked
    assert len(result.rebalance_events) > 0
    assert result.total_return is not None
    
    # Verify preselection was used
    for event in result.rebalance_events:
        assert len(event.new_weights) <= 50
    
    # Verify membership constraints
    cache.clear()
```

## Performance Validation

Integration tests can validate performance requirements:

```python
@pytest.mark.integration
def test_backtest_performance_acceptable():
    """Verify backtest completes in reasonable time."""
    import time
    
    # Setup realistic scenario
    returns = create_test_returns(n_assets=100, n_periods=2500)  # 10 years daily
    prices = returns_to_prices(returns, 100)
    
    config = BacktestConfig(
        start_date=returns.index[0].date(),
        end_date=returns.index[-1].date(),
        rebalance_frequency=RebalanceFrequency.MONTHLY,  # ~120 rebalances
    )
    
    strategy = EqualWeightStrategy()
    engine = BacktestEngine(config, strategy, prices, returns)
    
    # Measure execution time
    start = time.time()
    result = engine.run()
    duration = time.time() - start
    
    # Verify reasonable performance
    assert duration < 30, f"Backtest took {duration:.1f}s (expected <30s)"
    assert result is not None

@pytest.mark.integration
def test_caching_improves_performance():
    """Verify caching provides performance benefit."""
    import time
    
    returns = create_test_returns(n_assets=200, n_periods=1000)
    config = PreselectionConfig(top_k=50, lookback=252)
    
    # First run without cache
    preselection_no_cache = Preselection(config, cache=None)
    start = time.time()
    for i in range(100, 900, 100):
        date = returns.index[i].date()
        preselection_no_cache.select_assets(returns[:i], date)
    time_no_cache = time.time() - start
    
    # Second run with cache
    cache = FactorCache(Path(".cache/test"), enabled=True)
    cache.clear()
    preselection_with_cache = Preselection(config, cache=cache)
    start = time.time()
    for i in range(100, 900, 100):
        date = returns.index[i].date()
        preselection_with_cache.select_assets(returns[:i], date)
    time_with_cache = time.time() - start
    
    # Verify significant speedup on repeated dates
    cache.clear()
    start = time.time()
    for i in range(100, 900, 100):
        date = returns.index[i].date()
        preselection_with_cache.select_assets(returns[:i], date)
    time_cached_repeat = time.time() - start
    
    # Cached run should be much faster
    assert time_cached_repeat < time_no_cache * 0.5
```

## Testing Data Integrity

Verify data flows correctly through the system:

```python
@pytest.mark.integration
def test_data_integrity_through_pipeline():
    """Verify data maintains integrity through processing pipeline."""
    # Create known test data
    initial_prices = pd.DataFrame({
        "ASSET_001": [100, 105, 110, 108, 112],
        "ASSET_002": [50, 52, 51, 53, 54]
    }, index=pd.date_range("2023-01-01", periods=5, freq="D"))
    
    # Calculate returns
    returns = calculate_returns(initial_prices)
    
    # Reconstruct prices from returns
    reconstructed = returns_to_prices(returns, initial_prices.iloc[0])
    
    # Verify integrity
    pd.testing.assert_frame_equal(
        initial_prices.iloc[1:],
        reconstructed,
        atol=0.01
    )
```

## Best Practices

### DO:

✅ **Test realistic scenarios**: Use production-like data and configurations

✅ **Test component boundaries**: Verify interfaces between modules

✅ **Test error propagation**: Ensure errors flow correctly through system

✅ **Use appropriate timeouts**: Set reasonable time limits for long tests

✅ **Clean up resources**: Remove temporary files, close connections

✅ **Mark tests clearly**: Use `@pytest.mark.integration`

### DON'T:

❌ **Test everything together**: Keep tests focused on specific integration points

❌ **Skip error cases**: Integration tests should cover error scenarios

❌ **Ignore performance**: Monitor and assert on execution time

❌ **Leave artifacts**: Clean up temporary files and state

❌ **Depend on test order**: Each test should be independent

## Running Integration Tests

```bash
# Run all integration tests
pytest tests/integration/ -v

# Run specific integration test file
pytest tests/integration/test_backtest_integration.py -v

# Run integration tests excluding slow ones
pytest tests/integration/ -m "integration and not slow" -v

# Run with detailed output
pytest tests/integration/ -v -s

# Run in parallel (if tests are independent)
pytest tests/integration/ -n 4

# Run with coverage
pytest tests/integration/ --cov=src/portfolio_management
```

## Troubleshooting Integration Tests

### Common Issues

1. **Tests fail due to missing data**:
   - Ensure fixtures are properly set up
   - Check that test data files exist
   - Verify file paths are correct

2. **Tests are too slow**:
   - Reduce data size if possible
   - Mark as `@pytest.mark.slow` if necessary
   - Consider mocking expensive operations

3. **Tests fail intermittently**:
   - Check for race conditions
   - Ensure proper cleanup between tests
   - Verify no global state leakage

4. **Resource leaks**:
   - Use context managers for file operations
   - Clean up in `finally` blocks or fixtures
   - Check for open connections

## Related Documentation

- [Test Strategy](test_strategy.md) - Overall testing philosophy
- [Unit Testing](unit_testing.md) - Unit test guidelines
- [Long History Tests](long_history_tests.md) - Long-term validation
- [Testing Overview](overview.md) - Test organization
- [Troubleshooting Guide](../troubleshooting.md) - Debugging help
