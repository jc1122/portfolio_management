"""Tests for portfolio construction exceptions."""

import pandas as pd
import pytest

from portfolio_management.exceptions import (
    ConstraintViolationError,
    DependencyError,
    InsufficientDataError,
    InvalidStrategyError,
    OptimizationError,
    PortfolioConstructionError,
    PortfolioManagementError,
)
from portfolio_management.portfolio import (
    Portfolio,
    PortfolioConstraints,
    RebalanceConfig,
)


def test_portfolio_construction_error_inheritance():
    """Test that PortfolioConstructionError inherits from PortfolioManagementError."""
    assert issubclass(PortfolioConstructionError, PortfolioManagementError)


def test_invalid_strategy_error_inheritance():
    """Test that InvalidStrategyError inherits from PortfolioConstructionError."""
    assert issubclass(InvalidStrategyError, PortfolioConstructionError)


def test_constraint_violation_error():
    """Test ConstraintViolationError creation and attributes."""
    error = ConstraintViolationError(constraint_name="turnover", violated_value=0.5)
    assert issubclass(ConstraintViolationError, PortfolioConstructionError)
    assert error.constraint_name == "turnover"
    assert error.violated_value == 0.5
    assert "Constraint 'turnover' was violated with value: 0.5." in str(error)


def test_optimization_error():
    """Test OptimizationError creation and attributes."""
    error = OptimizationError(strategy_name="mean_variance")
    assert issubclass(OptimizationError, PortfolioConstructionError)
    assert error.strategy_name == "mean_variance"
    assert "Optimization failed for strategy: 'mean_variance'." in str(error)


def test_insufficient_data_error():
    """Test InsufficientDataError creation and attributes."""
    error = InsufficientDataError(required_periods=100, available_periods=50)
    assert issubclass(InsufficientDataError, PortfolioConstructionError)
    assert error.required_periods == 100
    assert error.available_periods == 50
    assert (
        "Insufficient data for portfolio construction. Required: 100, Available: 50."
        in str(error)
    )


def test_dependency_error():
    """Test DependencyError creation and attributes."""
    error = DependencyError(dependency_name="riskparityportfolio")
    assert issubclass(DependencyError, PortfolioConstructionError)
    assert error.dependency_name == "riskparityportfolio"
    assert "Optional dependency 'riskparityportfolio' is not installed." in str(error)


class TestPortfolioConstraints:
    """Tests for PortfolioConstraints dataclass."""

    def test_valid_constraints(self):
        """Test valid constraint initialization."""
        constraints = PortfolioConstraints(
            max_weight=0.25,
            min_weight=0.0,
            max_equity_exposure=0.90,
            min_bond_exposure=0.10,
        )
        assert constraints.max_weight == 0.25
        assert constraints.min_weight == 0.0

    def test_invalid_weight_bounds(self):
        """Test invalid weight bounds raise ValueError."""
        with pytest.raises(ValueError, match="Invalid weight bounds"):
            PortfolioConstraints(max_weight=0.1, min_weight=0.2)

    def test_invalid_exposure_bounds(self):
        """Test invalid exposure bounds raise ValueError."""
        with pytest.raises(ValueError, match="Invalid min_bond_exposure"):
            PortfolioConstraints(min_bond_exposure=1.1)

        with pytest.raises(ValueError, match="Invalid max_equity_exposure"):
            PortfolioConstraints(max_equity_exposure=-0.1)

    def test_infeasible_constraints(self):
        """Test infeasible constraints raise ValueError."""
        with pytest.raises(ValueError, match="Infeasible constraints"):
            PortfolioConstraints(min_bond_exposure=0.6, max_equity_exposure=0.3)


class TestRebalanceConfig:
    """Tests for RebalanceConfig dataclass."""

    def test_valid_config(self):
        """Test valid rebalance config initialization."""
        config = RebalanceConfig(
            frequency=30,
            tolerance_bands=0.2,
            min_trade_size=0.01,
            cost_per_trade=0.001,
        )
        assert config.frequency == 30

    def test_invalid_frequency(self):
        """Test invalid frequency raises ValueError."""
        with pytest.raises(ValueError, match="Invalid frequency"):
            RebalanceConfig(frequency=0)

    def test_invalid_tolerance_bands(self):
        """Test invalid tolerance bands raise ValueError."""
        with pytest.raises(ValueError, match="Invalid tolerance_bands"):
            RebalanceConfig(tolerance_bands=1.1)


class TestPortfolio:
    """Tests for Portfolio dataclass."""

    def test_valid_portfolio(self):
        """Test valid portfolio initialization."""
        weights = pd.Series([0.5, 0.5], index=["A", "B"])
        portfolio = Portfolio(weights=weights, strategy="test")
        assert portfolio.get_position_count() == 2

    def test_negative_weights(self):
        """Test negative weights raise ValueError."""
        weights = pd.Series([1.1, -0.1], index=["A", "B"])
        with pytest.raises(ValueError, match="Portfolio weights cannot be negative"):
            Portfolio(weights=weights, strategy="test")

    def test_non_normalized_weights(self):
        """Test non-normalized weights raise ValueError."""
        weights = pd.Series([0.5, 0.6], index=["A", "B"])
        with pytest.raises(ValueError, match=r"Portfolio weights must sum to 1\.0"):
            Portfolio(weights=weights, strategy="test")

    def test_empty_portfolio(self):
        """Test empty portfolio raises ValueError."""
        weights = pd.Series([], dtype=float)
        with pytest.raises(
            ValueError,
            match="Portfolio must contain at least one asset",
        ):
            Portfolio(weights=weights, strategy="test")

    def test_get_top_holdings(self):
        """Test get_top_holdings method."""
        weights = pd.Series([0.1, 0.4, 0.3, 0.2], index=["D", "A", "B", "C"])
        portfolio = Portfolio(weights=weights, strategy="test")
        top_2 = portfolio.get_top_holdings(2)
        assert top_2.equals(pd.Series([0.4, 0.3], index=["A", "B"]))
