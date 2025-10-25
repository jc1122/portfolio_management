# Test Organization

This document outlines the structure, categorization, and execution of tests in this project.

## Test Categories

Tests are categorized using pytest markers to allow for selective execution.

### Unit Tests (`@pytest.mark.unit`)
- **Purpose:** Test individual functions, methods, or classes in complete isolation. They should focus on a single piece of logic.
- **Speed:** Must be very fast (<100ms per test).
- **I/O:** Strictly forbidden. This includes file system access, network requests, and database calls. Use mocks or fakes for any external dependencies.
- **Location:** Can be placed in `tests/unit/` or alongside integration tests if they are simple helper functions.
- **Run with:** `pytest -m unit`

### Integration Tests (`@pytest.mark.integration`)
- **Purpose:** Test the interaction between multiple components or modules. These tests verify that different parts of the system work together as expected.
- **Speed:** Can be slower than unit tests, but should ideally complete in <1s per test.
- **I/O:** Allowed. These tests can interact with the file system, mock data files, or other services.
- **Location:** Typically located in `tests/integration/`.
- **Run with:** `pytest -m integration`

### Slow Tests (`@pytest.mark.slow`)
- **Purpose:** For tests that have a long runtime (>1s). These are often comprehensive integration tests or tests that process a significant amount of data.
- **Speed:** Slow by definition.
- **I/O:** Allowed.
- **Usage:** This mark is usually combined with another mark, e.g., `@pytest.mark.integration @pytest.mark.slow`.
- **Run with:** `pytest -m slow`
- **Exclude with:** `pytest -m "not slow"`

### Performance Tests (`@pytest.mark.performance`)
- **Purpose:** Benchmark the performance of critical algorithms or workflows. These tests are used to track performance regressions over time.
- **Speed:** Can be very slow.
- **Location:** `benchmarks/` or `tests/performance/`.
- **Run with:** `pytest -m performance`

### Tests Requiring Data (`@pytest.mark.requires_data`)
- **Purpose:** Mark tests that depend on large, external data files (e.g., historical price data) that may not be available in all environments.
- **Usage:** Often used with a `skipif` condition to check for the data's existence.
- **Run with:** `pytest -m requires_data`

### End-to-End (E2E) Tests (`@pytest.mark.e2e`)
- **Purpose:** Test the entire application workflow from start to finish, often by invoking the Command-Line Interface (CLI).
- **Speed:** Typically the slowest tests.
- **Location:** `tests/e2e/` or `tests/integration/`.
- **Run with:** `pytest -m e2e`

## Directory Structure

- `tests/unit/`: Contains only unit tests.
- `tests/integration/`: Contains integration and E2E tests.
- `tests/fixtures/`: Contains reusable pytest fixtures.
- `benchmarks/`: Contains performance tests.

## Running Tests

Here are some common commands for running tests.

### Fast feedback loop (for local development)
This command runs only the fast unit tests and sets a short timeout.

```bash
pytest -m unit --timeout=10
```

### Full validation (run before committing)
This command runs all tests except those explicitly marked as `slow` and applies a 60-second timeout.

```bash
pytest -m "not slow" --timeout=60
```

### Run only integration tests
```bash
pytest -m integration --timeout=60
```

### Run the entire test suite
This is typically done by CI.

```bash
pytest tests/ --timeout=120
```