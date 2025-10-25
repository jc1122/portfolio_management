# CI Test Strategy

This strategy outlines how automated runs in continuous integration should use the pytest
markers and timeouts defined in `pytest.ini`. The goal is to keep fast feedback on pull
requests while guaranteeing full coverage on scheduled or nightly jobs.

## Pipelines

### Pull Request Validation

- **Command:** `pytest -m "unit or integration" -v --timeout=60`
- **Purpose:** Provide confidence that core logic and component interactions still pass.
- **Runtime target:** Under 10 minutes.
- **Additional steps:**
  - Enable `pytest -n auto` when the CI executor has multiple cores.
  - Upload coverage reports to track regression trends.

### Nightly Comprehensive Run

- **Command:** `pytest tests/ -v --timeout=120`
- **Purpose:** Execute the entire suite, including slow, performance, and end-to-end tests.
- **Runtime target:** Under 60 minutes on the CI runner.
- **Additional steps:**
  - Persist artifacts such as generated reports under `results/` and `outputs/`.
  - Capture benchmark metrics to detect performance drift.

### Release Candidate / Pre-Deployment

- **Command:**
  ```bash
  pytest -m "(unit or integration or e2e) and not slow" -v --timeout=90
  pytest -m slow -v --timeout=300
  ```
- **Purpose:** Separate slow runs to keep the main pipeline responsive while still verifying
  long-history scenarios before shipping.
- **Runtime target:**
  - Mixed suite: <15 minutes.
  - Slow suite: <2 hours (can run on dedicated hardware).
- **Additional steps:**
  - Compare benchmark outputs against previous release baselines.
  - Require approval if slow tests fail or regress beyond tolerance thresholds.

## Marker Expectations

| Marker | Default PR Run | Nightly | Release | Notes |
| --- | --- | --- | --- | --- |
| `unit` | ✅ | ✅ | ✅ | Always included for fast feedback. |
| `integration` | ✅ | ✅ | ✅ | Ensures component interactions remain stable. |
| `slow` | ❌ | ✅ | ✅ (separate job) | Excluded from PR runs to keep them quick. |
| `performance` | ❌ | ✅ | ✅ | Report metrics; fail build if regression >10%. |
| `requires_data` | Conditional | ✅ | ✅ | Gate behind environment availability of large datasets. |
| `e2e` | Optional | ✅ | ✅ | Include smoke E2E tests on PRs when runtime permits. |

## Timeout Configuration

- **Global default:** `timeout = 60` with `timeout_method = thread` (defined in
  `pytest.ini`).
- **Overrides:** Individual tests can increase the timeout via `@pytest.mark.timeout` when
  justified.
- **Enforcement:** Timeouts apply in all CI jobs to prevent hung test processes; ensure
  cleanup code handles `TimeoutExpired` gracefully.

## Local Development Parity

Developers should mirror the PR workflow locally before opening a pull request:

```bash
pip install -e .[dev]
pytest -m unit -v --timeout=10
pytest -m "unit or integration" -v --timeout=60
```

Running the nightly command locally is optional but recommended before major refactors or
performance-sensitive changes.
