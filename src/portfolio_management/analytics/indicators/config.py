"""Configuration models for the technical indicator framework.

This module defines the `IndicatorConfig` dataclass, which is used to
configure how technical indicators are calculated and applied for filtering
in the portfolio construction process.

Key Classes:
    - IndicatorConfig: Holds settings for indicator-based filtering.

Usage Example:
    >>> from portfolio_management.analytics.indicators.config import IndicatorConfig
    >>>
    >>> # Configuration to enable a simple 20-day moving average filter
    >>> sma_config = IndicatorConfig(
    ...     enabled=True,
    ...     provider="talib", # Hypothetical provider
    ...     params={"indicator_type": "sma", "window": 20}
    ... )
    >>>
    >>> try:
    ...     sma_config.validate()
    ...     print("SMA config is valid.")
    ... except ValueError as e:
    ...     print(f"Config error: {e}")
    SMA config is valid.
    >>>
    >>> # A disabled configuration
    >>> disabled_config = IndicatorConfig.disabled()
    >>> print(f"Disabled config enabled: {disabled_config.enabled}")
    Disabled config enabled: False
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class IndicatorConfig:
    """Configuration for technical indicator-based filtering.

    This dataclass defines the parameters for technical indicator computation
    and filtering. It specifies whether the feature is enabled, which provider
    to use for calculations (e.g., 'talib'), and any indicator-specific
    parameters like window sizes or thresholds.

    Attributes:
        enabled (bool): If True, technical indicator filtering is active.
            Defaults to False.
        provider (str): The provider to use for indicator calculations.
            Examples: 'noop', 'talib', 'ta'. Defaults to 'noop'.
        params (dict[str, Any]): A dictionary of indicator-specific parameters.
            Common keys include 'window', 'threshold', 'indicator_type'.

    Example:
        >>> # Config for a 50-day RSI filter with a threshold of 0.5
        >>> rsi_config = IndicatorConfig(
        ...     enabled=True,
        ...     provider='talib', # Assuming 'talib' is a supported provider
        ...     params={'indicator_type': 'rsi', 'window': 50, 'threshold': 0.5}
        ... )
        >>> rsi_config.validate()
        >>>
        >>> print(f"Provider: {rsi_config.provider}, Window: {rsi_config.params['window']}")
        Provider: talib, Window: 50
    """

    enabled: bool = False
    provider: str = "noop"
    params: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        """Validate indicator configuration parameters.

        Checks if the provider is supported and validates common parameters
        like 'window' and 'threshold' if they are present.

        Raises:
            ValueError: If the configuration is invalid, such as having an
                unsupported provider or invalid parameter values.
        """
        if self.enabled and self.provider not in ("noop", "talib", "ta"):
            raise ValueError(
                f"Unsupported indicator provider: {self.provider}. "
                f"Supported providers: 'noop', 'talib', 'ta'",
            )

        # Validate common parameters if present
        if "window" in self.params and self.params["window"] <= 0:
            raise ValueError(
                f"Invalid window parameter: {self.params['window']} (must be positive)",
            )

        if "threshold" in self.params:
            threshold = self.params["threshold"]
            if not 0 <= threshold <= 1:
                raise ValueError(
                    f"Invalid threshold parameter: {threshold} (must be in [0, 1])",
                )

    @classmethod
    def disabled(cls) -> IndicatorConfig:
        """Create a disabled indicator configuration.

        This is a convenience factory method for creating a configuration
        that explicitly disables indicator filtering.

        Returns:
            IndicatorConfig: An instance with `enabled` set to False.
        """
        return cls(enabled=False, provider="noop", params={})

    @classmethod
    def noop(cls, params: dict[str, Any] | None = None) -> IndicatorConfig:
        """Create a no-op indicator configuration.

        This factory creates a configuration that is enabled but uses the 'noop'
        provider, which performs no actual filtering. Useful for testing the
        pipeline's structure without applying indicator logic.

        Args:
            params (dict[str, Any] | None): Optional parameters for the no-op
                provider, primarily for testing purposes.

        Returns:
            IndicatorConfig: An instance with `provider` set to 'noop' and `enabled`
                set to True.
        """
        return cls(enabled=True, provider="noop", params=params or {})