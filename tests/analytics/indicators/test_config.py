"""Tests for indicator configuration."""

import pytest
pytestmark = pytest.mark.integration

from portfolio_management.analytics.indicators import IndicatorConfig


class TestIndicatorConfig:
    """Tests for IndicatorConfig dataclass."""

    def test_default_disabled(self):
        """Test default configuration is disabled."""
        config = IndicatorConfig()

        assert config.enabled is False
        assert config.provider == "noop"
        assert config.params == {}

    def test_disabled_factory(self):
        """Test disabled() factory method."""
        config = IndicatorConfig.disabled()

        assert config.enabled is False
        assert config.provider == "noop"
        assert config.params == {}

    def test_noop_factory(self):
        """Test noop() factory method."""
        config = IndicatorConfig.noop()

        assert config.enabled is True
        assert config.provider == "noop"
        assert config.params == {}

    def test_noop_factory_with_params(self):
        """Test noop() factory with parameters."""
        params = {"window": 20, "threshold": 0.5}
        config = IndicatorConfig.noop(params)

        assert config.enabled is True
        assert config.provider == "noop"
        assert config.params == params

    def test_validate_valid_noop(self):
        """Test validation passes for valid noop configuration."""
        config = IndicatorConfig(enabled=True, provider="noop", params={})
        config.validate()  # Should not raise

    def test_validate_disabled_any_provider(self):
        """Test validation allows any provider when disabled."""
        config = IndicatorConfig(enabled=False, provider="unsupported")
        config.validate()  # Should not raise when disabled

    def test_validate_invalid_provider(self):
        """Test validation fails for unsupported provider when enabled."""
        config = IndicatorConfig(enabled=True, provider="unsupported")

        with pytest.raises(ValueError, match="Unsupported indicator provider"):
            config.validate()

    def test_validate_supported_providers(self):
        """Test validation passes for all supported providers."""
        for provider in ["noop", "talib", "ta"]:
            config = IndicatorConfig(enabled=True, provider=provider, params={})
            config.validate()  # Should not raise

    def test_validate_invalid_window(self):
        """Test validation fails for invalid window parameter."""
        config = IndicatorConfig(enabled=True, provider="noop", params={"window": 0})

        with pytest.raises(ValueError, match="Invalid window parameter"):
            config.validate()

    def test_validate_negative_window(self):
        """Test validation fails for negative window."""
        config = IndicatorConfig(enabled=True, provider="noop", params={"window": -5})

        with pytest.raises(ValueError, match="Invalid window parameter"):
            config.validate()

    def test_validate_invalid_threshold(self):
        """Test validation fails for threshold out of range."""
        config = IndicatorConfig(
            enabled=True, provider="noop", params={"threshold": 1.5}
        )

        with pytest.raises(ValueError, match="Invalid threshold parameter"):
            config.validate()

    def test_validate_negative_threshold(self):
        """Test validation fails for negative threshold."""
        config = IndicatorConfig(
            enabled=True, provider="noop", params={"threshold": -0.1}
        )

        with pytest.raises(ValueError, match="Invalid threshold parameter"):
            config.validate()

    def test_validate_valid_threshold(self):
        """Test validation passes for valid threshold values."""
        for threshold in [0.0, 0.5, 1.0]:
            config = IndicatorConfig(
                enabled=True, provider="noop", params={"threshold": threshold}
            )
            config.validate()  # Should not raise

    def test_validate_valid_window(self):
        """Test validation passes for valid window values."""
        for window in [1, 20, 50, 100, 200]:
            config = IndicatorConfig(
                enabled=True, provider="noop", params={"window": window}
            )
            config.validate()  # Should not raise

    def test_validate_mixed_valid_params(self):
        """Test validation passes with multiple valid parameters."""
        config = IndicatorConfig(
            enabled=True,
            provider="noop",
            params={
                "window": 20,
                "threshold": 0.5,
                "custom_param": "value",
                "another_param": 123,
            },
        )
        config.validate()  # Should not raise

    def test_config_immutable_after_creation(self):
        """Test that config can be modified (dataclass is not frozen)."""
        config = IndicatorConfig()
        config.enabled = True
        config.provider = "talib"
        config.params = {"window": 20}

        assert config.enabled is True
        assert config.provider == "talib"
        assert config.params == {"window": 20}
