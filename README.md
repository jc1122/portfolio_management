# Portfolio Management Toolkit

Offline-first Python command-line toolkit for constructing and backtesting long-horizon retirement portfolios for Polish investors trading via BOŚ Dom Maklerski and mBank's MDM. The project emphasizes diversified asset allocation, factor tilts, and disciplined risk overlays, with future plans to incorporate news- and sentiment-driven signals.

## Key Features (Planned)
- Modular pipeline: data acquisition (e.g., Stooq), sanitation, asset selection, strategy engines, backtesting, and reporting.
- Multiple allocation methods: equal weight, risk parity, and mean-variance optimization via established libraries (`PyPortfolioOpt`, `riskparityportfolio`).
- Monthly/quarterly rebalancing with commission-aware opportunistic bands and risk guardrails.
- Performance analytics including Sharpe ratio, drawdowns, realized volatility, and Expected Shortfall.
- Extensible architecture prepared for sentiment/event overlays using NLP and LLM-driven factors.

## Repository Structure
- `memory-bank/`: Persistent project documentation (project brief, product context, system patterns, tech context, active context, progress log).
- `AGENTS.md`: Operating instructions ensuring each session starts by reviewing the Memory Bank.

## Getting Started
1. Ensure Python 3.10+ is available.
2. Create and activate a virtual environment.
3. Install dependencies (list forthcoming as modules are implemented).
4. Populate cached historical data from Stooq or other free sources.
5. Run the CLI (to be added) to construct and evaluate portfolios.

## Status
- Documentation and repository scaffolding complete.
- Next steps involve implementing the modular CLI, data ingestion pipeline, and allocation engines.

## Contributing
Pull requests are welcome once contribution guidelines and tests are established. Keep the Memory Bank current after every meaningful change to preserve context across sessions.
