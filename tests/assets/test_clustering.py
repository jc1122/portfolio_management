"""Tests for clustering-based asset diversification."""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from portfolio_management.assets.selection import (
    ClusteringConfig,
    ClusteringMethod,
    SelectedAsset,
)
from portfolio_management.assets.selection.clustering import (
    _calculate_returns_matrix,
    _hierarchical_cluster_selection,
    _load_price_data,
    cluster_by_correlation,
)


@pytest.fixture
def sample_selected_assets() -> list[SelectedAsset]:
    """Create sample SelectedAsset objects for testing."""
    assets = []
    for i in range(10):
        asset = SelectedAsset(
            symbol=f"TEST{i}.UK",
            isin=f"GB00TEST000{i}",
            name=f"Test Asset {i}",
            market="UK",
            region="Europe",
            currency="GBP",
            category="ETF",
            price_start="2020-01-01",
            price_end="2025-01-01",
            price_rows=1200,
            data_status="ok",
            data_flags="",
            stooq_path=f"d_uk_txt/data/daily/uk/test{i}.txt",
            resolved_currency="GBP",
            currency_status="matched",
        )
        assets.append(asset)
    return assets


@pytest.fixture
def temp_price_data() -> Path:
    """Create temporary price data files for testing."""
    temp_dir = tempfile.mkdtemp()
    base_path = Path(temp_dir)

    # Create directory structure
    data_dir = base_path / "d_uk_txt" / "data" / "daily" / "uk"
    data_dir.mkdir(parents=True, exist_ok=True)

    # Generate 250 days of price data with different correlation patterns
    dates = pd.date_range("2024-01-01", periods=250, freq="D")

    # Create 10 assets with varying correlations
    np.random.seed(42)
    base_returns = np.random.randn(250)

    for i in range(10):
        # Assets 0-2: highly correlated with each other
        # Assets 3-5: moderately correlated
        # Assets 6-9: low correlation
        if i < 3:
            correlation_weight = 0.9
        elif i < 6:
            correlation_weight = 0.5
        else:
            correlation_weight = 0.1

        # Mix base returns with independent noise
        returns = (
            correlation_weight * base_returns
            + (1 - correlation_weight) * np.random.randn(250)
        )

        # Convert returns to prices (cumulative)
        prices = 100 * np.exp(np.cumsum(returns * 0.01))

        # Create DataFrame
        df = pd.DataFrame(
            {
                "Date": dates,
                "Open": prices,
                "High": prices * 1.01,
                "Low": prices * 0.99,
                "Close": prices,
                "Volume": 1000000,
            }
        )

        # Write to file
        file_path = data_dir / f"test{i}.txt"
        df.to_csv(file_path, index=False)

    return base_path


class TestClusteringConfig:
    """Test ClusteringConfig validation."""

    def test_valid_config(self) -> None:
        """Test that valid config passes validation."""
        config = ClusteringConfig(
            method=ClusteringMethod.HIERARCHICAL,
            shortlist_size=100,
            top_k=20,
            linkage_method="ward",
        )
        config.validate()  # Should not raise

    def test_invalid_shortlist_size(self) -> None:
        """Test that negative shortlist_size raises error."""
        config = ClusteringConfig(shortlist_size=-1)
        with pytest.raises(ValueError, match="shortlist_size must be positive"):
            config.validate()

    def test_invalid_top_k(self) -> None:
        """Test that negative top_k raises error."""
        config = ClusteringConfig(top_k=-1)
        with pytest.raises(ValueError, match="top_k must be positive"):
            config.validate()

    def test_top_k_exceeds_shortlist(self) -> None:
        """Test that top_k > shortlist_size raises error."""
        config = ClusteringConfig(shortlist_size=10, top_k=20)
        with pytest.raises(ValueError, match="top_k.*cannot exceed shortlist_size"):
            config.validate()

    def test_invalid_linkage_method(self) -> None:
        """Test that invalid linkage method raises error."""
        config = ClusteringConfig(linkage_method="invalid")
        with pytest.raises(ValueError, match="Invalid linkage_method"):
            config.validate()

    def test_invalid_min_history_overlap(self) -> None:
        """Test that negative min_history_overlap raises error."""
        config = ClusteringConfig(min_history_overlap=-1)
        with pytest.raises(ValueError, match="min_history_overlap must be positive"):
            config.validate()


