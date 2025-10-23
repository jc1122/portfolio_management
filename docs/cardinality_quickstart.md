# Cardinality Constraints - Quick Start

## What Are Cardinality Constraints?

Cardinality constraints limit the **number of non-zero positions** in a portfolio. This is useful for:
- Reducing transaction costs (fewer positions to rebalance)
- Simplifying portfolio management
- Enforcing minimum position sizes

## Current Implementation: Preselection

The **preselection approach** is production-ready and recommended:

```python
from portfolio_management.portfolio import (
    Preselection,
    PreselectionConfig,
    PreselectionMethod,
)

# Select top 30 assets by 12-month momentum
config = PreselectionConfig(
    method=PreselectionMethod.MOMENTUM,
    top_k=30,
    lookback=252,  # 12 months daily
    skip=1,        # Exclude most recent day
)
preselection = Preselection(config)
selected_assets = preselection.select_assets(returns, rebalance_date)

# Then optimize with selected assets
filtered_returns = returns[selected_assets]
portfolio = strategy.construct(filtered_returns, constraints)
```

**Advantages:**
- ✅ Fast (milliseconds)
- ✅ Factor-driven (interpretable)
- ✅ No special dependencies
- ✅ Works with any optimizer

**See:** `docs/preselection.md` for full guide

## Future: Optimizer-Integrated Cardinality

Three approaches are **designed but not yet implemented**:

### 1. MIQP (Mixed-Integer Quadratic Programming)
- Globally optimal solutions
- Requires commercial solver (Gurobi/CPLEX)
- Best for small universes (<100 assets)

### 2. Heuristics (Greedy/Local Search)
- Good approximate solutions
- No special solver needed
- Fast even for large universes

### 3. Relaxation (Continuous + Rounding)
- Continuous optimization with sparsity penalty
- Post-process to enforce exact cardinality
- Fast but may lose some optimality

## Using Future Methods (Stub Example)

```python
from portfolio_management.portfolio import (
    CardinalityConstraints,
    CardinalityMethod,
    optimize_with_cardinality_miqp,
)

# This will raise CardinalityNotImplementedError
constraints = CardinalityConstraints(
    enabled=True,
    method=CardinalityMethod.MIQP,
    max_assets=30,
)

try:
    portfolio = optimize_with_cardinality_miqp(returns, constraints, cardinality)
except CardinalityNotImplementedError as e:
    print(f"Not yet implemented: {e}")
    # Fall back to preselection
```

## Configuration Reference

### CardinalityConstraints Dataclass

```python
@dataclass
class CardinalityConstraints:
    enabled: bool = False                        # Enable cardinality
    method: CardinalityMethod = PRESELECTION     # Method to use
    max_assets: int | None = None                # Max positions
    min_position_size: float = 0.01              # Min weight (1%)
    group_limits: dict[str, int] | None = None   # Per-group limits
    enforce_in_optimizer: bool = False           # Future: in-optimizer
```

### CardinalityMethod Enum

```python
class CardinalityMethod(Enum):
    PRESELECTION = "preselection"  # Current ✅
    MIQP = "miqp"                  # Future
    HEURISTIC = "heuristic"        # Future
    RELAXATION = "relaxation"      # Future
```

## Trade-offs Summary

| Approach | Speed | Optimality | Solver | Production |
|----------|-------|------------|--------|------------|
| **Preselection** | ⚡ Fast | Approximate | None | ✅ Ready |
| **MIQP** | 🐌 Slow | Optimal | Gurobi | ❌ Future |
| **Heuristic** | 🚀 Fast | Near-optimal | None | ❌ Future |
| **Relaxation** | ⚡ Fast | Approximate | None | ❌ Future |

## Recommendations

**Use preselection for:**
- Production workflows
- Large universes (>500 assets)
- When speed matters
- When factors align with strategy

**Consider MIQP for (when implemented):**
- Small universes (<100 assets)
- Research and development
- When you have Gurobi/CPLEX license
- When optimality is critical

**Consider heuristics for (when implemented):**
- Medium universes (100-500 assets)
- Production without commercial solvers
- Good-enough solutions acceptable

## Documentation

- **Quick Start**: `docs/cardinality_quickstart.md` (this file)
- **Full Design**: `docs/cardinality_constraints.md`
- **Preselection Guide**: `docs/preselection.md`
- **API Reference**: `src/portfolio_management/portfolio/cardinality.py`

## Extension Points

For future implementers:

1. **Optimizer functions**: `optimize_with_cardinality_*()`
2. **Validation**: `validate_cardinality_constraints()`
3. **Factory**: `get_cardinality_optimizer()`
4. **Tests**: `tests/portfolio/test_cardinality.py`

See `docs/cardinality_constraints.md` for implementation guidance.
