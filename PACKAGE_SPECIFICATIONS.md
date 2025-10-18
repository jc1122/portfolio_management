# Package Specifications and Technical Details

**Date:** October 18, 2025
**Related:** MODULAR_MONOLITH_REFACTORING_PLAN.md, ARCHITECTURE_DIAGRAM.md

## Overview

This document provides detailed technical specifications for each package in the modular monolith architecture, including public APIs, internal structure, dependencies, and implementation guidelines.

______________________________________________________________________

## Package 1: core (Foundation Layer)

### Purpose

Provide foundational utilities, exceptions, configuration, and common types used across all packages.

### Public API

```python
# portfolio_management/core/__init__.py

from .exceptions import (
    # Base exceptions
    PortfolioManagementError,
    # Data exceptions
    DataValidationError,
    DataDirectoryNotFoundError,
    InsufficientDataError,
    # Business logic exceptions
    AssetSelectionError,
    ClassificationError,
    ReturnCalculationError,
    PortfolioConstructionError,
    OptimizationError,
    ConstraintViolationError,
    # System exceptions
    DependencyError,
    ConfigurationError,
)

from .config import (
    # Stooq configuration
    STOOQ_COLUMNS,
    LEGACY_PREFIXES,
    SYMBOL_ALIAS_MAP,
    # File patterns
    DATA_FILE_EXTENSIONS,
    # Other constants
)

from .utils import (
    run_in_parallel,
    timing_context,
    setup_logging,
)

from .types import (
    # Protocols
    IDataLoader,
    IAssetFilter,
    IPortfolioStrategy,
    # Type aliases
    SymbolType,
    DateType,
    PriceDataFrame,
)

__all__ = [
    # Exceptions
    "PortfolioManagementError",
    "DataValidationError",
    # ... (all exceptions)
    # Config
    "STOOQ_COLUMNS",
    # ... (all config)
    # Utils
    "run_in_parallel",
    "timing_context",
    "setup_logging",
    # Types
    "IDataLoader",
    # ... (all types)
]
```

### Internal Structure

```
core/
├── __init__.py (public API exports)
├── exceptions.py (exception hierarchy - no changes from current)
├── config.py (constants and configuration - no changes from current)
├── utils.py (utilities - no changes from current)
└── types.py (NEW - common protocols and type aliases)
```

### Implementation Details

#### types.py (NEW FILE)

```python
"""Common types, protocols, and interfaces used across packages."""

from typing import Protocol, TypeAlias
from datetime import date
import pandas as pd

# Type aliases
SymbolType: TypeAlias = str
DateType: TypeAlias = date | str
PriceDataFrame: TypeAlias = pd.DataFrame  # With specific columns expected

class IDataLoader(Protocol):
    """Protocol for data loading operations."""

    def load(self, path: str) -> pd.DataFrame:
        """Load data from path."""
        ...

class IAssetFilter(Protocol):
    """Protocol for asset filtering operations."""

    def filter(self, assets: list, criteria: object) -> list:
        """Filter assets based on criteria."""
        ...

class IPortfolioStrategy(Protocol):
    """Protocol for portfolio construction strategies."""

    def construct(self, returns: pd.DataFrame) -> pd.Series:
        """Construct portfolio weights from returns."""
        ...
```

### Dependencies

- None (foundation layer)

### Key Changes from Current

- Add `types.py` with common protocols
- Expose utilities with cleaner API (rename `_run_in_parallel` → `run_in_parallel`)
- No other changes to existing code

______________________________________________________________________

## Package 2: data (Data Management Layer)

### Purpose

Handle all data ingestion, I/O operations, symbol matching, and data quality analysis.

### Public API

```python
# portfolio_management/data/__init__.py

from .models import (
    StooqFile,
    TradeableInstrument,
    TradeableMatch,
    ExportConfig,
)

from .ingestion import (
    build_stooq_index,
    load_stooq_index,
)

from .io import (
    read_stooq_index,
    write_stooq_index,
    read_tradeable_instruments,
    write_match_report,
    export_tradeable_prices,
)

from .matching import (
    match_symbols,
    build_stooq_lookup,
)

from .analysis import (
    analyze_price_quality,
    infer_currency,
    resolve_currency,
    summarize_price_file,
)

__all__ = [
    # Models
    "StooqFile",
    "TradeableInstrument",
    "TradeableMatch",
    "ExportConfig",
    # Ingestion
    "build_stooq_index",
    "load_stooq_index",
    # I/O
    "read_stooq_index",
    "write_stooq_index",
    "read_tradeable_instruments",
    "write_match_report",
    "export_tradeable_prices",
    # Matching
    "match_symbols",
    "build_stooq_lookup",
    # Analysis
    "analyze_price_quality",
    "infer_currency",
    "resolve_currency",
    "summarize_price_file",
]
```