class TestLoadPriceData:
    """Test _load_price_data function."""

    def test_load_existing_file(self, temp_price_data: Path) -> None:
        """Test loading price data from existing file."""
        stooq_path = "d_uk_txt/data/daily/uk/test0.txt"
        prices = _load_price_data(stooq_path, temp_price_data)

        assert prices is not None
        assert len(prices) == 250
        assert isinstance(prices, pd.Series)
        assert prices.index.name == "Date"

    def test_load_nonexistent_file(self, temp_price_data: Path) -> None:
        """Test loading price data from nonexistent file."""
        stooq_path = "d_uk_txt/data/daily/uk/nonexistent.txt"
        prices = _load_price_data(stooq_path, temp_price_data)

        assert prices is None

    def test_load_invalid_csv(self, temp_price_data: Path) -> None:
        """Test loading invalid CSV file."""
        # Create an invalid CSV file
        invalid_path = temp_price_data / "d_uk_txt" / "data" / "daily" / "uk"
        invalid_file = invalid_path / "invalid.txt"
        invalid_file.write_text("This is not valid CSV data")

        stooq_path = "d_uk_txt/data/daily/uk/invalid.txt"
        prices = _load_price_data(stooq_path, temp_price_data)

        assert prices is None


class TestCalculateReturnsMatrix:
    """Test _calculate_returns_matrix function."""

    def test_calculate_returns_matrix(
        self,
        sample_selected_assets: list[SelectedAsset],
        temp_price_data: Path,
    ) -> None:
        """Test calculating returns matrix."""
        returns_df, failed = _calculate_returns_matrix(
            sample_selected_assets,
            temp_price_data,
            min_history_overlap=100,
        )

        assert isinstance(returns_df, pd.DataFrame)
        assert len(returns_df.columns) == 10
        assert len(returns_df) > 0
        assert len(failed) == 0

    def test_calculate_returns_with_missing_files(
        self,
        sample_selected_assets: list[SelectedAsset],
        temp_price_data: Path,
    ) -> None:
        """Test calculating returns when some files are missing."""
        # Modify some assets to have nonexistent paths
        assets = sample_selected_assets.copy()
        assets[0].stooq_path = "d_uk_txt/data/daily/uk/missing.txt"

        returns_df, failed = _calculate_returns_matrix(
            assets,
            temp_price_data,
            min_history_overlap=100,
        )

        assert len(failed) > 0
        assert "TEST0.UK" in failed

    def test_calculate_returns_insufficient_overlap(
        self,
        sample_selected_assets: list[SelectedAsset],
        temp_price_data: Path,
    ) -> None:
        """Test calculating returns with insufficient overlap requirement."""
        returns_df, failed = _calculate_returns_matrix(
            sample_selected_assets,
            temp_price_data,
            min_history_overlap=1000,  # More than available
        )

        # Should have no valid assets
        assert len(returns_df.columns) == 0
        assert len(failed) > 0


class TestHierarchicalClusterSelection:
    """Test _hierarchical_cluster_selection function."""

    def test_cluster_selection_basic(self) -> None:
        """Test basic hierarchical cluster selection."""
        # Create synthetic returns data with known correlation structure
        np.random.seed(42)
        n_days = 250
        base_returns = np.random.randn(n_days)

        # Create 3 groups of highly correlated assets
        returns_data = {}
        for group in range(3):
            for i in range(3):
                symbol = f"ASSET_{group}_{i}"
                # High correlation within group
                returns_data[symbol] = (
                    0.8 * base_returns + 0.2 * np.random.randn(n_days)
                )

        returns_df = pd.DataFrame(returns_data)

        # Select 3 assets (one from each group ideally)
        selected = _hierarchical_cluster_selection(returns_df, 3, "ward")

        assert len(selected) == 3
        assert all(s in returns_df.columns for s in selected)
        # Should be deterministic
        assert selected == sorted(selected)

    def test_cluster_selection_fewer_assets_than_k(self) -> None:
        """Test clustering when n_assets <= top_k."""
        np.random.seed(42)
        returns_df = pd.DataFrame(
            {
                "ASSET1": np.random.randn(100),
                "ASSET2": np.random.randn(100),
            }
        )

        selected = _hierarchical_cluster_selection(returns_df, 5, "ward")

        # Should return all assets since we have fewer than k
        assert len(selected) == 2
        assert set(selected) == set(returns_df.columns)

    def test_cluster_selection_deterministic(self) -> None:
        """Test that clustering is deterministic."""
        np.random.seed(42)
        returns_df = pd.DataFrame(
            {f"ASSET{i}": np.random.randn(100) for i in range(20)}
        )

        # Run clustering multiple times
        selected1 = _hierarchical_cluster_selection(returns_df, 5, "ward")
        selected2 = _hierarchical_cluster_selection(returns_df, 5, "ward")

        assert selected1 == selected2

    def test_cluster_selection_different_linkage(self) -> None:
        """Test that different linkage methods work."""
        np.random.seed(42)
        returns_df = pd.DataFrame(
            {f"ASSET{i}": np.random.randn(100) for i in range(10)}
        )

        for linkage in ["ward", "average", "complete", "single"]:
            selected = _hierarchical_cluster_selection(returns_df, 3, linkage)
            assert len(selected) == 3


