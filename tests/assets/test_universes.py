"""Tests for the universe management module."""

from pathlib import Path

import pandas as pd
import pytest
pytestmark = pytest.mark.integration

from portfolio_management.assets.universes import (
    UniverseConfigLoader,
    UniverseDefinition,
    UniverseManager,
)
from portfolio_management.core.exceptions import ConfigurationError


@pytest.fixture
def universe_config_path(tmp_path: Path) -> Path:
    """Creates a dummy universe config file for testing."""
    config_content = """
universes:
  test_universe:
    description: "A test universe"
    filter_criteria:
      min_history_days: 100
    classification_requirements:
      asset_classes: ["equity"]
  test_universe_2:
    description: "Another test universe"
    filter_criteria:
      min_history_days: 500
    """
    config_path = tmp_path / "universes.yaml"
    config_path.write_text(config_content)
    return config_path


@pytest.fixture
def matches_df() -> pd.DataFrame:
    """Creates a dummy matches DataFrame for testing."""
    return pd.DataFrame(
        {
            "symbol": ["A.US", "B.UK", "C.DE"],
            "isin": ["US01", "GB02", "DE03"],
            "name": ["Asset A", "Asset B", "Asset C"],
            "market": ["US", "UK", "DE"],
            "region": ["North America", "Europe", "Europe"],
            "currency": ["USD", "GBP", "EUR"],
            "category": ["Stock", "Stock", "ETF"],
            "price_start": ["2020-01-01", "2021-01-01", "2022-01-01"],
            "price_end": ["2023-01-01", "2023-01-01", "2023-01-01"],
            "price_rows": [756, 504, 252],
            "data_status": ["ok", "ok", "warning"],
            "data_flags": ["", "", "zero_volume_severity=high"],
            "stooq_path": ["a.us.txt", "b.uk.txt", "c.de.txt"],
            "resolved_currency": ["USD", "GBP", "EUR"],
            "currency_status": ["matched", "matched", "matched"],
        },
    )


@pytest.fixture
def prices_dir(tmp_path: Path) -> Path:
    """Creates a dummy prices directory for testing."""
    (tmp_path / "a.us.txt").write_text("date,close\n2022-01-03,100\n2022-01-04,101")
    (tmp_path / "b.uk.txt").write_text("date,close\n2022-01-03,200\n2022-01-04,202")
    return tmp_path


class TestUniverseConfigLoader:
    """Tests for the UniverseConfigLoader class."""

    def test_load_config_valid(self, universe_config_path: Path) -> None:
        """Test loading a valid universe config file."""
        config = UniverseConfigLoader.load_config(universe_config_path)
        assert "test_universe" in config
        assert isinstance(config["test_universe"], UniverseDefinition)
        assert config["test_universe"].description == "A test universe"
        assert config["test_universe"].filter_criteria.min_history_days == 100

    def test_load_config_not_found(self) -> None:
        """Test loading a non-existent config file."""
        with pytest.raises(ConfigurationError):
            UniverseConfigLoader.load_config(Path("nonexistent.yaml"))

    def test_load_config_invalid_yaml(self, tmp_path: Path) -> None:
        """Test loading an invalid YAML file."""
        config_path = tmp_path / "invalid.yaml"
        config_path.write_text("universes: {test: [}")
        with pytest.raises(ConfigurationError):
            UniverseConfigLoader.load_config(config_path)


class TestUniverseManager:
    """Tests for the UniverseManager class."""

    @pytest.fixture
    def universe_manager(
        self,
        universe_config_path: Path,
        matches_df: pd.DataFrame,
        prices_dir: Path,
    ) -> UniverseManager:
        """Returns an instance of the UniverseManager."""
        return UniverseManager(universe_config_path, matches_df, prices_dir)

    def test_list_universes(self, universe_manager: UniverseManager) -> None:
        """Test listing available universes."""
        assert set(universe_manager.list_universes()) == {
            "test_universe",
            "test_universe_2",
        }

    def test_get_definition(self, universe_manager: UniverseManager) -> None:
        """Test getting a universe definition."""
        definition = universe_manager.get_definition("test_universe")
        assert isinstance(definition, UniverseDefinition)
        assert definition.description == "A test universe"

    def test_select_assets(self, universe_manager: UniverseManager) -> None:
        """Test internal asset selection."""
        definition = universe_manager.get_definition("test_universe")
        assets = universe_manager._select_assets(definition)
        assert len(assets) == 2

    def test_classify_assets(self, universe_manager: UniverseManager) -> None:
        """Test internal asset classification."""
        definition = universe_manager.get_definition("test_universe")
        assets = universe_manager._select_assets(definition)
        classified_df = universe_manager._classify_assets(assets)
        assert len(classified_df) == 2

    def test_filter_by_classification(self, universe_manager: UniverseManager) -> None:
        """Test internal filtering by classification."""
        definition = universe_manager.get_definition("test_universe")
        assets = universe_manager._select_assets(definition)
        classified_df = universe_manager._classify_assets(assets)
        filtered_df = universe_manager._filter_by_classification(
            classified_df, definition
        )
        assert len(filtered_df) > 0

    def test_calculate_returns(self, universe_manager: UniverseManager) -> None:
        """Test internal return calculation."""
        definition = universe_manager.get_definition("test_universe")
        assets = universe_manager._select_assets(definition)
        returns_df = universe_manager._calculate_returns(assets, definition)
        assert isinstance(returns_df, pd.DataFrame)
        assert not returns_df.empty

    def test_load_universe(self, universe_manager: UniverseManager) -> None:
        """Test the full universe loading pipeline."""
        universe = universe_manager.load_universe("test_universe")
        assert isinstance(universe, dict)
        assert "assets" in universe
        assert "classifications" in universe
        assert "returns" in universe
        assert "metadata" in universe
        assert not universe["returns"].empty

    def test_compare_universes(self, universe_manager: UniverseManager) -> None:
        """Test comparing two universes."""
        comparison_df = universe_manager.compare_universes(
            ["test_universe", "test_universe_2"]
        )
        assert len(comparison_df) == 2
        assert "asset_count" in comparison_df.columns

    def test_get_universe_overlap(self, universe_manager: UniverseManager) -> None:
        """Test getting the overlap between two universes."""
        overlap = universe_manager.get_universe_overlap(
            "test_universe", "test_universe_2"
        )
        assert isinstance(overlap, set)

    def test_validate_universe(self, universe_manager: UniverseManager) -> None:
        """Test validating a universe."""
        result = universe_manager.validate_universe("test_universe")
        assert result["is_valid"] is True
