"""Documentation for portfolio statistics caching.

## Overview

The `RollingStatistics` class provides efficient caching of covariance matrices and
expected returns for portfolio construction strategies. This is particularly beneficial
when running monthly or quarterly rebalances where the data window has significant
overlap between periods.

## When to Use Caching

Caching is most effective when:

1. **High Data Overlap**: Monthly rebalances with a 252-day window have ~92% overlap
1. **Large Universes**: 300+ assets where covariance computation is expensive
1. **Multiple Strategies**: Running several strategies on the same data
1. **Complex Optimization**: Risk parity or mean-variance with iterative solvers

## Usage Examples

### Basic Usage

```python
from portfolio_management.portfolio.statistics import RollingStatistics
from portfolio_management.portfolio.strategies import RiskParityStrategy
from portfolio_management.portfolio.constraints.models import PortfolioConstraints

# Create a statistics cache
cache = RollingStatistics(window_size=252, annualization_factor=252)

# Create strategy with cache enabled
strategy = RiskParityStrategy(min_periods=252, statistics_cache=cache)

# Construct portfolio - first call populates cache
constraints = PortfolioConstraints()
portfolio1 = strategy.construct(returns_month1, constraints)

# Second call reuses cached statistics (if data overlaps)
portfolio2 = strategy.construct(returns_month2, constraints)
```

### Multiple Strategies Sharing Cache

```python
# Create a shared cache
cache = RollingStatistics(window_size=252)

# Multiple strategies can share the same cache
rp_strategy = RiskParityStrategy(min_periods=252, statistics_cache=cache)
mv_strategy = MeanVarianceStrategy(
    objective="max_sharpe",
    min_periods=252,
    statistics_cache=cache,
)

# Both strategies benefit from cached statistics
rp_portfolio = rp_strategy.construct(returns, constraints)
mv_portfolio = mv_strategy.construct(returns, constraints)
```

### Manual Cache Control

```python
cache = RollingStatistics()

# Get statistics explicitly
mean_returns, cov_matrix = cache.get_statistics(returns, annualize=True)

# Manually invalidate cache if needed
cache.invalidate_cache()

# Next call will recompute
mean_returns, cov_matrix = cache.get_statistics(returns, annualize=True)
```

## Cache Behavior

### Cache Key

The cache key is computed based on:

- Data shape (number of rows and columns)
- Column names (asset tickers)
- Date range (first and last dates)

### Automatic Invalidation

The cache is automatically invalidated when:

- The asset set changes (different tickers)
- The number of periods changes
- The date range shifts (rolling window moves forward)

### Cache Safety

The cache includes safety checks to ensure:

- Data integrity (shape and columns match)
- Numerical consistency (sample data points match)
- No stale data is returned

## Performance Considerations

### When Caching Helps

Caching provides the most benefit when:

1. **Monthly Rebalances with 1-Year Window**

   - Overlap: ~92% (231/252 days)
   - Cache hit on every rebalance after the first

1. **Large Universes**

   - 300+ assets: O(n²) covariance computation
   - Significant time saved on each rebalance

1. **Iterative Optimization**

   - Risk parity: Multiple optimizer iterations
   - Mean-variance: Multiple attempts with different parameters

### When Caching Doesn't Help

Caching provides little benefit when:

1. **No Data Overlap**

   - Different time periods
   - Different asset sets
   - Non-overlapping windows

1. **Small Universes**

   - \<50 assets: Statistics computation is already fast
   - Cache overhead may dominate

1. **One-Time Construction**

   - No repeated computations
   - No rebalancing

## Implementation Notes

### Thread Safety

The current implementation is not thread-safe. If you need to use caching in a
multi-threaded environment, create separate cache instances for each thread.

### Memory Usage

The cache stores:

- Full returns DataFrame (copied)
- Covariance matrix (n × n)
- Expected returns vector (n × 1)

For a 300-asset universe with 252 periods, the cache uses approximately:

- Returns: 300 × 252 × 8 bytes = ~600 KB
- Covariance: 300 × 300 × 8 bytes = ~720 KB
- Total per cache instance: ~1.5 MB

### Numerical Stability

The cache returns exactly the same results as non-cached computations.
All numerical operations use standard pandas/numpy functions with consistent
precision settings.

## Testing

The caching implementation includes comprehensive tests:

- 17 unit tests for `RollingStatistics` class
- 9 integration tests with portfolio strategies
- Tests verify cache hit/miss, invalidation, and result consistency

Run tests with:

```bash
pytest tests/portfolio/test_rolling_statistics.py -v
pytest tests/portfolio/test_strategy_caching.py -v
```

## Future Enhancements

Potential improvements for future versions:

1. **Incremental Updates**: Update statistics incrementally when only a few rows change
1. **EWMA Support**: Exponentially weighted moving average statistics
1. **Persistence**: Save/load cache to/from disk
1. **Thread Safety**: Lock-based or immutable cache for concurrent access
1. **Adaptive Caching**: Automatically decide when to cache based on universe size
   """
