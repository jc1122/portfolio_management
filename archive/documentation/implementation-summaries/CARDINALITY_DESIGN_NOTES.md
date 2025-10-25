# Cardinality Constraints: Design Notes & Trade-offs

**Status**: Design Phase - Stubs Implemented
**Date**: 2025-10-23
**Issue**: #35 - Advanced cardinality (design only): optimizer-integrated selection stub

## Executive Summary

This document provides design notes comparing **preselection** (current implementation) with **optimizer-integrated cardinality** (future extension points). The implementation includes:

1. Type-safe interfaces (`CardinalityConstraints`, `CardinalityMethod`)
1. Validation utilities with clear error messages
1. Stub functions for three future approaches (MIQP, Heuristic, Relaxation)
1. Comprehensive documentation and 89 unit tests

**Current Recommendation**: Use preselection for production. Consider integrated methods for research when commercial solvers or custom algorithms are available.

## Comparison: Preselection vs Integrated Cardinality

### Preselection (Current Implementation)

**Location**: `src/portfolio_management/portfolio/preselection.py`

**Approach**:

1. Compute factor scores (momentum, low-volatility, or combined)
1. Rank all assets by factor scores
1. Select top-K assets deterministically
1. Pass filtered universe to continuous optimizer

**Mathematical View**:

- Factor selection: `S = top_K(factor_score(R))`
- Optimization: `min w'Σw` over `S` only

**Advantages**:

- ✅ **Speed**: O(N log N) complexity, typically \<1 second for 1000 assets
- ✅ **Interpretability**: Factor-driven selection is transparent and explainable
- ✅ **Deterministic**: Same inputs always produce same outputs (ties broken alphabetically)
- ✅ **No Dependencies**: Works without commercial solvers or specialized libraries
- ✅ **Flexibility**: Works with any downstream optimizer (mean-variance, risk parity, etc.)
- ✅ **Mature**: Battle-tested in production, well-documented

**Limitations**:

- ❌ **Two-Stage**: Factor selection and optimization are separate, may not align
- ❌ **Suboptimal**: Selected assets may not be the globally optimal sparse portfolio
- ❌ **Factor Assumptions**: Assumes factors (e.g., momentum) predict portfolio objectives
- ❌ **Local to Factor**: Cannot easily incorporate portfolio-level considerations in selection

**When to Use**:

- Production environments (speed + reliability critical)
- Large universes (>500 assets)
- Factor-tilted strategies (momentum, low-vol preferences)
- When interpretability matters
- When no commercial solvers available

### MIQP (Future - Design Stub)

**Location**: `src/portfolio_management/portfolio/cardinality.py::optimize_with_cardinality_miqp()`

**Approach**: Mixed-Integer Quadratic Programming with binary variables

**Mathematical Formulation**:

```
minimize    w'Σw
subject to  w'μ >= r_target
            Σw_i = 1
            Σz_i <= K            (cardinality constraint)
            w_i <= z_i           (if z_i=0 then w_i=0)
            w_min*z_i <= w_i     (minimum position size)
            z_i ∈ {0, 1}         (binary selection variable)
```

**Advantages**:

- ✅ **Globally Optimal**: Finds the true optimal sparse portfolio (for convex objectives)
- ✅ **Single-Stage**: Selection and optimization are integrated
- ✅ **Theoretically Sound**: Well-studied in operations research literature
- ✅ **Flexible Objectives**: Can optimize Sharpe, risk, tracking error, etc.

**Limitations**:

- ❌ **Computationally Expensive**: NP-hard problem, exponential worst-case complexity
- ❌ **Commercial Solver Required**: Needs Gurobi ($1500-15000/year) or CPLEX ($1000+/year)
- ❌ **Scalability Issues**: >200 assets may not converge in reasonable time
- ❌ **License Management**: Additional operational overhead and costs
- ❌ **Less Interpretable**: Selected assets driven by optimization, not transparent factors

**Implementation Requirements**:

- Gurobi 10.0+ or CPLEX 22.1+ Python bindings
- Big-M constraint formulation for logical implications
- Warm-start from preselection to improve convergence
- Estimated effort: 2-3 weeks development + testing

**Expected Performance**:

