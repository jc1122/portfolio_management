"""Backtesting framework for portfolio strategies.

This package provides historical simulation capabilities, including:
- Transaction cost modeling (commissions, slippage, bid-ask spread)
- Rebalancing logic (scheduled, opportunistic, forced)
- Performance metrics calculation (Sharpe, Sortino, drawdown, etc.)
- Portfolio evolution tracking with cash management
- Point-in-time eligibility filtering to avoid look-ahead bias
"""

# Eligibility
from .eligibility import (
    compute_pit_eligibility,
    detect_delistings,
    get_asset_history_stats,
)

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
    # Eligibility
    "compute_pit_eligibility",
    "detect_delistings",
    "get_asset_history_stats",
]
