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
import logging
import warnings
from dataclasses import dataclass
from enum import Enum
from typing import Any

import numpy as np
import pandas as pd

from portfolio_management.core.exceptions import InsufficientDataError

logger = logging.getLogger(__name__)


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
        """Validate configuration parameters.

        Raises:
            ValueError: If any parameter is invalid, with actionable error message

        """
        # Validate top_k
        if self.config.top_k is not None and self.config.top_k < 0:
            raise ValueError(
                f"top_k must be >= 0, got {self.config.top_k}. "
                "Set to None or 0 to disable preselection, or use a positive integer. "
                "Example: PreselectionConfig(top_k=30)",
            )

        # Warn if top_k is too small
        if self.config.top_k is not None and 0 < self.config.top_k < 10:
            warnings.warn(
                f"top_k={self.config.top_k} is very small (<10 assets). "
                "This may lead to under-diversification and high concentration risk. "
                "Consider using top_k >= 10 for better diversification. "
                "Typical values: 20-50 assets.",
                UserWarning,
                stacklevel=3,
            )

        # Validate lookback
        if self.config.lookback < 1:
            raise ValueError(
                f"lookback must be >= 1, got {self.config.lookback}. "
                "Lookback defines the number of periods to use for factor calculation. "
                "Common values: 63 days (3 months), 126 days (6 months), 252 days (1 year). "
                "Example: PreselectionConfig(lookback=252)",
            )

        # Warn if lookback is too short
        if self.config.lookback < 63:
            warnings.warn(
                f"lookback={self.config.lookback} is very short (<63 days / 3 months). "
                "Short lookback periods may lead to noisy factor signals and high turnover. "
                "Consider using lookback >= 63 days for more stable signals. "
                "Typical values: 126 days (6 months), 252 days (1 year).",
                UserWarning,
                stacklevel=3,
            )

        # Validate skip
        if self.config.skip < 0:
            raise ValueError(
                f"skip must be >= 0, got {self.config.skip}. "
                "Skip defines the number of most recent periods to exclude from calculation. "
                "Common practice: skip=1 to avoid short-term reversals. "
                "Example: PreselectionConfig(skip=1)",
            )

        # Validate skip < lookback
        if self.config.skip >= self.config.lookback:
            raise ValueError(
                f"skip ({self.config.skip}) must be < lookback ({self.config.lookback}). "
                "You cannot skip more periods than your lookback window. "
                "To fix: reduce skip or increase lookback. "
                "Example: PreselectionConfig(lookback=252, skip=1)",
            )

        # Validate min_periods
        if self.config.min_periods < 1:
            raise ValueError(
                f"min_periods must be >= 1, got {self.config.min_periods}. "
                "min_periods defines the minimum number of valid observations required. "
                "It should be at least 1 to ensure meaningful calculations. "
                "Example: PreselectionConfig(min_periods=60)",
            )

        if self.config.min_periods > self.config.lookback:
            raise ValueError(
                f"min_periods ({self.config.min_periods}) must be <= lookback ({self.config.lookback}). "
                "You cannot require more periods than your lookback window. "
                "To fix: reduce min_periods or increase lookback. "
                "Example: PreselectionConfig(lookback=252, min_periods=60)",
            )

        # Validate combined method weights
        if self.config.method == PreselectionMethod.COMBINED:
            total_weight = self.config.momentum_weight + self.config.low_vol_weight
            if not np.isclose(total_weight, 1.0, atol=1e-6):
                raise ValueError(
                    f"Combined weights must sum to 1.0, got {total_weight} "
                    f"(momentum_weight={self.config.momentum_weight}, "
                    f"low_vol_weight={self.config.low_vol_weight}). "
                    "To fix: adjust weights so they sum to 1.0. "
                    "Example: PreselectionConfig(momentum_weight=0.6, low_vol_weight=0.4)",
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
            ValueError: If returns DataFrame is invalid
            InsufficientDataError: If insufficient data for factor calculation

        Examples:
            >>> config = PreselectionConfig(method=PreselectionMethod.MOMENTUM, top_k=30)
            >>> preselect = Preselection(config)
            >>> selected = preselect.select_assets(returns, rebalance_date=date(2023, 1, 1))

        """
        # Validate returns DataFrame
        if returns is None or returns.empty:
            raise ValueError(
                "returns DataFrame is empty or None. "
                "To fix: provide a non-empty DataFrame with returns data. "
                "Expected format: DataFrame with dates as index, assets as columns. "
                "Example: returns.shape = (1000, 50) for 1000 days, 50 assets.",
            )

        if not isinstance(returns, pd.DataFrame):
            raise ValueError(
                f"returns must be a pandas DataFrame, got {type(returns).__name__}. "
                "To fix: convert your data to a DataFrame. "
                "Example: returns = pd.DataFrame(data, index=dates, columns=tickers)",
            )

        if len(returns.columns) == 0:
            raise ValueError(
                "returns DataFrame has no columns (no assets). "
                "To fix: ensure returns DataFrame has asset columns. "
                "Example: returns.columns = ['AAPL', 'MSFT', 'GOOGL']",
            )

        # Validate rebalance_date if provided
        if rebalance_date is not None:
            if not isinstance(rebalance_date, datetime.date):
                raise ValueError(
                    f"rebalance_date must be a datetime.date, got {type(rebalance_date).__name__}. "
                    "To fix: use datetime.date object. "
                    "Example: from datetime import date; rebalance_date = date(2023, 1, 1)",
                )

            # Check if rebalance_date is within or after data range
            max_date = returns.index.max()
            if isinstance(max_date, pd.Timestamp):
                max_date = max_date.date()

            if rebalance_date > max_date:
                raise ValueError(
                    f"rebalance_date ({rebalance_date}) is after the last available date ({max_date}). "
                    "To fix: use a rebalance_date within your data range. "
                    f"Available date range: {returns.index.min()} to {max_date}",
                )

        # If no top_k or top_k <= 0, return all assets
        if self.config.top_k is None or self.config.top_k <= 0:
            logger.info(
                f"Preselection disabled (top_k={self.config.top_k}), "
                f"returning all {len(returns.columns)} assets",
            )
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
                asset_ticker=f"Insufficient data: need {self.config.min_periods} periods, "
                f"have {len(available_returns)} periods. "
                f"To fix: provide more historical data or reduce min_periods. "
                f"Current config: lookback={self.config.lookback}, min_periods={self.config.min_periods}",
            )

        # Compute factor scores (with caching if enabled)
        scores = self._get_or_compute_scores(returns, available_returns, rebalance_date)

        # Handle edge case: all NaN scores
        if scores.isna().all():
            warnings.warn(
                f"All factor scores are NaN for rebalance_date={rebalance_date}. "
                "This typically indicates insufficient valid data across all assets. "
                "Returning empty list. "
                "To fix: check data quality, reduce lookback/min_periods, or use more assets.",
                UserWarning,
                stacklevel=2,
            )
            return []

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
            # No valid assets - return empty list (edge case handled)
            logger.warning(
                "No valid scores after filtering NaN values. "
                "Returning empty asset list.",
            )
            return []

        # Determine how many to select
        k = min(self.config.top_k or len(valid_scores), len(valid_scores))

        # Log if we have fewer assets than requested
        if len(valid_scores) < (self.config.top_k or 0):
            logger.warning(
                f"Only {len(valid_scores)} valid assets available, "
                f"less than requested top_k={self.config.top_k}. "
                "Returning all valid assets.",
            )

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
            logger.debug(
                f"Broke ties at cutoff: {len(candidates)} candidates -> {k} selected",
            )
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
