"""Tests for FilterHook."""

import pandas as pd
import pytest

from portfolio_management.analytics.indicators import (
    FilterHook,
    IndicatorConfig,
    NoOpIndicatorProvider,
)


class TestFilterHook:
    """Tests for FilterHook class."""

    def test_filter_disabled_returns_all_assets(self):
        """Test that disabled filter returns all input assets."""
        config = IndicatorConfig.disabled()
        provider = NoOpIndicatorProvider()
        hook = FilterHook(config, provider)
        
        prices = pd.DataFrame({
            "AAPL": [100, 101, 102],
            "MSFT": [200, 201, 202],
            "GOOGL": [150, 151, 152]
        }, index=pd.date_range("2020-01-01", periods=3))
        
        assets = ["AAPL", "MSFT", "GOOGL"]
        filtered = hook.filter_assets(prices, assets)
        
        assert filtered == assets

    def test_filter_noop_returns_all_assets(self):
        """Test that noop provider returns all assets (all True signals)."""
        config = IndicatorConfig.noop()
        provider = NoOpIndicatorProvider()
        hook = FilterHook(config, provider)
        
        prices = pd.DataFrame({
            "AAPL": [100, 101, 102, 103],
            "MSFT": [200, 201, 202, 203],
        }, index=pd.date_range("2020-01-01", periods=4))
        
        assets = ["AAPL", "MSFT"]
        filtered = hook.filter_assets(prices, assets)
        
        assert filtered == assets

    def test_filter_missing_asset_in_prices(self):
        """Test that assets missing from price data are excluded."""
        config = IndicatorConfig.noop()
        provider = NoOpIndicatorProvider()
        hook = FilterHook(config, provider)
        
        prices = pd.DataFrame({
            "AAPL": [100, 101, 102],
            "MSFT": [200, 201, 202],
        }, index=pd.date_range("2020-01-01", periods=3))
        
        # Request includes GOOGL which is not in prices
        assets = ["AAPL", "MSFT", "GOOGL"]
        filtered = hook.filter_assets(prices, assets)
        
        # Only AAPL and MSFT should be returned
        assert set(filtered) == {"AAPL", "MSFT"}

    def test_filter_empty_price_series(self):
        """Test that assets with no valid prices are excluded."""
        config = IndicatorConfig.noop()
        provider = NoOpIndicatorProvider()
        hook = FilterHook(config, provider)
        
        prices = pd.DataFrame({
            "AAPL": [100, 101, 102],
            "MSFT": [None, None, None],  # All NaN
        }, index=pd.date_range("2020-01-01", periods=3))
        
        assets = ["AAPL", "MSFT"]
        filtered = hook.filter_assets(prices, assets)
        
        # Only AAPL should pass (MSFT has no valid data)
        assert filtered == ["AAPL"]

    def test_filter_validates_config_on_init(self):
        """Test that FilterHook validates config on initialization."""
        config = IndicatorConfig(enabled=True, provider="invalid")
        provider = NoOpIndicatorProvider()
        
        with pytest.raises(ValueError, match="Unsupported indicator provider"):
            FilterHook(config, provider)

    def test_filter_with_single_asset(self):
        """Test filtering with single asset."""
        config = IndicatorConfig.noop()
        provider = NoOpIndicatorProvider()
        hook = FilterHook(config, provider)
        
        prices = pd.DataFrame({
            "AAPL": [100, 101, 102, 103, 104]
        }, index=pd.date_range("2020-01-01", periods=5))
        
        assets = ["AAPL"]
        filtered = hook.filter_assets(prices, assets)
        
        assert filtered == ["AAPL"]

    def test_filter_empty_asset_list(self):
        """Test filtering with empty asset list."""
        config = IndicatorConfig.noop()
        provider = NoOpIndicatorProvider()
        hook = FilterHook(config, provider)
        
        prices = pd.DataFrame({
            "AAPL": [100, 101, 102],
            "MSFT": [200, 201, 202],
        }, index=pd.date_range("2020-01-01", periods=3))
        
        assets = []
        filtered = hook.filter_assets(prices, assets)
        
        assert filtered == []

    def test_filter_preserves_asset_order(self):
        """Test that filtering preserves asset order from input list."""
        config = IndicatorConfig.noop()
        provider = NoOpIndicatorProvider()
        hook = FilterHook(config, provider)
        
        prices = pd.DataFrame({
            "AAPL": [100, 101, 102],
            "MSFT": [200, 201, 202],
            "GOOGL": [150, 151, 152],
            "AMZN": [300, 301, 302]
        }, index=pd.date_range("2020-01-01", periods=3))
        
        # Specific order
        assets = ["GOOGL", "AAPL", "AMZN", "MSFT"]
        filtered = hook.filter_assets(prices, assets)
        
        # Order should be preserved
        assert filtered == assets

    def test_filter_with_params(self):
        """Test that hook passes params to provider."""
        config = IndicatorConfig.noop(params={"window": 20, "threshold": 0.5})
        provider = NoOpIndicatorProvider()
        hook = FilterHook(config, provider)
        
        prices = pd.DataFrame({
            "AAPL": [100, 101, 102, 103],
        }, index=pd.date_range("2020-01-01", periods=4))
        
        assets = ["AAPL"]
        filtered = hook.filter_assets(prices, assets)
        
        # With noop provider, should still return all assets
        assert filtered == ["AAPL"]


class MockIndicatorProvider:
    """Mock provider that returns custom signals for testing."""
    
    def __init__(self, signals_map):
        """Initialize with map of asset -> signal value."""
        self.signals_map = signals_map
    
    def compute(self, series, params):
        """Return predetermined signal based on series name."""
        # Get asset name from series.name or use first signal
        asset = getattr(series, 'name', list(self.signals_map.keys())[0])
        signal_value = self.signals_map.get(asset, True)
        
        # Return series with constant signal value
        return pd.Series(signal_value, index=series.index, dtype=bool)


class TestFilterHookWithMockProvider:
    """Tests using mock provider to verify filtering logic."""
    
    def test_filter_excludes_false_signals(self):
        """Test that assets with False signal are excluded."""
        # Mock provider that returns False for MSFT
        signals = {"AAPL": True, "MSFT": False, "GOOGL": True}
        provider = MockIndicatorProvider(signals)
        
        config = IndicatorConfig.noop()
        hook = FilterHook(config, provider)
        
        prices = pd.DataFrame({
            "AAPL": [100, 101, 102],
            "MSFT": [200, 201, 202],
            "GOOGL": [150, 151, 152]
        }, index=pd.date_range("2020-01-01", periods=3))
        
        # Add names to columns so mock can identify them
        prices.columns.name = None
        for col in prices.columns:
            prices[col].name = col
        
        assets = ["AAPL", "MSFT", "GOOGL"]
        filtered = hook.filter_assets(prices, assets)
        
        # MSFT should be excluded
        assert "MSFT" not in filtered
        assert "AAPL" in filtered
        assert "GOOGL" in filtered
