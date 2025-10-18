# Portfolio Construction

This document outlines the Phase 4 portfolio construction toolkit that sits on top of the asset selection and return preparation pipelines delivered in earlier phases.

## Overview

The construction stack provides:

- A standardised exception hierarchy (`PortfolioConstructionError` and subclasses) with descriptive context to aid CLI and downstream tooling.
- Strategy implementations that convert aligned return series into target weights:
  - **Equal Weight** – 1/N baseline with guardrails for asset class limits.
  - **Risk Parity** – Equal risk contribution using the `riskparityportfolio` optimiser.
  - **Mean Variance** – PyPortfolioOpt-backed optimiser supporting multiple objectives.
- A `PortfolioConstructor` orchestrator that registers strategies, enforces constraints, and exposes comparison utilities.
- A CLI entrypoint (`scripts/construct_portfolio.py`) to construct or compare portfolios from prepared CSV inputs.

## Constraints & Configuration

`PortfolioConstraints` captures the guardrails used throughout the strategies:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `max_weight` | Upper bound on any asset weight | 0.25 |
| `min_weight` | Lower bound on any asset weight | 0.0 |
| `max_equity_exposure` | Aggregate equity allocation limit | 0.90 |
| `min_bond_exposure` | Minimum bond/cash allocation | 0.10 |
| `sector_limits` | Optional sector → max-weight mapping | `None` |
| `require_full_investment` | Enforce weights sum to 1 | `True` |

Asset class exposures (equity vs. bond/cash) are validated whenever classifications are supplied. Sector limits are optional and only applied if the supplied classifications contain the relevant sectors.

## Strategy Summary

### Equal Weight Strategy

- Requires only the presence of return columns.
- Fails fast when `max_weight` is tighter than 1/N or when asset class constraints would be breached.

### Risk Parity Strategy

- Requires `riskparityportfolio`.
- Validates covariance positive semi-definiteness before optimisation and projects the resulting weights back onto the feasible set.
- Exposes marginal risk contributions in the portfolio metadata for diagnostics.

### Mean Variance Strategy

- Requires `PyPortfolioOpt` and a convex solver backend (`cvxpy`).
- Supports `max_sharpe`, `min_volatility`, and `efficient_risk` objectives.
- Injects sector limits and asset class exposure constraints directly into the optimisation problem.
- Returns portfolio metadata containing expected return, volatility, Sharpe ratio, and the selected objective.

## Portfolio Constructor

```python
from portfolio_management.portfolio import PortfolioConstructor

constructor = PortfolioConstructor()
portfolio = constructor.construct("equal_weight", returns_df)
comparison = constructor.compare_strategies(["equal_weight", "risk_parity"], returns_df)
```

The constructor registers the baseline strategies out of the box, while allowing additional adapters via `register_strategy`.

## CLI Usage

```bash
python scripts/construct_portfolio.py \
  --returns data/processed/universe_returns.csv \
  --strategy equal_weight \
  --max-weight 0.30 \
  --output outputs/portfolio_equal_weight.csv
```

Comparison mode calls `PortfolioConstructor.compare_strategies` and emits a weight table where columns correspond to strategies.

```bash
python scripts/construct_portfolio.py \
  --returns data/processed/universe_returns.csv \
  --compare \
  --output outputs/portfolio_comparison.csv
```

## Error Handling

All strategy-level failures funnel through `PortfolioConstructionError` subclasses:

- `DependencyError` – Optional package (e.g. PyPortfolioOpt) missing.
- `InsufficientDataError` – Not enough historical periods for the chosen strategy.
- `ConstraintViolationError` – Constraint guardrails breached (exposes `constraint_name` and `violated_value`).
- `OptimizationError` – Backend optimisers could not converge.
- `InvalidStrategyError` – Requested strategy not registered with the constructor.

The CLI converts these into exit code `1`, while unexpected failures bubble up as exit code `2`.

## Next Steps

- Extend coverage with advanced objectives (efficient frontier sweeps, Black–Litterman overlays).
- Add persistent metadata exports (JSON) for audit trails.
- Integrate with the forthcoming backtesting engine to feed constructed weights into simulation runs.
