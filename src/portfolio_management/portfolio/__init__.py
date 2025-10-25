"""A comprehensive suite for systematic portfolio construction and management.

This package provides a modular framework for building, optimizing, and analyzing
investment portfolios. It includes a variety of weighting strategies, constraint
management, and rebalancing logic, designed for both research and production
environments.

Key Components:
    - PortfolioConstructor: The main entry point for building portfolios. It acts as
      a factory for different portfolio strategies.
    - PortfolioStrategy: An interface for all portfolio construction strategies,
      with concrete implementations like `EqualWeightStrategy`,
      `MeanVarianceStrategy`, and `RiskParityStrategy`.
    - PortfolioConstraints: A data class to define investment constraints such as
      min/max weights, asset class exposure limits, and more.
    - CardinalityConstraints: A data class for advanced constraints on the number
      of assets in a portfolio.
    - RebalanceConfig: Configuration for defining rebalancing frequency and tolerance.

Usage Example:
    >>> import pandas as pd
    >>> from portfolio_management.portfolio import PortfolioConstructor, PortfolioConstraints
    >>>
    >>> import numpy as np
    >>> # 1. Define returns data
    >>> np.random.seed(42)
    >>> returns = pd.DataFrame({
    ...     "asset1": np.random.normal(0, 0.01, 30),
    ...     "asset2": np.random.normal(0, 0.02, 30),
    ...     "asset3": np.random.normal(0, 0.03, 30),
    ... })
    >>>
    >>> # 2. Define constraints
    >>> constraints = PortfolioConstraints(max_weight=0.5, require_full_investment=True)
    >>>
    >>> # 3. Initialize the constructor and build a portfolio
    >>> from portfolio_management.portfolio.strategies.mean_variance import MeanVarianceStrategy
    >>> constructor = PortfolioConstructor(constraints=constraints)
    >>> # The default min_periods for MeanVarianceStrategy is 252. We override it for the example.
    >>> constructor.register_strategy(
    ...     "mean_variance_min_vol",
    ...     MeanVarianceStrategy(objective="min_volatility", min_periods=30)
    ... )
    >>> portfolio = constructor.construct(
    ...     strategy_name="mean_variance_min_vol",
    ...     returns=returns
    ... )
    >>>
    >>> # 4. View the resulting weights (exact values depend on random data)
    >>> print(portfolio.weights.sum().round(2))
    1.0
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
from .constraints import CardinalityConstraints, CardinalityMethod, PortfolioConstraints
from .membership import MembershipPolicy, apply_membership_policy
from .models import Portfolio, StrategyType
from .preselection import (
    Preselection,
    PreselectionConfig,
    PreselectionMethod,
    create_preselection_from_dict,
)
from .rebalancing import RebalanceConfig
from .statistics import StatisticsCache
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
    "StatisticsCache",
    # Strategies
    "PortfolioStrategy",
    "EqualWeightStrategy",
    "MeanVarianceStrategy",
    "RiskParityStrategy",
    # Builder
    "PortfolioConstructor",
]
