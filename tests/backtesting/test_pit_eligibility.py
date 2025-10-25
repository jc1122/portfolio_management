"""Tests for point-in-time eligibility computation."""

from datetime import timedelta

import numpy as np
import pandas as pd
import pytest
pytestmark = pytest.mark.integration

from portfolio_management.backtesting.eligibility import (
    compute_pit_eligibility,
    detect_delistings,
    get_asset_history_stats,
)


@pytest.fixture
def sample_returns_with_late_starter():
    """Create returns with one asset starting later than others."""
    dates = pd.date_range("2020-01-01", periods=500, freq="D")

    rng = np.random.default_rng(42)

    # Asset A: Full history
    returns_a = rng.normal(0.0001, 0.01, len(dates))

    # Asset B: Full history
    returns_b = rng.normal(0.00015, 0.012, len(dates))

    # Asset C: Starts after 300 days (late starter)
    returns_c = np.full(len(dates), np.nan)
    returns_c[300:] = rng.normal(0.0001, 0.011, len(dates) - 300)

    df = pd.DataFrame(
        {
            "A": returns_a,
            "B": returns_b,
            "C": returns_c,
        },
        index=dates,
    )

    return df


@pytest.fixture
def sample_returns_with_delisting():
    """Create returns with one asset delisting mid-period."""
    dates = pd.date_range("2020-01-01", periods=500, freq="D")

    rng = np.random.default_rng(43)

    # Asset A: Full history
    returns_a = rng.normal(0.0001, 0.01, len(dates))

    # Asset B: Delists after 300 days
    returns_b = rng.normal(0.00015, 0.012, len(dates))
    returns_b[300:] = np.nan

    # Asset C: Full history
    returns_c = rng.normal(0.0001, 0.011, len(dates))

    df = pd.DataFrame(
        {
            "A": returns_a,
            "B": returns_b,
            "C": returns_c,
        },
        index=dates,
    )

    return df


@pytest.fixture
def sample_returns_with_gaps():
    """Create returns with gaps in the middle."""
    dates = pd.date_range("2020-01-01", periods=500, freq="D")

    rng = np.random.default_rng(44)

    # Asset A: Full history
    returns_a = rng.normal(0.0001, 0.01, len(dates))

    # Asset B: Has a 30-day gap in the middle
    returns_b = rng.normal(0.00015, 0.012, len(dates))
    returns_b[200:230] = np.nan

    df = pd.DataFrame(
        {
            "A": returns_a,
            "B": returns_b,
        },
        index=dates,
    )

    return df


