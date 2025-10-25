"""Configuration for return calculation.

This module defines the `ReturnConfig` dataclass, which holds all the
parameters for configuring the behavior of the `ReturnCalculator`. By using
this structured configuration, users can control aspects like the return
calculation method, frequency, and how missing data is handled.

Key Classes:
    - ReturnConfig: A dataclass for specifying return calculation settings.

Usage Example:
    >>> from portfolio_management.analytics.returns.config import ReturnConfig
    >>>
    >>> # Standard configuration for monthly log returns
    >>> monthly_log_config = ReturnConfig(
    ...     method="log",
    ...     frequency="monthly",
    ...     min_periods=12,
    ...     handle_missing="interpolate",
    ...     min_coverage=0.9
    ... )
    >>>
    >>> try:
    ...     monthly_log_config.validate()
    ...     print("Configuration is valid.")
    ... except ValueError as e:
    ...     print(f"Configuration error: {e}")
    Configuration is valid.
    >>>
    >>> # Example of an invalid configuration
    >>> invalid_config = ReturnConfig(method="geometric")
    >>> try:
    ...     invalid_config.validate()
    ... except ValueError as e:
    ...     print(f"Configuration error: {e}")
    Configuration error: Invalid return method: geometric

"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ReturnConfig:
    """Configuration for return preparation.

    This dataclass holds all settings related to the calculation and cleaning
    of asset returns. It provides a centralized place to define the behavior
    of the `ReturnCalculator`.

    Attributes:
        method (str): The method for calculating returns.
            Options: 'simple', 'log', 'excess'. Defaults to 'simple'.
        frequency (str): The target frequency for the returns.
            Options: 'daily', 'weekly', 'monthly'. Defaults to 'daily'.
        risk_free_rate (float): The annualized risk-free rate to use when
            `method` is 'excess'. Defaults to 0.0.
        handle_missing (str): The strategy for handling missing price data.
            Options: 'forward_fill', 'drop', 'interpolate'. Defaults to 'forward_fill'.
        max_forward_fill_days (int): The maximum number of consecutive days to
            forward-fill missing data. Defaults to 5.
        min_periods (int): The minimum number of price observations required
            for an asset to be included. Defaults to 2.
        align_method (str): The method for aligning dates across assets.
            Options: 'outer' (union of dates), 'inner' (intersection of dates).
            Defaults to 'outer'.
        reindex_to_business_days (bool): Whether to reindex the final returns
            to a standard business day calendar. Defaults to False.
        min_coverage (float): The minimum proportion of non-NaN returns an
            asset must have to be kept after processing. Defaults to 0.8.

    Example:
        >>> # Create a config for weekly log returns, requiring at least 1 year of data
        >>> config = ReturnConfig(
        ...     method="log",
        ...     frequency="weekly",
        ...     min_periods=52,
        ...     handle_missing="interpolate",
        ...     max_forward_fill_days=3,
        ...     min_coverage=0.95
        ... )
        >>> config.validate() # Raises ValueError on invalid settings
    """

    method: str = "simple"  # one of: simple, log, excess
    frequency: str = "daily"  # one of: daily, weekly, monthly
    risk_free_rate: float = 0.0  # annual rate used for excess returns
    handle_missing: str = "forward_fill"  # forward_fill, drop, interpolate
    max_forward_fill_days: int = 5
    min_periods: int = 2  # minimum price observations required per asset
    align_method: str = "outer"  # outer keeps full union, inner = intersection
    reindex_to_business_days: bool = False
    min_coverage: float = 0.8  # minimum proportion of non-NaN returns per asset

    def validate(self) -> None:
        """Validate the configuration values and raise ``ValueError`` on issues."""
        if self.method not in {"simple", "log", "excess"}:
            raise ValueError(f"Invalid return method: {self.method}")
        if self.frequency not in {"daily", "weekly", "monthly"}:
            raise ValueError(f"Invalid return frequency: {self.frequency}")
        if self.handle_missing not in {"forward_fill", "drop", "interpolate"}:
            raise ValueError(
                f"Invalid missing data handling method: {self.handle_missing}",
            )
        if self.align_method not in {"outer", "inner"}:
            raise ValueError(f"Invalid align_method: {self.align_method}")
        if self.max_forward_fill_days < 0:
            raise ValueError("max_forward_fill_days must be >= 0")
        if self.min_periods <= 1:
            raise ValueError("min_periods must be greater than 1")
        if not 0 < self.min_coverage <= 1:
            raise ValueError("min_coverage must be within (0, 1]")

    @classmethod
    def default(cls) -> ReturnConfig:
        """Factory for the default (daily, simple) configuration."""
        return cls()

    @classmethod
    def monthly_simple(cls) -> ReturnConfig:
        """Factory that annualises to monthly simple returns."""
        return cls(method="simple", frequency="monthly")

    @classmethod
    def weekly_log(cls) -> ReturnConfig:
        """Factory that prepares weekly log returns."""
        return cls(method="log", frequency="weekly")