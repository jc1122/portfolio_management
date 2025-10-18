"""Symbol matching.

DEPRECATED: This module has been moved to portfolio_management.data.matching.
Import from there instead. This module is maintained for backward compatibility only.
"""

from .data.matching.matchers import (  # noqa: F401
    annotate_unmatched_instruments,
    build_stooq_lookup,
    determine_unmatched_reason,
    match_tradeables,
)

__all__ = [
    "match_tradeables",
    "build_stooq_lookup",
    "annotate_unmatched_instruments",
    "determine_unmatched_reason",
]