### Internal Structure

```
data/
├── __init__.py (public API)
├── models.py (data models - from current models.py)
├── ingestion/
│   ├── __init__.py
│   ├── stooq.py (from current stooq.py)
│   └── loaders.py (price file loading utilities)
├── io/
│   ├── __init__.py
│   ├── readers.py (CSV reading - split from io.py)
│   ├── writers.py (CSV writing - split from io.py)
│   └── exporters.py (price export - split from io.py)
├── matching/
│   ├── __init__.py
│   ├── matchers.py (from current matching.py)
│   └── strategies.py (matching strategies - split from matching.py)
└── analysis/
    ├── __init__.py
    ├── quality.py (data quality checks - split from analysis.py)
    └── currency.py (currency inference - split from analysis.py)
```

### Module Split Guidelines

#### io.py → readers.py, writers.py, exporters.py

**readers.py:**

- `read_stooq_index()`
- `load_tradeable_instruments()`
- Helper functions for reading CSVs

**writers.py:**

- `write_stooq_index()`
- `write_match_report()`
- Helper functions for writing CSVs

**exporters.py:**

- `export_tradeable_prices()`
- `ExportConfig` usage
- Parallel export logic

#### analysis.py → quality.py, currency.py

**quality.py:**

- `summarize_price_file()`
- Data quality checks
- Gap analysis

**currency.py:**

- `infer_currency()`
- `resolve_currency()`
- Currency resolution logic

### Dependencies

- core (exceptions, config, utils)

### Key Changes from Current

- Split large modules for clarity
- Keep models.py as-is (only data models)
- Organize by functional area

______________________________________________________________________

## Package 3: assets (Asset Universe Layer)

### Purpose

Manage asset selection, classification, and universe definitions for portfolio construction.

### Public API

```python
# portfolio_management/assets/__init__.py

from .selection import (
    FilterCriteria,
    SelectedAsset,
    AssetSelector,
)

from .classification import (
    AssetClass,
    Geography,
    SubClass,
    AssetClassification,
    AssetClassifier,
    ClassificationOverrides,
)

from .universes import (
    UniverseDefinition,
    UniverseConfigLoader,
    UniverseManager,
)

__all__ = [
    # Selection
    "FilterCriteria",
    "SelectedAsset",
    "AssetSelector",
    # Classification
    "AssetClass",
    "Geography",
    "SubClass",
    "AssetClassification",
    "AssetClassifier",
    "ClassificationOverrides",
    # Universes
    "UniverseDefinition",
    "UniverseConfigLoader",
    "UniverseManager",
]
```

### Internal Structure

```
assets/
├── __init__.py (public API)
├── selection/
│   ├── __init__.py
│   ├── criteria.py (FilterCriteria dataclass)
│   ├── models.py (SelectedAsset dataclass)
│   └── selector.py (AssetSelector class)
├── classification/
│   ├── __init__.py
│   ├── taxonomy.py (AssetClass, Geography, SubClass enums)
│   ├── models.py (AssetClassification dataclass)
│   ├── classifier.py (AssetClassifier class)
│   └── overrides.py (ClassificationOverrides class)
└── universes/
    ├── __init__.py
    ├── definition.py (UniverseDefinition dataclass)
    ├── loader.py (UniverseConfigLoader class)
    └── manager.py (UniverseManager class)
```

### Module Split Guidelines

#### selection.py → criteria.py, models.py, selector.py

**criteria.py:**

```python
from dataclasses import dataclass, field
from portfolio_management.core import DataValidationError

@dataclass
class FilterCriteria:
    """Configuration for asset filtering."""
    data_status: list[str] = field(default_factory=lambda: ["ok"])
    min_history_days: int = 252
    # ... rest of FilterCriteria

    def validate(self) -> None:
        """Validate criteria."""
        # ... validation logic
```

**models.py:**

```python
from dataclasses import dataclass

@dataclass
class SelectedAsset:
    """Represents a selected asset with metadata."""
    symbol: str
    isin: str
    name: str
    # ... rest of SelectedAsset fields
```

**selector.py:**

```python
from portfolio_management.core import AssetSelectionError
from .criteria import FilterCriteria
from .models import SelectedAsset

class AssetSelector:
    """Main asset selection engine."""

    def filter(self, assets: list, criteria: FilterCriteria) -> list[SelectedAsset]:
        """Filter assets based on criteria."""
        # ... filtering logic
```

#### classification.py → taxonomy.py, models.py, classifier.py, overrides.py

**taxonomy.py:**

