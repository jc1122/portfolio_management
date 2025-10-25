# Test Organization

This guide defines how tests in the portfolio management project are categorized, where
they live in the repository, and how to execute targeted subsets during development or
continuous integration. Use it as the single source of truth when adding new tests or
tagging existing ones with pytest marks.

## Directory Conventions

- **Unit tests:** Prefer placing fast, isolated tests under `tests/unit/`. When a module
  already has an adjacent integration suite, unit tests may co-locate in the same file as
  long as they are marked with `@pytest.mark.unit`.
- **Integration tests:** Reside under `tests/integration/` and exercise multiple
  components or workflows together.
- **End-to-end tests:** Store in `tests/e2e/` (create if needed). These replicate full CLI
  runs or long-lived workflows.
- **Performance or slow tests:** Keep near the feature under test (e.g.,
  `tests/performance/`). Always mark them so they can be excluded from quick iterations.

## Test Categories and Pytest Marks

### Unit Tests — `@pytest.mark.unit`

- **Purpose:** Validate a single function, class, or small utility in isolation.
- **Runtime:** < 100 ms per test. Any dependency heavier than a lightweight helper should
  be mocked.
- **I/O:** Not allowed. Avoid touching the filesystem, network, or database.
- **Location:** `tests/unit/` or within module-specific files tagged with
  `@pytest.mark.unit`.
- **Run command:**
  ```bash
  pytest -m unit
  ```
- **Example:**
  ```python
  @pytest.mark.unit
  def test_membership_buffer_validation() -> None:
      with pytest.raises(ValueError, match="buffer_rank must be >= top_k"):
          MembershipPolicy(buffer_rank=5, top_k=10)
  ```

### Integration Tests — `@pytest.mark.integration`

- **Purpose:** Verify that multiple modules collaborate correctly, typically using real
  configuration or data fixtures.
- **Runtime:** Up to ~1 s per test; longer tests should also be marked `@pytest.mark.slow`.
- **I/O:** Allowed when necessary (e.g., reading fixture CSVs).
- **Location:** `tests/integration/`.
- **Run command:**
  ```bash
  pytest -m integration
  ```
- **Example:**
  ```python
  @pytest.mark.integration
  def test_backtest_smoke(snapshot_portfolio):
      result = snapshot_portfolio.run()
      assert result.metrics.total_return > 0
  ```

### Slow Tests — `@pytest.mark.slow`

- **Purpose:** Capture scenarios that take longer than one second, often due to long
  history data or iterative optimizers.
- **Runtime:** Minutes are acceptable, but document expectations in the test docstring.
- **Usage:** Combine with other marks such as `integration`, `performance`, or
  `requires_data` to signal the test type and runtime profile.
- **Run command:**
  ```bash
  pytest -m slow
  pytest -m "not slow"  # Exclude slow tests
  ```

### Performance Tests — `@pytest.mark.performance`

- **Purpose:** Track throughput, latency, and memory regressions for critical workflows.
- **Runtime:** Variable. Always report measured metrics in the assertion messages so
  regressions are easy to diagnose.
- **Location:** `tests/performance/` or close to the feature under test.
- **Run command:**
  ```bash
  pytest -m performance
  ```

### Data-Dependent Tests — `@pytest.mark.requires_data`

- **Purpose:** Identify suites that require large fixture sets (e.g., cached Stooq
  universes) and therefore may be skipped in constrained environments.
- **Usage:** Combine with `integration` or `slow` when both apply. Provide a helpful skip
  reason so developers know how to obtain the data locally.
- **Run command:**
  ```bash
  pytest -m requires_data
  ```

### End-to-End Tests — `@pytest.mark.e2e`

- **Purpose:** Exercise CLI commands or workflows from configuration parsing through
  report generation.
- **Runtime:** Often the slowest suite because it provisions data, runs backtests, and
  validates final artifacts. Consider running nightly or before releases.
- **Location:** `tests/e2e/`.
- **Run command:**
  ```bash
  pytest -m e2e
  ```

## Running Focused Suites

- **Fast feedback loop:** `pytest -m "unit and not slow" --timeout=10`
- **Feature validation:** `pytest -m "unit or integration" --timeout=60`
- **Exclude slow tests:** `pytest -m "not slow"`
- **Comprehensive run:** `pytest --timeout=60`

Refer to [`docs/testing/CI_TEST_STRATEGY.md`](CI_TEST_STRATEGY.md) for recommended
pipelines that incorporate these commands.

## Current Marker Usage Snapshot (October 2025)

The following marks already appear in the repository:

| Mark | Files | Notes |
| --- | --- | --- |
| `integration` | `tests/integration/test_smoke_integration.py`, `tests/integration/test_backtest_integration.py` | Smoke and backtest workflows |
| `slow` | `tests/integration/test_production_data.py`, `tests/integration/test_performance.py` | Long-history and performance scenarios |

No tests currently use the new `unit`, `performance`, `requires_data`, or `e2e` marks. As
the suite is reorganized in later phases, migrate eligible tests and update this table as
needed.
