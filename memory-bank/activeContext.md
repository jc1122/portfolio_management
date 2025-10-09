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

## Next Steps
- Curate a definitive asset universe (tickers compatible with BOŚ/MDM and Stooq symbols) and gather broker commission data, reconciling unmatched listings from the latest run.
- Finalize the data acquisition and sanitation modules by triaging the newly surfaced validation flags (zero volumes, duplicate dates, sparse histories) and determining remediation steps.
- Decide whether FX conversion is required for LSE share classes beyond the new policy switch and evaluate alternatives for the two empty Stooq histories now skipped in exports.
- Document the explicit data gaps (TSX/Xetra/Paris/Swiss) and plan whether to source alternative proxies or defer those assets until new Stooq bundles are available.
- Scaffold the CLI application structure with configuration management and plug-in strategy adapters (equal weight, risk parity, mean-variance).
- Design the backtesting engine with transaction cost modeling, rebalance bands, and performance reporting outputs.
- Identify candidate GitHub repositories/code snippets to accelerate later sentiment/news modules.
- Acquire and unpack missing Stooq regional datasets (e.g., `d_de_txt`, Canadian `.TO`, Swiss `.CH`) to close the remaining unmatched gap before tuning heuristics further.

## Decisions & Considerations
- Rebalance cadence set to monthly/quarterly with ±20% opportunistic bands to limit turnover and commissions.
- Portfolio guardrails enforce diversification (max 25% per ETF, min 10% bonds/cash, cap 90% equities post-overlays).
- Preference for leveraging established libraries (`PyPortfolioOpt`, `riskparityportfolio`, `empyrical`) to minimize bespoke optimization code.
- Future sentiment overlays will be treated as satellite tilts blended through Black–Litterman or capped allocation shifts.

## Insights
- Combining diversified core allocations with trend and volatility overlays can improve risk-adjusted returns without sacrificing long-term compounding.
- Sentiment-driven signals tend to decay quickly; the planned architecture must support regime-aware controls and cooldowns before integration.
- Maintaining rigorous documentation and run logs remains essential to combat agent memory resets and behavioral drift.
