# Test Strategy and Guidelines

This document outlines the testing philosophy, best practices, and guidelines for the portfolio management system.

## Testing Philosophy

### Core Principles

1. **Comprehensive Coverage**: Maintain 80%+ overall coverage, 90%+ for core modules
2. **Test Isolation**: Each test should be independent and deterministic
3. **Fast Feedback**: Unit tests should run in seconds, integration tests in minutes
4. **Real-World Validation**: Integration tests use production-like data
5. **Continuous Verification**: Tests run on every commit and PR

### Test Pyramid

```
        /\
       /  \     E2E Tests (Few)
      /----\    Integration Tests (Some)
     /------\   Unit Tests (Many)
    /--------\  
```

- **Unit Tests** (70%): Fast, isolated, mock dependencies
- **Integration Tests** (25%): Multiple components, real data
- **End-to-End Tests** (5%): Full workflow, production-like scenarios

## Test Categories

### Unit Tests

**Purpose**: Test individual functions and classes in isolation

**Characteristics**:
- Fast execution (< 1 second per test)
- Mock external dependencies
- Test single responsibility
- Cover edge cases and error handling

**Example**:
```python
def test_preselection_top_k_validation():
    """Validate that top_k parameter must be positive."""
    with pytest.raises(ValueError, match="top_k must be >= 0"):
        PreselectionConfig(top_k=-5)
```

**Best Practices**:
- Use descriptive names: `test_<function>_<scenario>_<expected_result>`
- One assertion per test (when possible)
- Test both success and failure paths
- Use fixtures for common setup
- Mock expensive operations (file I/O, network)

### Integration Tests

**Purpose**: Test multiple components working together

**Characteristics**:
- Moderate execution time (seconds to minutes)
- Use real or realistic data
- Test component interactions
- Validate end-to-end workflows

**Example**:
```python
@pytest.mark.integration
def test_backtest_with_preselection_and_membership():
    """Test full backtest with preselection and membership policy."""
    # Setup real data
    prices = load_prices("test_data.csv")
    returns = calculate_returns(prices)
    
    # Configure components
    preselection = Preselection(config=preselection_config)
    policy = MembershipPolicy(buffer_rank=40, top_k=30)
    engine = BacktestEngine(config, strategy, prices, returns)
    
    # Run backtest
    result = engine.run()
    
    # Validate results
    assert result.total_return > 0
    assert len(result.rebalance_events) > 0
```

**Best Practices**:
- Mark with `@pytest.mark.integration`
- Use realistic data sizes
- Test common workflows
- Validate key metrics
- Check for performance regressions

### Long-History Tests

**Purpose**: Validate system with extensive historical data (20 years)

**Characteristics**:
- Long execution time (minutes to hours)
- Use production-scale data
- Test determinism and backward compatibility
- Validate across market regimes

**Example**:
```python
@pytest.mark.slow
@pytest.mark.integration
def test_equal_weight_20_years():
    """Test equal-weight strategy over 20 years (2005-2025)."""
    config = BacktestConfig(
        start_date=date(2005, 1, 1),
        end_date=date(2024, 12, 31),
        rebalance_frequency=RebalanceFrequency.MONTHLY,
    )
    
    result = run_backtest(config, EqualWeightStrategy(), prices, returns)
    
    # Validate stability
    assert result.sharpe_ratio > 0.5
    assert result.max_drawdown < 0.6
    assert len(result.rebalance_events) > 200
```

**Best Practices**:
- Mark with `@pytest.mark.slow`
- Run in nightly builds, not on every commit
- Test determinism (multiple runs produce identical results)
- Validate across different market conditions
- Check for memory leaks

## Coverage Requirements

### Overall Coverage
- **Target**: 80%+ overall
- **Minimum**: 75% to pass CI
- **Exceptions**: Optional features, UI code, scaffolding

### Critical Modules
- **Core utilities**: 90%+ required
- **Asset selection**: 90%+ required
- **Portfolio construction**: 90%+ required
- **Backtesting engine**: 90%+ required
- **Returns calculation**: 85%+ required

### New Features
- All new features must include tests
- Minimum 85% coverage for new code
- Integration tests for user-facing features
- Performance tests for optimization-critical code

## Test Organization

### Structure

Tests mirror the production package structure:

```
src/portfolio_management/
├── core/              →  tests/core/
├── data/              →  tests/data/
├── assets/            →  tests/assets/
├── analytics/         →  tests/analytics/
├── portfolio/         →  tests/portfolio/
├── backtesting/       →  tests/backtesting/
└── reporting/         →  tests/reporting/
```

### Naming Conventions

**Test Files**:
- `test_<module>.py` - Unit tests for module
- `test_<module>_integration.py` - Integration tests

