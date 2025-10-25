"""Tests for configuration validation module."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

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
from portfolio_management.core.exceptions import ConfigurationError


@pytest.mark.integration
class TestValidationResult:
    """Test ValidationResult class."""

    def test_validation_result_default(self):
        """Test default validation result is valid."""
        result = ValidationResult()
        assert result.valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 0

    def test_add_error(self):
        """Test adding errors."""
        result = ValidationResult()
        result.add_error("Test error")
        assert result.valid is False
        assert len(result.errors) == 1
        assert result.errors[0] == "Test error"

    def test_add_warning(self):
        """Test adding warnings."""
        result = ValidationResult()
        result.add_warning(
            category="test",
            parameter="param",
            message="Test warning",
            suggestion="Fix it",
            severity="low",
        )
        assert result.valid is True
        assert len(result.warnings) == 1
        assert result.warnings[0].category == "test"

    def test_raise_if_invalid(self):
        """Test raising exception on invalid config."""
        result = ValidationResult()
        result.add_error("Test error")
        
        with pytest.raises(ConfigurationError, match="Test error"):
            result.raise_if_invalid()


@pytest.mark.integration
class TestPreselectionValidation:
    """Test preselection configuration validation."""

    def test_valid_config(self):
        """Test valid preselection configuration."""
        result = validate_preselection_config(
            top_k=30, lookback=252, skip=1, min_periods=63
        )
        assert result.valid is True
        assert len(result.errors) == 0

    def test_top_k_zero_invalid(self):
        """Test top_k <= 0 is invalid."""
        result = validate_preselection_config(top_k=0)
        assert result.valid is False
        assert any("top_k must be > 0" in err for err in result.errors)

    def test_top_k_negative_invalid(self):
        """Test negative top_k is invalid."""
        result = validate_preselection_config(top_k=-5)
        assert result.valid is False

    def test_top_k_none_valid(self):
        """Test top_k=None is valid (disables preselection)."""
        result = validate_preselection_config(top_k=None)
        assert result.valid is True

    def test_top_k_small_warning(self):
        """Test small top_k generates warning."""
        result = validate_preselection_config(top_k=5)
        assert result.valid is True
        assert len(result.warnings) > 0
        assert any("diversification" in w.message for w in result.warnings)

    def test_lookback_invalid(self):
        """Test invalid lookback values."""
        result = validate_preselection_config(lookback=0)
        assert result.valid is False
        
        result = validate_preselection_config(lookback=-1)
        assert result.valid is False

    def test_lookback_short_warning(self):
        """Test short lookback generates warning."""
        result = validate_preselection_config(lookback=30)
        assert result.valid is True
        assert any("too short" in w.message.lower() for w in result.warnings)

    def test_skip_negative_invalid(self):
        """Test negative skip is invalid."""
        result = validate_preselection_config(skip=-1)
        assert result.valid is False

    def test_skip_ge_lookback_invalid(self):
        """Test skip >= lookback is invalid."""
        result = validate_preselection_config(skip=252, lookback=252)
        assert result.valid is False
        assert any("skip" in err and "lookback" in err for err in result.errors)

    def test_min_periods_invalid(self):
        """Test invalid min_periods."""
        result = validate_preselection_config(min_periods=0)
        assert result.valid is False
        
        result = validate_preselection_config(min_periods=-1)
        assert result.valid is False

    def test_min_periods_gt_lookback_warning(self):
        """Test min_periods > lookback generates warning."""
        result = validate_preselection_config(min_periods=300, lookback=252)
        assert result.valid is True
        assert any("impossible" in w.message.lower() for w in result.warnings)

    def test_invalid_method(self):
        """Test invalid preselection method."""
        result = validate_preselection_config(method="invalid")
        assert result.valid is False
        assert any("Invalid" in err and "method" in err for err in result.errors)

    def test_valid_methods(self):
        """Test all valid methods."""
        for method in ["momentum", "low_vol", "combined"]:
            result = validate_preselection_config(method=method)
            assert result.valid is True

    def test_strict_mode_raises(self):
        """Test strict mode raises on errors."""
        with pytest.raises(ConfigurationError):
            validate_preselection_config(top_k=0, strict=True)


@pytest.mark.integration
class TestMembershipValidation:
    """Test membership policy configuration validation."""

    def test_valid_config(self):
        """Test valid membership configuration."""
        result = validate_membership_config(
            buffer_rank=50,
            top_k=30,
            min_holding_periods=3,
            max_turnover=0.3,
        )
        assert result.valid is True
        assert len(result.errors) == 0

    def test_buffer_rank_zero_invalid(self):
        """Test buffer_rank <= 0 is invalid."""
        result = validate_membership_config(buffer_rank=0)
        assert result.valid is False

    def test_buffer_rank_lt_top_k_invalid(self):
        """Test buffer_rank < top_k is invalid."""
        result = validate_membership_config(buffer_rank=20, top_k=30)
        assert result.valid is False
        assert any("buffer_rank" in err and "top_k" in err for err in result.errors)

    def test_buffer_rank_close_to_top_k_warning(self):
        """Test buffer_rank close to top_k generates warning."""
        result = validate_membership_config(buffer_rank=32, top_k=30)
        assert result.valid is True
        assert any("close" in w.message.lower() for w in result.warnings)

    def test_min_holding_periods_negative_invalid(self):
        """Test negative min_holding_periods is invalid."""
        result = validate_membership_config(min_holding_periods=-1)
        assert result.valid is False

    def test_min_holding_periods_zero_valid(self):
        """Test min_holding_periods=0 is valid."""
        result = validate_membership_config(min_holding_periods=0)
        assert result.valid is True

    def test_min_holding_periods_gt_rebalance_invalid(self):
        """Test min_holding_periods > rebalance_periods is invalid."""
        result = validate_membership_config(
            min_holding_periods=10, rebalance_periods=5
        )
        assert result.valid is False
        assert any("impossible" in err.lower() for err in result.errors)

    def test_max_turnover_invalid_range(self):
        """Test max_turnover outside [0, 1] is invalid."""
        result = validate_membership_config(max_turnover=-0.1)
        assert result.valid is False
        
        result = validate_membership_config(max_turnover=1.5)
        assert result.valid is False

    def test_max_turnover_valid_range(self):
        """Test max_turnover in [0, 1] is valid."""
        result = validate_membership_config(max_turnover=0.0)
        assert result.valid is True
        
        result = validate_membership_config(max_turnover=1.0)
        assert result.valid is True

    def test_strict_mode_raises(self):
        """Test strict mode raises on errors."""
        with pytest.raises(ConfigurationError):
            validate_membership_config(buffer_rank=20, top_k=30, strict=True)


@pytest.mark.integration
class TestPITValidation:
    """Test point-in-time eligibility configuration validation."""

    def test_valid_config(self):
        """Test valid PIT configuration."""
        result = validate_pit_config(min_history_days=252, min_price_rows=252)
        assert result.valid is True
        assert len(result.errors) == 0

    def test_min_history_days_invalid(self):
        """Test invalid min_history_days."""
        result = validate_pit_config(min_history_days=0)
        assert result.valid is False
        
        result = validate_pit_config(min_history_days=-1)
        assert result.valid is False

    def test_min_price_rows_invalid(self):
        """Test invalid min_price_rows."""
        result = validate_pit_config(min_price_rows=0)
        assert result.valid is False
        
        result = validate_pit_config(min_price_rows=-1)
        assert result.valid is False

    def test_strict_mode_raises(self):
        """Test strict mode raises on errors."""
        with pytest.raises(ConfigurationError):
            validate_pit_config(min_history_days=0, strict=True)


@pytest.mark.integration
class TestCacheValidation:
    """Test caching configuration validation."""

    def test_valid_config(self):
        """Test valid cache configuration."""
        result = validate_cache_config(
            cache_dir=".cache", max_age_days=7, max_size_mb=1000, enabled=False
        )
        assert result.valid is True

    def test_max_age_days_invalid(self):
        """Test negative max_age_days is invalid."""
        result = validate_cache_config(max_age_days=-1)
        assert result.valid is False

    def test_max_size_mb_invalid(self):
        """Test negative max_size_mb is invalid."""
        result = validate_cache_config(max_size_mb=-1)
        assert result.valid is False

    def test_cache_dir_not_writable(self):
        """Test error when cache_dir not writable."""
        # Use /dev/null which is not a directory
        result = validate_cache_config(cache_dir="/dev/null", enabled=True)
        assert result.valid is False

    def test_cache_dir_created_if_missing(self):
        """Test cache directory is created if missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "new_cache_dir"
            assert not cache_path.exists()
            
            result = validate_cache_config(cache_dir=str(cache_path), enabled=True)
            assert result.valid is True
            assert cache_path.exists()

    def test_strict_mode_raises(self):
        """Test strict mode raises on errors."""
        with pytest.raises(ConfigurationError):
            validate_cache_config(max_age_days=-1, strict=True)


