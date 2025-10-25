# CI/CD Test Strategy

This document defines the automated testing strategy used in the Continuous Integration (CI) pipeline.

## On every commit (fast feedback)

To provide rapid feedback to developers, a fast-running suite of tests is executed on every commit pushed to a branch.

```bash
pytest -m "unit" -v --timeout=10
```

- **Goal:** Complete in < 5 seconds.
- **Purpose:** Catch simple regressions in isolated logic immediately.
- **Scope:** Runs all tests marked as `unit`.

## On pull request (full validation)

Before a pull request can be merged, a more comprehensive set of tests is run to ensure the changes are well-integrated and do not cause regressions.

```bash
pytest -m "unit or integration" -v --timeout=60
```

- **Goal:** Complete in < 60 seconds.
- **Purpose:** Perform a thorough validation of the changes.
- **Scope:** Runs all `unit` and `integration` tests. Slow tests are excluded to keep the feedback loop reasonably fast.

## Nightly Build (comprehensive)

A full test run is executed nightly to catch any issues that might have been missed in the faster test suites, including performance regressions.

```bash
pytest tests/ -v --timeout=120
```

- **Goal:** Complete in a reasonable time, but thoroughness is prioritized over speed.
- **Purpose:** Ensure the stability and performance of the entire system over time.
- **Scope:** Runs all tests in the `tests/` directory, including those marked as `slow` and `performance`.