# Service Layer

The service layer provides reusable orchestration classes that encapsulate the
complex coordination previously embedded inside CLI scripts.  Each service is
stateless and accepts its dependencies via the constructor, making it trivial to
swap real implementations for lightweight fakes during testing.  The
public classes expose ergonomic request/response data structures so the same
workflows can be executed from CLIs, notebooks, or automated jobs.

## Available Services

### `DataPreparationService`
Coordinates the tradeable instrument preparation pipeline – building the Stooq
index, matching broker feeds, and exporting reports.  It exposes a
`DataPreparationConfig` input dataclass and returns a
`DataPreparationResult` that documents the pipeline outcome and key artefacts.

### `PortfolioConstructionService`
Runs portfolio construction workflows using the `PortfolioConstructor` factory.
It provides helpers for loading input data, writing results, and comparing
strategies without invoking the CLI scripts.

### `BacktestService`
Wraps the `BacktestEngine` to produce equity curves, performance metrics, and
rebalance events while optionally exporting reporting artefacts.

### `UniverseManagementService`
Offers a thin façade over the universe configuration utilities, allowing callers
to list, inspect, compare, and export universes programmatically.

## Design Principles

- **Dependency Injection:** All external collaborators are injected, enabling
  targeted unit tests and easy substitution in other environments.
- **Statelessness:** Services do not persist mutable state between calls;
  every invocation is self-contained.
- **Focused Results:** Each service returns a structured result object capturing
  outputs and diagnostics, avoiding ad-hoc return tuples.
- **CLI Compatibility:** The scripts now translate CLI arguments into service
  requests, ensuring backwards compatibility while improving maintainability.
