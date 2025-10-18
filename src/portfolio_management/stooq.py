"""Stooq data indexing.

DEPRECATED: This module has been moved to portfolio_management.data.ingestion.stooq.
Import from there instead. This module is maintained for backward compatibility only.
"""

from .data.ingestion.stooq import (  # noqa: F401
    build_stooq_index,
    derive_region_and_category,
)

__all__ = ["build_stooq_index", "derive_region_and_category"]
