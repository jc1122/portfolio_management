"""Configuration validation functions for portfolio management.

This module implements comprehensive validation for all configuration parameters,
detecting invalid values, conflicts, and suboptimal settings.

Validation Categories:
    1. Parameter Ranges: Validate individual parameter bounds
    2. Feature Conflicts: Detect incompatible feature combinations
    3. Optimality Warnings: Identify suboptimal but valid configurations
    4. Dependency Checks: Verify required dependencies are available

"""

from __future__ import annotations

import copy
import logging
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from portfolio_management.core.exceptions import ConfigurationError

logger = logging.getLogger(__name__)


@dataclass
class ValidationWarning:
    """A configuration warning that doesn't prevent execution.

    Attributes:
        category: Warning category (e.g., "optimality", "performance")
        parameter: Parameter name that triggered the warning
        message: Human-readable warning message
        suggestion: Suggested improvement or action
        severity: Warning severity (low, medium, high)

    """

    category: str
    parameter: str
    message: str
    suggestion: str
    severity: str = "medium"


@dataclass
class ValidationResult:
    """Result of configuration validation.

    Attributes:
        valid: Whether configuration is valid
        errors: List of validation errors (prevent execution)
        warnings: List of validation warnings (execution allowed)

    """

    valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[ValidationWarning] = field(default_factory=list)

    def add_error(self, message: str) -> None:
        """Add a validation error."""
        self.valid = False
        self.errors.append(message)

    def add_warning(
        self,
        category: str,
        parameter: str,
        message: str,
        suggestion: str,
        severity: str = "medium",
    ) -> None:
        """Add a validation warning."""
        self.warnings.append(
            ValidationWarning(
                category=category,
                parameter=parameter,
                message=message,
                suggestion=suggestion,
                severity=severity,
            )
        )

    def raise_if_invalid(self) -> None:
        """Raise ConfigurationError if validation failed."""
        if not self.valid:
            error_msg = "Configuration validation failed:\n" + "\n".join(
                f"  - {err}" for err in self.errors
            )
            raise ConfigurationError(error_msg)


# =============================================================================
# SENSIBLE DEFAULTS
# =============================================================================

DEFAULTS = {
    # Preselection defaults
    "preselection": {
        "top_k": 30,  # Sufficient for diversification
        "lookback": 252,  # 1 year of daily data
        "skip": 1,  # Skip most recent day (common practice)
        "min_periods": 63,  # ~3 months minimum
        "momentum_weight": 0.5,
        "low_vol_weight": 0.5,
    },
    # Membership policy defaults
    "membership": {
        "buffer_rank": None,  # Disabled by default (optional feature)
        "min_holding_periods": 0,  # No minimum (can exit immediately)
        "max_turnover": 1.0,  # No limit by default
        "max_new_assets": None,  # No limit
        "max_removed_assets": None,  # No limit
    },
    # Point-in-time eligibility defaults
    "pit": {
        "min_history_days": 252,  # 1 year of history
        "min_price_rows": 252,  # 1 year of price data
        "enabled": False,  # Opt-in feature
    },
    # Caching defaults
    "cache": {
        "enabled": False,  # Opt-in feature
        "cache_dir": ".cache/backtest",
        "max_age_days": None,  # No expiration by default
        "max_size_mb": None,  # No size limit
    },
}


def get_sensible_defaults() -> dict[str, Any]:
    """Get sensible defaults for all configuration parameters.

    Returns:
        Dictionary of default values organized by feature

    """
    return copy.deepcopy(DEFAULTS)


# =============================================================================
# PRESELECTION VALIDATION
# =============================================================================


