"""Custom exception hierarchy for the portfolio management toolkit.

This module defines a structured hierarchy of custom exceptions, all inheriting
from the base `PortfolioManagementError`. This allows for precise and
predictable error handling throughout the application. By catching specific
exceptions, different parts of the system can react appropriately to failures
in data validation, configuration, portfolio construction, or backtesting.

The hierarchy is designed to be granular, enabling developers to write robust
error-handling logic. For example, a caller can distinguish between a fatal
`DataDirectoryNotFoundError` and a recoverable `InsufficientAssetsError`.

Classes:
    - PortfolioManagementError: Base exception for all errors in the toolkit.
    - DataValidationError: Base for data-related validation errors.
    - ConfigurationError: For errors in configuration files or parameters.
    - DataQualityError: For issues with the quality of input data.
    - PortfolioConstructionError: Base for errors during portfolio creation.
    - BacktestError: Base for errors during backtesting execution.

Example:
    Catching a specific exception and accessing its attributes.

    >>> from portfolio_management.core.exceptions import (
    ...     DependencyNotInstalledError,
    ...     PortfolioManagementError
    ... )
    >>>
    >>> def check_for_optional_package():
    ...     try:
    ...         import non_existent_package
    ...     except ImportError:
    ...         raise DependencyNotInstalledError(
    ...             "non_existent_package",
    ...             context="for advanced analytics"
    ...         )
    >>>
    >>> try:
    ...     check_for_optional_package()
    ... except DependencyNotInstalledError as e:
    ...     print(f"Caught expected error: {e}")
    ...     print(f"Missing package: {e.package}, Context: {e.context}")
    ... except PortfolioManagementError:
    ...     print("Caught a generic portfolio management error.")
    Caught expected error: non_existent_package is required for advanced analytics. Please install non_existent_package before continuing.
    Missing package: non_existent_package, Context: for advanced analytics
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from datetime import date
    from pathlib import Path


class PortfolioManagementError(Exception):
    """Base exception for all errors in the portfolio management toolkit.

    All custom exceptions raised by the application should inherit from this class.
    This allows a user to catch all toolkit-specific errors with a single
    `except PortfolioManagementError:` block.
    """


# --- Data and Configuration Errors ---

class DataValidationError(PortfolioManagementError):
    """Raised when input data fails validation checks.

    This is a general exception for when data does not conform to expected
    formats, schemas, or semantic rules.
    """


class ConfigurationError(PortfolioManagementError):
    """Raised when configuration files or parameters are invalid.

    This can occur if a required configuration file is missing, malformed (e.g.,
    invalid YAML), or contains logically inconsistent values.
    """


class DataQualityError(PortfolioManagementError):
    """Raised when data quality is insufficient for processing.

    This differs from `DataValidationError` in that the data may be correctly
    formatted but is not usable for a specific task (e.g., too many missing
    values, insufficient history).
    """


class DependencyNotInstalledError(PortfolioManagementError):
    """Raised when an optional runtime dependency is missing.

    Attributes:
        package (str): The name of the missing package.
        context (str): The context or feature that requires the package.
    """

    def __init__(self, package: str, *, context: str) -> None:
        """Initializes the exception.

        Args:
            package: The name of the missing package.
            context: The context in which the package is required.
        """
        self.package = package
        self.context = context
        super().__init__(
            f"{package} is required {context}. Please install {package} before continuing.",
        )


class DataDirectoryNotFoundError(DataValidationError):
    """Raised when the expected Stooq data directory is missing.

    Attributes:
        data_dir (Path): The path to the directory that was not found.
    """

    def __init__(self, data_dir: Path) -> None:
        """Initializes the exception.

        Args:
            data_dir: The path to the missing data directory.
        """
        self.data_dir = data_dir
        super().__init__(
            f"Data directory not found: {data_dir}. "
            "Run prepare_tradeable_data.py to generate the required data directory.",
        )


class InsufficientAssetsError(DataQualityError):
    """Raised when the number of available assets does not meet a minimum threshold.

    Attributes:
        asset_count (int): The number of assets that were available.
        required_count (int): The minimum number of assets that were required.
    """

    def __init__(self, message: str, *, asset_count: int = 0, required_count: int = 0):
        """Initializes the exception.

        Args:
            message: The user-facing error message.
            asset_count: The number of available assets.
            required_count: The number of required assets.
        """
        super().__init__(message)
        self.asset_count = asset_count
        self.required_count = required_count


# --- Business Logic Errors ---

class AssetSelectionError(PortfolioManagementError):
    """Raised for errors that occur during the asset selection phase."""


class ClassificationError(PortfolioManagementError):
    """Raised for errors related to asset classification (e.g., sector, industry)."""


class ReturnCalculationError(PortfolioManagementError):
    """Raised when return calculation fails, often due to missing data."""


class UniverseLoadError(PortfolioManagementError):
    """Raised when a universe definition cannot be loaded or parsed."""


# --- Portfolio Construction Errors ---

class PortfolioConstructionError(PortfolioManagementError):
    """Base exception for errors during the portfolio construction process."""


class InvalidStrategyError(PortfolioConstructionError):
    """Raised when an invalid portfolio construction strategy is specified."""


class ConstraintViolationError(PortfolioConstructionError):
    """Raised when a portfolio constraint (e.g., max weight) is violated.

    Attributes:
        constraint_name (str): The name of the violated constraint.
        violated_value (float | None): The value that violated the constraint.
    """

    def __init__(
        self,
        *,
        constraint_name: str,
        violated_value: float | None,
        message: str | None = None,
    ) -> None:
        """Initializes the exception.

        Args:
            constraint_name: The name of the violated constraint.
            violated_value: The value that violated the constraint.
            message: An optional custom error message.
        """
        self.constraint_name: str = constraint_name
        self.violated_value: float | None = violated_value
        final_message = message or (
            f"Constraint '{constraint_name}' was violated with value: {violated_value}."
        )
        super().__init__(final_message)


class OptimizationError(PortfolioConstructionError):
    """Raised when the portfolio optimization process fails to converge.

    Attributes:
        strategy_name (str): The name of the strategy that failed optimization.
    """

    def __init__(
        self,
        *,
        strategy_name: str,
        message: str | None = None,
    ) -> None:
        """Initializes the exception.

        Args:
            strategy_name: The name of the strategy that failed optimization.
            message: An optional custom error message.
        """
        self.strategy_name: str = strategy_name
        final_message = message or (
            f"Optimization failed for strategy: '{strategy_name}'."
        )
        super().__init__(final_message)


class InsufficientDataError(PortfolioConstructionError):
    """Raised when historical data is insufficient for portfolio construction.

    Attributes:
        required_periods (int | None): The number of required data periods.
        available_periods (int | None): The number of available data periods.
        context (dict[str, object]): Additional context for debugging.
    """

    def __init__(
        self,
        *,
        required_periods: int | None = None,
        available_periods: int | None = None,
        message: str | None = None,
        **context: object,
    ) -> None:
        """Initializes the exception.

        Args:
            required_periods: The number of required data periods.
            available_periods: The number of available data periods.
            message: An optional custom error message.
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
    """Raised when an optional dependency for a strategy is not installed.

    This is a more specific version of `DependencyNotInstalledError` for use
    within the portfolio construction context.

    Attributes:
        dependency_name (str): The name of the missing dependency.
    """

    def __init__(
        self,
        *,
        dependency_name: str,
        message: str | None = None,
    ) -> None:
        """Initializes the exception.

        Args:
            dependency_name: The name of the missing dependency.
            message: An optional custom error message.
        """
        self.dependency_name: str = dependency_name
        final_message = message or (
            f"Optional dependency '{dependency_name}' is not installed. "
            "Please install it to use this feature."
        )
        super().__init__(final_message)


