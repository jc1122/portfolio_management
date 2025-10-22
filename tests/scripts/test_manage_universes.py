"""Tests for the manage_universes CLI script."""

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Import the main function to test
from scripts.manage_universes import main


@pytest.fixture
def mock_args_list(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock command-line arguments for the list command."""
    test_args = [
        "manage_universes.py",
        "--config",
        "config/universes.yaml",
        "list",
    ]
    monkeypatch.setattr(sys, "argv", test_args)


@pytest.fixture
def mock_args_show(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock command-line arguments for the show command."""
    test_args = [
        "manage_universes.py",
        "--config",
        "config/universes.yaml",
        "show",
        "core_global",
    ]
    monkeypatch.setattr(sys, "argv", test_args)


@pytest.fixture
def mock_args_load(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Mock command-line arguments for the load command."""
    test_args = [
        "manage_universes.py",
        "--config",
        "config/universes.yaml",
        "--matches",
        "data/metadata/tradeable_matches.csv",
        "load",
        "test_universe",
        "--output-dir",
        str(tmp_path),
    ]
    monkeypatch.setattr(sys, "argv", test_args)


class TestLazyLoading:
    """Tests to verify lazy loading behavior."""

    def test_list_command_does_not_load_matches_csv(
        self, mock_args_list: None, capsys: pytest.CaptureFixture
    ) -> None:
        """Verify that the list command does not load the matches CSV."""
        _ = mock_args_list  # Used via monkeypatch
        with patch("scripts.manage_universes.pd.read_csv") as mock_read_csv:
            # The list command should run successfully
            main()

            # Verify that pd.read_csv was never called for list command
            mock_read_csv.assert_not_called()

            # Verify the output is correct
            captured = capsys.readouterr()
            assert "Available universes:" in captured.out

    def test_show_command_does_not_load_matches_csv(
        self, mock_args_show: None, capsys: pytest.CaptureFixture
    ) -> None:
        """Verify that the show command does not load the matches CSV."""
        _ = mock_args_show  # Used via monkeypatch
        with patch("scripts.manage_universes.pd.read_csv") as mock_read_csv:
            # The show command should run successfully
            main()

            # Verify that pd.read_csv was never called for show command
            mock_read_csv.assert_not_called()

            # Verify the output is correct
            captured = capsys.readouterr()
            assert "Universe: core_global" in captured.out

    def test_load_command_loads_matches_csv(
        self, mock_args_load: None, tmp_path: Path  # noqa: ARG002
    ) -> None:
        """Verify that the load command does load the matches CSV."""
        _ = mock_args_load  # Used via monkeypatch
        with patch("scripts.manage_universes.pd.read_csv") as mock_read_csv:
            with patch(
                "scripts.manage_universes.UniverseManager"
            ) as mock_manager:
                # Mock the manager to return an empty universe
                mock_instance = MagicMock()
                mock_instance.load_universe.return_value = None
                mock_manager.return_value = mock_instance

                # The load command should try to load matches
                main()

                # Verify that pd.read_csv was called for load command
                mock_read_csv.assert_called_once()


class TestBehaviorPreservation:
    """Tests to verify that behavior remains the same."""

    def test_list_command_output(self) -> None:
        """Test that list command produces expected output."""
        result = subprocess.run(
            [
                sys.executable,
                "scripts/manage_universes.py",
                "--config",
                "config/universes.yaml",
                "list",
            ],
            check=False, cwd=Path.cwd(),
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        assert "Available universes:" in result.stdout
        assert "core_global" in result.stdout
        # Verify that matches CSV is not being accessed
        assert "tradeable_matches.csv" not in result.stderr

    def test_show_command_output(self) -> None:
        """Test that show command produces expected output."""
        result = subprocess.run(
            [
                sys.executable,
                "scripts/manage_universes.py",
                "--config",
                "config/universes.yaml",
                "show",
                "core_global",
            ],
            check=False, cwd=Path.cwd(),
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        assert "Universe: core_global" in result.stdout
        assert "UniverseDefinition" in result.stdout
        # Verify that matches CSV is not being accessed
        assert "tradeable_matches.csv" not in result.stderr

    def test_show_command_unknown_universe(self) -> None:
        """Test that show command fails gracefully for unknown universe."""
        result = subprocess.run(
            [
                sys.executable,
                "scripts/manage_universes.py",
                "--config",
                "config/universes.yaml",
                "show",
                "nonexistent_universe",
            ],
            check=False, cwd=Path.cwd(),
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 1
        assert "not found" in result.stderr.lower()
