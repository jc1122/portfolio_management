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

    def __init__(
        self,
        *,
        constraint_name: str,
        violated_value: float | None,
        message: str | None = None,
    ) -> None:
        """Initialize the exception.

        Args:
            constraint_name: The name of the violated constraint.
            violated_value: The value that violated the constraint.
            message: Optional custom error message.

        """
        self.constraint_name: str = constraint_name
        self.violated_value: float | None = violated_value
        final_message = message or (
            f"Constraint '{constraint_name}' was violated with value: {violated_value}."
        )
        super().__init__(final_message)


class OptimizationError(PortfolioConstructionError):
    """Raised when the portfolio optimization process fails."""

    def __init__(
        self,
        *,
        strategy_name: str,
        message: str | None = None,
    ) -> None:
        """Initialize the exception.

        Args:
            strategy_name: The name of the strategy that failed optimization.
            message: Optional custom error message.

        """
        self.strategy_name: str = strategy_name
        final_message = message or (
            f"Optimization failed for strategy: '{strategy_name}'."
        )
        super().__init__(final_message)


class InsufficientDataError(PortfolioConstructionError):
    """Raised when historical data is insufficient for portfolio construction."""

    def __init__(
        self,
        *,
        required_periods: int | None = None,
        available_periods: int | None = None,
        message: str | None = None,
        **context: object,
    ) -> None:
        """Initialize the exception.

        Args:
            required_periods: The number of required data periods.
            available_periods: The number of available data periods.
            message: Optional custom error message.
            **context: Additional context, such as asset counts.

        """
        self.required_periods: int | None = required_periods
        self.available_periods: int | None = available_periods
        self.context: dict[str, object] = context
        if message is None:
            if required_periods is not None and available_periods is not None:
                message = (
                    "Insufficient data for portfolio construction. "
                    f"Required: {required_periods}, Available: {available_periods}."
                )
            else:
                message = "Insufficient data for portfolio construction."
        super().__init__(message)


class DependencyError(PortfolioConstructionError):
    """Raised when an optional dependency for a strategy is not installed."""

    def __init__(
        self,
        *,
        dependency_name: str,
        message: str | None = None,
    ) -> None:
        """Initialize the exception.

        Args:
            dependency_name: The name of the missing dependency.
            message: Optional custom error message.

        """
        self.dependency_name: str = dependency_name
        final_message = message or (
            f"Optional dependency '{dependency_name}' is not installed. "
            "Please install it to use this feature."
        )
        super().__init__(final_message)
