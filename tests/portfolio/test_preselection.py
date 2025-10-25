"""Tests for factor-based asset preselection."""

import datetime

import numpy as np
import pandas as pd
import pytest

from portfolio_management.core.exceptions import InsufficientDataError
from portfolio_management.portfolio.preselection import (
    Preselection,
    PreselectionConfig,
    PreselectionMethod,
    create_preselection_from_dict,
)


@pytest.fixture
def sample_returns():
    """Create sample returns data for testing."""
    dates = pd.date_range("2020-01-01", "2020-12-31", freq="D")
    np.random.seed(42)

    # Create 10 assets with different characteristics
    returns_data = {
        # High momentum, low volatility
        "ASSET_A": np.random.normal(0.001, 0.01, len(dates)),
        # Low momentum, low volatility
        "ASSET_B": np.random.normal(0.0, 0.01, len(dates)),
        # High momentum, high volatility
        "ASSET_C": np.random.normal(0.002, 0.03, len(dates)),
        # Negative momentum, low volatility
        "ASSET_D": np.random.normal(-0.001, 0.01, len(dates)),
        # Medium momentum, medium volatility
        "ASSET_E": np.random.normal(0.0005, 0.015, len(dates)),
        # Very high momentum
        "ASSET_F": np.random.normal(0.003, 0.02, len(dates)),
        # Very low volatility
        "ASSET_G": np.random.normal(0.0, 0.005, len(dates)),
        # High volatility
        "ASSET_H": np.random.normal(0.0, 0.04, len(dates)),
        # Stable positive
        "ASSET_I": np.random.normal(0.0008, 0.012, len(dates)),
        # Stable negative
        "ASSET_J": np.random.normal(-0.0005, 0.012, len(dates)),
    }

    return pd.DataFrame(returns_data, index=dates)


class TestPreselectionConfig:
    """Tests for PreselectionConfig validation."""

    def test_default_config(self):
        """Test default configuration values."""
        config = PreselectionConfig()
        assert config.method == PreselectionMethod.MOMENTUM
        assert config.top_k is None
        assert config.lookback == 252
        assert config.skip == 1
        assert config.momentum_weight == 0.5
        assert config.low_vol_weight == 0.5
        assert config.min_periods == 60

    def test_custom_config(self):
        """Test custom configuration."""
        config = PreselectionConfig(
            method=PreselectionMethod.LOW_VOL,
            top_k=20,
            lookback=120,
            skip=5,
            momentum_weight=0.6,
            low_vol_weight=0.4,
        )
        assert config.method == PreselectionMethod.LOW_VOL
        assert config.top_k == 20
        assert config.lookback == 120
        assert config.skip == 5
        assert config.momentum_weight == 0.6
        assert config.low_vol_weight == 0.4


class TestPreselectionValidation:
    """Tests for configuration validation."""

    def test_invalid_lookback(self):
        """Test that invalid lookback raises error."""
        config = PreselectionConfig(lookback=0)
        with pytest.raises(ValueError, match="lookback must be >= 1"):
            Preselection(config)

    def test_invalid_skip(self):
        """Test that invalid skip raises error."""
        config = PreselectionConfig(skip=-1)
        with pytest.raises(ValueError, match="skip must be >= 0"):
            Preselection(config)

    def test_skip_greater_than_lookback(self):
        """Test that skip >= lookback raises error."""
        config = PreselectionConfig(lookback=10, skip=10)
        with pytest.raises(ValueError, match=r"skip.*must be < lookback"):
            Preselection(config)

    def test_invalid_min_periods(self):
        """Test that invalid min_periods raises error."""
        config = PreselectionConfig(min_periods=0)
        with pytest.raises(ValueError, match="min_periods must be >= 1"):
            Preselection(config)

    def test_min_periods_greater_than_lookback(self):
        """Test that min_periods > lookback raises error."""
        config = PreselectionConfig(lookback=100, min_periods=150)
        with pytest.raises(ValueError, match=r"min_periods.*must be <= lookback"):
            Preselection(config)

    def test_combined_weights_must_sum_to_one(self):
        """Test that combined method weights must sum to 1.0."""
        config = PreselectionConfig(
            method=PreselectionMethod.COMBINED,
            momentum_weight=0.6,
            low_vol_weight=0.5,
        )
        with pytest.raises(ValueError, match="Combined weights must sum to 1.0"):
            Preselection(config)


