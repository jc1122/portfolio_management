# Test Organization

The automated test suite mirrors the package layout, which makes it easy to target a single functional area or run everything end-to-end. Each top-level directory under `tests/` corresponds to a production package and contains either module-focused unit tests or scenario-driven integration tests.

## Directory Overview

```
tests/
├── core/          # Core utilities, exceptions, configuration helpers
├── assets/        # Selection, classification, and universe management flows
├── analytics/     # Return calculation and data-alignment logic
├── portfolio/     # Strategy engines, constraints, and allocation plumbing
├── backtesting/   # Backtest engine, metrics, and transaction modelling
├── reporting/     # Visualization helpers and summary builders
├── integration/   # Full workflow regressions (marked with pytest `integration`)
└── scripts/       # CLI entrypoints and orchestration smoke tests
```

## Running Tests

### Run Everything

```bash
pytest tests/
```

### Target a Specific Package

```bash
pytest tests/portfolio/      # strategy engines and constraints
pytest tests/backtesting/    # simulation and metrics
pytest tests/reporting/      # reporting helpers
```

### Skip Slow Data-Prep Fixtures

The `tests/scripts/test_prepare_tradeable_data.py` module rebuilds large fixture sets and takes noticeably longer than the rest of the suite. You can exclude it during rapid feedback loops:

```bash
pytest tests/ --ignore=tests/scripts/test_prepare_tradeable_data.py
```

### Coverage Examples

```bash
pytest tests/ --cov=src/portfolio_management --cov-report=term-missing
pytest tests/portfolio/ --cov=src/portfolio_management/portfolio
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
