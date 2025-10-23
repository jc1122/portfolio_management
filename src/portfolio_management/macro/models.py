"""Data models for macroeconomic series and regime configuration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MacroSeries:
    """Represents a macroeconomic time series with metadata.

    This dataclass captures information about a macro series loaded from
    Stooq data directories, including its identifier, path, and available
    date range.

    Attributes:
        ticker: Macro series identifier (e.g., "gdp.us", "pmi.us").
        rel_path: Relative path to the series file in Stooq directory.
        start_date: First available date in the series (ISO format YYYY-MM-DD).
        end_date: Last available date in the series (ISO format YYYY-MM-DD).
        region: Geographic region for the series (e.g., "us", "uk").
        category: Series category (e.g., "economic_indicators", "yields").

    Example:
        >>> series = MacroSeries(
        ...     ticker="gdp.us",
        ...     rel_path="data/daily/us/economic/gdp.txt",
        ...     start_date="2000-01-01",
        ...     end_date="2025-10-23",
        ...     region="us",
        ...     category="economic_indicators"
        ... )

    """

    ticker: str
    rel_path: str
    start_date: str
    end_date: str
    region: str = ""
    category: str = ""


@dataclass
class RegimeConfig:
    """Configuration for regime detection and gating rules.

    This dataclass defines the rules for detecting market regimes (e.g.,
    recession, risk-off) and how they should affect asset selection.

    Currently implemented as NoOp stubs that always return neutral signals.
    Future implementations can add actual regime detection logic.

    Attributes:
        recession_indicator: Optional ticker for recession indicator series.
            If None, recession detection is disabled (always neutral).
        risk_off_threshold: Optional threshold for risk-off regime detection.
            If None, risk-off detection is disabled (always neutral).
        enable_gating: Whether to apply regime gating to selection (default: False).
            When False, selection passes through unchanged (documented NoOp behavior).
        custom_rules: Optional dict for extensible regime rules.
            Reserved for future custom regime detection logic.

    Example:
        >>> # NoOp configuration (default)
        >>> config = RegimeConfig()
        >>> config.is_enabled()
        False
        >>> # Configuration with indicators (but still NoOp until implemented)
        >>> config = RegimeConfig(
        ...     recession_indicator="recession_indicator.us",
        ...     risk_off_threshold=0.5,
        ...     enable_gating=False  # Explicitly disabled
        ... )

    """

    recession_indicator: str | None = None
    risk_off_threshold: float | None = None
    enable_gating: bool = False
    custom_rules: dict[str, Any] | None = None

    def is_enabled(self) -> bool:
        """Check if regime gating is enabled.

        Returns:
            True if gating should be applied, False otherwise (NoOp).

        Example:
            >>> config = RegimeConfig(enable_gating=False)
            >>> config.is_enabled()
            False

        """
        return self.enable_gating

    def validate(self) -> None:
        """Validate regime configuration parameters.

        Raises:
            ValueError: If parameters are invalid (e.g., negative thresholds).

        Example:
            >>> config = RegimeConfig(risk_off_threshold=-0.5)
            >>> config.validate()  # Raises ValueError

        """
        if self.risk_off_threshold is not None and self.risk_off_threshold < 0:
            raise ValueError(
                f"risk_off_threshold must be non-negative, got {self.risk_off_threshold}",
            )