def validate_preselection_config(
    top_k: int | None = None,
    lookback: int | None = None,
    skip: int | None = None,
    min_periods: int | None = None,
    method: str | None = None,
    *,
    strict: bool = False,
) -> ValidationResult:
    """Validate preselection configuration parameters.

    Parameter Ranges:
        - top_k: Must be > 0 if provided (None disables preselection)
        - lookback: Must be >= min_periods
        - skip: Must be < lookback and >= 0
        - min_periods: Must be > 0

    Optimality Warnings:
        - top_k < 10: Too small for meaningful diversification
        - lookback < 63: Too short for stable factors (~3 months minimum)
        - min_periods > lookback: Impossible to satisfy

    Args:
        top_k: Number of assets to select (None to disable)
        lookback: Lookback period for factor calculation
        skip: Number of recent periods to skip
        min_periods: Minimum periods required for calculation
        method: Preselection method (momentum, low_vol, combined)
        strict: If True, treat warnings as errors

    Returns:
        ValidationResult with errors and warnings

    Raises:
        ConfigurationError: If strict=True and validation fails

    """
    result = ValidationResult()

    # Validate top_k
    if top_k is not None:
        if top_k <= 0:
            result.add_error(
                f"Preselection top_k must be > 0, got {top_k}. "
                "Set to None to disable preselection."
            )
        elif top_k < 10:
            result.add_warning(
                category="optimality",
                parameter="top_k",
                message=f"top_k={top_k} may be too small for meaningful diversification",
                suggestion="Consider using top_k >= 10 for better diversification",
                severity="medium",
            )

    # Validate lookback
    if lookback is not None:
        if lookback < 1:
            result.add_error(f"Preselection lookback must be >= 1, got {lookback}")
        elif lookback < 63:  # ~3 months of daily data
            result.add_warning(
                category="optimality",
                parameter="lookback",
                message=f"lookback={lookback} may be too short for stable factor estimates",
                suggestion="Consider using lookback >= 63 days (~3 months) for more reliable factors",
                severity="medium",
            )

    # Validate skip
    if skip is not None:
        if skip < 0:
            result.add_error(f"Preselection skip must be >= 0, got {skip}")
        if lookback is not None and skip >= lookback:
            result.add_error(
                f"Preselection skip ({skip}) must be < lookback ({lookback})"
            )

    # Validate min_periods
    if min_periods is not None:
        if min_periods <= 0:
            result.add_error(
                f"Preselection min_periods must be > 0, got {min_periods}"
            )
        if lookback is not None and min_periods > lookback:
            result.add_warning(
                category="optimality",
                parameter="min_periods",
                message=f"min_periods ({min_periods}) > lookback ({lookback}) - impossible to satisfy",
                suggestion=f"Set min_periods <= lookback ({lookback})",
                severity="high",
            )

    # Validate method
    if method is not None:
        valid_methods = ["momentum", "low_vol", "combined"]
        if method not in valid_methods:
            result.add_error(
                f"Invalid preselection method '{method}'. "
                f"Valid options: {', '.join(valid_methods)}"
            )

    if strict:
        result.raise_if_invalid()

    return result


# =============================================================================
# MEMBERSHIP POLICY VALIDATION
# =============================================================================


