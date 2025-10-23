"""Analytics package for financial calculations.

This package provides tools for analyzing financial data:
- Return calculation from price data
- Technical indicator-based filtering (stub implementation)
- Performance and risk metrics (future)
"""

from .indicators import (
    FilterHook,
    IndicatorConfig,
    IndicatorProvider,
    NoOpIndicatorProvider,
)
from .returns import PriceLoader, ReturnCalculator, ReturnConfig, ReturnSummary

__all__ = [
    # Returns
    "ReturnCalculator",
    "ReturnConfig",
    "PriceLoader",
    "ReturnSummary",
    # Indicators
    "IndicatorProvider",
    "NoOpIndicatorProvider",
    "IndicatorConfig",
    "FilterHook",
]
