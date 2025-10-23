"""Portfolio construction package.

This package provides portfolio construction strategies and utilities.
"""

from .builder import PortfolioConstructor
from .cardinality import (
    CardinalityNotImplementedError,
    get_cardinality_optimizer,
    optimize_with_cardinality_heuristic,
    optimize_with_cardinality_miqp,
    optimize_with_cardinality_relaxation,
    validate_cardinality_constraints,
)
from .constraints import (
    CardinalityConstraints,
    CardinalityMethod,
    PortfolioConstraints,
)
from .membership import MembershipPolicy, apply_membership_policy
from .models import Portfolio, StrategyType
from .preselection import (
    Preselection,
    PreselectionConfig,
    PreselectionMethod,
    create_preselection_from_dict,
)
from .rebalancing import RebalanceConfig
from .statistics import RollingStatistics
from .strategies import (
    EqualWeightStrategy,
    MeanVarianceStrategy,
    PortfolioStrategy,
    RiskParityStrategy,
)

__all__ = [
    # Models
    "Portfolio",
    "StrategyType",
    # Constraints
    "CardinalityConstraints",
    "CardinalityMethod",
    "PortfolioConstraints",
    # Cardinality (design stubs)
    "CardinalityNotImplementedError",
    "get_cardinality_optimizer",
    "optimize_with_cardinality_heuristic",
    "optimize_with_cardinality_miqp",
    "optimize_with_cardinality_relaxation",
    "validate_cardinality_constraints",
    # Membership
    "MembershipPolicy",
    "apply_membership_policy",
    # Preselection
    "Preselection",
    "PreselectionConfig",
    "PreselectionMethod",
    "create_preselection_from_dict",
    # Rebalancing
    "RebalanceConfig",
    # Statistics
    "RollingStatistics",
    # Strategies
    "PortfolioStrategy",
    "EqualWeightStrategy",
    "MeanVarianceStrategy",
    "RiskParityStrategy",
    # Builder
    "PortfolioConstructor",
]