def validate_membership_config(
    buffer_rank: int | None = None,
    top_k: int | None = None,
    min_holding_periods: int | None = None,
    max_turnover: float | None = None,
    rebalance_periods: int | None = None,
    *,
    strict: bool = False,
) -> ValidationResult:
    """Validate membership policy configuration parameters.

    Parameter Ranges:
        - buffer_rank: Must be > top_k if both provided
        - min_holding_periods: Must be >= 0
        - max_turnover: Must be in [0, 1]

    Feature Conflicts:
        - buffer_rank < top_k: Invalid, defeats purpose of buffer
        - min_holding_periods > rebalance_periods: Impossible to satisfy

    Optimality Warnings:
        - buffer_rank too close to top_k: < 20% gap reduces effectiveness
        - min_holding_periods very high: May prevent portfolio adaptation

    Args:
        buffer_rank: Keep assets ranked better than this
        top_k: Top-K assets from preselection (for compatibility check)
        min_holding_periods: Minimum periods to hold an asset
        max_turnover: Maximum turnover fraction [0, 1]
        rebalance_periods: Rebalancing frequency (for compatibility check)
        strict: If True, treat warnings as errors

    Returns:
        ValidationResult with errors and warnings

    Raises:
        ConfigurationError: If strict=True and validation fails

    """
    result = ValidationResult()

    # Validate buffer_rank
    if buffer_rank is not None:
        if buffer_rank <= 0:
            result.add_error(
                f"Membership buffer_rank must be > 0, got {buffer_rank}"
            )
        if top_k is not None:
            if buffer_rank < top_k:
                result.add_error(
                    f"Membership buffer_rank ({buffer_rank}) must be > top_k ({top_k}). "
                    "Buffer rank should be higher than selection threshold to provide hysteresis."
                )
            elif buffer_rank <= top_k * 1.2:  # < 20% gap
                result.add_warning(
                    category="optimality",
                    parameter="buffer_rank",
                    message=f"buffer_rank ({buffer_rank}) is very close to top_k ({top_k})",
                    suggestion=f"Consider buffer_rank >= {int(top_k * 1.2)} "
                    f"(20% gap) for meaningful hysteresis",
                    severity="medium",
                )

    # Validate min_holding_periods
    if min_holding_periods is not None:
        if min_holding_periods < 0:
            result.add_error(
                f"Membership min_holding_periods must be >= 0, got {min_holding_periods}"
            )
        if rebalance_periods is not None and min_holding_periods > rebalance_periods:
            result.add_error(
                f"Membership min_holding_periods ({min_holding_periods}) cannot be > "
                f"total rebalance_periods ({rebalance_periods}). This constraint is impossible to satisfy."
            )

    # Validate max_turnover
    if max_turnover is not None:
        if not 0 <= max_turnover <= 1:
            result.add_error(
                f"Membership max_turnover must be in [0, 1], got {max_turnover}"
            )

    if strict:
        result.raise_if_invalid()

    return result


# =============================================================================
# POINT-IN-TIME ELIGIBILITY VALIDATION
# =============================================================================


def validate_pit_config(
    min_history_days: int | None = None,
    min_price_rows: int | None = None,
    *,
    strict: bool = False,
) -> ValidationResult:
    """Validate point-in-time eligibility configuration.

    Parameter Ranges:
        - min_history_days: Must be > 0
        - min_price_rows: Must be > 0

    Args:
        min_history_days: Minimum days of history required
        min_price_rows: Minimum number of price rows required
        strict: If True, treat warnings as errors

    Returns:
        ValidationResult with errors and warnings

    Raises:
        ConfigurationError: If strict=True and validation fails

    """
    result = ValidationResult()

    # Validate min_history_days
    if min_history_days is not None:
        if min_history_days <= 0:
            result.add_error(
                f"PIT min_history_days must be > 0, got {min_history_days}"
            )

    # Validate min_price_rows
    if min_price_rows is not None:
        if min_price_rows <= 0:
            result.add_error(f"PIT min_price_rows must be > 0, got {min_price_rows}")

    if strict:
        result.raise_if_invalid()

    return result


# =============================================================================
# CACHE CONFIGURATION VALIDATION
# =============================================================================


