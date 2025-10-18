"""Analytics package for financial calculations.

This package provides tools for analyzing financial data:
- Return calculation from price data
- Performance and risk metrics (future)
"""

from .returns import PriceLoader, ReturnCalculator, ReturnConfig, ReturnSummary

__all__ = [
    # Returns
    "ReturnCalculator",
    "ReturnConfig",
    "PriceLoader",
    "ReturnSummary",
]
