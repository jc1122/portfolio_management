# Active Context

## Current Focus
- Standing up the data ingestion and sanitization workflow, including tooling to align Stooq histories with the brokers' tradeable universe.

## Recent Changes
- Captured project scope, architectural patterns, and technology stack in the Memory Bank based on the detailed brief and literature survey.
- Recorded portfolio construction goals (core diversification, factor tilts, risk overlays) and future sentiment-integration ambitions.
- Implemented an optimized `prepare_tradeable_data.py` script that indexes unpacked Stooq files, matches them against BOŚ/mBank universes, and exports price panels with multicore support and cached metadata.
- Hardened the matching logic to stop cross-venue fallbacks, added alias handling for stubborn U.S. listings, and enriched the reports with price coverage/currency diagnostics.
- Latest export produced 5 ,560 matched instruments (4 ,146 price files after skipping empties) and 1 ,262 unmatched, with gaps concentrated in missing `.TO`, `.DE`, `.FR/.PA`, and `.CH` Stooq bundles.
- Introduced currency overrides for LSE multi-currency share classes and flagged two empty Stooq histories (`HSON.US`, `WPS.UK`) for follow-up.
- Hardened the ingestion pipeline with row-level validation (duplicate dates, non-positive prices, missing/zero volume), optional LSE currency policies, and automatic skipping of empty Stooq histories during export.
- Enhanced the validation stage to classify zero-volume exposure severity (low/moderate/high/critical) and regenerated the tradeable match report; captured the details in `data/metadata/tradeable_data_flags.csv` for offline triage and now flag them as warnings without filtering.
- Replaced the row-by-row CSV validator with a pandas-backed summarizer (C-engine, selective columns) as the default path, keeping the legacy parser only as a temporary fallback and benchmarking the new approach to parity/slight gains.

## Next Steps
- Curate a definitive asset universe (tickers compatible with BOŚ/MDM and Stooq symbols) and gather broker commission data, reconciling unmatched listings from the latest run.
- Finalize the data acquisition and sanitation modules by determining whether any additional remediation is required beyond the current warning-only zero-volume tagging, and whether duplicate-date/sparse-history checks need more automation.
- Decide whether FX conversion is required for LSE share classes beyond the new policy switch and evaluate alternatives for the two empty Stooq histories now skipped in exports.
- Scaffold the CLI application structure with configuration management and plug-in strategy adapters (equal weight, risk parity, mean-variance).
- Design the backtesting engine with transaction cost modeling, rebalance bands, and performance reporting outputs.
- Identify candidate GitHub repositories/code snippets to accelerate later sentiment/news modules.
- Confirm pandas availability across execution environments and remove the legacy CSV validation path once safe to do so.

## Decisions & Considerations
- Rebalance cadence set to monthly/quarterly with ±20% opportunistic bands to limit turnover and commissions.
- Portfolio guardrails enforce diversification (max 25% per ETF, min 10% bonds/cash, cap 90% equities post-overlays).
- Preference for leveraging established libraries (`PyPortfolioOpt`, `riskparityportfolio`, `empyrical`) to minimize bespoke optimization code.
- Future sentiment overlays will be treated as satellite tilts blended through Black–Litterman or capped allocation shifts.
- User has mandated offline operation for now—no automated Stooq downloads until the restriction is lifted; focus on documenting gaps and preparing offline import scripts instead.
- Zero-volume anomalies remain in the dataset with severity warnings only; remediation will occur manually once better volume data or broker guidance is available.

## Insights
- Combining diversified core allocations with trend and volatility overlays can improve risk-adjusted returns without sacrificing long-term compounding.
- Sentiment-driven signals tend to decay quickly; the planned architecture must support regime-aware controls and cooldowns before integration.
- Maintaining rigorous documentation and run logs remains essential to combat agent memory resets and behavioral drift.
