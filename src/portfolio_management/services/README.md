# Service Layer (Experimental)

This package introduces an experimental service layer that extracts
orchestration logic from command-line entry points. The initial focus is on the
portfolio construction workflow, providing a `PortfolioConstructionService`
that mirrors the behaviour of `scripts/construct_portfolio.py` while exposing a
programmatic API suitable for tests or notebooks.

The remaining services defined in this directory are light-weight stubs that
capture the intended public surface area. They will be completed in subsequent
iterations as additional workflows are migrated out of the CLI scripts.
