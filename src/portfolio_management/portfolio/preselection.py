"""Factor-based asset preselection for portfolio construction.

This module implements deterministic preselection of assets based on momentum
and low-volatility factors, designed to reduce the universe size before
portfolio optimization while using only information available up to each
rebalance date (no lookahead bias).

Key Features:
    - Momentum: Cumulative return over lookback period with optional skip
    - Low-volatility: Inverse of realized volatility
    - Combined: Weighted Z-score combination of multiple factors
    - Deterministic tie-breaking by asset symbol
    - No future data leakage

Example:
    >>> preselect = Preselection(method="momentum", top_k=20, lookback=252)
    >>> selected_assets = preselect.select_assets(
    ...     returns=historical_returns,
    ...     rebalance_date=date(2023, 1, 1)
    ... )

"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from enum import Enum
from typing import Any

import numpy as np
import pandas as pd

from portfolio_management.core.exceptions import InsufficientDataError


class PreselectionMethod(Enum):
    """Available preselection methods."""

    MOMENTUM = "momentum"
    LOW_VOL = "low_vol"
    COMBINED = "combined"


@dataclass
class PreselectionConfig:
    """Configuration for asset preselection.

    Attributes:
        method: Preselection method to use
        top_k: Number of assets to select (if None or 0, no preselection)
        lookback: Number of periods to look back for factor calculation
        skip: Number of most recent periods to skip (for momentum)
        momentum_weight: Weight for momentum factor (when using combined)
        low_vol_weight: Weight for low-volatility factor (when using combined)
        min_periods: Minimum number of periods required for valid calculation

    """

    method: PreselectionMethod = PreselectionMethod.MOMENTUM
    top_k: int | None = None
    lookback: int = 252  # ~1 year of daily data
    skip: int = 1  # Skip most recent day (common in momentum strategies)
    momentum_weight: float = 0.5
    low_vol_weight: float = 0.5
    min_periods: int = 60  # Minimum data required


class Preselection:
    """Factor-based asset preselection engine.

    Computes momentum and/or low-volatility factors from historical returns
    and selects top-K assets deterministically without lookahead bias.

    Supports optional caching to avoid recomputing factor scores across runs.
    """

    def __init__(self, config: PreselectionConfig, cache: Any | None = None) -> None:
        """Initialize preselection engine.

        Args:
            config: Preselection configuration
            cache: Optional FactorCache instance for caching factor scores

        """
        self.config = config
        self.cache = cache
        self._validate_config()

    def _validate_config(self) -> None:
        """Validate configuration parameters."""
        if self.config.lookback < 1:
            raise ValueError("lookback must be >= 1")
        if self.config.skip < 0:
            raise ValueError("skip must be >= 0")
        if self.config.skip >= self.config.lookback:
            raise ValueError("skip must be < lookback")
        if self.config.min_periods < 1:
            raise ValueError("min_periods must be >= 1")
        if self.config.min_periods > self.config.lookback:
            raise ValueError("min_periods must be <= lookback")

        if self.config.method == PreselectionMethod.COMBINED:
            total_weight = self.config.momentum_weight + self.config.low_vol_weight
            if not np.isclose(total_weight, 1.0, atol=1e-6):
                raise ValueError(
                    f"Combined weights must sum to 1.0, got {total_weight}",
                )

    def select_assets(
        self,
        returns: pd.DataFrame,
        rebalance_date: datetime.date | None = None,
    ) -> list[str]:
        """Select top-K assets based on configured factors.

        Uses only data available up to (but not including) rebalance_date.
        If rebalance_date is None, uses all available data.

        Args:
            returns: DataFrame with returns (assets as columns, dates as index)
            rebalance_date: Date of rebalancing (uses data strictly before this)

        Returns:
            List of selected asset tickers (sorted alphabetically for determinism)

        Raises:
            InsufficientDataError: If insufficient data for factor calculation

        """
        # If no top_k or top_k <= 0, return all assets
        if self.config.top_k is None or self.config.top_k <= 0:
            return sorted(returns.columns.tolist())

        # Filter data up to rebalance date (no lookahead)
        if rebalance_date is not None:
            # Convert index to dates for comparison
            if isinstance(returns.index, pd.DatetimeIndex):
                date_mask = returns.index.date < rebalance_date
            else:
                # Assume index is already dates
                date_mask = returns.index < rebalance_date
            available_returns = returns.loc[date_mask]
        else:
            available_returns = returns

        # Check if we have enough data
        if len(available_returns) < self.config.min_periods:
            raise InsufficientDataError(
                required_start=rebalance_date or datetime.date.today(),
                available_start=rebalance_date or datetime.date.today(),
                asset_ticker=f"Need {self.config.min_periods} periods, "
                f"have {len(available_returns)}",
            )

        # Compute factor scores (with caching if enabled)
        scores = self._get_or_compute_scores(returns, available_returns, rebalance_date)

        # Select top-K assets
        return self._select_top_k(scores)

    def _get_or_compute_scores(
        self,
        full_returns: pd.DataFrame,
        available_returns: pd.DataFrame,
        rebalance_date: datetime.date | None,
    ) -> pd.Series:
        """Get factor scores from cache or compute them.

        Args:
            full_returns: Full returns matrix (for cache key)
            available_returns: Returns filtered to rebalance date
            rebalance_date: Rebalance date for cache key

        Returns:
            Series of factor scores

        """
        # Build cache config
        cache_config = {
            "method": self.config.method.value,
            "lookback": self.config.lookback,
            "skip": self.config.skip,
            "min_periods": self.config.min_periods,
            "momentum_weight": self.config.momentum_weight,
            "low_vol_weight": self.config.low_vol_weight,
        }

        # Determine date range for cache key
        start_date = str(available_returns.index[0])
        end_date = str(available_returns.index[-1])

        # Try to get from cache
        if self.cache is not None:
            cached_scores = self.cache.get_factor_scores(
                full_returns,
                cache_config,
                start_date,
                end_date,
            )
            if cached_scores is not None:
                return cached_scores

        # Compute scores
        if self.config.method == PreselectionMethod.MOMENTUM:
            scores = self._compute_momentum(available_returns)
        elif self.config.method == PreselectionMethod.LOW_VOL:
            scores = self._compute_low_volatility(available_returns)
        elif self.config.method == PreselectionMethod.COMBINED:
            scores = self._compute_combined(available_returns)
        else:
            raise ValueError(f"Unknown preselection method: {self.config.method}")

        # Cache the scores
        if self.cache is not None:
            self.cache.put_factor_scores(
                scores,
                full_returns,
                cache_config,
                start_date,
                end_date,
            )

        return scores

    def _compute_momentum(self, returns: pd.DataFrame) -> pd.Series:
        """Compute momentum factor (cumulative return with optional skip).

        Args:
            returns: Historical returns up to rebalance date

        Returns:
            Series of momentum scores (one per asset)

        """
        # Get lookback window
        lookback_start = max(0, len(returns) - self.config.lookback)
        lookback_returns = returns.iloc[lookback_start:]

        # Apply skip period (exclude most recent N periods)
        if self.config.skip > 0:
            lookback_returns = lookback_returns.iloc[: -self.config.skip]

        # Compute cumulative return for each asset
        # Using (1+r1)*(1+r2)*...*(1+rn) - 1
        # Note: prod() with skipna=False will propagate NaN properly
        cumulative = (1 + lookback_returns).prod(axis=0, skipna=False) - 1

        return cumulative

    def _compute_low_volatility(self, returns: pd.DataFrame) -> pd.Series:
        """Compute low-volatility factor (inverse of realized volatility).

        Higher scores = lower volatility = more attractive for low-vol strategy.

        Args:
            returns: Historical returns up to rebalance date

        Returns:
            Series of low-volatility scores (one per asset)

        """
        # Get lookback window
        lookback_start = max(0, len(returns) - self.config.lookback)
        lookback_returns = returns.iloc[lookback_start:]

        # Compute realized volatility (standard deviation)
        volatility = lookback_returns.std(axis=0)

        # Return inverse (higher = better)
        # Use small epsilon to avoid division by zero
        epsilon = 1e-8
        return 1.0 / (volatility + epsilon)

    def _compute_combined(self, returns: pd.DataFrame) -> pd.Series:
        """Compute combined factor score using weighted Z-scores.

        Args:
            returns: Historical returns up to rebalance date

        Returns:
            Series of combined scores (one per asset)

        """
        # Compute individual factors
        momentum = self._compute_momentum(returns)
        low_vol = self._compute_low_volatility(returns)

        # Normalize to Z-scores (mean=0, std=1)
        momentum_z = self._standardize(momentum)
        low_vol_z = self._standardize(low_vol)

        # Combine with weights
        combined = (
            self.config.momentum_weight * momentum_z
            + self.config.low_vol_weight * low_vol_z
        )

        return combined

    def _standardize(self, scores: pd.Series) -> pd.Series:
        """Standardize scores to Z-scores (mean=0, std=1).

        Handles all-NaN and zero-variance cases gracefully.

        Args:
            scores: Raw factor scores

        Returns:
            Standardized scores

        """
        # Drop NaN values for statistics
        valid_scores = scores.dropna()

        if len(valid_scores) == 0:
            # All NaN - return zeros
            return pd.Series(0.0, index=scores.index)

        mean = valid_scores.mean()
        std = valid_scores.std()

        # Handle zero variance (all values identical)
        if std < 1e-8:
            # Return zeros (all assets equally ranked)
            return pd.Series(0.0, index=scores.index)

        # Standardize
        z_scores = (scores - mean) / std

        # Replace any remaining NaN with 0 (neutral score)
        return z_scores.fillna(0.0)

    def _select_top_k(self, scores: pd.Series) -> list[str]:
        """Select top-K assets by score with deterministic tie-breaking.

        Args:
            scores: Factor scores for each asset

        Returns:
            List of selected asset tickers (sorted alphabetically)

        """
        # Drop NaN scores (assets with insufficient data)
        valid_scores = scores.dropna()

        if len(valid_scores) == 0:
            # No valid assets - return empty list
            return []

        # Determine how many to select
        k = min(self.config.top_k or len(valid_scores), len(valid_scores))

        # Sort by score (descending) then by ticker (ascending) for determinism
        # This ensures ties are broken consistently
        sorted_scores = valid_scores.sort_values(ascending=False)

        # Handle ties at the cutoff point
        # Get all assets with scores >= the k-th highest score
        if k < len(sorted_scores):
            kth_score = sorted_scores.iloc[k - 1]
            # Select all assets with score >= kth_score
            candidates = sorted_scores[sorted_scores >= kth_score]
        else:
            candidates = sorted_scores

        # If we have more candidates than k (due to ties), break ties by symbol
        if len(candidates) > k:
            # Sort by score (desc) then symbol (asc) for deterministic tie-breaking
            candidates_df = pd.DataFrame(
                {"score": candidates, "symbol": candidates.index},
            )
            candidates_df = candidates_df.sort_values(
                by=["score", "symbol"],
                ascending=[False, True],
            )
            selected = candidates_df.head(k)["symbol"].tolist()
        else:
            selected = candidates.index.tolist()

        # Return sorted alphabetically for consistent output
        return sorted(selected)


def create_preselection_from_dict(config_dict: dict) -> Preselection | None:
    """Create Preselection instance from dictionary configuration.

    Args:
        config_dict: Dictionary with preselection configuration

    Returns:
        Preselection instance or None if preselection disabled

    """
    if not config_dict:
        return None

    top_k = config_dict.get("top_k", 0)
    if top_k is None or top_k <= 0:
        return None

    method_str = config_dict.get("method", "momentum")
    try:
        method = PreselectionMethod(method_str)
    except ValueError:
        raise ValueError(
            f"Invalid preselection method: {method_str}. "
            f"Must be one of: {[m.value for m in PreselectionMethod]}",
        )

    config = PreselectionConfig(
        method=method,
        top_k=config_dict.get("top_k"),
        lookback=config_dict.get("lookback", 252),
        skip=config_dict.get("skip", 1),
        momentum_weight=config_dict.get("momentum_weight", 0.5),
        low_vol_weight=config_dict.get("low_vol_weight", 0.5),
        min_periods=config_dict.get("min_periods", 60),
    )

    return Preselection(config)
