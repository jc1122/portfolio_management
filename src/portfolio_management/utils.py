"""Shared utilities for parallel execution and performance monitoring.

DEPRECATED: This module has been moved to portfolio_management.core.utils.
Import from there instead. This module is maintained for backward compatibility only.
"""

# Backward compatibility - re-export all utils from core
from .core.utils import (  # noqa: F401
    _run_in_parallel,
    log_duration,
)

__all__ = [
    "_run_in_parallel",
    "log_duration",
]
