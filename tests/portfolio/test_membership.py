"""Tests for membership policy module.

This module tests the membership policy logic that controls asset membership
changes during rebalancing.
"""

from __future__ import annotations

import pandas as pd
import pytest

from portfolio_management.portfolio.membership import (
    MembershipPolicy,
    apply_membership_policy,
)


class TestMembershipPolicy:
    """Tests for MembershipPolicy dataclass."""

    def test_default_policy(self) -> None:
        """Test default policy creation."""
        policy = MembershipPolicy.default()

        assert policy.enabled is True
        assert policy.min_holding_periods == 3
        assert policy.max_turnover == 0.30
        assert policy.max_new_assets == 5
        assert policy.max_removed_assets == 5
        assert policy.buffer_rank is None  # Should be set based on top_k

    def test_disabled_policy(self) -> None:
        """Test disabled policy creation."""
        policy = MembershipPolicy.disabled()

        assert policy.enabled is False
        assert policy.buffer_rank is None
        assert policy.min_holding_periods is None

    def test_custom_policy(self) -> None:
        """Test custom policy creation."""
        policy = MembershipPolicy(
            buffer_rank=50,
            min_holding_periods=2,
            max_turnover=0.25,
            max_new_assets=3,
            max_removed_assets=3,
        )

        assert policy.enabled is True
        assert policy.buffer_rank == 50
        assert policy.min_holding_periods == 2
        assert policy.max_turnover == 0.25
        assert policy.max_new_assets == 3
        assert policy.max_removed_assets == 3

    def test_validate_buffer_rank(self) -> None:
        """Test buffer_rank validation."""
        policy = MembershipPolicy(buffer_rank=-1)

        with pytest.raises(ValueError, match="buffer_rank must be >= 1"):
            policy.validate()

    def test_validate_min_holding_periods(self) -> None:
        """Test min_holding_periods validation."""
        policy = MembershipPolicy(min_holding_periods=-1)

        with pytest.raises(
            ValueError, match="min_holding_periods must be non-negative"
        ):
            policy.validate()

    def test_validate_max_turnover_low(self) -> None:
        """Test max_turnover validation - too low."""
        policy = MembershipPolicy(max_turnover=-0.1)

        with pytest.raises(ValueError, match="max_turnover must be in"):
            policy.validate()

    def test_validate_max_turnover_high(self) -> None:
        """Test max_turnover validation - too high."""
        policy = MembershipPolicy(max_turnover=1.5)

        with pytest.raises(ValueError, match="max_turnover must be in"):
            policy.validate()

    def test_validate_max_new_assets(self) -> None:
        """Test max_new_assets validation."""
        policy = MembershipPolicy(max_new_assets=-1)

        with pytest.raises(ValueError, match="max_new_assets must be non-negative"):
            policy.validate()

    def test_validate_max_removed_assets(self) -> None:
        """Test max_removed_assets validation."""
        policy = MembershipPolicy(max_removed_assets=-1)

        with pytest.raises(ValueError, match="max_removed_assets must be non-negative"):
            policy.validate()

    def test_validate_success(self) -> None:
        """Test successful validation."""
        policy = MembershipPolicy(
            buffer_rank=50,
            min_holding_periods=3,
            max_turnover=0.30,
            max_new_assets=5,
            max_removed_assets=5,
        )

        # Should not raise
        policy.validate()