```python
from enum import Enum

class AssetClass(str, Enum):
    """Broad asset classes."""
    EQUITY = "equity"
    FIXED_INCOME = "fixed_income"
    # ... rest of enum

class Geography(str, Enum):
    """Geographical classifications."""
    # ... enum values

class SubClass(str, Enum):
    """Granular sub-classes."""
    # ... enum values
```

**models.py:**

```python
from dataclasses import dataclass
from .taxonomy import AssetClass, Geography

@dataclass
class AssetClassification:
    """Classification result for an asset."""
    symbol: str
    asset_class: str
    geography: Geography
    # ... rest of fields
```

**classifier.py:**

```python
from portfolio_management.core import ClassificationError
from portfolio_management.assets.selection import SelectedAsset
from .models import AssetClassification
from .overrides import ClassificationOverrides
from .taxonomy import AssetClass, Geography, SubClass

class AssetClassifier:
    """Rule-based asset classification engine."""

    def __init__(self, overrides: ClassificationOverrides | None = None):
        self.overrides = overrides

    def classify(self, asset: SelectedAsset) -> AssetClassification:
        """Classify a single asset."""
        # ... classification logic
```

**overrides.py:**

```python
from pathlib import Path
import pandas as pd

class ClassificationOverrides:
    """Manual classification overrides."""

    @classmethod
    def from_csv(cls, path: Path) -> ClassificationOverrides:
        """Load from CSV."""
        # ... loading logic
```

#### universes.py → definition.py, loader.py, manager.py

**definition.py:**

```python
from dataclasses import dataclass, field
from portfolio_management.assets.selection import FilterCriteria
from portfolio_management.analytics import ReturnConfig

@dataclass
class UniverseDefinition:
    """Investment universe definition."""
    description: str
    filter_criteria: FilterCriteria
    classification_requirements: dict = field(default_factory=dict)
    return_config: ReturnConfig = field(default_factory=ReturnConfig)

    def validate(self) -> None:
        """Validate definition."""
        # ... validation logic
```

**loader.py:**

```python
from pathlib import Path
import yaml
from portfolio_management.core import ConfigurationError
from .definition import UniverseDefinition

class UniverseConfigLoader:
    """Load universe definitions from YAML."""

    @staticmethod
    def load_config(path: Path) -> dict[str, UniverseDefinition]:
        """Load and parse configuration."""
        # ... loading logic
```

**manager.py:**

```python
from portfolio_management.core import UniverseLoadError
from .definition import UniverseDefinition
from .loader import UniverseConfigLoader

class UniverseManager:
    """Manage multiple universe definitions."""

    def __init__(self, config_path: Path):
        self.universes = UniverseConfigLoader.load_config(config_path)

    def get_universe(self, name: str) -> UniverseDefinition:
        """Retrieve universe by name."""
        # ... retrieval logic
```

### Dependencies

- core (exceptions, config)
- data (for loading price data if needed)

### Key Changes from Current

- Split monolithic modules into focused files
- Clear separation between data models and logic
- Better encapsulation of classification rules

______________________________________________________________________

## Package 4: analytics (Financial Calculations Layer)

### Purpose

Perform financial calculations including returns, performance metrics, and risk analytics.

### Public API

```python
# portfolio_management/analytics/__init__.py

from .returns import (
    ReturnConfig,
    ReturnSummary,
    PriceLoader,
    ReturnCalculator,
)

from .metrics import (
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    calculate_max_drawdown,
    calculate_volatility,
)

__all__ = [
    # Returns
    "ReturnConfig",
    "ReturnSummary",
    "PriceLoader",
    "ReturnCalculator",
    # Metrics
    "calculate_sharpe_ratio",
    "calculate_sortino_ratio",
    "calculate_max_drawdown",
    "calculate_volatility",
]
```

### Internal Structure

```
analytics/
├── __init__.py (public API)
├── returns/
│   ├── __init__.py
│   ├── config.py (ReturnConfig dataclass)
│   ├── models.py (ReturnSummary dataclass)
│   ├── loaders.py (PriceLoader class)
│   └── calculator.py (ReturnCalculator class)
└── metrics/
    ├── __init__.py
    ├── performance.py (Sharpe, Sortino, etc.)
    └── risk.py (volatility, drawdown, VaR)
```

### Module Split Guidelines

#### returns.py → config.py, models.py, loaders.py, calculator.py

**config.py:**

```python
from dataclasses import dataclass

@dataclass
class ReturnConfig:
    """Configuration for return preparation."""
    method: str = "simple"
    frequency: str = "daily"
    risk_free_rate: float = 0.0
    # ... rest of config

    def validate(self) -> None:
        """Validate configuration."""
        # ... validation
```

