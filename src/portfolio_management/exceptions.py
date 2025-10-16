# ruff: noqa
"""Custom exception hierarchy for portfolio management workflows."""

from __future__ import annotations


class PortfolioManagementError(Exception):
    """Base exception for portfolio management errors."""


class DataValidationError(PortfolioManagementError):
    """Raised when input data fails validation checks."""


class ConfigurationError(PortfolioManagementError):
    """Raised when configuration files or parameters are invalid."""


class DataQualityError(PortfolioManagementError):
    """Raised when data quality is insufficient for processing."""


class AssetSelectionError(PortfolioManagementError):
    """Raised when asset selection fails."""


class ClassificationError(PortfolioManagementError):
    """Raised when classification fails."""


class ReturnCalculationError(PortfolioManagementError):
    """Raised when return calculation fails."""


class UniverseLoadError(PortfolioManagementError):
    """Raised when universe loading fails."""


class InsufficientDataError(DataQualityError):
    """Raised when the available data does not meet minimum requirements."""

    def __init__(self, message: str, *, asset_count: int = 0, required_count: int = 0):
        super().__init__(message)
        self.asset_count = asset_count
        self.required_count = required_count
