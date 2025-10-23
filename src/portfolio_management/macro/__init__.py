"""Macroeconomic signal provider and regime gating.

This module provides infrastructure for loading macroeconomic time series
from Stooq data directories and defining regime configurations that can
gate asset selection decisions.

Key components:
- MacroSeries: Data model for a single macro time series
- RegimeConfig: Configuration for regime detection rules
- MacroSignalProvider: Loads selected macro series from local Stooq paths
- RegimeGate: Applies regime rules to modify selection (currently NoOp)

Example:
    >>> from portfolio_management.macro import MacroSignalProvider, RegimeConfig, RegimeGate
    >>> provider = MacroSignalProvider(data_dir="data/stooq")
    >>> series = provider.locate_series("gdp.us")
    >>> config = RegimeConfig(recession_indicator=None)  # NoOp stub
    >>> gate = RegimeGate(config)
    >>> # Regime gating currently does nothing (neutral/pass-through)
    >>> regime = gate.get_current_regime()
    >>> print(regime)  # {'recession': 'neutral', 'risk_sentiment': 'neutral', 'mode': 'noop'}

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