**models.py:**

```python
from dataclasses import dataclass
import pandas as pd

@dataclass
class ReturnSummary:
    """Summary statistics for returns."""
    mean_returns: pd.Series
    volatility: pd.Series
    correlation: pd.DataFrame
    coverage: pd.Series
```

**loaders.py:**

```python
from pathlib import Path
import pandas as pd
from portfolio_management.core import InsufficientDataError

class PriceLoader:
    """Load and validate price files."""

    def load_price_file(self, path: Path) -> pd.Series:
        """Load single price file."""
        # ... loading logic
```

**calculator.py:**

```python
import pandas as pd
from portfolio_management.core import ReturnCalculationError
from portfolio_management.assets import SelectedAsset
from .config import ReturnConfig
from .models import ReturnSummary
from .loaders import PriceLoader

class ReturnCalculator:
    """Calculate aligned return series."""

    def __init__(self, config: ReturnConfig):
        self.config = config
        self.loader = PriceLoader()

    def calculate_returns(
        self,
        assets: list[SelectedAsset],
        prices_dir: Path
    ) -> tuple[pd.DataFrame, ReturnSummary]:
        """Calculate and align returns."""
        # ... calculation logic
```

#### Extract Metrics (from backtest.py or create new)

**metrics/performance.py:**

```python
import pandas as pd
import numpy as np

def calculate_sharpe_ratio(
    returns: pd.Series,
    risk_free_rate: float = 0.0
) -> float:
    """Calculate Sharpe ratio."""
    # ... calculation

def calculate_sortino_ratio(
    returns: pd.Series,
    target_return: float = 0.0
) -> float:
    """Calculate Sortino ratio."""
    # ... calculation
```

**metrics/risk.py:**

```python
import pandas as pd

def calculate_volatility(returns: pd.Series) -> float:
    """Calculate annualized volatility."""
    # ... calculation

def calculate_max_drawdown(equity_curve: pd.Series) -> float:
    """Calculate maximum drawdown."""
    # ... calculation

def calculate_var(
    returns: pd.Series,
    confidence_level: float = 0.95
) -> float:
    """Calculate Value at Risk."""
    # ... calculation
```

### Dependencies

- core (exceptions, config)
- assets (SelectedAsset model)

### Key Changes from Current

- Extract metrics from backtest.py if they exist
- Split returns.py into focused modules
- Add more financial metrics as needed

______________________________________________________________________

## Package 5: portfolio (Portfolio Construction Layer)

### Purpose

Construct portfolios using various allocation strategies with constraints and rebalancing logic.

### Public API

```python
# portfolio_management/portfolio/__init__.py

from .models import (
    Portfolio,
    StrategyType,
)

from .builder import (
    PortfolioBuilder,
)

from .strategies import (
    PortfolioStrategy,
    EqualWeightStrategy,
    RiskParityStrategy,
    MeanVarianceStrategy,
)

from .constraints import (
    PortfolioConstraints,
    validate_constraints,
)

from .rebalancing import (
    RebalanceConfig,
    calculate_rebalance_trades,
)

__all__ = [
    # Models
    "Portfolio",
    "StrategyType",
    # Builder
    "PortfolioBuilder",
    # Strategies
    "PortfolioStrategy",
    "EqualWeightStrategy",
    "RiskParityStrategy",
    "MeanVarianceStrategy",
    # Constraints
    "PortfolioConstraints",
    "validate_constraints",
    # Rebalancing
    "RebalanceConfig",
    "calculate_rebalance_trades",
]
```

### Internal Structure

```
portfolio/
├── __init__.py (public API)
├── models.py (Portfolio, StrategyType)
├── builder.py (PortfolioBuilder orchestration)
├── strategies/
│   ├── __init__.py
│   ├── base.py (PortfolioStrategy ABC)
│   ├── equal_weight.py (EqualWeightStrategy)
│   ├── risk_parity.py (RiskParityStrategy)
│   └── mean_variance.py (MeanVarianceStrategy)
├── constraints/
│   ├── __init__.py
│   ├── models.py (PortfolioConstraints)
│   └── validators.py (constraint validation)
└── rebalancing/
    ├── __init__.py
    ├── config.py (RebalanceConfig)
    └── logic.py (rebalancing algorithms)
```

### Module Split Guidelines

#### portfolio.py → Comprehensive Split

**models.py:**

