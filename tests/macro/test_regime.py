"""Tests for RegimeGate and regime-based selection gating."""

from dataclasses import dataclass

from portfolio_management.macro.models import RegimeConfig
from portfolio_management.macro.regime import RegimeGate


# Mock SelectedAsset for testing (simpler than importing the full class)
@dataclass
class MockSelectedAsset:
    """Mock SelectedAsset for testing."""

    symbol: str
    isin: str = "TEST_ISIN"
    name: str = "Test Asset"
    market: str = "US"
    region: str = "North America"
    currency: str = "USD"
    category: str = "ETF"


class TestRegimeGateInit:
    """Tests for RegimeGate initialization."""

    def test_init_with_config(self) -> None:
        """Test initialization with a RegimeConfig."""
        config = RegimeConfig(enable_gating=False)
        gate = RegimeGate(config)

        assert gate.config == config

    def test_init_with_enabled_config(self) -> None:
        """Test initialization with enabled gating."""
        config = RegimeConfig(enable_gating=True)
        gate = RegimeGate(config)

        assert gate.config.is_enabled() is True


class TestApplyGating:
    """Tests for apply_gating method."""

    def test_apply_gating_disabled(self) -> None:
        """Test that gating is NoOp when disabled."""
        config = RegimeConfig(enable_gating=False)
        gate = RegimeGate(config)

        assets = [
            MockSelectedAsset(symbol="AAPL.US"),
            MockSelectedAsset(symbol="MSFT.US"),
            MockSelectedAsset(symbol="GOOGL.US"),
        ]

        result = gate.apply_gating(assets)

        # Should return all assets unchanged (NoOp)
        assert result == assets
        assert len(result) == 3

    def test_apply_gating_enabled_but_noop(self) -> None:
        """Test that gating is NoOp even when enabled (stub behavior)."""
        config = RegimeConfig(enable_gating=True)
        gate = RegimeGate(config)

        assets = [
            MockSelectedAsset(symbol="AAPL.US"),
            MockSelectedAsset(symbol="MSFT.US"),
            MockSelectedAsset(symbol="GOOGL.US"),
        ]

        result = gate.apply_gating(assets)

        # Even with enabled gating, current implementation is NoOp
        assert result == assets
        assert len(result) == 3

    def test_apply_gating_with_date(self) -> None:
        """Test that date parameter is accepted (but currently ignored)."""
        config = RegimeConfig(enable_gating=False)
        gate = RegimeGate(config)

        assets = [
            MockSelectedAsset(symbol="AAPL.US"),
        ]

        result = gate.apply_gating(assets, date="2025-10-23")

        # Should work without error (date currently ignored in NoOp)
        assert result == assets

    def test_apply_gating_empty_list(self) -> None:
        """Test applying gating to an empty asset list."""
        config = RegimeConfig(enable_gating=False)
        gate = RegimeGate(config)

        assets: list[MockSelectedAsset] = []

        result = gate.apply_gating(assets)

        assert result == []
        assert len(result) == 0


class TestGetCurrentRegime:
    """Tests for get_current_regime method."""

    def test_get_current_regime_noop(self) -> None:
        """Test that current regime is always neutral (NoOp)."""
        config = RegimeConfig(enable_gating=False)
        gate = RegimeGate(config)

        regime = gate.get_current_regime()

        assert "recession" in regime
        assert "risk_sentiment" in regime
        assert "mode" in regime
        assert regime["recession"] == "neutral"
        assert regime["risk_sentiment"] == "neutral"
        assert regime["mode"] == "noop"

    def test_get_current_regime_with_date(self) -> None:
        """Test getting regime for a specific date (currently ignored)."""
        config = RegimeConfig(enable_gating=False)
        gate = RegimeGate(config)

        regime = gate.get_current_regime(date="2025-10-23")

        # Should work without error and return neutral
        assert regime["recession"] == "neutral"
        assert regime["risk_sentiment"] == "neutral"

    def test_get_current_regime_enabled_config(self) -> None:
        """Test regime with enabled config (still NoOp)."""
        config = RegimeConfig(
            enable_gating=True,
            recession_indicator="recession_indicator.us",
            risk_off_threshold=0.5,
        )
        gate = RegimeGate(config)

        regime = gate.get_current_regime()

        # Even with configuration, current implementation is NoOp
        assert regime["recession"] == "neutral"
        assert regime["risk_sentiment"] == "neutral"
        assert regime["mode"] == "noop"


class TestFilterByAssetClass:
    """Tests for filter_by_asset_class method."""

    def test_filter_by_asset_class_noop(self) -> None:
        """Test that asset class filtering is NoOp."""
        config = RegimeConfig(enable_gating=False)
        gate = RegimeGate(config)

        assets = [
            MockSelectedAsset(symbol="EQUITY.US", category="equity"),
            MockSelectedAsset(symbol="BOND.US", category="bond"),
        ]

        result = gate.filter_by_asset_class(assets, allowed_classes=["equity"])

        # NoOp: should return all assets unchanged
        assert result == assets
        assert len(result) == 2

    def test_filter_by_asset_class_no_restriction(self) -> None:
        """Test filtering with no allowed classes specified."""
        config = RegimeConfig(enable_gating=False)
        gate = RegimeGate(config)

        assets = [
            MockSelectedAsset(symbol="EQUITY.US", category="equity"),
            MockSelectedAsset(symbol="BOND.US", category="bond"),
        ]

        result = gate.filter_by_asset_class(assets, allowed_classes=None)

        # Should return all assets
        assert result == assets