class TestComputePitEligibility:
    """Tests for compute_pit_eligibility function."""

    def test_all_assets_eligible_with_sufficient_history(
        self, sample_returns_with_late_starter
    ):
        """Test that assets with sufficient history are eligible."""
        returns = sample_returns_with_late_starter

        # Check at day 400 (100 days after late starter begins)
        check_date = returns.index[400].date()

        eligible = compute_pit_eligibility(
            returns=returns,
            date=check_date,
            min_history_days=50,  # Lower threshold
            min_price_rows=50,
        )

        # All assets should be eligible
        assert eligible["A"]
        assert eligible["B"]
        assert eligible["C"]

    def test_late_starter_not_eligible_early(self, sample_returns_with_late_starter):
        """Test that late-starting asset is not eligible before it has enough history."""
        returns = sample_returns_with_late_starter

        # Check at day 320 (only 20 days after late starter begins)
        check_date = returns.index[320].date()

        eligible = compute_pit_eligibility(
            returns=returns,
            date=check_date,
            min_history_days=50,
            min_price_rows=50,
        )

        # A and B should be eligible, C should not
        assert eligible["A"]
        assert eligible["B"]
        assert not eligible["C"]

    def test_late_starter_becomes_eligible_later(
        self, sample_returns_with_late_starter
    ):
        """Test that late-starting asset becomes eligible once it has enough history."""
        returns = sample_returns_with_late_starter

        # Check at day 360 (60 days after late starter begins)
        check_date = returns.index[360].date()

        eligible = compute_pit_eligibility(
            returns=returns,
            date=check_date,
            min_history_days=50,
            min_price_rows=50,
        )

        # All assets should now be eligible
        assert eligible["A"]
        assert eligible["B"]
        assert eligible["C"]

    def test_no_assets_eligible_at_start(self, sample_returns_with_late_starter):
        """Test that no assets are eligible at the very start."""
        returns = sample_returns_with_late_starter

        # Check at day 10
        check_date = returns.index[10].date()

        eligible = compute_pit_eligibility(
            returns=returns,
            date=check_date,
            min_history_days=252,  # Need 1 year
            min_price_rows=252,
        )

        # No assets should be eligible yet
        assert not eligible["A"]
        assert not eligible["B"]
        assert not eligible["C"]

    def test_eligibility_respects_min_rows(self, sample_returns_with_gaps):
        """Test that eligibility considers minimum row count."""
        returns = sample_returns_with_gaps

        # Check at day 250 (after the gap)
        check_date = returns.index[250].date()

        # Asset B has a gap, so fewer rows
        eligible = compute_pit_eligibility(
            returns=returns,
            date=check_date,
            min_history_days=100,  # Days threshold met
            min_price_rows=240,  # But row count matters
        )

        # A should be eligible (full 251 rows)
        # B might not be (only 221 rows due to gap)
        assert eligible["A"]
        assert not eligible["B"]

    def test_eligibility_with_no_data(self):
        """Test eligibility computation with no data."""
        returns = pd.DataFrame(
            {"A": [np.nan, np.nan], "B": [np.nan, np.nan]},
            index=pd.date_range("2020-01-01", periods=2, freq="D"),
        )

        check_date = returns.index[1].date()

        eligible = compute_pit_eligibility(
            returns=returns,
            date=check_date,
            min_history_days=1,
            min_price_rows=1,
        )

        # No assets should be eligible (no valid data)
        assert not eligible["A"]
        assert not eligible["B"]

    def test_eligibility_before_any_data(self, sample_returns_with_late_starter):
        """Test eligibility check before any data exists."""
        returns = sample_returns_with_late_starter

        # Check before the first date
        check_date = returns.index[0].date() - timedelta(days=1)

        eligible = compute_pit_eligibility(
            returns=returns,
            date=check_date,
            min_history_days=1,
            min_price_rows=1,
        )

        # Nothing should be eligible
        assert not eligible["A"]
        assert not eligible["B"]
        assert not eligible["C"]


class TestDetectDelistings:
    """Tests for detect_delistings function."""

    def test_detect_delisted_asset(self, sample_returns_with_delisting):
        """Test detection of delisted asset."""
        returns = sample_returns_with_delisting

        # Check at day 350 (50 days after delisting)
        check_date = returns.index[350].date()

        delistings = detect_delistings(
            returns=returns,
            current_date=check_date,
            lookforward_days=30,
        )

        # Asset B should be detected as delisted
        assert "B" in delistings
        # Other assets should not be delisted
        assert "A" not in delistings
        assert "C" not in delistings

    def test_no_delistings_when_all_active(self, sample_returns_with_late_starter):
        """Test that no delistings are detected when all assets are active."""
        returns = sample_returns_with_late_starter

        # Check at day 400 (all assets active)
        check_date = returns.index[400].date()

        delistings = detect_delistings(
            returns=returns,
            current_date=check_date,
            lookforward_days=30,
        )

        # No delistings should be detected
        assert len(delistings) == 0

    def test_late_starter_not_detected_as_delisting(
        self, sample_returns_with_late_starter
    ):
        """Test that late-starting assets are not detected as delistings."""
        returns = sample_returns_with_late_starter

        # Check before late starter begins
        check_date = returns.index[250].date()

        delistings = detect_delistings(
            returns=returns,
            current_date=check_date,
            lookforward_days=30,
        )

        # Asset C should not be detected as delisted (it hasn't started yet)
        assert "C" not in delistings

    def test_delisting_last_date_correct(self, sample_returns_with_delisting):
        """Test that the last date of delisted asset is correct."""
        returns = sample_returns_with_delisting

        # Check at day 350
        check_date = returns.index[350].date()

        delistings = detect_delistings(
            returns=returns,
            current_date=check_date,
            lookforward_days=30,
        )

        # Asset B delisted at day 299 (last valid observation)
        expected_last_date = returns.index[299].date()
        assert delistings["B"] == expected_last_date


