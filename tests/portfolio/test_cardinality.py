"""Tests for cardinality constraint interfaces and stubs.

These tests validate the design interfaces for cardinality-constrained
optimization, ensuring that stub functions raise appropriate errors and
validation logic works correctly.
"""

from __future__ import annotations

import pandas as pd
import pytest
pytestmark = pytest.mark.integration

from portfolio_management.portfolio import (
    CardinalityConstraints,
    CardinalityMethod,
    CardinalityNotImplementedError,
    PortfolioConstraints,
    get_cardinality_optimizer,
    optimize_with_cardinality_heuristic,
    optimize_with_cardinality_miqp,
    optimize_with_cardinality_relaxation,
    validate_cardinality_constraints,
)


class TestCardinalityConstraints:
    """Tests for CardinalityConstraints dataclass."""

    def test_default_values(self) -> None:
        """Test default constraint values."""
        constraints = CardinalityConstraints()

        assert constraints.enabled is False
        assert constraints.method == CardinalityMethod.PRESELECTION
        assert constraints.max_assets is None
        assert constraints.min_position_size == 0.01
        assert constraints.group_limits is None
        assert constraints.enforce_in_optimizer is False

    def test_simple_cardinality(self) -> None:
        """Test simple cardinality constraint configuration."""
        constraints = CardinalityConstraints(
            enabled=True,
            max_assets=30,
            min_position_size=0.02,
        )

        assert constraints.enabled is True
        assert constraints.max_assets == 30
        assert constraints.min_position_size == 0.02

    def test_group_based_cardinality(self) -> None:
        """Test group-based cardinality constraints."""
        constraints = CardinalityConstraints(
            enabled=True,
            max_assets=30,
            group_limits={"equity": 20, "fixed_income": 10},
        )

        assert constraints.group_limits is not None
        assert constraints.group_limits["equity"] == 20
        assert constraints.group_limits["fixed_income"] == 10

    def test_validation_max_assets_negative(self) -> None:
        """Test validation rejects negative max_assets."""
        with pytest.raises(ValueError, match="max_assets must be >= 1"):
            CardinalityConstraints(enabled=True, max_assets=0)

        with pytest.raises(ValueError, match="max_assets must be >= 1"):
            CardinalityConstraints(enabled=True, max_assets=-5)

    def test_validation_min_position_size_invalid(self) -> None:
        """Test validation rejects invalid min_position_size."""
        with pytest.raises(ValueError, match="min_position_size must be in"):
            CardinalityConstraints(enabled=True, min_position_size=0.0)

        with pytest.raises(ValueError, match="min_position_size must be in"):
            CardinalityConstraints(enabled=True, min_position_size=-0.01)

        with pytest.raises(ValueError, match="min_position_size must be in"):
            CardinalityConstraints(enabled=True, min_position_size=1.5)

    def test_validation_group_limits_invalid(self) -> None:
        """Test validation rejects invalid group_limits."""
        with pytest.raises(ValueError, match="group_limits.*must be >= 1"):
            CardinalityConstraints(
                enabled=True,
                group_limits={"equity": 0},
            )

        with pytest.raises(ValueError, match="group_limits.*must be >= 1"):
            CardinalityConstraints(
                enabled=True,
                group_limits={"equity": 20, "bonds": -5},
            )

    def test_validation_enforce_in_optimizer_requires_method(self) -> None:
        """Test enforce_in_optimizer requires non-preselection method."""
        with pytest.raises(
            ValueError,
            match="enforce_in_optimizer=True requires method != PRESELECTION",
        ):
            CardinalityConstraints(
                enabled=True,
                method=CardinalityMethod.PRESELECTION,
                enforce_in_optimizer=True,
            )

    def test_validation_disabled_constraints_no_error(self) -> None:
        """Test disabled constraints skip validation."""
        # Should not raise even with invalid parameters
        constraints = CardinalityConstraints(
            enabled=False,
            max_assets=-1,  # Invalid if enabled
            min_position_size=0.0,  # Invalid if enabled
        )
        assert constraints.enabled is False


class TestCardinalityMethod:
    """Tests for CardinalityMethod enum."""

    def test_enum_values(self) -> None:
        """Test enum has expected values."""
        assert CardinalityMethod.PRESELECTION.value == "preselection"
        assert CardinalityMethod.MIQP.value == "miqp"
        assert CardinalityMethod.HEURISTIC.value == "heuristic"
        assert CardinalityMethod.RELAXATION.value == "relaxation"

    def test_enum_from_string(self) -> None:
        """Test creating enum from string value."""
        method = CardinalityMethod("miqp")
        assert method == CardinalityMethod.MIQP

    def test_enum_invalid_string(self) -> None:
        """Test invalid string raises error."""
        with pytest.raises(ValueError):
            CardinalityMethod("invalid_method")