class TestAdjustSelectionScores:
    """Tests for adjust_selection_scores method."""

    def test_adjust_selection_scores_noop(self) -> None:
        """Test that score adjustment is NoOp (all scores 1.0)."""
        config = RegimeConfig(enable_gating=False)
        gate = RegimeGate(config)

        assets = [
            MockSelectedAsset(symbol="AAPL.US"),
            MockSelectedAsset(symbol="MSFT.US"),
            MockSelectedAsset(symbol="GOOGL.US"),
        ]

        scored_assets = gate.adjust_selection_scores(assets)

        # Should return all assets with neutral score 1.0
        assert len(scored_assets) == 3
        for asset, score in scored_assets:
            assert score == 1.0
            assert isinstance(asset, MockSelectedAsset)

    def test_adjust_selection_scores_with_date(self) -> None:
        """Test score adjustment with date parameter (currently ignored)."""
        config = RegimeConfig(enable_gating=False)
        gate = RegimeGate(config)

        assets = [
            MockSelectedAsset(symbol="AAPL.US"),
        ]

        scored_assets = gate.adjust_selection_scores(assets, date="2025-10-23")

        # Should work without error
        assert len(scored_assets) == 1
        assert scored_assets[0][1] == 1.0

    def test_adjust_selection_scores_empty_list(self) -> None:
        """Test score adjustment with empty list."""
        config = RegimeConfig(enable_gating=False)
        gate = RegimeGate(config)

        assets: list[MockSelectedAsset] = []

        scored_assets = gate.adjust_selection_scores(assets)

        assert len(scored_assets) == 0


class TestIntegrationScenarios:
    """Integration tests for complete regime gating scenarios."""

    def test_full_gating_workflow_disabled(self) -> None:
        """Test complete workflow with gating disabled."""
        # Create config and gate
        config = RegimeConfig(enable_gating=False)
        gate = RegimeGate(config)

        # Create asset list
        assets = [
            MockSelectedAsset(symbol="AAPL.US"),
            MockSelectedAsset(symbol="MSFT.US"),
            MockSelectedAsset(symbol="BOND.US", category="bond"),
        ]

        # Check current regime
        regime = gate.get_current_regime()
        assert regime["mode"] == "noop"

        # Apply gating
        gated_assets = gate.apply_gating(assets, date="2025-10-23")
        assert len(gated_assets) == 3

        # Adjust scores
        scored_assets = gate.adjust_selection_scores(gated_assets)
        assert all(score == 1.0 for _, score in scored_assets)

    def test_full_gating_workflow_enabled(self) -> None:
        """Test complete workflow with gating enabled (but still NoOp)."""
        # Create config with all features enabled
        config = RegimeConfig(
            enable_gating=True,
            recession_indicator="recession_indicator.us",
            risk_off_threshold=0.5,
        )
        gate = RegimeGate(config)

        # Create asset list
        assets = [
            MockSelectedAsset(symbol="AAPL.US"),
            MockSelectedAsset(symbol="MSFT.US"),
            MockSelectedAsset(symbol="BOND.US", category="bond"),
        ]

        # Even with enabled config, behavior is NoOp
        regime = gate.get_current_regime()
        assert regime["mode"] == "noop"

        gated_assets = gate.apply_gating(assets, date="2025-10-23")
        assert len(gated_assets) == 3

        scored_assets = gate.adjust_selection_scores(gated_assets)
        assert all(score == 1.0 for _, score in scored_assets)

    def test_documented_noop_behavior(self) -> None:
        """Test that documented NoOp behavior is consistent."""
        # Create various configurations
        configs = [
            RegimeConfig(),  # Default
            RegimeConfig(enable_gating=False),  # Explicitly disabled
            RegimeConfig(enable_gating=True),  # Enabled but still NoOp
            RegimeConfig(  # Fully configured but still NoOp
                enable_gating=True,
                recession_indicator="recession_indicator.us",
                risk_off_threshold=0.5,
            ),
        ]

        assets = [
            MockSelectedAsset(symbol="AAPL.US"),
            MockSelectedAsset(symbol="MSFT.US"),
        ]

        # All configurations should produce identical NoOp behavior
        for config in configs:
            gate = RegimeGate(config)

            # Test apply_gating
            result = gate.apply_gating(assets)
            assert result == assets, f"Failed for config: {config}"

            # Test get_current_regime
            regime = gate.get_current_regime()
            assert regime["recession"] == "neutral", f"Failed for config: {config}"
            assert regime["risk_sentiment"] == "neutral", f"Failed for config: {config}"

            # Test adjust_selection_scores
            scored = gate.adjust_selection_scores(assets)
            assert all(
                score == 1.0 for _, score in scored
            ), f"Failed for config: {config}"
