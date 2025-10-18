"""Universe management.

DEPRECATED: This module has been moved to portfolio_management.assets.universes.
Import from there instead. This module is maintained for backward compatibility only.
"""

from .assets.universes.universes import (  # noqa: F401
    UniverseConfigLoader,
    UniverseDefinition,
    UniverseManager,
)

__all__ = ["UniverseDefinition", "UniverseConfigLoader", "UniverseManager"]
