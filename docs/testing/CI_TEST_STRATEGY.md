# Continuous Integration Test Strategy

This guide outlines which pytest selections should run at different stages of the delivery
pipeline. Adjust timings based on hardware available to the CI executor.

## Local Development

Developers should prioritise fast feedback:

```bash
# Fast unit feedback (<5s target)
pytest -m unit -v --timeout=10

# Validate interactions without slow jobs
pytest -m "unit or integration" -v --timeout=60
```

Tips:
- Use `-n auto` to distribute tests when CPU cores are available.
- Run `pytest --maxfail=1` during TDD loops to surface the first failure quickly.

## Pull Request Gate

CI should block merges unless the combined unit and integration suite passes:

```bash
pytest -m "unit or integration" -v --timeout=60
```

Rationale:
- Ensures functional coverage without incurring the full cost of slow datasets.
- Keeps wall-clock time under one minute on standard runners.
- Mark any flaky or data-heavy tests with `@pytest.mark.slow` or
  `@pytest.mark.requires_data` so they can be excluded from this stage.

## Scheduled / Nightly Runs

Run the complete suite, including slow and performance categories, at least once daily:

```bash
pytest tests/ -v --timeout=120
```

Enhancements for the scheduled workflow:
- Emit HTML or JUnit reports for long-running jobs.
- Capture benchmark deltas for `@pytest.mark.performance` tests.
- Publish artefacts such as coverage reports or generated CSV outputs.

## Handling Timeouts

The global timeout (`timeout = 60`, `timeout_method = thread`) defined in `pytest.ini`
prevents hung tests from blocking CI. Tune the value per stage as needed using the
`--timeout` override shown above. If legitimate tests exceed the limit, mark them as
`@pytest.mark.slow` and run them in the scheduled pipeline instead of the PR gate.

## Marker Expectations

| Marker            | Included in Local Fast Loop | Included in PR Gate | Included in Nightly |
| ----------------- | --------------------------- | ------------------- | ------------------- |
| `unit`            | ✅                          | ✅                  | ✅                  |
| `integration`     | ⚠️ (optional)               | ✅                  | ✅                  |
| `slow`            | ❌                          | ❌                  | ✅                  |
| `performance`     | ❌                          | ❌                  | ✅                  |
| `requires_data`   | ❌ (unless data available)  | ❌                  | ✅                  |
| `e2e`             | ❌                          | ❌ (or quarantined) | ✅                  |

Review this table when adding new tests to ensure they land in the appropriate pipeline.
