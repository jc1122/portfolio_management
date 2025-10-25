# Module Dependencies

## Module Hierarchy

The portfolio management toolkit follows a layered architecture where higher layers can depend on lower layers, but not vice versa:

```
┌─────────────────────────────────────────┐
│          scripts (CLI layer)            │  ← Entry points
├─────────────────────────────────────────┤
│         reporting (output)              │  ← Visualization, exports
├─────────────────────────────────────────┤
│       backtesting (simulation)          │  ← Backtest engine
├─────────────────────────────────────────┤
│      portfolio (construction)           │  ← Strategies, constraints
├─────────────────────────────────────────┤
│        analytics (calculations)         │  ← Returns, metrics
├─────────────────────────────────────────┤
│        assets (universe)                │  ← Selection, classification
├─────────────────────────────────────────┤
│         data (I/O)                      │  ← Ingestion, matching
├─────────────────────────────────────────┤
│         core (foundation)               │  ← Exceptions, types, utils
└─────────────────────────────────────────┘
```

## Allowed Dependencies

### Layer 0: core
- **Depends on:** NOTHING (foundation layer)
- **Provides:** Exceptions, types, protocols, utilities
- **Files:** `src/portfolio_management/core/`

### Layer 1: data
- **Depends on:** core
- **Provides:** Data ingestion, I/O, matching, caching
- **Files:** `src/portfolio_management/data/`
- **NOT allowed:** assets, analytics, portfolio, backtesting, reporting

### Layer 2: assets
- **Depends on:** core, data
- **Provides:** Asset selection, classification, universe management
- **Files:** `src/portfolio_management/assets/`
- **NOT allowed:** analytics, portfolio, backtesting, reporting

### Layer 3: analytics
- **Depends on:** core, data, assets
- **Provides:** Returns calculation, metrics, indicators
- **Files:** `src/portfolio_management/analytics/`
- **NOT allowed:** portfolio, backtesting, reporting

### Layer 4: portfolio
- **Depends on:** core, data, assets, analytics
- **Provides:** Portfolio construction, strategies, constraints
- **Files:** `src/portfolio_management/portfolio/`
- **NOT allowed:** backtesting, reporting

### Layer 5: backtesting
- **Depends on:** core, data, assets, analytics, portfolio
- **Provides:** Backtest engine, transaction modeling, performance
- **Files:** `src/portfolio_management/backtesting/`
- **NOT allowed:** reporting (backtesting should not know about visualization)

### Layer 6: reporting
- **Depends on:** core, backtesting (for results), portfolio (for weights)
- **Provides:** Visualization, chart generation, exports
- **Files:** `src/portfolio_management/reporting/`
- **Can depend on:** All layers (top layer)

### Layer 7: scripts
- **Depends on:** ALL modules (orchestration layer)
- **Provides:** CLI entry points, workflow orchestration
- **Files:** `scripts/`

## Special Module: macro

The `macro` module is currently a stub for future macroeconomic signals:
- **Depends on:** core, data
- **Provides:** Macro signal providers, regime gating
- **Files:** `src/portfolio_management/macro/`
- **Status:** NoOp stubs, minimal dependencies

## Forbidden Patterns

### ❌ Circular Dependencies
```python
# BAD: data imports from assets
# data/loader.py
from portfolio_management.assets import AssetSelector  # FORBIDDEN
```

### ❌ Lower Layer Depending on Higher Layer
```python
# BAD: core importing from data
# core/utils.py
from portfolio_management.data import PriceLoader  # FORBIDDEN
```

### ❌ Skipping Layers Inappropriately
```python
# QUESTIONABLE: backtesting importing from data (skip analytics/portfolio)
# backtesting/engine.py
from portfolio_management.data import load_prices  # Use analytics.returns instead
```

## Allowed Patterns

### ✅ Higher Layer Depending on Lower Layer
```python
# GOOD: portfolio imports from analytics
# portfolio/strategies/risk_parity.py
from portfolio_management.analytics.returns import calculate_returns
```

### ✅ Same Layer Imports (within module)
```python
# GOOD: Within same module
# assets/selection/selector.py
from portfolio_management.assets.classification import classify_asset
```

### ✅ Scripts Import Everything
```python
# GOOD: scripts can orchestrate all modules
# scripts/run_backtest.py
from portfolio_management.data import load_data
from portfolio_management.assets import select_assets
from portfolio_management.portfolio import construct_portfolio
from portfolio_management.backtesting import run_backtest
```

## Validation

Use `import-linter` to enforce these rules automatically:

```bash
# Check architecture
lint-imports

# CI/CD integration
lint-imports --config .importlinter
```

See `.importlinter` file for detailed contract definitions.
