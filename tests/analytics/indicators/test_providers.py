"""Tests for indicator providers."""

import pandas as pd
import pytest

from portfolio_management.analytics.indicators import (
    IndicatorProvider,
    NoOpIndicatorProvider,
)


class TestNoOpIndicatorProvider:
    """Tests for NoOpIndicatorProvider stub implementation."""

    def test_compute_returns_all_true(self):
        """Test that NoOpIndicatorProvider returns all True signals."""
        provider = NoOpIndicatorProvider()
        
        # Create sample price series
        dates = pd.date_range("2020-01-01", periods=10, freq="D")
        prices = pd.Series([100 + i for i in range(10)], index=dates)
        
        # Compute signal
        signal = provider.compute(prices, {"window": 20})
        
        # Verify all True
        assert len(signal) == len(prices)
        assert signal.all()
        assert signal.dtype == bool

    def test_compute_with_empty_params(self):
        """Test that provider works with empty parameters."""
        provider = NoOpIndicatorProvider()
        
        dates = pd.date_range("2020-01-01", periods=5, freq="D")
        prices = pd.Series([100, 101, 102, 103, 104], index=dates)
        
        signal = provider.compute(prices, {})
        
        assert len(signal) == 5
        assert signal.all()

    def test_compute_preserves_index(self):
        """Test that computed signal preserves input index."""
        provider = NoOpIndicatorProvider()
        
        dates = pd.date_range("2020-01-01", periods=7, freq="D")
        prices = pd.Series([100, 105, 110, 108, 112, 115, 120], index=dates)
        
        signal = provider.compute(prices, {"threshold": 0.5})
        
        assert signal.index.equals(prices.index)

    def test_compute_with_single_value(self):
        """Test provider with single-value series."""
        provider = NoOpIndicatorProvider()
        
        prices = pd.Series([100], index=[pd.Timestamp("2020-01-01")])
        signal = provider.compute(prices, {})
        
        assert len(signal) == 1
        assert signal.iloc[0] == True

    def test_inherits_from_indicator_provider(self):
        """Test that NoOpIndicatorProvider inherits from IndicatorProvider."""
        provider = NoOpIndicatorProvider()
        assert isinstance(provider, IndicatorProvider)

    def test_compute_with_various_params(self):
        """Test that provider ignores various parameter types."""
        provider = NoOpIndicatorProvider()
        
        dates = pd.date_range("2020-01-01", periods=5, freq="D")
        prices = pd.Series([100, 101, 102, 103, 104], index=dates)
        
        # Various parameter combinations should all work
        params_list = [
            {"window": 20},
            {"threshold": 0.7},
            {"window": 50, "threshold": 0.5, "indicator": "rsi"},
            {"complex": {"nested": {"param": True}}},
        ]
        
        for params in params_list:
            signal = provider.compute(prices, params)
            assert signal.all()
            assert len(signal) == 5
