"""Indicator provider interfaces and implementations.

This module defines the core IndicatorProvider interface and provides
a no-op stub implementation for testing and preparation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import pandas as pd


class IndicatorProvider(ABC):
    """Abstract interface for technical indicator computation.

    This interface defines the contract for computing technical indicators
    from price/volume data. Implementations can use different libraries
    (ta-lib, ta, etc.) to compute actual indicators.

    Future implementations should inherit from this class and implement
    the compute() method with actual indicator calculations.

    Example:
        >>> class RSIIndicatorProvider(IndicatorProvider):
        ...     def compute(self, series: pd.Series, params: dict[str, Any]) -> pd.Series:
        ...         # Compute RSI using ta-lib or similar
        ...         window = params.get("window", 14)
        ...         # ... RSI calculation ...
        ...         return rsi_series
    """

    @abstractmethod
    def compute(self, series: pd.Series, params: dict[str, Any]) -> pd.Series:
        """Compute technical indicator from price/volume series.

        Args:
            series: Price or volume time series (indexed by date)
            params: Indicator-specific parameters (e.g., {"window": 20, "threshold": 0.5})

        Returns:
            Indicator signal series with same index as input.
            Values should typically be in [0, 1] range for filtering purposes,
            or boolean True/False for direct inclusion/exclusion signals.

        Example:
            >>> provider = SomeIndicatorProvider()
            >>> prices = pd.Series([100, 101, 102, 103], index=pd.date_range('2020-01-01', periods=4))
            >>> signal = provider.compute(prices, {"window": 2})
        """
        pass


class NoOpIndicatorProvider(IndicatorProvider):
    """No-op stub implementation that returns passthrough signals.

    This implementation always returns a series of True values (or 1.0),
    effectively including all assets without any filtering. It serves as
    a placeholder for testing the indicator framework without requiring
    heavy technical analysis dependencies.

    Use this provider when:
    - Testing the indicator configuration system
    - Validating the filter hook infrastructure
    - Running backtests without indicator-based filtering
    - Preparing for future indicator integration

    Example:
        >>> provider = NoOpIndicatorProvider()
        >>> prices = pd.Series([100, 101, 102], index=pd.date_range('2020-01-01', periods=3))
        >>> signal = provider.compute(prices, {"window": 20})
        >>> print(signal)
        2020-01-01    True
        2020-01-02    True
        2020-01-03    True
        dtype: bool
    """

    def compute(self, series: pd.Series, params: dict[str, Any]) -> pd.Series:
        """Return passthrough signal (all True).

        Args:
            series: Price or volume time series (ignored in no-op implementation)
            params: Indicator parameters (ignored in no-op implementation)

        Returns:
            Boolean series with all True values, same index as input.
            This effectively includes all assets without filtering.
        """
        # Return all True values - no filtering
        return pd.Series(True, index=series.index, dtype=bool)
