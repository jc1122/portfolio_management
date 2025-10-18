"""Return calculation for portfolio construction.

This package provides end-to-end return calculation from price data:
- Configuration and models for flexible return preparation
- Price data loaders with validation
- Return calculator with missing data handling and alignment
- Summary statistics for prepared returns
"""

from .calculator import ReturnCalculator
from .config import ReturnConfig
from .loaders import PriceLoader
from .models import ReturnSummary

__all__ = [
    "PriceLoader",
    "ReturnCalculator",
    "ReturnConfig",
    "ReturnSummary",
]
