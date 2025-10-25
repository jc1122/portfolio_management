"""Integration tests for technical indicators with universe configuration."""

import tempfile
from pathlib import Path

import pytest
pytestmark = pytest.mark.integration

import yaml

from portfolio_management.assets.universes import (
    UniverseConfigLoader,
)


class TestUniverseIndicatorConfiguration:
    """Tests for indicator configuration in universe YAML."""

    def test_universe_without_indicators(self):
        """Test loading universe without technical_indicators block."""
        config_yaml = """
universes:
  test_universe:
    description: "Test universe without indicators"
    filter_criteria:
      data_status: ["ok"]
      min_history_days: 252
    return_config:
      method: "simple"
      frequency: "monthly"
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(config_yaml)
            config_path = Path(f.name)

        try:
            universes = UniverseConfigLoader.load_config(config_path)

            assert "test_universe" in universes
            universe = universes["test_universe"]

            # Should have default disabled indicators
            assert universe.technical_indicators.enabled is False
            assert universe.technical_indicators.provider == "noop"
        finally:
            config_path.unlink()

    def test_universe_with_disabled_indicators(self):
        """Test loading universe with explicitly disabled indicators."""
        config_yaml = """
universes:
  test_universe:
    description: "Test universe with disabled indicators"
    filter_criteria:
      data_status: ["ok"]
      min_history_days: 252
    return_config:
      method: "simple"
      frequency: "monthly"
    technical_indicators:
      enabled: false
      provider: "noop"
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(config_yaml)
            config_path = Path(f.name)

        try:
            universes = UniverseConfigLoader.load_config(config_path)
            universe = universes["test_universe"]

            assert universe.technical_indicators.enabled is False
            assert universe.technical_indicators.provider == "noop"
        finally:
            config_path.unlink()

    def test_universe_with_enabled_noop_indicators(self):
        """Test loading universe with enabled noop indicators."""
        config_yaml = """
universes:
  test_universe:
    description: "Test universe with noop indicators"
    filter_criteria:
      data_status: ["ok"]
      min_history_days: 252
    return_config:
      method: "simple"
      frequency: "monthly"
    technical_indicators:
      enabled: true
      provider: "noop"
      params:
        window: 20
        threshold: 0.5
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(config_yaml)
            config_path = Path(f.name)

        try:
            universes = UniverseConfigLoader.load_config(config_path)
            universe = universes["test_universe"]

            assert universe.technical_indicators.enabled is True
            assert universe.technical_indicators.provider == "noop"
            assert universe.technical_indicators.params["window"] == 20
            assert universe.technical_indicators.params["threshold"] == 0.5
        finally:
            config_path.unlink()

    def test_universe_validation_fails_invalid_provider(self):
        """Test that universe validation fails with invalid provider."""
        config_yaml = """
universes:
  test_universe:
    description: "Test universe with invalid provider"
    filter_criteria:
      data_status: ["ok"]
      min_history_days: 252
    return_config:
      method: "simple"
      frequency: "monthly"
    technical_indicators:
      enabled: true
      provider: "invalid_provider"
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(config_yaml)
            config_path = Path(f.name)

        try:
            from portfolio_management.core.exceptions import ConfigurationError

            with pytest.raises(ConfigurationError, match="failed validation"):
                UniverseConfigLoader.load_config(config_path)
        finally:
            config_path.unlink()

    def test_universe_validation_fails_invalid_window(self):
        """Test that validation fails with invalid window parameter."""
        config_yaml = """
universes:
  test_universe:
    description: "Test universe with invalid window"
    filter_criteria:
      data_status: ["ok"]
      min_history_days: 252
    return_config:
      method: "simple"
      frequency: "monthly"
    technical_indicators:
      enabled: true
      provider: "noop"
      params:
        window: -5
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(config_yaml)
            config_path = Path(f.name)

        try:
            from portfolio_management.core.exceptions import ConfigurationError

            with pytest.raises(ConfigurationError, match="failed validation"):
                UniverseConfigLoader.load_config(config_path)
        finally:
            config_path.unlink()

    def test_existing_universe_config_loads(self):
        """Test that existing universe config still loads correctly."""
        # This tests backward compatibility
        config_path = Path("config/universes.yaml")

        if not config_path.exists():
            pytest.skip("Main universe config not found")

        universes = UniverseConfigLoader.load_config(config_path)

        # Should load successfully
        assert len(universes) > 0

        # All universes should have technical_indicators field
        for name, universe in universes.items():
            assert hasattr(universe, "technical_indicators")
            # Should be valid
            universe.validate()

    def test_equity_with_indicators_universe(self):
        """Test the example equity_with_indicators universe from config."""
        config_path = Path("config/universes.yaml")

        if not config_path.exists():
            pytest.skip("Main universe config not found")

        universes = UniverseConfigLoader.load_config(config_path)

        # Check if equity_with_indicators exists
        if "equity_with_indicators" in universes:
            universe = universes["equity_with_indicators"]

            assert universe.technical_indicators.enabled is True
            assert universe.technical_indicators.provider == "noop"
            assert "window" in universe.technical_indicators.params
            assert "threshold" in universe.technical_indicators.params

    def test_configuration_roundtrip(self):
        """Test that configuration can be saved and loaded correctly."""
        original_config = {
            "universes": {
                "test_universe": {
                    "description": "Test roundtrip",
                    "filter_criteria": {
                        "data_status": ["ok"],
                        "min_history_days": 252,
                        "min_price_rows": 252,
                    },
                    "return_config": {
                        "method": "simple",
                        "frequency": "monthly",
                    },
                    "technical_indicators": {
                        "enabled": True,
                        "provider": "noop",
                        "params": {"window": 20, "threshold": 0.7},
                    },
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(original_config, f)
            config_path = Path(f.name)

        try:
            # Load configuration
            universes = UniverseConfigLoader.load_config(config_path)
            universe = universes["test_universe"]

            # Verify all fields preserved
            assert universe.description == "Test roundtrip"
            assert universe.technical_indicators.enabled is True
            assert universe.technical_indicators.provider == "noop"
            assert universe.technical_indicators.params["window"] == 20
            assert universe.technical_indicators.params["threshold"] == 0.7
        finally:
            config_path.unlink()
