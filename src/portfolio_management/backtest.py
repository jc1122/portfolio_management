"""Backtesting framework for portfolio strategies.

BACKWARD COMPATIBILITY SHIM:
This module now imports from the new backtesting package structure.
For new code, please use: from portfolio_management.backtesting import ...

This module provides historical simulation capabilities, including:
- Transaction cost modeling (commissions, slippage, bid-ask spread)
- Rebalancing logic (scheduled, opportunistic, forced)
- Performance metrics calculation (Sharpe, Sortino, drawdown, etc.)
- Portfolio evolution tracking with cash management
"""

from __future__ import annotations

# Import everything from the new modular structure for backward compatibility
from portfolio_management.backtesting import (
    BacktestConfig,
    BacktestEngine,
    PerformanceMetrics,
    RebalanceEvent,
    RebalanceFrequency,
    RebalanceTrigger,
    TransactionCostModel,
    calculate_metrics,
)

__all__ = [
    "BacktestConfig",
    "BacktestEngine",
    "PerformanceMetrics",
    "RebalanceEvent",
    "RebalanceFrequency",
    "RebalanceTrigger",
    "TransactionCostModel",
    "calculate_metrics",
]
