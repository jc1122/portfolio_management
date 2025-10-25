# Test Organization

This guide explains how the portfolio management test suite is organized and how pytest
markers should be applied to keep feedback fast and targeted.

## Test Categories

### Unit Tests (`@pytest.mark.unit`)
- **Purpose:** Validate a single function, class, or method in isolation.
- **Speed Target:** <100ms per test.
- **I/O:** None. Use mocks or fakes for any external interaction.
- **Data:** Synthetic fixtures, factories, or inline inputs.
- **Location:** Prefer `tests/unit/` or package-specific subdirectories such as
  `tests/portfolio/` with the `@pytest.mark.unit` marker when colocated with
  integration tests.
- **Run with:**
  ```bash
  pytest -m unit
  ```

### Integration Tests (`@pytest.mark.integration`)
- **Purpose:** Exercise multiple components working together using realistic
  dependencies.
- **Speed Target:** <1s per test when possible.
- **I/O:** Allowed (file system, lightweight network mocks, database fixtures).
- **Data:** Realistic fixture data or curated slices of production exports.
- **Location:** `tests/integration/`.
- **Run with:**
  ```bash
  pytest -m integration
  ```

### Slow Tests (`@pytest.mark.slow`)
- **Purpose:** Validate performance, long-history scenarios, and boundary cases
  that require significant computation or large data.
- **Speed Target:** >1s per test is acceptable; many run minutes.
- **I/O:** Allowed. Prefer to re-use cached artifacts to limit runtime.
- **Location:** Typically under `tests/integration/` or `tests/long_history/`.
- **Run with:**
  ```bash
  pytest -m slow
  ```

### Performance Tests (`@pytest.mark.performance`)
- **Purpose:** Detect regressions in runtime, memory usage, or algorithmic
  complexity.
- **Speed Target:** Depends on the benchmark; record baseline timings in the
  test docstring.
- **I/O:** Avoid unless benchmarking I/O specifically.
- **Location:** `tests/performance/` or colocated with the subsystem under test.
- **Run with:**
  ```bash
  pytest -m performance
  ```

### Data-Dependent Tests (`@pytest.mark.requires_data`)
- **Purpose:** Cover scenarios that need large, git-ignored datasets (for
  example, the 20-year Stooq exports).
- **Speed Target:** Variable; often slow.
- **I/O:** Heavy file system usage expected.
- **Location:** Integration or end-to-end directories with clear fixture setup
  and teardown.
- **Run with:**
  ```bash
  pytest -m requires_data
  ```

### End-to-End Tests (`@pytest.mark.e2e`)
- **Purpose:** Simulate real user workflows such as running CLI scripts or full
  backtests from configuration to report generation.
- **Speed Target:** Minutes per workflow is acceptable. Reserve for CI pipelines
  rather than local TDD loops.
- **I/O:** Full workflow (file system, configuration, reports).
- **Location:** `tests/e2e/` or under `tests/integration/` with explicit
  scenarios.
- **Run with:**
  ```bash
  pytest -m e2e
  ```

## Directory Structure

The test tree mirrors the production package layout. Within each directory:

- Place fast, isolated tests in a `unit/` subdirectory when a mix of unit and
  integration coverage exists.
- Create `integration/` subdirectories for workflow-level coverage when the
  parent directory already contains unit tests.
- Use descriptive filenames that match the module under test, e.g.
  `test_strategy_caching.py` for `strategy/caching.py`.
- Keep helper utilities in `_helpers.py` modules or `conftest.py` fixtures to
  avoid duplication.

Example layout:

```
tests/
├── analytics/
│   ├── test_returns_unit.py        # Unit tests marked with @pytest.mark.unit
│   └── integration/
│       └── test_returns_pipeline.py  # @pytest.mark.integration
├── integration/
│   ├── test_smoke_integration.py     # @pytest.mark.integration
│   ├── test_long_history.py          # @pytest.mark.slow
│   └── test_cli_backtest.py          # @pytest.mark.e2e
└── performance/
    └── test_backtest_performance.py  # @pytest.mark.performance
```

## Applying Markers Consistently

1. **Always register new markers** in `pytest.ini` before committing code.
2. **Combine markers** when a test fits multiple categories, e.g. a long-running
   integration workflow should use both `@pytest.mark.integration` and
   `@pytest.mark.slow`.
3. **Document intent** in the test docstring describing why the marker is
   applied.
4. **Avoid mislabeling**: do not mark slow tests as unit tests simply to include
   them in fast feedback loops.
5. **Review markers regularly** during test reviews to ensure they still reflect
   the test’s behavior.

## Running Tests by Category

```bash
# Collect-only mode is useful when a category is not yet populated
pytest -m unit --collect-only
pytest -m integration --collect-only
pytest -m slow --collect-only
pytest -m "not slow"  # Run everything except long-running scenarios

# Combine categories
pytest -m "unit or integration"
pytest -m "integration and not slow"
```

## Developer Workflow

1. **Local iteration**: run unit tests (`pytest -m unit`) with `--maxfail=1` for
   quick feedback.
2. **Feature ready**: run the relevant integration suite plus
   `pytest -m "not slow"` to catch regressions.
3. **Pre-commit**: execute the command set defined in
   [`CI_TEST_STRATEGY.md`](CI_TEST_STRATEGY.md) to mirror CI expectations.
4. **Nightly/weekly**: schedule slow, performance, and data-heavy suites to
   maintain long-term stability.

Following this structure keeps the test suite predictable and enables targeted
execution in both local and CI environments.