class TestApplyMembershipPolicy:
    """Tests for apply_membership_policy function."""

    def test_disabled_policy_returns_top_k(self) -> None:
        """Test that disabled policy returns top_k without modifications."""
        current_holdings = ["AAPL", "MSFT", "GOOGL"]
        ranks = pd.Series(
            {
                "AAPL": 1,
                "MSFT": 2,
                "AMZN": 3,
                "TSLA": 4,
                "GOOGL": 45,
                "META": 5,
                "NVDA": 6,
            }
        )

        policy = MembershipPolicy.disabled()

        result = apply_membership_policy(
            current_holdings=current_holdings,
            preselected_ranks=ranks,
            policy=policy,
            top_k=5,
        )

        # Should return exactly top 5
        assert len(result) == 5
        assert set(result) == {"AAPL", "MSFT", "AMZN", "TSLA", "META"}

    def test_no_policy_constraints_returns_top_k(self) -> None:
        """Test that policy with no constraints returns top_k."""
        current_holdings = ["AAPL", "MSFT", "GOOGL"]
        ranks = pd.Series(
            {
                "AAPL": 1,
                "MSFT": 2,
                "AMZN": 3,
                "TSLA": 4,
                "GOOGL": 45,
                "META": 5,
            }
        )

        policy = MembershipPolicy(enabled=True)  # No constraints set

        result = apply_membership_policy(
            current_holdings=current_holdings,
            preselected_ranks=ranks,
            policy=policy,
            top_k=5,
        )

        # Should return exactly top 5
        assert len(result) == 5
        assert set(result) == {"AAPL", "MSFT", "AMZN", "TSLA", "META"}

    def test_buffer_rank_keeps_existing_holdings(self) -> None:
        """Test that buffer_rank keeps existing holdings within buffer."""
        current_holdings = ["AAPL", "MSFT", "GOOGL"]
        ranks = pd.Series(
            {
                "AAPL": 1,
                "MSFT": 2,
                "AMZN": 3,
                "TSLA": 4,
                "META": 5,
                "GOOGL": 35,  # Outside top 5 but within buffer
                "NVDA": 6,
            }
        )

        policy = MembershipPolicy(buffer_rank=40)

        result = apply_membership_policy(
            current_holdings=current_holdings,
            preselected_ranks=ranks,
            policy=policy,
            top_k=5,
        )

        # Should include GOOGL due to buffer
        assert "GOOGL" in result
        assert "AAPL" in result
        assert "MSFT" in result

    def test_buffer_rank_removes_holdings_outside_buffer(self) -> None:
        """Test that buffer_rank removes holdings outside buffer."""
        current_holdings = ["AAPL", "MSFT", "GOOGL"]
        ranks = pd.Series(
            {
                "AAPL": 1,
                "MSFT": 2,
                "AMZN": 3,
                "TSLA": 4,
                "META": 5,
                "GOOGL": 55,  # Outside buffer
                "NVDA": 6,
            }
        )

        policy = MembershipPolicy(buffer_rank=40)

        result = apply_membership_policy(
            current_holdings=current_holdings,
            preselected_ranks=ranks,
            policy=policy,
            top_k=5,
        )

        # Should not include GOOGL (outside buffer)
        assert "GOOGL" not in result
        assert len(result) == 5

    def test_min_holding_periods_protects_assets(self) -> None:
        """Test that min_holding_periods protects recently added assets."""
        current_holdings = ["AAPL", "MSFT", "GOOGL"]
        ranks = pd.Series(
            {
                "AAPL": 1,
                "MSFT": 2,
                "AMZN": 3,
                "TSLA": 4,
                "META": 5,
                "GOOGL": 55,  # Poor rank but recently added
                "NVDA": 6,
            }
        )
        holding_periods = {
            "AAPL": 10,
            "MSFT": 5,
            "GOOGL": 1,  # Recently added
        }

        policy = MembershipPolicy(min_holding_periods=3)

        result = apply_membership_policy(
            current_holdings=current_holdings,
            preselected_ranks=ranks,
            policy=policy,
            holding_periods=holding_periods,
            top_k=5,
        )

        # GOOGL should be kept despite poor rank (held < 3 periods)
        assert "GOOGL" in result

    def test_min_holding_periods_requires_holding_periods(self) -> None:
        """Test that min_holding_periods requires holding_periods dict."""
        current_holdings = ["AAPL", "MSFT"]
        ranks = pd.Series({"AAPL": 1, "MSFT": 2, "AMZN": 3})

        policy = MembershipPolicy(min_holding_periods=3)

        with pytest.raises(ValueError, match="holding_periods required"):
            apply_membership_policy(
                current_holdings=current_holdings,
                preselected_ranks=ranks,
                policy=policy,
                top_k=5,
            )

    def test_max_new_assets_limits_additions(self) -> None:
        """Test that max_new_assets limits the number of new additions."""
        current_holdings = ["AAPL"]
        ranks = pd.Series(
            {
                "AAPL": 1,
                "MSFT": 2,
                "AMZN": 3,
                "TSLA": 4,
                "META": 5,
                "NVDA": 6,
                "NFLX": 7,
            }
        )

        policy = MembershipPolicy(max_new_assets=2)

        result = apply_membership_policy(
            current_holdings=current_holdings,
            preselected_ranks=ranks,
            policy=policy,
            top_k=5,
        )

        # Should have 1 existing + 2 new = 3 total (not 5)
        assert len(result) == 3
        assert "AAPL" in result
        # Best 2 new assets: MSFT (2) and AMZN (3)
        assert "MSFT" in result
        assert "AMZN" in result

    def test_max_removed_assets_limits_removals(self) -> None:
        """Test that max_removed_assets limits the number of removals."""
        current_holdings = ["A", "B", "C", "D", "E"]
        ranks = pd.Series(
            {
                "X": 1,
                "Y": 2,
                "Z": 3,
                "A": 50,
                "B": 51,
                "C": 52,
                "D": 53,
                "E": 54,
            }
        )

        policy = MembershipPolicy(max_removed_assets=2)

        result = apply_membership_policy(
            current_holdings=current_holdings,
            preselected_ranks=ranks,
            policy=policy,
            top_k=3,
        )

        # Should keep 3 of the old holdings (5 - 2 = 3)
        old_kept = [h for h in current_holdings if h in result]
        assert len(old_kept) == 3

        # Should add all top 3 new
        assert "X" in result
        assert "Y" in result
        assert "Z" in result

    def test_combined_policies(self) -> None:
        """Test multiple policies applied together."""
        current_holdings = ["AAPL", "MSFT", "GOOGL", "META"]
        ranks = pd.Series(
            {
                "AAPL": 1,  # Top rank, existing
                "AMZN": 2,  # Top rank, new
                "TSLA": 3,  # Top rank, new
                "NVDA": 4,  # New
                "NFLX": 5,  # New
                "MSFT": 25,  # Existing, within buffer
                "GOOGL": 55,  # Existing, poor rank, recently added
                "META": 60,  # Existing, poor rank, old
            }
        )
        holding_periods = {
            "AAPL": 10,
            "MSFT": 5,
            "GOOGL": 1,  # Recently added - should be protected
            "META": 10,  # Old holding - can be removed
        }

        policy = MembershipPolicy(
            buffer_rank=40,
            min_holding_periods=3,
            max_new_assets=2,
            max_removed_assets=1,
        )

        result = apply_membership_policy(
            current_holdings=current_holdings,
            preselected_ranks=ranks,
            policy=policy,
            holding_periods=holding_periods,
            top_k=4,
        )

        # AAPL: top 4, existing -> kept
        assert "AAPL" in result

        # MSFT: within buffer -> kept
        assert "MSFT" in result

        # GOOGL: protected by min_holding_periods -> kept
        assert "GOOGL" in result

        # Max 2 new assets: AMZN, TSLA (best ranked)
        new_assets = [a for a in result if a not in current_holdings]
        assert len(new_assets) == 2
        assert "AMZN" in result
        assert "TSLA" in result

    def test_deterministic_output(self) -> None:
        """Test that output is deterministic (sorted)."""
        current_holdings = ["B", "A", "C"]
        ranks = pd.Series({"A": 1, "B": 2, "C": 3, "D": 4, "E": 5})

        policy = MembershipPolicy(enabled=True)

        result1 = apply_membership_policy(
            current_holdings=current_holdings,
            preselected_ranks=ranks,
            policy=policy,
            top_k=5,
        )

        result2 = apply_membership_policy(
            current_holdings=current_holdings,
            preselected_ranks=ranks,
            policy=policy,
            top_k=5,
        )

        # Results should be identical and sorted
        assert result1 == result2
        assert result1 == sorted(result1)

    def test_empty_current_holdings(self) -> None:
        """Test behavior with no current holdings (initial portfolio)."""
        current_holdings = []
        ranks = pd.Series({"A": 1, "B": 2, "C": 3, "D": 4, "E": 5})

        policy = MembershipPolicy(
            buffer_rank=10,
            max_new_assets=3,
        )

        result = apply_membership_policy(
            current_holdings=current_holdings,
            preselected_ranks=ranks,
            policy=policy,
            top_k=5,
        )

        # Should respect max_new_assets since all are new
        assert len(result) == 3
        assert set(result) == {"A", "B", "C"}

    def test_turnover_warning_when_configured(self, caplog) -> None:
        """Test that max_turnover emits a warning (not yet implemented)."""
        import logging

        current_holdings = ["AAPL"]
        ranks = pd.Series({"AAPL": 1, "MSFT": 2})

        policy = MembershipPolicy(max_turnover=0.30)
        current_weights = {"AAPL": 1.0}
        candidate_weights = {"AAPL": 0.5, "MSFT": 0.5}

        with caplog.at_level(logging.WARNING):
            result = apply_membership_policy(
                current_holdings=current_holdings,
                preselected_ranks=ranks,
                policy=policy,
                top_k=2,
                current_weights=current_weights,
                candidate_weights=candidate_weights,
            )

        # Should warn that turnover is not enforced yet
        assert "max_turnover policy is configured but not yet enforced" in caplog.text

    def test_turnover_requires_weights(self) -> None:
        """Test that max_turnover requires weight dicts."""
        current_holdings = ["AAPL"]
        ranks = pd.Series({"AAPL": 1, "MSFT": 2})

        policy = MembershipPolicy(max_turnover=0.30)

        with pytest.raises(
            ValueError, match="current_weights and candidate_weights required"
        ):
            apply_membership_policy(
                current_holdings=current_holdings,
                preselected_ranks=ranks,
                policy=policy,
                top_k=2,
            )


