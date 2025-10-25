# Unit Testing Guidelines

This document provides guidelines and examples for writing effective unit tests in the portfolio management system.

## What is a Unit Test?

A unit test validates a single "unit" of code (function, method, or class) in isolation from its dependencies. Unit tests should be:

- **Fast**: Execute in milliseconds
- **Isolated**: Independent of other tests
- **Deterministic**: Same input always produces same output
- **Focused**: Test one thing at a time

## Structure

### Test Organization

Unit tests are organized to mirror the production code structure:

```
src/portfolio_management/
├── assets/selection.py     →  tests/assets/test_selection.py
├── portfolio/strategies.py →  tests/portfolio/test_strategies.py
├── backtesting/engine.py   →  tests/backtesting/test_engine.py
```

### Test File Template

```python
"""Unit tests for <module_name>.

This module tests:
- Function 1: Description
- Function 2: Description
- Class: Description
"""

import pytest
from portfolio_management.<module> import <functions/classes>


class Test<ClassName>:
    """Tests for <ClassName>."""
    
    def test_<method>_<scenario>(self):
        """Verify <method> <expected_behavior> when <scenario>."""
        # Arrange
        instance = ClassName(param=value)
        
        # Act
        result = instance.method(input)
        
        # Assert
        assert result == expected


def test_<function>_<scenario>():
    """Verify <function> <expected_behavior> when <scenario>."""
    # Arrange
    input_data = create_input()
    
    # Act
    result = function(input_data)
    
    # Assert
    assert result == expected
```

## Writing Effective Tests

### Arrange-Act-Assert (AAA) Pattern

Every test should follow the AAA pattern:

```python
def test_preselection_selects_top_k_assets():
    """Verify preselection returns exactly top_k assets."""
    # Arrange: Setup test data and configuration
    config = PreselectionConfig(
        method=PreselectionMethod.MOMENTUM,
        top_k=30,
        lookback=252
    )
    returns = create_test_returns(n_assets=100, n_periods=500)
    rebalance_date = returns.index[-1].date()
    
    # Act: Execute the function under test
    selected = select_assets(config, returns, rebalance_date)
    
    # Assert: Verify expected outcomes
    assert len(selected) == 30
    assert all(asset in returns.columns for asset in selected)
```

### Testing Success Paths

Test the expected behavior with valid inputs:

```python
def test_calculate_returns_with_valid_prices():
    """Verify return calculation with valid price data."""
    # Create sample prices
    prices = pd.Series([100, 102, 101, 105], name="ASSET")
    
    # Calculate returns
    returns = calculate_returns(prices)
    
    # Verify results
    assert len(returns) == 3  # One less than prices
    assert returns.iloc[0] == pytest.approx(0.02)  # (102-100)/100
    assert returns.iloc[1] == pytest.approx(-0.0098, abs=0.0001)  # (101-102)/102
    assert returns.iloc[2] == pytest.approx(0.0396, abs=0.0001)  # (105-101)/101
```

### Testing Error Paths

Test that errors are raised appropriately:

```python
def test_preselection_raises_on_negative_top_k():
    """Verify ValueError is raised when top_k is negative."""
    with pytest.raises(ValueError, match="top_k must be >= 0"):
        PreselectionConfig(top_k=-5)

def test_backtest_raises_on_empty_prices():
    """Verify exception when prices DataFrame is empty."""
    config = BacktestConfig(start_date=date(2020, 1, 1), end_date=date(2023, 12, 31))
    strategy = EqualWeightStrategy()
    empty_prices = pd.DataFrame()
    returns = pd.DataFrame()
    
    with pytest.raises(ValueError, match="empty"):
        BacktestEngine(config, strategy, empty_prices, returns)
```

### Testing Edge Cases

Always test boundary conditions and edge cases:

```python
def test_preselection_with_exactly_top_k_assets():
    """Verify behavior when universe size equals top_k."""
    config = PreselectionConfig(top_k=50)
    # Create exactly 50 assets
    returns = create_test_returns(n_assets=50, n_periods=500)
    
    selected = select_assets(config, returns, returns.index[-1].date())
    
    # Should return all 50 assets
    assert len(selected) == 50
    assert set(selected) == set(returns.columns)

def test_preselection_with_fewer_than_top_k_assets():
    """Verify behavior when universe size is less than top_k."""
    config = PreselectionConfig(top_k=50)
    # Create only 30 assets
    returns = create_test_returns(n_assets=30, n_periods=500)
    
    selected = select_assets(config, returns, returns.index[-1].date())
    
    # Should return all 30 available assets
    assert len(selected) == 30

def test_membership_policy_with_zero_current_holdings():
    """Verify policy works with empty current portfolio."""
    policy = MembershipPolicy(buffer_rank=40, top_k=30)
    current_holdings = []  # Empty portfolio
    preselected_ranks = {f"ASSET_{i:03d}": i+1 for i in range(50)}
    
    new_holdings = apply_membership_policy(
        current_holdings, preselected_ranks, policy, top_k=30
    )
    
    # Should select top 30 from preselected
    assert len(new_holdings) == 30
```