```python
from dataclasses import dataclass
from enum import Enum
import pandas as pd

class StrategyType(str, Enum):
    """Supported strategies."""
    EQUAL_WEIGHT = "equal_weight"
    RISK_PARITY = "risk_parity"
    MEAN_VARIANCE = "mean_variance"

@dataclass
class Portfolio:
    """Portfolio with weights and metadata."""
    weights: pd.Series
    strategy: str
    timestamp: pd.Timestamp
    metadata: dict | None = None

    def validate(self) -> None:
        """Validate portfolio."""
        # ... validation
```

**builder.py:**

```python
import pandas as pd
from portfolio_management.analytics import ReturnCalculator
from .strategies import PortfolioStrategy
from .constraints import PortfolioConstraints, validate_constraints
from .models import Portfolio

class PortfolioBuilder:
    """Orchestrate portfolio construction."""

    def __init__(
        self,
        strategy: PortfolioStrategy,
        constraints: PortfolioConstraints | None = None
    ):
        self.strategy = strategy
        self.constraints = constraints

    def build(
        self,
        returns: pd.DataFrame,
        **kwargs
    ) -> Portfolio:
        """Build portfolio using strategy."""
        # ... orchestration logic
        weights = self.strategy.construct(returns, **kwargs)

        if self.constraints:
            validate_constraints(weights, self.constraints)

        return Portfolio(
            weights=weights,
            strategy=self.strategy.__class__.__name__,
            # ...
        )
```

**strategies/base.py:**

```python
from abc import ABC, abstractmethod
import pandas as pd

class PortfolioStrategy(ABC):
    """Base class for portfolio construction strategies."""

    @abstractmethod
    def construct(
        self,
        returns: pd.DataFrame,
        **kwargs
    ) -> pd.Series:
        """Construct portfolio weights."""
        pass

    def validate_inputs(self, returns: pd.DataFrame) -> None:
        """Validate inputs before construction."""
        # ... common validation
```

**strategies/equal_weight.py:**

```python
import pandas as pd
from .base import PortfolioStrategy

class EqualWeightStrategy(PortfolioStrategy):
    """Equal-weight allocation strategy."""

    def construct(
        self,
        returns: pd.DataFrame,
        **kwargs
    ) -> pd.Series:
        """Construct equal-weighted portfolio."""
        n_assets = len(returns.columns)
        weights = pd.Series(
            data=1.0 / n_assets,
            index=returns.columns
        )
        return weights
```

**strategies/risk_parity.py:**

```python
import pandas as pd
import numpy as np
from portfolio_management.core import OptimizationError
from .base import PortfolioStrategy

class RiskParityStrategy(PortfolioStrategy):
    """Risk parity allocation strategy."""

    def construct(
        self,
        returns: pd.DataFrame,
        **kwargs
    ) -> pd.Series:
        """Construct risk-parity portfolio."""
        # ... risk parity optimization
        # Use scipy.optimize or similar
        pass
```

**strategies/mean_variance.py:**

```python
import pandas as pd
from portfolio_management.core import OptimizationError, DependencyError
from .base import PortfolioStrategy

try:
    from cvxpy import Variable, Problem, Minimize
    HAS_CVXPY = True
except ImportError:
    HAS_CVXPY = False

class MeanVarianceStrategy(PortfolioStrategy):
    """Mean-variance optimization strategy."""

    def __init__(self, target_return: float | None = None):
        if not HAS_CVXPY:
            raise DependencyError(
                "cvxpy",
                "Mean-variance optimization requires cvxpy"
            )
        self.target_return = target_return

    def construct(
        self,
        returns: pd.DataFrame,
        **kwargs
    ) -> pd.Series:
        """Construct mean-variance optimal portfolio."""
        # ... mean-variance optimization
        pass
```

**constraints/models.py:**

```python
from dataclasses import dataclass

@dataclass
class PortfolioConstraints:
    """Portfolio constraints."""
    max_weight: float = 0.25
    min_weight: float = 0.0
    max_equity_exposure: float = 0.90
    min_bond_exposure: float = 0.10
    sector_limits: dict[str, float] | None = None

    def validate(self) -> None:
        """Validate constraints."""
        # ... validation
```

**constraints/validators.py:**

```python
import pandas as pd
from portfolio_management.core import ConstraintViolationError
from .models import PortfolioConstraints

def validate_constraints(
    weights: pd.Series,
    constraints: PortfolioConstraints
) -> None:
    """Validate portfolio against constraints."""
    # Check max/min weights
    if (weights > constraints.max_weight).any():
        raise ConstraintViolationError("...")

    if (weights < constraints.min_weight).any():
        raise ConstraintViolationError("...")

    # ... other validations
```

**rebalancing/config.py:**

```python
from dataclasses import dataclass

@dataclass
class RebalanceConfig:
    """Rebalancing configuration."""
    frequency: int = 30  # days
    tolerance_bands: float = 0.20
    min_trade_size: float = 0.01
    cost_per_trade: float = 0.001

    def validate(self) -> None:
        """Validate config."""
        # ... validation
```

