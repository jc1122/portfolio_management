# Cardinality Constraints in Portfolio Optimization

## Overview

This document describes the design for cardinality-constrained portfolio optimization, including current implementation (preselection) and future extension points for optimizer-integrated cardinality.

**Status**: Design phase with stubs for future implementation
**Current Implementation**: Preselection (factor-based filtering)
**Future Extensions**: MIQP, heuristics, relaxation methods

## What Are Cardinality Constraints?

Cardinality constraints limit the number of non-zero positions in a portfolio. This is useful for:

- **Transaction Cost Management**: Fewer positions = lower rebalancing costs
- **Operational Simplicity**: Easier to manage and monitor smaller portfolios
- **Minimum Investment Sizes**: Enforce practical position sizes (e.g., no positions \< $1,000)
- **Tax Efficiency**: Limit number of tax lots to track
- **Compliance**: Some mandates require concentrated portfolios

### Mathematical Formulation

Standard mean-variance optimization:

```
minimize    w'Σw
subject to  w'μ >= r_target
            Σw_i = 1
            0 <= w_i <= w_max
```

With cardinality constraint:

```
Additional:  ||w||_0 <= K    (at most K non-zero positions)
            w_i >= w_min or w_i = 0  (minimum position size)
```

This becomes a **Mixed-Integer Quadratic Program (MIQP)**, which is NP-hard.

## Design Architecture

### Current: Preselection Approach

**Implementation**: `src/portfolio_management/portfolio/preselection.py`

**How it works**:

1. Compute factor scores (momentum, low-volatility, or combined)
1. Rank assets by factor scores
1. Select top-K assets deterministically
1. Pass filtered universe to continuous optimizer

**Advantages**:

- ✅ Fast: Linear time complexity O(N)
- ✅ Deterministic and reproducible
- ✅ Factor-driven: Interpretable asset selection
- ✅ Works with any downstream optimizer
- ✅ No special solver requirements

**Limitations**:

- ❌ Two-stage process: Factor selection may not align with portfolio objectives
- ❌ May miss globally optimal sparse portfolios
- ❌ Factor assumptions (e.g., momentum predicts returns) may not hold

**Example**:

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
    lookback=252,  # 12 months of daily data
    skip=1,        # Exclude most recent day
)
preselection = Preselection(config)
selected_assets = preselection.select_assets(returns, rebalance_date)

# Then optimize using only selected assets
filtered_returns = returns[selected_assets]
portfolio = strategy.construct(filtered_returns, constraints)
```

### Future: Integrated Cardinality Optimization

**Implementation**: Stubs in `src/portfolio_management/portfolio/cardinality.py`

Three approaches are designed but not yet implemented:

#### 1. Mixed-Integer Quadratic Programming (MIQP)

**Approach**: Solve optimization with binary variables for asset selection

**Formulation**:

```
minimize    w'Σw
subject to  w'μ >= r_target
            Σw_i = 1
            Σz_i <= K            (cardinality constraint)
            w_i <= z_i           (if z_i=0 then w_i=0)
            w_min*z_i <= w_i     (minimum position size)
            z_i ∈ {0, 1}         (binary variable)