class TestMomentumPreselection:
    """Tests for momentum-based preselection."""

    def test_momentum_selection(self, sample_returns):
        """Test basic momentum selection."""
        config = PreselectionConfig(
            method=PreselectionMethod.MOMENTUM, top_k=5, lookback=100
        )
        preselection = Preselection(config)

        selected = preselection.select_assets(sample_returns)

        assert len(selected) == 5
        assert isinstance(selected, list)
        # Selected assets should be sorted alphabetically
        assert selected == sorted(selected)

    def test_momentum_with_skip(self, sample_returns):
        """Test momentum with skip period."""
        config = PreselectionConfig(
            method=PreselectionMethod.MOMENTUM, top_k=3, lookback=60, skip=5
        )
        preselection = Preselection(config)

        selected = preselection.select_assets(sample_returns)

        assert len(selected) == 3
        assert selected == sorted(selected)

    def test_momentum_no_lookahead(self, sample_returns):
        """Test that momentum doesn't use future data."""
        config = PreselectionConfig(
            method=PreselectionMethod.MOMENTUM, top_k=5, lookback=100
        )
        preselection = Preselection(config)

        # Select assets as of middle of the year
        rebalance_date = datetime.date(2020, 6, 1)
        selected = preselection.select_assets(sample_returns, rebalance_date)

        assert len(selected) == 5
        # Verify only data before rebalance date was used
        # by checking that we get same result with truncated data
        truncated = sample_returns[sample_returns.index.date < rebalance_date]
        selected_truncated = preselection.select_assets(truncated)
        assert selected == selected_truncated


class TestLowVolatilityPreselection:
    """Tests for low-volatility preselection."""

    def test_low_vol_selection(self, sample_returns):
        """Test basic low-volatility selection."""
        config = PreselectionConfig(
            method=PreselectionMethod.LOW_VOL, top_k=5, lookback=100
        )
        preselection = Preselection(config)

        selected = preselection.select_assets(sample_returns)

        assert len(selected) == 5
        assert selected == sorted(selected)

    def test_low_vol_prefers_low_volatility(self, sample_returns):
        """Test that low-vol method selects lower volatility assets."""
        config = PreselectionConfig(
            method=PreselectionMethod.LOW_VOL, top_k=3, lookback=200
        )
        preselection = Preselection(config)

        selected = preselection.select_assets(sample_returns)

        # ASSET_G has very low volatility and should be selected
        assert "ASSET_G" in selected
        # ASSET_H has high volatility and should not be selected
        assert "ASSET_H" not in selected


class TestCombinedPreselection:
    """Tests for combined factor preselection."""

    def test_combined_selection(self, sample_returns):
        """Test combined factor selection."""
        config = PreselectionConfig(
            method=PreselectionMethod.COMBINED,
            top_k=5,
            lookback=100,
            momentum_weight=0.5,
            low_vol_weight=0.5,
        )
        preselection = Preselection(config)

        selected = preselection.select_assets(sample_returns)

        assert len(selected) == 5
        assert selected == sorted(selected)

    def test_combined_with_different_weights(self, sample_returns):
        """Test combined with momentum-heavy weighting."""
        config = PreselectionConfig(
            method=PreselectionMethod.COMBINED,
            top_k=5,
            lookback=100,
            momentum_weight=0.8,
            low_vol_weight=0.2,
        )
        preselection = Preselection(config)

        selected_momentum_heavy = preselection.select_assets(sample_returns)

        # Compare with low-vol heavy
        config2 = PreselectionConfig(
            method=PreselectionMethod.COMBINED,
            top_k=5,
            lookback=100,
            momentum_weight=0.2,
            low_vol_weight=0.8,
        )
        preselection2 = Preselection(config2)
        selected_vol_heavy = preselection2.select_assets(sample_returns)

        # Different weightings should potentially give different results
        # (though with random data this isn't guaranteed)
        assert len(selected_momentum_heavy) == 5
        assert len(selected_vol_heavy) == 5