- Small universes (20-50 assets): 1-10 seconds, reliable convergence
- Medium universes (50-100 assets): 10-60 seconds, usually converges
- Large universes (100-200 assets): 1-10 minutes, may struggle
- Very large (>200 assets): May not converge, warm-start essential

**When to Use** (once implemented):

- Small universes (\<100 assets)
- Research and strategy development
- When optimality is worth computation time
- When Gurobi/CPLEX license available
- When factor-neutral selection desired

### Heuristic (Future - Design Stub)

**Location**: `src/portfolio_management/portfolio/cardinality.py::optimize_with_cardinality_heuristic()`

**Approach**: Iterative algorithms (greedy forward/backward, local search)

**Potential Algorithms**:

1. **Greedy Forward Selection**:

   ```python
   S = {}
   while |S| < K:
       i* = argmin_i objective(S ∪ {i})
       S = S ∪ {i*}
   ```

1. **Greedy Backward Elimination**:

   ```python
   S = all assets
   while |S| > K:
       i* = argmin_i objective(S \ {i})
       S = S \ {i*}
   ```

1. **Local Search with Swaps**:

   ```python
   S = initial solution (e.g., from preselection)
   while improving:
       Try swapping assets in S with assets outside S
       Accept swaps that improve objective
   ```

**Advantages**:

- ✅ **Fast**: Polynomial time, typically 1-30 seconds even for 500+ assets
- ✅ **No Special Solver**: Pure Python implementation possible
- ✅ **Near-Optimal**: Typically within 5-10% of MIQP solution quality
- ✅ **Scalable**: Works well for large universes
- ✅ **Flexible**: Can incorporate domain knowledge in heuristic design

**Limitations**:

- ❌ **Suboptimal**: No optimality guarantees, may get stuck in local optima
- ❌ **Algorithm Complexity**: Multiple variants to implement and tune
- ❌ **Initialization Sensitive**: Solution quality depends on starting point
- ❌ **Multiple Restarts Needed**: Random restarts improve but add computation time

**Implementation Requirements**:

- Custom Python algorithms (greedy selection, local search)
- Multiple restart logic for robustness
- Warm-start from preselection
- Performance benchmarking against MIQP baseline
- Estimated effort: 3-4 weeks development + extensive testing

**Expected Performance**:

- Small universes (\<100 assets): \<1 second, good quality
- Medium universes (100-500 assets): 1-10 seconds, good quality
- Large universes (>500 assets): 10-30 seconds, acceptable quality

**When to Use** (once implemented):

- Medium to large universes (100-1000 assets)
- Production without commercial solvers
- When good-enough solutions acceptable
- When speed more important than perfection
- When multiple solution candidates desired (via restarts)

### Relaxation (Future - Design Stub)

**Location**: `src/portfolio_management/portfolio/cardinality.py::optimize_with_cardinality_relaxation()`

**Approach**: Continuous optimization with sparsity penalty + post-processing

**Process**:

1. **Solve Continuous Relaxation**:

   ```
   minimize    w'Σw + λ*||w||_1
   subject to  w'μ >= r_target
               Σw_i = 1
               w_i >= 0
   ```

1. **Threshold Weights**: Keep top-K by magnitude, zero out rest

1. **Re-normalize**: Scale remaining weights to sum to 1.0

1. **Optional Re-optimize**: Solve continuous problem over remaining K assets

**Advantages**:

- ✅ **Fast**: Similar speed to standard continuous optimization
- ✅ **No Special Solver**: Works with standard CVXPY/PyPortfolioOpt
- ✅ **Smooth Landscape**: Continuous optimization avoids integer variables
- ✅ **Easy to Implement**: Extend existing optimization code with L1 penalty

**Limitations**:

- ❌ **Two-Stage**: Optimization + rounding, similar to preselection
- ❌ **Rounding Degrades Quality**: Post-processing can hurt portfolio quality
- ❌ **Approximate Cardinality**: L1 penalty encourages sparsity but doesn't guarantee exact K
- ❌ **Parameter Tuning**: Regularization strength (λ) requires careful tuning

**Implementation Requirements**:

- Extend CVXPY models with L1 or elastic-net penalty
- Implement rounding/thresholding heuristics
- Parameter tuning utilities (cross-validation for λ)
- Optional: local refinement after rounding
- Estimated effort: 1-2 weeks development + tuning