```

**Advantages**:

- ✅ Globally optimal solution (for convex objectives)
- ✅ Single-stage optimization
- ✅ Directly aligns sparsity with portfolio objectives

**Limitations**:

- ❌ Computationally expensive: NP-hard problem
- ❌ Requires commercial solver (Gurobi or CPLEX)
- ❌ Scales poorly: >200 assets may not converge
- ❌ License costs for commercial solvers

**Recommended Use Cases**:

- Small universes (\<100 assets)
- Research and strategy development
- When optimality is critical

**Implementation Requirements**:

- Gurobi or CPLEX Python bindings
- License for commercial solver
- Big-M formulation for binary constraints
- Estimated effort: 2-3 weeks

#### 2. Heuristic Optimization

**Approach**: Iterative algorithms to find good (not optimal) sparse portfolios

**Potential Algorithms**:

1. **Greedy Forward Selection**:

   - Start with empty portfolio
   - Iteratively add asset with best marginal contribution
   - Stop at K assets

1. **Greedy Backward Elimination**:

   - Start with full portfolio
   - Iteratively remove asset with least contribution
   - Stop at K assets

1. **Local Search**:

   - Start with initial solution (e.g., from preselection)
   - Iteratively swap assets to improve objective
   - Accept moves that reduce risk or increase Sharpe ratio

1. **Threshold-Based**:

   - Optimize without cardinality constraint
   - Threshold small weights to zero
   - Re-optimize with remaining assets

**Advantages**:

- ✅ Fast: Polynomial time complexity
- ✅ No special solver required
- ✅ Good approximate solutions (typically within 5-10% of optimal)
- ✅ Scalable to large universes (>500 assets)

**Limitations**:

- ❌ Suboptimal: May get stuck in local optima
- ❌ Solution quality depends on initialization
- ❌ No optimality guarantees

**Recommended Use Cases**:

- Medium to large universes (100-1000 assets)
- Production environments without commercial solvers
- When speed is more important than optimality

**Implementation Requirements**:

- Custom Python algorithms
- Multiple random restarts for robustness
- Warm-start from preselection
- Estimated effort: 3-4 weeks

#### 3. Continuous Relaxation + Rounding

**Approach**: Solve continuous relaxation with sparsity penalty, then round

**Process**:

1. Solve continuous optimization with L1 or elastic-net penalty:
   ```
   minimize    w'Σw + λ*||w||_1
   subject to  w'μ >= r_target
               Σw_i = 1
               w_i >= 0
   ```
1. Threshold weights: Keep top-K by magnitude
1. Re-normalize and optionally re-optimize

**Advantages**:

- ✅ Fast: Similar to standard continuous optimization
- ✅ No special solver required
- ✅ Smooth optimization landscape
- ✅ Mature optimization libraries available

**Limitations**:

- ❌ Two-stage process (optimize, then round)
- ❌ Rounding may degrade solution quality
- ❌ Penalty parameter (λ) requires tuning
- ❌ Hard cardinality constraint only approximated

**Recommended Use Cases**:

- When MIQP solver not available
- Exploratory analysis with varying sparsity levels
- Warm-start for other methods

**Implementation Requirements**:

- Extend CVXPY formulations with L1 penalty
- Rounding heuristics
- Parameter tuning utilities
- Estimated effort: 1-2 weeks

## Configuration Interface

### CardinalityConstraints Dataclass

Located in `src/portfolio_management/portfolio/constraints/models.py`:

```python
@dataclass(frozen=True)
class CardinalityConstraints:
    """Cardinality constraints for portfolio optimization.

    Attributes:
        enabled: Whether cardinality constraints are active
        method: Method for enforcing cardinality
        max_assets: Maximum number of non-zero positions
        min_position_size: Minimum weight for non-zero positions
        group_limits: Optional per-group position limits
        enforce_in_optimizer: Whether to enforce within optimizer

    """
    enabled: bool = False
    method: CardinalityMethod = CardinalityMethod.PRESELECTION
    max_assets: int | None = None
    min_position_size: float = 0.01
    group_limits: dict[str, int] | None = None
    enforce_in_optimizer: bool = False
```

### CardinalityMethod Enum

```python
class CardinalityMethod(str, Enum):
    PRESELECTION = "preselection"  # Current implementation
    MIQP = "miqp"                  # Future: Mixed-integer programming
    HEURISTIC = "heuristic"        # Future: Greedy algorithms
    RELAXATION = "relaxation"      # Future: Continuous + rounding
```

### Example Configurations

#### Simple Cardinality: Max 30 Assets

```python
from portfolio_management.portfolio import (
    CardinalityConstraints,
    CardinalityMethod,
)

