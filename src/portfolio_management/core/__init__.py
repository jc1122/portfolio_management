"""Core foundation utilities, exceptions, configuration, and types.

This package provides the foundation layer for the portfolio management toolkit,
including:

- Exception hierarchy for all error types
- Configuration constants and mappings
- Parallel execution utilities
- Common type definitions and protocols

Public API:
    Exceptions:
        - PortfolioManagementError (base exception)
        - DataValidationError, ConfigurationError, DataQualityError
        - AssetSelectionError, ClassificationError, ReturnCalculationError
        - PortfolioConstructionError, OptimizationError, ConstraintViolationError
        - BacktestError, RebalanceError, TransactionCostError
    
    Configuration:
        - STOOQ_COLUMNS, LEGACY_PREFIXES, SYMBOL_ALIAS_MAP
        - REGION_CURRENCY_MAP, STOOQ_PANDAS_COLUMNS
    
    Utilities:
        - run_in_parallel: Execute tasks in parallel with result ordering
        - log_duration: Context manager for timing operations
    
    Types:
        - SymbolType, DateType, PriceDataFrame (type aliases)
        - IDataLoader, IAssetFilter, IPortfolioStrategy (protocols)
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
from .types import (
    DateType,
    IAssetFilter,
    IDataLoader,
    IPortfolioStrategy,
    PriceDataFrame,
    SymbolType,
)
from .utils import _run_in_parallel as run_in_parallel
from .utils import log_duration

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
    "run_in_parallel",
    "log_duration",
    # Types
    "SymbolType",
    "DateType",
    "PriceDataFrame",
    "IDataLoader",
    "IAssetFilter",
    "IPortfolioStrategy",
]