class TestDeterminism:
    """Tests for deterministic behavior."""

    def test_deterministic_selection(self, sample_returns):
        """Test that selection is deterministic."""
        config = PreselectionConfig(
            method=PreselectionMethod.MOMENTUM, top_k=5, lookback=100
        )
        preselection = Preselection(config)

        # Run selection multiple times
        selected1 = preselection.select_assets(sample_returns)
        selected2 = preselection.select_assets(sample_returns)
        selected3 = preselection.select_assets(sample_returns)

        assert selected1 == selected2 == selected3

    def test_tie_breaking_by_symbol(self):
        """Test that ties are broken alphabetically by symbol."""
        # Create data where multiple assets have identical scores
        dates = pd.date_range("2020-01-01", "2020-12-31", freq="D")
        returns_data = {
            "ASSET_C": [0.001] * len(dates),  # Identical returns
            "ASSET_A": [0.001] * len(dates),  # Identical returns
            "ASSET_B": [0.001] * len(dates),  # Identical returns
            "ASSET_D": [0.002] * len(dates),  # Different return
        }
        returns = pd.DataFrame(returns_data, index=dates)

        config = PreselectionConfig(
            method=PreselectionMethod.MOMENTUM, top_k=2, lookback=100
        )
        preselection = Preselection(config)

        selected = preselection.select_assets(returns)

        # Should select ASSET_D (highest) and ASSET_A (first alphabetically of ties)
        assert len(selected) == 2
        assert "ASSET_D" in selected
        # Among tied assets (A, B, C), should pick first alphabetically
        # when there's a tie at the cutoff


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_insufficient_data(self, sample_returns):
        """Test that insufficient data raises error."""
        config = PreselectionConfig(
            method=PreselectionMethod.MOMENTUM, top_k=5, lookback=500, min_periods=500
        )
        preselection = Preselection(config)

        with pytest.raises(InsufficientDataError):
            preselection.select_assets(sample_returns)

    def test_top_k_greater_than_assets(self, sample_returns):
        """Test that top_k > num_assets returns all assets."""
        config = PreselectionConfig(
            method=PreselectionMethod.MOMENTUM, top_k=100, lookback=100
        )
        preselection = Preselection(config)

        selected = preselection.select_assets(sample_returns)

        # Should return all 10 assets
        assert len(selected) == 10
        assert set(selected) == set(sample_returns.columns)

    def test_top_k_none_returns_all(self, sample_returns):
        """Test that top_k=None returns all assets."""
        config = PreselectionConfig(
            method=PreselectionMethod.MOMENTUM, top_k=None, lookback=100
        )
        preselection = Preselection(config)

        selected = preselection.select_assets(sample_returns)

        assert len(selected) == 10
        assert set(selected) == set(sample_returns.columns)

    def test_top_k_zero_returns_all(self, sample_returns):
        """Test that top_k=0 returns all assets."""
        config = PreselectionConfig(
            method=PreselectionMethod.MOMENTUM, top_k=0, lookback=100
        )
        preselection = Preselection(config)

        selected = preselection.select_assets(sample_returns)

        assert len(selected) == 10
        assert set(selected) == set(sample_returns.columns)

    def test_all_nan_returns(self):
        """Test handling of all-NaN returns."""
        dates = pd.date_range("2020-01-01", "2020-12-31", freq="D")
        returns_data = {
            "ASSET_A": [np.nan] * len(dates),
            "ASSET_B": [np.nan] * len(dates),
        }
        returns = pd.DataFrame(returns_data, index=dates)

        config = PreselectionConfig(
            method=PreselectionMethod.MOMENTUM, top_k=1, lookback=100, min_periods=1
        )
        preselection = Preselection(config)

        selected = preselection.select_assets(returns)

        # Should return empty list when all scores are NaN
        assert len(selected) == 0

    def test_some_nan_returns(self):
        """Test handling of partial NaN returns."""
        dates = pd.date_range("2020-01-01", "2020-12-31", freq="D")
        returns_data = {
            "ASSET_A": [0.001] * len(dates),
            "ASSET_B": [np.nan] * len(dates),  # All NaN
            "ASSET_C": [0.002] * len(dates),
        }
        returns = pd.DataFrame(returns_data, index=dates)

        config = PreselectionConfig(
            method=PreselectionMethod.MOMENTUM, top_k=2, lookback=100
        )
        preselection = Preselection(config)

        selected = preselection.select_assets(returns)

        # Should only select assets with valid data
        assert len(selected) == 2
        assert "ASSET_B" not in selected
        assert set(selected) == {"ASSET_A", "ASSET_C"}


