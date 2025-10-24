"""Configuration validation and defaults for portfolio management toolkit.

This module provides comprehensive validation for configuration parameters
across all features, detecting invalid combinations, conflicts, and suboptimal
settings with helpful warnings.

Main Components:
    - validate_preselection_config: Validate preselection parameters
    - validate_membership_config: Validate membership policy parameters
    - validate_pit_config: Validate point-in-time eligibility parameters
    - validate_cache_config: Validate caching configuration
    - validate_feature_compatibility: Check for feature conflicts
    - check_optimality_warnings: Identify suboptimal configurations
    - check_dependencies: Verify optional dependencies availability
    - get_sensible_defaults: Retrieve recommended default values

Example:
    >>> from portfolio_management.config import validate_preselection_config
    >>> validate_preselection_config(top_k=30, lookback=252, skip=1)
    >>> # Raises ValidationError if invalid, returns warnings if suboptimal

"""

from portfolio_management.config.validation import (
    ValidationResult,
    ValidationWarning,
    check_dependencies,
    check_optimality_warnings,
    get_sensible_defaults,
    validate_cache_config,
    validate_feature_compatibility,
    validate_membership_config,
    validate_pit_config,
    validate_preselection_config,
)

__all__ = [
    "ValidationResult",
    "ValidationWarning",
    "validate_preselection_config",
    "validate_membership_config",
    "validate_pit_config",
    "validate_cache_config",
    "validate_feature_compatibility",
    "check_optimality_warnings",
    "check_dependencies",
    "get_sensible_defaults",
]