class TestBufferZoneEdgeCases:
    """Edge case tests for buffer zone transitions and behavior."""

    def test_asset_enters_buffer_zone(self) -> None:
        """Test asset entering buffer zone (ranks 31-50 with top_k=30, buffer=50)."""
        current_holdings = ["AAPL", "MSFT"]
        # GOOGL at rank 35 - in buffer zone (outside top 30, within buffer 50)
        ranks = pd.Series({
            "AAPL": 1,
            "MSFT": 2,
            "AMZN": 3,
            "TSLA": 4,
            **{f"ASSET{i}": i + 4 for i in range(1, 27)},  # Fill ranks 5-30
            "GOOGL": 35,  # In buffer zone
            **{f"FILLER{i}": i + 35 for i in range(1, 16)},  # Ranks 36-50
        })

        policy = MembershipPolicy(buffer_rank=50)

        result = apply_membership_policy(
            current_holdings=current_holdings + ["GOOGL"],
            preselected_ranks=ranks,
            policy=policy,
            top_k=30,
        )

        # GOOGL should be kept even though it's outside top 30 (in buffer zone)
        assert "GOOGL" in result
        assert "AAPL" in result
        assert "MSFT" in result

    def test_asset_exits_buffer_zone(self) -> None:
        """Test asset exiting buffer zone (drops below buffer rank)."""
        current_holdings = ["AAPL", "MSFT", "GOOGL"]
        # GOOGL at rank 55 - outside buffer zone
        ranks = pd.Series({
            "AAPL": 1,
            "MSFT": 2,
            **{f"ASSET{i}": i + 2 for i in range(1, 29)},  # Fill ranks 3-30
            **{f"BUFFER{i}": i + 30 for i in range(1, 21)},  # Ranks 31-50
            "GOOGL": 55,  # Outside buffer zone
        })

        policy = MembershipPolicy(buffer_rank=50)

        result = apply_membership_policy(
            current_holdings=current_holdings,
            preselected_ranks=ranks,
            policy=policy,
            top_k=30,
        )

        # GOOGL should be removed (outside buffer zone)
        assert "GOOGL" not in result
        assert "AAPL" in result
        assert "MSFT" in result

    def test_asset_oscillates_around_buffer_boundary(self) -> None:
        """Test asset oscillating around buffer boundary (rank = buffer_rank)."""
        current_holdings = ["AAPL", "MSFT", "GOOGL"]
        # GOOGL exactly at buffer boundary
        ranks = pd.Series({
            "AAPL": 1,
            "MSFT": 2,
            **{f"ASSET{i}": i + 2 for i in range(1, 29)},  # Fill ranks 3-30
            **{f"BUFFER{i}": i + 30 for i in range(1, 20)},  # Ranks 31-49
            "GOOGL": 50,  # Exactly at buffer boundary
        })

        policy = MembershipPolicy(buffer_rank=50)

        result = apply_membership_policy(
            current_holdings=current_holdings,
            preselected_ranks=ranks,
            policy=policy,
            top_k=30,
        )

        # GOOGL at exactly buffer_rank should be kept (<=buffer_rank)
        assert "GOOGL" in result

    def test_multiple_assets_in_buffer_zone(self) -> None:
        """Test multiple assets in buffer zone."""
        current_holdings = ["AAPL", "MSFT", "GOOGL", "META", "NFLX"]
        # Multiple assets in buffer zone (31-50)
        ranks = pd.Series({
            "AAPL": 1,
            **{f"TOP{i}": i + 1 for i in range(1, 30)},  # Ranks 2-30
            "MSFT": 35,  # In buffer
            "GOOGL": 40,  # In buffer
            "META": 45,  # In buffer
            "NFLX": 48,  # In buffer
            **{f"FILLER{i}": i + 50 for i in range(1, 11)},  # Ranks 51-60
        })

        policy = MembershipPolicy(buffer_rank=50)

        result = apply_membership_policy(
            current_holdings=current_holdings,
            preselected_ranks=ranks,
            policy=policy,
            top_k=30,
        )

        # All buffered assets should be kept
        assert "MSFT" in result
        assert "GOOGL" in result
        assert "META" in result
        assert "NFLX" in result
        assert "AAPL" in result

    def test_buffer_zone_empty_all_ranks_within_top_k(self) -> None:
        """Test buffer zone empty (all current holdings within top_k)."""
        current_holdings = ["AAPL", "MSFT", "GOOGL"]
        ranks = pd.Series({
            "AAPL": 1,
            "MSFT": 2,
            "GOOGL": 3,
            **{f"ASSET{i}": i + 3 for i in range(1, 48)},  # Ranks 4-50
        })

        policy = MembershipPolicy(buffer_rank=50)

        result = apply_membership_policy(
            current_holdings=current_holdings,
            preselected_ranks=ranks,
            policy=policy,
            top_k=30,
        )

        # All holdings within top_k, buffer has no effect
        assert "AAPL" in result
        assert "MSFT" in result
        assert "GOOGL" in result
        assert len(result) == 30  # Should return exactly top_k

    def test_buffer_zone_with_no_buffer_policy(self) -> None:
        """Test behavior when buffer_rank is None (buffer disabled)."""
        current_holdings = ["AAPL", "MSFT", "GOOGL"]
        ranks = pd.Series({
            "AAPL": 1,
            "MSFT": 2,
            **{f"ASSET{i}": i + 2 for i in range(1, 29)},  # Ranks 3-30
            "GOOGL": 45,  # Would be in buffer if enabled
        })

        policy = MembershipPolicy(buffer_rank=None)  # Buffer disabled

        result = apply_membership_policy(
            current_holdings=current_holdings,
            preselected_ranks=ranks,
            policy=policy,
            top_k=30,
        )

        # GOOGL should be removed (no buffer protection)
        assert "GOOGL" not in result
        assert "AAPL" in result
        assert "MSFT" in result

    def test_buffer_rank_at_top_k_boundary(self) -> None:
        """Test buffer_rank exactly equal to top_k (minimal buffer)."""
        current_holdings = ["AAPL", "MSFT", "GOOGL"]
        ranks = pd.Series({
            "AAPL": 1,
            "MSFT": 2,
            **{f"ASSET{i}": i + 2 for i in range(1, 29)},  # Ranks 3-30
            "GOOGL": 30,  # Exactly at top_k = buffer_rank
            "META": 31,  # Just outside
        })

        policy = MembershipPolicy(buffer_rank=30)

        result = apply_membership_policy(
            current_holdings=current_holdings + ["META"],
            preselected_ranks=ranks,
            policy=policy,
            top_k=30,
        )

        # GOOGL at rank 30 should be kept
        assert "GOOGL" in result
        # META at rank 31 should be removed (outside buffer)
        assert "META" not in result


