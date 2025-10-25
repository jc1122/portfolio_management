# CI Test Strategy

This document codifies which subsets of the test suite run at different stages of the
continuous integration pipeline. Pair it with the [Test Organization](TEST_ORGANIZATION.md)
reference when deciding how to tag new tests or introduce additional workflows.

## Goals

1. Provide fast feedback to developers before code review.
2. Guarantee integration scenarios execute before merge.
3. Reserve the slowest or most data-heavy suites for scheduled builds.
4. Enforce consistent timeouts so runaway tests cannot block pipelines.

## Default Pytest Configuration

The `pytest.ini` file registers common marks and configures a 60-second default timeout
using the thread-based cancellation method. CI jobs should rely on the repository config:

```bash
pytest --timeout=60
```

When invoking pytest with `-m`, the configured default still applies unless you override it
explicitly.

## Pipeline Stages

### 1. Pre-Commit / Developer Lint Job

| Objective | Command | Notes |
| --- | --- | --- |
| Fast correctness check | `pytest -m "unit and not slow" --timeout=30` | Targets only isolated logic; should finish in < 1 minute. |

- Optional: run with `pytest -q` to reduce noise.
- Skips integration, performance, and data-heavy suites for maximal speed.

### 2. Pull Request Validation (CI Required)

| Objective | Command | Notes |
| --- | --- | --- |
| Functional coverage | `pytest -m "unit or integration" --timeout=60 --strict-markers` | Combines unit and integration tests while still respecting the global timeout. |
| Marker audit | `pytest --markers` | Useful to ensure new markers remain documented (can be part of a docs check). |

- Executed on every push to an open PR.
- The `--strict-markers` flag is redundant because it is already configured in
  `pyproject.toml`, but including it here highlights the expectation that all marks are
  registered.
- If large fixture data is unavailable in CI, add `-m "not requires_data"` to the command
  while ensuring those tests run nightly.

### 3. Scheduled / Nightly Builds

| Objective | Command | Notes |
| --- | --- | --- |
| Full regression | `pytest --timeout=120` | Executes entire suite, including slow and performance tests. |
| Performance trend | `pytest -m performance --timeout=180 -vv` | Captures benchmark metrics; output can be fed into trend dashboards. |
| Data validation | `pytest -m requires_data --timeout=180` | Ensures cached universes remain compatible with analytics code. |

- Nightly builds should archive pytest reports and performance metrics for trend
  analysis.
- Failures in these jobs do not block merges immediately but must be triaged within the
  next working day.

## Adding New Jobs

When introducing a new CI job:

1. Select the smallest test subset that proves the desired quality gate.
2. Prefer existing marks before inventing new ones. If a new mark is required, register it
   in both `pytest.ini` and `pyproject.toml` and document it in
   [`TEST_ORGANIZATION.md`](TEST_ORGANIZATION.md).
3. Keep total runtime per job under 15 minutes. Split long jobs into parallel groups using
   `pytest -m` expressions or `pytest-xdist`.
4. Use the `pytest-timeout` plugin (already declared in dependencies) to enforce per-test
   or per-suite limits, adjusting `--timeout` when a job allows longer execution.

## Local Developer Tips

- Install development extras: `pip install -e .[dev]` to access `pytest-timeout` and other
  tooling.
- Use `pytest -m integration --maxfail=1` while iterating on multi-component changes.
- Combine marks: `pytest -m "integration and not slow"` runs the faster integration tests
  while skipping long-history scenarios.
- Generate coverage during local validation:
  ```bash
  pytest -m "unit or integration" --cov=portfolio_management
  ```

Keeping these practices aligned between local development and CI ensures predictable build
outcomes and minimizes surprises late in the release process.
