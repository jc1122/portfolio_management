"""Macroeconomic signal provider and regime gating.

This package provides infrastructure for loading macroeconomic time series
and defining regime configurations that can gate asset selection decisions.
The current implementation uses local Stooq data files and features a NoOp
regime gate that serves as a placeholder for future logic.

Key Classes:
- `MacroSignalProvider`: Locates and loads macro series from a local Stooq
  data directory.
- `RegimeGate`: A NoOp class that applies placeholder regime gating rules to
  an asset selection. It always returns neutral signals.
- `MacroSeries`: A data model for a single macro time series.
- `RegimeConfig`: Configuration for regime detection rules.

Usage Example:
    >>> from portfolio_management.macro import RegimeConfig, RegimeGate
    >>>
    >>> # The RegimeGate is a NoOp and always returns a neutral regime.
    >>> config = RegimeConfig(enable_gating=True)
    >>> gate = RegimeGate(config)
    >>> current_regime = gate.get_current_regime()
    >>> print(current_regime)
    {'recession': 'neutral', 'risk_sentiment': 'neutral', 'mode': 'noop'}

Data Sources:
- This module is designed to work with local data files downloaded from
  Stooq (https://stooq.com/). It expects a directory structure where
  macroeconomic data is organized, typically by region and category.

"""

from portfolio_management.macro.models import MacroSeries, RegimeConfig
from portfolio_management.macro.provider import MacroSignalProvider
from portfolio_management.macro.regime import RegimeGate

__all__ = [
    "MacroSeries",
    "RegimeConfig",
    "MacroSignalProvider",
    "RegimeGate",
]