class TestValidateCardinalityConstraints:
    """Tests for validate_cardinality_constraints function."""

    def test_disabled_constraints_pass(self) -> None:
        """Test disabled constraints pass validation."""
        constraints = CardinalityConstraints(enabled=False)
        portfolio_constraints = PortfolioConstraints()

        # Should not raise
        validate_cardinality_constraints(
            constraints,
            portfolio_constraints,
            num_assets=100,
        )

    def test_preselection_method_passes(self) -> None:
        """Test preselection method passes validation."""
        constraints = CardinalityConstraints(
            enabled=True,
            method=CardinalityMethod.PRESELECTION,
            max_assets=30,
        )
        portfolio_constraints = PortfolioConstraints()

        # Should not raise
        validate_cardinality_constraints(
            constraints,
            portfolio_constraints,
            num_assets=100,
        )

    def test_non_preselection_method_raises(self) -> None:
        """Test non-preselection methods raise NotImplementedError."""
        for method in [
            CardinalityMethod.MIQP,
            CardinalityMethod.HEURISTIC,
            CardinalityMethod.RELAXATION,
        ]:
            constraints = CardinalityConstraints(
                enabled=True,
                method=method,
                max_assets=30,
            )
            portfolio_constraints = PortfolioConstraints()

            with pytest.raises(CardinalityNotImplementedError):
                validate_cardinality_constraints(
                    constraints,
                    portfolio_constraints,
                    num_assets=100,
                )

    def test_string_methods_normalize_and_raise(self) -> None:
        """String methods should normalize to enums before raising."""
        constraints = CardinalityConstraints(
            enabled=True,
            method="miqp",
            max_assets=30,
        )
        portfolio_constraints = PortfolioConstraints()

        with pytest.raises(CardinalityNotImplementedError):
            validate_cardinality_constraints(
                constraints,
                portfolio_constraints,
                num_assets=100,
            )

    def test_unknown_method_string_raises(self) -> None:
        """Unknown string methods raise CardinalityNotImplementedError."""
        constraints = CardinalityConstraints(
            enabled=True,
            method="totally_new_method",
            max_assets=30,
        )
        portfolio_constraints = PortfolioConstraints()

        with pytest.raises(CardinalityNotImplementedError) as exc_info:
            validate_cardinality_constraints(
                constraints,
                portfolio_constraints,
                num_assets=100,
            )

        assert "totally_new_method" in str(exc_info.value)

    def test_max_assets_exceeds_universe(self) -> None:
        """Test max_assets > num_assets raises error."""
        constraints = CardinalityConstraints(
            enabled=True,
            max_assets=150,
        )
        portfolio_constraints = PortfolioConstraints()

        with pytest.raises(ValueError, match="exceeds universe size"):
            validate_cardinality_constraints(
                constraints,
                portfolio_constraints,
                num_assets=100,
            )

    def test_infeasible_position_sizes(self) -> None:
        """Test infeasible position sizes raise error."""
        constraints = CardinalityConstraints(
            enabled=True,
            max_assets=30,
            min_position_size=0.04,  # 30 * 0.04 = 1.2 > 1.0
        )
        portfolio_constraints = PortfolioConstraints(require_full_investment=True)

        with pytest.raises(ValueError, match="Infeasible.*min_position_size"):
            validate_cardinality_constraints(
                constraints,
                portfolio_constraints,
                num_assets=100,
            )

    def test_group_limits_warning(self) -> None:
        """Test group_limits < max_assets triggers warning."""
        constraints = CardinalityConstraints(
            enabled=True,
            max_assets=30,
            group_limits={"equity": 10, "bonds": 10},  # Sum = 20 < 30
        )
        portfolio_constraints = PortfolioConstraints()

        with pytest.warns(UserWarning, match="Sum of group_limits"):
            validate_cardinality_constraints(
                constraints,
                portfolio_constraints,
                num_assets=100,
            )


class TestCardinalityNotImplementedError:
    """Tests for CardinalityNotImplementedError exception."""

    def test_error_message_format(self) -> None:
        """Test error message is informative."""
        error = CardinalityNotImplementedError("miqp")

        assert "miqp" in str(error)
        assert "not yet implemented" in str(error).lower()
        assert "preselection" in str(error)
        assert "MIQP" in str(error)
        assert "Heuristic" in str(error)

    def test_error_attributes(self) -> None:
        """Test error has expected attributes."""
        error = CardinalityNotImplementedError("heuristic", ["preselection"])

        assert error.method == "heuristic"
        assert error.available_methods == ["preselection"]