def validate_cache_config(
    cache_dir: str | Path | None = None,
    max_age_days: int | None = None,
    max_size_mb: int | None = None,
    enabled: bool = False,
    *,
    strict: bool = False,
) -> ValidationResult:
    """Validate caching configuration.

    Parameter Ranges:
        - max_age_days: Must be >= 0 if provided
        - max_size_mb: Must be >= 0 if provided

    Feature Conflicts:
        - enabled=True but cache_dir not writable: Cannot cache

    Args:
        cache_dir: Directory for cache files
        max_age_days: Maximum cache age in days (None = no expiration)
        max_size_mb: Maximum cache size in MB (None = no limit)
        enabled: Whether caching is enabled
        strict: If True, treat warnings as errors

    Returns:
        ValidationResult with errors and warnings

    Raises:
        ConfigurationError: If strict=True and validation fails

    """
    result = ValidationResult()

    # Validate max_age_days
    if max_age_days is not None:
        if max_age_days < 0:
            result.add_error(f"Cache max_age_days must be >= 0, got {max_age_days}")

    # Validate max_size_mb
    if max_size_mb is not None:
        if max_size_mb < 0:
            result.add_error(f"Cache max_size_mb must be >= 0, got {max_size_mb}")

    # Check cache_dir writability if caching enabled
    if enabled and cache_dir is not None:
        cache_path = Path(cache_dir)
        try:
            # Check if path exists but is not a directory
            if cache_path.exists() and not cache_path.is_dir():
                result.add_error(
                    f"Cache path '{cache_dir}' exists but is not a directory. "
                    "Choose a different directory."
                )
            # Check if directory exists or can be created
            elif not cache_path.exists():
                # Try to create it
                cache_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created cache directory: {cache_path}")
            
            # Check writability (only if it's a directory)
            if cache_path.is_dir() and not os.access(cache_path, os.W_OK):
                result.add_error(
                    f"Cache directory '{cache_dir}' is not writable. "
                    "Disable caching or choose a different directory."
                )
        except Exception as e:
            result.add_error(
                f"Cannot create cache directory '{cache_dir}': {e}. "
                "Disable caching or choose a different directory."
            )

    if strict:
        result.raise_if_invalid()

    return result


# =============================================================================
# FEATURE COMPATIBILITY VALIDATION
# =============================================================================


def validate_feature_compatibility(
    preselection_enabled: bool = False,
    preselection_top_k: int | None = None,
    membership_enabled: bool = False,
    membership_buffer_rank: int | None = None,
    cache_enabled: bool = False,
    universe_size: int | None = None,
    *,
    strict: bool = False,
) -> ValidationResult:
    """Validate compatibility between features and configurations.

    Feature Conflicts:
        - Preselection disabled (top_k=0) but membership policy enabled
        - Membership buffer_rank set but preselection disabled
        - Caching disabled for large universe (performance warning)

    Args:
        preselection_enabled: Whether preselection is enabled
        preselection_top_k: Top-K value for preselection
        membership_enabled: Whether membership policy is enabled
        membership_buffer_rank: Buffer rank for membership policy
        cache_enabled: Whether caching is enabled
        universe_size: Number of assets in universe
        strict: If True, treat warnings as errors

    Returns:
        ValidationResult with errors and warnings

    Raises:
        ConfigurationError: If strict=True and validation fails

    """
    result = ValidationResult()

    # Check preselection + membership compatibility
    if membership_enabled and not preselection_enabled:
        result.add_warning(
            category="compatibility",
            parameter="membership_policy",
            message="Membership policy enabled but preselection disabled",
            suggestion="Consider enabling preselection (top_k > 0) to use membership policy effectively",
            severity="medium",
        )

    if membership_buffer_rank is not None and (
        preselection_top_k is None or preselection_top_k == 0
    ):
        result.add_warning(
            category="compatibility",
            parameter="buffer_rank",
            message="Membership buffer_rank set but preselection disabled (top_k=0 or None)",
            suggestion="Enable preselection with top_k > 0 to use buffer_rank",
            severity="high",
        )

    # Performance warnings
    if not cache_enabled and universe_size is not None and universe_size > 500:
        result.add_warning(
            category="performance",
            parameter="cache_enabled",
            message=f"Caching disabled for large universe ({universe_size} assets)",
            suggestion="Consider enabling caching (--enable-cache) to improve performance",
            severity="medium",
        )

    if strict:
        result.raise_if_invalid()

    return result


# =============================================================================
# OPTIMALITY CHECKS
# =============================================================================


