"""Tests for macro data models."""

import pytest
pytestmark = pytest.mark.integration

from portfolio_management.macro.models import MacroSeries, RegimeConfig


class TestMacroSeries:
    """Tests for MacroSeries dataclass."""

    def test_create_macro_series(self) -> None:
        """Test creating a MacroSeries instance."""
        series = MacroSeries(
            ticker="gdp.us",
            rel_path="data/daily/us/economic/gdp.txt",
            start_date="2000-01-01",
            end_date="2025-10-23",
            region="us",
            category="economic_indicators",
        )

        assert series.ticker == "gdp.us"
        assert series.rel_path == "data/daily/us/economic/gdp.txt"
        assert series.start_date == "2000-01-01"
        assert series.end_date == "2025-10-23"
        assert series.region == "us"
        assert series.category == "economic_indicators"

    def test_macro_series_frozen(self) -> None:
        """Test that MacroSeries is immutable (frozen)."""
        series = MacroSeries(
            ticker="gdp.us",
            rel_path="data/daily/us/economic/gdp.txt",
            start_date="2000-01-01",
            end_date="2025-10-23",
        )

        with pytest.raises(AttributeError):
            series.ticker = "pmi.us"

    def test_macro_series_defaults(self) -> None:
        """Test MacroSeries with default values."""
        series = MacroSeries(
            ticker="gdp.us",
            rel_path="data/daily/us/economic/gdp.txt",
            start_date="2000-01-01",
            end_date="2025-10-23",
        )

        assert series.region == ""
        assert series.category == ""


class TestRegimeConfig:
    """Tests for RegimeConfig dataclass."""

    def test_create_regime_config(self) -> None:
        """Test creating a RegimeConfig instance."""
        config = RegimeConfig(
            recession_indicator="recession_indicator.us",
            risk_off_threshold=0.5,
            enable_gating=True,
        )

        assert config.recession_indicator == "recession_indicator.us"
        assert config.risk_off_threshold == 0.5
        assert config.enable_gating is True

    def test_regime_config_defaults(self) -> None:
        """Test RegimeConfig with default values."""
        config = RegimeConfig()

        assert config.recession_indicator is None
        assert config.risk_off_threshold is None
        assert config.enable_gating is False
        assert config.custom_rules is None

    def test_is_enabled(self) -> None:
        """Test is_enabled method."""
        # Disabled by default
        config = RegimeConfig()
        assert config.is_enabled() is False

        # Explicitly enabled
        config_enabled = RegimeConfig(enable_gating=True)
        assert config_enabled.is_enabled() is True

    def test_validate_valid_config(self) -> None:
        """Test validation with valid configuration."""
        config = RegimeConfig(
            recession_indicator="recession_indicator.us",
            risk_off_threshold=0.5,
        )
        # Should not raise
        config.validate()

    def test_validate_zero_threshold(self) -> None:
        """Test validation with zero threshold (valid)."""
        config = RegimeConfig(risk_off_threshold=0.0)
        # Should not raise
        config.validate()

    def test_validate_negative_threshold(self) -> None:
        """Test validation with negative threshold (invalid)."""
        config = RegimeConfig(risk_off_threshold=-0.5)

        with pytest.raises(ValueError, match="risk_off_threshold must be non-negative"):
            config.validate()

    def test_custom_rules(self) -> None:
        """Test configuration with custom rules."""
        custom = {"rule1": "value1", "rule2": "value2"}
        config = RegimeConfig(custom_rules=custom)

        assert config.custom_rules == custom
