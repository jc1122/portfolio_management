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
