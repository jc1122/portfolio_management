"""Asset universe management layer.

This package provides:
- Asset selection and filtering criteria
- Asset classification taxonomy
- Universe management and loading

Public API:
    Selection:
        - FilterCriteria, SelectedAsset, AssetSelector
    
    Classification:
        - AssetClass, Geography, SubClass
        - AssetClassification, AssetClassifier
        - ClassificationOverrides
    
    Universes:
        - UniverseDefinition, UniverseConfigLoader
"""

# Selection
from .selection import AssetSelector, FilterCriteria, SelectedAsset

# Classification
from .classification import (
    AssetClass,
    AssetClassification,
    AssetClassifier,
    ClassificationOverrides,
    Geography,
    SubClass,
)

# Universes
from .universes import UniverseConfigLoader, UniverseDefinition, UniverseManager

__all__ = [
    # Selection
    "FilterCriteria",
    "SelectedAsset",
    "AssetSelector",
    # Classification
    "AssetClass",
    "Geography",
    "SubClass",
    "AssetClassification",
    "AssetClassifier",
    "ClassificationOverrides",
    # Universes
    "UniverseDefinition",
    "UniverseConfigLoader",
    "UniverseManager",
]
