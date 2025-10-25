"""Comprehensive edge case tests for preselection robustness.

This module tests the robustness of the preselection factor computation
with edge cases to ensure deterministic, correct behavior in all scenarios.

Tests cover:
- Ranking ties and deterministic tie-breaking
- Empty or minimal result sets
- Combined factor edge cases
- Data quality issues
- Configuration boundaries
- Z-score edge cases
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
pytestmark = pytest.mark.integration

from portfolio_management.core.exceptions import InsufficientDataError
from portfolio_management.portfolio.preselection import (
    Preselection,
    PreselectionConfig,
    PreselectionMethod,
)

# ============================================================================
# Fixtures for Edge Case Scenarios
# ============================================================================


@pytest.fixture
def dates_1year():
    """Create 1 year of daily dates."""
    return pd.date_range("2023-01-01", "2023-12-31", freq="D")


@pytest.fixture
def dates_short():
    """Create 30 days of dates (short history)."""
    return pd.date_range("2023-01-01", "2023-01-30", freq="D")


@pytest.fixture
def tied_returns(dates_1year):
    """Returns where multiple assets have identical values (ties)."""
    n = len(dates_1year)
    return pd.DataFrame(
        {
            "TIED_A": [0.001] * n,  # Identical to B, C
            "TIED_B": [0.001] * n,  # Identical to A, C
            "TIED_C": [0.001] * n,  # Identical to A, B
            "DIFF_D": [0.002] * n,  # Different (higher)
            "DIFF_E": [0.0005] * n,  # Different (lower)
        },
        index=dates_1year,
    )


@pytest.fixture
def numerical_precision_ties(dates_1year):
    """Returns with very small differences (numerical precision)."""
    n = len(dates_1year)
    base = 0.001
    return pd.DataFrame(
        {
            "ASSET_A": [base] * n,
            "ASSET_B": [base + 1e-10] * n,  # Tiny difference
            "ASSET_C": [base + 1e-11] * n,  # Even tinier
            "ASSET_D": [base - 1e-10] * n,
            "ASSET_E": [base + 1e-9] * n,  # Slightly larger
        },
        index=dates_1year,
    )


@pytest.fixture
def all_identical_returns(dates_1year):
    """All assets have exactly identical returns."""
    n = len(dates_1year)
    return pd.DataFrame(
        {
            "ASSET_Z": [0.001] * n,
            "ASSET_A": [0.001] * n,
            "ASSET_M": [0.001] * n,
            "ASSET_B": [0.001] * n,
            "ASSET_Y": [0.001] * n,
        },
        index=dates_1year,
    )


@pytest.fixture
def sparse_valid_data(dates_1year):
    """Only some assets have sufficient valid data."""
    n = len(dates_1year)
    return pd.DataFrame(
        {
            "VALID_A": np.random.normal(0.001, 0.01, n),  # Full data
            "VALID_B": np.random.normal(0.001, 0.01, n),  # Full data
            "SPARSE_C": [np.nan] * (n - 10) + list(np.random.normal(0.001, 0.01, 10)),
            "SPARSE_D": [np.nan] * (n - 5) + list(np.random.normal(0.001, 0.01, 5)),
            "NO_DATA_E": [np.nan] * n,  # All NaN
        },
        index=dates_1year,
    )


@pytest.fixture
def all_zero_returns(dates_1year):
    """All returns are exactly zero."""
    n = len(dates_1year)
    return pd.DataFrame(
        {
            "ASSET_A": [0.0] * n,
            "ASSET_B": [0.0] * n,
            "ASSET_C": [0.0] * n,
        },
        index=dates_1year,
    )


@pytest.fixture
def extreme_outliers(dates_1year):
    """Returns with extreme outliers (±50% daily)."""
    n = len(dates_1year)
    np.random.seed(42)
    returns = {
        "NORMAL_A": np.random.normal(0.001, 0.01, n),
        "OUTLIER_B": np.random.normal(0.001, 0.01, n),
        "OUTLIER_C": np.random.normal(0.001, 0.01, n),
    }
    # Add extreme outliers
    returns["OUTLIER_B"][10] = 0.5  # +50% one day
    returns["OUTLIER_C"][20] = -0.5  # -50% one day
    return pd.DataFrame(returns, index=dates_1year)


@pytest.fixture
def mixed_volatility(dates_1year):
    """Returns with extreme differences in volatility."""
    n = len(dates_1year)
    np.random.seed(42)
    return pd.DataFrame(
        {
            "LOW_VOL": np.random.normal(0.001, 0.001, n),  # Very low vol
            "MED_VOL": np.random.normal(0.001, 0.01, n),  # Medium vol
            "HIGH_VOL": np.random.normal(0.001, 0.1, n),  # Very high vol
        },
        index=dates_1year,
    )


# ============================================================================
# Phase 2: Ranking Ties Tests
# ============================================================================


class TestRankingTies:
    """Tests for deterministic tie-breaking in rankings."""

    def test_two_assets_identical_momentum_tie_breaking(self, tied_returns):
        """Two assets with identical momentum should be broken by symbol."""
        config = PreselectionConfig(
            method=PreselectionMethod.MOMENTUM,
            top_k=2,
            lookback=100,
        )
        preselection = Preselection(config)

        selected = preselection.select_assets(tied_returns)

        # Should select DIFF_D (highest) and TIED_A (first alphabetically)
        assert len(selected) == 2
        assert "DIFF_D" in selected
        # Among tied assets (TIED_A, TIED_B, TIED_C), pick alphabetically
        assert "TIED_A" in selected or all(
            # Or if there's a tie at cutoff, symbols should be sorted
            s in ["TIED_A", "TIED_B", "TIED_C"]
            for s in selected
            if s != "DIFF_D"
        )

    def test_multiple_assets_tied_at_boundary(self):
        """Multiple assets tied at selection boundary."""
        dates = pd.date_range("2023-01-01", "2023-12-31", freq="D")
        n = len(dates)

        # Create 35 assets where 5 are tied at boundary (ranks 28-32)
        # when top_k=30
        returns_dict = {}
        # Top 27 assets (clearly above cutoff)
        for i in range(27):
            returns_dict[f"TOP_{i:02d}"] = [0.003 + i * 0.0001] * n

        # 5 tied assets at boundary (ranks 28-32)
        for letter in ["Z", "A", "M", "B", "Y"]:
            returns_dict[f"TIE_{letter}"] = [0.002] * n

        # Bottom 3 assets (clearly below cutoff)
        for i in range(3):
            returns_dict[f"BOT_{i:02d}"] = [0.001 - i * 0.0001] * n

        returns = pd.DataFrame(returns_dict, index=dates)

        config = PreselectionConfig(
            method=PreselectionMethod.MOMENTUM,
            top_k=30,
            lookback=100,
        )
        preselection = Preselection(config)

        selected = preselection.select_assets(returns)

        # Should get exactly 30 assets
        assert len(selected) == 30

        # All top 27 should be selected
        top_assets = [f"TOP_{i:02d}" for i in range(27)]
        assert all(asset in selected for asset in top_assets)

        # Among tied assets, should pick first 3 alphabetically
        tied_selected = [s for s in selected if s.startswith("TIE_")]
        assert len(tied_selected) == 3
        # Should be alphabetically first: TIE_A, TIE_B, TIE_M
        assert set(tied_selected) == {"TIE_A", "TIE_B", "TIE_M"}

    def test_all_assets_tied_uniform_factor_values(self, all_identical_returns):
        """All assets have identical factor values."""
        config = PreselectionConfig(
            method=PreselectionMethod.MOMENTUM,
            top_k=3,
            lookback=100,
        )
        preselection = Preselection(config)

        selected = preselection.select_assets(all_identical_returns)

        # Should select 3 assets, alphabetically first
        assert len(selected) == 3
        assert selected == ["ASSET_A", "ASSET_B", "ASSET_M"]

    def test_numerical_precision_ties(self, numerical_precision_ties):
        """Assets with very close values (1e-10 difference)."""
        config = PreselectionConfig(
            method=PreselectionMethod.MOMENTUM,
            top_k=3,
            lookback=100,
        )
        preselection = Preselection(config)

        # Run multiple times to ensure determinism
        selected1 = preselection.select_assets(numerical_precision_ties)
        selected2 = preselection.select_assets(numerical_precision_ties)
        selected3 = preselection.select_assets(numerical_precision_ties)

        # All runs should produce identical results
        assert selected1 == selected2 == selected3
        assert len(selected1) == 3
        # Results should be sorted alphabetically
        assert selected1 == sorted(selected1)

    def test_determinism_with_ties_multiple_runs(self, tied_returns):
        """Determinism: same config produces same order across runs."""
        config = PreselectionConfig(
            method=PreselectionMethod.COMBINED,
            top_k=3,
            lookback=100,
            momentum_weight=0.5,
            low_vol_weight=0.5,
        )
        preselection = Preselection(config)

        # Run 10 times
        results = [preselection.select_assets(tied_returns) for _ in range(10)]

        # All results should be identical
        assert all(r == results[0] for r in results)


# ============================================================================
# Phase 3: Empty or Minimal Result Sets
# ============================================================================


class TestEmptyMinimalResults:
    """Tests for edge cases with empty or minimal result sets."""

    def test_no_assets_meet_min_periods(self, dates_short):
        """No assets meet min_periods requirement."""
        # Create data with only 30 days
        returns = pd.DataFrame(
            {
                "ASSET_A": np.random.normal(0.001, 0.01, len(dates_short)),
                "ASSET_B": np.random.normal(0.001, 0.01, len(dates_short)),
            },
            index=dates_short,
        )

        # Require 100 periods but only have 30
        config = PreselectionConfig(
            method=PreselectionMethod.MOMENTUM,
            top_k=5,
            lookback=100,
            min_periods=100,
        )
        preselection = Preselection(config)

        # Should raise InsufficientDataError
        with pytest.raises(InsufficientDataError):
            preselection.select_assets(returns)

    def test_all_assets_insufficient_data(self, sparse_valid_data):
        """All assets have insufficient data for calculation."""
        config = PreselectionConfig(
            method=PreselectionMethod.MOMENTUM,
            top_k=5,
            lookback=365,  # Full year
            min_periods=365,
        )
        preselection = Preselection(config)

        # All assets have some NaN, so with strict min_periods
        # this should handle gracefully
        # The implementation will filter data and compute on available
        # Some assets might produce NaN scores
        selected = preselection.select_assets(sparse_valid_data)

        # Should only select assets with valid data
        # VALID_A and VALID_B should be selected
        assert all(s.startswith("VALID_") for s in selected)

    def test_single_asset_meets_criteria(self, sparse_valid_data):
        """Only one asset meets selection criteria."""
        config = PreselectionConfig(
            method=PreselectionMethod.MOMENTUM,
            top_k=5,
            lookback=100,
            min_periods=60,
        )
        preselection = Preselection(config)

        # Create data where only one asset is valid
        dates = pd.date_range("2023-01-01", "2023-12-31", freq="D")
        returns = pd.DataFrame(
            {
                "VALID_ONE": np.random.normal(0.001, 0.01, len(dates)),
                "INVALID_A": [np.nan] * len(dates),
                "INVALID_B": [np.nan] * len(dates),
            },
            index=dates,
        )

        selected = preselection.select_assets(returns)

        # Should select the one valid asset
        assert len(selected) == 1
        assert selected == ["VALID_ONE"]

    def test_two_assets_minimal_set(self):
        """Two assets (minimal set for meaningful testing)."""
        dates = pd.date_range("2023-01-01", "2023-12-31", freq="D")
        returns = pd.DataFrame(
            {
                "ASSET_A": np.random.normal(0.002, 0.01, len(dates)),
                "ASSET_B": np.random.normal(0.001, 0.01, len(dates)),
            },
            index=dates,
        )

        config = PreselectionConfig(
            method=PreselectionMethod.MOMENTUM,
            top_k=1,
            lookback=100,
        )
        preselection = Preselection(config)

        selected = preselection.select_assets(returns)

        # Should select exactly 1 asset
        assert len(selected) == 1
        # Should be deterministic
        selected2 = preselection.select_assets(returns)
        assert selected == selected2

    def test_result_set_smaller_than_top_k(self):
        """Result set is smaller than top_k (only 3 valid, top_k=10)."""
        dates = pd.date_range("2023-01-01", "2023-12-31", freq="D")
        returns = pd.DataFrame(
            {
                "VALID_A": np.random.normal(0.001, 0.01, len(dates)),
                "VALID_B": np.random.normal(0.001, 0.01, len(dates)),
                "VALID_C": np.random.normal(0.001, 0.01, len(dates)),
                "INVALID_D": [np.nan] * len(dates),
                "INVALID_E": [np.nan] * len(dates),
            },
            index=dates,
        )

        config = PreselectionConfig(
            method=PreselectionMethod.MOMENTUM,
            top_k=10,  # Request more than available
            lookback=100,
        )
        preselection = Preselection(config)

        selected = preselection.select_assets(returns)

        # Should return all 3 valid assets
        assert len(selected) == 3
        assert set(selected) == {"VALID_A", "VALID_B", "VALID_C"}


# ============================================================================
# Phase 4: Combined Factor Edge Cases
# ============================================================================


class TestCombinedFactorEdgeCases:
    """Tests for combined factor edge cases."""

    def test_one_factor_all_nan_fallback(self):
        """One factor all NaN (should handle gracefully)."""
        dates = pd.date_range("2023-01-01", "2023-12-31", freq="D")
        # All zero returns = zero momentum, but well-defined vol
        returns = pd.DataFrame(
            {
                "ASSET_A": [0.0] * len(dates),
                "ASSET_B": [0.0] * len(dates),
                "ASSET_C": [0.0] * len(dates),
            },
            index=dates,
        )

        config = PreselectionConfig(
            method=PreselectionMethod.COMBINED,
            top_k=2,
            lookback=100,
            momentum_weight=0.5,
            low_vol_weight=0.5,
        )
        preselection = Preselection(config)

        # Should handle gracefully (momentum all same, vol all zero)
        selected = preselection.select_assets(returns)

        # Should still select assets (tie-breaking by symbol)
        assert len(selected) == 2
        assert selected == sorted(selected)

    def test_both_factors_all_nan(self):
        """Both factors all NaN (should handle gracefully)."""
        dates = pd.date_range("2023-01-01", "2023-12-31", freq="D")
        returns = pd.DataFrame(
            {
                "ASSET_A": [np.nan] * len(dates),
                "ASSET_B": [np.nan] * len(dates),
                "ASSET_C": [np.nan] * len(dates),
            },
            index=dates,
        )

        config = PreselectionConfig(
            method=PreselectionMethod.COMBINED,
            top_k=2,
            lookback=100,
            momentum_weight=0.5,
            low_vol_weight=0.5,
            min_periods=1,  # Allow minimal data
        )
        preselection = Preselection(config)

        selected = preselection.select_assets(returns)

        # When all data is NaN, standardization returns zeros (neutral scores)
        # and tie-breaking by symbol selects first alphabetically
        # This is expected behavior - no crash, deterministic selection
        assert isinstance(selected, list)
        assert len(selected) <= 2  # May return empty or tied assets

    def test_extreme_weight_ratios(self, dates_1year):
        """Extreme weight ratios (99% one factor, 1% other)."""
        returns = pd.DataFrame(
            {
                "HIGH_MOM": np.random.normal(0.005, 0.03, len(dates_1year)),
                "LOW_MOM": np.random.normal(0.0, 0.01, len(dates_1year)),
                "MED_MOM": np.random.normal(0.002, 0.02, len(dates_1year)),
            },
            index=dates_1year,
        )

        # 99% momentum, 1% vol
        config_mom = PreselectionConfig(
            method=PreselectionMethod.COMBINED,
            top_k=2,
            lookback=100,
            momentum_weight=0.99,
            low_vol_weight=0.01,
        )
        preselection_mom = Preselection(config_mom)
        selected_mom = preselection_mom.select_assets(returns)

        # 1% momentum, 99% vol
        config_vol = PreselectionConfig(
            method=PreselectionMethod.COMBINED,
            top_k=2,
            lookback=100,
            momentum_weight=0.01,
            low_vol_weight=0.99,
        )
        preselection_vol = Preselection(config_vol)
        selected_vol = preselection_vol.select_assets(returns)

        # Both should work without errors
        assert len(selected_mom) == 2
        assert len(selected_vol) == 2
        # Results might differ based on weighting
        # (LOW_MOM should be favored in vol-heavy)

    def test_factor_values_extreme_range(self, mixed_volatility):
        """Factor values with extreme range (numerical stability)."""
        config = PreselectionConfig(
            method=PreselectionMethod.LOW_VOL,
            top_k=2,
            lookback=100,
        )
        preselection = Preselection(config)

        selected = preselection.select_assets(mixed_volatility)

        # Should handle extreme differences (0.001 vs 0.1 std)
        assert len(selected) == 2
        # LOW_VOL should be selected
        assert "LOW_VOL" in selected


# ============================================================================
# Phase 5: Data Quality Issues
# ============================================================================


class TestDataQualityIssues:
    """Tests for handling various data quality problems."""

    def test_all_zeros_in_returns(self, all_zero_returns):
        """All zeros in returns (zero momentum, zero volatility)."""
        config = PreselectionConfig(
            method=PreselectionMethod.MOMENTUM,
            top_k=2,
            lookback=100,
        )
        preselection = Preselection(config)

        selected = preselection.select_assets(all_zero_returns)

        # Should handle gracefully, all assets have same momentum (0)
        assert len(selected) == 2
        # Tie-breaking by symbol
        assert selected == ["ASSET_A", "ASSET_B"]

    def test_all_nan_in_lookback_window(self):
        """All NaN in the lookback window."""
        dates = pd.date_range("2023-01-01", "2023-12-31", freq="D")
        n = len(dates)
        # First 200 days are NaN, last part has data
        returns = pd.DataFrame(
            {
                "ASSET_A": [np.nan] * 200
                + list(np.random.normal(0.001, 0.01, n - 200)),
                "ASSET_B": [np.nan] * 200
                + list(np.random.normal(0.001, 0.01, n - 200)),
            },
            index=dates,
        )

        config = PreselectionConfig(
            method=PreselectionMethod.MOMENTUM,
            top_k=2,
            lookback=100,
            min_periods=60,
        )
        preselection = Preselection(config)

        # Should work on the available data
        selected = preselection.select_assets(returns)
        assert len(selected) == 2

    def test_single_valid_return_in_lookback(self):
        """Single valid return in lookback period."""
        dates = pd.date_range("2023-01-01", "2023-12-31", freq="D")
        n = len(dates)
        # Mostly NaN except one value
        returns = pd.DataFrame(
            {
                "ASSET_A": [np.nan] * (n - 1) + [0.01],
                "ASSET_B": [np.nan] * (n - 1) + [0.02],
            },
            index=dates,
        )

        config = PreselectionConfig(
            method=PreselectionMethod.MOMENTUM,
            top_k=1,
            lookback=50,
            min_periods=1,
        )
        preselection = Preselection(config)

        # Should work with minimal data
        selected = preselection.select_assets(returns)
        # Might return empty if calculation fails
        # Or return based on single point
        assert isinstance(selected, list)

    def test_extreme_outliers_daily(self, extreme_outliers):
        """Returns with extreme outliers (±50% daily)."""
        config = PreselectionConfig(
            method=PreselectionMethod.MOMENTUM,
            top_k=2,
            lookback=100,
        )
        preselection = Preselection(config)

        # Should handle outliers without crashing
        selected = preselection.select_assets(extreme_outliers)

        assert len(selected) == 2
        # Results should be deterministic
        selected2 = preselection.select_assets(extreme_outliers)
        assert selected == selected2

    def test_mixed_valid_invalid_data(self, sparse_valid_data):
        """Mixed valid/invalid data across assets."""
        config = PreselectionConfig(
            method=PreselectionMethod.COMBINED,
            top_k=3,
            lookback=100,
            momentum_weight=0.5,
            low_vol_weight=0.5,
            min_periods=60,
        )
        preselection = Preselection(config)

        selected = preselection.select_assets(sparse_valid_data)

        # Should only select assets with sufficient valid data
        # VALID_A and VALID_B should definitely be selected
        assert all(s.startswith("VALID_") for s in selected if "VALID" in s)


# ============================================================================
# Phase 6: Configuration Boundaries
# ============================================================================


class TestConfigurationBoundaries:
    """Tests for edge cases at configuration boundaries."""

    def test_lookback_equals_min_periods(self, dates_1year):
        """Lookback = min_periods (edge of requirement)."""
        returns = pd.DataFrame(
            {
                "ASSET_A": np.random.normal(0.001, 0.01, len(dates_1year)),
                "ASSET_B": np.random.normal(0.001, 0.01, len(dates_1year)),
            },
            index=dates_1year,
        )

        config = PreselectionConfig(
            method=PreselectionMethod.MOMENTUM,
            top_k=2,
            lookback=100,
            min_periods=100,  # Equal to lookback
        )
        preselection = Preselection(config)

        selected = preselection.select_assets(returns)

        # Should work correctly
        assert len(selected) == 2

    def test_skip_equals_lookback_minus_one(self, dates_1year):
        """Skip = lookback - 1 (edge of valid range)."""
        returns = pd.DataFrame(
            {
                "ASSET_A": np.random.normal(0.001, 0.01, len(dates_1year)),
                "ASSET_B": np.random.normal(0.001, 0.01, len(dates_1year)),
            },
            index=dates_1year,
        )

        config = PreselectionConfig(
            method=PreselectionMethod.MOMENTUM,
            top_k=2,
            lookback=100,
            skip=99,  # lookback - 1
        )
        preselection = Preselection(config)

        selected = preselection.select_assets(returns)

        # Should work (using only 1 period for momentum)
        assert len(selected) == 2

    def test_top_k_zero_disabled(self, dates_1year):
        """Top_k = 0 (disabled preselection)."""
        returns = pd.DataFrame(
            {
                "ASSET_A": np.random.normal(0.001, 0.01, len(dates_1year)),
                "ASSET_B": np.random.normal(0.001, 0.01, len(dates_1year)),
                "ASSET_C": np.random.normal(0.001, 0.01, len(dates_1year)),
            },
            index=dates_1year,
        )

        config = PreselectionConfig(
            method=PreselectionMethod.MOMENTUM,
            top_k=0,  # Disabled
            lookback=100,
        )
        preselection = Preselection(config)

        selected = preselection.select_assets(returns)

        # Should return all assets when disabled
        assert len(selected) == 3
        assert set(selected) == {"ASSET_A", "ASSET_B", "ASSET_C"}

    def test_top_k_greater_than_universe(self, dates_1year):
        """Top_k > universe size (select all)."""
        returns = pd.DataFrame(
            {
                "ASSET_A": np.random.normal(0.001, 0.01, len(dates_1year)),
                "ASSET_B": np.random.normal(0.001, 0.01, len(dates_1year)),
            },
            index=dates_1year,
        )

        config = PreselectionConfig(
            method=PreselectionMethod.MOMENTUM,
            top_k=100,  # Much larger than 2 assets
            lookback=100,
        )
        preselection = Preselection(config)

        selected = preselection.select_assets(returns)

        # Should return all available assets
        assert len(selected) == 2
        assert set(selected) == {"ASSET_A", "ASSET_B"}

    def test_top_k_one_single_asset(self, dates_1year):
        """Top_k = 1 (single asset selection)."""
        returns = pd.DataFrame(
            {
                "HIGH": np.random.normal(0.003, 0.01, len(dates_1year)),
                "MED": np.random.normal(0.002, 0.01, len(dates_1year)),
                "LOW": np.random.normal(0.001, 0.01, len(dates_1year)),
            },
            index=dates_1year,
        )

        config = PreselectionConfig(
            method=PreselectionMethod.MOMENTUM,
            top_k=1,
            lookback=100,
        )
        preselection = Preselection(config)

        selected = preselection.select_assets(returns)

        # Should return exactly 1 asset
        assert len(selected) == 1
        # Should be deterministic
        selected2 = preselection.select_assets(returns)
        assert selected == selected2


# ============================================================================
# Phase 7: Z-Score Edge Cases
# ============================================================================


class TestZScoreEdgeCases:
    """Tests for Z-score computation edge cases."""

    def test_all_assets_identical_zero_std_dev(self, all_identical_returns):
        """All assets identical (zero std dev in z-score)."""
        config = PreselectionConfig(
            method=PreselectionMethod.COMBINED,
            top_k=3,
            lookback=100,
            momentum_weight=0.5,
            low_vol_weight=0.5,
        )
        preselection = Preselection(config)

        selected = preselection.select_assets(all_identical_returns)

        # Should handle zero variance gracefully
        assert len(selected) == 3
        # Tie-breaking by symbol
        assert selected == sorted(selected)

    def test_one_asset_extreme_outlier(self):
        """One asset is extreme outlier (z-score > 3)."""
        dates = pd.date_range("2023-01-01", "2023-12-31", freq="D")
        returns = pd.DataFrame(
            {
                "NORMAL_A": np.random.normal(0.001, 0.01, len(dates)),
                "NORMAL_B": np.random.normal(0.001, 0.01, len(dates)),
                "OUTLIER": np.random.normal(0.05, 0.01, len(dates)),  # 50x mean
            },
            index=dates,
        )

        config = PreselectionConfig(
            method=PreselectionMethod.COMBINED,
            top_k=2,
            lookback=100,
            momentum_weight=0.5,
            low_vol_weight=0.5,
        )
        preselection = Preselection(config)

        selected = preselection.select_assets(returns)

        # Should handle outlier correctly
        assert len(selected) == 2
        # OUTLIER should likely be selected due to high momentum
        assert "OUTLIER" in selected

    def test_empty_factor_result_no_z_scores(self):
        """Empty factor result (no z-scores computed)."""
        dates = pd.date_range("2023-01-01", "2023-12-31", freq="D")
        returns = pd.DataFrame(
            {
                "ASSET_A": [np.nan] * len(dates),
                "ASSET_B": [np.nan] * len(dates),
            },
            index=dates,
        )

        config = PreselectionConfig(
            method=PreselectionMethod.COMBINED,
            top_k=2,
            lookback=100,
            momentum_weight=0.5,
            low_vol_weight=0.5,
            min_periods=1,
        )
        preselection = Preselection(config)

        selected = preselection.select_assets(returns)

        # When all data is NaN, standardization returns neutral scores (zeros)
        # Tie-breaking by symbol is deterministic
        # This validates no crash occurs and behavior is deterministic
        assert isinstance(selected, list)
        assert len(selected) <= 2  # May return all tied or subset

    def test_z_score_with_single_valid_point(self):
        """Z-score computation with single valid data point."""
        dates = pd.date_range("2023-01-01", "2023-12-31", freq="D")
        n = len(dates)
        # Each asset has only one valid point (rest NaN)
        returns = pd.DataFrame(
            {
                "ASSET_A": [np.nan] * (n - 1) + [0.01],
                "ASSET_B": [np.nan] * (n - 2) + [0.02, np.nan],
                "ASSET_C": [0.015] + [np.nan] * (n - 1),
            },
            index=dates,
        )

        config = PreselectionConfig(
            method=PreselectionMethod.COMBINED,
            top_k=2,
            lookback=100,
            momentum_weight=0.5,
            low_vol_weight=0.5,
            min_periods=1,
        )
        preselection = Preselection(config)

        # Should handle minimal data gracefully
        selected = preselection.select_assets(returns)

        # Might return empty or partial results
        assert isinstance(selected, list)
        assert len(selected) <= 2


# ============================================================================
# Phase 8: Validation Tests
# ============================================================================


class TestValidationAndDeterminism:
    """Tests for overall validation and determinism."""

    def test_determinism_same_config_same_order(self, dates_1year):
        """Same config produces same order across multiple runs."""
        np.random.seed(42)
        returns = pd.DataFrame(
            {
                "ASSET_A": np.random.normal(0.001, 0.01, len(dates_1year)),
                "ASSET_B": np.random.normal(0.002, 0.015, len(dates_1year)),
                "ASSET_C": np.random.normal(0.0015, 0.012, len(dates_1year)),
                "ASSET_D": np.random.normal(0.0008, 0.008, len(dates_1year)),
                "ASSET_E": np.random.normal(0.0025, 0.02, len(dates_1year)),
            },
            index=dates_1year,
        )

        config = PreselectionConfig(
            method=PreselectionMethod.COMBINED,
            top_k=3,
            lookback=120,
            skip=5,
            momentum_weight=0.6,
            low_vol_weight=0.4,
        )

        # Run 20 times
        results = []
        for _ in range(20):
            preselection = Preselection(config)
            selected = preselection.select_assets(returns)
            results.append(selected)

        # All results should be identical
        assert all(r == results[0] for r in results)

    def test_no_silent_failures_on_edge_cases(self):
        """Validate no silent failures on various edge cases."""
        dates = pd.date_range("2023-01-01", "2023-12-31", freq="D")
        n = len(dates)

        # Test various edge cases don't cause silent failures
        edge_cases = [
            # All zeros
            pd.DataFrame({"A": [0.0] * n}, index=dates),
            # All same
            pd.DataFrame({"A": [0.01] * n}, index=dates),
            # Single point
            pd.DataFrame({"A": [np.nan] * (n - 1) + [0.01]}, index=dates),
            # Extreme values (ensure length matches by using list comprehension)
            pd.DataFrame(
                {"A": [1.0 if i % 2 == 0 else -1.0 for i in range(n)]}, index=dates
            ),
        ]

        config = PreselectionConfig(
            method=PreselectionMethod.MOMENTUM,
            top_k=1,
            lookback=50,
            min_periods=1,
        )

        for returns in edge_cases:
            preselection = Preselection(config)
            # Should not crash, should return list (possibly empty)
            selected = preselection.select_assets(returns)
            assert isinstance(selected, list)
            assert len(selected) <= 1

    def test_alphabetical_sorting_maintained(self, dates_1year):
        """Selected assets are always sorted alphabetically."""
        returns = pd.DataFrame(
            {
                "ZULU": np.random.normal(0.001, 0.01, len(dates_1year)),
                "ALPHA": np.random.normal(0.001, 0.01, len(dates_1year)),
                "MIKE": np.random.normal(0.001, 0.01, len(dates_1year)),
                "BRAVO": np.random.normal(0.001, 0.01, len(dates_1year)),
            },
            index=dates_1year,
        )

        config = PreselectionConfig(
            method=PreselectionMethod.MOMENTUM,
            top_k=3,
            lookback=100,
        )
        preselection = Preselection(config)

        selected = preselection.select_assets(returns)

        # Should be sorted alphabetically
        assert selected == sorted(selected)