**rebalancing/logic.py:**

```python
import pandas as pd
from .config import RebalanceConfig

def calculate_rebalance_trades(
    current_weights: pd.Series,
    target_weights: pd.Series,
    config: RebalanceConfig
) -> dict[str, float]:
    """Calculate trades needed to rebalance."""
    trades = {}
    for symbol in target_weights.index:
        current = current_weights.get(symbol, 0.0)
        target = target_weights[symbol]
        diff = target - current

        if abs(diff) >= config.min_trade_size:
            trades[symbol] = diff

    return trades
```

### Dependencies

- core (exceptions)
- analytics (for return data)

### Key Changes from Current

- Split 821-line portfolio.py into focused modules
- Each strategy in its own file
- Clear separation of concerns
- Easy to add new strategies

______________________________________________________________________

## Package 6: backtesting (Historical Simulation Layer)

### Purpose

Simulate portfolio performance over historical periods with transaction costs and rebalancing.

### Public API

```python
# portfolio_management/backtesting/__init__.py

from .models import (
    BacktestConfig,
    BacktestResult,
    PerformanceMetrics,
)

from .engine import (
    BacktestEngine,
    run_backtest,
)

from .transactions import (
    TransactionCostModel,
    calculate_commission,
    calculate_slippage,
)

from .rebalancing import (
    RebalanceTrigger,
    RebalanceFrequency,
    RebalanceEvent,
)

from .performance import (
    calculate_performance_metrics,
    analyze_trades,
)

__all__ = [
    # Models
    "BacktestConfig",
    "BacktestResult",
    "PerformanceMetrics",
    # Engine
    "BacktestEngine",
    "run_backtest",
    # Transactions
    "TransactionCostModel",
    "calculate_commission",
    "calculate_slippage",
    # Rebalancing
    "RebalanceTrigger",
    "RebalanceFrequency",
    "RebalanceEvent",
    # Performance
    "calculate_performance_metrics",
    "analyze_trades",
]
```

### Internal Structure

```
backtesting/
├── __init__.py (public API)
├── models.py (BacktestConfig, BacktestResult, PerformanceMetrics)
├── engine/
│   ├── __init__.py
│   ├── backtest.py (BacktestEngine class)
│   └── simulator.py (portfolio evolution simulation)
├── transactions/
│   ├── __init__.py
│   ├── costs.py (transaction cost calculation)
│   └── execution.py (trade execution logic)
├── rebalancing/
│   ├── __init__.py
│   ├── triggers.py (RebalanceTrigger, RebalanceFrequency)
│   └── events.py (RebalanceEvent)
└── performance/
    ├── __init__.py
    ├── metrics.py (PerformanceMetrics calculation)
    └── analytics.py (performance analysis utilities)
```

### Module Split Guidelines

#### backtest.py → Comprehensive Split

**models.py:**

```python
from dataclasses import dataclass
from decimal import Decimal
import datetime
import pandas as pd

@dataclass
class BacktestConfig:
    """Backtest configuration."""
    start_date: datetime.date
    end_date: datetime.date
    initial_capital: Decimal = Decimal("100000.00")
    # ... other config

    def validate(self) -> None:
        """Validate configuration."""
        # ... validation

@dataclass
class BacktestResult:
    """Backtest results."""
    equity_curve: pd.DataFrame
    trades: list[RebalanceEvent]
    metrics: PerformanceMetrics
    config: BacktestConfig

@dataclass
class PerformanceMetrics:
    """Performance metrics."""
    total_return: float
    annual_return: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    # ... other metrics
```

**engine/backtest.py:**

```python
import pandas as pd
from portfolio_management.portfolio import Portfolio, PortfolioStrategy
from ..models import BacktestConfig, BacktestResult
from .simulator import PortfolioSimulator

class BacktestEngine:
    """Main backtesting engine."""

    def __init__(self, config: BacktestConfig):
        self.config = config
        self.simulator = PortfolioSimulator(config)

    def run(
        self,
        strategy: PortfolioStrategy,
        returns: pd.DataFrame
    ) -> BacktestResult:
        """Run backtest."""
        # ... orchestration logic
        result = self.simulator.simulate(strategy, returns)
        return result
```

**engine/simulator.py:**

```python
import pandas as pd
from portfolio_management.portfolio import PortfolioStrategy
from ..models import BacktestConfig, BacktestResult
from ..transactions import TransactionCostModel

class PortfolioSimulator:
    """Simulate portfolio evolution."""

    def __init__(self, config: BacktestConfig):
        self.config = config
        self.cost_model = TransactionCostModel(config)

    def simulate(
        self,
        strategy: PortfolioStrategy,
        returns: pd.DataFrame
    ) -> BacktestResult:
        """Simulate portfolio evolution."""
        # ... simulation logic
        pass
```

