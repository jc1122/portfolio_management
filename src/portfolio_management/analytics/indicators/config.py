"""Configuration models for technical indicator framework."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class IndicatorConfig:
    """Configuration for technical indicator-based filtering.

    This dataclass defines parameters for technical indicator computation
    and filtering. It can be extended with indicator-specific parameters
    as needed for future implementations.

    Attributes:
        enabled: Whether technical indicator filtering is enabled (default: False)
        provider: Provider type to use ('noop', 'talib', 'ta', etc.) (default: 'noop')
        params: Indicator-specific parameters (default: empty dict)
            Common parameters might include:
            - window: Rolling window size for indicators (e.g., 20, 50, 200)
            - threshold: Signal threshold for filtering (e.g., 0.5, 0.7)
            - indicator_type: Specific indicator to compute (e.g., 'rsi', 'macd', 'sma')

    Example:
        >>> config = IndicatorConfig(
        ...     enabled=True,
        ...     provider='noop',
        ...     params={'window': 20, 'threshold': 0.5}
        ... )
        >>> config.validate()  # Raises ValueError if invalid

    Extension Points:
        Future implementations can add provider-specific configurations:
        >>> @dataclass
        ... class RSIIndicatorConfig(IndicatorConfig):
        ...     rsi_period: int = 14
        ...     overbought_threshold: float = 70.0
        ...     oversold_threshold: float = 30.0

    """

    enabled: bool = False
    provider: str = "noop"
    params: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        """Validate indicator configuration parameters.

        Raises:
            ValueError: If configuration is invalid (e.g., unsupported provider)

        Example:
            >>> config = IndicatorConfig(provider='unsupported')
            >>> config.validate()  # Raises ValueError

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

        Returns:
            IndicatorConfig with enabled=False (no filtering)

        Example:
            >>> config = IndicatorConfig.disabled()
            >>> assert config.enabled is False

        """
        return cls(enabled=False, provider="noop", params={})

    @classmethod
    def noop(cls, params: dict[str, Any] | None = None) -> IndicatorConfig:
        """Create a no-op indicator configuration.

        Args:
            params: Optional parameters for the no-op provider (mostly for testing)

        Returns:
            IndicatorConfig with noop provider enabled

        Example:
            >>> config = IndicatorConfig.noop({'window': 20})
            >>> assert config.enabled is True
            >>> assert config.provider == 'noop'

        """
        return cls(enabled=True, provider="noop", params=params or {})
