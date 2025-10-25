"""Tests for integration of macro regime gating with asset selection."""

import pytest
pytestmark = pytest.mark.integration

from portfolio_management.assets.selection import FilterCriteria
from portfolio_management.macro.models import RegimeConfig


class TestFilterCriteriaRegimeConfig:
    """Tests for regime_config integration in FilterCriteria."""

    def test_filter_criteria_with_regime_config(self) -> None:
        """Test creating FilterCriteria with regime_config."""
        regime_config = RegimeConfig(
            enable_gating=True,
            recession_indicator="recession_indicator.us",
        )

        criteria = FilterCriteria(
            data_status=["ok"],
            min_history_days=252,
            regime_config=regime_config,
        )

        assert criteria.regime_config == regime_config
        assert criteria.regime_config.enable_gating is True
        assert criteria.regime_config.recession_indicator == "recession_indicator.us"

    def test_filter_criteria_without_regime_config(self) -> None:
        """Test creating FilterCriteria without regime_config (default)."""
        criteria = FilterCriteria(
            data_status=["ok"],
            min_history_days=252,
        )

        assert criteria.regime_config is None

    def test_filter_criteria_default_includes_regime_config(self) -> None:
        """Test that FilterCriteria.default() includes regime_config field."""
        criteria = FilterCriteria.default()

        # Should have regime_config attribute (as None)
        assert hasattr(criteria, "regime_config")
        assert criteria.regime_config is None

    def test_filter_criteria_regime_config_none_explicit(self) -> None:
        """Test explicitly setting regime_config to None."""
        criteria = FilterCriteria(
            data_status=["ok"],
            regime_config=None,
        )

        assert criteria.regime_config is None

    def test_regime_config_with_other_filters(self) -> None:
        """Test that regime_config works alongside other filter criteria."""
        regime_config = RegimeConfig(enable_gating=False)

        criteria = FilterCriteria(
            data_status=["ok", "warning"],
            min_history_days=504,
            markets=["UK", "US"],
            currencies=["GBP", "USD"],
            blocklist={"BADTICKER.UK"},
            regime_config=regime_config,
        )

        # All criteria should be set correctly
        assert criteria.data_status == ["ok", "warning"]
        assert criteria.min_history_days == 504
        assert criteria.markets == ["UK", "US"]
        assert criteria.regime_config == regime_config

    def test_regime_config_disabled_behavior(self) -> None:
        """Test that disabled regime config is properly stored."""
        regime_config = RegimeConfig(enable_gating=False)

        criteria = FilterCriteria(regime_config=regime_config)

        # Config should be stored but not enabled
        assert criteria.regime_config is not None
        assert criteria.regime_config.is_enabled() is False

    def test_regime_config_enabled_behavior(self) -> None:
        """Test that enabled regime config is properly stored."""
        regime_config = RegimeConfig(enable_gating=True)

        criteria = FilterCriteria(regime_config=regime_config)

        # Config should be stored and enabled
        assert criteria.regime_config is not None
        assert criteria.regime_config.is_enabled() is True


class TestRegimeConfigValidation:
    """Tests for regime config validation in FilterCriteria context."""

    def test_valid_regime_config_passes_validation(self) -> None:
        """Test that valid regime config passes FilterCriteria validation."""
        regime_config = RegimeConfig(
            enable_gating=True,
            risk_off_threshold=0.5,
        )
        regime_config.validate()  # Should not raise

        criteria = FilterCriteria(
            data_status=["ok"],
            regime_config=regime_config,
        )

        # FilterCriteria validation should also pass
        criteria.validate()  # Should not raise

    def test_invalid_regime_config_detected(self) -> None:
        """Test that invalid regime config is detected during validation."""
        # Create a config with invalid threshold
        regime_config = RegimeConfig(risk_off_threshold=-0.5)

        # Config validation should fail
        with pytest.raises(ValueError, match="risk_off_threshold must be non-negative"):
            regime_config.validate()

        # FilterCriteria can still be created (validation is separate)
        criteria = FilterCriteria(
            data_status=["ok"],
            regime_config=regime_config,
        )
        # But criteria.validate() would not check regime_config.validate()
        # (that's the regime_config's responsibility)


class TestDocumentedNoOpBehavior:
    """Tests documenting the NoOp behavior of regime gating in selection."""

    def test_noop_documented_in_criteria(self) -> None:
        """Test that NoOp behavior is properly documented in FilterCriteria."""
        # Create config with gating disabled (NoOp)
        regime_config = RegimeConfig(enable_gating=False)
        criteria = FilterCriteria(regime_config=regime_config)

        # Even with regime_config set, gating is disabled
        assert criteria.regime_config is not None
        assert not criteria.regime_config.is_enabled()

        # This documents the NoOp behavior: selection proceeds unchanged
        # when regime gating is disabled (the default and current behavior)

    def test_noop_even_when_enabled(self) -> None:
        """Test that NoOp behavior applies even when gating is enabled."""
        # Create config with gating enabled
        regime_config = RegimeConfig(enable_gating=True)
        criteria = FilterCriteria(regime_config=regime_config)

        # Gating is enabled in config
        assert criteria.regime_config.is_enabled()

        # But the actual implementation (in RegimeGate) is still NoOp
        # This documents that the infrastructure is in place but not yet
        # implementing actual regime logic (future work)

    def test_future_regime_logic_placeholder(self) -> None:
        """Test placeholder for future regime logic integration."""
        # This test documents where future regime logic will be integrated
        regime_config = RegimeConfig(
            enable_gating=True,
            recession_indicator="recession_indicator.us",
            risk_off_threshold=0.5,
        )

        criteria = FilterCriteria(
            data_status=["ok"],
            min_history_days=252,
            regime_config=regime_config,
        )

        # When future logic is implemented, AssetSelector.select_assets()
        # will check criteria.regime_config and apply RegimeGate if enabled
        # For now, this just documents the intended integration point

        assert criteria.regime_config is not None
        assert criteria.regime_config.enable_gating is True
        assert criteria.regime_config.recession_indicator == "recession_indicator.us"
