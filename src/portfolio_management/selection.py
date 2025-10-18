"""Asset selection and filtering.

DEPRECATED: This module has been moved to portfolio_management.assets.selection.
Import from there instead. This module is maintained for backward compatibility only.
"""

from .assets.selection.selection import (  # noqa: F401
    AssetSelector,
    FilterCriteria,
    SelectedAsset,
)

__all__ = ["FilterCriteria", "SelectedAsset", "AssetSelector"]
