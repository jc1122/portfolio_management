"""Clustering-based diversification for asset preselection.

This module provides hierarchical clustering functionality to select a diversified
subset of assets based on their historical return correlations. The goal is to
reduce concentration risk by choosing assets that are less correlated with each other.

Key components:
- ClusteringConfig: Configuration for clustering parameters
- cluster_by_correlation: Main clustering function using hierarchical clustering
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from .selection import SelectedAsset

try:
    from scipy.cluster import hierarchy
    from scipy.spatial.distance import squareform

    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


class ClusteringMethod(Enum):
    """Supported clustering methods."""

    NONE = "none"
    HIERARCHICAL = "hierarchical"


@dataclass
class ClusteringConfig:
    """Configuration for clustering-based preselection.

    Attributes:
        method: Clustering method to use (none or hierarchical).
        shortlist_size: Number of top-ranked candidates to shortlist before clustering.
        top_k: Final number of assets to select after clustering.
        linkage_method: Linkage method for hierarchical clustering (ward, average, complete, single).
        min_history_overlap: Minimum number of overlapping days required for correlation calculation.
    """

    method: ClusteringMethod = ClusteringMethod.NONE
    shortlist_size: int = 200
    top_k: int = 50
    linkage_method: str = "ward"
    min_history_overlap: int = 126  # ~6 months of trading days

    def validate(self) -> None:
        """Validate clustering configuration.

        Raises:
            ValueError: If configuration parameters are invalid.
        """
        if self.shortlist_size <= 0:
            raise ValueError(
                f"shortlist_size must be positive, got {self.shortlist_size}",
            )
        if self.top_k <= 0:
            raise ValueError(f"top_k must be positive, got {self.top_k}")
        if self.top_k > self.shortlist_size:
            raise ValueError(
                f"top_k ({self.top_k}) cannot exceed shortlist_size ({self.shortlist_size})",
            )
        if self.linkage_method not in ["ward", "average", "complete", "single"]:
            raise ValueError(
                f"Invalid linkage_method: {self.linkage_method}. "
                f"Must be one of: ward, average, complete, single",
            )
        if self.min_history_overlap <= 0:
            raise ValueError(
                f"min_history_overlap must be positive, got {self.min_history_overlap}",
            )


def _load_price_data(
    stooq_path: str,
    data_dir: Path,
) -> pd.Series | None:
    """Load price data for a single asset.

    Args:
        stooq_path: Relative path to price file in Stooq data directory.
        data_dir: Base directory containing Stooq data.

    Returns:
        Series with date index and close prices, or None if loading fails.
    """
    logger = logging.getLogger(__name__)

    try:
        full_path = data_dir / stooq_path
        if not full_path.exists():
            logger.warning(f"Price file not found: {full_path}")
            return None

        # Try to detect format by reading first line
        with open(full_path, encoding="utf-8") as f:
            header = f.readline().strip()

        # Check if it's Stooq format with <DATE> column
        if "<DATE>" in header:
            # Stooq format: <TICKER>,<PER>,<DATE>,<TIME>,<OPEN>,<HIGH>,<LOW>,<CLOSE>,<VOL>
            df = pd.read_csv(full_path)
            if "<DATE>" not in df.columns or "<CLOSE>" not in df.columns:
                logger.warning(f"Expected Stooq columns not found in {stooq_path}")
                return None

            # Convert date to datetime and set as index
            df["Date"] = pd.to_datetime(df["<DATE>"], format="%Y%m%d")
            df = df.set_index("Date")

            # Return close prices as a Series
            return df["<CLOSE>"]
        else:
            # Standard format with Date and Close columns
            df = pd.read_csv(
                full_path,
                parse_dates=["Date"],
                index_col="Date",
            )

            if "Close" not in df.columns:
                logger.warning(f"Close column not found in {stooq_path}")
                return None

            # Return close prices as a Series
            return df["Close"]

    except Exception as e:
        logger.warning(f"Failed to load price data from {stooq_path}: {e}")
        return None


def _calculate_returns_matrix(
    assets: list[SelectedAsset],
    data_dir: Path,
    min_history_overlap: int,
) -> tuple[pd.DataFrame, list[str]]:
    """Calculate returns matrix for clustering.

    Args:
        assets: List of SelectedAsset objects.
        data_dir: Base directory containing Stooq data.
        min_history_overlap: Minimum overlapping days required.

    Returns:
        Tuple of (returns DataFrame with symbols as columns, list of symbols with insufficient data).
    """
    logger = logging.getLogger(__name__)

    # Load price data for all assets
    prices = {}
    failed_symbols = []

    for asset in assets:
        price_series = _load_price_data(asset.stooq_path, data_dir)
        if price_series is not None and len(price_series) > 0:
            prices[asset.symbol] = price_series
        else:
            failed_symbols.append(asset.symbol)
            logger.debug(f"Failed to load prices for {asset.symbol}")

    if not prices:
        logger.error("No price data could be loaded for any asset")
        return pd.DataFrame(), list(failed_symbols)

    # Align price data to common dates
    prices_df = pd.DataFrame(prices)
    logger.info(
        f"Loaded prices for {len(prices_df.columns)} assets, "
        f"date range: {prices_df.index.min()} to {prices_df.index.max()}",
    )

    # Calculate returns (percentage change)
    # Note: dropna() will remove any rows with NaN, so we don't need explicit fill_method
    returns_df = prices_df.pct_change().dropna()

    # Check for sufficient overlapping data
    valid_symbols = []
    insufficient_symbols = []

    for symbol in returns_df.columns:
        non_null_count = returns_df[symbol].notna().sum()
        if non_null_count >= min_history_overlap:
            valid_symbols.append(symbol)
        else:
            insufficient_symbols.append(symbol)
            logger.debug(
                f"Insufficient data for {symbol}: {non_null_count} < {min_history_overlap} days",
            )

    # Filter to valid symbols only
    returns_df = returns_df[valid_symbols]

    # Drop rows where any asset has missing data (for clean correlation calculation)
    returns_df = returns_df.dropna()

    logger.info(
        f"Returns matrix: {len(returns_df)} days × {len(returns_df.columns)} assets",
    )

    all_failed = failed_symbols + insufficient_symbols
    return returns_df, all_failed


def _hierarchical_cluster_selection(
    returns_df: pd.DataFrame,
    top_k: int,
    linkage_method: str,
) -> list[str]:
    """Select diverse assets using hierarchical clustering.

    Args:
        returns_df: DataFrame of returns with symbols as columns.
        top_k: Number of assets to select.
        linkage_method: Linkage method for clustering.

    Returns:
        List of selected symbols.
    """
    logger = logging.getLogger(__name__)

    if not SCIPY_AVAILABLE:
        raise ImportError(
            "scipy is required for hierarchical clustering. "
            "Install with: pip install scipy",
        )

    n_assets = len(returns_df.columns)

    if n_assets <= top_k:
        logger.warning(
            f"Number of assets ({n_assets}) <= top_k ({top_k}), "
            "returning all assets without clustering",
        )
        return sorted(returns_df.columns.tolist())

    # Calculate correlation matrix
    corr_matrix = returns_df.corr()

    # Convert correlation to distance (1 - correlation)
    # Correlation of 1 = distance 0 (identical), correlation of -1 = distance 2 (opposite)
    distance_matrix = 1 - corr_matrix

    # Ensure non-negative distances and symmetric
    distance_matrix = distance_matrix.clip(lower=0)
    distance_matrix = (distance_matrix + distance_matrix.T) / 2

    # Convert to condensed distance matrix for scipy
    condensed_dist = squareform(distance_matrix, checks=False)

    # Perform hierarchical clustering
    linkage_matrix = hierarchy.linkage(condensed_dist, method=linkage_method)

    # Cut tree to get top_k clusters
    cluster_labels = hierarchy.fcluster(linkage_matrix, top_k, criterion="maxclust")

    # Select one representative from each cluster
    # Use the asset with the lowest average correlation within its cluster
    selected_symbols = []
    symbols = returns_df.columns.tolist()

    for cluster_id in range(1, top_k + 1):
        # Get assets in this cluster
        cluster_mask = cluster_labels == cluster_id
        cluster_indices = np.where(cluster_mask)[0]

        if len(cluster_indices) == 0:
            continue

        # If single asset in cluster, select it
        if len(cluster_indices) == 1:
            selected_symbols.append(symbols[cluster_indices[0]])
            continue

        # Select asset with lowest average correlation to other assets in cluster
        min_avg_corr = float("inf")
        selected_idx = cluster_indices[0]

        for idx in cluster_indices:
            other_indices = [i for i in cluster_indices if i != idx]
            avg_corr = corr_matrix.iloc[idx, other_indices].mean()

            # Use deterministic tie-breaking: prefer alphabetically first symbol
            if avg_corr < min_avg_corr or (
                avg_corr == min_avg_corr and symbols[idx] < symbols[selected_idx]
            ):
                min_avg_corr = avg_corr
                selected_idx = idx

        selected_symbols.append(symbols[selected_idx])

    # Sort for deterministic output
    selected_symbols = sorted(selected_symbols)

    logger.info(f"Selected {len(selected_symbols)} assets via hierarchical clustering")

    return selected_symbols


def cluster_by_correlation(
    assets: list[SelectedAsset],
    config: ClusteringConfig,
    data_dir: Path,
) -> list[SelectedAsset]:
    """Select diverse assets using correlation-based clustering.

    This function implements the clustering-based preselection algorithm:
    1. Load price data for all assets in the shortlist
    2. Calculate returns and correlation matrix
    3. Perform hierarchical clustering on correlation-based distances
    4. Select one representative from each cluster

    Args:
        assets: List of assets to cluster (should be pre-filtered shortlist).
        config: Clustering configuration.
        data_dir: Base directory containing Stooq data (e.g., data/stooq/).

    Returns:
        List of selected assets after clustering.

    Raises:
        ValueError: If configuration is invalid.
        ImportError: If scipy is not available.
    """
    logger = logging.getLogger(__name__)

    config.validate()

    if config.method == ClusteringMethod.NONE:
        logger.info("Clustering disabled, returning input assets")
        return assets

    if len(assets) <= config.top_k:
        logger.warning(
            f"Number of assets ({len(assets)}) <= top_k ({config.top_k}), "
            "returning all assets without clustering",
        )
        return assets

    logger.info(
        f"Starting clustering with {len(assets)} assets, target {config.top_k} selected",
    )

    # Calculate returns matrix
    returns_df, failed_symbols = _calculate_returns_matrix(
        assets,
        data_dir,
        config.min_history_overlap,
    )

    if returns_df.empty:
        logger.error("Failed to calculate returns matrix, returning input assets")
        return assets

    if len(returns_df.columns) <= config.top_k:
        logger.warning(
            f"Only {len(returns_df.columns)} assets with sufficient data, "
            f"returning all without clustering",
        )
        # Return assets that have sufficient data, sorted by symbol
        valid_symbols = set(returns_df.columns)
        valid_assets = [a for a in assets if a.symbol in valid_symbols]
        return sorted(valid_assets, key=lambda a: a.symbol)

    # Perform clustering
    selected_symbols = _hierarchical_cluster_selection(
        returns_df,
        config.top_k,
        config.linkage_method,
    )

    # Map back to SelectedAsset objects
    symbol_to_asset = {a.symbol: a for a in assets}
    selected_assets = [
        symbol_to_asset[symbol]
        for symbol in selected_symbols
        if symbol in symbol_to_asset
    ]

    logger.info(
        f"Clustering complete: selected {len(selected_assets)} of {len(assets)} assets",
    )
    logger.info(f"Assets with insufficient data: {len(failed_symbols)}")

    return selected_assets