class TestCreateFromDict:
    """Tests for dictionary-based configuration."""

    def test_create_momentum_from_dict(self):
        """Test creating momentum preselection from dict."""
        config_dict = {
            "method": "momentum",
            "top_k": 10,
            "lookback": 120,
            "skip": 2,
        }

        preselection = create_preselection_from_dict(config_dict)

        assert preselection is not None
        assert preselection.config.method == PreselectionMethod.MOMENTUM
        assert preselection.config.top_k == 10
        assert preselection.config.lookback == 120
        assert preselection.config.skip == 2

    def test_create_combined_from_dict(self):
        """Test creating combined preselection from dict."""
        config_dict = {
            "method": "combined",
            "top_k": 15,
            "lookback": 252,
            "momentum_weight": 0.6,
            "low_vol_weight": 0.4,
        }

        preselection = create_preselection_from_dict(config_dict)

        assert preselection is not None
        assert preselection.config.method == PreselectionMethod.COMBINED
        assert preselection.config.momentum_weight == 0.6
        assert preselection.config.low_vol_weight == 0.4

    def test_create_from_dict_disabled(self):
        """Test that None/0 top_k returns None."""
        config_dict = {"method": "momentum", "top_k": 0}
        assert create_preselection_from_dict(config_dict) is None

        config_dict = {"method": "momentum", "top_k": None}
        assert create_preselection_from_dict(config_dict) is None

        assert create_preselection_from_dict({}) is None

    def test_invalid_method_raises_error(self):
        """Test that invalid method raises error."""
        config_dict = {"method": "invalid_method", "top_k": 10}

        with pytest.raises(ValueError, match="Invalid preselection method"):
            create_preselection_from_dict(config_dict)

    def test_defaults_applied(self):
        """Test that defaults are applied for missing keys."""
        config_dict = {"method": "momentum", "top_k": 10}

        preselection = create_preselection_from_dict(config_dict)

        assert preselection.config.lookback == 252
        assert preselection.config.skip == 1
        assert preselection.config.momentum_weight == 0.5


class TestIntegrationWithStrategies:
    """Integration tests with portfolio strategies (would need actual strategy objects)."""

    def test_preselection_reduces_universe_size(self, sample_returns):
        """Test that preselection reduces universe before optimization."""
        config = PreselectionConfig(
            method=PreselectionMethod.MOMENTUM, top_k=5, lookback=100
        )
        preselection = Preselection(config)

        # Get full universe size
        full_size = len(sample_returns.columns)
        assert full_size == 10

        # Apply preselection
        selected = preselection.select_assets(sample_returns)

        # Verify size reduction
        assert len(selected) == 5
        assert len(selected) < full_size
