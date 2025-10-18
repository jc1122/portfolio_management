"""Return calculation utilities.

DEPRECATED: This module has been moved to portfolio_management.analytics.returns.
Import from there instead. This module is maintained for backward compatibility only.
"""

from .analytics.returns import (  # noqa: F401
    PriceLoader,
    ReturnCalculator,
    ReturnConfig,
    ReturnSummary,
)

__all__ = [
    "ReturnCalculator",
    "ReturnConfig",
    "PriceLoader",
    "ReturnSummary",
]
