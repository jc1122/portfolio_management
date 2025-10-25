"""Core foundation for the portfolio management toolkit.

This package provides the foundational utilities, exceptions, configuration,
and types for the entire system. It serves as the stable base layer upon
which other components like data loading, factor computation, and portfolio
construction are built.

The package exposes its main components at the top level for convenient access.

Example:
    Importing and using common components from the core package.

    >>> from portfolio_management.core import (
    ...     _run_in_parallel,
    ...     log_duration,
    ...     PortfolioManagementError
    ... )
    >>>
    >>> def sample_task(x: int) -> int:
    ...     return x * x
    >>>
    >>> with log_duration("Running sample parallel task"):
    ...     # Executes sample_task(i) for i in [1, 2, 3] in parallel
    ...     # The arguments must be wrapped in tuples, e.g., [(1,), (2,), (3,)]
    ...     results = _run_in_parallel(sample_task, [(1,), (2,), (3,)], max_workers=2)
    ...
    >>> sorted(results) == [1, 4, 9]
    True
    >>>
    >>> try:
    ...     raise PortfolioManagementError("Something went wrong.")
    ... except PortfolioManagementError as e:
    ...     print(f"Caught expected error: {e}")
    Caught expected error: Something went wrong.

Key Components:
    - **Exceptions**: A comprehensive hierarchy of custom exceptions, with
      `PortfolioManagementError` as the base. This allows for granular
      error handling across the application.
    - **Configuration**: Global constants and mappings, such as column names
      (`STOOQ_COLUMNS`) and region-to-currency maps.
    - **Utilities**: High-level helper functions, including `_run_in_parallel`
      for efficient parallel processing and `log_duration` for timing code blocks.
    - **Types**: Common type aliases (`SymbolType`, `DateLike`) and TypedDicts
      for structuring data like prices and returns, enhancing static analysis.
    - **Protocols**: `typing.Protocol` definitions that establish contracts for
      key components like data loaders (`DataLoaderProtocol`) and factor
      computation engines (`FactorProtocol`), enabling a modular architecture.

"""

from .config import (
    LEGACY_PREFIXES,
    REGION_CURRENCY_MAP,
    STOOQ_COLUMNS,
    STOOQ_PANDAS_COLUMNS,
    SYMBOL_ALIAS_MAP,
)
from .exceptions import (
    AssetSelectionError,
    BacktestError,
    ClassificationError,
    ConfigurationError,
    ConstraintViolationError,
    DataDirectoryNotFoundError,
    DataQualityError,
    DataValidationError,
    DependencyError,
    DependencyNotInstalledError,
    InsufficientAssetsError,
    InsufficientDataError,
    InsufficientHistoryError,
    InvalidBacktestConfigError,
    InvalidStrategyError,
    OptimizationError,
    PortfolioConstructionError,
    PortfolioManagementError,
    RebalanceError,
    ReturnCalculationError,
    TransactionCostError,
    UniverseLoadError,
)
from .protocols import (
    CacheProtocol,
    DataLoaderProtocol,
    EligibilityProtocol,
    FactorProtocol,
)
from .types import (
    DateLike,
    DateType,
    FactorScores,
    IAssetFilter,
    IDataLoader,
    IPortfolioStrategy,
    PriceDataFrame,
    ReturnsDataFrame,
    SymbolType,
)
from .utils import _run_in_parallel, log_duration

__all__ = [
    # Exceptions - Base
    "PortfolioManagementError",
    # Exceptions - Data
    "DataValidationError",
    "DataDirectoryNotFoundError",
    "DataQualityError",
    "InsufficientAssetsError",
    # Exceptions - Business Logic
    "AssetSelectionError",
    "ClassificationError",
    "ReturnCalculationError",
    "UniverseLoadError",
    # Exceptions - Portfolio Construction
    "PortfolioConstructionError",
    "InvalidStrategyError",
    "ConstraintViolationError",
    "OptimizationError",
    "InsufficientDataError",
    "DependencyError",
    # Exceptions - Backtesting
    "BacktestError",
    "InvalidBacktestConfigError",
    "InsufficientHistoryError",
    "RebalanceError",
    "TransactionCostError",
    # Exceptions - System
    "ConfigurationError",
    "DependencyNotInstalledError",
    # Configuration
    "STOOQ_COLUMNS",
    "STOOQ_PANDAS_COLUMNS",
    "LEGACY_PREFIXES",
    "SYMBOL_ALIAS_MAP",
    "REGION_CURRENCY_MAP",
    # Utilities
    "_run_in_parallel",
    "log_duration",
    # Types
    "SymbolType",
    "DateType",
    "DateLike",
    "PriceDataFrame",
    "ReturnsDataFrame",
    "FactorScores",
    "IDataLoader",
    "IAssetFilter",
    "IPortfolioStrategy",
    # Protocols
    "CacheProtocol",
    "DataLoaderProtocol",
    "FactorProtocol",
    "EligibilityProtocol",
]
