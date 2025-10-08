# Active Context

## Current Focus
- Standing up the data ingestion and sanitization workflow, including tooling to align Stooq histories with the brokers' tradeable universe.

## Recent Changes
- Captured project scope, architectural patterns, and technology stack in the Memory Bank based on the detailed brief and literature survey.
- Recorded portfolio construction goals (core diversification, factor tilts, risk overlays) and future sentiment-integration ambitions.
- Implemented an optimized `prepare_tradeable_data.py` script that indexes unpacked Stooq files, matches them against BOŚ/mBank universes, and exports price panels with multicore support and cached metadata.

## Next Steps
- Curate a definitive asset universe (tickers compatible with BOŚ/MDM and Stooq symbols) and gather broker commission data, reconciling unmatched listings from the latest run.
- Finalize the data acquisition and sanitation modules, extending validation on price quality, missing data handling, and currency alignment.
- Scaffold the CLI application structure with configuration management and plug-in strategy adapters (equal weight, risk parity, mean-variance).
- Design the backtesting engine with transaction cost modeling, rebalance bands, and performance reporting outputs.
- Identify candidate GitHub repositories/code snippets to accelerate later sentiment/news modules.

## Decisions & Considerations
- Rebalance cadence set to monthly/quarterly with ±20% opportunistic bands to limit turnover and commissions.
- Portfolio guardrails enforce diversification (max 25% per ETF, min 10% bonds/cash, cap 90% equities post-overlays).
- Preference for leveraging established libraries (`PyPortfolioOpt`, `riskparityportfolio`, `empyrical`) to minimize bespoke optimization code.
- Future sentiment overlays will be treated as satellite tilts blended through Black–Litterman or capped allocation shifts.

## Insights
- Combining diversified core allocations with trend and volatility overlays can improve risk-adjusted returns without sacrificing long-term compounding.
- Sentiment-driven signals tend to decay quickly; the planned architecture must support regime-aware controls and cooldowns before integration.
- Maintaining rigorous documentation and run logs remains essential to combat agent memory resets and behavioral drift.
