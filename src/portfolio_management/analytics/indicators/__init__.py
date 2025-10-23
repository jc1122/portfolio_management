"""Technical indicator framework for asset filtering.

This module provides interfaces and stub implementations for technical indicator-based
asset filtering. Currently implemented as no-op stubs to prepare for future integration
with technical analysis libraries (ta-lib, ta, etc.).

Key components:
- IndicatorProvider: Interface for computing technical indicators
- NoOpIndicatorProvider: Stub implementation that returns passthrough signals
- FilterHook: Hook for filtering assets based on indicator signals
- IndicatorConfig: Configuration for technical indicator parameters

Example:
    >>> from portfolio_management.analytics.indicators import NoOpIndicatorProvider
    >>> provider = NoOpIndicatorProvider()
    >>> signal = provider.compute(price_series, {"window": 20})
    >>> # Returns passthrough signal (all True) - no actual filtering

Extension Points:
    To add real technical indicators in the future:
    1. Create new IndicatorProvider implementation (e.g., TalibIndicatorProvider)
    2. Implement compute() method with actual indicator calculations
    3. Update FilterHook to use the new provider
    4. Add indicator-specific parameters to IndicatorConfig

"""

from .config import IndicatorConfig
from .filter_hook import FilterHook
from .providers import IndicatorProvider, NoOpIndicatorProvider

__all__ = [
    "IndicatorConfig",
    "IndicatorProvider",
    "NoOpIndicatorProvider",
    "FilterHook",
]
