# ruff: noqa
"""Custom exception hierarchy for portfolio management workflows."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class PortfolioManagementError(Exception):
    """Base exception for portfolio management errors."""


class DataValidationError(PortfolioManagementError):
    """Raised when input data fails validation checks."""


class ConfigurationError(PortfolioManagementError):
    """Raised when configuration files or parameters are invalid."""


class DataQualityError(PortfolioManagementError):
    """Raised when data quality is insufficient for processing."""


class DependencyNotInstalledError(PortfolioManagementError):
    """Raised when an optional runtime dependency is missing."""

    def __init__(self, package: str, *, context: str) -> None:
        self.package = package
        self.context = context
        super().__init__(
            f"{package} is required {context}. Please install {package} before continuing."
        )


class AssetSelectionError(PortfolioManagementError):
    """Raised when asset selection fails."""


class ClassificationError(PortfolioManagementError):
    """Raised when classification fails."""


class ReturnCalculationError(PortfolioManagementError):
    """Raised when return calculation fails."""


class UniverseLoadError(PortfolioManagementError):
    """Raised when universe loading fails."""


class DataDirectoryNotFoundError(DataValidationError):
    """Raised when the expected Stooq data directory is missing."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        super().__init__(
            f"Data directory not found: {data_dir}. "
            "Run prepare_tradeable_data.py to generate the required data directory."
        )


class InsufficientDataError(DataQualityError):
    """Raised when the available data does not meet minimum requirements."""

    def __init__(self, message: str, *, asset_count: int = 0, required_count: int = 0):
        super().__init__(message)
        self.asset_count = asset_count
        self.required_count = required_count
