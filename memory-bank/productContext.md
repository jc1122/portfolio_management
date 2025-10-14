# Product Context

## Purpose

- Empower a long-horizon Polish investor to construct evidence-based portfolios combining global diversification, factor tilts (value, quality, small), and disciplined risk controls.
- Provide an auditable workflow that can evolve from purely historical analysis to sentiment-informed active tilts once the offline engine proves robust.

## Target Users

- Primary: Individual or small-scale asset manager in Poland investing via BOŚ Dom Maklerski and MDM, managing ~50k USD with periodic contributions.
- Secondary: Future collaborators who may extend the system with news analytics or alternative data overlays.

## Use Cases

- Run historical backtests of candidate portfolios using monthly/quarterly rebalancing while honoring commission and allocation constraints.
- Compare allocation engines (equal weight, risk parity, mean-variance) and record performance diagnostics for decision-making.
- Generate risk reports (ES 97.5%, max drawdown, realized volatility, factor exposure estimates) for portfolio review sessions.
- Stage future experiments where sentiment or event-driven factors adjust allocations within predefined satellite limits.

## Experience Principles

- Favor configuration over code changes; key parameters (assets, strategy, rebalance cadence) should be switchable via CLI flags or config files.
- Minimize custom quantitative code by leveraging vetted open-source libraries; keep implementation transparent and well-documented.
- Maintain low operational friction: reproducible runs, cached data, and concise textual/graphical outputs suitable for logbooks.
- Guard against behavioral drift by enforcing checklists and logging every rebalance decision.

## Outstanding Questions

- What presentation format (CLI summary, CSV, PDF report) best supports the user's review cadence?
- Are there regulatory or tax-reporting outputs that must be generated alongside performance metrics?
- Which factor exposure analytics are most valuable (e.g., regressions vs. heuristic tilts)?
- How will sentiment-driven overlays be governed to prevent excessive turnover or signal overfitting?
