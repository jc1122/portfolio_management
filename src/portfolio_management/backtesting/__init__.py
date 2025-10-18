"""Backtesting framework for portfolio strategies.

This package provides historical simulation capabilities, including:
- Transaction cost modeling (commissions, slippage, bid-ask spread)
- Rebalancing logic (scheduled, opportunistic, forced)
- Performance metrics calculation (Sharpe, Sortino, drawdown, etc.)
- Portfolio evolution tracking with cash management
"""

# Engine
from .engine import BacktestEngine

# Core models
from .models import (
    BacktestConfig,
    PerformanceMetrics,
    RebalanceEvent,
    RebalanceFrequency,
    RebalanceTrigger,
)

# Performance metrics
from .performance import calculate_metrics

# Transaction costs
from .transactions import TransactionCostModel

__all__ = [
    # Models
    "BacktestConfig",
    "PerformanceMetrics",
    "RebalanceEvent",
    "RebalanceFrequency",
    "RebalanceTrigger",
    # Engine
    "BacktestEngine",
    # Transaction costs
    "TransactionCostModel",
    # Performance
    "calculate_metrics",
]
