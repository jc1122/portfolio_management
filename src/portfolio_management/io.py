"""Data I/O operations.

DEPRECATED: This module has been moved to portfolio_management.data.io.
Import from there instead. This module is maintained for backward compatibility only.
"""

from .data.io.io import (  # noqa: F401
    export_tradeable_prices,
    load_tradeable_instruments,
    read_stooq_index,
    write_match_report,
    write_stooq_index,
    write_unmatched_report,
)

__all__ = [
    "read_stooq_index",
    "write_stooq_index",
    "load_tradeable_instruments",
    "write_unmatched_report",
    "write_match_report",
    "export_tradeable_prices",
]
