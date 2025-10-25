"""High-level service layer for complex application workflows.

This package exposes orchestrators that wrap the core domain modules into
programmatic, reusable entry points.  Each service coordinates multiple
subsystems while remaining stateless and dependency-injectable to support unit
 testing and CLI reuse.
"""

from .backtest import BacktestRequest, BacktestResult, BacktestService
from .data_preparation import (
    DataPreparationConfig,
    DataPreparationResult,
    DataPreparationService,
)
from .portfolio_construction import (
    PortfolioConstructionRequest,
    PortfolioConstructionResult,
    PortfolioConstructionService,
)
from .universe_management import (
    UniverseComparison,
    UniverseList,
    UniverseLoadResult,
    UniverseManagementService,
)

__all__ = [
    "BacktestRequest",
    "BacktestResult",
    "BacktestService",
    "DataPreparationConfig",
    "DataPreparationResult",
    "DataPreparationService",
    "PortfolioConstructionRequest",
    "PortfolioConstructionResult",
    "PortfolioConstructionService",
    "UniverseComparison",
    "UniverseList",
    "UniverseLoadResult",
    "UniverseManagementService",
]