## Parametrized Tests

Use `@pytest.mark.parametrize` to test multiple scenarios efficiently:

```python
@pytest.mark.parametrize("top_k,expected", [
    (10, 10),
    (30, 30),
    (50, 50),
    (100, 100),
])
def test_preselection_respects_top_k_parameter(top_k, expected):
    """Verify preselection returns exactly top_k assets."""
    config = PreselectionConfig(top_k=top_k)
    returns = create_test_returns(n_assets=200, n_periods=500)
    
    selected = select_assets(config, returns, returns.index[-1].date())
    
    assert len(selected) == expected

@pytest.mark.parametrize("method", [
    PreselectionMethod.MOMENTUM,
    PreselectionMethod.LOW_VOL,
    PreselectionMethod.COMBINED,
])
def test_preselection_methods_return_valid_results(method):
    """Verify all preselection methods work correctly."""
    config = PreselectionConfig(method=method, top_k=30)
    returns = create_test_returns(n_assets=100, n_periods=500)
    
    selected = select_assets(config, returns, returns.index[-1].date())
    
    assert len(selected) == 30
    assert all(asset in returns.columns for asset in selected)
```

## Using Fixtures

Fixtures provide reusable test setup:

```python
@pytest.fixture
def sample_returns():
    """Create sample returns DataFrame for testing."""
    dates = pd.date_range("2020-01-01", "2023-12-31", freq="D")
    n_assets = 100
    assets = [f"ASSET_{i:03d}" for i in range(n_assets)]
    
    # Generate random returns
    np.random.seed(42)  # For reproducibility
    data = np.random.randn(len(dates), n_assets) * 0.01
    
    return pd.DataFrame(data, index=dates, columns=assets)

@pytest.fixture
def preselection_config():
    """Create standard preselection config for testing."""
    return PreselectionConfig(
        method=PreselectionMethod.MOMENTUM,
        top_k=30,
        lookback=252,
        skip=21
    )

def test_with_fixtures(sample_returns, preselection_config):
    """Test using fixtures."""
    selected = select_assets(
        preselection_config,
        sample_returns,
        sample_returns.index[-1].date()
    )
    
    assert len(selected) == 30
```

## Mocking External Dependencies

Use mocks to isolate the code under test:

```python
from unittest.mock import Mock, patch, MagicMock

def test_preselection_uses_cache():
    """Verify preselection attempts to use cache."""
    mock_cache = Mock()
    mock_cache.get.return_value = None  # Simulate cache miss
    
    config = PreselectionConfig(top_k=30)
    preselection = Preselection(config, cache=mock_cache)
    returns = create_test_returns(100, 500)
    
    result = preselection.select_assets(returns, date(2023, 12, 31))
    
    # Verify cache was checked and updated
    mock_cache.get.assert_called_once()
    mock_cache.put.assert_called_once()
    assert len(result) == 30

def test_loads_data_from_file():
    """Test data loading with mocked file I/O."""
    mock_data = pd.DataFrame({
        "ASSET_001": [100, 101, 102],
        "ASSET_002": [200, 201, 202]
    })
    
    with patch("pandas.read_csv", return_value=mock_data):
        result = load_prices("dummy_path.csv")
        
        assert result.equals(mock_data)
```

## Testing Numerical Computations

Use appropriate tolerances for floating-point comparisons:

```python
def test_sharpe_ratio_calculation():
    """Verify Sharpe ratio calculation."""
    returns = pd.Series([0.01, 0.02, -0.01, 0.015, 0.005])
    risk_free_rate = 0.02 / 252  # Daily risk-free rate
    
    sharpe = calculate_sharpe_ratio(returns, risk_free_rate)
    
    # Use pytest.approx for floating-point comparison
    expected = 0.5123  # Pre-calculated expected value
    assert sharpe == pytest.approx(expected, abs=0.01)

def test_portfolio_weights_sum_to_one():
    """Verify portfolio weights sum to 1.0."""
    strategy = EqualWeightStrategy()
    assets = ["ASSET_001", "ASSET_002", "ASSET_003"]
    
    weights = strategy.compute_weights(assets)
    
    # Allow small floating-point error
    assert sum(weights.values()) == pytest.approx(1.0, abs=1e-10)
```

## Testing DataFrames

