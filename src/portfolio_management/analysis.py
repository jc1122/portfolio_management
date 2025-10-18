"""Data quality analysis.

DEPRECATED: This module has been moved to portfolio_management.data.analysis.
Import from there instead. This module is maintained for backward compatibility only.
"""

from .data.analysis.analysis import (  # noqa: F401
    collect_available_extensions,
    infer_currency,
    log_summary_counts,
    resolve_currency,
    summarize_price_file,
)

__all__ = [
    "summarize_price_file",
    "infer_currency",
    "resolve_currency",
    "collect_available_extensions",
    "log_summary_counts",
]