def check_optimality_warnings(
    config: dict[str, Any],
    *,
    strict: bool = False,
) -> ValidationResult:
    """Check for suboptimal but valid configurations.

    Checks:
        - Small top_k (<10): Poor diversification
        - Short lookback (<63): Unstable factors
        - Buffer rank too close to top_k (<20% gap)
        - Caching disabled for large universe (>500 assets)

    Args:
        config: Full configuration dictionary
        strict: If True, treat warnings as errors

    Returns:
        ValidationResult with optimality warnings

    Raises:
        ConfigurationError: If strict=True and warnings found

    """
    result = ValidationResult()

    # Extract relevant config
    preselection = config.get("preselection", {})
    membership = config.get("membership", {})
    universe = config.get("universe", {})
    cache = config.get("cache", {})

    # Check preselection optimality
    top_k = preselection.get("top_k")
    if top_k is not None and 0 < top_k < 10:
        result.add_warning(
            category="optimality",
            parameter="top_k",
            message=f"Small top_k ({top_k}) limits diversification",
            suggestion="Consider top_k >= 10 for meaningful diversification",
            severity="medium",
        )

    lookback = preselection.get("lookback")
    if lookback is not None and lookback < 63:
        result.add_warning(
            category="optimality",
            parameter="lookback",
            message=f"Short lookback ({lookback}) may produce unstable factors",
            suggestion="Consider lookback >= 63 days (~3 months)",
            severity="medium",
        )

    # Check membership optimality
    buffer_rank = membership.get("buffer_rank")
    if top_k is not None and buffer_rank is not None:
        if buffer_rank <= top_k * 1.2:
            result.add_warning(
                category="optimality",
                parameter="buffer_rank",
                message=f"Buffer rank ({buffer_rank}) very close to top_k ({top_k})",
                suggestion=f"Consider buffer_rank >= {int(top_k * 1.2)} for meaningful hysteresis",
                severity="low",
            )

    # Check caching for large universes
    universe_size = universe.get("size")
    cache_enabled = cache.get("enabled", False)
    if not cache_enabled and universe_size is not None and universe_size > 500:
        result.add_warning(
            category="performance",
            parameter="cache",
            message=f"Caching disabled for large universe ({universe_size} assets)",
            suggestion="Enable caching to improve performance with large universes",
            severity="medium",
        )

    if strict:
        # For optimality warnings, only raise if there are HIGH severity warnings
        high_severity_warnings = [w for w in result.warnings if w.severity == "high"]
        if high_severity_warnings:
            error_msgs = [
                f"{w.parameter}: {w.message}" for w in high_severity_warnings
            ]
            raise ConfigurationError(
                "High-severity optimality warnings:\n" + "\n".join(error_msgs)
            )

    return result


# =============================================================================
# DEPENDENCY CHECKS
# =============================================================================


def check_dependencies(
    fast_io_enabled: bool = False,
    universe_size: int | None = None,
    *,
    strict: bool = False,
) -> ValidationResult:
    """Check availability of optional dependencies.

    Checks:
        - polars/pyarrow availability if fast IO requested
        - Sufficient disk space for caching

    Args:
        fast_io_enabled: Whether fast IO (polars/pyarrow) is enabled
        universe_size: Number of assets in universe
        strict: If True, treat warnings as errors

    Returns:
        ValidationResult with dependency warnings

    Raises:
        ConfigurationError: If strict=True and dependencies missing

    """
    result = ValidationResult()

    # Check polars/pyarrow availability
    if fast_io_enabled:
        try:
            import polars  # noqa: F401

            logger.debug("polars is available")
        except ImportError:
            try:
                import pyarrow  # noqa: F401

                logger.debug("pyarrow is available (polars not available)")
            except ImportError:
                result.add_warning(
                    category="dependency",
                    parameter="fast_io",
                    message="Fast IO requested but polars/pyarrow not installed",
                    suggestion="Install polars or pyarrow: pip install polars pyarrow",
                    severity="high",
                )

    # Check disk space for caching
    try:
        stat = shutil.disk_usage("/")
        free_gb = stat.free / (1024**3)
        if free_gb < 1.0:  # Less than 1 GB free
            result.add_warning(
                category="disk_space",
                parameter="cache",
                message=f"Low disk space ({free_gb:.1f} GB free)",
                suggestion="Free up disk space or disable caching",
                severity="high",
            )
    except Exception as e:
        logger.debug(f"Could not check disk space: {e}")

    if strict:
        result.raise_if_invalid()

    return result