class TestBoundaryConditions:
    """Edge case tests for boundary conditions."""

    def test_all_current_holdings_fail_criteria(self) -> None:
        """Test when all current holdings fall outside both top_k and buffer."""
        current_holdings = ["OLD1", "OLD2", "OLD3"]
        ranks = pd.Series({
            **{f"NEW{i}": i for i in range(1, 31)},  # New top 30 assets
            "OLD1": 100,  # Far outside buffer
            "OLD2": 101,
            "OLD3": 102,
        })

        policy = MembershipPolicy(buffer_rank=50, min_holding_periods=None)

        result = apply_membership_policy(
            current_holdings=current_holdings,
            preselected_ranks=ranks,
            policy=policy,
            top_k=30,
        )

        # All old holdings should be removed
        assert "OLD1" not in result
        assert "OLD2" not in result
        assert "OLD3" not in result
        # Should have top 30 new assets
        assert len(result) == 30

    def test_all_current_holdings_protected_by_min_holding_period(self) -> None:
        """Test all holdings protected even when they fail all other criteria."""
        current_holdings = ["OLD1", "OLD2", "OLD3"]
        ranks = pd.Series({
            **{f"NEW{i}": i for i in range(1, 31)},  # New top 30 assets
            "OLD1": 100,  # Far outside buffer
            "OLD2": 101,
            "OLD3": 102,
        })
        holding_periods = {"OLD1": 1, "OLD2": 1, "OLD3": 1}  # All recently added

        policy = MembershipPolicy(buffer_rank=50, min_holding_periods=3)

        result = apply_membership_policy(
            current_holdings=current_holdings,
            preselected_ranks=ranks,
            policy=policy,
            holding_periods=holding_periods,
            top_k=30,
        )

        # All old holdings should be protected by min_holding_periods
        assert "OLD1" in result
        assert "OLD2" in result
        assert "OLD3" in result

    def test_single_asset_portfolio(self) -> None:
        """Test edge case with single asset in portfolio."""
        current_holdings = ["AAPL"]
        ranks = pd.Series({
            "AAPL": 50,  # Outside top_k but within buffer
            **{f"ASSET{i}": i for i in range(1, 31)},  # Ranks 1-30
        })

        policy = MembershipPolicy(buffer_rank=50)

        result = apply_membership_policy(
            current_holdings=current_holdings,
            preselected_ranks=ranks,
            policy=policy,
            top_k=30,
        )

        # AAPL should be kept due to buffer
        assert "AAPL" in result

    def test_exact_top_k_boundary(self) -> None:
        """Test asset exactly at top_k boundary (rank = top_k)."""
        current_holdings = ["ASSET30"]
        ranks = pd.Series({
            **{f"ASSET{i}": i for i in range(1, 31)},  # Ranks 1-30
            **{f"FILLER{i}": i + 30 for i in range(1, 21)},  # Ranks 31-50
        })

        policy = MembershipPolicy(buffer_rank=50)

        result = apply_membership_policy(
            current_holdings=current_holdings,
            preselected_ranks=ranks,
            policy=policy,
            top_k=30,
        )

        # ASSET30 at rank 30 should be in top_k
        assert "ASSET30" in result

    def test_all_assets_equal_rank(self) -> None:
        """Test edge case where all new candidates have equal rank."""
        current_holdings = ["AAPL"]
        # All new assets have same rank (tied)
        ranks = pd.Series({
            "AAPL": 1,
            "MSFT": 2,
            "AMZN": 2,
            "TSLA": 2,
            "META": 2,
            "GOOGL": 2,
        })

        policy = MembershipPolicy(max_new_assets=2)

        result = apply_membership_policy(
            current_holdings=current_holdings,
            preselected_ranks=ranks,
            policy=policy,
            top_k=5,
        )

        # Should have AAPL + 2 new assets (but which 2 is deterministic by pandas)
        assert "AAPL" in result
        assert len(result) == 3


