"""Type aliases and type definitions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeAlias

if TYPE_CHECKING:
    import pandas as pd

# DataFrame type aliases
PriceFrame: TypeAlias = "pd.DataFrame"  # Columns: Date, Symbol, Close, Volume
ReturnFrame: TypeAlias = "pd.DataFrame"  # Index: Date, Columns: Asset tickers
WeightFrame: TypeAlias = "pd.DataFrame"  # Index: Date, Columns: Asset tickers

# Series type aliases
ReturnSeries: TypeAlias = "pd.Series[float]"  # Index: Date, values: returns
PriceSeries: TypeAlias = "pd.Series[float]"  # Index: Date, values: prices
DateSeries: TypeAlias = "pd.Series[pd.Timestamp]"  # Index: int, values: dates

# Weight dictionaries
WeightDict: TypeAlias = dict[str, float]  # Asset ticker -> weight (sum to 1.0)
ConstraintDict: TypeAlias = dict[str, tuple[float, float]]  # Asset -> (min, max)

# Asset collections
AssetList: TypeAlias = list[str]  # List of asset tickers
AssetSet: TypeAlias = set[str]  # Set of asset tickers

# Configuration types
UniverseConfig: TypeAlias = dict[str, Any]  # Universe YAML configuration
StrategyConfig: TypeAlias = dict[str, Any]  # Strategy configuration

# Result types
BacktestMetrics: TypeAlias = dict[str, float]  # Metric name -> value
DiagnosticFlags: TypeAlias = dict[str, int]  # Flag name -> count