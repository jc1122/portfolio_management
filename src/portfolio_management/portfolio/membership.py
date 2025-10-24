"""Membership policy for controlling portfolio turnover and stability.

This module provides tools for managing asset membership changes during rebalancing
to reduce churn, control turnover, and enforce minimum holding periods.

The membership policy sits between preselection (or universe definition) and the
optimizer, adjusting the candidate set based on existing holdings and policy rules.

Example:
    >>> from portfolio_management.portfolio.membership import MembershipPolicy, apply_membership_policy
    >>> import pandas as pd
    >>>
    >>> # Define policy
    >>> policy = MembershipPolicy(
    ...     buffer_rank=50,
    ...     min_holding_periods=3,
    ...     max_turnover=0.30,
    ...     max_new_assets=5,
    ...     max_removed_assets=5
    ... )
    >>>
    >>> # Apply policy at rebalance
    >>> current_holdings = ["AAPL", "MSFT", "GOOGL"]
    >>> preselected_ranks = pd.Series({"AAPL": 1, "MSFT": 2, "AMZN": 3, "TSLA": 4, ...})
    >>> holding_periods = {"AAPL": 5, "MSFT": 2, "GOOGL": 1}
    >>>
    >>> final_candidates = apply_membership_policy(
    ...     current_holdings=current_holdings,
    ...     preselected_ranks=preselected_ranks,
    ...     policy=policy,
    ...     holding_periods=holding_periods,
    ...     top_k=30
    ... )

"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import pandas as pd

from portfolio_management.utils.validation import (
    validate_positive_int,
    validate_probability,
)

logger = logging.getLogger(__name__)


@dataclass
class MembershipPolicy:
    """Configuration for membership policy rules.

    This dataclass defines the rules that control how asset membership changes
    during portfolio rebalancing. Policies are applied in a specific order to
    ensure stability while respecting selection criteria.

    Application order:
        1. Min holding period: protect assets from premature exit
        2. Rank buffer: keep existing holdings unless they fall far out of favor
        3. Max changes: limit the number of additions/removals per rebalance
        4. Turnover cap: limit the fraction of portfolio value that can change

    Attributes:
        buffer_rank: Assets currently held are kept if their rank is better than this
            threshold, even if they fall outside top_k. For example, if top_k=30 and
            buffer_rank=50, existing holdings ranked 31-50 will be retained.
            Set to None to disable buffer. Default: None.
        min_holding_periods: Minimum number of rebalance periods an asset must be held
            before it can be removed. Set to None or 0 to disable. Default: None.
        max_turnover: Maximum fraction of portfolio value that can change in a single
            rebalance (0.0 to 1.0). Calculated as sum of absolute weight changes.
            Set to None to disable. Default: None.
        max_new_assets: Maximum number of new assets that can be added in a single
            rebalance. Set to None to disable. Default: None.
        max_removed_assets: Maximum number of assets that can be removed in a single
            rebalance. Set to None to disable. Default: None.
        enabled: Master switch to enable/disable all policy rules. Default: True.

    Example:
        >>> # Conservative policy: limit churn
        >>> policy = MembershipPolicy(
        ...     buffer_rank=50,
        ...     min_holding_periods=3,
        ...     max_turnover=0.30,
        ...     max_new_assets=5,
        ...     max_removed_assets=5
        ... )
        >>>
        >>> # Aggressive policy: more freedom to rebalance
        >>> policy = MembershipPolicy(
        ...     buffer_rank=35,
        ...     min_holding_periods=1,
        ...     max_turnover=0.50,
        ...     max_new_assets=10,
        ...     max_removed_assets=10
        ... )
        >>>
        >>> # Disabled policy
        >>> policy = MembershipPolicy(enabled=False)

    """

    buffer_rank: int | None = None
    min_holding_periods: int | None = None
    max_turnover: float | None = None
    max_new_assets: int | None = None
    max_removed_assets: int | None = None
    enabled: bool = True

    def validate(self) -> None:
        """Validate policy parameters.

        Raises:
            ValueError: If any parameter is invalid.

        """
        if self.buffer_rank is not None:
            validate_positive_int(self.buffer_rank, "buffer_rank")

        if self.min_holding_periods is not None:
            validate_positive_int(self.min_holding_periods, "min_holding_periods", allow_zero=True)

        if self.max_turnover is not None:
            validate_probability(self.max_turnover, "max_turnover")

        if self.max_new_assets is not None:
            validate_positive_int(self.max_new_assets, "max_new_assets", allow_zero=True)

        if self.max_removed_assets is not None:
            validate_positive_int(self.max_removed_assets, "max_removed_assets", allow_zero=True)

    @classmethod
    def default(cls) -> MembershipPolicy:
        """Create a default membership policy suitable for most portfolios.

        Returns:
            MembershipPolicy with moderate defaults:
            - buffer_rank: top_k + 20 (recommended to set explicitly based on top_k)
            - min_holding_periods: 3 rebalances
            - max_turnover: 30%
            - max_new_assets: 5 per rebalance
            - max_removed_assets: 5 per rebalance

        Example:
            >>> policy = MembershipPolicy.default()
            >>> policy.min_holding_periods
            3

        """
        return cls(
            buffer_rank=None,  # Should be set based on top_k
            min_holding_periods=3,
            max_turnover=0.30,
            max_new_assets=5,
            max_removed_assets=5,
            enabled=True,
        )

    @classmethod
    def disabled(cls) -> MembershipPolicy:
        """Create a disabled membership policy (no restrictions).

        Returns:
            MembershipPolicy with enabled=False.

        Example:
            >>> policy = MembershipPolicy.disabled()
            >>> policy.enabled
            False

        """
        return cls(enabled=False)


def apply_membership_policy(  # noqa: PLR0913
    current_holdings: list[str],
    preselected_ranks: pd.Series,
    policy: MembershipPolicy,
    holding_periods: dict[str, int] | None = None,
    top_k: int = 30,
    current_weights: dict[str, float] | None = None,
    candidate_weights: dict[str, float] | None = None,
) -> list[str]:
    """Apply membership policy to determine final candidate set.

    This function takes the preselected candidates (typically from a ranking/scoring
    step) and current portfolio holdings, then applies policy rules to determine the
    final set of assets that should be passed to the optimizer.

    Policy application order:
        1. Start with top_k from preselected_ranks
        2. Apply min_holding_periods: keep assets that haven't been held long enough
        3. Apply buffer_rank: keep existing holdings within buffer
        4. Apply max_new_assets: limit additions
        5. Apply max_removed_assets: limit removals
        6. Check max_turnover: if violated, reduce changes (future enhancement)

    Args:
        current_holdings: List of asset IDs currently in the portfolio.
        preselected_ranks: Series mapping asset IDs to their rank (1=best).
            Lower rank is better. Must include all current_holdings if they are
            still in the universe.
        policy: MembershipPolicy configuration.
        holding_periods: Dict mapping asset ID to number of periods held.
            Required if policy.min_holding_periods is set. Default: None.
        top_k: Number of top-ranked assets to target. Default: 30.
        current_weights: Dict mapping current holdings to their portfolio weights.
            Required if policy.max_turnover is set. Default: None.
        candidate_weights: Dict mapping candidate assets to their expected weights
            after rebalance. Required if policy.max_turnover is set. Default: None.

    Returns:
        List of asset IDs that should be passed to the optimizer, respecting all
        policy constraints.

    Raises:
        ValueError: If required data is missing or invalid.

    Example:
        >>> current_holdings = ["AAPL", "MSFT", "GOOGL"]
        >>> ranks = pd.Series({"AAPL": 1, "MSFT": 2, "AMZN": 3, "GOOGL": 45, ...})
        >>> holding_periods = {"AAPL": 5, "MSFT": 2, "GOOGL": 1}
        >>> policy = MembershipPolicy(
        ...     buffer_rank=50,
        ...     min_holding_periods=3,
        ...     max_new_assets=2
        ... )
        >>>
        >>> final = apply_membership_policy(
        ...     current_holdings=current_holdings,
        ...     preselected_ranks=ranks,
        ...     policy=policy,
        ...     holding_periods=holding_periods,
        ...     top_k=30
        ... )
        >>> # GOOGL kept despite rank=45 (within buffer) and min_holding_periods
        >>> # Only 2 new assets added due to max_new_assets

    """
    # Validate inputs
    if not policy.enabled:
        # Return top_k without any policy constraints
        top_assets = preselected_ranks.nsmallest(top_k).index.tolist()
        logger.debug(
            f"Membership policy disabled, returning top {top_k} assets: {len(top_assets)} assets",
        )
        return top_assets

    policy.validate()

    if policy.min_holding_periods and holding_periods is None:
        raise ValueError(
            "holding_periods required when min_holding_periods is set in policy",
        )

    if policy.max_turnover is not None and (
        current_weights is None or candidate_weights is None
    ):
        raise ValueError(
            "current_weights and candidate_weights required when max_turnover is set",
        )

    # Start with top_k candidates
    top_candidates = set(preselected_ranks.nsmallest(top_k).index.tolist())
    logger.debug(f"Starting with top {top_k} candidates: {len(top_candidates)} assets")

    current_holdings_set = set(current_holdings)
    logger.debug(f"Current holdings: {len(current_holdings_set)} assets")

    # Step 1: Apply min_holding_periods - protect assets from premature exit
    protected_assets = set()
    if policy.min_holding_periods is not None and holding_periods is not None:
        for asset in current_holdings:
            periods_held = holding_periods.get(asset, 0)
            if periods_held < policy.min_holding_periods:
                protected_assets.add(asset)
                logger.debug(
                    f"Protecting {asset}: held {periods_held} < {policy.min_holding_periods} periods",
                )

        if protected_assets:
            logger.info(
                f"Min holding period protection: {len(protected_assets)} assets protected",
            )

    # Step 2: Apply buffer_rank - keep existing holdings within buffer
    buffered_assets = set()
    if policy.buffer_rank is not None:
        for asset in current_holdings:
            rank = preselected_ranks.get(asset)
            if rank is not None and rank <= policy.buffer_rank:
                buffered_assets.add(asset)
                logger.debug(
                    f"Buffering {asset}: rank {rank} <= buffer_rank {policy.buffer_rank}",
                )

        if buffered_assets:
            logger.info(
                f"Buffer rank protection: {len(buffered_assets)} assets within buffer",
            )

    # Combine protected and buffered assets with top_k
    candidate_set = top_candidates | protected_assets | buffered_assets

    # Step 3: Apply max_new_assets - limit additions
    new_assets = candidate_set - current_holdings_set
    if policy.max_new_assets is not None and len(new_assets) > policy.max_new_assets:
        # Keep the best-ranked new assets up to the limit
        new_asset_ranks = preselected_ranks[list(new_assets)].sort_values()
        allowed_new = set(new_asset_ranks.head(policy.max_new_assets).index)

        removed_new = new_assets - allowed_new
        candidate_set = candidate_set - removed_new

        logger.info(
            f"Max new assets constraint: kept {len(allowed_new)}/{len(new_assets)} new assets",
        )
        logger.debug(f"Rejected new assets: {removed_new}")

    # Step 4: Apply max_removed_assets - limit removals
    removed_assets = current_holdings_set - candidate_set
    if (
        policy.max_removed_assets is not None
        and len(removed_assets) > policy.max_removed_assets
    ):
        # Keep the worst-ranked assets up to the limit (i.e., remove the best of the worst)
        removed_asset_ranks = preselected_ranks[list(removed_assets)].sort_values()
        actually_removed = set(
            removed_asset_ranks.head(policy.max_removed_assets).index,
        )
        kept_back = removed_assets - actually_removed

        candidate_set = candidate_set | kept_back

        logger.info(
            f"Max removed assets constraint: removing {len(actually_removed)}/{len(removed_assets)} assets",
        )
        logger.debug(f"Kept back (would-be-removed): {kept_back}")

    # Step 5: Turnover check (currently informational only)
    # Full implementation requires optimizer-generated weights, which aren't available yet
    # This is a placeholder for future enhancement
    if policy.max_turnover is not None:
        logger.warning(
            "max_turnover policy is configured but not yet enforced "
            "(requires post-optimization weight adjustment)",
        )
        # Future: iteratively adjust candidate_set to meet turnover constraint

    final_candidates = sorted(candidate_set)  # Sort for determinism

    logger.info(
        f"Membership policy applied: {len(current_holdings)} holdings -> "
        f"{len(final_candidates)} candidates "
        f"(+{len(candidate_set - current_holdings_set)} new, "
        f"-{len(current_holdings_set - candidate_set)} removed)",
    )

    return final_candidates