**Expected Performance**:

- All universe sizes: Similar to continuous optimization (1-10 seconds)
- Solution quality: Depends on λ tuning, typically 10-20% worse than MIQP

**When to Use** (once implemented):

- Exploratory analysis with varying sparsity levels
- Warm-start for MIQP or heuristics
- When MIQP solver unavailable but better than preselection desired
- When L1-type sparsity aligns with investment philosophy

## Decision Matrix

| Criterion | Preselection | MIQP | Heuristic | Relaxation |
|-----------|-------------|------|-----------|------------|
| **Optimality** | Approximate | Optimal ✅ | Near-optimal | Approximate |
| **Speed (100 assets)** | \<1s ✅ | 10-60s | 1-5s | 1-3s |
| **Speed (500 assets)** | \<2s ✅ | May not converge ❌ | 5-30s | 3-10s |
| **Solver Required** | None ✅ | Gurobi/CPLEX ❌ | None ✅ | None ✅ |
| **Interpretability** | High ✅ | Low | Medium | Medium |
| **Implementation** | ✅ Done | 2-3 weeks | 3-4 weeks | 1-2 weeks |
| **Production Ready** | ✅ Yes | No (license) | Future | Future |
| **Factor-Driven** | Yes ✅ | No | No | No |
| **Single-Stage** | No | Yes ✅ | Yes ✅ | No |
| **Scalability** | Excellent ✅ | Poor ❌ | Good | Good |

## Trade-off Analysis

### Computation vs Optimality

```
Optimality
    ^
    |  MIQP
    |    ●
    |        Heuristic
    |            ●
    |                Relaxation
    |                    ●
    |                        Preselection
    |                            ●
    +--------------------------------> Computation Time
      Fast                          Slow
```

### Implementation Effort vs Value

```
Value
(Production)
    ^
    | Preselection
    |    ● (Done)
    |
    |        Heuristic
    |            ●
    |
    |                Relaxation
    |                    ●
    |
    |                            MIQP
    |                                ●
    +--------------------------------> Implementation Effort
      Low                            High
```

## Design Decisions & Rationale

### Decision 1: Implement Preselection First

**Rationale**:

- Fastest to implement and test
- No external dependencies
- Meets 80% of use cases
- Serves as baseline for comparisons
- Can co-exist with future methods

**Alternative Considered**: MIQP first
**Rejected Because**: License costs, limited scalability, complex implementation

### Decision 2: Use Enum for Method Selection

**Rationale**:

- Type-safe method specification
- Clear error messages for invalid methods
- Easy to extend (add new methods)
- Self-documenting code

**Alternative Considered**: String-based configuration
**Rejected Because**: Prone to typos, less IDE support, weaker typing

### Decision 3: Separate Validation Function

**Rationale**:

- Early detection of configuration errors
- Clearer error messages with context
- Reusable across different entry points
- Testable independently

**Alternative Considered**: Validation in optimizer functions
**Rejected Because**: Error detection too late, duplicated logic

### Decision 4: Comprehensive Documentation First

**Rationale**:

- Clarifies design before implementation
- Reduces implementation rework
- Makes trade-offs explicit
- Guides future implementers

**Alternative Considered**: Minimal docs, implement first
**Rejected Because**: Design clarity prevents costly mistakes

### Decision 5: Stubs Raise Specific Exception

**Rationale**:

- Clear distinction between not-implemented vs actual errors
- Informative error messages guide users
- Prevents silent failures
- Easy to check for in calling code

**Alternative Considered**: Generic NotImplementedError
**Rejected Because**: Less helpful error messages, harder to handle

## Implementation Roadmap

### Phase 0: Design & Stubs ✅ COMPLETE

- \[x\] Define CardinalityConstraints dataclass
- \[x\] Define CardinalityMethod enum
- \[x\] Create stub functions with comprehensive documentation
- \[x\] Define CardinalityNotImplementedError
- \[x\] Add validation utilities
- \[x\] Document trade-offs and design decisions
- \[x\] Write unit tests (89 test cases)
- \[x\] Update user documentation

### Phase 1: Relaxation Method (Easiest)

