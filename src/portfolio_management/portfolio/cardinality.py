"""Cardinality-constrained portfolio optimization (design stubs).

This module defines interfaces and stubs for future cardinality-constrained
optimization methods. Currently, cardinality constraints are handled via
preselection (see preselection.py), but this module establishes extension
points for integrated cardinality enforcement within optimizers.

Design Overview:
    - MIQP approach: Mixed-Integer Quadratic Programming (requires Gurobi/CPLEX)
    - Heuristic approach: Iterative algorithms (greedy selection, local search)
    - Relaxation approach: Continuous optimization + post-processing

Trade-offs vs Preselection:
    
    Preselection (Current):
        ✓ Fast and deterministic
        ✓ Factor-driven asset selection
        ✓ No special solver requirements
        ✓ Works with any downstream optimizer
        ✗ Two-stage process (select, then optimize)
        ✗ May miss globally optimal sparse portfolios
        ✗ Factor assumptions may not align with portfolio objectives
    
    Integrated Cardinality (Future):
        ✓ Single-stage optimization
        ✓ Globally optimal solutions (MIQP) or good approximations (heuristics)
        ✓ Directly aligns sparsity with portfolio objectives
        ✗ Computationally expensive (MIQP: NP-hard)
        ✗ May require commercial solvers (MIQP)
        ✗ Less interpretable asset selection
        ✗ Convergence challenges with heuristics

Recommendation:
    - Use preselection for production workflows (fast, reliable)
    - Consider integrated methods for research and strategy development
    - MIQP for small universes (<100 assets) with commercial solvers
    - Heuristics for medium universes (100-500 assets) without solvers

References:
    - Bertsimas & Shioda (2009): "Algorithm for cardinality-constrained QP"
    - Bienstock (1996): "Computational study of a family of MIQP problems"
    - Fastrich et al. (2014): "Constructing optimal sparse portfolios"
    - Shaw et al. (2008): "Lagrangian relaxation procedure for cardinality"

"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from .constraints.models import CardinalityConstraints, PortfolioConstraints
    from .models import Portfolio


class CardinalityNotImplementedError(NotImplementedError):
    """Raised when attempting to use unimplemented cardinality methods.
    
    This exception is raised when a cardinality constraint method other than
    PRESELECTION is specified but not yet implemented. This is expected behavior
    for design stubs.
    
    Attributes:
        method: The cardinality method that was attempted
        message: Descriptive error message with implementation guidance
    
    """
    
    def __init__(self, method: str, available_methods: list[str] | None = None) -> None:
        """Initialize exception with method information.
        
        Args:
            method: The cardinality method that was attempted
            available_methods: List of currently implemented methods
        
        """
        self.method = method
        self.available_methods = available_methods or ["preselection"]
        
        msg = (
            f"Cardinality method '{method}' is not yet implemented. "
            f"This is a design stub for future optimizer-integrated cardinality.\n\n"
            f"Currently available: {', '.join(self.available_methods)}\n\n"
            f"Future implementation path:\n"
            f"  - MIQP: Requires commercial solver (Gurobi/CPLEX) integration\n"
            f"  - Heuristic: Implement greedy/local search algorithms\n"
            f"  - Relaxation: Implement continuous relaxation + rounding\n\n"
            f"For now, use preselection (see preselection.py module)."
        )
        super().__init__(msg)


def validate_cardinality_constraints(
    constraints: CardinalityConstraints,
    portfolio_constraints: PortfolioConstraints,
    num_assets: int,
) -> None:
    """Validate cardinality constraints for feasibility.
    
    Checks that cardinality constraints are internally consistent and
    compatible with portfolio constraints.
    
    Args:
        constraints: Cardinality constraints to validate
        portfolio_constraints: Portfolio-level constraints
        num_assets: Number of assets in the universe
    
    Raises:
        ValueError: If constraints are infeasible or inconsistent
        CardinalityNotImplementedError: If non-preselection method specified
    
    """
    if not constraints.enabled:
        return
    
    # Check for unimplemented methods
    from .constraints.models import CardinalityMethod
    
    try:
        method = CardinalityMethod(constraints.method)
    except ValueError as exc:
        raise CardinalityNotImplementedError(
            method=str(constraints.method),
            available_methods=[CardinalityMethod.PRESELECTION.value],
        ) from exc

    if method != CardinalityMethod.PRESELECTION:
        raise CardinalityNotImplementedError(
            method=method.value,
            available_methods=[CardinalityMethod.PRESELECTION.value],
        )
    
    # Validate max_assets vs universe size
    if constraints.max_assets is not None and constraints.max_assets > num_assets:
        msg = (
            f"max_assets ({constraints.max_assets}) exceeds universe size ({num_assets})"
        )
        raise ValueError(msg)
    
    # Validate min_position_size compatibility with max_assets
    if constraints.max_assets is not None and constraints.min_position_size > 0:
        min_total_weight = constraints.max_assets * constraints.min_position_size
        if min_total_weight > 1.0 and portfolio_constraints.require_full_investment:
            msg = (
                f"Infeasible: max_assets={constraints.max_assets} × "
                f"min_position_size={constraints.min_position_size} = "
                f"{min_total_weight:.3f} > 1.0"
            )
            raise ValueError(msg)
    
    # Validate group_limits consistency
    if constraints.group_limits is not None and constraints.max_assets is not None:
        total_group_limits = sum(constraints.group_limits.values())
        if total_group_limits < constraints.max_assets:
            msg = (
                f"Sum of group_limits ({total_group_limits}) is less than "
                f"max_assets ({constraints.max_assets}), which may be infeasible"
            )
            # This is a warning condition, not an error
            import warnings
            warnings.warn(msg, UserWarning, stacklevel=2)


def optimize_with_cardinality_miqp(
    returns: pd.DataFrame,
    constraints: PortfolioConstraints,
    cardinality: CardinalityConstraints,
    asset_classes: pd.Series | None = None,
) -> Portfolio:
    """Optimize portfolio with cardinality via MIQP (design stub).
    
    This is a design stub for future MIQP-based cardinality optimization.
    When implemented, this will use Mixed-Integer Quadratic Programming to
    find the optimal sparse portfolio subject to cardinality constraints.
    
    Implementation Requirements:
        - Commercial solver: Gurobi or CPLEX with Python bindings
        - Binary variable z_i for each asset (z_i=1 if w_i > 0)
        - Constraint: sum(z_i) <= max_assets
        - Constraint: w_i <= z_i (big-M formulation)
        - Objective: Minimize risk or maximize Sharpe ratio
    
    Expected Performance:
        - Small universes (<50 assets): Seconds to optimal solution
        - Medium universes (50-200 assets): Minutes to optimal solution
        - Large universes (>200 assets): May not converge in reasonable time
    
    Args:
        returns: Historical returns DataFrame
        constraints: Portfolio constraints
        cardinality: Cardinality constraints
        asset_classes: Optional asset class mapping
    
    Returns:
        Portfolio with optimal sparse weights
    
    Raises:
        CardinalityNotImplementedError: Always (not yet implemented)
    
    """
    raise CardinalityNotImplementedError(
        method="miqp",
        available_methods=["preselection"],
    )


def optimize_with_cardinality_heuristic(
    returns: pd.DataFrame,
    constraints: PortfolioConstraints,
    cardinality: CardinalityConstraints,
    asset_classes: pd.Series | None = None,
) -> Portfolio:
    """Optimize portfolio with cardinality via heuristics (design stub).
    
    This is a design stub for future heuristic-based cardinality optimization.
    When implemented, this will use iterative algorithms to find good (not
    necessarily optimal) sparse portfolios.
    
    Potential Algorithms:
        1. Greedy forward selection: Start with empty portfolio, add assets one-by-one
        2. Greedy backward elimination: Start with full portfolio, remove assets one-by-one
        3. Local search: Start with initial solution, iteratively swap assets
        4. Threshold-based: Optimize without cardinality, then threshold small weights
    
    Expected Performance:
        - Fast: Minutes even for large universes (>500 assets)
        - Near-optimal: Typically within 5-10% of MIQP solution
        - No special solver required
    
    Implementation Considerations:
        - Greedy algorithms may get stuck in local optima
        - Multiple random restarts can improve solution quality
        - Warm-start from preselection results often helps
    
    Args:
        returns: Historical returns DataFrame
        constraints: Portfolio constraints
        cardinality: Cardinality constraints
        asset_classes: Optional asset class mapping
    
    Returns:
        Portfolio with good approximate sparse weights
    
    Raises:
        CardinalityNotImplementedError: Always (not yet implemented)
    
    """
    raise CardinalityNotImplementedError(
        method="heuristic",
        available_methods=["preselection"],
    )


def optimize_with_cardinality_relaxation(
    returns: pd.DataFrame,
    constraints: PortfolioConstraints,
    cardinality: CardinalityConstraints,
    asset_classes: pd.Series | None = None,
) -> Portfolio:
    """Optimize portfolio with cardinality via relaxation (design stub).
    
    This is a design stub for future relaxation-based cardinality optimization.
    When implemented, this will use continuous relaxation followed by
    post-processing to enforce cardinality.
    
    Approach:
        1. Solve continuous (non-integer) relaxation with penalty on number of assets
        2. Use L1 or elastic-net regularization to encourage sparsity
        3. Post-process: threshold or round weights to satisfy exact cardinality
        4. Optional: local refinement after rounding
    
    Trade-offs:
        ✓ Fast: Similar to standard continuous optimization
        ✓ No special solver required
        ✓ Smooth optimization landscape
        ✗ Two-stage process (optimize, then round)
        ✗ Rounding may degrade solution quality
        ✗ Hard cardinality constraint approximated by penalty
    
    Implementation Considerations:
        - L1 penalty: λ * sum(|w_i|) encourages sparsity but doesn't control exact count
        - Regularization strength (λ) requires tuning
        - Rounding strategy: sort by weight magnitude, keep top-K
    
    Args:
        returns: Historical returns DataFrame
        constraints: Portfolio constraints
        cardinality: Cardinality constraints
        asset_classes: Optional asset class mapping
    
    Returns:
        Portfolio with approximate sparse weights
    
    Raises:
        CardinalityNotImplementedError: Always (not yet implemented)
    
    """
    raise CardinalityNotImplementedError(
        method="relaxation",
        available_methods=["preselection"],
    )


def get_cardinality_optimizer(method: str):
    """Get optimizer function for specified cardinality method (stub).
    
    Factory function to retrieve the appropriate optimizer implementation
    based on the cardinality method.
    
    Args:
        method: Cardinality method name ('miqp', 'heuristic', 'relaxation')
    
    Returns:
        Optimizer function for the specified method
    
    Raises:
        CardinalityNotImplementedError: If method not implemented
        ValueError: If method is unknown
    
    """
    from .constraints.models import CardinalityMethod
    
    try:
        method_enum = CardinalityMethod(method)
    except ValueError:
        valid_methods = [m.value for m in CardinalityMethod]
        msg = f"Unknown cardinality method: {method}. Valid: {valid_methods}"
        raise ValueError(msg) from None
    
    if method_enum == CardinalityMethod.PRESELECTION:
        msg = "Use preselection module directly, not cardinality optimizer"
        raise ValueError(msg)
    elif method_enum == CardinalityMethod.MIQP:
        return optimize_with_cardinality_miqp
    elif method_enum == CardinalityMethod.HEURISTIC:
        return optimize_with_cardinality_heuristic
    elif method_enum == CardinalityMethod.RELAXATION:
        return optimize_with_cardinality_relaxation
    else:
        raise CardinalityNotImplementedError(
            method=method_enum.value,
            available_methods=["preselection"],
        )