**transactions/costs.py:**

```python
from decimal import Decimal

class TransactionCostModel:
    """Model transaction costs."""

    def __init__(self, config):
        self.commission_pct = config.commission_pct
        self.commission_min = config.commission_min
        self.slippage_bps = config.slippage_bps

    def calculate_commission(
        self,
        trade_value: Decimal
    ) -> Decimal:
        """Calculate commission for trade."""
        commission = trade_value * Decimal(str(self.commission_pct))
        return max(commission, Decimal(str(self.commission_min)))

    def calculate_slippage(
        self,
        trade_value: Decimal
    ) -> Decimal:
        """Calculate slippage for trade."""
        return trade_value * Decimal(str(self.slippage_bps / 10000))
```

**rebalancing/triggers.py:**

```python
from enum import Enum

class RebalanceFrequency(Enum):
    """Rebalancing frequencies."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"

class RebalanceTrigger(Enum):
    """Rebalance trigger types."""
    SCHEDULED = "scheduled"
    OPPORTUNISTIC = "opportunistic"
    FORCED = "forced"
```

**rebalancing/events.py:**

```python
from dataclasses import dataclass
from decimal import Decimal
import datetime
from .triggers import RebalanceTrigger

@dataclass
class RebalanceEvent:
    """Record of rebalancing event."""
    date: datetime.date
    trigger: RebalanceTrigger
    trades: dict[str, int]
    costs: Decimal
    pre_value: Decimal
    post_value: Decimal
```

**performance/metrics.py:**

```python
import pandas as pd
from portfolio_management.analytics import (
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    calculate_max_drawdown,
)
from ..models import PerformanceMetrics

def calculate_performance_metrics(
    equity_curve: pd.DataFrame,
    returns: pd.Series
) -> PerformanceMetrics:
    """Calculate performance metrics from backtest results."""
    total_return = (equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1
    annual_return = (1 + total_return) ** (252 / len(equity_curve)) - 1

    return PerformanceMetrics(
        total_return=total_return,
        annual_return=annual_return,
        sharpe_ratio=calculate_sharpe_ratio(returns),
        sortino_ratio=calculate_sortino_ratio(returns),
        max_drawdown=calculate_max_drawdown(equity_curve),
        # ... other metrics
    )
```

### Dependencies

- core (exceptions)
- portfolio (strategies, Portfolio)
- analytics (metrics)

### Key Changes from Current

- Split 749-line backtest.py into focused modules
- Separate transaction costs, rebalancing, performance
- Clear simulation flow

______________________________________________________________________

## Package 7: reporting (Visualization & Reporting Layer)

### Purpose

Generate visualizations and reports from portfolio and backtest results.

### Public API

```python
# portfolio_management/reporting/__init__.py

from .visualization import (
    prepare_equity_curve,
    prepare_drawdown_series,
    prepare_allocation_history,
    prepare_rolling_metrics,
    prepare_returns_distribution,
    prepare_monthly_returns_heatmap,
)

from .reports import (
    create_summary_report,
    create_comparison_report,
    create_trade_analysis,
)

from .exporters import (
    export_to_csv,
    export_to_json,
    export_to_html,
)

__all__ = [
    # Visualization
    "prepare_equity_curve",
    "prepare_drawdown_series",
    "prepare_allocation_history",
    "prepare_rolling_metrics",
    "prepare_returns_distribution",
    "prepare_monthly_returns_heatmap",
    # Reports
    "create_summary_report",
    "create_comparison_report",
    "create_trade_analysis",
    # Exporters
    "export_to_csv",
    "export_to_json",
    "export_to_html",
]
```

### Internal Structure

```
reporting/
├── __init__.py (public API)
├── visualization/
│   ├── __init__.py
│   ├── equity_curves.py
│   ├── drawdowns.py
│   ├── allocations.py
│   ├── distributions.py
│   └── heatmaps.py
├── reports/
│   ├── __init__.py
│   ├── summary.py
│   ├── comparison.py
│   └── trade_analysis.py
└── exporters/
    ├── __init__.py
    ├── csv.py
    ├── json.py
    └── html.py
```

### Module Split Guidelines

#### visualization.py → Multiple Focused Files

**visualization/equity_curves.py:**

```python
import pandas as pd

def prepare_equity_curve(equity_df: pd.DataFrame) -> pd.DataFrame:
    """Prepare equity curve data for plotting."""
    # ... existing logic from visualization.py
    pass
```