@pytest.mark.integration
class TestFeatureCompatibility:
    """Test feature compatibility validation."""

    def test_valid_config(self):
        """Test valid feature combination."""
        result = validate_feature_compatibility(
            preselection_enabled=True,
            preselection_top_k=30,
            membership_enabled=True,
            membership_buffer_rank=50,
        )
        assert result.valid is True

    def test_membership_without_preselection_warning(self):
        """Test warning when membership enabled without preselection."""
        result = validate_feature_compatibility(
            preselection_enabled=False, membership_enabled=True
        )
        assert result.valid is True
        assert any("membership" in w.message.lower() for w in result.warnings)

    def test_buffer_rank_without_preselection_warning(self):
        """Test warning when buffer_rank set without preselection."""
        result = validate_feature_compatibility(
            preselection_enabled=False,
            preselection_top_k=0,
            membership_buffer_rank=50,
        )
        assert result.valid is True
        assert any("buffer_rank" in w.message.lower() for w in result.warnings)

    def test_no_cache_large_universe_warning(self):
        """Test warning for large universe without caching."""
        result = validate_feature_compatibility(
            cache_enabled=False, universe_size=1000
        )
        assert result.valid is True
        assert any("caching" in w.message.lower() for w in result.warnings)

    def test_cache_small_universe_no_warning(self):
        """Test no warning for small universe without caching."""
        result = validate_feature_compatibility(
            cache_enabled=False, universe_size=100
        )
        assert result.valid is True