constraints = CardinalityConstraints(
    enabled=True,
    method=CardinalityMethod.PRESELECTION,
    max_assets=30,
    min_position_size=0.02,  # Minimum 2% position
)
```

#### Group-Based Cardinality

```python
# Max 20 equity, 10 bonds, 30 total
constraints = CardinalityConstraints(
    enabled=True,
    max_assets=30,
    group_limits={
        "equity": 20,
        "fixed_income": 10,
    },
    min_position_size=0.01,
)
```

#### Future: MIQP Integration (stub)

```python
# This will raise CardinalityNotImplementedError
constraints = CardinalityConstraints(
    enabled=True,
    method=CardinalityMethod.MIQP,  # Not yet implemented
    max_assets=30,
    enforce_in_optimizer=True,
)
```

## Extension Points

### For Future Implementers

The codebase provides clear extension points for cardinality optimization:

1. **Optimizer Functions** (in `cardinality.py`):

   - `optimize_with_cardinality_miqp()` - MIQP implementation
   - `optimize_with_cardinality_heuristic()` - Heuristic algorithms
   - `optimize_with_cardinality_relaxation()` - Continuous relaxation

1. **Validation** (in `cardinality.py`):

   - `validate_cardinality_constraints()` - Check feasibility
   - Returns `CardinalityNotImplementedError` for non-preselection methods

1. **Factory** (in `cardinality.py`):

   - `get_cardinality_optimizer()` - Returns appropriate optimizer function

1. **Integration Points** (strategy classes):

   - Extend `PortfolioStrategy.construct()` to accept `CardinalityConstraints`
   - Call appropriate optimizer based on `method` field
   - Fall back to preselection for current implementation

### Testing Strategy

When implementing future methods:

1. **Unit Tests**:

   - Test each optimizer function independently
   - Validate constraint satisfaction
   - Test edge cases (empty universe, infeasible constraints)

1. **Integration Tests**:

   - Compare solutions across methods
   - Verify computational complexity
   - Test with real historical data

1. **Performance Tests**:

   - Benchmark runtime vs universe size
   - Measure solution quality vs MIQP baseline
   - Profile memory usage

1. **Regression Tests**:

   - Ensure preselection path still works
   - Verify backward compatibility
   - Test feature flag behavior

## Trade-off Analysis: Preselection vs Integrated

### Decision Matrix

| Criterion | Preselection | MIQP | Heuristic | Relaxation |
|-----------|-------------|------|-----------|------------|
| **Optimality** | Approximate | Optimal | Near-optimal | Approximate |
| **Speed (100 assets)** | \<1s | 10-60s | 1-5s | 1-3s |
| **Speed (500 assets)** | \<2s | May not converge | 5-30s | 3-10s |
| **Solver Required** | No | Gurobi/CPLEX | No | No |
| **Interpretability** | High | Low | Medium | Medium |
| **Implementation Effort** | ✅ Done | 2-3 weeks | 3-4 weeks | 1-2 weeks |
| **Production Ready** | ✅ Yes | No (license) | Maybe | Maybe |

### Recommendations

**Use Preselection When**:

- Production environment without commercial solvers
- Factor-based selection aligns with investment philosophy
- Speed and reliability are critical
- Universe size is large (>500 assets)

**Consider MIQP When**:

- Small universe (\<100 assets)
- Research and strategy development
- Have access to Gurobi/CPLEX license
- Optimality is worth computation time

**Consider Heuristics When**:

- Medium universe (100-500 assets)
- No commercial solver available
- Good-enough solutions acceptable
- Need faster than MIQP

**Consider Relaxation When**:

- Quick prototyping
- Warm-start for other methods
- Exploring trade-offs between sparsity and performance

## API Examples

### Current: Using Preselection

```python
from portfolio_management.portfolio import (
    Preselection,
    PreselectionConfig,
    PreselectionMethod,
    RiskParityStrategy,
    PortfolioConstraints,
)

# Step 1: Configure preselection
preselection_config = PreselectionConfig(
    method=PreselectionMethod.MOMENTUM,
    top_k=30,
    lookback=252,
)
preselection = Preselection(preselection_config)

# Step 2: Select assets
selected_assets = preselection.select_assets(
    returns=historical_returns,
    rebalance_date=rebalance_date,
)

# Step 3: Filter returns
filtered_returns = historical_returns[selected_assets]

# Step 4: Construct portfolio
constraints = PortfolioConstraints(max_weight=0.20)
strategy = RiskParityStrategy()
portfolio = strategy.construct(filtered_returns, constraints)
```

### Future: Using MIQP (stub)

```python
from portfolio_management.portfolio import (
    CardinalityConstraints,
    CardinalityMethod,
    optimize_with_cardinality_miqp,
    PortfolioConstraints,
)

# This will raise CardinalityNotImplementedError
cardinality = CardinalityConstraints(
    enabled=True,
    method=CardinalityMethod.MIQP,
    max_assets=30,
    enforce_in_optimizer=True,
)

try:
    portfolio = optimize_with_cardinality_miqp(
        returns=historical_returns,
        constraints=constraints,
        cardinality=cardinality,
    )
except CardinalityNotImplementedError as e:
    print(f"Not yet implemented: {e}")
    # Fall back to preselection
