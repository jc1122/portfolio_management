# Test Organization

The test suite is organized to mirror the package structure, allowing you to run tests for specific packages independently.

## Test Structure

```
tests/
├── core/              # Core package tests (utils, exceptions, config) - 26 tests
├── data/              # Data package tests (io, matching, analysis) - 0 tests (will be added)
├── assets/            # Assets package tests - 98 tests
│   ├── test_selection.py
│   ├── test_classification.py
│   └── test_universes.py
├── analytics/         # Analytics package tests - 14 tests
│   └── test_returns.py
├── portfolio/         # Portfolio package tests - 36 tests
│   └── test_portfolio.py
├── backtesting/       # Backtesting package tests - 12 tests
│   └── test_backtest.py
├── reporting/         # Reporting/visualization tests - 9 tests
│   └── test_visualization.py
├── integration/       # Integration tests - 14 tests
│   ├── test_full_pipeline.py
│   ├── test_performance.py
│   └── test_production_data.py
└── scripts/           # Script tests - 22 tests
    ├── test_calculate_returns.py (2 tests, ~1s)
    ├── test_construct_portfolio.py (3 tests, ~1s)
    └── test_prepare_tradeable_data.py (17 tests, ~84s) ⚠️ SLOW

Total: 231 tests
```

## Running Tests

### Run All Tests

```bash
pytest tests/                        # All tests (~160s)
```

### Run Tests by Package

```bash
# Fast tests
pytest tests/core/                   # Core utilities (26 tests, ~2s)
pytest tests/assets/                 # Asset management (98 tests, ~3s)
pytest tests/analytics/              # Analytics/returns (14 tests, ~1s)
pytest tests/portfolio/              # Portfolio construction (36 tests, ~2s)
pytest tests/backtesting/            # Backtesting (12 tests, ~4s)
pytest tests/reporting/              # Visualization (9 tests, ~1s)

# Moderate tests
pytest tests/integration/            # Integration tests (14 tests, ~33s)
pytest tests/scripts/test_calculate_returns.py        # ~1s
pytest tests/scripts/test_construct_portfolio.py      # ~1s

# Slow tests (run only when needed)
pytest tests/scripts/test_prepare_tradeable_data.py   # 17 tests, ~84s ⚠️
```

### Run Fast Tests Only (Exclude Slow Data Prep)

```bash
pytest tests/ --ignore=tests/scripts/test_prepare_tradeable_data.py
# 214 tests in ~75s (vs 231 tests in ~160s)
```

### Run Tests with Coverage

```bash
# Full coverage
pytest tests/ --cov=src/portfolio_management --cov-report=term-missing

# Package-specific coverage
pytest tests/assets/ --cov=src/portfolio_management/assets
pytest tests/core/ --cov=src/portfolio_management/core
```

### Run Tests in Parallel

```bash
# Requires pytest-xdist
pytest tests/ -n auto                                    # Auto-detect CPU count
pytest tests/ -n 4                                       # Use 4 workers
pytest tests/assets/ -n 4                                # Parallel for specific package
```

## CI/CD Recommendations

For continuous integration, consider splitting test runs:

```yaml
# Fast feedback (run on every commit)
- name: Fast Tests
  run: pytest tests/ --ignore=tests/scripts/test_prepare_tradeable_data.py

# Full validation (run on PR/merge)
- name: Full Test Suite
  run: pytest tests/
```

## Benefits of Organized Test Structure

1. **Faster Development**: Run only relevant tests while developing a specific package
1. **Better Organization**: Tests mirror the code structure, easier to find and maintain
1. **Selective CI**: Run quick tests first, slow tests only when needed
1. **Isolation**: Each package can be tested independently
1. **Clear Ownership**: Know which tests relate to which code

## Adding New Tests

When adding new tests, place them in the appropriate package directory:

- Testing `src/portfolio_management/core/*` → `tests/core/`
- Testing `src/portfolio_management/assets/*` → `tests/assets/`
- Testing end-to-end workflows → `tests/integration/`
- Testing CLI scripts → `tests/scripts/`