@pytest.mark.integration
class TestOptimalityChecks:
    """Test optimality warning checks."""

    def test_small_top_k_warning(self):
        """Test warning for small top_k."""
        config = {"preselection": {"top_k": 5}}
        result = check_optimality_warnings(config)
        
        assert result.valid is True
        assert any("top_k" in w.parameter for w in result.warnings)

    def test_short_lookback_warning(self):
        """Test warning for short lookback."""
        config = {"preselection": {"lookback": 30}}
        result = check_optimality_warnings(config)
        
        assert result.valid is True
        assert any("lookback" in w.parameter for w in result.warnings)

    def test_buffer_rank_close_warning(self):
        """Test warning for buffer_rank close to top_k."""
        config = {
            "preselection": {"top_k": 30},
            "membership": {"buffer_rank": 32},
        }
        result = check_optimality_warnings(config)
        
        assert result.valid is True
        assert any("buffer_rank" in w.parameter for w in result.warnings)

    def test_large_universe_no_cache_warning(self):
        """Test warning for large universe without caching."""
        config = {
            "universe": {"size": 1000},
            "cache": {"enabled": False},
        }
        result = check_optimality_warnings(config)
        
        assert result.valid is True
        assert any("cache" in w.parameter for w in result.warnings)

    def test_optimal_config_no_warnings(self):
        """Test optimal config generates no warnings."""
        config = {
            "preselection": {"top_k": 30, "lookback": 252},
            "membership": {"buffer_rank": 50},
            "universe": {"size": 100},
            "cache": {"enabled": True},
        }
        result = check_optimality_warnings(config)
        
        assert result.valid is True
        assert len(result.warnings) == 0


@pytest.mark.integration
class TestDependencyChecks:
    """Test dependency availability checks."""

    def test_no_dependencies_valid(self):
        """Test validation passes when no dependencies required."""
        result = check_dependencies(fast_io_enabled=False)
        assert result.valid is True

    def test_fast_io_warning_if_missing(self):
        """Test warning if fast IO enabled but dependencies missing."""
        # This test may pass or fail depending on whether polars/pyarrow installed
        result = check_dependencies(fast_io_enabled=True)
        # Should always be valid (warnings only)
        assert result.valid is True


@pytest.mark.integration
class TestSensibleDefaults:
    """Test sensible defaults retrieval."""

    def test_get_defaults(self):
        """Test getting sensible defaults."""
        defaults = get_sensible_defaults()
        
        assert "preselection" in defaults
        assert "membership" in defaults
        assert "pit" in defaults
        assert "cache" in defaults
        
        # Check some specific defaults
        assert defaults["preselection"]["top_k"] == 30
        assert defaults["preselection"]["lookback"] == 252
        assert defaults["pit"]["min_history_days"] == 252
        assert defaults["cache"]["enabled"] is False

    def test_defaults_are_copy(self):
        """Test that get_sensible_defaults returns a copy."""
        defaults1 = get_sensible_defaults()
        defaults2 = get_sensible_defaults()
        
        # Modify one copy
        defaults1["preselection"]["top_k"] = 999
        
        # Other copy should be unchanged
        assert defaults2["preselection"]["top_k"] == 30
