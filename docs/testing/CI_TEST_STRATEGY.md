# CI Test Strategy

This document defines the standard test selections and timeouts used by the
continuous integration (CI) pipelines and recommended local workflows.

## Test Bands

| Band | Purpose | Marker Expression | Timeout | Trigger |
| ---- | ------- | ----------------- | ------- | ------- |
| **Smoke** | Validate critical functionality in seconds | `unit` | 10s per test | Every commit (pre-push) |
| **Core** | Validate primary workflows without long scenarios | `unit or integration` and `not slow` | 60s per test | Pull requests |
| **Full** | Exhaustive verification including slow and data-heavy suites | none (entire `tests/`) | 120s per test | Nightly / scheduled |

All commands inherit the default configuration from `pytest.ini`, including the
60-second global timeout and registered markers.

## Recommended Pipelines

### 1. Local Development Hook (Optional Pre-Commit)

Run the fastest suite while iterating on code:

```bash
pytest -m unit -v --maxfail=1
```

Add `-n auto` to leverage xdist when multiple CPU cores are available.

### 2. Pull Request Validation

Combine fast unit coverage with integration checks while skipping long-running
scenarios:

```bash
pytest -m "unit or integration" -v --timeout=60
```

The `--timeout` flag is optional because the same value is configured globally,
but keeping it explicit in CI scripts makes intent clear.

### 3. Slow & Data-Heavy Scenarios

Nightly or scheduled jobs should cover slow performance and data-dependent
tests to catch regressions that may not appear in fast feedback loops:

```bash
pytest tests/ -v --timeout=120
```

If the environment has access to the large Stooq datasets, include
`pytest -m requires_data` as part of the schedule.

## Marker Conventions in CI

- `slow` markers are excluded from the Pull Request band to keep runtime under
  one minute. Use `pytest -m "not slow"` for this filter.
- `performance` benchmarks should run in dedicated jobs where timing stability is
  guaranteed (fixed CPU allocations).
- `requires_data` tests only run when the backing datasets are mounted. CI jobs
  that lack the data should skip these suites using `-m "not requires_data"`.
- `e2e` suites are optional for nightly builds but recommended before releases.

## Adding New Pipelines

When introducing a new CI workflow:

1. Decide which marker expression best fits the job’s goal.
2. Reference this document in the workflow description.
3. Ensure the command uses the global timeout or overrides it explicitly.
4. Update this table if the pipeline creates a new band (e.g., weekly stress
   tests).

Keeping CI commands centralized avoids drift between developer expectations and
automation, ensuring fast feedback without sacrificing coverage.