**visualization/drawdowns.py:**

```python
import pandas as pd

def prepare_drawdown_series(equity_df: pd.DataFrame) -> pd.DataFrame:
    """Prepare drawdown series for plotting."""
    # ... existing logic from visualization.py
    pass
```

**visualization/allocations.py:**

```python
import pandas as pd

def prepare_allocation_history(
    allocation_df: pd.DataFrame,
    top_n: int = 10
) -> pd.DataFrame:
    """Prepare allocation history for stacked area chart."""
    # ... existing logic from visualization.py
    pass
```

**reports/summary.py:**

```python
import pandas as pd
from portfolio_management.backtesting import BacktestResult

def create_summary_report(result: BacktestResult) -> dict:
    """Create comprehensive summary report."""
    return {
        "performance": result.metrics,
        "trades": len(result.trades),
        "equity_curve": result.equity_curve,
        # ... other summary data
    }
```

**exporters/csv.py:**

```python
from pathlib import Path
import pandas as pd

def export_to_csv(data: pd.DataFrame, output_path: Path) -> None:
    """Export data to CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(output_path, index=True)
```

**exporters/html.py:**

```python
from pathlib import Path
import pandas as pd

def export_to_html(
    data: dict,
    output_path: Path,
    template: str | None = None
) -> None:
    """Export report to HTML."""
    # ... HTML generation logic
    pass
```

### Dependencies

- core (for utilities)
- backtesting (BacktestResult, PerformanceMetrics)
- portfolio (Portfolio)
- analytics (metrics)

### Key Changes from Current

- Split visualization.py by chart type
- Add report generation capabilities
- Add various export formats

______________________________________________________________________

## Cross-Cutting Concerns

### Logging

**Standard Pattern Across All Packages:**

```python
import logging

logger = logging.getLogger(__name__)

# Usage in modules
logger.debug("Detailed debug info")
logger.info("Important info")
logger.warning("Warning message")
logger.error("Error occurred")
```

### Exception Handling

**Standard Pattern:**

```python
from portfolio_management.core import (
    PortfolioConstructionError,
    DataValidationError,
)

try:
    # ... operation
except ValueError as e:
    raise DataValidationError("Validation failed") from e
except Exception as e:
    raise PortfolioConstructionError("Construction failed") from e
```

### Type Hints

**Standard Pattern:**

```python
from __future__ import annotations

from typing import TYPE_CHECKING
import pandas as pd

if TYPE_CHECKING:
    from pathlib import Path
    from portfolio_management.assets import SelectedAsset

def process_assets(
    assets: list[SelectedAsset],
    output_path: Path
) -> pd.DataFrame:
    """Process assets with type hints."""
    # ... implementation
```

### Testing

**Standard Test Structure:**

```python
# tests/unit/assets/test_selection.py

import pytest
from portfolio_management.assets import FilterCriteria, AssetSelector

class TestFilterCriteria:
    """Tests for FilterCriteria."""

    def test_default_creation(self):
        """Test default criteria creation."""
        criteria = FilterCriteria.default()
        assert criteria.min_history_days == 252

    def test_validation(self):
        """Test criteria validation."""
        criteria = FilterCriteria(min_history_days=-1)
        with pytest.raises(ValueError):
            criteria.validate()

class TestAssetSelector:
    """Tests for AssetSelector."""

    @pytest.fixture
    def selector(self):
        """Create selector instance."""
        return AssetSelector()

    def test_filter_assets(self, selector, sample_assets):
        """Test asset filtering."""
        criteria = FilterCriteria.default()
        result = selector.filter(sample_assets, criteria)
        assert len(result) > 0
```

______________________________________________________________________

## Implementation Checklist

### Per-Package Checklist

For each package, ensure:

- \[ \] `__init__.py` created with public API exports
- \[ \] All modules split appropriately
- \[ \] Internal imports use relative imports
- \[ \] External imports use absolute imports from public APIs
- \[ \] Type hints added
- \[ \] Docstrings updated
- \[ \] Tests migrated and passing
- \[ \] Dependencies documented
- \[ \] Example usage in docstrings

### Global Checklist

- \[ \] All packages follow naming conventions
- \[ \] Dependency rules enforced
- \[ \] No circular dependencies
- \[ \] All tests passing
- \[ \] Coverage maintained
- \[ \] Scripts updated
- \[ \] Documentation updated
- \[ \] Migration guide created

______________________________________________________________________

**Document Prepared By:** GitHub Copilot
**Date:** October 18, 2025
**Related:** MODULAR_MONOLITH_REFACTORING_PLAN.md, ARCHITECTURE_DIAGRAM.md