class TestOptimizerStubs:
    """Tests for optimizer stub functions."""

    @pytest.fixture
    def sample_returns(self) -> pd.DataFrame:
        """Create sample returns data."""
        dates = pd.date_range("2020-01-01", periods=100, freq="D")
        assets = ["AAPL", "MSFT", "GOOGL"]
        data = {asset: [0.001 * (i % 3 - 1) for i in range(100)] for asset in assets}
        return pd.DataFrame(data, index=dates)

    @pytest.fixture
    def constraints(self) -> PortfolioConstraints:
        """Create portfolio constraints."""
        return PortfolioConstraints()

    @pytest.fixture
    def cardinality(self) -> CardinalityConstraints:
        """Create cardinality constraints."""
        return CardinalityConstraints(
            enabled=True,
            method=CardinalityMethod.MIQP,
            max_assets=2,
        )

    def test_miqp_stub_raises(
        self,
        sample_returns: pd.DataFrame,
        constraints: PortfolioConstraints,
        cardinality: CardinalityConstraints,
    ) -> None:
        """Test MIQP stub raises CardinalityNotImplementedError."""
        with pytest.raises(CardinalityNotImplementedError) as excinfo:
            optimize_with_cardinality_miqp(
                sample_returns,
                constraints,
                cardinality,
            )

        assert "miqp" in str(excinfo.value).lower()

    def test_heuristic_stub_raises(
        self,
        sample_returns: pd.DataFrame,
        constraints: PortfolioConstraints,
        cardinality: CardinalityConstraints,
    ) -> None:
        """Test heuristic stub raises CardinalityNotImplementedError."""
        with pytest.raises(CardinalityNotImplementedError) as excinfo:
            optimize_with_cardinality_heuristic(
                sample_returns,
                constraints,
                cardinality,
            )

        assert "heuristic" in str(excinfo.value).lower()

    def test_relaxation_stub_raises(
        self,
        sample_returns: pd.DataFrame,
        constraints: PortfolioConstraints,
        cardinality: CardinalityConstraints,
    ) -> None:
        """Test relaxation stub raises CardinalityNotImplementedError."""
        with pytest.raises(CardinalityNotImplementedError) as excinfo:
            optimize_with_cardinality_relaxation(
                sample_returns,
                constraints,
                cardinality,
            )

        assert "relaxation" in str(excinfo.value).lower()


class TestGetCardinalityOptimizer:
    """Tests for get_cardinality_optimizer factory function."""

    def test_preselection_raises(self) -> None:
        """Test preselection method raises ValueError."""
        with pytest.raises(ValueError, match="Use preselection module directly"):
            get_cardinality_optimizer("preselection")

    def test_miqp_returns_function(self) -> None:
        """Test MIQP method returns function."""
        optimizer = get_cardinality_optimizer("miqp")
        assert callable(optimizer)
        assert optimizer == optimize_with_cardinality_miqp

    def test_heuristic_returns_function(self) -> None:
        """Test heuristic method returns function."""
        optimizer = get_cardinality_optimizer("heuristic")
        assert callable(optimizer)
        assert optimizer == optimize_with_cardinality_heuristic

    def test_relaxation_returns_function(self) -> None:
        """Test relaxation method returns function."""
        optimizer = get_cardinality_optimizer("relaxation")
        assert callable(optimizer)
        assert optimizer == optimize_with_cardinality_relaxation

    def test_invalid_method_raises(self) -> None:
        """Test invalid method raises ValueError."""
        with pytest.raises(ValueError, match="Unknown cardinality method"):
            get_cardinality_optimizer("invalid_method")


class TestIntegrationScenarios:
    """Integration tests for cardinality constraint scenarios."""

    def test_disabled_cardinality_no_impact(self) -> None:
        """Test disabled cardinality has no effect."""
        constraints = CardinalityConstraints(enabled=False, max_assets=5)
        portfolio_constraints = PortfolioConstraints()

        # Should pass validation even with small max_assets
        validate_cardinality_constraints(
            constraints,
            portfolio_constraints,
            num_assets=100,
        )

    def test_realistic_configuration(self) -> None:
        """Test realistic cardinality configuration."""
        constraints = CardinalityConstraints(
            enabled=True,
            method=CardinalityMethod.PRESELECTION,
            max_assets=30,
            min_position_size=0.02,
            group_limits={"equity": 20, "fixed_income": 10},
        )
        portfolio_constraints = PortfolioConstraints(
            max_weight=0.15,
            min_weight=0.01,
        )

        # Should pass validation
        validate_cardinality_constraints(
            constraints,
            portfolio_constraints,
            num_assets=500,
        )

    def test_edge_case_single_asset(self) -> None:
        """Test edge case with single asset universe."""
        constraints = CardinalityConstraints(
            enabled=True,
            max_assets=1,
            min_position_size=1.0,
        )
        portfolio_constraints = PortfolioConstraints()

        # Should pass validation
        validate_cardinality_constraints(
            constraints,
            portfolio_constraints,
            num_assets=1,
        )
