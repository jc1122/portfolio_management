# Test Organization

This document describes how the repository's automated tests are categorized, where they
live in the tree, and how to run the different groups with pytest markers.

## Test Categories

### Unit Tests (`@pytest.mark.unit`)
- **Purpose:** Validate individual functions or classes in isolation.
- **Speed target:** Under 100 ms per test.
- **External effects:** None; avoid touching the filesystem or network. Prefer mocks and
  fakes for collaborators.
- **Location:** `tests/unit/` (preferred) or colocated with integration tests when the
  module structure makes more sense. Always include the `@pytest.mark.unit` marker when
  colocated.
- **Run with:** `pytest -m unit`.

### Integration Tests (`@pytest.mark.integration`)
- **Purpose:** Exercise multiple components working together (e.g., loaders + engines).
- **Speed target:** Typically below one second per test.
- **External effects:** File I/O and larger in-memory data structures are acceptable.
- **Location:** `tests/integration/` or any directory dedicated to multi-component flows.
- **Run with:** `pytest -m integration`.

### Slow Tests (`@pytest.mark.slow`)
- **Purpose:** Cover scenarios that are expected to take longer than one second, such as
  end-to-end workflows on large data sets.
- **External effects:** Free to use real data or complex computations.
- **Location:** Usually under `tests/integration/` or `tests/performance/`.
- **Run with:** `pytest -m slow` (often combined with additional markers, e.g.,
  `pytest -m "slow and integration"`).

### Performance Benchmarks (`@pytest.mark.performance`)
- **Purpose:** Benchmark critical paths and guard performance regressions.
- **Speed target:** Can be long-running but should remain deterministic.
- **External effects:** May depend on representative datasets; document required inputs.
- **Location:** `tests/performance/`.
- **Run with:** `pytest -m performance`.

### Data-Dependent Tests (`@pytest.mark.requires_data`)
- **Purpose:** Validate behaviour that requires large or external datasets that are not
  distributed with the repository.
- **Speed target:** Variable; often slower because of I/O.
- **External effects:** May need access to the `data/` directory or remote resources.
- **Location:** Wherever the relevant feature is tested; ensure the marker is applied so
  these tests can be skipped in environments without data access.
- **Run with:** `pytest -m requires_data`.

### End-to-End Tests (`@pytest.mark.e2e`)
- **Purpose:** Execute full workflows that mimic production usage (e.g., CLI scripts,
  backtests).
- **Speed target:** Typically the slowest class; keep under several minutes.
- **External effects:** May touch the filesystem and require prepared fixtures.
- **Location:** `tests/e2e/` or scenario-specific directories.
- **Run with:** `pytest -m e2e`.

## Directory Structure Conventions

```
tests/
├── unit/            # Fast, isolated unit tests
├── integration/     # Multi-component flows
├── performance/     # Benchmarks and profiling helpers
├── e2e/             # Full workflow tests (often slower)
├── data/            # Tests for data loaders and ingestion utilities
└── conftest.py      # Shared fixtures
```

Not every directory exists yet, but they represent the intended layout as the suite grows.
When a module naturally owns its tests (e.g., `tests/portfolio/`), apply the appropriate
marker to each test class or function so the categorisation remains consistent.

## Writing New Tests

1. **Choose a category first.** Decide whether the behaviour under test is unit,
   integration, performance, etc.
2. **Place the file in the matching directory.** If colocating with module-specific
   tests, add the appropriate marker to each test.
3. **Keep tests deterministic.** Use fixed seeds, temporary directories, or mock layers to
   eliminate nondeterminism.
4. **Document special requirements.** Mention large fixture files, environment variables,
   or credentials in the test module docstring.

## Running Tests by Category

```bash
# Fast feedback during development
pytest -m unit --timeout=10

# Integration and unit tests together (default CI focus)
pytest -m "unit or integration" --timeout=60

# Everything except slow tests
pytest -m "not slow" --timeout=60

# Full suite including slow and performance checks
pytest tests/ --timeout=120
```

Use `--maxfail=1` for quick failure and `-n auto` (via `pytest-xdist`) when parallelism is
appropriate for the environment.

## Current Marker Usage Snapshot

The following counts reflect the repository at the time of this update:

```
2 @pytest.mark.integration
2 @pytest.mark.slow
5 @pytest.mark.skipif
1 @pytest.mark.xfail
```

Use this as a baseline when triaging additional tests or converting existing cases to the
new categories.
