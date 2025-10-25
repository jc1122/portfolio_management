# Test Organization

A consistent test structure keeps the suite understandable and makes it easy to run the
right subset of checks during development and CI. This document describes the available
pytest markers, when to apply them, and how the repository organizes fast unit tests and
broader integration coverage.

## Test Categories

### Unit Tests (`@pytest.mark.unit`)

- **Purpose:** Validate a single function or class in isolation.
- **Runtime target:** Under 100ms per test.
- **I/O:** None. Mock file system, network, and database access.
- **Data volume:** Minimal, use small synthetic fixtures.
- **Location:** `tests/unit/` (preferred) or co-located beside integration tests with the
  `@pytest.mark.unit` decorator.
- **Run with:** `pytest -m unit`.

### Integration Tests (`@pytest.mark.integration`)

- **Purpose:** Exercise multiple components working together (e.g., loader + strategy +
  report).
- **Runtime target:** Seconds per test.
- **I/O:** Allowed, including reading fixture data.
- **Data volume:** Moderate, use curated fixtures from `tests/fixtures/`.
- **Location:** `tests/integration/`.
- **Run with:** `pytest -m integration`.

### Slow Tests (`@pytest.mark.slow`)

- **Purpose:** Cover scenarios that require large datasets, long histories, or
  performance-sensitive calculations.
- **Runtime target:** Longer than one second; often minutes.
- **I/O:** Allowed; typically reads from `tradeable_instruments/` or generated outputs.
- **Location:** Co-located with integration tests, always marked as both `slow` and any
  relevant functional category (e.g., `integration`).
- **Run with:** `pytest -m slow` or exclude via `pytest -m "not slow"`.

### Performance Benchmarks (`@pytest.mark.performance`)

- **Purpose:** Detect regressions in algorithmic speed or memory usage.
- **Runtime target:** Bounded micro-benchmarks, ideally <10s overall.
- **I/O:** Avoid external I/O; use in-memory fixtures.
- **Location:** `tests/performance/` or near the component under test with the
  `performance` marker.
- **Run with:** `pytest -m performance`.

### Data-Dependent Tests (`@pytest.mark.requires_data`)

- **Purpose:** Validate behavior that relies on large, optionally gitignored datasets
  (e.g., full universes or historical CSVs in `data/`).
- **Runtime target:** Varies depending on dataset size.
- **I/O:** Required; ensure paths reference fixtures that exist in developer environments.
- **Location:** Typically integration or end-to-end directories. Combine with other marks
  (`integration`, `slow`) to describe scope fully.
- **Run with:** `pytest -m requires_data`.

### End-to-End Tests (`@pytest.mark.e2e`)

- **Purpose:** Execute full CLI workflows, from configuration parsing to report
  generation.
- **Runtime target:** Several seconds to a few minutes.
- **I/O:** Yes; uses prepared configuration files and expects outputs in `outputs/` or
  `results/`.
- **Location:** `tests/e2e/` or scenario-specific directories.
- **Run with:** `pytest -m e2e`.

## Directory Structure Conventions

The repository mirrors `src/portfolio_management/` inside `tests/` to keep related code
close together:

```
src/portfolio_management/
├── analytics/         → tests/analytics/
├── backtesting/       → tests/backtesting/
├── portfolio/         → tests/portfolio/
├── reporting/         → tests/reporting/
└── ...
```

Additional top-level folders capture cross-cutting concerns:

- `tests/unit/`: Fast, isolated unit suites that apply to multiple modules.
- `tests/integration/`: Cross-component scenarios.
- `tests/performance/`: Benchmarks and regression guards.
- `tests/e2e/`: CLI and workflow validations.
- `tests/fixtures/`: Shared data fixtures and builders.

When adding new directories, update `pytest.ini` or documentation if selective execution
is required.

## Marking Guidelines

1. **Always include at least one marker** beyond `unit` for tests that require external
   resources (e.g., pair `slow` with `integration`).
2. **Prefer explicit markers** over relying on directory names so `pytest -m ...` works
   consistently.
3. **Document unusual requirements** (e.g., environment variables) in the test docstring
   and reference them in the relevant documentation section.
4. **Avoid over-marking**: choose the minimal set of markers that accurately describe the
   test.

## Example Patterns

```python
import pytest


@pytest.mark.unit
@pytest.mark.parametrize("config_value", [10, 30, 50])
def test_membership_policy_top_k_bounds(config_value):
    """Unit test that validates configuration ranges without I/O."""
    config = MembershipPolicyConfig(top_k=config_value)
    assert 0 < config.top_k <= 50


@pytest.mark.integration
@pytest.mark.requires_data
def test_backtest_long_history(tmp_path, sample_prices):
    """Integration test that loads historical data and runs the CLI end-to-end."""
    output_dir = tmp_path / "results"
    output_dir.mkdir()
    run_cli_backtest(sample_prices, output_dir)
    assert (output_dir / "summary.json").exists()
```

## Running Specific Test Sets

| Goal | Command |
| --- | --- |
| Fast developer feedback | `pytest -m unit --timeout=10` |
| Integration-only sweep | `pytest -m integration --timeout=60` |
| Skip slow scenarios | `pytest -m "not slow"` |
| Performance benchmarks | `pytest -m performance` |
| End-to-end workflows | `pytest -m e2e --timeout=120` |

Combine markers with logical expressions (e.g., `pytest -m "integration and not slow"`).