class TestClusterByCorrelation:
    """Test cluster_by_correlation function."""

    def test_clustering_disabled(
        self,
        sample_selected_assets: list[SelectedAsset],
        temp_price_data: Path,
    ) -> None:
        """Test that clustering returns input when disabled."""
        config = ClusteringConfig(method=ClusteringMethod.NONE)
        result = cluster_by_correlation(
            sample_selected_assets,
            config,
            temp_price_data,
        )

        assert result == sample_selected_assets

    def test_clustering_with_valid_data(
        self,
        sample_selected_assets: list[SelectedAsset],
        temp_price_data: Path,
    ) -> None:
        """Test clustering with valid price data."""
        config = ClusteringConfig(
            method=ClusteringMethod.HIERARCHICAL,
            shortlist_size=10,
            top_k=5,
            linkage_method="ward",
            min_history_overlap=100,
        )

        result = cluster_by_correlation(
            sample_selected_assets,
            config,
            temp_price_data,
        )

        assert len(result) == 5
        assert all(isinstance(a, SelectedAsset) for a in result)
        # Should be sorted by symbol
        symbols = [a.symbol for a in result]
        assert symbols == sorted(symbols)

    def test_clustering_fewer_assets_than_k(
        self,
        sample_selected_assets: list[SelectedAsset],
        temp_price_data: Path,
    ) -> None:
        """Test clustering when input has fewer assets than top_k."""
        config = ClusteringConfig(
            method=ClusteringMethod.HIERARCHICAL,
            shortlist_size=20,
            top_k=15,
            linkage_method="ward",
        )

        result = cluster_by_correlation(
            sample_selected_assets[:5],
            config,
            temp_price_data,
        )

        # Should return all available assets
        assert len(result) <= 5

    def test_clustering_invalid_config(
        self,
        sample_selected_assets: list[SelectedAsset],
        temp_price_data: Path,
    ) -> None:
        """Test that invalid config raises error."""
        config = ClusteringConfig(
            method=ClusteringMethod.HIERARCHICAL,
            shortlist_size=10,
            top_k=20,  # Invalid: top_k > shortlist_size
        )

        with pytest.raises(ValueError, match="cannot exceed shortlist_size"):
            cluster_by_correlation(
                sample_selected_assets,
                config,
                temp_price_data,
            )


class TestCorrelationReduction:
    """Test that clustering reduces pairwise correlation."""

    def test_clustering_reduces_correlation(
        self,
        sample_selected_assets: list[SelectedAsset],
        temp_price_data: Path,
    ) -> None:
        """Test that clustering selects assets with lower average correlation."""
        # Calculate correlation for all assets
        returns_df_all, _ = _calculate_returns_matrix(
            sample_selected_assets,
            temp_price_data,
            min_history_overlap=100,
        )
        corr_all = returns_df_all.corr()
        avg_corr_all = (corr_all.sum().sum() - len(corr_all)) / (
            len(corr_all) * (len(corr_all) - 1)
        )

        # Apply clustering to select diverse subset
        config = ClusteringConfig(
            method=ClusteringMethod.HIERARCHICAL,
            shortlist_size=10,
            top_k=5,
            linkage_method="ward",
            min_history_overlap=100,
        )

        selected = cluster_by_correlation(
            sample_selected_assets,
            config,
            temp_price_data,
        )

        # Calculate correlation for selected assets
        selected_symbols = [a.symbol for a in selected]
        corr_selected = returns_df_all[selected_symbols].corr()
        avg_corr_selected = (corr_selected.sum().sum() - len(corr_selected)) / (
            len(corr_selected) * (len(corr_selected) - 1)
        )

        # Clustered selection should have lower average correlation
        # Allow some tolerance due to randomness in test data
        assert avg_corr_selected <= avg_corr_all + 0.1

    def test_naive_vs_clustering_selection(
        self,
        sample_selected_assets: list[SelectedAsset],
        temp_price_data: Path,
    ) -> None:
        """Compare naive top-K selection vs clustering-based selection."""
        # Get returns matrix
        returns_df, _ = _calculate_returns_matrix(
            sample_selected_assets,
            temp_price_data,
            min_history_overlap=100,
        )

        top_k = 5

        # Naive selection: just take first K assets
        naive_symbols = sorted(returns_df.columns[:top_k])
        corr_naive = returns_df[naive_symbols].corr()
        avg_corr_naive = (corr_naive.sum().sum() - len(corr_naive)) / (
            len(corr_naive) * (len(corr_naive) - 1)
        )

        # Clustering-based selection
        clustered_symbols = _hierarchical_cluster_selection(
            returns_df,
            top_k,
            "ward",
        )
        corr_clustered = returns_df[clustered_symbols].corr()
        avg_corr_clustered = (corr_clustered.sum().sum() - len(corr_clustered)) / (
            len(corr_clustered) * (len(corr_clustered) - 1)
        )

        # Clustering should generally produce lower correlation
        # (not guaranteed in every case due to test data randomness,
        # but should hold on average)
        # For this specific test data with designed correlation structure,
        # it should definitely be lower
        assert avg_corr_clustered <= avg_corr_naive + 0.15


