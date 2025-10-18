"""Domain models and dataclasses.

DEPRECATED: This module has been moved to portfolio_management.data.models.
Import from there instead. This module is maintained for backward compatibility only.
"""

# Backward compatibility - re-export from data package
from .data.models import (  # noqa: F401
    ExportConfig,
    StooqFile,
    TradeableInstrument,
    TradeableMatch,
)

__all__ = [
    "StooqFile",
    "TradeableInstrument",
    "TradeableMatch",
    "ExportConfig",
]
