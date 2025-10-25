"""Indicator provider interfaces and implementations.

This module defines the core `IndicatorProvider` abstract base class, which
establishes a contract for all technical indicator providers. It uses a
provider pattern to decouple the indicator filtering logic from the specific
libraries (e.g., TA-Lib, `ta`) used for computation.

This module also includes a `NoOpIndicatorProvider`, a default implementation
that performs no actual filtering and serves as a placeholder or for testing.

Key Classes:
    - IndicatorProvider: An abstract base class for indicator computation.
    - NoOpIndicatorProvider: A default provider that includes all assets.

Usage Example:
    >>> from portfolio_management.analytics.indicators.providers import (
    ...     IndicatorProvider, NoOpIndicatorProvider
    ... )
    >>>
    >>> def get_provider(name: str) -> IndicatorProvider:
    ...     if name == "noop":
    ...         return NoOpIndicatorProvider()
    ...     # In a real scenario, you might have:
    ...     # elif name == "talib":
    ...     #     return TALibIndicatorProvider()
    ...     else:
    ...         raise ValueError(f"Unknown provider: {name}")
    >>>
    >>> provider = get_provider("noop")
    >>> print(isinstance(provider, IndicatorProvider))
    True
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import pandas as pd


class IndicatorProvider(ABC):
    """Abstract interface for technical indicator computation.

    This abstract class defines the contract for computing technical indicators
    from a time series. Concrete implementations should inherit from this class
    and implement the `compute` method, typically by wrapping a technical
    analysis library like TA-Lib or `ta`.

    The provider pattern allows the system to remain agnostic to the specific
    backend used for indicator calculations.

    Example (for creating a new provider):
        >>> class MovingAverageCrossProvider(IndicatorProvider):
        ...     def compute(self, series: pd.Series, params: dict[str, Any]) -> pd.Series:
        ...         short_window = params.get("short", 20)
        ...         long_window = params.get("long", 50)
        ...         short_ma = series.rolling(window=short_window).mean()
        ...         long_ma = series.rolling(window=long_window).mean()
        ...         # Signal is True when short MA crosses above long MA
        ...         signal = (short_ma > long_ma)
        ...         return signal.fillna(False)
    """

    @abstractmethod
    def compute(self, series: pd.Series, params: dict[str, Any]) -> pd.Series:
        """Compute a technical indicator signal from a time series.

        Args:
            series (pd.Series): An input time series of data, typically prices,
                indexed by date.
            params (dict[str, Any]): A dictionary of indicator-specific parameters,
                such as window sizes or thresholds (e.g., `{"window": 20}`).

        Returns:
            pd.Series: A Series of indicator signals with the same index as the
            input. Values should be boolean (True/False) or float (0.0 to 1.0)
            to signify inclusion or exclusion.
        """


class NoOpIndicatorProvider(IndicatorProvider):
    """No-op stub implementation that returns pass-through signals.

    This implementation of `IndicatorProvider` always returns a signal of `True`,
    effectively including all assets without applying any filtering. It serves as a
    default placeholder, useful for testing the indicator framework's structure
    without requiring technical analysis dependencies or logic.

    Use this provider for:
    - Testing the overall asset selection pipeline.
    - Disabling indicator filtering while keeping the configuration enabled.
    - Serving as a base for future indicator implementations.

    Example:
        >>> import pandas as pd
        >>> provider = NoOpIndicatorProvider()
        >>> prices = pd.Series(
        ...     [100, 101, 102],
        ...     index=pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03'])
        ... )
        >>> signal = provider.compute(prices, params={})
        >>> print(signal)
        2023-01-01    True
        2023-01-02    True
        2023-01-03    True
        dtype: bool
    """

    def compute(self, series: pd.Series, params: dict[str, Any]) -> pd.Series:
        """Return a pass-through signal (all True).

        This method ignores the input series and parameters and simply returns
        a boolean Series of `True` values with the same index.

        Args:
            series (pd.Series): The input time series (ignored).
            params (dict[str, Any]): Indicator-specific parameters (ignored).

        Returns:
            pd.Series: A boolean Series of `True` values, which results in no
            assets being filtered out.
        """
        # Return all True values - no filtering
        return pd.Series(True, index=series.index, dtype=bool)