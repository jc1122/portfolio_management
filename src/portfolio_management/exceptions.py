"""Custom exception hierarchy for portfolio management workflows."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from datetime import date
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


class BacktestError(PortfolioManagementError):
    """Base exception for backtesting errors."""


class InvalidBacktestConfigError(BacktestError):
    """Raised when a backtest configuration value is invalid."""

    def __init__(
        self,
        *,
        config_field: str,
        invalid_value: Any,
        reason: str,
    ) -> None:
        """Initialize the exception.

        Args:
            config_field: The name of the invalid configuration field.
            invalid_value: The value that failed validation.
            reason: The reason the value is considered invalid.

        """
        self.config_field: str = config_field
        self.invalid_value: Any = invalid_value
        self.reason: str = reason
        message = (
            f"Invalid value for backtest config field '{config_field}': "
            f"{invalid_value!r}. Reason: {reason}."
        )
        super().__init__(message)


class InsufficientHistoryError(BacktestError):
    """Raised when historical data does not cover the requested backtest period."""

    def __init__(
        self,
        *,
        required_start: date,
        available_start: date,
        asset_ticker: str,
    ) -> None:
        """Initialize the exception.

        Args:
            required_start: The earliest date required for the backtest.
            available_start: The earliest date available in the dataset.
            asset_ticker: The ticker symbol with insufficient history.

        """
        self.required_start: date = required_start
        self.available_start: date = available_start
        self.asset_ticker: str = asset_ticker
        message = (
            f"Insufficient history for asset '{asset_ticker}'. "
            f"Required start: {required_start.isoformat()}, "
            f"available start: {available_start.isoformat()}."
        )
        super().__init__(message)


class RebalanceError(BacktestError):
    """Raised when a rebalancing operation fails."""

    def __init__(
        self,
        *,
        rebalance_date: date,
        error_type: str,
        context: dict[str, Any] | None = None,
        message: str | None = None,
    ) -> None:
        """Initialize the exception.

        Args:
            rebalance_date: The date of the failed rebalancing event.
            error_type: Classification of the rebalancing failure.
            context: Additional diagnostic context for debugging.
            message: Optional custom error message.

        """
        self.rebalance_date: date = rebalance_date
        self.error_type: str = error_type
        self.context: dict[str, Any] = dict(context or {})
        final_message = message or (
            f"Rebalance error on {rebalance_date.isoformat()} "
            f"({error_type}). Context: {self.context}"
        )
        super().__init__(final_message)


class TransactionCostError(BacktestError):
    """Raised when transaction cost calculations fail."""

    def __init__(
        self,
        *,
        transaction_type: str,
        amount: float,
        reason: str,
        message: str | None = None,
    ) -> None:
        """Initialize the exception.

        Args:
            transaction_type: The type of transaction being processed.
            amount: The monetary amount associated with the transaction.
            reason: Explanation of why the cost calculation failed.
            message: Optional custom error message.

        """
        self.transaction_type: str = transaction_type
        self.amount: float = amount
        self.reason: str = reason
        final_message = message or (
            f"Transaction cost error for '{transaction_type}' transaction "
            f"with amount {amount}: {reason}."
        )
        super().__init__(final_message)