Use pandas testing utilities:

```python
import pandas.testing as pd_testing

def test_returns_calculation_dataframe():
    """Test return calculation for DataFrame."""
    prices = pd.DataFrame({
        "ASSET_001": [100, 110, 105],
        "ASSET_002": [50, 52, 51]
    })
    
    returns = calculate_returns(prices)
    
    expected = pd.DataFrame({
        "ASSET_001": [0.10, -0.0455],
        "ASSET_002": [0.04, -0.0192]
    })
    
    # Use pandas testing for DataFrame comparison
    pd_testing.assert_frame_equal(returns, expected, atol=0.01)
```

## Testing with Temporary Files

Use pytest's `tmp_path` fixture for file operations:

```python
def test_save_and_load_universe(tmp_path):
    """Test saving and loading universe configuration."""
    # Create test universe
    universe = Universe(
        name="test_universe",
        assets=["ASSET_001", "ASSET_002"],
        description="Test universe"
    )
    
    # Save to temporary file
    file_path = tmp_path / "universe.yaml"
    save_universe(universe, file_path)
    
    # Load and verify
    loaded = load_universe(file_path)
    assert loaded.name == universe.name
    assert loaded.assets == universe.assets
```

## Testing Async Code

If you have asynchronous code, use pytest-asyncio:

```python
@pytest.mark.asyncio
async def test_async_data_fetch():
    """Test asynchronous data fetching."""
    fetcher = AsyncDataFetcher()
    
    result = await fetcher.fetch_prices("ASSET_001")
    
    assert result is not None
    assert len(result) > 0
```

## Common Anti-Patterns to Avoid

### ❌ Testing Multiple Things

```python
# Bad: Tests multiple unrelated things
def test_everything():
    assert preselect_assets(...) == expected_selection
    assert calculate_returns(...) == expected_returns
    assert create_portfolio(...) == expected_weights
```

### ✅ Separate Focused Tests

```python
# Good: Each test has single responsibility
def test_preselection_returns_top_k():
    assert len(preselect_assets(...)) == 30

def test_returns_calculation_accuracy():
    assert calculate_returns(...) == expected_returns

def test_portfolio_weights_valid():
    assert sum(create_portfolio(...).values()) == pytest.approx(1.0)
```

### ❌ Implicit Dependencies

```python
# Bad: Test depends on test execution order
def test_step_1():
    global state
    state = initialize()

def test_step_2():  # Depends on test_step_1
    result = process(state)
```

### ✅ Isolated Tests

```python
# Good: Each test is independent
def test_step_1():
    state = initialize()
    assert state is not None

def test_step_2():
    state = initialize()  # Create own state
    result = process(state)
    assert result is not None
```

### ❌ Testing Implementation Details

```python
# Bad: Tests internal implementation
def test_uses_specific_algorithm():
    selector = AssetSelector()
    assert selector._internal_cache == {}  # Testing private attribute
```

### ✅ Testing Behavior

```python
# Good: Tests public interface and behavior
def test_selection_is_cached():
    selector = AssetSelector()
    
    # First call
    result1 = selector.select(data, date1)
    
    # Second call with same inputs should use cache
    result2 = selector.select(data, date1)
    
    assert result1 == result2
    # Verify caching through behavior, not implementation
```

## Best Practices Checklist

- [ ] Test follows AAA pattern (Arrange, Act, Assert)
- [ ] Test name clearly describes what is being tested
- [ ] Test is fast (< 100ms)
- [ ] Test is deterministic (no randomness unless seeded)
- [ ] Test is isolated (doesn't depend on other tests)
- [ ] Both success and failure paths tested
- [ ] Edge cases and boundaries tested
- [ ] Appropriate assertions used (exact match, approx, raises)
- [ ] Test has clear docstring explaining purpose
- [ ] External dependencies are mocked
- [ ] Test data is minimal but sufficient

## Running Unit Tests

```bash
# Run all unit tests (exclude integration)
pytest tests/ -m "not integration"

# Run specific test file
pytest tests/assets/test_selection.py

# Run specific test
pytest tests/assets/test_selection.py::test_preselection_top_k

# Run with coverage
pytest tests/ -m "not integration" --cov=src/portfolio_management

# Run in parallel
pytest tests/ -m "not integration" -n auto

# Run with verbose output
pytest tests/ -m "not integration" -v

# Run and stop on first failure
pytest tests/ -m "not integration" -x
```

## Related Documentation

- [Test Strategy](test_strategy.md) - Overall testing philosophy
- [Integration Testing](integration_testing.md) - Integration test guidelines
- [Testing Overview](overview.md) - Test organization
- [Troubleshooting Guide](../troubleshooting.md) - Debugging help
