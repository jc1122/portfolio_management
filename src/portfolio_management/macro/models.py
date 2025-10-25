"""Data models for macroeconomic series and regime configuration.

This module defines the data structures used to represent macroeconomic data
and the configurations for regime detection.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MacroSeries:
    """Represents metadata for a macroeconomic time series.

    This immutable dataclass captures key information about a macro series
    as located within a Stooq data directory. It does not contain the series
    data itself but rather points to its location and describes it.

    Attributes:
        ticker (str): The unique identifier for the macro series (e.g., "gdp.us").
        rel_path (str): The relative path to the series data file within the
                        Stooq directory.
        start_date (str): The first available date in the series (YYYY-MM-DD).
                          Note: This is often populated after loading the data.
        end_date (str): The last available date in the series (YYYY-MM-DD).
                        Note: This is often populated after loading the data.
        region (str): The geographic region of the series (e.g., "us", "de").
        category (str): The category of the series (e.g., "economic", "pmi").
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

    This dataclass defines the parameters for detecting market regimes (e.g.,
    recession, risk-off) and specifies whether this gating logic should be
    applied to an asset selection.

    Note:
        The logic that uses this configuration is currently a NoOp (No Operation)
        placeholder. The system is designed to accept this configuration, but
        the gating itself is not yet implemented.

    Attributes:
        recession_indicator (str, optional): The ticker for the series used to
            indicate a recession. Defaults to `None`.
        risk_off_threshold (float, optional): A threshold for detecting a
            risk-off environment. Defaults to `None`.
        enable_gating (bool): If `True`, enables the regime gating step in the
            selection process. Defaults to `False`.
        custom_rules (dict, optional): A dictionary for any custom or
            experimental rules. Reserved for future use. Defaults to `None`.
    """

    recession_indicator: str | None = None
    risk_off_threshold: float | None = None
    enable_gating: bool = False
    custom_rules: dict[str, Any] | None = None

    def is_enabled(self) -> bool:
        """Check if regime gating is enabled in the configuration.

        Returns:
            `True` if gating is enabled, `False` otherwise.
        """
        return self.enable_gating

    def validate(self) -> None:
        """Validate the regime configuration parameters.

        This method ensures that the configuration values are logical and
        within acceptable bounds.

        Raises:
            ValueError: If `risk_off_threshold` is negative.

        Example:
            >>> config = RegimeConfig(risk_off_threshold=-0.5)
            >>> try:
            ...     config.validate()
            ... except ValueError as e:
            ...     print(e)
            risk_off_threshold must be non-negative, got -0.5
        """
        if self.risk_off_threshold is not None and self.risk_off_threshold < 0:
            raise ValueError(
                f"risk_off_threshold must be non-negative, got {self.risk_off_threshold}",
            )