**Estimated Effort**: 1-2 weeks
**Complexity**: Low
**Value**: Medium

- \[ \] Extend CVXPY models with L1/elastic-net penalty
- \[ \] Implement thresholding heuristics
- \[ \] Add parameter tuning utilities
- \[ \] Benchmark vs preselection
- \[ \] Integration tests

**Rationale**: Easiest to implement, provides learning before harder methods

### Phase 2: Heuristic Methods (Most Practical)

**Estimated Effort**: 3-4 weeks
**Complexity**: Medium
**Value**: High

- \[ \] Implement greedy forward selection
- \[ \] Implement greedy backward elimination
- \[ \] Implement local search with swaps
- \[ \] Add multiple restart logic
- \[ \] Warm-start from preselection
- \[ \] Extensive performance testing
- \[ \] Compare against MIQP (if available)

**Rationale**: Production-ready solution without commercial solvers

### Phase 3: MIQP Integration (Optimal)

**Estimated Effort**: 2-3 weeks + license setup
**Complexity**: Medium
**Value**: Medium (limited by license requirement)

- \[ \] Integrate Gurobi/CPLEX Python bindings
- \[ \] Implement big-M formulation
- \[ \] Add warm-start logic
- \[ \] Performance profiling
- \[ \] Fallback logic when solver unavailable
- \[ \] Document solver setup

**Rationale**: Provides optimal baseline for research, but limited production use

### Phase 4: Production Integration

**Estimated Effort**: 1-2 weeks
**Complexity**: Low
**Value**: High

- \[ \] Update strategy classes to accept CardinalityConstraints
- \[ \] Add CLI flags for cardinality configuration
- \[ \] Update universe YAML schema
- \[ \] End-to-end integration tests
- \[ \] Update user guides
- \[ \] Performance optimization

## Open Questions

1. **Q**: Should we support combined approach (preselection + MIQP)?
   **A**: Yes, makes sense - use preselection to reduce to 100 assets, then MIQP for final 30

1. **Q**: How to handle infeasible cardinality constraints?
   **A**: Validation function raises clear error, suggests fixes (e.g., reduce min_position_size)

1. **Q**: Should group_limits be enforced exactly or as soft constraints?
   **A**: Start with hard constraints (raise error if violated), add soft constraints later if needed

1. **Q**: Performance monitoring for optimizer methods?
   **A**: Add optional timing/logging, expose via metadata in Portfolio object

1. **Q**: How to choose between methods programmatically?
   **A**: Heuristic based on universe size, solver availability, time budget - add helper function

## References

### Academic Papers

1. **Bertsimas & Shioda (2009)** - Algorithm for cardinality-constrained QP
   _Computational Optimization and Applications_, 43(1), 1-22

1. **Fastrich et al. (2014)** - Constructing optimal sparse portfolios
   _Computational Management Science_, 12(3), 417-434

1. **Cesarone et al. (2013)** - New method for mean-variance with cardinality
   _Annals of Operations Research_, 205(1), 213-234

### Software & Libraries

- **Gurobi** - https://www.gurobi.com/ (Commercial MIQP solver)
- **CPLEX** - https://www.ibm.com/analytics/cplex-optimizer (IBM solver)
- **CVXPY** - https://www.cvxpy.org/ (Convex optimization modeling)
- **PyPortfolioOpt** - https://pyportfolioopt.readthedocs.io/ (Portfolio optimization)

## Conclusion

This design establishes a clear path from the current **preselection** approach to future **optimizer-integrated cardinality** methods. Key design principles:

1. **Pragmatic First**: Implement working solution (preselection) before perfect solution
1. **Clear Extension Points**: Stub functions and interfaces make future work straightforward
1. **Comprehensive Documentation**: Trade-offs explicitly stated, decisions justified
1. **Type Safety**: Enums and dataclasses catch errors early
1. **Testable**: 89 unit tests validate interfaces and error handling

The preselection method is production-ready and recommended for most use cases. Future integrated methods provide clear value for specific scenarios (small universes with MIQP, large universes with heuristics) without breaking existing code.

**Next Step**: Implement Phase 1 (Relaxation) when continuous optimization with L1 regularization is needed for research, or Phase 2 (Heuristics) when production use without commercial solvers is prioritized.