class TestPolicyConstraintConflicts:
    """Edge case tests for conflicting policy constraints."""

    def test_min_holding_vs_max_removed_conflict(self) -> None:
        """Test conflict between min_holding_periods and max_removed_assets."""
        # 5 holdings, all old (can be removed), but max_removed_assets=2
        current_holdings = ["OLD1", "OLD2", "OLD3", "OLD4", "OLD5"]
        ranks = pd.Series({
            **{f"NEW{i}": i for i in range(1, 31)},  # New top 30 assets
            "OLD1": 100,
            "OLD2": 101,
            "OLD3": 102,
            "OLD4": 103,
            "OLD5": 104,
        })
        holding_periods = {
            f"OLD{i}": 10 for i in range(1, 6)
        }  # All held long enough

        policy = MembershipPolicy(
            buffer_rank=50,
            min_holding_periods=3,
            max_removed_assets=2,  # Can only remove 2
        )

        result = apply_membership_policy(
            current_holdings=current_holdings,
            preselected_ranks=ranks,
            policy=policy,
            holding_periods=holding_periods,
            top_k=30,
        )

        # Should keep 3 old holdings (5 - 2 removed)
        old_kept = [h for h in current_holdings if h in result]
        assert len(old_kept) == 3

    def test_max_new_vs_top_k_conflict(self) -> None:
        """Test when max_new_assets is less than top_k with empty portfolio."""
        current_holdings = []
        ranks = pd.Series({f"ASSET{i}": i for i in range(1, 51)})  # 50 assets

        policy = MembershipPolicy(max_new_assets=10)  # Can only add 10

        result = apply_membership_policy(
            current_holdings=current_holdings,
            preselected_ranks=ranks,
            policy=policy,
            top_k=30,  # Want 30 but can only add 10
        )

        # Should only have 10 assets (max_new_assets constraint)
        assert len(result) == 10

    def test_buffer_keeps_more_than_top_k(self) -> None:
        """Test buffer can cause result set larger than top_k."""
        # 10 current holdings in buffer zone
        current_holdings = [f"BUFFER{i}" for i in range(1, 11)]
        ranks = pd.Series({
            **{f"TOP{i}": i for i in range(1, 31)},  # New top 30
            **{f"BUFFER{i}": i + 30 for i in range(1, 11)},  # Ranks 31-40 (in buffer)
        })

        policy = MembershipPolicy(buffer_rank=50)

        result = apply_membership_policy(
            current_holdings=current_holdings,
            preselected_ranks=ranks,
            policy=policy,
            top_k=30,
        )

        # Should have 30 top + 10 buffered = 40 total
        assert len(result) == 40
        for i in range(1, 11):
            assert f"BUFFER{i}" in result

    def test_zero_max_new_assets(self) -> None:
        """Test max_new_assets=0 prevents all additions."""
        current_holdings = ["AAPL", "MSFT"]
        ranks = pd.Series({
            "AAPL": 1,
            "MSFT": 2,
            "AMZN": 3,  # Would be in top_k but blocked
            "TSLA": 4,
            "META": 5,
        })

        policy = MembershipPolicy(max_new_assets=0)

        result = apply_membership_policy(
            current_holdings=current_holdings,
            preselected_ranks=ranks,
            policy=policy,
            top_k=5,
        )

        # Should only have existing holdings (no new assets)
        assert len(result) == 2
        assert set(result) == {"AAPL", "MSFT"}

    def test_zero_max_removed_assets(self) -> None:
        """Test max_removed_assets=0 prevents all removals."""
        current_holdings = ["OLD1", "OLD2", "OLD3"]
        ranks = pd.Series({
            **{f"NEW{i}": i for i in range(1, 31)},  # New top 30
            "OLD1": 100,  # Should be removed but blocked
            "OLD2": 101,
            "OLD3": 102,
        })
        holding_periods = {f"OLD{i}": 10 for i in range(1, 4)}  # All held long enough

        policy = MembershipPolicy(
            buffer_rank=50,
            min_holding_periods=3,
            max_removed_assets=0,  # Cannot remove any
        )

        result = apply_membership_policy(
            current_holdings=current_holdings,
            preselected_ranks=ranks,
            policy=policy,
            holding_periods=holding_periods,
            top_k=30,
        )

        # All old holdings must be kept
        assert "OLD1" in result
        assert "OLD2" in result
        assert "OLD3" in result

    def test_min_holding_period_zero(self) -> None:
        """Test min_holding_periods=0 (no protection)."""
        current_holdings = ["AAPL", "MSFT"]
        ranks = pd.Series({
            "AMZN": 1,
            "TSLA": 2,
            "AAPL": 100,  # Can be removed immediately
            "MSFT": 101,
        })
        holding_periods = {"AAPL": 0, "MSFT": 0}  # Just added

        policy = MembershipPolicy(min_holding_periods=0, buffer_rank=50)

        result = apply_membership_policy(
            current_holdings=current_holdings,
            preselected_ranks=ranks,
            policy=policy,
            holding_periods=holding_periods,
            top_k=2,
        )

        # Assets can be removed even with 0 periods held
        assert "AAPL" not in result
        assert "MSFT" not in result