**Test Functions**:
- `test_<function>_<scenario>` - Basic pattern
- `test_<function>_<scenario>_<expected_result>` - Detailed
- `test_<class>_<method>_<scenario>` - Class methods

**Examples**:
```python
# Good names
test_preselection_momentum_method_returns_ranked_assets()
test_backtest_engine_raises_error_on_empty_prices()
test_membership_policy_respects_max_turnover()

# Poor names
test_preselection()  # Too vague
test_it_works()  # Not descriptive
test_case_1()  # No context
```

## Test Writing Guidelines

### Arrange-Act-Assert Pattern

```python
def test_example():
    # Arrange: Set up test data and dependencies
    config = PreselectionConfig(top_k=30, lookback=252)
    returns = create_test_returns(100, 1000)
    
    # Act: Execute the code under test
    result = preselect_assets(config, returns, date(2023, 12, 31))
    
    # Assert: Verify expected outcomes
    assert len(result) == 30
    assert all(asset in returns.columns for asset in result)
```

### Edge Cases and Error Handling

Always test:
- Empty inputs
- None/null values
- Boundary conditions
- Invalid parameters
- Error conditions
- Resource exhaustion

```python
def test_preselection_edge_cases():
    """Test preselection with edge case inputs."""
    config = PreselectionConfig(top_k=30)
    
    # Empty DataFrame
    with pytest.raises(ValueError, match="empty"):
        preselect_assets(config, pd.DataFrame(), date.today())
    
    # Date out of range
    returns = create_test_returns(100, 1000)
    max_date = returns.index.max().date()
    future_date = max_date + timedelta(days=100)
    with pytest.raises(ValueError, match="after"):
        preselect_assets(config, returns, future_date)
```

### Parametrized Tests

Use `@pytest.mark.parametrize` for multiple scenarios:

```python
@pytest.mark.parametrize("top_k,expected_count", [
    (10, 10),
    (30, 30),
    (50, 50),
    (100, 100),
])
def test_preselection_respects_top_k(top_k, expected_count):
    """Verify preselection returns exactly top_k assets."""
    config = PreselectionConfig(top_k=top_k)
    returns = create_test_returns(200, 1000)
    result = preselect_assets(config, returns, date(2023, 12, 31))
    assert len(result) == expected_count
```

### Fixtures

Use fixtures for common setup:

```python
@pytest.fixture
def sample_returns():
    """Create sample returns DataFrame for testing."""
    dates = pd.date_range("2020-01-01", "2023-12-31", freq="D")
    assets = [f"ASSET_{i:03d}" for i in range(100)]
    data = np.random.randn(len(dates), len(assets)) * 0.01
    return pd.DataFrame(data, index=dates, columns=assets)

def test_with_fixture(sample_returns):
    """Test using fixture."""
    assert len(sample_returns) > 1000
    assert len(sample_returns.columns) == 100
```

## Performance Testing

### Benchmarks

Create benchmarks for performance-critical code:

```python
def test_preselection_performance_1000_assets(benchmark):
    """Benchmark preselection with 1000 assets."""
    config = PreselectionConfig(top_k=50)
    returns = create_test_returns(1000, 1000)
    
    result = benchmark(preselect_assets, config, returns, date(2023, 12, 31))
    
    assert len(result) == 50
```

### Performance Regressions

Set thresholds for acceptable performance:

```python
def test_backtest_completes_within_time_limit():
    """Verify backtest completes in reasonable time."""
    import time
    
    start = time.time()
    result = run_backtest(config, strategy, prices, returns)
    duration = time.time() - start
    
    # Should complete in under 5 minutes for 10-year monthly backtest
    assert duration < 300, f"Backtest took {duration:.1f}s (>300s limit)"
```

## Mocking and Test Doubles

### When to Mock

Mock external dependencies:
- File I/O operations
- Network requests
- Database queries
- Expensive computations
- Non-deterministic operations (random, time)

### Mocking Examples

```python
from unittest.mock import Mock, patch, MagicMock

def test_with_mock_file_io():
    """Test with mocked file operations."""
    mock_data = pd.DataFrame({"ASSET_001": [1.0, 1.1, 1.2]})
    
    with patch("pandas.read_csv", return_value=mock_data):
        result = load_prices("dummy.csv")
        assert len(result) == 3

def test_with_mock_cache():
    """Test with mocked cache."""
    mock_cache = Mock()
    mock_cache.get.return_value = None  # Cache miss
    
    preselection = Preselection(config, cache=mock_cache)
    result = preselection.select_assets(returns, date.today())
    
    mock_cache.get.assert_called_once()
    mock_cache.put.assert_called_once()
```

