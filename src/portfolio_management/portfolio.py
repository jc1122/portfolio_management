"""Portfolio construction.

DEPRECATED: This module has been moved to portfolio_management.portfolio.
Import from there instead. This module is maintained for backward compatibility only.
"""

from .portfolio import (  # noqa: F401
    EqualWeightStrategy,
    MeanVarianceStrategy,
    Portfolio,
    PortfolioConstraints,
    PortfolioConstructor,
    PortfolioStrategy,
    RebalanceConfig,
    RiskParityStrategy,
    StrategyType,
)

__all__ = [
    "Portfolio",
    "StrategyType",
    "PortfolioConstraints",
    "RebalanceConfig",
    "PortfolioStrategy",
    "EqualWeightStrategy",
    "MeanVarianceStrategy",
    "RiskParityStrategy",
    "PortfolioConstructor",
]
