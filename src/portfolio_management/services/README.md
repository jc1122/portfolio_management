# Service Layer

The service layer provides orchestration helpers for high-level workflows. Each
service wraps an existing subsystem and exposes a focused API suitable for
scripts, notebooks, or external automation.

## Available Services

### `DataPreparationService`
Coordinates the tradeable instrument preparation pipeline. Handles Stooq index
management, matching, report generation, and incremental resume support.

### `PortfolioConstructionService`
Wraps `PortfolioConstructor` with optional preselection and comparison helpers to
construct portfolios from either in-memory data or CSV files.

### `BacktestService`
Simplifies running the historical backtesting engine with a small registry of
strategies and dependency injection hooks for testing.

### `UniverseManagementService`
Provides programmatic access to universe listing, inspection, loading, and
validation workflows that were previously only exposed via the CLI.

Each service is designed to be testable—dependencies can be injected for unit
coverage while defaults mirror the production configuration used by CLI scripts.
