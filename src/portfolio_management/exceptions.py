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
        """Initialize the exception.

        Args:
            package: The name of the missing package.
            context: The context in which the package is required.

        """
        self.package = package
        self.context = context
        super().__init__(
            f"{package} is required {context}. Please install {package} before continuing.",
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
        """Initialize the exception.

        Args:
            data_dir: The path to the missing data directory.

        """
        self.data_dir = data_dir
        super().__init__(
            f"Data directory not found: {data_dir}. "
            "Run prepare_tradeable_data.py to generate the required data directory.",
        )


class InsufficientAssetsError(DataQualityError):
    """Raised when the number of available assets does not meet minimum requirements."""

    def __init__(self, message: str, *, asset_count: int = 0, required_count: int = 0):
        """Initialize the exception.

        Args:
            message: The error message.
            asset_count: The number of available assets.
            required_count: The number of required assets.

        """
        super().__init__(message)
        self.asset_count = asset_count
        self.required_count = required_count


class PortfolioConstructionError(PortfolioManagementError):
    """Base exception for portfolio construction errors."""


class InvalidStrategyError(PortfolioConstructionError):
    """Raised when an invalid portfolio construction strategy is specified."""


class ConstraintViolationError(PortfolioConstructionError):
    """Raised when a portfolio constraint is violated."""

    def __init__(self, *, constraint_name: str, violated_value: float | None) -> None:
        """Initialize the exception.

        Args:
            constraint_name: The name of the violated constraint.
            violated_value: The value that violated the constraint.

        """
        self.constraint_name = constraint_name
        self.violated_value = violated_value
        super().__init__(
            f"Constraint '{constraint_name}' was violated with value: {violated_value}.",
        )


class OptimizationError(PortfolioConstructionError):
    """Raised when the portfolio optimization process fails."""

    def __init__(self, *, strategy_name: str) -> None:
        """Initialize the exception.

        Args:
            strategy_name: The name of the strategy that failed optimization.

        """
        self.strategy_name = strategy_name
        super().__init__(f"Optimization failed for strategy: '{strategy_name}'.")


class InsufficientDataError(PortfolioConstructionError):
    """Raised when historical data is insufficient for portfolio construction."""

    def __init__(self, *, required_periods: int, available_periods: int) -> None:
        """Initialize the exception.

        Args:
            required_periods: The number of required data periods.
            available_periods: The number of available data periods.

        """
        self.required_periods = required_periods
        self.available_periods = available_periods
        super().__init__(
            f"Insufficient data for portfolio construction. "
            f"Required: {required_periods}, Available: {available_periods}.",
        )


class DependencyError(PortfolioConstructionError):
    """Raised when an optional dependency for a strategy is not installed."""

    def __init__(self, *, dependency_name: str) -> None:
        """Initialize the exception.

        Args:
            dependency_name: The name of the missing dependency.

        """
        self.dependency_name = dependency_name
        super().__init__(
            f"Optional dependency '{dependency_name}' is not installed. "
            f"Please install it to use this feature.",
        )