```

## References

### Academic Literature

1. **Bertsimas, D., & Shioda, R. (2009)**
   "Algorithm for cardinality-constrained quadratic optimization"
   _Computational Optimization and Applications_, 43(1), 1-22.

1. **Bienstock, D. (1996)**
   "Computational study of a family of mixed-integer quadratic programming problems"
   _Mathematical Programming_, 74(2), 121-140.

1. **Fastrich, B., Paterlini, S., & Winker, P. (2014)**
   "Constructing optimal sparse portfolios using regularization methods"
   _Computational Management Science_, 12(3), 417-434.

1. **Shaw, D. X., Liu, S., & Kopman, L. (2008)**
   "Lagrangian relaxation procedure for cardinality-constrained portfolio optimization"
   _Optimization Methods and Software_, 23(3), 411-420.

1. **Cesarone, F., Scozzari, A., & Tardella, F. (2013)**
   "A new method for mean-variance portfolio optimization with cardinality constraints"
   _Annals of Operations Research_, 205(1), 213-234.

### Software and Tools

- **Gurobi**: https://www.gurobi.com/
  Commercial MIQP solver with Python bindings

- **CPLEX**: https://www.ibm.com/analytics/cplex-optimizer
  IBM commercial MIQP solver

- **PyPortfolioOpt**: https://pyportfolioopt.readthedocs.io/
  Open-source portfolio optimization (no cardinality support)

- **CVXPY**: https://www.cvxpy.org/
  Python-embedded modeling language for convex optimization

## Implementation Roadmap

### Phase 1: Design & Stubs (Current)

- \[x\] Define `CardinalityConstraints` dataclass
- \[x\] Define `CardinalityMethod` enum
- \[x\] Create stub functions with comprehensive documentation
- \[x\] Define `CardinalityNotImplementedError`
- \[x\] Add validation utilities
- \[x\] Document trade-offs and design decisions

### Phase 2: MIQP Implementation (Future)

- \[ \] Integrate Gurobi/CPLEX Python bindings
- \[ \] Implement `optimize_with_cardinality_miqp()`
- \[ \] Add big-M constraint formulation
- \[ \] Write unit tests
- \[ \] Benchmark performance
- \[ \] Document solver setup

### Phase 3: Heuristic Implementation (Future)

- \[ \] Implement greedy forward selection
- \[ \] Implement greedy backward elimination
- \[ \] Implement local search algorithm
- \[ \] Add multiple restart logic
- \[ \] Write unit and integration tests
- \[ \] Compare against MIQP baseline

### Phase 4: Relaxation Implementation (Future)

- \[ \] Extend CVXPY models with L1 penalty
- \[ \] Implement rounding heuristics
- \[ \] Add parameter tuning utilities
- \[ \] Write tests
- \[ \] Compare against other methods

### Phase 5: Production Integration (Future)

- \[ \] Update strategy classes to accept cardinality constraints
- \[ \] Add CLI flags for cardinality configuration
- \[ \] Update universe YAML schema
- \[ \] Write end-to-end integration tests
- \[ \] Update user documentation

## FAQ

**Q: Why not implement MIQP now?**
A: Requires commercial solver license (Gurobi/CPLEX) which may not be available in all environments. Preselection provides a good alternative without dependencies.

**Q: Can I use both preselection and cardinality constraints?**
A: Yes! You can use preselection to reduce universe size, then apply integrated cardinality within the optimizer (when implemented).

**Q: What's the difference between max_assets and preselection top_k?**
A: `top_k` is factor-based filtering before optimization. `max_assets` is a constraint during optimization. They can be different values.

**Q: How do group_limits work?**
A: They enforce position limits per asset class (e.g., max 20 equity positions, max 10 bond positions), in addition to overall `max_assets`.

**Q: What if my constraints are infeasible?**
A: `validate_cardinality_constraints()` will raise `ValueError` with a clear message about the infeasibility.

**Q: Can I implement custom cardinality methods?**
A: Yes! Follow the signature of stub functions in `cardinality.py` and add your method to `CardinalityMethod` enum.

## Conclusion

This design establishes a clear path for cardinality-constrained optimization while maintaining backward compatibility with the current preselection approach. The stub implementations provide:

1. **Type-safe interfaces** for future extensions
1. **Clear documentation** of trade-offs and design decisions
1. **Validation utilities** to catch configuration errors early
1. **Extension points** that minimize future code changes
1. **Production-ready preselection** as the current implementation

Future implementers can follow the roadmap to add MIQP, heuristic, or relaxation methods without breaking existing code.