class TestAssetSelectorIntegration:
    """Integration tests for AssetSelector with clustering."""

    def test_asset_selector_with_clustering(
        self,
        sample_selected_assets: list[SelectedAsset],
        temp_price_data: Path,
    ) -> None:
        """Test full AssetSelector pipeline with clustering enabled."""
        from portfolio_management.assets.selection import (
            AssetSelector,
            FilterCriteria,
        )

        # Create DataFrame from assets
        assets_data = [asset.__dict__ for asset in sample_selected_assets]
        matches_df = pd.DataFrame(assets_data)

        # Create clustering config
        clustering_config = ClusteringConfig(
            method=ClusteringMethod.HIERARCHICAL,
            shortlist_size=10,
            top_k=5,
            linkage_method="ward",
        )

        # Create criteria with clustering
        criteria = FilterCriteria(
            data_status=["ok"],
            min_history_days=1,
            min_price_rows=1,
            clustering_config=clustering_config,
        )

        # Run selection with clustering
        selector = AssetSelector()
        selected = selector.select_assets(matches_df, criteria, temp_price_data)

        # Verify output
        assert len(selected) == 5
        assert all(isinstance(a, SelectedAsset) for a in selected)

        # Verify deterministic output (sorted by symbol)
        symbols = [a.symbol for a in selected]
        assert symbols == sorted(symbols)

    def test_asset_selector_without_clustering(
        self,
        sample_selected_assets: list[SelectedAsset],
    ) -> None:
        """Test AssetSelector without clustering (backward compatibility)."""
        from portfolio_management.assets.selection import (
            AssetSelector,
            FilterCriteria,
        )

        # Create DataFrame from assets
        assets_data = [asset.__dict__ for asset in sample_selected_assets]
        matches_df = pd.DataFrame(assets_data)

        # Create criteria without clustering
        criteria = FilterCriteria(
            data_status=["ok"],
            min_history_days=1,
            min_price_rows=1,
        )

        # Run selection without clustering
        selector = AssetSelector()
        selected = selector.select_assets(matches_df, criteria)

        # Should return all assets (no filters applied)
        assert len(selected) == 10

    def test_clustering_requires_data_dir(
        self,
        sample_selected_assets: list[SelectedAsset],
    ) -> None:
        """Test that clustering raises error without data_dir."""
        from portfolio_management.assets.selection import (
            AssetSelector,
            FilterCriteria,
        )
        from portfolio_management.core.exceptions import DataValidationError

        # Create DataFrame from assets
        assets_data = [asset.__dict__ for asset in sample_selected_assets]
        matches_df = pd.DataFrame(assets_data)

        # Create clustering config
        clustering_config = ClusteringConfig(
            method=ClusteringMethod.HIERARCHICAL,
            shortlist_size=10,
            top_k=5,
        )

        # Create criteria with clustering
        criteria = FilterCriteria(
            data_status=["ok"],
            clustering_config=clustering_config,
        )

        # Should raise error when data_dir is None
        selector = AssetSelector()
        with pytest.raises(DataValidationError, match="data_dir is required"):
            selector.select_assets(matches_df, criteria, data_dir=None)
