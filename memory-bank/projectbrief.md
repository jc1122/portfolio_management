# Project Brief

## Overview

- Build a Python command-line toolkit that constructs and backtests retirement-oriented portfolios for a ~30-year horizon using historical market data.
- Serve a Polish retail investor (≈50k USD capital) who can trade through BOŚ Dom Maklerski and mBank's MDM, with future expansion to active overlays driven by news/sentiment analytics.

## Goals

- Deliver an offline-first workflow that ingests free daily price data (e.g., Stooq) and produces allocation recommendations across diversified core, factor tilts, and defensive sleeves.
- Support multiple portfolio construction engines (equal weight, risk parity, mean-variance via PyPortfolioOpt) selectable via configuration or CLI flags.
- Incorporate monthly-to-quarterly rebalancing logic that accounts for commission drag, opportunistic bands, and risk controls (trend, volatility targeting) where feasible.
- Generate performance analytics (Sharpe, drawdown, Expected Shortfall, volatility) and visualizations suitable for decision logs and compliance documentation.
- Lay groundwork for a subsequent module that integrates LLM-driven news/sentiment factors into allocation views (Black–Litterman, satellite tilts).

## Constraints

- Asset universe limited to securities available on BOŚ and MDM platforms; prefer UCITS accumulating ETFs to optimize tax efficiency for a Polish resident.
- Tooling must operate offline once data sets are cached; external data sources must be freely accessible without restrictive licensing.
- Rebalancing frequency capped at monthly/quarterly to manage transaction costs; opportunistic trading bands (±20%) recommended.
- Portfolio guardrails: max single ETF weight 25%, max post-overlay equity exposure 90%, minimum bonds/cash 10%.

## Open Questions

- Confirm definitive ticker list (ETFs, bonds, alternatives) supported by both brokers and Stooq symbol coverage.
- Specify commission schedule and slippage assumptions to embed in backtests.
- Determine which risk overlays (trend filter, volatility targeting) are in scope for the initial offline release versus deferred.
- Clarify reporting expectations (format, storage, frequency) for risk metrics and decision logs.
- Outline acceptance criteria for the future news/sentiment integration stage.
