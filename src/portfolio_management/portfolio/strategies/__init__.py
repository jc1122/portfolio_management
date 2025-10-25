"""A collection of portfolio construction and optimization strategies.

This package contains various strategies for determining optimal asset weights in a
portfolio. Each strategy is implemented as a class that adheres to the
`PortfolioStrategy` interface defined in the `base` module.

Available Strategies:
    - EqualWeightStrategy: Allocates an equal weight to each asset.
    - MeanVarianceStrategy: Optimizes the portfolio based on mean-variance
      optimization (MVO), targeting either minimum volatility or maximum Sharpe ratio.
    - RiskParityStrategy: Constructs a portfolio where each asset contributes equally
      to the total portfolio risk.

The `PortfolioStrategy` base class provides a common interface for constructing
portfolios, making it easy to interchange and compare different strategies.
"""

from .base import PortfolioStrategy
from .equal_weight import EqualWeightStrategy
from .mean_variance import MeanVarianceStrategy
from .risk_parity import RiskParityStrategy

__all__ = [
    "EqualWeightStrategy",
    "MeanVarianceStrategy",
    "PortfolioStrategy",
    "RiskParityStrategy",
]
