# Service Layer

The `portfolio_management.services` package exposes high-level orchestration APIs
for the most complex workflows in the toolkit. Each service wraps the existing
modules that perform the heavy lifting and provides:

- Dependency injection points for unit testing.
- Declarative configuration dataclasses.
- Structured result objects for callers that need more than CLI side-effects.
- Logging hooks for observability outside the CLI entry points.

## Available Services

### DataPreparationService
Coordinates the tradeable data preparation pipeline. It encapsulates Stooq index
management, tradeable matching, report generation, and incremental cache
handling. Consumers pass a `DataPreparationConfig` and receive a
`DataPreparationResult` describing what happened (including whether the run was
skipped due to incremental resume).

### PortfolioConstructionService
Provides programmatic access to the portfolio construction workflows powering
the `construct_portfolio` CLI. The service loads inputs, applies constraints,
and either constructs a single portfolio or compares multiple strategies.

### BacktestService
Wraps the `BacktestEngine` to make it easy to execute backtests without invoking
the CLI. Callers supply a `BacktestRequest` containing all runtime dependencies
and receive a `BacktestResult` with the equity curve, metrics, and event log.

### UniverseManagementService
Offers utilities for listing, describing, loading, comparing, and validating
universes without interacting with the CLI script. Methods return rich objects
that are straightforward to inspect in tests or other tooling.

Each service is intentionally thin: it orchestrates existing domain modules
without re-implementing business logic, making complex operations accessible and
testable.