class TestGetAssetHistoryStats:
    """Tests for get_asset_history_stats function."""

    def test_stats_for_full_history_assets(self, sample_returns_with_late_starter):
        """Test statistics for assets with full history."""
        returns = sample_returns_with_late_starter

        # Check at day 400
        check_date = returns.index[400].date()

        stats = get_asset_history_stats(
            returns=returns,
            date=check_date,
        )

        # Should have stats for all 3 assets
        assert len(stats) == 3
        assert set(stats["ticker"]) == {"A", "B", "C"}

        # Asset A should have ~401 rows
        stats_a = stats[stats["ticker"] == "A"].iloc[0]
        assert stats_a["total_rows"] == 401
        assert stats_a["first_valid_date"] == returns.index[0].date()

    def test_stats_for_late_starter(self, sample_returns_with_late_starter):
        """Test statistics for late-starting asset."""
        returns = sample_returns_with_late_starter

        # Check at day 400
        check_date = returns.index[400].date()

        stats = get_asset_history_stats(
            returns=returns,
            date=check_date,
        )

        # Asset C should have ~101 rows (started at day 300)
        stats_c = stats[stats["ticker"] == "C"].iloc[0]
        assert stats_c["total_rows"] == 101
        assert stats_c["first_valid_date"] == returns.index[300].date()
        assert stats_c["days_since_first"] == 100

    def test_stats_for_delisted_asset(self, sample_returns_with_delisting):
        """Test statistics for delisted asset."""
        returns = sample_returns_with_delisting

        # Check at day 400 (after delisting)
        check_date = returns.index[400].date()

        stats = get_asset_history_stats(
            returns=returns,
            date=check_date,
        )

        # Asset B should show last valid date at day 299
        stats_b = stats[stats["ticker"] == "B"].iloc[0]
        assert stats_b["last_valid_date"] == returns.index[299].date()
        assert stats_b["total_rows"] == 300  # Days 0-299

    def test_stats_with_no_data(self):
        """Test statistics when asset has no valid data."""
        returns = pd.DataFrame(
            {"A": [1.0, 2.0], "B": [np.nan, np.nan]},
            index=pd.date_range("2020-01-01", periods=2, freq="D"),
        )

        check_date = returns.index[1].date()

        stats = get_asset_history_stats(
            returns=returns,
            date=check_date,
        )

        # Asset B should have zero stats
        stats_b = stats[stats["ticker"] == "B"].iloc[0]
        assert stats_b["total_rows"] == 0
        assert pd.isna(stats_b["first_valid_date"])
        assert stats_b["days_since_first"] == 0

    def test_coverage_percentage(self, sample_returns_with_gaps):
        """Test coverage percentage calculation."""
        returns = sample_returns_with_gaps

        # Check at day 250
        check_date = returns.index[250].date()

        stats = get_asset_history_stats(
            returns=returns,
            date=check_date,
        )

        # Asset A should have 100% coverage
        stats_a = stats[stats["ticker"] == "A"].iloc[0]
        assert stats_a["coverage_pct"] == pytest.approx(100.0, rel=1e-2)

        # Asset B should have less coverage due to gap
        stats_b = stats[stats["ticker"] == "B"].iloc[0]
        # 30-day gap out of 251 days = ~88% coverage
        expected_coverage = (251 - 30) / 251 * 100
        assert stats_b["coverage_pct"] == pytest.approx(expected_coverage, rel=1e-2)
