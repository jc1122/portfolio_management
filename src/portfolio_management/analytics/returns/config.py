"""Configuration for return calculation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ReturnConfig:
    """Configuration for return preparation.

    Attributes mirror the levers described in the Stage 3 implementation plan.
    Validation keeps the pipeline defensive against misconfiguration.
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
