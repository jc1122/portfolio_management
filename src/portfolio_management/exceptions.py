"""Custom exception hierarchy for portfolio management workflows.

DEPRECATED: This module has been moved to portfolio_management.core.exceptions.
Import from there instead. This module is maintained for backward compatibility only.
"""

# Backward compatibility - re-export all exceptions from core
from .core.exceptions import (  # noqa: F401
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

__all__ = [
    "PortfolioManagementError",
    "DataValidationError",
    "DataDirectoryNotFoundError",
    "DataQualityError",
    "InsufficientAssetsError",
    "AssetSelectionError",
    "ClassificationError",
    "ReturnCalculationError",
    "UniverseLoadError",
    "PortfolioConstructionError",
    "InvalidStrategyError",
    "ConstraintViolationError",
    "OptimizationError",
    "InsufficientDataError",
    "DependencyError",
    "BacktestError",
    "InvalidBacktestConfigError",
    "InsufficientHistoryError",
    "RebalanceError",
    "TransactionCostError",
    "ConfigurationError",
    "DependencyNotInstalledError",
]