class TestSpecialScenarios:
    """Edge case tests for special/unusual scenarios."""

    def test_current_holding_missing_from_ranks(self) -> None:
        """Test behavior when current holding is not in preselected_ranks."""
        current_holdings = ["AAPL", "MSFT", "DELISTED"]
        ranks = pd.Series({
            "AAPL": 1,
            "MSFT": 2,
            "AMZN": 3,
            # DELISTED is missing - may have been delisted or excluded
        })

        policy = MembershipPolicy(buffer_rank=50)

        result = apply_membership_policy(
            current_holdings=current_holdings,
            preselected_ranks=ranks,
            policy=policy,
            top_k=30,
        )

        # DELISTED should not be in result (not in ranks)
        assert "DELISTED" not in result
        assert "AAPL" in result
        assert "MSFT" in result

    def test_all_new_candidates_worse_than_holdings(self) -> None:
        """Test when all new candidates rank worse than current holdings."""
        current_holdings = ["AAPL", "MSFT", "GOOGL"]
        ranks = pd.Series({
            "AAPL": 1,
            "MSFT": 2,
            "GOOGL": 3,
            # All other candidates rank worse
            **{f"WORSE{i}": i + 3 for i in range(1, 48)},  # Ranks 4-50
        })

        policy = MembershipPolicy(buffer_rank=50, max_new_assets=5)

        result = apply_membership_policy(
            current_holdings=current_holdings,
            preselected_ranks=ranks,
            policy=policy,
            top_k=30,
        )

        # Should include holdings + top new candidates up to top_k
        assert "AAPL" in result
        assert "MSFT" in result
        assert "GOOGL" in result
        assert len(result) == 30

    def test_large_buffer_includes_all_assets(self) -> None:
        """Test when buffer_rank is larger than universe."""
        current_holdings = ["AAPL", "MSFT"]
        ranks = pd.Series({
            "AAPL": 1,
            "MSFT": 50,  # Far from top_k but buffer is huge
            **{f"ASSET{i}": i + 1 for i in range(1, 49)},  # Ranks 2-49
        })

        policy = MembershipPolicy(buffer_rank=1000)  # Larger than universe

        result = apply_membership_policy(
            current_holdings=current_holdings,
            preselected_ranks=ranks,
            policy=policy,
            top_k=30,
        )

        # MSFT should be kept (buffer covers entire universe)
        assert "MSFT" in result
        assert "AAPL" in result

    def test_multiple_policies_all_at_limits(self) -> None:
        """Test all policy constraints active at their limits simultaneously."""
        current_holdings = [f"HOLD{i}" for i in range(1, 11)]  # 10 holdings
        ranks = pd.Series({
            **{f"NEW{i}": i for i in range(1, 31)},  # New top 30
            **{f"HOLD{i}": i + 35 for i in range(1, 11)},  # Ranks 36-45 (in buffer)
        })
        holding_periods = {
            f"HOLD{i}": 1 if i <= 5 else 10 for i in range(1, 11)
        }  # First 5 protected

        policy = MembershipPolicy(
            buffer_rank=50,  # Active: keeps HOLD1-10 in buffer
            min_holding_periods=3,  # Active: protects HOLD1-5
            max_new_assets=3,  # Active: limits additions
            max_removed_assets=2,  # Active: limits removals
        )

        result = apply_membership_policy(
            current_holdings=current_holdings,
            preselected_ranks=ranks,
            policy=policy,
            holding_periods=holding_periods,
            top_k=30,
        )

        # All holdings kept by buffer
        for i in range(1, 11):
            assert f"HOLD{i}" in result

        # At most 3 new assets added
        new_in_result = [a for a in result if a.startswith("NEW")]
        assert len(new_in_result) <= 3
