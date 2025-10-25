# Type Checking Best Practices

## Overview

This project uses mypy for static type checking to catch bugs early and improve code quality.

## Running Type Checks

```bash
# Check all source code
mypy src/

# Check specific module
mypy src/portfolio_management/portfolio/

# Check with verbose output
mypy src/ --show-error-codes --pretty
```

## Type Aliases

Use type aliases from `portfolio_management.core.types`:

```python
from portfolio_management.core.types import WeightDict, ReturnFrame

def construct_portfolio(returns: ReturnFrame) -> WeightDict:
    # Type-safe function
    pass
```

## Common Patterns

### DataFrame with specific columns

```python
def process_prices(df: PriceFrame) -> ReturnFrame:
    """Process price data to returns.

    Args:
        df: Price DataFrame with Date, Symbol, Close columns

    Returns:
        Return DataFrame with Date index and asset columns
    """
    pass
```

### Series with specific dtype

```python
from portfolio_management.core.types import ReturnSeries

def calculate_metric(returns: ReturnSeries) -> float:
    """Calculate metric from returns series."""
    pass
```

### Pandas-stubs limitations

Some pandas operations have strict type stubs that may not match all use cases:

```python
# If legitimate pandas-stubs limitation, use type ignore with comment
df = pd.read_csv(path, **kwargs)  # type: ignore[call-overload]  # Complex kwargs

# Better: Specify parameters explicitly
df = pd.read_csv(path, parse_dates=["Date"], index_col=0)  # No type ignore needed
```

## Configuration

Type checking is configured in `mypy.ini`:
- Source code: Strict typing
- Tests: Relaxed (don't need full type annotations)
- Scripts: Relaxed (will be refactored to use services)

## CI/CD

Type checking runs automatically on:
- Every commit (via pre-commit hook)
- Every pull request (via GitHub Actions)

## Troubleshooting

### False positives

If mypy reports an error but code is correct:
1. Check if pandas-stubs is up to date
2. Consider if type can be more specific
3. Use `type: ignore` with detailed comment as last resort

### Missing type stubs

If mypy complains about missing stubs:
```bash
# Install type stubs
pip install types-package-name
```

Or add to mypy.ini:
```ini
[mypy-package_name.*]
ignore_missing_imports = True
```