## Test Markers

Use pytest markers for categorization:

```python
# Integration test
@pytest.mark.integration
def test_full_workflow():
    pass

# Slow test (skip in quick runs)
@pytest.mark.slow
def test_long_backtest():
    pass

# Requires optional dependency
@pytest.mark.skipif(not HAVE_CVXPY, reason="Requires cvxpy")
def test_mean_variance():
    pass

# Parametrized test
@pytest.mark.parametrize("param", [1, 2, 3])
def test_with_params(param):
    pass
```

Run specific markers:
```bash
pytest -m integration          # Only integration tests
pytest -m "not slow"           # Skip slow tests
pytest -m "not integration"    # Only unit tests
```

## Continuous Integration

### Pre-commit Checks

Before every commit:
1. Run unit tests: `pytest tests/ -m "not integration"`
2. Check coverage: `pytest --cov=src/portfolio_management`
3. Run linters: `ruff check`, `mypy`
4. Format code: `black`, `isort`

### Pull Request Checks

On every PR:
1. All tests (except slow): `pytest tests/ -m "not slow"`
2. Coverage report
3. Linting and type checking
4. Documentation build

### Nightly Builds

Every night:
1. Full test suite including slow tests
2. Long-history integration tests
3. Performance benchmarks
4. Memory profiling

## Common Patterns

### Testing Exceptions

```python
def test_raises_specific_exception():
    """Test that specific exception is raised."""
    with pytest.raises(ValueError, match="top_k must be"):
        PreselectionConfig(top_k=-1)

def test_raises_any_exception():
    """Test that any exception is raised."""
    with pytest.raises(Exception):
        risky_operation()
```

### Testing Warnings

```python
def test_emits_warning():
    """Test that warning is emitted."""
    with pytest.warns(UserWarning, match="small"):
        PreselectionConfig(top_k=5)
```

### Testing Logs

```python
def test_logs_message(caplog):
    """Test that message is logged."""
    with caplog.at_level(logging.INFO):
        run_operation()
    
    assert "Processing complete" in caplog.text
```

### Testing Output

```python
def test_prints_output(capsys):
    """Test that output is printed."""
    print_summary(result)
    
    captured = capsys.readouterr()
    assert "Total Return" in captured.out
```

## Documentation in Tests

### Test Docstrings

Every test should have a docstring:

```python
def test_membership_policy_respects_constraints():
    """Verify membership policy enforces turnover and count constraints.
    
    This test ensures that:
    1. New asset count doesn't exceed max_new_assets
    2. Removed asset count doesn't exceed max_removed_assets
    3. Total turnover doesn't exceed max_turnover
    4. Holdings respect min_holding_periods
    """
    # Test implementation
```

### Comments for Complex Logic

```python
def test_complex_scenario():
    """Test complex edge case."""
    # Setup: Create dataset with specific gap pattern
    # Day 1-10: Asset present
    # Day 11-20: Asset missing (gap)
    # Day 21-30: Asset returns
    returns = create_gapped_returns(gap_start=11, gap_end=20)
    
    # Act: Compute eligibility should handle gap correctly
    eligible = compute_eligibility(returns, min_history=30)
    
    # Assert: Asset should be ineligible due to gap
    assert "GAPPED_ASSET" not in eligible
```

## Troubleshooting Test Failures

### Common Issues

1. **Flaky tests**: Tests that sometimes pass, sometimes fail
   - Cause: Non-deterministic behavior (random, time, order)
   - Solution: Seed random generators, mock time, sort collections

2. **Test pollution**: Tests affect each other
   - Cause: Shared state, global variables, file artifacts
   - Solution: Use fixtures with proper cleanup, isolate tests

3. **Slow tests**: Tests take too long
   - Cause: Real I/O, large datasets, complex computations
   - Solution: Mock expensive ops, reduce data size, mark as slow

4. **Data-dependent failures**: Tests fail with different data
   - Cause: Hardcoded assumptions, insufficient data
   - Solution: Generate deterministic test data, test edge cases

### Debugging Tests

```bash
# Run single test with verbose output
pytest tests/test_file.py::test_function -v -s

# Run with pdb debugger on failure
pytest tests/test_file.py --pdb

# Print full diff on assertion failure
pytest tests/test_file.py -vv

# Show local variables on failure
pytest tests/test_file.py -l
```

## Related Documentation

- [Testing Overview](overview.md) - Test organization
- [Unit Testing](unit_testing.md) - Unit test guidelines
- [Integration Testing](integration_testing.md) - Integration patterns
- [Long History Tests](long_history_tests.md) - Long-term validation
- [Troubleshooting Guide](../troubleshooting.md) - Debugging help
