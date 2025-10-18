"""Configuration for the portfolio management toolkit.

DEPRECATED: This module has been moved to portfolio_management.core.config.
Import from there instead. This module is maintained for backward compatibility only.
"""

# Backward compatibility - re-export all config from core
from .core.config import (  # noqa: F401
    LEGACY_PREFIXES,
    REGION_CURRENCY_MAP,
    STOOQ_COLUMNS,
    STOOQ_PANDAS_COLUMNS,
    SYMBOL_ALIAS_MAP,
)

__all__ = [
    "REGION_CURRENCY_MAP",
    "LEGACY_PREFIXES",
    "SYMBOL_ALIAS_MAP",
    "STOOQ_COLUMNS",
    "STOOQ_PANDAS_COLUMNS",
]