# --- Backtesting Errors ---

class BacktestError(PortfolioManagementError):
    """Base exception for errors that occur during backtesting."""


class InvalidBacktestConfigError(BacktestError):
    """Raised when a backtest configuration value is invalid.

    Attributes:
        config_field (str): The name of the invalid configuration field.
        invalid_value (Any): The value that failed validation.
        reason (str): The reason the value is considered invalid.
    """

    def __init__(
        self,
        *,
        config_field: str,
        invalid_value: Any,
        reason: str,
    ) -> None:
        """Initializes the exception.

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
    """Raised when historical data does not cover the requested backtest period.

    Attributes:
        required_start (date): The earliest date required for the backtest.
        available_start (date): The earliest date available in the dataset.
        asset_ticker (str): The ticker symbol with insufficient history.
    """

    def __init__(
        self,
        *,
        required_start: date,
        available_start: date,
        asset_ticker: str,
    ) -> None:
        """Initializes the exception.

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
    """Raised when a rebalancing operation fails for a specific date.

    Attributes:
        rebalance_date (date): The date of the failed rebalancing event.
        error_type (str): A classification of the rebalancing failure (e.g., "OPTIMIZATION_FAILED").
        context (dict[str, Any]): Additional diagnostic context for debugging.
    """

    def __init__(
        self,
        *,
        rebalance_date: date,
        error_type: str,
        context: dict[str, Any] | None = None,
        message: str | None = None,
    ) -> None:
        """Initializes the exception.

        Args:
            rebalance_date: The date of the failed rebalancing event.
            error_type: Classification of the rebalancing failure.
            context: Additional diagnostic context for debugging.
            message: An optional custom error message.
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
    """Raised when transaction cost calculations fail.

    Attributes:
        transaction_type (str): The type of transaction being processed (e.g., "buy", "sell").
        amount (float): The monetary amount of the transaction.
        reason (str): An explanation of why the cost calculation failed.
    """

    def __init__(
        self,
        *,
        transaction_type: str,
        amount: float,
        reason: str,
        message: str | None = None,
    ) -> None:
        """Initializes the exception.

        Args:
            transaction_type: The type of transaction being processed.
            amount: The monetary amount associated with the transaction.
            reason: Explanation of why the cost calculation failed.
            message: An optional custom error message.
        """
        self.transaction_type: str = transaction_type
        self.amount: float = amount
        self.reason: str = reason
        final_message = message or (
            f"Transaction cost error for '{transaction_type}' transaction "
            f"with amount {amount}: {reason}."
        )
        super().__init__(final_message)